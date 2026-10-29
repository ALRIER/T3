#!/usr/bin/env Rscript
# Evaluate discovery-frozen W on independently generated within-family parameter rows.
# No fitting, HPO, threshold selection, or candidate selection is permitted here.
a <- commandArgs(TRUE)
if (length(a) != 6L) stop('Usage: FAMILY PARAMETER_ROW SEED N MC_PATH DISCOVERY_DIR')
family <- a[[1L]]; parameter_row <- as.integer(a[[2L]]); seed <- as.integer(a[[3L]])
n <- as.integer(a[[4L]]); mc_path <- a[[5L]]; discovery_root <- a[[6L]]
source('R/00_shared/load_all.R'); t2_load('.')
if (!family %in% t2_families() || !seed %in% t2_v3_indices('parametric_transfer') ||
    !n %in% c(200L,1000L,3000L) || !file.exists(mc_path)) stop('Invalid transfer identity/input')
source('R/00_shared/pipeline.R'); source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R'); source('R/00_shared/t2_v3_b3_resources.R')
source('R/00_shared/t3_b3_partitions.R')
mc <- readRDS(mc_path)
if (!identical(mc$protocol,'t3_b3_parametric_transfer_v1') ||
    !identical(mc$family,family) || as.integer(mc$parameter_row)!=parameter_row ||
    as.integer(mc$seed_index)!=seed || as.integer(mc$n)!=n ||
    !identical(mc$component_names,ESTIMATOR_NAMES) || length(mc$scenarios)!=321L)
  stop('Parametric transfer Monte Carlo contract mismatch')
out <- file.path('artifacts','t3_b3_parametric_transfer',family,
  sprintf('parameter_row%02d',parameter_row),sprintf('seed%02d_n%d',seed,n))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
target <- file.path(out,'scores.csv')
if (file.exists(target)) stop('Refusing to overwrite immutable scoring shard')
first <- TRUE
for (training_seed in t2_v3_indices('discovery')) {
  d <- file.path(discovery_root,family,sprintf('seed%02d',training_seed),sprintf('n%d',n))
  model_file <- file.path(d,'discovery.rds')
  if (!file.exists(model_file)) stop('Missing frozen Discovery W: ',model_file)
  contract <- t3_stage_require(file.path(d,'stage_contract.rds'),'discovery',
    sprintf('b3_%s_n%d',family,n),family,training_seed,n)
  if (!identical(contract$payload$model_sha256,t2_sha256(model_file)))
    stop('Frozen W checksum mismatch: ',model_file)
  fit <- readRDS(model_file)
  engines <- Filter(function(m) !is.null(m$weights),fit$models)
  if (length(engines)!=4L || anyDuplicated(vapply(engines,`[[`,character(1),'id')))
    stop('Expected four frozen discovery engines')
  rows <- lapply(mc$scenarios,function(sc) {
    z <- score_model_set(sc$T,c(list(new_frozen_model('mean',component='mean')),engines),sc$target)
    z$scenario_id <- as.integer(sc$scenario_id)
    z$family <- family; z$source_family <- family; z$evaluation_family <- family
    z$transfer_scope <- 'within_family_parameter_transfer'
    z$parameter_row <- parameter_row; z$training_seed <- training_seed
    z$parametric_seed <- seed; z$sample_n <- n
    z$contamination <- as.numeric(mc$grid$contamination[match(sc$scenario_id,mc$grid$scenario_id)])
    z$mad_scale <- as.numeric(mc$grid$mad_scale[match(sc$scenario_id,mc$grid$scenario_id)])
    z$mechanism <- as.character(mc$grid$mechanism[match(sc$scenario_id,mc$grid$scenario_id)])
    z$discovery_sha256 <- t2_sha256(model_file)
    z
  })
  block <- do.call(rbind,rows)
  write.table(block,target,sep=',',append=!first,col.names=first,row.names=FALSE,quote=TRUE)
  first <- FALSE
  rm(fit,engines,rows,block); invisible(gc(FALSE))
}
if (first) stop('No frozen Discovery weights were scored')
manifest <- data.frame(protocol='t3_b3_parametric_transfer_score_v1',family,
  parameter_row,seed,n,replications=500L,scenario_count=321L,
  scores_sha256=t2_sha256(target),selection='frozen_discovery_W_no_retuning',
  benchmark='sample_mean_component',code_revision=Sys.getenv('GITHUB_SHA','local'),
  stringsAsFactors=FALSE)
write.csv(manifest,file.path(out,'score_manifest.csv'),row.names=FALSE)
cat('T3_B3_PARAMETRIC_TRANSFER_SCORE_PASS',family,parameter_row,seed,n,'\n')
