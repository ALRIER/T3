#!/usr/bin/env Rscript
# Stage-wide primary inference: one BH panel across all candidate/metric,
# family, sample-size, and transfer strata after reducing repeated scenarios.
a<-commandArgs(TRUE)
if(length(a)!=1L||!a[1L]%in%c('heldout','stress'))
  stop('Usage: STAGE (heldout|stress)')
stage<-a[1L]
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R');source('R/05_audits/stage_inference.R')
standard_root<-if(stage=='heldout')'artifacts/heldout_v3' else 'artifacts/v3_stress_scoring'
cross_root<-file.path('artifacts','v3_cross_family_scoring',stage)
standard_files<-if(dir.exists(standard_root))list.files(standard_root,
  if(stage=='heldout')'^non_evolutionary_control_scores[.]csv$' else '^scores[.]csv$',
  recursive=TRUE,full.names=TRUE) else character()
cross_files<-if(dir.exists(cross_root))list.files(cross_root,'^scores[.]csv$',
  recursive=TRUE,full.names=TRUE) else character()
paths<-sort(unique(c(standard_files,cross_files)))
if(!length(paths))stop('No complete confirmatory score artifacts found')
if(!length(cross_files))stop('Frozen cross-family score artifacts are required for the primary global panel')
eval_col<-paste0(stage,'_seed')
required<-c('model','mse','q95','training_seed',eval_col,'family','sample_n',
            'source_family','evaluation_family','transfer_scope')
reduce_one<-function(path){
  d<-read.csv(path,stringsAsFactors=FALSE,check.names=FALSE)
  if(!all(required%in%names(d)))stop('Missing confirmatory columns in ',path)
  if(any(!is.finite(d$mse))||any(!is.finite(d$q95)))stop('Non-finite score in ',path)
  keys<-c('family','source_family','evaluation_family','transfer_scope','sample_n',
          eval_col,'training_seed','model')
  aggregate(d[,c('mse','q95'),drop=FALSE],d[,keys,drop=FALSE],mean)
}
reduced<-do.call(rbind,lapply(paths,reduce_one));rownames(reduced)<-NULL
key<-c('family','source_family','evaluation_family','transfer_scope','sample_n',
       eval_col,'training_seed','model')
if(anyDuplicated(reduced[key]))stop('Duplicate reduced score keys across artifacts')
inference<-t3_confirmatory_seed_summary(reduced,stage)
taxonomy<-t3_winner_taxonomy(inference)
out<-file.path('artifacts','v3_confirmatory_global',stage)
if(dir.exists(out))stop('Refusing to overwrite immutable global panel: ',out)
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write.csv(inference,file.path(out,'stage_global_inference.csv'),row.names=FALSE)
write.csv(taxonomy,file.path(out,'stage_global_winner_taxonomy.csv'),row.names=FALSE)
write.csv(reduced,file.path(out,'independent_seed_scores.csv'),row.names=FALSE)
write.csv(data.frame(stage=stage,score_files=length(paths),
  strata=length(unique(interaction(reduced[c('source_family','evaluation_family',
    'transfer_scope','sample_n')],drop=TRUE))),
  evaluation_seed_count=length(unique(reduced[[eval_col]])),
  hypotheses=nrow(inference),global_bh_family='all reported candidate x metric x transfer strata',
  score_file_manifest=paste(paths,collapse=';'),stringsAsFactors=FALSE),
  file.path(out,'panel_manifest.csv'),row.names=FALSE)
write.csv(data.frame(path=paths,sha256=vapply(paths,t2_sha256,character(1)),
  score_role=ifelse(grepl('v3_cross_family_scoring',paths),'cross_family','within_family'),
  stringsAsFactors=FALSE),file.path(out,'input_manifest.csv'),row.names=FALSE)
writeLines(c(paste0('confirmatory_run_id=',Sys.getenv('T3_CONFIRMATORY_RUN_ID','unspecified')),
  paste0('cross_family_run_id=',Sys.getenv('T3_CROSS_FAMILY_RUN_ID','unspecified')),
  paste0('code_revision=',Sys.getenv('GITHUB_SHA','unverified-local')),
  paste0('runtime_image=',Sys.getenv('T2_R_IMAGE','unspecified'))),
  file.path(out,'run_provenance.txt'))
cat('T3_STAGE_GLOBAL_PANEL_PASS',stage,'files',length(paths),
    'hypotheses',nrow(inference),'\n')
