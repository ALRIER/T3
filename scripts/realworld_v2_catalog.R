#!/usr/bin/env Rscript
# Phase A of the regime-matched external audit.  This phase is outcome blind:
# it only freezes public sources, raw hashes and structural diagnostics.
args <- commandArgs(trailingOnly = TRUE)
stage <- if (length(args)) args[[1L]] else stop('Usage: catalog|profile [batch]')
batch <- if (length(args) > 1L) as.integer(args[[2L]]) else NA_integer_
root <- Sys.getenv('T2_RW_CATALOG_ROOT', 'artifacts/realworld_regime_matched_v2')
dir.create(root, recursive = TRUE, showWarnings = FALSE)
source('R/04_real_datasets/legacy_sources/realworld_external_battery_utils.R', local = .GlobalEnv)
source('R/04_real_datasets/legacy_sources/13_realworld_external_battery.R', local = .GlobalEnv)

finance_specs <- function(download_dir) {
  # FRED's public tag pages are accessible from Actions without an API key.
  # The resulting series identifiers are frozen into catalog.csv before scoring.
  ids <- character()
  for (page in 1:12) {
    u <- sprintf('https://fred.stlouisfed.org/tags/series?t=financial%%20markets&pageID=%d', page)
    h <- tryCatch(paste(readLines(u, warn=FALSE), collapse='\n'), error=function(e) '')
    ids <- c(ids, sub('^series/', '', unique(regmatches(h, gregexpr('series/[A-Za-z0-9_-]+', h))[[1L]])))
  }
  ids <- unique(ids); ids <- ids[nzchar(ids) & ids != '-1']; ids <- head(ids, 260L)
  lapply(ids, function(id) eb_record(paste0('FRED_', id), 'financial_macro_series',
    sprintf('https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s', id),
    loader='fred_csv_return', variable=id, transform='diff(log(value)) where positive; otherwise diff(value)',
    family_hint='financial_market'))
}

rw2_load_one <- function(sp, download_dir) {
  if (!identical(sp$loader, 'fred_csv_return')) return(eb_load_one(sp, download_dir))
  dir.create(download_dir, recursive=TRUE, showWarnings=FALSE)
  p <- file.path(download_dir, paste0(sp$id, '.csv'))
  ok <- tryCatch({ utils::download.file(sp$source_url, p, quiet=TRUE, mode='wb'); file.info(p)$size > 20L }, error=function(e) FALSE)
  if (!ok) return(list(ok=FALSE, error='FRED download failed', x=numeric(0)))
  z <- tryCatch(utils::read.csv(p, stringsAsFactors=FALSE, check.names=FALSE), error=function(e) NULL)
  if (is.null(z) || ncol(z) < 2L) return(list(ok=FALSE, error='Invalid FRED CSV', x=numeric(0)))
  x <- suppressWarnings(as.numeric(z[[2L]])); x <- x[is.finite(x)]
  if (length(x) < 151L) return(list(ok=FALSE, error='Insufficient finite FRED values', x=numeric(0)))
  x <- if (all(x > 0)) diff(log(x)) else diff(x)
  list(ok=length(x) >= 150L, error=if(length(x) >= 150L) '' else 'Insufficient returns', x=x)
}

write_csv <- function(x, path) utils::write.csv(x, path, row.names = FALSE, na = '')
catalog_path <- file.path(root, 'catalog.rds')
if (stage == 'catalog') {
  # Collect a fresh outcome-blind candidate pool. B3 freezes its new parents
  # according to current Discovery profiles; no historical target count.
  Sys.setenv(EXTERNAL_RDATASETS_MAX = '480', EXTERNAL_RDATASETS_MIN_ROWS = '150')
  specs <- c(finance_specs(file.path(root, 'downloads')), eb_uci_specs(), eb_rdatasets_specs(file.path(root, 'downloads')))
  ids <- vapply(specs, `[[`, character(1), 'id')
  specs <- specs[!duplicated(ids)]
  saveRDS(specs, catalog_path)
  tab <- do.call(rbind, lapply(specs, function(z) data.frame(
    dataset_id=z$id, domain=z$domain, source_url=z$source_url, loader=z$loader,
    variable=z$variable, transform=z$transform, family_hint=z$family_hint, stringsAsFactors=FALSE)))
  tab$batch <- (seq_len(nrow(tab)) - 1L) %/% 10L + 1L
  write_csv(tab, file.path(root, 'catalog.csv'))
  writeLines('CATALOG_COMPLETE', file.path(root, 'catalog.status'))
  cat('CATALOG', nrow(tab), 'candidates in', max(tab$batch), 'batches\n')
} else if (stage == 'profile') {
  if (!is.finite(batch) || batch < 1L || !file.exists(catalog_path)) stop('A valid batch and catalog are required')
  specs <- readRDS(catalog_path); tab <- read.csv(file.path(root, 'catalog.csv'), stringsAsFactors=FALSE)
  ids <- tab$dataset_id[tab$batch == batch]; specs <- specs[match(ids, vapply(specs, `[[`, character(1), 'id'))]
  out <- file.path(root, sprintf('profile_batch_%03d', batch)); dir.create(file.path(out, 'raw'), recursive=TRUE, showWarnings=FALSE)
  rows <- lapply(specs, function(sp) {
    got <- tryCatch(rw2_load_one(sp, file.path(root, 'downloads')), error=function(e) list(ok=FALSE,error=conditionMessage(e),x=numeric(0)))
    x <- suppressWarnings(as.numeric(got$x)); x <- x[is.finite(x)]
    ok <- isTRUE(got$ok) && length(x) >= 150L
    if (ok) saveRDS(x, file.path(out, 'raw', paste0(sp$id, '.rds')))
    d <- if (ok) rw_diag(x) else list(n=length(x),skew=NA_real_,kurt=NA_real_,support_sign='failed')
    data.frame(dataset_id=sp$id, parent_dataset_id=sp$id, domain=sp$domain, source_url=sp$source_url,
      loader=sp$loader, variable=sp$variable, transform=sp$transform, family_hint=sp$family_hint,
      load_ok=ok, load_error=if(ok) '' else as.character(got$error %||% 'insufficient observations'), n=d$n,
      skewness=d$skew, excess_kurtosis=d$kurt, support_sign=d$support_sign,
      empirical_profile=if(ok) .eb_empirical_profile(sp$family_hint,sp$domain,d$skew,d$kurt,d$support_sign) else 'load_failed',
      raw_sha256=if(ok) rw_md5(file.path(out,'raw',paste0(sp$id,'.rds'))) else '', stringsAsFactors=FALSE)
  })
  write_csv(do.call(rbind, rows), file.path(out, 'profiles.csv'))
  writeLines('PROFILE_COMPLETE', file.path(out, 'profile.status'))
  cat('PROFILE BATCH', batch, 'COMPLETE\n')
} else stop('Unknown stage')

# Uniform B3 publication on any successful catalog/profile run.
source('R/00_shared/t2_v3_b3_naming.R')
if(stage=='catalog') t2_b3_publish(root)
if(stage=='profile') t2_b3_publish(file.path(root,sprintf('profile_batch_%03d',batch)))
