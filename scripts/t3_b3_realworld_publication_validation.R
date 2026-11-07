#!/usr/bin/env Rscript
# Real World paired sensitivity experiment; frozen Discovery W and frozen controls.
# One immutable source-family/parent-block/sample-size job, ten evaluation seeds.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=5L)stop('Usage: FAMILY BLOCK N FROZEN_MANIFEST DISCOVERY_BUNDLE_ROOT')
family<-args[[1L]];block<-args[[2L]];n<-as.integer(args[[3L]])
manifest<-args[[4L]];bundle<-args[[5L]]
if(!family%in%c('normal','lognormal','weibull','invgauss','exgaussian','exwald')||
   !n%in%c(200L,1000L,3000L))stop('Invalid source family/sample size')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R');source('R/00_shared/v3_inference.R')
source('R/00_shared/v3_scientific_adapter.R');source('R/00_shared/v3_downstream.R')
tab<-read.csv(manifest,stringsAsFactors=FALSE,check.names=FALSE)
required<-c('parent_dataset_id','dataset_id','training_family','parent_block_id',
            'processed_path','processed_sha256','source_path','source_sha256')
if(!all(required%in%names(tab))||!nrow(tab)||any(tab$training_family!=family)||
   any(tab$parent_block_id!=block))stop('Frozen family/block source manifest mismatch')
if(anyDuplicated(tab$dataset_id)||anyDuplicated(paste(tab$parent_dataset_id,tab$dataset_id)))
 stop('Duplicate child ID in parent block')
# Pilot evaluates one genuine frozen child, while production always includes every child.
pilot_limit<-as.integer(Sys.getenv('T3_RW_PUBLICATION_PILOT_CHILD_LIMIT','0'))
if(is.na(pilot_limit)||pilot_limit<0L)stop('Invalid pilot child limit')
if(pilot_limit>0L)tab<-tab[seq_len(min(nrow(tab),pilot_limit)),,drop=FALSE]
root<-normalizePath(Sys.getenv('T3_REALWORLD_SOURCE_ROOT','.'),mustWork=TRUE)
resolve<-function(p){p<-as.character(p);if(startsWith(p,'/'))p else file.path(root,p)}
for(i in seq_len(nrow(tab))) {
 for(pair in list(c('processed_path','processed_sha256'),c('source_path','source_sha256'))) {
  path<-resolve(tab[[pair[[1L]]]][i]);if(!file.exists(path)||
      t2_sha256(path)!=as.character(tab[[pair[[2L]]]][i]))stop('Source SHA check failed: ',path)
 }
}
# The controls were trained in Discovery and never reoptimized using Real World outcomes.
eval_seeds<-as.integer(strsplit(Sys.getenv('T3_RW_PUBLICATION_EVAL_SEEDS','30,31,32,33,34,35,36,37,38,39'),',',fixed=TRUE)[[1L]])
if(!length(eval_seeds)||anyNA(eval_seeds)||anyDuplicated(eval_seeds)||any(!eval_seeds%in%30:39))stop('Invalid Real World publication evaluation seed selection')
fits<-lapply(0:9,function(train) {
 path<-file.path(bundle,family,sprintf('seed%02d',train),sprintf('n%d',n),'discovery.rds')
 contract<-file.path(dirname(path),'stage_contract.rds')
 if(!file.exists(path)||!file.exists(contract))stop('Missing frozen Discovery model/contract: ',path)
 v<-readRDS(path)
 if(!is.list(v$non_evolutionary_controls)||
   !setequal(names(v$non_evolutionary_controls),c('convex_mse','local_deterministic')))
  stop('Discovery-frozen control registry incomplete')
 learned<-Filter(function(m)!is.null(m$weights),v$models)
 if(length(learned)!=4L)stop('Expected four original frozen evolutionary candidates')
 for(k in seq_along(learned)) {
  w<-as.numeric(learned[[k]]$weights)
  if(length(w)!=26L||any(!is.finite(w)))stop('Invalid frozen evolutionary weight vector')
  learned[[k]]$id<-paste0(family,'_',learned[[k]]$id,'_train',sprintf('%02d',train))
 }
 controls<-lapply(names(v$non_evolutionary_controls),function(id) {
  w<-as.matrix(v$non_evolutionary_controls[[id]]$weights)
  if(nrow(w)!=26L||ncol(w)!=1L||any(!is.finite(w))||
     any(w< -1e-10)||abs(sum(w)-1)>1e-8)stop('Invalid Discovery-frozen control weights')
  new_frozen_model(paste0(family,'_',id,'_train',sprintf('%02d',train)),
                   weights=as.numeric(w[,1L]),family=id)
 })
 list(models=c(list(new_frozen_model('mean',component='mean')),learned,controls),
      discovery_sha256=t2_sha256(path))
})
outdir<-file.path('artifacts','rw_pub_validation',family,paste0(block,'_n',n))
dir.create(outdir,recursive=TRUE,showWarnings=FALSE)
outfile<-file.path(outdir,'replicate_sensitivity.csv.gz')
if(file.exists(outfile))stop('Immutable output already exists')
# Store parent-level sums in memory; avoid hundreds of millions of raw rows.
# Each child receives equal total weight, each eligible depth equal within child;
# split-fold means are also averaged within child. No pseudo-independent draws.
acc<-new.env(hash=TRUE,parent=emptyenv())
child_stats<-list()
rows_written<-0L
for(i in seq_len(nrow(tab))) {
 row<-tab[i,,drop=FALSE]
 x<-as.numeric(readRDS(resolve(row$processed_path)))
 x<-x[is.finite(x)]
 if(length(x)<150L)stop('Frozen parent child vector too small')
  sd0<-stats::sd(x);med0<-stats::median(x);scale0<-stats::mad(x,constant=1)
  skew0<-if(sd0>0)mean((x-mean(x))^3)/sd0^3 else 0
  out0<-if(scale0>0)mean(abs(x-med0)>3*scale0) else 0
  child_stats[[length(child_stats)+1L]]<-data.frame(
    parent_dataset_id=as.character(row$parent_dataset_id),dataset_id=as.character(row$dataset_id),
    sample_size=length(x),skewness=skew0,outlier_fraction=out0,
    coefficient_variation=if(mean(x)!=0)sd0/abs(mean(x)) else NA_real_,
    source_family=family,stringsAsFactors=FALSE)
 quant<-stats::quantile(x,c(.10,.75,.90),type=8,names=FALSE)
 depths<-list(full=x,body_10_90=x[x>=quant[1L]&x<=quant[3L]])
 upper<-x[x>=quant[2L]];if(length(upper)>=150L)depths$upper_tail<-upper
 depths<-depths[vapply(depths,length,integer(1))>=150L]
 for(depth in names(depths)) {
  xx<-depths[[depth]]
  for(eval_seed in eval_seeds) {
   # Two deterministic disjoint split-halves; all candidate W evaluated on SAME draws.
   # Targets are empirical reference means, not unknown population truth.
   split_seed<-t2_seed(paste('T3_RW_PUBLICATION_SPLIT',family,eval_seed,
                    row$parent_dataset_id,row$dataset_id,depth,n),88511L)
   set.seed(split_seed);perm<-sample.int(length(xx))
   h<-floor(length(xx)/2)
   for(fold in 1:2) {
    estimate<-xx[perm[if(fold==1L)seq_len(h) else (h+1L):length(xx)]]
    reference<-xx[perm[if(fold==1L)(h+1L):length(xx) else seq_len(h)]]
    if(length(estimate)<50L||length(reference)<50L)stop('Insufficient disjoint reference folds')
    eval_draw_seed<-t2_seed(paste('T3_RW_PUB_DRAW',family,eval_seed,
                     row$parent_dataset_id,row$dataset_id,depth,n,fold),88512L)
    set.seed(eval_draw_seed)
    T<-matrix(NA_real_,500L,26L,dimnames=list(NULL,ESTIMATOR_NAMES))
    for(b in seq_len(500L))T[b,]<-component_vector(sample(estimate,n,replace=TRUE))
    if(any(!is.finite(T)))stop('Nonfinite component vector')
    # Full-sample reference can share information with sampling pool; report separately.
    target_values<-c(holdout_half_mean=mean(reference),full_sample_mean=mean(xx))
    for(tg in names(target_values)) {
     target<-unname(target_values[[tg]])
     for(train in 0:9) {
      z<-score_model_set(T,fits[[train+1L]]$models,target)
      if(!all(c('model','mse','q95')%in%names(z))||nrow(z)!=7L)
       stop('Seven frozen models (mean, four engines, two controls) expected')
      for(k in seq_len(nrow(z))) {
       model<-as.character(z$model[k])
       cls<-if(model=='mean')'mean' else if(grepl('convex_mse|local_deterministic',model))'non_evolutionary' else 'evolutionary'
       key<-paste(row$parent_dataset_id,train,eval_seed,tg,model,sep='|')
       weight<-1/(2*length(depths))
       if(!exists(key,envir=acc,inherits=FALSE)) {
        assign(key,list(pid=as.character(row$parent_dataset_id),train=train,
          ev=eval_seed,ref=tg,model=model,cls=cls,
          sha=fits[[train+1L]]$discovery_sha256,
          mse=0,q95=0,weight=0,children=0),envir=acc)
       }
       a<-get(key,envir=acc,inherits=FALSE)
       a$mse<-a$mse+as.numeric(z$mse[k])*weight
       a$q95<-a$q95+as.numeric(z$q95[k])*weight
       a$weight<-a$weight+weight
       assign(key,a,envir=acc)
       rows_written<-rows_written+1L
      }
     }
    }
    rm(T);invisible(gc(FALSE))
   }
  }
 }
 cat('RW_PUBLICATION_PARENT_CHILD_COMPLETE',family,block,n,i,nrow(tab),'\n')
}
if(rows_written==0L)stop('No supplementary scoring produced')
keys<-ls(acc,all.names=TRUE)
con<-gzfile(outfile,'wt')
writeLines('source_family,parent_dataset_id,block_id,sample_n,training_seed,realworld_seed,reference_policy,model,model_class,discovery_sha256,mse,q95,n_child_depth_fold_scores',con)
for(key in keys) {
 a<-get(key,envir=acc,inherits=FALSE)
 if(a$weight<=0)stop('Nonpositive parent aggregation weight')
 v<-c(family,a$pid,block,n,a$train,a$ev,a$ref,a$model,a$cls,a$sha,
      signif(a$mse/a$weight,16),signif(a$q95/a$weight,16),signif(a$weight,8))
 if(any(grepl(',',v,fixed=TRUE)))stop('Invalid metadata comma')
 writeLines(paste(v,collapse=','),con)
}
close(con)
write.csv(do.call(rbind,child_stats),file.path(outdir,'frozen_child_characteristics.csv'),row.names=FALSE)
manifest_out<-list(protocol='T3_B3_REALWORLD_PUBLICATION_VALIDATION_V1',
 source_family=family,block_id=block,sample_n=n,original_discovery_seeds=0:9,
 evaluation_seeds=eval_seeds,models_per_fit=7L,replications=500L,
 full_raw_parent_child_source_sha256=t2_sha256(manifest),
 sensitivity_output_sha256=t2_sha256(outfile),component_score_records=rows_written,
 aggregated_parent_model_rows=length(keys),
 independence='parent_dataset_id',target_truth_known=FALSE,
 training_on_RealWorld=FALSE)
jsonlite::write_json(manifest_out,file.path(outdir,'validation_manifest.json'),auto_unbox=TRUE,pretty=TRUE)
cat('RW_PUBLICATION_CONTROLS_AND_SPLIT_TARGETS_PASS',family,block,n,rows_written,'\n')
