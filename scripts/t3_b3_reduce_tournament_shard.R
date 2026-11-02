#!/usr/bin/env Rscript
# Reduce a bounded block of immutable score artifacts to independent units.
a <- commandArgs(trailingOnly=TRUE)
if(length(a)!=3L) stop('Usage: STAGE INPUT_DIR OUTPUT.csv.gz')
stage <- a[[1L]]; input <- a[[2L]]; output <- a[[3L]]
if(!stage%in%c('heldout','stress','realworld')) stop('Invalid stage')
source('R/00_shared/load_all.R'); t2_load('.')
files <- list.files(input,'^scores[.]csv$',recursive=TRUE,full.names=TRUE)
if(!length(files)) files <- list.files(input,'^non_evolutionary_control_scores[.]csv$',recursive=TRUE,full.names=TRUE)
if(!length(files)) stop('No raw score CSVs in this block')
engine_from_id <- function(x) {
  x<-tolower(as.character(x)); order<-c('dirichlet','nsga2','de','ga')
  tokens<-strsplit(gsub('[^a-z0-9]+','_',x),'_',fixed=TRUE)[[1L]]
  tokens<-setdiff(tokens,c('normal','lognormal','weibull','invgauss','exgaussian','exwald'))
  z<-order[order%in%tokens]; if(length(z))z[[1L]] else NA_character_
}
reduce_file <- function(path) {
  d <- read.csv(path,stringsAsFactors=FALSE,check.names=FALSE)
  if(any(!is.finite(d$mse))||any(!is.finite(d$q95))) stop('Raw score shard contains nonfinite values: ',path)
  e<-vapply(d$model,function(m)if(m%in%ESTIMATOR_NAMES)NA_character_ else engine_from_id(m),character(1))
  d$model[!is.na(e)]<-e[!is.na(e)]
  if(stage=='realworld') {
    need<-c('parent_dataset_id','dataset_id','family','transfer_scope','matched_scenario_id',
            'depth','sample_n','model','mse','q95')
    if(!all(need%in%names(d))||anyNA(d$parent_dataset_id)||any(!nzchar(d$parent_dataset_id)))
      stop('Real-world shard lacks parent/child/depth identity: ',path)
    optional<-intersect(c('evaluation_profile','domain','source_sector','realworld_seed'),names(d))
    keys<-c('parent_dataset_id','dataset_id','family','transfer_scope','sample_n',
            'matched_scenario_id','depth',optional,'model')
    names(d)[names(d)=='matched_scenario_id']<-'scenario_id'
    keys[keys=='matched_scenario_id']<-'scenario_id'
    sums<-aggregate(d[c('mse','q95')],d[keys],mean)
    cnt<-aggregate(rep(1,nrow(d)),d[keys],sum);names(cnt)[ncol(cnt)]<-'n_score_rows'
    z<-merge(sums,cnt,by=keys,sort=FALSE);z$independent_unit<-z$parent_dataset_id
  } else {
    eval_col<-paste0(stage,'_seed')
    strata<-c('family','source_family','evaluation_family','transfer_scope','sample_n','scenario_id')
    need<-c('model','mse','q95','training_seed','scenario_id',eval_col,strata)
    if(!all(need%in%names(d))) stop('Confirmatory score shard lacks transfer/taxonomy fields: ',path)
    keys<-c(strata,eval_col,'model')
    z<-aggregate(d[c('mse','q95')],d[keys],mean)
    names(z)[names(z)==eval_col]<-'independent_unit'
  }
  z
}
parts<-lapply(files,reduce_file)
z<-do.call(rbind,parts);rownames(z)<-NULL
if(stage!='realworld') {
  keys<-c('family','source_family','evaluation_family','transfer_scope','sample_n','scenario_id','independent_unit','model')
  if(anyDuplicated(z[keys])) stop('Duplicate independent-unit/model score across this block')
}
dir.create(dirname(output),recursive=TRUE,showWarnings=FALSE)
con<-gzfile(output,'wt');write.csv(z,con,row.names=FALSE);close(con)
cat('TOURNAMENT_BLOCK_REDUCED',stage,'files',length(files),'rows',nrow(z),
    normalizePath(output,mustWork=FALSE),'\n')
