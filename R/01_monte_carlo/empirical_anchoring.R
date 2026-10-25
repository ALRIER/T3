# Empirical shape anchoring for the Monte Carlo validation layer.
# This layer is intentionally separate from the final frozen-model realworld battery.

t2_mc_manifest <- function() {
  path <- file.path('config', 'mc_validation_datasets.csv')
  if (!file.exists(path)) stop('MC empirical manifest is missing')
  x <- read.csv(path, stringsAsFactors=FALSE, check.names=FALSE)
  required <- c('dataset_id','source_url','local_path','loader','transform','matched_family',
                'purpose','license','sha256')
  if (!all(required %in% names(x))) stop('MC empirical manifest is incomplete')
  if (nrow(x) != 5L || anyDuplicated(x$dataset_id)) stop('MC empirical manifest must contain five unique anchors')
  x
}

t2_mc_diagnostics <- function(x) {
  x <- as.numeric(x[is.finite(x)])
  if (length(x) < 4L) stop('MC empirical anchor has fewer than four finite observations')
  mu <- mean(x); s <- stats::sd(x)
  if (!is.finite(s) || s <= 0) stop('MC empirical anchor has zero or invalid variance')
  data.frame(n=length(x), mean=mu, variance=stats::var(x),
             skewness=mean((x-mu)^3)/s^3,
             excess_kurtosis=mean((x-mu)^4)/s^4-3,
             median=stats::median(x), mad=stats::mad(x, constant=1),
             iqr=stats::IQR(x), stringsAsFactors=FALSE)
}

t2_mc_load_anchor <- function(row) {
  path <- as.character(row$local_path)
  if (!file.exists(path)) stop(sprintf('Missing MC empirical input: %s', path))
  loader <- as.character(row$loader)
  if (loader == 'uci_wine') {
    z <- read.csv(path, header=FALSE)
    return(as.numeric(z[[2L]]))
  }
  if (loader == 'uci_forestfires') {
    z <- read.csv(path, stringsAsFactors=FALSE)
    if (!'area' %in% names(z)) stop('Forest Fires input lacks area')
    return(log1p(as.numeric(z$area)))
  }
  if (loader == 'rdatasets_gbsg') {
    z <- read.csv(path, stringsAsFactors=FALSE)
    time_col <- intersect(c('rfstime','time','futime','t'), names(z))[1L]
    event_col <- intersect(c('status','cens','event','dead'), names(z))[1L]
    if (is.na(time_col) || is.na(event_col)) stop('GBSG2 input lacks time/event columns')
    return(as.numeric(z[[time_col]][as.integer(z[[event_col]]) == 1L]))
  }
  if (loader %in% c('rtdists_or_public_fallback','market_returns','r_datasets_eustockmarkets')) {
    z <- read.csv(path, stringsAsFactors=FALSE)
    value_col <- intersect(c('value','log_return','logreturn','return'), names(z))[1L]
    if (is.na(value_col)) stop(sprintf('Standardized MC input lacks value column: %s', path))
    return(as.numeric(z[[value_col]]))
  }
  stop('Unsupported MC empirical loader: ', loader)
}

t2_mc_range_check <- function(value, low, high, tolerance=0.20) {
  if (!is.finite(value) || !is.finite(low) || !is.finite(high)) return(FALSE)
  span <- max(abs(high-low), 1e-12)
  value >= low - tolerance*span && value <= high + tolerance*span
}

t2_mc_synthetic_ranges <- function(grids=build_param_grids(), n_each=3000L, seed=77L) {
  set.seed(seed)
  out <- list()
  for (fam in names(grids)) {
    vals <- lapply(seq_len(nrow(grids[[fam]])), function(i) {
      x <- generate_population(fam, n_each, as.list(grids[[fam]][i,,drop=FALSE]))
      t2_mc_diagnostics(x)
    })
    z <- do.call(rbind, vals)
    out[[fam]] <- data.frame(
      matched_family=fam,
      skew_min=min(z$skewness), skew_max=max(z$skewness),
      kurt_min=min(z$excess_kurtosis), kurt_max=max(z$excess_kurtosis),
      cv_min=min(z$mad/abs(z$mean), na.rm=TRUE),
      cv_max=max(z$mad/abs(z$mean), na.rm=TRUE),
      stringsAsFactors=FALSE)
  }
  do.call(rbind, out)
}

t2_run_mc_empirical_anchoring <- function(mode='full', shard='mc_anchor',
                                          n_each=3000L, tolerance=0.20) {
  if (mode != 'full') {
    return(list(status='SKIPPED', reason='Empirical MC anchoring is a full-mode layer',
                manifest=t2_mc_manifest()))
  }
  manifest <- t2_mc_manifest()
  if (any(is.na(manifest$license) | !nzchar(trimws(manifest$license)) |
          grepl('review|pending|unknown|nonredistributable', manifest$license, ignore.case=TRUE)) ||
      any(is.na(manifest$sha256) | !nzchar(trimws(manifest$sha256))))
    stop('MC empirical manifest requires license and SHA-256 for every input')
  if (any(!file.exists(manifest$local_path)))
    stop('MC empirical cache is incomplete; acquire all five anchors before full mode')
  actual <- vapply(manifest$local_path, t2_sha256, character(1))
  if (any(tolower(actual) != tolower(manifest$sha256)))
    stop('MC empirical input checksum mismatch')
  if (all(c('raw_path','raw_sha256') %in% names(manifest))) {
    if (any(is.na(manifest$raw_path) | !nzchar(trimws(manifest$raw_path)) |
            !file.exists(manifest$raw_path)))
      stop('MC empirical raw cache is incomplete')
    raw_actual <- vapply(manifest$raw_path, t2_sha256, character(1))
    if (any(is.na(manifest$raw_sha256) | !nzchar(trimws(manifest$raw_sha256)) |
            tolower(raw_actual) != tolower(manifest$raw_sha256)))
      stop('MC empirical raw input checksum mismatch')
  } else raw_actual <- rep(NA_character_, nrow(manifest))
  ranges <- t2_mc_synthetic_ranges(n_each=n_each, seed=t2_seed(shard, 770L))
  rows <- lapply(seq_len(nrow(manifest)), function(i) {
    row <- manifest[i,,drop=FALSE]
    d <- t2_mc_diagnostics(t2_mc_load_anchor(row))
    r <- ranges[ranges$matched_family == row$matched_family, , drop=FALSE]
    policy <- if ('shape_policy' %in% names(row)) as.character(row$shape_policy) else 'in_family'
    stress_ok <- identical(policy, 'stress_out_of_family') && is.finite(d$skewness) &&
      is.finite(d$excess_kurtosis) && d$n >= 100L
    shape_ok <- t2_mc_range_check(d$skewness,r$skew_min,r$skew_max,tolerance) &&
      t2_mc_range_check(d$excess_kurtosis,r$kurt_min,r$kurt_max,tolerance)
    data.frame(dataset_id=row$dataset_id, matched_family=row$matched_family,
               n_obs=d$n, skewness=d$skewness, excess_kurtosis=d$excess_kurtosis,
               skew_in_range=t2_mc_range_check(d$skewness,r$skew_min,r$skew_max,tolerance),
               kurt_in_range=t2_mc_range_check(d$excess_kurtosis,r$kurt_min,r$kurt_max,tolerance),
               shape_in_range=shape_ok, shape_policy=policy,
               stress_anchor_valid=stress_ok, source_sha256=actual[i],
               raw_sha256=raw_actual[i], status=if (shape_ok || stress_ok) 'PASS' else 'FAIL',
               stringsAsFactors=FALSE)
  })
  results <- do.call(rbind, rows)
  results$status <- ifelse(results$shape_in_range | results$stress_anchor_valid, 'PASS', 'FAIL')
  list(status=if(all(results$status == 'PASS')) 'PASS' else 'FAIL',
       manifest=manifest, ranges=ranges, results=results,
       method='Empirical shape diagnostics compared with synthetic family ranges',
       tolerance=tolerance)
}
