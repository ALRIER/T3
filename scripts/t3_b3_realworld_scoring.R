#!/usr/bin/env Rscript
# Score a frozen parent/child sample with discovery W only; no refitting/tuning.
a<-commandArgs(TRUE)
if(!(length(a)%in%c(4L,5L)))stop('Usage: TRAINING_FAMILY REALWORLD_SEED N FROZEN_PARENT_CHILD_MANIFEST [TRAINING_SEEDS_COMMA_SEPARATED]')
family<-a[1L];eval_seed<-as.integer(a[2L]);n<-as.integer(a[3L]);manifest_path<-a[4L]
training_seed_arg<-if(length(a)==5L)strsplit(a[5L],',',fixed=TRUE)[[1L]] else NULL
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R');source('R/00_shared/v3_inference.R')
source('R/00_shared/v3_scientific_adapter.R');source('R/00_shared/v3_downstream.R')
training_seeds<-if(is.null(training_seed_arg))t2_v3_indices('discovery') else as.integer(training_seed_arg)
if(!length(training_seeds)||anyNA(training_seeds)||anyDuplicated(training_seeds)||
   any(!training_seeds%in%t2_v3_indices('discovery')))stop('Invalid frozen Discovery training-seed shard')
if(!family%in%t2_families()||!eval_seed%in%t2_v3_indices('realworld')||
   !n%in%t2_v3_sample_sizes('realworld'))stop('Invalid Real-world family/seed/n')
if(!file.exists(manifest_path))stop('Frozen parent-child manifest missing')
tab<-read.csv(manifest_path,stringsAsFactors=FALSE,check.names=FALSE)
required<-c('parent_dataset_id','dataset_id','training_family','transfer_scope',
 'matched_scenario_id','processed_path','processed_sha256','profile_sha256',
 'source_path','source_sha256','license_review_status','license_name','license_url','catalog_commit',
 'upstream_license_status','upstream_source_url','source_archive_doi',
 'license_evidence','license_evidence_sha256','license_evidence_path',
 'source_group',
 'license_basis',
 'child_selection_rule','variable','n',
 'empirical_profile','domain','source_url')
if(!all(required%in%names(tab)))stop('Frozen parent-child schema incomplete')
if(any(tolower(tab$license_review_status)!='verified'))stop('Real-world scoring requires individually verified source licenses')
if(any(!grepl('^https://[^/]+',tab$source_url))||any(!grepl('^https://[^/]+',tab$license_url))||
   any(!grepl('^[[:xdigit:]]{40,64}$',tab$catalog_commit)))
 stop('Frozen source/license URL or catalog revision is invalid')
source_root<-normalizePath(Sys.getenv('T3_REALWORLD_SOURCE_ROOT','.'),mustWork=TRUE)
resolve_catalog_path<-function(p){p<-as.character(p);if(startsWith(p,'/'))p else file.path(source_root,p)}
for(i in seq_len(nrow(tab))){
 evidence<-resolve_catalog_path(tab$license_evidence_path[i])
 if(!file.exists(evidence)||!identical(tolower(t2_sha256(evidence)),tolower(tab$license_evidence_sha256[i])))
  stop('License evidence snapshot missing or changed for ',tab$dataset_id[i])
}
tab<-tab[tab$training_family==family,,drop=FALSE]
if(!nrow(tab))stop('No frozen parent-child profile for source family ',family)
if(anyDuplicated(tab[c('parent_dataset_id','dataset_id')]))stop('Duplicate parent-child frozen identity')
if(length(unique(tab$parent_dataset_id))<5L)stop('Too few independent parents for this family')
block_id<-Sys.getenv('T3_REALWORLD_BLOCK_ID','')
if(nzchar(block_id)) {
 if(!'parent_block_id'%in%names(tab)||any(tab$parent_block_id!=block_id))
  stop('Parent block ID does not match the frozen input bundle')
 if(!all(c('empirical_family_assignment','family_assignment_confidence',
           'family_assignment_status','empirical_family_relation')%in%names(tab)))
  stop('Outcome-blind empirical family proximity labels are missing')
}
shard_suffix<-if(nzchar(block_id))paste0('_',block_id) else
 if(length(a)==5L)paste0('_trainseeds_',paste(training_seeds,collapse='_')) else ''
out<-file.path('artifacts','realworld_T3_B3',family,paste0(sprintf('seed%02d_n%d',eval_seed,n),shard_suffix))
dir.create(file.path(out,'raw'),recursive=TRUE,showWarnings=FALSE)
score_path<-file.path(out,'scores.csv')
if(file.exists(score_path))stop('Refusing to overwrite immutable real-world shard')
baselines<-lapply(ESTIMATOR_NAMES,function(nm)new_frozen_model(nm,component=nm))
first<-TRUE
for(j in seq_len(nrow(tab))) {
 row<-tab[j,,drop=FALSE];vector_path<-resolve_catalog_path(row$processed_path)
 if(!file.exists(vector_path)||!identical(t2_sha256(vector_path),as.character(row$processed_sha256)))
  stop('Frozen child vector hash mismatch: ',vector_path)
 source_path<-resolve_catalog_path(row$source_path)
 if(!file.exists(source_path)||!identical(t2_sha256(source_path),as.character(row$source_sha256)))
  stop('Original source hash mismatch: ',source_path)
 x<-as.numeric(readRDS(vector_path));x<-x[is.finite(x)]
 if(length(x)<150L)stop('Frozen child has insufficient observations: ',row$dataset_id)
 profile_key<-paste(row$parent_dataset_id,row$dataset_id,as.integer(row$n),
   format({s<-stats::sd(x);if(s>0)mean((x-mean(x))^3)/s^3 else 0},digits=17),
   format({s<-stats::sd(x);if(s>0)mean((x-mean(x))^4)/s^4-3 else 0},digits=17),
   if(all(x>0))'strictly_positive' else 'contains_nonpositive',
   format({s<-stats::sd(x);med<-stats::median(x);m<-stats::mad(x,constant=1);
     scale<-if(is.finite(m)&&m>0)m else stats::IQR(x,type=8)/1.349;
     if(is.finite(scale)&&scale>0)mean(abs(x-med)>3*scale) else 0},digits=17),sep='|')
 profile_tmp<-tempfile();writeBin(charToRaw(profile_key),profile_tmp)
 profile_actual<-t2_sha256(profile_tmp);unlink(profile_tmp)
 if(!identical(profile_actual,as.character(row$profile_sha256)))stop('Frozen profile fingerprint mismatch: ',row$dataset_id)
 quant<-stats::quantile(x,c(.10,.75,.90),type=8,names=FALSE)
 depths<-list(full=x,body_10_90=x[x>=quant[1L]&x<=quant[3L]])
 upper<-x[x>=quant[2L]];if(length(upper)>=150L)depths$upper_tail<-upper
 depths<-depths[vapply(depths,length,integer(1))>=150L]
 for(depth in names(depths)) {
  xx<-depths[[depth]];R<-500L
  seed<-t2_seed(paste('T3_REALWORLD',family,eval_seed,row$parent_dataset_id,
                      row$dataset_id,depth,n),59117L)
  set.seed(seed);T<-matrix(NA_real_,R,26L,dimnames=list(NULL,ESTIMATOR_NAMES))
  for(b in seq_len(R))T[b,]<-component_vector(sample(xx,n,replace=TRUE))
  if(any(!is.finite(T)))stop('Nonfinite estimator component in child ',row$dataset_id)
  for(training_seed in training_seeds) {
   d<-file.path('artifacts','discovery_v3',family,sprintf('seed%02d',training_seed),sprintf('n%d',n))
   frozen<-file.path(d,'discovery.rds')
   if(!file.exists(frozen))stop('Missing frozen Discovery W: ',frozen)
   cpath<-file.path(d,'stage_contract.rds')
   contract<-t3_stage_require(cpath,'discovery',sprintf('b3_%s_n%d',family,n),family,training_seed,n)
   if(!identical(contract$payload$model_sha256,t2_sha256(frozen)))stop('Discovery W provenance mismatch')
   fit<-readRDS(frozen);learned<-Filter(function(m)!is.null(m$weights),fit$models)
   if(length(learned)!=4L)stop('Expected four frozen Discovery engines')
   for(k in seq_along(learned))learned[[k]]$id<-paste0(family,'_',learned[[k]]$id,'_train',sprintf('%02d',training_seed))
   models<-c(baselines,learned)
   z<-score_model_set(T,models,mean(xx))
   z$dataset_id<-row$dataset_id;z$parent_dataset_id<-row$parent_dataset_id
  z$family<-family;z$training_family<-family;z$source_family<-family
  z$evaluation_family<-if('empirical_family_assignment'%in%names(row))
    as.character(row$empirical_family_assignment) else family
  z$evaluation_profile<-row$empirical_profile
   z$domain<-row$domain;z$source_url<-row$source_url
   z$license_name<-row$license_name;z$license_url<-row$license_url
   z$upstream_license_status<-row$upstream_license_status
   z$upstream_source_url<-row$upstream_source_url
   z$source_archive_doi<-row$source_archive_doi
   z$license_evidence<-row$license_evidence
   z$license_evidence_sha256<-row$license_evidence_sha256
   z$license_evidence_path<-row$license_evidence_path
   z$source_group<-row$source_group
   z$license_basis<-row$license_basis
   z$child_selection_rule<-row$child_selection_rule
   z$variable<-row$variable
   z$transfer_scope<-row$transfer_scope;z$matched_scenario_id<-row$matched_scenario_id
  for(nm in c('empirical_family_assignment','family_assignment_runner_up',
      'family_assignment_confidence','family_assignment_margin',
      'family_assignment_compatible_set','family_assignment_status',
      'family_assignment_method','family_assignment_bootstrap_B',
      'family_assignment_seed','empirical_family_relation','family_assignment_scope'))
   if(nm%in%names(row))z[[nm]]<-row[[nm]]
   z$depth<-depth;z$sample_n<-n;z$training_seed<-training_seed;z$realworld_seed<-eval_seed
   z$parent_cluster_unit<-'parent_dataset_id';z$target_type<-'evaluated_child_depth_mean_proxy'
   z$source_sha256<-row$source_sha256;z$processed_sha256<-row$processed_sha256
   z$profile_sha256<-row$profile_sha256;z$discovery_sha256<-t2_sha256(frozen)
   write.table(z,score_path,sep=',',append=!first,col.names=first,row.names=FALSE,quote=TRUE)
   first<-FALSE;rm(fit,learned,models,z);invisible(gc(FALSE))
  }
  rm(T);invisible(gc(FALSE))
 }
 cat('T3_REALWORLD_PARENT_CHILD_SCORED',j,row$parent_dataset_id,row$dataset_id,'\n')
}
if(first)stop('No scores were created')
manifest<-data.frame(family,realworld_seed=eval_seed,sample_n=n,
 parent_block_id=if(nzchar(block_id))block_id else 'full',
 parent_count=length(unique(tab$parent_dataset_id)),child_count=nrow(tab),
 parent_ids=paste(sort(unique(tab$parent_dataset_id)),collapse=';'),
 scoring_training_seeds=paste(training_seeds,collapse=';'),
 score_sha256=t2_sha256(score_path),parent_manifest_sha256=t2_sha256(manifest_path),
 family_classifier_method=if('family_assignment_method'%in%names(tab))
  paste(unique(tab$family_assignment_method),collapse=';') else 'legacy_profile_only',
 benchmark='mean',weight_selection='frozen_discovery_no_retuning',
 code_revision=Sys.getenv('GITHUB_SHA','local'),stringsAsFactors=FALSE)
write.csv(manifest,file.path(out,'score_manifest.csv'),row.names=FALSE)
cat('T3_B3_REALWORLD_SCORE_PASS',family,eval_seed,n,'parents',manifest$parent_count,'\n')
