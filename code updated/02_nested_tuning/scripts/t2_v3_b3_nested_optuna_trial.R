#!/usr/bin/env Rscript
a<-commandArgs(TRUE)
if(length(a)!=7L)stop('Usage: FAMILY SEED OUTER_FOLD INNER_FOLD ENGINE PARAMS_JSON N')
fam<-a[1];seed<-as.integer(a[2]);outer<-as.integer(a[3]);inner<-as.integer(a[4]);engine<-a[5];path<-a[6];n<-as.integer(a[7])
if(!engine%in%c('ga','nsga2','de','dirichlet')||!seed%in%0:9||!outer%in%1:5||!inner%in%1:3)stop('Invalid nested fold')
if(!requireNamespace('jsonlite',quietly=TRUE))stop('jsonlite required')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
source('R/02_discovery/t3_predeclared_w_selection.R')
params<-jsonlite::fromJSON(path)
source('R/02_discovery/t2_v3_b3_nested_folds.R')
parts<-t2_b3_nested_partitions(fam,seed,outer,inner,n=n)
training_ids<-parts$training
validation_ids<-parts$validation
if(length(intersect(training_ids,validation_ids))||length(training_ids)<50L||!length(validation_ids))stop('Nested fold leakage')
training<-t2_v3_discovery_input(fam,seed,n=n,selected=training_ids)$scenarios
cfg<-ga_config
cfg$population<-as.integer(params$population)
cfg$generations<-as.integer(params$generations)
cfg$mutation_rate<-as.numeric(params$mutation_rate)
cfg$crossover_probability<-as.numeric(params$crossover_probability)
cfg$discovery_weight_regularization_lambda<-as.numeric(params$regularization_lambda)
# Adaptive early stopping remains enabled; actual and maximum costs are recorded.
set.seed(t2_seed(paste('B3_nested',fam,seed,outer,inner,engine,basename(path)),821L))
trial_started<-proc.time()[['elapsed']]
fit<-switch(engine,ga=ga_discover(training,cfg,seed=sample.int(1000000000,1),shard=NULL),
nsga2=nsga_discover(training,cfg,seed=sample.int(1000000000,1),shard=NULL),
de=de_discover(training,cfg,seed=sample.int(1000000000,1),
 F=as.numeric(params$F),CR=as.numeric(params$CR),shard=NULL),
dirichlet=dirichlet_discover(training,cfg,seed=sample.int(1000000000,1),
 alpha=as.numeric(params$alpha),n_draws=t3_common_budget(cfg),shard=NULL))

training_scales<-t3_training_reference_scales(training)
chosen<-t3_select_weights(fit,training_scales)
trial_evaluations<-as.integer(fit$evaluations_used)
trial_budget<-as.integer(fit$evaluation_budget)
trial_elapsed<-as.numeric(proc.time()[['elapsed']]-trial_started)
trial_scenarios<-length(training_ids)
if(is.na(trial_evaluations)||trial_evaluations<1L||trial_evaluations>trial_budget)
 stop('Invalid observed Optuna trial computational cost')
w<-matrix(chosen$weights,ncol=1L)
rm(training,fit);invisible(gc(FALSE))
val<-t2_v3_discovery_input(fam,seed,n=n,selected=validation_ids)$scenarios
stats<-t(vapply(val,function(sc)as.numeric(evaluate_weights(sc$T,w,sc$target)$objectives[1,]),numeric(2)))
base<-t(vapply(val,function(sc){
 e<-(sc$T[,1L]-sc$target)^2
 c(mean(e),unname(quantile(e,.95,type=8)))
},numeric(2)))
score<-0.5*mean(stats[,1]/pmax(base[,1],1e-12))+0.5*mean(stats[,2]/pmax(base[,2],1e-12))
cat(jsonlite::toJSON(list(score=score,outer=outer,inner=inner,engine=engine,
 validation_scenarios=length(validation_ids),
 objective_evaluations=trial_evaluations,maximum_objective_evaluations=trial_budget,
 scenario_evaluations=trial_evaluations*trial_scenarios,
 training_scenarios=trial_scenarios,elapsed_seconds=trial_elapsed,
 early_stop_saved=trial_budget-trial_evaluations,
 budget_policy='B3_EQUAL_MAX_BUDGET_ADAPTIVE_V2'),auto_unbox=TRUE),'\n')
