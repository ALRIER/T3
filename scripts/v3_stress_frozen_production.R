#!/usr/bin/env Rscript
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=3L)stop('Usage: FAMILY STRESS_SEED N')
family<-args[[1L]];seed<-as.integer(args[[2L]]);n<-as.integer(args[[3L]])
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
source('R/00_shared/t2_v3_b3_resources.R')
if(!seed%in%15:19 || !n%in%c(200L,1000L,3000L))stop('Reserved stress role contract violated')
out<-file.path('artifacts','v3_stress_scoring',family,sprintf('seed%02d_n%d',seed,n))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
input<-file.path('artifacts','discovery_v3')
if(!dir.exists(input))stop('Frozen Discovery results absent')
t2_b3_inputs_manifest(c(
  file.path(input,family,sprintf('seed%02d',0:9),'discovery.rds'),
  file.path(t2_v3_block_dir('stress',family,seed,n),sprintf('scenario_%04d.rds',0:120))
),out,'stress')
t2_b3_ram_guard('stress',out,'start')
first<-TRUE
for(training_seed in 0:9) {
  source_file<-file.path(input,family,sprintf('seed%02d',training_seed),'discovery.rds')
  if(!file.exists(source_file))stop('Missing frozen Discovery: ',source_file)
  fit<-t2_read_rds(source_file)
  if(length(fit$engines)!=4L)stop('Incomplete frozen engine registry')
  baselines<-lapply(ESTIMATOR_NAMES,function(nm)new_frozen_model(nm,component=nm))
  learned<-Filter(function(m)!is.null(m$weights),fit$models)
  models<-c(baselines,learned)
  if(length(models)!=30L)stop('B3 requires all 26 benchmarks and four frozen learners')
  if(length(models)<8L || anyDuplicated(vapply(models,function(m)m$id,character(1))))
    stop('Invalid frozen candidate registry')
  z<-t2_v3_stream_scores('stress',family,seed,n,models,reps=500L,selected=0:120)
  z$training_seed<-training_seed
  z$stress_seed<-seed
  z$source_discovery_sha256<-t2_sha256(source_file)
  outpath<-file.path(out,'scores.csv')
  write.table(z,outpath,append=!first,row.names=FALSE,col.names=first,
              sep=',',quote=TRUE)
  first<-FALSE
  rm(fit,models,z,learned,baselines);invisible(gc(verbose=FALSE))
  t2_b3_ram_guard('stress',out,paste0('train_',training_seed))
  cat('V3_STRESS_SCORE_PASS',family,'train',training_seed,'stress',seed,'n',n,'rows',nrow(z),'\\n')
}
summary<-read.csv(file.path(out,'scores.csv'))
if(any(!is.finite(summary$mse)) || any(!is.finite(summary$q95)))stop('Invalid stress scores')
write.csv(aggregate(cbind(mse,q95)~model+training_seed,data=summary,FUN=mean),
  file.path(out,'training_comparison.csv'),row.names=FALSE)
cat('V3_STRESS_SHARD_PASS',family,seed,n,'\\n')

# Publish canonical B3-named counterparts without breaking existing downstream references.
source('R/00_shared/t2_v3_b3_naming.R')
t2_b3_publish(out)
