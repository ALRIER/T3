#!/usr/bin/env Rscript
a<-commandArgs(trailingOnly=TRUE)
if(length(a)<4L)stop('Usage: heldout|stress FAMILY SEED N [smoke]')
role<-a[[1]];fam<-a[[2]];seed<-as.integer(a[[3]]);n<-as.integer(a[[4]])
smoke<-length(a)>=5L&&identical(a[[5]],'smoke')
if(!role%in%c('heldout','stress'))stop('Invalid role')
if(!seed%in%if(role=='heldout')10:14 else 15:19)stop('Illegal evaluation seed')
if(!n%in%c(200L,1000L,3000L))stop('Illegal sample size')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
source('R/00_shared/v3_inference.R')
source('R/00_shared/t2_v3_b3_resources.R')
out<-file.path('artifacts','v3_confirmatory_inference',role,fam,sprintf('seed%02d_n%d',seed,n))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
t2_b3_inputs_manifest(c(
 file.path('artifacts/discovery_v3',fam,sprintf('seed%02d',if(smoke)0L else 0:9),'discovery.rds'),
 file.path(t2_v3_block_dir(role,fam,seed,n),sprintf('scenario_%04d.rds',if(smoke)c(0L,1L,120L) else 0:120))
),out,role)
t2_b3_ram_guard(role,out,'start')
# Stream each scenario directly to persistent storage; do not retain the
# 121 x 10 inference result tables or scientific matrices in memory.
scores_file<-file.path(out,'paired_inference.csv')
null_file<-file.path(out,'null_calibration.csv')
if(file.exists(scores_file))file.remove(scores_file)
if(file.exists(null_file))file.remove(null_file)
count<-0L
for(training_seed in if(smoke)0L else 0:9){
  p<-file.path('artifacts/discovery_v3',fam,sprintf('seed%02d',training_seed),'discovery.rds')
  if(!file.exists(p))stop('Missing frozen Discovery: ',p)
  fit<-readRDS(p);if(length(fit$engines)!=4L)stop('Incomplete engines')
  baselines<-lapply(ESTIMATOR_NAMES,function(nm)new_frozen_model(nm,component=nm))
  learned<-Filter(function(m)!is.null(m$weights),fit$models)
  models<-c(baselines,learned)
  if(length(models)!=30L || anyDuplicated(vapply(models,function(m)m$id,character(1))))
    stop('T2 V3 B3 requires 26 benchmarks plus four frozen candidates')
  discovery_hash<-t2_sha256(p)
  for(id in if(smoke)c(0L,1L,120L) else 0:120){
    sc<-t2_v3_read_scenario(role,fam,seed,n,id)
    set.seed(t2_seed(paste(role,fam,seed,n,training_seed,id),9001L))
    z<-t2_v3_infer_scenario(sc,models,training_seed,seed,n,B=if(smoke)50L else as.integer(ga_config$bootstrap_B),reference='mean')
    z$role<-role;z$family<-fam;z$discovery_sha256<-discovery_hash
    stopifnot(all(is.finite(z$ci_lower)),all(is.finite(z$ci_upper)))
    write.table(z,scores_file,sep=',',append=count>0L,col.names=count==0L,row.names=FALSE)
    count<-count+1L
    if(id==0L){
      null<-t2_v3_null_fpr(sc,models,training_seed,seed,
         Bnull=if(smoke)30L else as.integer(ga_config$bootstrap_B),reference='mean')
      null$role<-role;null$family<-fam
      write.table(null,null_file,sep=',',append=training_seed>0L,col.names=training_seed==0L,row.names=FALSE)
      rm(null)
    }
    rm(sc,z)
    if(id%%20L==0L)invisible(gc(verbose=FALSE))
  }
  rm(fit,models,learned,baselines);invisible(gc(verbose=FALSE))
  t2_b3_ram_guard(role,out,paste0('training_',training_seed))
}
# Holm adjustment applies to the complete prespecified shard family, after
# streaming all candidate/scenario tests. No large Monte Carlo arrays reloaded.
z<-read.csv(scores_file)
z<-t2_v3_adjust_inference(z)
key<-paste(z$model,z$training_seed,z$scenario_id,sep=':')
m<-z$metric=='mse';q<-z$metric=='q95'
mse_ok<-z$confirmed_mse_gain[match(key,paste(z$model[m],z$training_seed[m],z$scenario_id[m],sep=':'))]
q95_ok<-z$confirmed_q95_gain[match(key,paste(z$model[q],z$training_seed[q],z$scenario_id[q],sep=':'))]
if(anyNA(mse_ok)||anyNA(q95_ok))stop('B3 taxonomy matching failed')
z$taxonomy<-ifelse(mse_ok&q95_ok,'mse_and_q95_bh_fdr',
 ifelse(mse_ok,'mse_only_bh_fdr',
 ifelse(q95_ok,'q95_only_bh_fdr','no_supported_gain')))
write.csv(z,file.path(out,'adjusted_inference.csv'),row.names=FALSE)
stopifnot(all(c('mse','q95')%in%z$metric),file.exists(null_file))
rm(z);invisible(gc(verbose=FALSE))
writeLines(c(sprintf('role=%s',role),sprintf('family=%s',fam),
 sprintf('evaluation_seed=%d',seed),sprintf('sample_n=%d',n),
 'B3_streaming=true','bootstrap=paired','reference=mean_predeclared','null=paired_random_swap',
 'q95_inference=bootstrap_normal_BH_and_Holm_sensitivity',
 'FPR_scope=diagnostic_not_procedure_wide'),file.path(out,'protocol.txt'))
cat('T2_V3_B3_INFERENCE_STREAM_PASS',role,fam,seed,n,count,'scenarios\\n')

# Publish canonical B3-named counterparts without breaking existing downstream references.
source('R/00_shared/t2_v3_b3_naming.R')
t2_b3_publish(out)
