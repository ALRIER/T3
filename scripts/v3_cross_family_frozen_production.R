#!/usr/bin/env Rscript
# Frozen transfer audit: evaluate source-family W on an independent evaluation
# family. No refitting, retuning, or selection occurs in this script.
a<-commandArgs(TRUE)
if(length(a)!=4L)stop('Usage: ROLE EVALUATION_FAMILY EVALUATION_SEED N')
role<-a[1];eval_family<-a[2];eval_seed<-as.integer(a[3]);n<-as.integer(a[4])
if(!role%in%c('heldout','stress'))stop('Transfer confirmation requires heldout or stress')
source('R/00_shared/load_all.R');t2_load('.')
families<-c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
if(!eval_family%in%families||!eval_seed%in%t2_v3_indices(role)||!n%in%t2_v3_sample_sizes(role))stop('Invalid evaluation identity')
source('R/00_shared/pipeline.R');source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R');source('R/00_shared/t2_v3_b3_resources.R')
source('R/00_shared/t3_b3_partitions.R')
ids<-if(role=='heldout')t3_b3_partition_ids('discovery_support') else t3_b3_partition_ids('stress_exclusive')
eval_block<-t2_v3_block_dir(role,eval_family,eval_seed,n,500L)
eval_contract<-t3_stage_require(file.path(eval_block,'stage_contract.rds'),'montecarlo',
  sprintf('b3_%s_n%d',eval_family,n),eval_family,eval_seed,n)
if(!identical(eval_contract$payload$canonical_sha256,t2_sha256(file.path(eval_block,'canonical.rds'))))
  stop('Evaluation Monte Carlo contract checksum mismatch')
out<-file.path('artifacts','v3_cross_family_scoring',role,
  sprintf('evaluation_%s',eval_family),sprintf('seed%02d_n%d',eval_seed,n))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
target<-file.path(out,'scores.csv')
if(file.exists(target))stop('Immutable transfer shard already exists')
base<-lapply(ESTIMATOR_NAMES,function(nm)new_frozen_model(nm,component=nm))
first<-TRUE
for(source_family in setdiff(families,eval_family))for(train_seed in t2_v3_indices('discovery')) {
  d<-file.path('artifacts','discovery_v3',source_family,
    sprintf('seed%02d',train_seed),sprintf('n%d',n))
  model_file<-file.path(d,'discovery.rds')
  if(!file.exists(model_file))stop('Missing frozen source W: ',model_file)
  source_contract<-t3_stage_require(file.path(d,'stage_contract.rds'),'discovery',
    sprintf('b3_%s_n%d',source_family,n),source_family,train_seed,n)
  if(!identical(source_contract$payload$model_sha256,t2_sha256(model_file)))
    stop('Frozen source W checksum mismatch: ',model_file)
  fit<-t2_read_rds(model_file)
  learned<-Filter(function(m)!is.null(m$weights),fit$models)
  if(length(learned)!=4L)stop('Source model registry must contain four frozen engines')
  controls<-fit$non_evolutionary_controls
  if(!is.list(controls)||!setequal(names(controls),c('convex_mse','local_deterministic')))
    stop('Frozen non-evolutionary controls absent')
  control_models<-lapply(names(controls),function(id){
    w<-as.numeric(controls[[id]]$weights)
    if(length(w)!=26L||any(!is.finite(w))||any(w<0)||abs(sum(w)-1)>1e-8)stop('Invalid frozen control')
    new_frozen_model(id,weights=w,family=id)
  })
  models<-c(base,learned,control_models)
  if(length(models)!=32L||anyDuplicated(vapply(models,function(m)m$id,character(1))))stop('Invalid transfer panel')
  z<-t2_v3_stream_scores(role,eval_family,eval_seed,n,models,reps=500L,selected=ids)
  z$source_family<-source_family;z$evaluation_family<-eval_family
  z$family<-eval_family;z$transfer_scope<-t3_b3_transfer_scope(source_family,eval_family,role,z$mechanism)
  z$training_seed<-train_seed
  z[[paste0(role,'_seed')]]<-eval_seed
  z$discovery_sha256<-t2_sha256(model_file)
  write.table(z,target,sep=',',append=!first,col.names=first,row.names=FALSE,quote=TRUE)
  first<-FALSE
  rm(z,fit,learned,controls,control_models,models);invisible(gc(FALSE))
}
if(first)stop('No cross-family source model was evaluated')
manifest<-data.frame(role=role,source_families=paste(setdiff(families,eval_family),collapse=';'),
 evaluation_family=eval_family,evaluation_seed=eval_seed,n=n,
 scenario_ids=paste(ids,collapse=';'),scores_sha256=t2_sha256(target),
 evaluation_mc_sha256=eval_contract$payload$canonical_sha256,
 grid_sha256=t2_sha256('config/T2_V3_B3_prospective_321_grid.csv'),
 code_revision=Sys.getenv('GITHUB_SHA','unverified-local'),
 workflow_run_id=Sys.getenv('GITHUB_RUN_ID','local'),
 selection='frozen_source_weights_no_retuning',stringsAsFactors=FALSE)
write.csv(manifest,file.path(out,'transfer_manifest.csv'),row.names=FALSE)
cat('V3_CROSS_FAMILY_FROZEN_PASS',role,eval_family,eval_seed,n,'rows',length(ids)*32L*5L*10L,'\n')
