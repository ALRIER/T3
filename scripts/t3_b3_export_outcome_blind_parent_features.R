#!/usr/bin/env Rscript
# Generate outcome-blind parent covariates from original frozen child samples.
# This is NOT an estimator scoring/selection step. No Real World outcomes read.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=4L)stop('Usage: SOURCE_FAMILY BLOCK_ID FROZEN_PARENT_MANIFEST OUTPUT_CSV')
family<-args[[1L]];block<-args[[2L]];manifest<-args[[3L]];output<-args[[4L]]
if(!family%in%c('normal','lognormal','weibull','invgauss','exgaussian','exwald')||
   !grepl('^b[0-9]{2}$',block))stop('Invalid source parent block identity')
source('R/00_shared/load_all.R');t2_load('.')
tab<-read.csv(manifest,stringsAsFactors=FALSE,check.names=FALSE)
needed<-c('parent_dataset_id','dataset_id','training_family','parent_block_id',
 'processed_path','processed_sha256','source_path','source_sha256',
 'domain','family_assignment_confidence','family_assignment_status')
if(!all(needed%in%names(tab))||!nrow(tab)||
   any(tab$training_family!=family)||any(tab$parent_block_id!=block))
 stop('Outcome-blind frozen source manifest missing or altered')
if(anyDuplicated(tab[c('parent_dataset_id','dataset_id')]))stop('Duplicate frozen child')
root<-normalizePath(Sys.getenv('T3_REALWORLD_SOURCE_ROOT','.'),mustWork=TRUE)
resolve<-function(z){z<-as.character(z);if(startsWith(z,'/'))z else file.path(root,z)}
rows<-list()
for(i in seq_len(nrow(tab))) {
 r<-tab[i,,drop=FALSE]
 for(prefix in c('processed','source')) {
  file<-resolve(r[[paste0(prefix,'_path')]])
  if(!file.exists(file)||!identical(tolower(t2_sha256(file)),
     tolower(as.character(r[[paste0(prefix,'_sha256')]]))))
    stop('Frozen external file SHA256 mismatch: ',file)
 }
 x<-as.numeric(readRDS(resolve(r$processed_path)));x<-x[is.finite(x)]
 if(length(x)<150L)stop('Insufficient frozen child profile')
 avg<-mean(x);med<-stats::median(x);sd0<-stats::sd(x)
 m0<-stats::mad(x,constant=1);scale<-if(is.finite(m0)&&m0>0)m0 else
  stats::IQR(x,type=8)/1.349
 q<-stats::quantile(x,c(.05,.25,.50,.75,.95),type=8,names=FALSE)
 skew<-if(sd0>0)mean((x-avg)^3)/sd0^3 else 0
 kurt<-if(sd0>0)mean((x-avg)^4)/sd0^4-3 else 0
 outfrac<-if(scale>0)mean(abs(x-med)>3*scale) else 0
 tailratio<-if(q[[4]]>q[[2]])(q[[5]]-q[[3]])/(q[[4]]-q[[2]]) else NA_real_
 source_domain<-as.character(r$domain)
 conf<-as.numeric(r$family_assignment_confidence)
 if(!is.finite(conf)||conf<0||conf>1)stop('Invalid outcome-blind family confidence')
 rows[[i]]<-data.frame(parent_dataset_id=as.character(r$parent_dataset_id),
  sample_n=NA_integer_,source_family=family,data_source=source_domain,
  profile_fit_confidence=conf,
  empirical_family_assignment=if('empirical_family_assignment'%in%names(r))
    as.character(r$empirical_family_assignment) else NA_character_,
  family_assignment_status=as.character(r$family_assignment_status),
  family_assignment_margin=if('family_assignment_margin'%in%names(r))
    as.numeric(r$family_assignment_margin) else NA_real_,
  skewness=skew,kurtosis=kurt,
  coefficient_variation=if(avg!=0)sd0/abs(avg) else NA_real_,
  outlier_fraction=outfrac,positive_support_share=mean(x>0),
  tail_ratio=tailratio,
  median_mean_ratio=if(avg!=0)med/avg else NA_real_,
  child_dataset_id=as.character(r$dataset_id),raw_child_n=length(x),
  source_sha256=as.character(r$source_sha256),processed_sha256=as.character(r$processed_sha256),
  stringsAsFactors=FALSE)
}
d<-do.call(rbind,rows)
parents<-split(d,d$parent_dataset_id)
out<-list()
features<-c('skewness','kurtosis','coefficient_variation','outlier_fraction',
 'positive_support_share','tail_ratio','median_mean_ratio')
for(pid in names(parents)) {
 r<-parents[[pid]]
 if(length(unique(r$data_source))!=1L||length(unique(r$source_family))!=1L)
  stop('Parent source family/domain collision; cannot create outcome-blind descriptor')
 # Equal child weight prevents long child vectors from dominating the parent.
 f<-vapply(features,function(col) {
  v<-as.numeric(r[[col]]);if(all(!is.finite(v)))NA_real_ else mean(v[is.finite(v)])
 },numeric(1))
 for(n in c(200L,1000L,3000L)){
  z<-data.frame(parent_dataset_id=pid,sample_n=n,source_family=family,
   data_source=r$data_source[[1L]],profile_fit_confidence=min(r$profile_fit_confidence),
   stringsAsFactors=FALSE)
  for(j in seq_along(features))z[[features[[j]]]]<-f[[j]]
  z$empirical_family_assignment<-paste(sort(unique(r$empirical_family_assignment)),collapse=';')
  z$family_assignment_status<-paste(sort(unique(r$family_assignment_status)),collapse=';')
  z$family_assignment_margin<-if(all(!is.finite(r$family_assignment_margin)))NA_real_ else min(r$family_assignment_margin,na.rm=TRUE)
  z$independent_parent_child_count<-nrow(r)
  z$original_parent_block_id<-block
  z$original_profile_label_scope<-'frozen_outcome_blind'
  out[[length(out)+1L]]<-z
 }
}
dir.create(dirname(output),recursive=TRUE,showWarnings=FALSE)
write.csv(do.call(rbind,out),output,row.names=FALSE)
cat('T3_B3_FROZEN_OUTCOME_BLIND_PARENT_FEATURE_BLOCK_PASS',family,block,
    length(parents),length(out),'\n')
