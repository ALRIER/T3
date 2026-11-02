#!/usr/bin/env Rscript
# Final global inference from compact shard summaries; no raw Monte Carlo or
# large score CSVs are loaded in this job.
a<-commandArgs(trailingOnly=TRUE)
if(length(a)!=2L)stop('Usage: STAGE REDUCED_ARTIFACT_ROOT')
stage<-a[[1L]];root<-a[[2L]]
if(!stage%in%c('heldout','stress','realworld'))stop('Invalid stage')
source('R/00_shared/load_all.R');t2_load('.')
files<-list.files(root,'[.]csv[.]gz$',recursive=TRUE,full.names=TRUE)
if(!length(files))stop('No reduced tournament inputs')
parts<-lapply(files,function(p)read.csv(gzfile(p),stringsAsFactors=FALSE,check.names=FALSE))
z<-do.call(rbind,parts);rownames(z)<-NULL
if(stage=='realworld') {
  g<-c('parent_dataset_id','family','transfer_scope','sample_n','model')
  if(!all(g%in%names(z))||!'n_observations'%in%names(z))stop('Invalid reduced parent schema')
  weighted<-z[g]
  weighted$weighted_mse<-z$mse*z$n_observations
  weighted$weighted_q95<-z$q95*z$n_observations
  weighted$n_observations<-z$n_observations
  sums<-aggregate(weighted[c('weighted_mse','weighted_q95','n_observations')],
                  weighted[g],sum)
  sums$mse<-sums$cbind_mse/sums$n_observations
  sums$q95<-sums$cbind_q95/sums$n_observations
  z<-sums[c(g,'mse','q95')]
  names(z)[names(z)=='parent_dataset_id']<-'independent_unit'
  groups<-c('family','transfer_scope','sample_n')
} else {
  groups<-c('family','source_family','evaluation_family','transfer_scope','sample_n')
}
z$candidate_engine<-NA_character_
ans<-t3_pairwise_tournament(z,stage,'independent_unit',groups,alpha=ga_config$fdr_primary)
out<-file.path('artifacts','v3_confirmatory_pairwise',paste0(stage,'_v2'))
if(dir.exists(out))stop('Refusing to overwrite immutable tournament output')
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write.csv(z,file.path(out,'independent_unit_scores.csv'),row.names=FALSE)
write.csv(ans$metrics,file.path(out,'all_benchmark_pairwise_inference.csv'),row.names=FALSE)
write.csv(ans$taxonomy,file.path(out,'four_tier_winner_matrix.csv'),row.names=FALSE)
write.csv(ans$manifest,file.path(out,'panel_manifest.csv'),row.names=FALSE)
write.csv(data.frame(path=files,sha256=vapply(files,t2_sha256,character(1))),
  file.path(out,'input_manifest.csv'),row.names=FALSE)
writeLines(c(paste0('code_revision=',Sys.getenv('GITHUB_SHA','unverified-local')),
             paste0('workflow_run_id=',Sys.getenv('GITHUB_RUN_ID','local'))),
  file.path(out,'run_provenance.txt'))
cat('T3_PAIRWISE_REDUCED_TOURNAMENT_PASS',stage,'inputs',length(files),
  'hypotheses',nrow(ans$metrics),'units',length(unique(z$independent_unit)),'\n')
