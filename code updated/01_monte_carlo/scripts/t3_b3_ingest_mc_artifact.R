#!/usr/bin/env Rscript
# Materialize one immutable Monte Carlo Actions artifact for a downstream T3 job.
# Source data are copied, never regenerated or overwritten.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 6L) stop('Usage: ROLE FAMILY SEED N INCOMING_DIR SOURCE_RUN_ID')
role <- args[[1L]]; family <- args[[2L]]; seed <- as.integer(args[[3L]])
n <- as.integer(args[[4L]]); incoming <- args[[5L]]; source_run <- args[[6L]]
source('R/00_shared/load_all.R'); t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
if (!role %in% c('discovery','heldout','stress')) stop('Invalid Monte Carlo role')
if (!family %in% t2_families() || !seed %in% t2_v3_indices(role) ||
    !n %in% t2_v3_sample_sizes(role)) stop('Role/family/seed/sample-size contract mismatch')
if (!dir.exists(incoming) || !grepl('^[0-9]+$', source_run)) stop('Invalid Actions artifact input')

expected_dir <- file.path(sprintf('seed%02d', seed), sprintf('n%d_r500', n))
sources <- list.files(incoming, 'canonical\\.rds$', recursive=TRUE, full.names=TRUE)
sources <- sources[grepl(paste0('/', expected_dir, '/canonical\\.rds$'), sources)]
if (length(sources) != 1L) stop('Expected exactly one canonical artifact for ', expected_dir)
source_path <- sources[[1L]]
source_manifest <- file.path(dirname(source_path), 'manifest.csv')
if (!file.exists(source_manifest)) stop('Source artifact lacks manifest.csv')
manifest <- read.csv(source_manifest, stringsAsFactors=FALSE)
if (nrow(manifest) != 1L || !identical(as.character(manifest$role), role) ||
    !identical(as.character(manifest$family), family) ||
    !identical(as.integer(manifest$seed), seed) || !identical(as.integer(manifest$n), n) ||
    !identical(as.integer(manifest$reps), 500L) || !identical(as.integer(manifest$scenarios), 321L))
  stop('Monte Carlo manifest provenance mismatch')
if (!identical(t2_sha256(source_path), as.character(manifest$sha256))) stop('Monte Carlo manifest checksum mismatch')

target <- t2_v3_block_dir(role, family, seed, n, 500L)
dir.create(target, recursive=TRUE, showWarnings=FALSE)
canonical <- file.path(target, 'canonical.rds')
source_hash <- t2_sha256(source_path)
if (file.exists(canonical)) {
  if (!identical(t2_sha256(canonical), source_hash)) stop('Refusing to replace a different canonical block')
} else if (!file.copy(source_path, canonical, copy.date=TRUE)) stop('Failed to materialize canonical block')

z <- t2_read_rds(canonical)
if (!identical(z$protocol, t2_v3_protocol()) || !identical(z$role, role) ||
    !identical(z$family, family) || !identical(as.integer(z$seed_index), seed) ||
    !identical(as.integer(z$n), n) || !identical(as.integer(z$replications), 500L) ||
    length(z$scenarios) != 321L) stop('Canonical block provenance mismatch')
for (id in 0:320) {
  s <- z$scenarios[[id + 1L]]
  t2_v3_validate_scenario(s, id, 500L)
  p <- file.path(target, sprintf('scenario_%04d.rds', id))
  if (file.exists(p)) {
    old <- t2_read_rds(p); t2_v3_validate_scenario(old, id, 500L)
    if (!identical(old, s)) stop('Refusing to replace a different materialized scenario: ', id)
  } else saveRDS(s, p, compress='xz')
}
scenario_paths <- file.path(target, sprintf('scenario_%04d.rds', 0:320))
if (!all(file.exists(scenario_paths))) stop('Scenario materialization incomplete')
write.csv(data.frame(role=role, family=family, seed=seed, n=n, replications=500L,
  source_actions_run_id=source_run, source_sha256=source_hash,
  canonical_sha256=t2_sha256(canonical), scenario_count=321L,
  stringsAsFactors=FALSE), file.path(target, 'actions_ingest_manifest.csv'), row.names=FALSE)
contract <- file.path(target, 'stage_contract.rds')
if (!file.exists(contract)) t3_stage_publish('montecarlo', sprintf('b3_%s_n%d', family, n),
  list(scenario_ids=0:320, canonical_sha256=t2_sha256(canonical),
       source_actions_run_id=source_run), family, seed, n, 500L, contract,
  parents=paste0('actions_run_', source_run), seed_role=role)
invisible(t3_stage_require(contract, 'montecarlo', sprintf('b3_%s_n%d', family, n), family, seed, n))
cat('T3_B3_ACTIONS_MC_INGEST_PASS', role, family, seed, n, source_hash, '\n')
