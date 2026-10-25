#!/usr/bin/env Rscript
# Prueba T2 Version 3 B3: external scoring on immutable, independently
# catalogued datasets. Explicitly proxy-estimand (complete-series mean).
a<-commandArgs(trailingOnly=TRUE)
if(length(a)<2L)stop('Usage: PROFILE_BATCH_DIRECTORY FAMILY [smoke]')
batchdir<-a[[1L]];family<-a[[2L]]
smoke<-length(a)>2L&&identical(a[[3L]],'smoke')
if(!family%in%c('normal','lognormal','weibull','invgauss','exgaussian','exwald'))stop('Invalid family')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_inference.R')
source('R/00_shared/t2_v3_b3_resources.R')
# Reuse the depth definitions from the earlier Real World protocol.
rw_depths <- function(x) {
  q<-stats::quantile(x,c(.1,.75,.9),type=8,names=FALSE)
  out<-list(full=x,body_10_90=x[x>=q[1L]&x<=q[3L]])
  tail<-x[x>=q[2L]]
  if(length(tail)>=150L)out$upper_tail<-tail
  out[vapply(out,length,integer(1))>=150L]
}
rw_proximity <- function(f,p) {
  direct<-switch(f,normal=p=='normal_like',lognormal=p=='lognormal_like',
    weibull=p=='weibull_like',invgauss=p%in%c('lognormal_like','weibull_like'),
    exgaussian=p%in%c('normal_like','lognormal_like'),
    exwald=p%in%c('lognormal_like','weibull_like'))
  near<-switch(f,normal=p=='empirical_unknown',lognormal=p=='weibull_like',
    weibull=p=='lognormal_like',invgauss=p=='empirical_unknown',
    exgaussian=p%in%c('weibull_like','empirical_unknown'),
    exwald=p=='empirical_unknown')
  if(isTRUE(direct))'direct_intraregime' else if(isTRUE(near))'near_intrfamily' else 'crossfamily_transfer'
}
if(!dir.exists(batchdir))stop('Missing audited batch: ',batchdir)
profile<-read.csv(file.path(batchdir,'profiles.csv'),stringsAsFactors=FALSE)
profile<-profile[profile$load_ok %in% TRUE,,drop=FALSE]
if(smoke) profile<-head(profile,1L)
# Enforce outcome-blind frozen parent registry for production B3.
if(!smoke){
 frozen<-Sys.getenv('T2_B3_RW_PARENT_MANIFEST','artifacts/T2_V3_B3_realworld_freeze/frozen_parent_family_manifest_T2_V3_B3.csv')
 if(!file.exists(frozen))stop('B3 frozen parent manifest missing; scoring forbidden')
 parent_manifest<-read.csv(frozen,stringsAsFactors=FALSE)
 allowed<-parent_manifest[parent_manifest$family==family,,drop=FALSE]
 if(!nrow(allowed)||anyDuplicated(allowed$parent_dataset_id))
   stop('B3 newly selected parent family registry invalid')
 # Score only new parents selected and frozen before any model scoring.
 profile<-profile[profile$parent_dataset_id %in% allowed$parent_dataset_id,,drop=FALSE]
 actual<-profile$parent_dataset_id
 if(any(vapply(seq_along(actual),function(i){
   z<-allowed[allowed$parent_dataset_id==actual[i],,drop=FALSE]
   !identical(as.character(z$source_hash[1L]),as.character(profile$raw_sha256[i]))
 },logical(1)))) stop('Frozen provenance mismatch')
}

if(!nrow(profile)){
 dir.create(file.path('artifacts','realworld_T2_V3_B3',family,basename(batchdir)),recursive=TRUE,showWarnings=FALSE)
 writeLines('NO_ELIGIBLE_B3_PARENTS',file.path('artifacts','realworld_T2_V3_B3',family,basename(batchdir),'excluded_batch_T2_V3_B3.txt'))
 quit(save='no',status=0L)
}
root<-file.path('artifacts','realworld_T2_V3_B3',family,basename(batchdir))
dir.create(root,recursive=TRUE,showWarnings=FALSE)
outfile<-file.path(root,'scores_T2_V3_B3.csv')
inferfile<-file.path(root,'paired_inference_T2_V3_B3.csv')
if(file.exists(outfile))file.remove(outfile)
if(file.exists(inferfile))file.remove(inferfile)
nullfile<-file.path(root,'null_calibration_T2_V3_B3.csv')
if(file.exists(nullfile))file.remove(nullfile)
null_rows<-0L
rows<-0L
train_seeds<-if(smoke)0L else 0:9
# Cache four frozen W candidates once per family worker.
candidate_cache<-new.env(parent=emptyenv())
t2_b3_inputs_manifest(c(
 file.path(batchdir,'profiles.csv'),
 file.path(batchdir,'raw',paste0(profile$dataset_id,'.rds')),
 file.path('artifacts/discovery_v3',family,sprintf('seed%02d',train_seeds),'discovery.rds')
),root,'realworld')
t2_b3_ram_guard('realworld',root,'start')
for(j in seq_len(nrow(profile))) {
  id<-profile$dataset_id[j]
  raw<-file.path(batchdir,'raw',paste0(id,'.rds'))
  if(!file.exists(raw))stop('Missing audited raw: ',id)
  if(!identical(unname(tools::md5sum(raw)),profile$raw_sha256[j]))stop('Raw audit fingerprint mismatch: ',id)
  x<-readRDS(raw);x<-as.numeric(x);x<-x[is.finite(x)]
  if(length(x)<150L)stop('Insufficient parent observations: ',id)
  bench<-if(profile$empirical_profile[j]=='normal_like')'mean' else
    if(profile$empirical_profile[j]=='empirical_unknown')'huber' else 'trimmed20'
  depths<-rw_depths(x)
  for(depth in names(depths)) {
  xx<-depths[[depth]]
  for(n in if(smoke)200L else c(200L,1000L)) {
    # Number of bootstrap children per parent/depth/sample-size; frozen by run env.
    R<-if(smoke)100L else as.integer(Sys.getenv('T2_B3_RW_CHILD_REPS','500'))
    if(!is.finite(R)||R<100L||R>10000L)stop('Children must be in [100,10000]')
    set.seed(t2_seed(paste('B3',family,id,depth,n),18517L))
    T<-matrix(NA_real_,R,26L,dimnames=list(NULL,ESTIMATOR_NAMES))
    for(i in seq_len(R))T[i,]<-component_vector(sample(xx,n,replace=TRUE))
    if(any(!is.finite(T)))stop('Invalid component scores')
    sc<-list(T=T,target=mean(xx),scenario_id=j)
    baselines<-lapply(ESTIMATOR_NAMES,function(nm)new_frozen_model(nm,component=nm))
    for(k in train_seeds) {
      p<-file.path('artifacts','discovery_v3',family,sprintf('seed%02d',k),'discovery.rds')
      if(!file.exists(p))stop('Missing frozen Discovery model: ',p)
      cache_key<-as.character(k)
      if(!exists(cache_key,envir=candidate_cache,inherits=FALSE)){
       fit<-readRDS(p)
       if(length(fit$engines)!=4L)stop('Invalid frozen engines')
       assign(cache_key,Filter(function(m)!is.null(m$weights),fit$models),envir=candidate_cache)
       rm(fit)
      }
      candidates<-get(cache_key,envir=candidate_cache,inherits=FALSE)
      models<-c(baselines,candidates)
      if(anyDuplicated(vapply(models,function(m)m$id,character(1))))stop('Duplicate candidates')
      z<-score_model_set(T,models,mean(xx))
      z$dataset_id<-id;z$parent_dataset_id<-profile$parent_dataset_id[j]
      z$family<-family;z$training_seed<-k;z$sample_n<-n
      z$child_bootstrap_reps<-R;z$depth<-depth;z$target_type<-'depth_parent_empirical_mean_proxy'
      z$domain<-profile$domain[j];z$source_url<-profile$source_url[j]
      z$empirical_profile<-profile$empirical_profile[j]
      z$proximity_layer<-rw_proximity(family,profile$empirical_profile[j])
      if(!smoke){
       fr<-allowed[allowed$parent_dataset_id==profile$parent_dataset_id[j],,drop=FALSE]
       z$mad_band_proxy<-fr$mad_band_proxy[1L]
       z$contamination_band_proxy<-fr$contamination_band_proxy[1L]
       z$synthetic_regime_match<-fr$synthetic_regime_match[1L]
      }
      z$raw_md5<-profile$raw_sha256[j];z$weights_sha256<-t2_sha256(p)
      write.table(z,outfile,sep=',',append=rows>0L,col.names=rows==0L,row.names=FALSE)
      set.seed(t2_seed(paste('B3_infer',family,id,depth,n,k),19000L))
      inf<-t2_v3_infer_scenario(sc,models,k,j,n,B=if(smoke)50L else 500L,reference=bench)
      inf$dataset_id<-id;inf$family<-family;inf$depth<-depth
      inf$child_bootstrap_reps<-R
      inf$parent_dataset_id<-profile$parent_dataset_id[j]
      inf$proximity_layer<-rw_proximity(family,profile$empirical_profile[j])
      if(!smoke){
       inf$mad_band_proxy<-fr$mad_band_proxy[1L]
       inf$contamination_band_proxy<-fr$contamination_band_proxy[1L]
       inf$synthetic_regime_match<-fr$synthetic_regime_match[1L]
      }
      inf$target_type<-'depth_parent_empirical_mean_proxy'
      write.table(inf,inferfile,sep=',',append=rows>0L,col.names=rows==0L,row.names=FALSE)
      if(k==0L&&depth=='full') {
        set.seed(t2_seed(paste('B3_null',family,id,n),19400L))
        nul<-t2_v3_null_fpr(sc,models,k,j,Bnull=if(smoke)30L else 200L,reference=bench)
        nul$dataset_id<-id;nul$family<-family;nul$depth<-depth
        nul$null_scope<-'paired_exchangeability_only'
        write.table(nul,nullfile,sep=',',append=null_rows>0L,col.names=null_rows==0L,row.names=FALSE)
        null_rows<-null_rows+1L;rm(nul)
      }
      rows<-rows+1L;rm(z,inf,models,candidates)
    }
    rm(T,sc,baselines);invisible(gc(verbose=FALSE))
    t2_b3_ram_guard('realworld',root,paste0(j,'_',depth,'_',n))
  }
  }
  rm(depths,x);invisible(gc(verbose=FALSE))
}
writeLines(c('Prueba T2 version 3 B3',
             'Full, body 10-90 and upper-tail subsets retain separate empirical mean proxies',
             sprintf('Bootstrap children per parent/depth/N: %s',if(smoke)100L else Sys.getenv('T2_B3_RW_CHILD_REPS','500')),
             'Repeated samples from the same parent dataset are dependent',
             'Real-world false-positive rate is not identifiable without a valid null-generating mechanism',
             'Per-dataset paired intervals are descriptive; parent-level confirmatory aggregation is separate',
             'Original raw fingerprint and frozen Discovery weights were checked'),
           file.path(root,'scientific_scope_T2_V3_B3.txt'))
source('R/00_shared/t2_v3_b3_naming.R')
# Already suffixed output names are preserved, no rewriting of original raw artifacts.
cat('T2_V3_B3_REALWORLD_SCORING_PASS',family,basename(batchdir),rows,'comparisons\n')
