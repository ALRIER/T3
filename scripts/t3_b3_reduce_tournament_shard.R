#!/usr/bin/env Rscript
# Reduce one downloaded immutable Actions score artifact to compact independent
# unit/model summaries. Designed for a one-artifact-per-runner matrix.
a <- commandArgs(trailingOnly=TRUE)
if(length(a)!=3L) stop('Usage: STAGE INPUT_DIR OUTPUT.csv.gz')
stage <- a[[1L]]; input <- a[[2L]]; output <- a[[3L]]
if(!stage%in%c('heldout','stress','realworld')) stop('Invalid tournament stage')
source('R/00_shared/load_all.R'); t2_load('.')
files <- list.files(input,'^scores[.]csv$',recursive=TRUE,full.names=TRUE)
if(!length(files)) files <- list.files(input,'^non_evolutionary_control_scores[.]csv$',recursive=TRUE,full.names=TRUE)
if(length(files)!=1L) stop('Expected exactly one raw score CSV in the Actions artifact')
d <- read.csv(files[[1L]],stringsAsFactors=FALSE,check.names=FALSE)
if(any(!is.finite(d$mse))||any(!is.finite(d$q95))) stop('Raw score shard contains nonfinite values')
engine_from_id <- function(x) {
  x<-tolower(as.character(x)); order<-c('dirichlet','nsga2','de','ga')
  tokens<-strsplit(gsub('[^a-z0-9]+','_',x),'_',fixed=TRUE)[[1L]]
  tokens<-setdiff(tokens,c('normal','lognormal','weibull','invgauss','exgaussian','exwald'))
  z<-order[order%in%tokens]; if(length(z))z[[1L]] else NA_character_
}
e<-vapply(d$model,function(m)if(m%in%ESTIMATOR_NAMES)NA_character_ else engine_from_id(m),character(1))
d$model[!is.na(e)]<-e[!is.na(e)]
if(stage=='realworld') {
  need<-c('parent_dataset_id','family','transfer_scope','model','mse','q95')
  if(!all(need%in%names(d))||anyNA(d$parent_dataset_id)||any(!nzchar(d$parent_dataset_id)))
    stop('Real-world shard lacks parent-cluster identity')
  keys<-c('parent_dataset_id','family','transfer_scope',
    intersect(c('sample_n'),names(d)),'model')
  sums<-aggregate(d[c('mse','q95')],d[keys],sum)
  cnt<-aggregate(rep(1,nrow(d)),d[keys],sum);names(cnt)[ncol(cnt)]<-'n_observations'
  z<-merge(sums,cnt,by=keys,sort=FALSE)
  z$mse<-z$mse/z$n_observations;z$q95<-z$q95/z$n_observations
  z$independent_unit<-z$parent_dataset_id
} else {
  eval_col<-paste0(stage,'_seed')
  strata<-c('family','source_family','evaluation_family','transfer_scope','sample_n')
  need<-c('model','mse','q95','training_seed','scenario_id',eval_col,strata)
  if(!all(need%in%names(d)))stop('Confirmatory score shard lacks transfer/taxonomy fields')
  # Equal weighting by prepared scenario and frozen training seed; then one
  # average score per independent evaluation seed and model.
  keys<-c(strata,eval_col,'model')
  z<-aggregate(d[c('mse','q95')],d[keys],mean)
  names(z)[names(z)==eval_col]<-'independent_unit'
}
dir.create(dirname(output),recursive=TRUE,showWarnings=FALSE)
con<-gzfile(output,'wt');write.csv(z,con,row.names=FALSE);close(con)
cat('TOURNAMENT_SHARD_REDUCED',stage,nrow(z),normalizePath(output,mustWork=FALSE),'\n')
