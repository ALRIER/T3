#!/usr/bin/env Rscript
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/02_discovery/t3_predeclared_w_selection.R')
set.seed(412L)
scenarios<-lapply(1:5,function(i) {
 T<-matrix(rnorm(30L*26L),30L,26L)
 colnames(T)<-ESTIMATOR_NAMES
 list(T=T,target=0)
})
s<-t3_training_reference_scales(scenarios)
stopifnot(identical(names(s),c('mse','q95')),all(s>0))
mk<-function() {
 W<-matrix(rexp(26L*3L),26L,3L);W<-sweep(W,2,colSums(W),'/')
 O<-matrix(c(1,3,2,2,3,1),ncol=2)
 colnames(O)<-c('mse','q95')
 list(weights=W,objectives=O,evaluations_used=20L,evaluation_budget=30L,
      budget_policy='B3_EQUAL_MAX_BUDGET_ADAPTIVE_V2')
}
engines<-setNames(replicate(4,mk(),simplify=FALSE),c('ga','nsga2','de','dirichlet'))
stopifnot(nrow(t3_assert_engine_budget_parity(engines))==4L)
broken<-engines;broken$de$evaluations_used<-31L
stopifnot(inherits(try(t3_assert_engine_budget_parity(broken),silent=TRUE),'try-error'))
z<-t3_select_models(engines,scenarios)
stopifnot(length(z$models)==30L,
  identical(vapply(z$models[1:26],function(x)x$id,character(1)),ESTIMATOR_NAMES),
  identical(vapply(z$models[27:30],function(x)x$id,character(1)),names(engines)),
  all(vapply(z$selection,function(x)identical(x$scales,z$scales),logical(1))),
  all(vapply(z$selection,function(x)abs(sum(x$weights)-1)<1e-10,logical(1))))
d<-score_model_set(scenarios[[1]]$T,z$models,0)
stopifnot(nrow(d)==30L,all(is.finite(d$mse)),all(is.finite(d$q95)))
cat('T3_26_BENCHMARK_COMMON_W_SELECTION_PASS\n')

# Lightweight shared-objective smoke for non-evolutionary controls.
cfg<-ga_config;cfg$population<-4L;cfg$generations<-2L
cfg$early_stop_enabled<-FALSE
training<-lapply(seq_along(scenarios),function(i) {
  z<-scenarios[[i]]
  z$band<-c('clean','low','intermediate','high')[((i-1L)%%4L)+1L]
  z$eligible<-rep(TRUE,26L)
  z$benchmark<-precompute_benchmarks(z$T,z$target,z$eligible)
  z
})
controls<-list(convex_mse=t3_control_optimize(training,cfg,method='convex_mse'),
               local_deterministic=t3_control_optimize(training,cfg,method='local_deterministic'))
stopifnot(nrow(t3_assert_engine_budget_parity(controls))==2L)
for(z in controls)stopifnot(z$evaluations_used<=t3_common_budget(cfg),
  abs(sum(z$weights)-1)<1e-8,all(z$weights>=0),
  nrow(t3_convergence_table(z,t3_training_reference_scales(training)))>=1L)
cat('T3_NON_EVOLUTIONARY_CONTROLS_SMOKE_PASS\\n')
