#!/usr/bin/env Rscript
# Freeze outcome-blind numeric child profiles while preserving source parents.
a <- commandArgs(TRUE)
if(length(a)<2L)stop('Usage: CANDIDATE_CATALOG OUTPUT_DIR [CATALOG_COMMIT]')
catalog_path<-a[1L];out<-a[2L]
catalog_commit<-if(length(a)>=3L)a[3L] else Sys.getenv('GITHUB_SHA','unverified-local')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
if(!file.exists(catalog_path))stop('Candidate catalog missing')
catalog<-read.csv(catalog_path,stringsAsFactors=FALSE,check.names=FALSE)
required<-c('dataset_id','parent_dataset_id','source_path','source_url','domain',
  'source_sector','variable','license_name','license_url','license_review_status')
if(!all(required%in%names(catalog))||!nrow(catalog))stop('Candidate parent/child catalog schema incomplete')
if(anyDuplicated(catalog[c('parent_dataset_id','dataset_id')]))stop('Duplicate parent-child identity')
slug<-function(x)gsub('[^A-Za-z0-9_.-]+','_',x)
numeric_values<-function(row){
 p<-as.character(row$source_path[1]); ext<-tolower(tools::file_ext(p))
 if(!file.exists(p))stop('Missing raw source: ',p)
 obj<-if(ext=='rds')readRDS(p) else if(ext=='csv')read.csv(p,stringsAsFactors=FALSE,check.names=FALSE) else
   stop('Source must be pre-extracted CSV or RDS: ',p)
 v<-as.character(row$variable[1])
 if(is.data.frame(obj)){if(!v%in%names(obj))stop('Variable absent from source: ',v);x<-obj[[v]]}
 else if(is.atomic(obj)&&is.null(dim(obj)))x<-obj else stop('Unsupported source object: ',p)
 x<-suppressWarnings(as.numeric(x));x<-x[is.finite(x)]
 transform<-if('transform'%in%names(row)&&!is.na(row$transform[1])&&nzchar(row$transform[1]))
   as.character(row$transform[1]) else 'raw'
 if(transform=='log1p')x<-log1p(x[x>=0])
 if(transform=='log')x<-log(x[x>0])
 if(transform=='diff_log')x<-diff(log(x[x>0]))
 x[is.finite(x)]
}
features<-function(x){
 s<-stats::sd(x); med<-stats::median(x); mad<-stats::mad(x,constant=1)
 sk<-if(s>0)mean((x-mean(x))^3)/s^3 else 0
 ku<-if(s>0)mean((x-mean(x))^4)/s^4-3 else 0
 scale<-if(is.finite(mad)&&mad>0)mad else stats::IQR(x,type=8)/1.349
 outlier<-if(is.finite(scale)&&scale>0)mean(abs(x-med)>3*scale) else 0
 profile<-if(min(x)>=0&&sk>=1.25)'lognormal_like' else
   if(min(x)>=0&&sk>.25&&sk<2.5&&ku<8)'weibull_like' else
   if(abs(sk)<=.6&&ku<=4)'normal_like' else
   if(abs(sk)<=1&&ku>4)'heavy_tail_symmetric' else 'empirical_unknown'
 list(n=length(x),mean=mean(x),skewness=sk,excess_kurtosis=ku,
      support_sign=if(all(x>0))'strictly_positive' else 'contains_nonpositive',
      outlier_fraction_3mad=outlier,empirical_profile=profile)
}
dir.create(file.path(out,'vectors'),recursive=TRUE,showWarnings=FALSE)
dir.create(file.path(out,'sources'),recursive=TRUE,showWarnings=FALSE)
rows<-vector('list',nrow(catalog))
for(i in seq_len(nrow(catalog))){
 r<-catalog[i,,drop=FALSE];source_path<-normalizePath(r$source_path,mustWork=TRUE)
 source_hash<-t2_sha256(source_path)
 target_source<-file.path(out,'sources',paste0(slug(r$dataset_id),'.',tools::file_ext(source_path)))
 if(!file.exists(target_source)&&!file.copy(source_path,target_source))stop('Failed to retain raw source')
 if(!identical(t2_sha256(target_source),source_hash))stop('Raw source copy hash mismatch')
 x<-numeric_values(r);if(length(x)<150L)stop('Child vector has fewer than 150 observations: ',r$dataset_id)
 f<-features(x)
 vector_path<-file.path(out,'vectors',paste0(slug(r$dataset_id),'.rds'))
 saveRDS(x,vector_path,version=3,compress='xz')
 profile_key<-paste(r$parent_dataset_id,r$dataset_id,f$n,
   format(f$skewness,digits=17),format(f$excess_kurtosis,digits=17),
   f$support_sign,format(f$outlier_fraction_3mad,digits=17),sep='|')
 profile_tmp<-tempfile();writeBin(charToRaw(profile_key),profile_tmp)
 profile_hash<-t2_sha256(profile_tmp);unlink(profile_tmp)
 rows[[i]]<-data.frame(dataset_id=r$dataset_id,parent_dataset_id=r$parent_dataset_id,
   source_url=r$source_url,source_path=target_source,source_sha256=source_hash,
   processed_path=vector_path,processed_sha256=t2_sha256(vector_path),
   profile_sha256=profile_hash,domain=r$domain,
   source_sector=r$source_sector,variable=r$variable,transform=if('transform'%in%names(r)&&!is.na(r$transform[1]))r$transform else 'raw',
   n=f$n,skewness=f$skewness,excess_kurtosis=f$excess_kurtosis,
   support_sign=f$support_sign,outlier_fraction_3mad=f$outlier_fraction_3mad,
   empirical_profile=f$empirical_profile,license_name=r$license_name,
   license_url=r$license_url,license_review_status=r$license_review_status,
   catalog_commit=catalog_commit,stringsAsFactors=FALSE)
}
profile<-do.call(rbind,rows)
write.csv(profile,file.path(out,'outcome_blind_profiles.csv'),row.names=FALSE)
cat('T3_B3_REALWORLD_PROFILE_PASS children=',nrow(profile),'parents=',
  length(unique(profile$parent_dataset_id)),'\n',sep='')
