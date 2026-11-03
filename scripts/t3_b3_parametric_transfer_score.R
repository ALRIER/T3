#!/usr/bin/env Rscript
# Score the frozen Discovery W* on independent, within-family parameter rows.
# Retain only mean, the Discovery-frozen own benchmark, and the four W* engines.
a <- commandArgs(TRUE)
if (length(a) != 7L) stop('Usage: FAMILY PARAMETER_ROW SEED N MC_PATH DISCOVERY_DIR OWN_BENCHMARK_MAP.csv')
family <- a[[1L]]; parameter_row <- as.integer(a[[2L]]); seed <- as.integer(a[[3L]])
n <- as.integer(a[[4L]]); mc_path <- a[[5L]]; discovery_root <- a[[6L]]
benchmark_map_path <- a[[7L]]
source('R/00_shared/load_all.R'); t2_load('.')
source('R/00_shared/pipeline.R')
if (!family %in% t2_families() || !seed %in% t2_v3_indices('parametric_transfer') ||
    !n %in% c(200L,1000L,3000L) || !file.exists(mc_path) ||
    !file.exists(benchmark_map_path)) stop('Invalid transfer identity/input')
source('R/00_shared/t3_b3_partitions.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R'); source('R/00_shared/t2_v3_b3_resources.R')
source('R/00_shared/t3_b3_partitions.R')
mc <- readRDS(mc_path)
expected_block_count <- 1L
expected_scenario_count <- 241L
if (!identical(mc$protocol,'t3_b3_parametric_transfer_v3') ||
    !identical(mc$family,family) || as.integer(mc$parameter_row)!=parameter_row ||
    as.integer(mc$seed_index)!=seed || as.integer(mc$n)!=n ||
    !identical(mc$component_names,ESTIMATOR_NAMES) || length(mc$scenarios)<1L ||
    length(mc$scenarios)!=expected_scenario_count ||
    as.integer(mc$scenario_block_count)!=expected_block_count ||
    anyDuplicated(as.integer(mc$grid$scenario_id)) ||
    !all(as.integer(mc$grid$scenario_id)%in%t3_b3_partition_ids('discovery_support')))
  stop('Parametric transfer Monte Carlo contract mismatch')
benchmark_map <- read.csv(benchmark_map_path,stringsAsFactors=FALSE,check.names=FALSE)
map <- benchmark_map[benchmark_map$evaluation_family==family &
  as.integer(benchmark_map$sample_n)==n,,drop=FALSE]
if (nrow(map)!=241L || anyDuplicated(map$scenario_id) ||
    !setequal(as.integer(map$scenario_id),t3_b3_partition_ids('discovery_support')) ||
    any(!map$own_benchmark %in% setdiff(ESTIMATOR_NAMES,'mean')))
  stop('Discovery-frozen own-benchmark map does not cover this transfer panel')
map <- map[match(as.integer(mc$grid$scenario_id),as.integer(map$scenario_id)),,drop=FALSE]
if (nrow(map)!=length(mc$scenarios) || anyNA(map$own_benchmark))
  stop('Discovery-frozen own-benchmark map could not be aligned to this scenario half')

out <- file.path('artifacts','t3_b3_parametric_transfer',family,
  sprintf('parameter_row%02d',parameter_row),sprintf('seed%02d_n%d',seed,n),
  sprintf('b%d',as.integer(mc$scenario_block)))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
target <- file.path(out,'scores.csv')
if (file.exists(target)) stop('Refusing to overwrite immutable scoring shard')
engine_from_id <- function(x) {
  x <- tolower(as.character(x)); engines <- c('dirichlet','nsga2','de','ga')
  tokens <- strsplit(gsub('[^a-z0-9]+','_',x),'_',fixed=TRUE)[[1L]]
  found <- engines[engines %in% tokens]
  if (length(found)) found[[1L]] else NA_character_
}
parts <- vector('list',length(t2_v3_indices('discovery')))
for (ti in seq_along(t2_v3_indices('discovery'))) {
  training_seed <- t2_v3_indices('discovery')[[ti]]
  d <- file.path(discovery_root,family,sprintf('seed%02d',training_seed),sprintf('n%d',n))
  model_file <- file.path(d,'discovery.rds')
  if (!file.exists(model_file)) stop('Missing frozen Discovery W: ',model_file)
  contract <- t3_stage_require(file.path(d,'stage_contract.rds'),'discovery',
    sprintf('b3_%s_n%d',family,n),family,training_seed,n)
  if (!identical(contract$payload$model_sha256,t2_sha256(model_file)))
    stop('Frozen W checksum mismatch: ',model_file)
  fit <- readRDS(model_file)
  engines <- Filter(function(m) !is.null(m$weights),fit$models)
  if (length(engines)!=4L || anyDuplicated(vapply(engines,function(m)engine_from_id(m$id),character(1))))
    stop('Expected four uniquely identified frozen Discovery engines')
  engine_labels <- vapply(engines,function(m)engine_from_id(m$id),character(1))
  if (anyNA(engine_labels)) stop('Could not identify a frozen engine')
  for (k in seq_along(engines)) engines[[k]]$id <- paste0(family,'_',engine_labels[[k]],'_parametric_frozen_W')
  classical <- lapply(ESTIMATOR_NAMES,function(nm)new_frozen_model(nm,component=nm))
  rows <- lapply(mc$scenarios,function(sc) {
    z <- score_model_set(sc$T,c(classical,engines),sc$target)
    z$scenario_id <- as.integer(sc$scenario_id)
    ref <- map$own_benchmark[match(as.integer(sc$scenario_id),as.integer(map$scenario_id))]
    if (length(ref)!=1L || is.na(ref) || !nzchar(ref))
      stop('Missing Discovery-frozen own benchmark for scenario ',sc$scenario_id)
    keep <- z$model=='mean' | z$model==ref | z$model%in%vapply(engines,`[[`,character(1),'id')
    z <- z[keep,,drop=FALSE]
    z$family <- family; z$source_family <- family; z$evaluation_family <- family
    z$transfer_scope <- 'within_family_parameter_transfer'
    z$parameter_row <- parameter_row; z$parametric_seed <- seed; z$sample_n <- n
    z$training_seed <- training_seed
    z$contamination <- as.numeric(mc$grid$contamination[match(sc$scenario_id,mc$grid$scenario_id)])
    z$mad_scale <- as.numeric(mc$grid$mad_scale[match(sc$scenario_id,mc$grid$scenario_id)])
    z$mechanism <- as.character(mc$grid$mechanism[match(sc$scenario_id,mc$grid$scenario_id)])
    z$own_benchmark <- rep(ref,nrow(z))
    z$discovery_sha256 <- t2_sha256(model_file)
    z
  })
  parts[[ti]] <- do.call(rbind,rows)
  rm(fit,engines,classical,rows); invisible(gc(FALSE))
}
raw <- do.call(rbind,parts)
train_seeds <- t2_v3_indices('discovery')
keys <- c('family','source_family','evaluation_family','transfer_scope','parameter_row',
  'sample_n','scenario_id','parametric_seed','own_benchmark','model','contamination','mad_scale','mechanism')
summary <- aggregate(raw[c('mse','q95')],raw[keys],mean)
summary$training_seed_count <- length(train_seeds)
summary$training_seed_set <- paste(train_seeds,collapse=';')
write.csv(summary,target,row.names=FALSE)
manifest <- data.frame(protocol='t3_b3_parametric_transfer_score_v3',family,
  parameter_row,seed,n,replications=500L,scenario_count=length(mc$scenarios),
  scenario_block=as.integer(mc$scenario_block),scenario_block_count=as.integer(mc$scenario_block_count),
  scenario_ids=paste(as.integer(mc$grid$scenario_id),collapse=';'),
  training_seed_count=length(train_seeds),score_rows=nrow(summary),
  scores_sha256=t2_sha256(target),mc_sha256=t2_sha256(mc_path),
  benchmark_map_sha256=t2_sha256(benchmark_map_path),
  selection='frozen_discovery_W_no_retuning',benchmark='discovery_frozen_best_classical_per_scenario_plus_mean',
  code_revision=Sys.getenv('GITHUB_SHA','local'),stringsAsFactors=FALSE)
write.csv(manifest,file.path(out,'score_manifest.csv'),row.names=FALSE)
cat('T3_B3_PARAMETRIC_TRANSFER_SCORE_PASS',family,parameter_row,seed,n,'rows',nrow(summary),'\n')
