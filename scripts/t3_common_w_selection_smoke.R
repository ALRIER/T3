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

# Stability: isolate seed, fold and n effects without mixing model families.
registry<-data.frame(family=rep('normal',4),engine=rep('ga',4),
 seed=c(0,1,0,0),fold=c(1,1,2,1),sample_n=c(200,200,200,1000))
registry$weights<-I(list(rep(1/26,26),c(0.5,rep(0.5/25,25)),
 rep(1/26,26),rep(1/26,26)))
st<-t3_w_stability(registry)
stopifnot(setequal(st$contrast,c('seed','fold','sample_n')),
 all(st$l1>=0),all(st$cosine<=1+1e-12))
cat('T3_FROZEN_W_STABILITY_SMOKE_PASS\\n')

# Global preregistered seed partition guard for all four experiment stages.
t2_assert_seed_plan_v3()
stopifnot(identical(t2_v3_indices('discovery'),0:9),
 identical(t2_v3_indices('heldout'),10:19),
 identical(t2_v3_indices('stress'),20:29),
 identical(t2_v3_indices('realworld'),30:39))
for(role in c('discovery','heldout','stress','realworld')) {
 for(other in setdiff(c('discovery','heldout','stress','realworld'),role))
  stopifnot(!any(t2_v3_indices(role)%in%t2_v3_indices(other)))
}
cat('T3_FORTY_DISJOINT_SEEDS_PASS\\n')

# Frozen baseline scales must control W selection and convergence identically.
objective_matrix<-matrix(c(1,10,2,3),nrow=2L,byrow=TRUE,
 dimnames=list(NULL,c('mse','q95')))
reference_scales<-c(mse=1,q95=20)
point<-t3_convergence_point(objective_matrix,7L,reference_scales)
stopifnot(identical(unname(point['mse']),1),
 abs(unname(point['joint_normalized'])-0.75)<1e-12)
cost<-t3_budget_ledger(engines,full_scenarios=321L,
 outer_folds=5L,inner_folds=3L,hyperparameter_trials=2L)
stopifnot(all(cost$evaluations_used==20L),
 all(cost$objective_scenario_evaluations==6420L),
 all(cost$tuning_max_objective_calls==900L))
cat('T3_FAIR_CONVERGENCE_AND_BUDGET_LEDGER_PASS\\n')
