#!/usr/bin/env Rscript
# Re-score immutable Held-out/Stress artifacts as a paired W* versus every
# classical benchmark tournament. The raw scoring artifacts are not rewritten.
a <- commandArgs(trailingOnly=TRUE)
if (length(a)!=1L || !a[[1L]] %in% c('heldout','stress')) stop('Usage: STAGE (heldout|stress)')
stage <- a[[1L]]
source('R/00_shared/load_all.R'); t2_load('.')
eval_col <- paste0(stage,'_seed')
standard_root <- if(stage=='heldout') 'artifacts/heldout_v3' else 'artifacts/v3_stress_scoring'
cross_root <- file.path('artifacts','v3_cross_family_scoring',stage)
standard_files <- if(dir.exists(standard_root)) list.files(standard_root,
  if(stage=='heldout') '^non_evolutionary_control_scores[.]csv$' else '^scores[.]csv$',
  recursive=TRUE,full.names=TRUE) else character()
cross_files <- if(dir.exists(cross_root)) list.files(cross_root,'^scores[.]csv$',
  recursive=TRUE,full.names=TRUE) else character()
files <- sort(unique(c(standard_files,cross_files)))
if(!length(files)||!length(cross_files)) stop('Both within-family and frozen cross-family score artifacts are required')
group_cols <- c('family','source_family','evaluation_family','transfer_scope','sample_n')
required <- c('model','mse','q95','training_seed',eval_col,'scenario_id',group_cols)
engine_from_id <- function(x) {
  x <- tolower(as.character(x)); order <- c('dirichlet','nsga2','de','ga')
  tokens <- strsplit(gsub('[^a-z0-9]+','_',x),'_',fixed=TRUE)[[1L]]
  tokens <- setdiff(tokens,c('normal','lognormal','weibull','invgauss','exgaussian','exwald'))
  z <- order[order %in% tokens]
  if(length(z)) z[[1L]] else NA_character_
}
unit_parts <- vector('list',length(files))
for(i in seq_along(files)) {
  d <- read.csv(files[[i]],stringsAsFactors=FALSE,check.names=FALSE)
  if(!all(required%in%names(d))) stop('Missing pairwise score fields: ',files[[i]])
  if(any(!is.finite(d$mse))||any(!is.finite(d$q95))) stop('Nonfinite score: ',files[[i]])
  d$candidate_engine <- vapply(d$model,function(m)
    if(m %in% ESTIMATOR_NAMES) NA_character_ else engine_from_id(m),character(1))
  evolved <- !is.na(d$candidate_engine)
  d$model[evolved] <- d$candidate_engine[evolved]
  # Collapse repeated scenarios and Discovery training seeds within the
  # independent held-out/stress evaluation seed before any inference.
  keys <- c(group_cols,eval_col,'model')
  unit_parts[[i]] <- aggregate(d[c('mse','q95')],d[keys],mean)
  rm(d); invisible(gc(FALSE))
  if(i %% 20L == 0L) cat('PAIRWISE_FILE_REDUCED',i,'of',length(files),'\n')
}
units <- do.call(rbind,unit_parts); rownames(units)<-NULL
key <- c(group_cols,eval_col,'model')
if(anyDuplicated(units[key])) stop('Duplicate independent-unit model scores across artifacts')
names(units)[names(units)==eval_col] <- 'evaluation_unit'
ans <- t3_pairwise_tournament(units,stage, 'evaluation_unit',group_cols,
  alpha=ga_config$fdr_primary,bootstrap_B=2000L)
ans$metrics$stage <- stage; ans$taxonomy$stage <- stage; ans$manifest$stage <- stage
out <- file.path('artifacts','v3_confirmatory_pairwise',stage)
if(dir.exists(out)) stop('Refusing to overwrite immutable pairwise tournament output')
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write.csv(units,file.path(out,'independent_unit_scores.csv'),row.names=FALSE)
write.csv(ans$metrics,file.path(out,'all_benchmark_pairwise_inference.csv'),row.names=FALSE)
write.csv(ans$taxonomy,file.path(out,'four_tier_winner_matrix.csv'),row.names=FALSE)
write.csv(ans$manifest,file.path(out,'panel_manifest.csv'),row.names=FALSE)
write.csv(data.frame(path=files,sha256=vapply(files,t2_sha256,character(1))),
  file.path(out,'input_manifest.csv'),row.names=FALSE)
cat('T3_PAIRWISE_TOURNAMENT_PASS',stage,'score_files',length(files),
    'hypotheses',nrow(ans$metrics),'retained_models',length(unique(ans$taxonomy$candidate_model)),'\n')
