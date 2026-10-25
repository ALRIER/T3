#!/usr/bin/env Rscript
# B3 Real World: independent external datasets; frozen Discovery weights only.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=3L)stop('Usage: FAMILY REALWORLD_SEED N')
family<-args[[1L]];seed<-as.integer(args[[2L]]);n<-as.integer(args[[3L]])
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
if(!family%in%t2_families()||!seed%in%t2_v3_indices('realworld')||
   !n%in%t2_v3_sample_sizes('realworld'))stop('B3 Real World role/seed/n mismatch')
Sys.setenv(T2_REALWORLD_SAMPLE_SIZES=as.character(n),T2_REALWORLD_REPS='500')
if(!file.exists(Sys.getenv('T2_REALWORLD_MANIFEST','config/public_datasets.csv')))
 stop('Reviewed external dataset manifest not available; fail closed')
out<-file.path('artifacts','realworld_v3',family,sprintf('seed%02d_n%d',seed,n))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
for(train_seed in t2_v3_indices('discovery')) {
  root<-file.path('artifacts','discovery_v3',family,sprintf('seed%02d',train_seed),sprintf('n%d',n))
  t3_stage_require(file.path(root,'stage_contract.rds'),
    'discovery',sprintf('b3_%s_n%d',family,n),family,train_seed,n)
  frozen<-file.path(root,'discovery.rds')
  if(!file.exists(frozen))stop('Missing frozen Discovery: ',frozen)
  fit<-t2_read_rds(frozen)
  if(length(fit$engines)!=4L||length(fit$models)!=30L)
    stop('Expected frozen 26 classical plus four primary optimization models')
  result<-t2_run_realworld_public(fit,mode='full',
      shard=sprintf('b3_realworld_%s_%d_%d_%d',family,seed,n,train_seed),
      seed_index=seed)
  result$scores$training_seed<-train_seed
  result$scores$realworld_seed<-seed
  result$scores$discovery_sha256<-t2_sha256(frozen)
  target<-file.path(out,sprintf('train_seed%02d_scores.csv',train_seed))
  if(file.exists(target))stop('Immutable Real World output already exists: ',target)
  write.csv(result$scores,target,row.names=FALSE)
  rm(fit,result);invisible(gc(verbose=FALSE))
}
t3_stage_publish('realworld',sprintf('b3_%s_n%d',family,n),
  list(score_files=sprintf('train_seed%02d_scores.csv',t2_v3_indices('discovery')),
       target='full_dataset_mean_proxy',seed_role='realworld'),
  family,seed,n,500L,file.path(out,'stage_contract.rds'))
cat('B3_REALWORLD_PASS',family,seed,n,'\\n')
