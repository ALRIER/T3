#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=3L)stop('Usage: FAMILY HELDOUT_SEED N')
family<-args[[1L]];seed<-as.integer(args[[2L]]);n<-as.integer(args[[3L]])
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
source('R/00_shared/t2_v3_b3_resources.R')
if(!seed %in% t2_v3_indices('heldout') || !n %in% t2_v3_sample_sizes('heldout'))
  stop('Held-out reserved seed/sample-size contract violated')
t3_stage_preflight('heldout',family,seed,n,require_scenarios=TRUE)
root<-file.path('artifacts','discovery_v3')
out<-file.path('artifacts','heldout_v3',family,sprintf('seed%02d_n%d',seed,n))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
outcsv<-file.path(out,'scores.csv')
t2_b3_inputs_manifest(c(
  file.path(root,family,sprintf('seed%02d',0:9),sprintf('n%d',n),'discovery.rds'),
  file.path(t2_v3_block_dir('heldout',family,seed,n),sprintf('scenario_%04d.rds',0:320))
),out,'heldout')
t2_b3_ram_guard('heldout',out,'start')
first<-TRUE
control_first<-TRUE
controlcsv<-file.path(out,'non_evolutionary_control_scores.csv')
for(train_seed in 0:9) {
  frozen_file<-file.path(root,family,sprintf('seed%02d',train_seed),sprintf('n%d',n),'discovery.rds')
  if(!file.exists(frozen_file)) stop('Missing immutable discovery model: ',frozen_file)
  t3_stage_require(file.path(dirname(frozen_file),'stage_contract.rds'),
     'discovery',sprintf('b3_%s_n%d',family,n),family,train_seed,n)
  fit<-t2_read_rds(frozen_file)
  if(length(fit$engines)!=4L || length(fit$models)<8L)stop('Frozen training registry incomplete')
  baselines<-lapply(ESTIMATOR_NAMES,function(nm)new_frozen_model(nm,component=nm))
  learned<-Filter(function(m)!is.null(m$weights),fit$models)
  models<-c(baselines,learned)
  if(length(models)!=30L)stop('B3 requires all 26 benchmarks and four frozen learners')
  z<-t2_v3_stream_scores('heldout',family,seed,n,models,
                        reps=500L,selected=0:320)
  # Controls are fitted in Discovery only. Held-out never tunes their weights.
  controls<-fit$non_evolutionary_controls
  if(!is.list(controls)||!setequal(names(controls),c('convex_mse','local_deterministic')))
    stop('Missing two frozen non-evolutionary controls in Discovery artifact')
  control_models<-lapply(names(controls),function(name) {
    W<-controls[[name]]$weights
    if(!is.matrix(W)||nrow(W)!=26L||ncol(W)!=1L ||
       any(!is.finite(W))||any(W<0)||abs(sum(W)-1)>1e-8)
      stop('Invalid frozen control W')
    new_frozen_model(name,weights=as.numeric(W[,1L]),family=name)
  })
  cz<-t2_v3_stream_scores('heldout',family,seed,n,
       c(baselines,learned,control_models),reps=500L,selected=0:320)
  cz$training_seed<-train_seed
  cz$heldout_seed<-seed
  cz$discovery_sha256<-t2_sha256(frozen_file)
  if(nrow(cz)!=321L*32L||any(!is.finite(cz$mse))||any(!is.finite(cz$q95)))
    stop('Invalid 32-model heldout comparison')
  write.table(cz,controlcsv,append=!control_first,col.names=control_first,
              row.names=FALSE,sep=',',quote=TRUE)
  control_first<-FALSE
  rm(cz,control_models,controls)
  z$training_seed<-train_seed
  z$heldout_seed<-seed
  z$discovery_sha256<-t2_sha256(frozen_file)
  if(any(!is.finite(z$mse)) || any(!is.finite(z$q95))) stop('Invalid heldout scores')
  write.table(z,outcsv,append=!first,col.names=first,
              row.names=FALSE,sep=',',quote=TRUE)
  first<-FALSE
  rows_written<-nrow(z)
  rm(fit,models,z,learned,baselines);invisible(gc(verbose=FALSE))
  t2_b3_ram_guard('heldout',out,paste0('train_',train_seed))
  cat('V3_HELDOUT_SEED_PASS',family,'training',train_seed,
      'evaluation',seed,'n',n,'rows',rows_written,'\n')
}
out_data<-read.csv(outcsv)
write.csv(aggregate(cbind(mse,q95)~model+training_seed,data=out_data,mean),
          file.path(out,'summary.csv'),row.names=FALSE)
t3_stage_publish('heldout',sprintf('b3_%s_n%d',family,n),
 list(scores_path=outcsv,score_sha256=t2_sha256(outcsv),scenario_ids=0:320),
 family,seed,n,500L,file.path(out,'stage_contract.rds'),
 parents=sprintf('discovery__%s__%02d',family,t2_v3_indices('discovery')))
t3_stage_postflight(file.path(out,'stage_contract.rds'),'heldout',family,seed,n,expected_files=outcsv)
cat('V3_HELDOUT_SHARD_PASS',family,seed,n,'\n')

# Publish canonical B3-named counterparts without breaking existing downstream references.
source('R/00_shared/t2_v3_b3_naming.R')
t2_b3_publish(out)
