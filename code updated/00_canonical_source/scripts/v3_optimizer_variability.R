#!/usr/bin/env Rscript
# Three optimizer-seed repeats on one fixed Discovery shard. Audit only:
# never selects replacement production weights and never consumes heldout data.
a<-commandArgs(TRUE)
if(length(a)!=3L)stop('Usage: FAMILY DISCOVERY_SEED N')
family<-a[1];seed<-as.integer(a[2]);n<-as.integer(a[3])
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R');source('R/00_shared/v3_scientific_adapter.R')
source('R/02_discovery/t3_predeclared_w_selection.R');source('R/00_shared/t3_b3_partitions.R')
if(!family%in%t2_families()||!seed%in%t2_v3_indices('discovery')||n!=1000L)stop('Audit design is fixed to n=1000')
root<-file.path('artifacts','v3_optimizer_variability',family,sprintf('seed%02d_n%d',seed,n))
dir.create(root,recursive=TRUE,showWarnings=FALSE)
completion_manifest<-file.path(root,'audit_complete.csv')
if(file.exists(completion_manifest))stop('Immutable optimizer audit output already completed')
d<-t2_v3_discovery_input(family,seed,n,500L,t3_b3_partition_ids('discovery_support'))
hpo_path<-file.path('artifacts','discovery_v3',family,sprintf('seed%02d',seed),sprintf('n%d',n),'frozen_hyperparameters.json')
model_path<-file.path('artifacts','discovery_v3',family,sprintf('seed%02d',seed),sprintf('n%d',n),'discovery.rds')
contract<-t3_stage_require(file.path(dirname(model_path),'stage_contract.rds'),'discovery',
  sprintf('b3_%s_n%d',family,n),family,seed,n)
if(!file.exists(model_path)||!identical(contract$payload$model_sha256,t2_sha256(model_path)))
  stop('Optimizer sensitivity audit requires the matching immutable frozen Discovery model')
if(!file.exists(hpo_path)||!requireNamespace('jsonlite',quietly=TRUE))stop('Frozen nested HPO registry missing')
hpo<-jsonlite::fromJSON(hpo_path,simplifyVector=FALSE)
if(!identical(hpo$protocol,'T3_B3_nested_5x3_hpo_freeze_v2_equal_budget'))stop('HPO protocol mismatch')
if(!identical(hpo$family,family)||as.integer(hpo$seed)!=seed||
   as.integer(hpo$sample_n)!=n||!identical(as.integer(hpo$outer_folds),5L)||
   !identical(as.integer(hpo$inner_folds),3L)||
   !setequal(names(hpo$engines),c('ga','nsga2','de','dirichlet')))
  stop('Frozen HPO registry provenance mismatch')
chosen<-list();summary<-list()
for(rep_id in 1:3) {
  repeat_path<-file.path(root,sprintf('repeat_%02d.rds',rep_id))
  if(file.exists(repeat_path)) {
    checkpoint<-readRDS(repeat_path)
    if(!identical(checkpoint$family,family)||!identical(as.integer(checkpoint$seed),seed)||
       !identical(as.integer(checkpoint$n),n)||!identical(as.integer(checkpoint$repeat_id),rep_id)||
       !identical(checkpoint$audit_only,TRUE)||
       !setequal(names(checkpoint$selected),c('ga','nsga2','de','dirichlet'))||
       !setequal(checkpoint$engine_accounting$engine,c('ga','nsga2','de','dirichlet')))
      stop('Existing optimizer repeat checkpoint is invalid: ',repeat_path)
    pick<-list(selection=checkpoint$selected)
    accounting<-checkpoint$engine_accounting
  } else {
    engines<-list()
    for(engine in c('ga','nsga2','de','dirichlet')) {
      p<-hpo$engines[[engine]];cfg<-ga_config
      cfg$population<-as.integer(p$population);cfg$generations<-as.integer(p$generations)
      cfg$mutation_rate<-as.numeric(p$mutation_rate);cfg$crossover_probability<-as.numeric(p$crossover_probability)
      cfg$discovery_weight_regularization_lambda<-as.numeric(p$regularization_lambda)
      run_seed<-t2_seed(paste('T3_OPTIMIZER_VARIABILITY',family,seed,n,rep_id,engine),8181L)
      engines[[engine]]<-switch(engine,
        ga=ga_discover(d$scenarios,cfg,run_seed,shard=NULL),
        nsga2=nsga_discover(d$scenarios,cfg,run_seed,shard=NULL),
        de=de_discover(d$scenarios,cfg,run_seed,F=as.numeric(p$F),CR=as.numeric(p$CR),shard=NULL),
        dirichlet=dirichlet_discover(d$scenarios,cfg,run_seed,alpha=as.numeric(p$alpha),n_draws=t3_common_budget(cfg),shard=NULL))
    }
    t3_assert_engine_budget_parity(engines)
    pick<-t3_select_models(engines,d$scenarios)
    accounting<-data.frame(engine=names(engines),
      evaluations=vapply(engines,function(x)as.integer(x$evaluations_used),integer(1)),
      budget=vapply(engines,function(x)as.integer(x$evaluation_budget),integer(1)))
    t2_atomic_save(list(family=family,seed=seed,n=n,repeat_id=rep_id,
      selected=pick$selection,engine_accounting=accounting,
      selection_policy='T3_EQUAL_MSE_Q95_BASELINE26_TRAIN_ONLY_V1',audit_only=TRUE),repeat_path)
    rm(engines);invisible(gc(FALSE))
  }
  chosen[[rep_id]]<-pick$selection
  for(engine in names(pick$selection)) {
    w<-as.numeric(pick$selection[[engine]]$weights)
    o<-pick$selection[[engine]]
    summary[[length(summary)+1L]]<-data.frame(family,seed,sample_n=n,repeat_id=rep_id,
      engine,normalized_loss=o$normalized_loss,mse=o$mse,q95=o$q95,
      evaluations=accounting$evaluations[match(engine,accounting$engine)],
      budget=accounting$budget[match(engine,accounting$engine)],
      stringsAsFactors=FALSE)
    if(length(w)!=26L||any(!is.finite(w))||any(w<0)||abs(sum(w)-1)>1e-8)
      stop('Optimizer audit selected an invalid simplex vector')
  }
  rm(pick,accounting);invisible(gc(FALSE))
}
stability<-list()
for(engine in c('ga','nsga2','de','dirichlet'))for(i in 1:2) {
  x<-chosen[[i]][[engine]]$weights;y<-chosen[[i+1]][[engine]]$weights
  stability[[length(stability)+1L]]<-data.frame(family,seed,n,engine,
    repeat_a=i,repeat_b=i+1L,l1_weight_distance=sum(abs(x-y)),
    max_component_shift=max(abs(x-y)),correlation=if(sd(x)>0&&sd(y)>0)cor(x,y) else NA_real_,
    interpretation='descriptive_optimizer_seed_sensitivity')
}
write.csv(do.call(rbind,summary),file.path(root,'repeat_performance.csv'),row.names=FALSE)
write.csv(do.call(rbind,stability),file.path(root,'weight_stability.csv'),row.names=FALSE)
writeLines(c('Three optimizer RNG repeats; same frozen Discovery scenarios and nested-HPO parameters.',
 'Audit only: repeats never replace or select the production W.',
 'No confirmatory inference is performed.'),file.path(root,'scope.txt'))
write.csv(data.frame(status='PASS',family=family,seed=seed,n=n,
  repeat_checkpoints=paste(vapply(1:3,function(i)t2_sha256(file.path(root,sprintf('repeat_%02d.rds',i))),character(1)),collapse=';'),
  performance_sha256=t2_sha256(file.path(root,'repeat_performance.csv')),
  stability_sha256=t2_sha256(file.path(root,'weight_stability.csv')),
  code_revision=Sys.getenv('GITHUB_SHA','unverified-local')),
  completion_manifest,row.names=FALSE)
cat('V3_OPTIMIZER_VARIABILITY_PASS',family,seed,n,'repeats=3\n')
