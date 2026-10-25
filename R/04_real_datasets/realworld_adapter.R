# Final real-world validation adapter.
# This module is intentionally separate from the Monte Carlo empirical anchors.

t2_realworld_manifest <- function(path = Sys.getenv('T2_REALWORLD_MANIFEST',
                                                       unset=file.path('config', 'public_datasets.csv'))) {
  if (!file.exists(path)) stop('Final real-world manifest is missing')
  tab <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  required <- c('dataset_id', 'path', 'sha256', 'license')
  if (!all(required %in% names(tab)) || !nrow(tab))
    stop('Final real-world manifest is incomplete')
  tab
}

t2_realworld_validate_manifest <- function(tab, mode = 'smoke') {
  if (any(is.na(tab$license) | !nzchar(trimws(tab$license))))
    stop('Final real-world manifest contains undocumented licenses')
  if (mode == 'full' && any(grepl('fixture|nonredistributable|review|pending|unknown',
                                   tab$license, ignore.case = TRUE)))
    stop('Final real-world full mode requires reviewed redistributable inputs')
  if (any(!file.exists(tab$path))) stop('Final real-world cache is incomplete')
  actual <- vapply(tab$path, t2_sha256, character(1))
  if (any(is.na(tab$sha256) | !nzchar(trimws(tab$sha256)) |
          tolower(actual) != tolower(tab$sha256)))
    stop('Final real-world input checksum mismatch')
  tab$sha256_actual <- actual
  tab
}

t2_realworld_load_vector <- function(row) {
  z <- read.csv(row$path, stringsAsFactors = FALSE, check.names = FALSE)
  variable <- if ('variable' %in% names(row) && nzchar(row$variable)) row$variable else NA_character_
  if (!is.na(variable) && variable %in% names(z)) {
    x <- z[[variable]]
  } else {
    numeric_cols <- names(z)[vapply(z, function(v) {
      q <- suppressWarnings(as.numeric(v)); sum(is.finite(q)) >= 20L && length(unique(q[is.finite(q)])) > 1L
    }, logical(1))]
    if (!length(numeric_cols)) stop(sprintf('No numeric validation variable in %s', row$dataset_id))
    x <- z[[numeric_cols[1L]]]
    variable <- numeric_cols[1L]
  }
  x <- suppressWarnings(as.numeric(x))
  transform <- if ('transform' %in% names(row)) as.character(row$transform) else 'raw'
  if (identical(transform, 'log1p')) x <- log1p(x[x >= 0])
  if (identical(transform, 'log')) x <- log(x[x > 0])
  if (identical(transform, 'diff_log')) x <- diff(log(x[x > 0]))
  x <- x[is.finite(x)]
  if (length(x) < 20L) stop(sprintf('Insufficient observations in %s', row$dataset_id))
  list(dataset_id = as.character(row$dataset_id), variable = variable,
       transform = transform, x = x)
}

t2_run_realworld_public <- function(discovery, mode = 'smoke', shard = 'realworld') {
  tab <- t2_realworld_validate_manifest(t2_realworld_manifest(), mode)
  sample_sizes <- if (mode == 'smoke') c(200L, 1000L, 3000L) else {
    raw <- Sys.getenv('T2_REALWORLD_SAMPLE_SIZES', unset = '200,1000,3000')
    as.integer(strsplit(raw, ',', fixed = TRUE)[[1]])
  }
  sample_sizes <- sample_sizes[is.finite(sample_sizes) & sample_sizes > 1L]
  if (!length(sample_sizes)) stop('No valid real-world sample sizes configured')
  reps <- as.integer(Sys.getenv('T2_REALWORLD_REPS', unset = if (mode == 'smoke') '30' else '500'))
  bundle_path <- Sys.getenv('T2_REALWORLD_BUNDLE', unset = '')
  bundle <- NULL
  if (nzchar(bundle_path) && file.exists(bundle_path)) {
    bundle <- t2_read_rds(bundle_path)
    if (!identical(bundle$mode, mode) || !identical(as.integer(bundle$reps), reps) ||
        !identical(as.integer(bundle$sample_sizes), as.integer(sample_sizes)) ||
        !identical(bundle$manifest_sha256, as.character(tab$sha256)))
      stop('Real-world prepared bundle provenance/configuration mismatch')
    prepared <- bundle$prepared
    dataset_ids <- names(prepared)
  } else {
    datasets <- lapply(seq_len(nrow(tab)), function(i) t2_realworld_load_vector(tab[i, , drop = FALSE]))
    names(datasets) <- vapply(datasets, `[[`, character(1), 'dataset_id')
    dataset_ids <- names(datasets)
    prepared <- lapply(seq_along(datasets), function(i) {
      realworld_prepare(datasets[[i]]$x, sample_sizes = sample_sizes, R = reps,
                        seed = t2_seed('realworld_canonical_bundle', 502L + i))
    })
    names(prepared) <- dataset_ids
  }
  scores <- do.call(rbind, lapply(seq_along(prepared), function(i) {
    realworld_compare_models(prepared[[i]], discovery$models,
                             dataset_id = dataset_ids[i])
  }))
  # Keep the bootstrap/inference audit as a separate table. The compact score
  # table retains the same mse/q95 contract used by heldout and aggregate.
  audit <- realworld_integrated_audit(
    datasets = setNames(lapply(dataset_ids, function(x) x), dataset_ids), models = discovery$models,
    sample_sizes = sample_sizes, R = reps, seed = t2_seed('realworld_canonical_audit', 702L),
    control = 'mean', prepared = prepared)
  list(status = 'PASS', fixture = any(grepl('fixture', tab$license, ignore.case = TRUE)),
       manifest = tab, scores = scores, condition_rows = audit$condition_rows,
       dataset_level = audit$dataset_level,
       results = list(realworld_inference = audit$condition_rows),
       stage = 'realworld_external_battery', reps = reps,
       sample_sizes = sample_sizes, empirical_target = 'full_dataset_mean_proxy',
       final_battery = TRUE, prepared_bundle = if (is.null(bundle)) 'local_canonical' else bundle$bundle_id)
}
