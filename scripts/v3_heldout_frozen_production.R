#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=3L)stop('Usage: FAMILY HELDOUT_SEED N')
family<-args[[1L]];seed<-as.integer(args[[2L]]);n<-as.integer(args[[3L]])
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
source('R/00_shared/t2_v3_b3_resources.R')
if(!seed %in% 10:14 || !n %in% c(200L,1000L,3000L))
  stop('Held-out reserved seed/sample-size contract violated')
root<-file.path('artifacts','discovery_v3')
out<-file.path('artifacts','heldout_v3',family,sprintf('seed%02d_n%d',seed,n))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
outcsv<-file.path(out,'scores.csv')
t2_b3_inputs_manifest(c(
  file.path(root,family,sprintf('seed%02d',0:9),'discovery.rds'),
  file.path(t2_v3_block_dir('heldout',family,seed,n),sprintf('scenario_%04d.rds',0:120))
),out,'heldout')
t2_b3_ram_guard('heldout',out,'start')
first<-TRUE
for(train_seed in 0:9) {
  frozen_file<-file.path(root,family,sprintf('seed%02d',train_seed),'discovery.rds')
  if(!file.exists(frozen_file)) stop('Missing immutable discovery model: ',frozen_file)
  fit<-t2_read_rds(frozen_file)
  if(length(fit$engines)!=4L || length(fit$models)<8L)stop('Frozen training registry incomplete')
  baselines<-lapply(ESTIMATOR_NAMES,function(nm)new_frozen_model(nm,component=nm))
  learned<-Filter(function(m)!is.null(m$weights),fit$models)
  models<-c(baselines,learned)
  if(length(models)!=30L)stop('B3 requires all 26 benchmarks and four frozen learners')
  z<-t2_v3_stream_scores('heldout',family,seed,n,models,
                        reps=500L,selected=0:120)
  z$training_seed<-train_seed
  z$heldout_seed<-seed
  z$discovery_sha256<-t2_sha256(frozen_file)
  if(any(!is.finite(z$mse)) || any(!is.finite(z$q95))) stop('Invalid heldout scores')
  write.table(z,outcsv,append=!first,col.names=first,
              row.names=FALSE,sep=',',quote=TRUE)
  first<-FALSE
  rm(fit,models,z,learned,baselines);invisible(gc(verbose=FALSE))
  t2_b3_ram_guard('heldout',out,paste0('train_',train_seed))
  cat('V3_HELDOUT_SEED_PASS',family,'training',train_seed,
      'evaluation',seed,'n',n,'rows',nrow(z),'\n')
}
out_data<-read.csv(outcsv)
write.csv(aggregate(cbind(mse,q95)~model+training_seed,data=out_data,mean),
          file.path(out,'summary.csv'),row.names=FALSE)
cat('V3_HELDOUT_SHARD_PASS',family,seed,n,'\n')

# Publish canonical B3-named counterparts without breaking existing downstream references.
source('R/00_shared/t2_v3_b3_naming.R')
t2_b3_publish(out)
