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
  cfg$early_stop_enabled<-FALSE
  cfg$t3_equal_budget<-TRUE
  cfg
}
t3_budget_finalize <- function(result, cfg, engine, convergence=NULL) {
  expected<-t3_common_budget(cfg)
  if(is.null(result$evaluations_used)||result$evaluations_used!=expected)
    stop(sprintf("Budget parity failure %s: %s versus %s",engine,
      result$evaluations_used,expected))
  result$budget_policy<-"B3_EQUAL_CANDIDATE_EVALUATIONS_V1"
  result$evaluation_budget<-expected
  result$early_stop_enabled<-FALSE
  if(!is.null(convergence))result$convergence<-convergence
  result
}
