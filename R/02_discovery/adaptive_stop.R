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
t3_convergence_point <- function(objectives, evaluations, scales=NULL) {
  O<-as.matrix(objectives)
  if(ncol(O)!=2L||!nrow(O)||any(!is.finite(O)))stop("Invalid convergence objectives")
  if(!is.null(colnames(O))&&all(c("mse","q95")%in%colnames(O)))
    O<-O[,c("mse","q95"),drop=FALSE]
  if(is.null(scales))scales<-c(mse=1,q95=1)
  if(any(!is.finite(scales))||any(scales<=0))stop("Invalid reference scales")
  j<-which.min(rowMeans(sweep(O,2L,as.numeric(scales[c("mse","q95")]),"/")))
  c(evaluations=as.numeric(evaluations),mse=O[j,1L],q95=O[j,2L],
    joint_normalized=mean(O[j,]/as.numeric(scales[c("mse","q95")])))
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
