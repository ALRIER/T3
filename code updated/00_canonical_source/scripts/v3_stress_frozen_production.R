#!/usr/bin/env Rscript
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=3L)stop('Usage: FAMILY STRESS_SEED N')
family<-args[[1L]];seed<-as.integer(args[[2L]]);n<-as.integer(args[[3L]])
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
source('R/00_shared/t2_v3_b3_resources.R')
source('R/00_shared/t3_b3_partitions.R')
if(!seed%in%t2_v3_indices('stress') || !n%in%t2_v3_sample_sizes('stress'))stop('Reserved stress role contract violated')
t3_stage_preflight('stress',family,seed,n,require_scenarios=TRUE)
out<-file.path('artifacts','v3_stress_scoring',family,sprintf('seed%02d_n%d',seed,n))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
input<-file.path('artifacts','discovery_v3')
scenario_ids<-t3_b3_partition_ids('stress_exclusive')
if(!dir.exists(input))stop('Frozen Discovery results absent')
t2_b3_inputs_manifest(c(
  file.path(input,family,sprintf('seed%02d',0:9),sprintf('n%d',n),'discovery.rds'),
  file.path(t2_v3_block_dir('stress',family,seed,n),sprintf('scenario_%04d.rds',scenario_ids))
),out,'stress')
t2_b3_ram_guard('stress',out,'start')
first<-TRUE
for(training_seed in 0:9) {
  source_file<-file.path(input,family,sprintf('seed%02d',training_seed),sprintf('n%d',n),'discovery.rds')
  if(!file.exists(source_file))stop('Missing frozen Discovery: ',source_file)
  t3_stage_require(file.path(dirname(source_file),'stage_contract.rds'),
     'discovery',sprintf('b3_%s_n%d',family,n),family,training_seed,n)
  fit<-t2_read_rds(source_file)
  if(length(fit$engines)!=4L)stop('Incomplete frozen engine registry')
  baselines<-lapply(ESTIMATOR_NAMES,function(nm)new_frozen_model(nm,component=nm))
  learned<-Filter(function(m)!is.null(m$weights),fit$models)
  models<-c(baselines,learned)
  if(length(models)!=30L)stop('B3 requires all 26 benchmarks and four frozen learners')
  controls<-fit$non_evolutionary_controls
  if(!is.list(controls)||!setequal(names(controls),c('convex_mse','local_deterministic')))
    stop('Stress requires two frozen non-evolutionary controls')
  extra<-lapply(names(controls),function(id) {
    w<-as.matrix(controls[[id]]$weights)
    if(nrow(w)!=26L||ncol(w)!=1L||any(!is.finite(w))||
       any(w<0)||abs(sum(w)-1)>1e-8)stop('Invalid frozen stress control')
    new_frozen_model(id,weights=as.numeric(w[,1L]),family=id)
  })
  models<-c(models,extra)
  if(length(models)!=32L)stop('Stress comparison must contain 32 models')
  if(length(models)<8L || anyDuplicated(vapply(models,function(m)m$id,character(1))))
    stop('Invalid frozen candidate registry')
  z<-t2_v3_stream_scores('stress',family,seed,n,models,reps=500L,selected=scenario_ids)
  z$training_seed<-training_seed
  z$stress_seed<-seed
  z$source_family<-family
  z$evaluation_family<-family
  z$transfer_scope<-t3_b3_transfer_scope(family,family,'stress',z$mechanism)
  z$source_discovery_sha256<-t2_sha256(source_file)
  outpath<-file.path(out,'scores.csv')
  write.table(z,outpath,append=!first,row.names=FALSE,col.names=first,
              sep=',',quote=TRUE)
  first<-FALSE
  rows_written<-nrow(z)
  rm(fit,models,z,learned,baselines);invisible(gc(verbose=FALSE))
  t2_b3_ram_guard('stress',out,paste0('train_',training_seed))
  cat('V3_STRESS_SCORE_PASS',family,'train',training_seed,'stress',seed,'n',n,'rows',rows_written,'\\n')
}
summary<-read.csv(file.path(out,'scores.csv'))
if(any(!is.finite(summary$mse)) || any(!is.finite(summary$q95)))stop('Invalid stress scores')
write.csv(aggregate(cbind(mse,q95)~model+training_seed,data=summary,FUN=mean),
  file.path(out,'training_comparison.csv'),row.names=FALSE)
t3_stage_publish('stress',sprintf('b3_%s_n%d',family,n),
 list(scores_path=file.path(out,'scores.csv'),
      score_sha256=t2_sha256(file.path(out,'scores.csv')),scenario_ids=scenario_ids),
 family,seed,n,500L,file.path(out,'stage_contract.rds'))
t3_stage_postflight(file.path(out,'stage_contract.rds'),'stress',family,seed,n,expected_files=file.path(out,'scores.csv'))
cat('V3_STRESS_SHARD_PASS',family,seed,n,'\\n')

# Publish canonical B3-named counterparts without breaking existing downstream references.
source('R/00_shared/t2_v3_b3_naming.R')
t2_b3_publish(out)
