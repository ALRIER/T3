# Training-only adaptive early stopping policy shared by GA, NSGA-II and DE.
# Indicators must be transformed to higher-is-better before calling.
t2_adaptive_stop <- function(history,stale,cfg) {
 if(!isTRUE(cfg$early_stop_enabled))return(FALSE)
 g<-length(history);minimum<-as.integer(if(is.null(cfg$min_generations)) max(10L,ceiling(.30*cfg$generations)) else cfg$min_generations)
 if(g<minimum)return(FALSE)
 window<-as.integer(if(is.null(cfg$stop_window)) 8L else cfg$stop_window)
 lower<-as.integer(if(is.null(cfg$patience)) 10L else cfg$patience)
 upper<-as.integer(if(is.null(cfg$max_patience)) max(lower,ceiling(.35*cfg$generations)) else cfg$max_patience)
 if(length(history)<window+1L)return(FALSE)
 recent<-tail(history,window+1L)
 gain<-diff(recent)
 scale<-max(1,abs(recent[1L]))
 signal<-max(0,sum(pmax(gain,0))/scale)
 threshold<-if(is.null(cfg$improvement)) .001 else cfg$improvement
 # Positive recent gains grant patience; quiet plateaus use base patience.
 extra<-if(signal>threshold) ceiling(min(1,signal/(5*threshold))*max(0,upper-lower)) else 0L
 effective<-min(upper,lower+extra)
 stale>=effective
}

# B3 confirmation-comparison budget: one objective evaluation per candidate W
# over the complete, identical training-scenario collection.
t3_common_budget <- function(cfg) {
  n<-as.integer(cfg$population); g<-as.integer(cfg$generations)
  if(length(n)!=1L||length(g)!=1L||is.na(n)||is.na(g)||n<4L||g<1L)
    stop("Invalid common optimization budget")
  as.integer(n*(g+1L))
}
t3_equal_budget_config <- function(cfg) {
  # Preserve original adaptive stopping; only cap the maximum budget.
  cfg$t3_equal_budget<-TRUE
  cfg
}
t3_budget_finalize <- function(result, cfg, engine, convergence=NULL) {
  expected<-t3_common_budget(cfg)
  if(is.null(result$evaluations_used)||!is.finite(result$evaluations_used)||result$evaluations_used<1L||result$evaluations_used>expected)
    stop(sprintf("Budget parity failure %s: %s versus %s",engine,
      result$evaluations_used,expected))
  result$budget_policy<-"B3_EQUAL_MAX_BUDGET_ADAPTIVE_V2"
  result$evaluation_budget<-expected
  result$early_stop_enabled<-isTRUE(cfg$early_stop_enabled)
  if(!is.null(convergence))result$convergence<-convergence
  result
}

# Training-only, comparable convergence at actual candidate-evaluation counts.
# The same prospectively fixed reference scales apply to all four engines.
t3_convergence_point <- function(objectives,evaluations,scales=NULL) {
 O<-as.matrix(objectives)
 if(ncol(O)!=2L||!nrow(O)||any(!is.finite(O)))stop("Invalid convergence objectives")
 if(!is.null(colnames(O))&&all(c("mse","q95")%in%colnames(O)))
   O<-O[,c("mse","q95"),drop=FALSE]
 if(is.null(scales))stop("Training-only reference scales are required")
 if(!all(c("mse","q95")%in%names(scales))||
    any(!is.finite(scales[c("mse","q95")]))||
    any(scales[c("mse","q95")]<=0))stop("Invalid reference scales")
 normalized<-rowMeans(sweep(O,2L,as.numeric(scales[c("mse","q95")]),"/"))
 j<-order(normalized,O[,1L],O[,2L],seq_len(nrow(O)))[1L]
 c(evaluations=as.numeric(evaluations),mse=unname(O[j,1L]),
   q95=unname(O[j,2L]),joint_normalized=unname(normalized[j]))
}

t3_convergence_table <- function(result, scales) {
  trace<-result$convergence
  if(is.null(trace)||!length(trace))stop("Missing actual convergence trace")
  z<-as.data.frame(do.call(rbind,trace))
  if(any(diff(z$evaluations)<=0)||tail(z$evaluations,1)!=result$evaluations_used)
    stop("Invalid cumulative evaluation steps")
  z$joint_normalized<-rowMeans(sweep(as.matrix(z[,c("mse","q95")]),2L,
    as.numeric(scales[c("mse","q95")]),"/"))
  z
}

# Shared scalar stop signal is the best-so-far training-only normalized loss.
t3_fair_stop_signal <- function(archive_objectives,actual_evaluations,scales) {
 point<-t3_convergence_point(archive_objectives,actual_evaluations,scales)
 list(point=point,history_value=-unname(point["joint_normalized"]))
}
# Audit objective calls separately from total tuning trials.
t3_budget_ledger <- function(engines,full_scenarios,outer_folds=1L,
                             inner_folds=1L,hyperparameter_trials=1L) {
 z<-data.frame(engine=names(engines),
  evaluations_used=vapply(engines,function(v)as.numeric(v$evaluations_used),numeric(1)),
  evaluations_cap=vapply(engines,function(v)as.numeric(v$evaluation_budget),numeric(1)))
 if(any(!is.finite(z$evaluations_used))||any(z$evaluations_used>z$evaluations_cap))
  stop("Invalid optimizer budget ledger")
 if(any(c(outer_folds,inner_folds,hyperparameter_trials)<1)||
    any(!is.finite(c(outer_folds,inner_folds,hyperparameter_trials))))stop("Invalid tuning design")
 z$scenarios_per_objective<-as.integer(full_scenarios)
 z$objective_scenario_evaluations<-z$evaluations_used*full_scenarios
 z$tuning_max_objective_calls<-z$evaluations_cap*outer_folds*inner_folds*hyperparameter_trials
 z$tuning_max_scenario_evaluations<-z$tuning_max_objective_calls*full_scenarios
 z$tuning_actual_objective_calls<-NA_real_
 z$tuning_actual_status<-"PENDING_TRIAL_LEDGER"
 z
}
