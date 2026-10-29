# Independent confirmatory layer.
# This module deliberately does not read held-out, stress, or real-world
# results from the exploratory full run. It reads only frozen discovery weights
# and generates new Monte Carlo streams with confirmatory seeds.

t2_confirmatory_root <- function() {
  Sys.getenv('T2_CONFIRMATORY_ROOT', unset = file.path('artifacts', 'confirmatory'))
}

t2_confirmatory_version <- function() 'v1_independent'

t2_confirmatory_protocol <- function(path = file.path('config', 'confirmatory_protocol.csv')) {
  if (!file.exists(path)) stop('Confirmatory protocol is missing: ', path)
  x <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  if (!all(c('key', 'value', 'description') %in% names(x)) || !nrow(x))
    stop('Confirmatory protocol is incomplete')
  if (anyDuplicated(x$key)) stop('Confirmatory protocol has duplicate keys')
  x
}

t2_confirmatory_value <- function(key, protocol = t2_confirmatory_protocol()) {
  i <- match(key, protocol$key)
  if (is.na(i)) stop('Missing confirmatory protocol key: ', key)
  protocol$value[i]
}

t2_confirmatory_ints <- function(key, protocol = t2_confirmatory_protocol()) {
  z <- strsplit(t2_confirmatory_value(key, protocol), ':', fixed = TRUE)[[1L]]
  if (length(z) == 2L) return(seq.int(as.integer(z[1L]), as.integer(z[2L])))
  as.integer(strsplit(t2_confirmatory_value(key, protocol), '|', fixed = TRUE)[[1L]])
}

t2_confirmatory_sizes <- function(mode = 'full') {
  if (identical(mode, 'smoke')) return(200L)
  as.integer(strsplit(t2_confirmatory_value('sample_sizes'), '|', fixed = TRUE)[[1L]])
}

t2_confirmatory_reps <- function(mode = 'full') {
  if (identical(mode, 'smoke')) return(20L)
  as.integer(t2_confirmatory_value('replications'))
}

t2_confirmatory_bootstrap_B <- function(mode = 'full') {
  if (identical(mode, 'smoke')) return(100L)
  as.integer(t2_confirmatory_value('bootstrap_B'))
}

t2_confirmatory_seeds <- function(mode = 'full') {
  if (identical(mode, 'smoke')) return(9L)
  t2_confirmatory_ints('confirmatory_seed_indices')
}

t2_confirmatory_mc_seed <- function(family, confirm_seed) {
  t2_seed(sprintf('confirmatory_mc_%s_seed%02d', family, as.integer(confirm_seed)), 1001L)
}

t2_confirmatory_scenario_seed <- function(family, confirm_seed, scenario_id) {
  t2_seed(sprintf('confirmatory_mc_%s_seed%02d_scenario%04d', family,
                  as.integer(confirm_seed), as.integer(scenario_id)), 1007L)
}

t2_confirmatory_mc_path <- function(family, confirm_seed, n, replications) {
  file.path(t2_confirmatory_root(), 'montecarlo', t2_confirmatory_version(), family,
            sprintf('seed%02d', as.integer(confirm_seed)),
            sprintf('n%s_r%s.rds', as.integer(n), as.integer(replications)))
}

t2_confirmatory_mc_checkpoint <- function(path) {
  list(root = paste0(path, '.parts'), progress = paste0(path, '.progress.rds'))
}

t2_confirmatory_grid <- function(mode = 'full') {
  grid <- build_contamination_grid(ga_config)
  if (identical(mode, 'smoke')) grid <- grid[c(1L, 2L, which(grid$rate == .10)[1L]), , drop = FALSE]
  grid
}

t2_confirmatory_generate_scenario <- function(family, n, replications, row, target,
                                               base_samples, confirm_seed) {
  if (!is.matrix(base_samples) || nrow(base_samples) != n || ncol(base_samples) != replications)
    stop('Invalid confirmatory Monte Carlo base pool')
  if (row$rate > 0)
    set.seed(t2_confirmatory_scenario_seed(family, confirm_seed, row$scenario_id))
  samples <- vector('list', replications)
  for (k in seq_len(replications)) {
    x <- base_samples[, k]
    if (row$rate > 0)
      x <- inject_outliers_realistic(x, contamination_rate = row$rate,
                                     outlier_scale_mad = row$scale,
                                     type = row$mechanism)
    samples[[k]] <- x
  }
  Tmat <- component_matrix(samples)
  list(T = Tmat, target = target,
       benchmark = precompute_benchmarks(Tmat, target, rep(TRUE, 26L)),
       band = ifelse(row$rate == 0, 'clean',
                     ifelse(row$rate <= .05, 'low',
                            ifelse(row$rate <= .10, 'intermediate', 'high'))),
       scenario_id = row$scenario_id, rate = row$rate, mechanism = row$mechanism)
}

t2_confirmatory_mc <- function(family, confirm_seed, n, replications, mode = 'full',
                               generate = TRUE) {
  if (!family %in% t2_families()) stop('Unknown confirmatory family: ', family)
  path <- t2_confirmatory_mc_path(family, confirm_seed, n, replications)
  if (file.exists(path)) {
    out <- t2_read_rds(path)
    if (!identical(out$family, family) || !identical(as.integer(out$confirm_seed), as.integer(confirm_seed)) ||
        !identical(as.integer(out$n), as.integer(n)) || !identical(as.integer(out$replications), as.integer(replications)) ||
        !identical(out$version, t2_confirmatory_version()))
      stop('Confirmatory Monte Carlo provenance mismatch: ', path)
    return(out)
  }
  if (!isTRUE(generate)) stop('Confirmatory Monte Carlo block is missing: ', path)
  grid <- t2_confirmatory_grid(mode)
  cp <- t2_confirmatory_mc_checkpoint(path)
  dir.create(cp$root, recursive = TRUE, showWarnings = FALSE)
  target <- analytic_mean_from_params(family, t2_params(family))
  base_path <- file.path(cp$root, 'base_samples.rds')
  if (file.exists(base_path)) {
    base_samples <- t2_read_rds(base_path)
  } else {
    set.seed(t2_confirmatory_mc_seed(family, confirm_seed))
    base_samples <- vapply(seq_len(replications),
                           function(k) generate_population(family, n, t2_params(family)),
                           numeric(n))
    t2_atomic_save(base_samples, base_path)
  }
  expected <- list(mode = mode, family = family, confirm_seed = as.integer(confirm_seed),
                   n = as.integer(n), replications = as.integer(replications), grid = grid,
                   version = t2_confirmatory_version(),
                   base_seed = t2_confirmatory_mc_seed(family, confirm_seed))
  if (file.exists(cp$progress)) {
    progress <- t2_read_rds(cp$progress)
    if (!identical(progress[c('mode', 'family', 'confirm_seed', 'n', 'replications',
                              'grid', 'version', 'base_seed')], expected))
      stop('Confirmatory Monte Carlo checkpoint provenance mismatch')
  } else {
    progress <- c(expected, list(completed = integer()))
    t2_atomic_save(progress, cp$progress)
  }
  completed <- sort(unique(as.integer(progress$completed)))
  if (length(completed)) {
    part_paths <- file.path(cp$root, sprintf('scenario_%04d.rds', completed))
    if (any(!file.exists(part_paths))) stop('Confirmatory Monte Carlo checkpoint is incomplete')
  }
  for (j in setdiff(seq_len(nrow(grid)), completed)) {
    part <- t2_confirmatory_generate_scenario(family, n, replications,
                                              grid[j, , drop = FALSE], target,
                                              base_samples, confirm_seed)
    t2_atomic_save(part, file.path(cp$root, sprintf('scenario_%04d.rds', j)))
    completed <- sort(c(completed, j)); progress$completed <- completed
    t2_atomic_save(progress, cp$progress)
  }
  scenarios <- lapply(seq_len(nrow(grid)), function(j)
    t2_read_rds(file.path(cp$root, sprintf('scenario_%04d.rds', j))))
  out <- list(scenarios = scenarios, grid = grid, family = family,
              confirm_seed = as.integer(confirm_seed), n = as.integer(n),
              replications = as.integer(replications),
              version = t2_confirmatory_version(), role = 'confirmatory',
              scenario_seed_scheme = 'confirmatory_family_seed_scenario_id')
  out$canonical_id <- sprintf('confirmatory_%s_seed%02d_n%s_r%s', family,
                              as.integer(confirm_seed), n, replications)
  t2_atomic_save(out, path)
  out
}

t2_confirmatory_model_manifest <- function(path = file.path('config', 'confirmatory_frozen_models.csv')) {
  if (!file.exists(path)) stop('Frozen confirmatory model manifest is missing: ', path)
  x <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  required <- c('model_id', 'family', 'engine', 'training_seed', 'weights_path', 'weights_sha256')
  if (!all(required %in% names(x)) || nrow(x) != 192L) stop('Frozen model manifest must contain 192 rows')
  if (anyDuplicated(x$model_id) || any(x$training_seed < 0L | x$training_seed > 7L))
    stop('Frozen model manifest has invalid IDs or training seeds')
  if (any(!file.exists(x$weights_path))) stop('Frozen model file is missing')
  actual <- vapply(x$weights_path, t2_sha256, character(1))
  if (any(tolower(actual) != tolower(x$weights_sha256))) stop('Frozen model checksum mismatch')
  x$sha256_actual <- actual
  x
}

t2_confirmatory_load_models <- function(family,
                                        manifest = t2_confirmatory_model_manifest()) {
  x <- manifest[manifest$family == family, , drop = FALSE]
  if (nrow(x) != 32L) stop('Expected 32 frozen models for family ', family)
  refs <- reference_model_set()
  candidates <- lapply(seq_len(nrow(x)), function(i) {
    w <- read.csv(x$weights_path[i], stringsAsFactors = FALSE, check.names = FALSE)
    if (!all(c('component', 'weight') %in% names(w)) || nrow(w) != 26L)
      stop('Invalid frozen weight file: ', x$weights_path[i])
    if (!identical(as.character(w$component), as.character(ESTIMATOR_NAMES)))
      stop('Frozen component order mismatch: ', x$weights_path[i])
    new_frozen_model(x$model_id[i], weights = as.numeric(w$weight), family = family)
  })
  names(candidates) <- x$model_id
  by_engine <- split(candidates, x$engine)
  list(reference = refs, candidates = candidates, by_engine = by_engine,
       manifest = x, all = c(refs, candidates))
}

t2_confirmatory_score_root <- function(family, confirm_seed) {
  file.path(t2_confirmatory_root(), 'score', family,
            sprintf('confirm_seed%02d', as.integer(confirm_seed)))
}

t2_confirmatory_score_block <- function(family, confirm_seed, mode = 'full') {
  models <- t2_confirmatory_load_models(family)
  ns <- t2_confirmatory_sizes(mode); reps <- t2_confirmatory_reps(mode)
  root <- t2_confirmatory_score_root(family, confirm_seed)
  dir.create(root, recursive = TRUE, showWarnings = FALSE)
  raw_manifest <- list(); score_rows <- list()
  for (n in ns) {
    mc <- t2_confirmatory_mc(family, confirm_seed, n, reps, mode, generate = FALSE)
    raw_entries <- vector('list', length(mc$scenarios))
    for (i in seq_along(mc$scenarios)) {
      sc <- mc$scenarios[[i]]; benchmark_se <- (model_predict(sc$T, models$reference[[1L]]) - sc$target)^2
      se <- do.call(cbind, lapply(models$candidates, function(m)
        (model_predict(sc$T, m) - sc$target)^2))
      colnames(se) <- names(models$candidates)
      raw_entries[[i]] <- list(family = family, confirm_seed = as.integer(confirm_seed),
                               sample_n = as.integer(n), scenario_id = sc$scenario_id,
                               band = sc$band, rate = sc$rate, mechanism = sc$mechanism,
                               benchmark_id = 'mean', benchmark_se = benchmark_se,
                               candidate_ids = colnames(se), candidate_se = se,
                               replications = nrow(se))
      score_rows[[length(score_rows) + 1L]] <- do.call(rbind, lapply(seq_len(ncol(se)), function(j) {
        data.frame(family = family, engine = sub(sprintf('^%s_', family), '',
                                                 sub('_train[0-9]+$', '', colnames(se)[j])),
                  model_id = colnames(se)[j], training_seed = as.integer(sub('.*_train', '', colnames(se)[j])),
                  confirm_seed = as.integer(confirm_seed), scenario_id = sc$scenario_id,
                  sample_n = n, band = sc$band, rate = sc$rate, mechanism = sc$mechanism,
                  mse = mean(se[, j]), q95 = unname(quantile(se[, j], .95, type = 8)),
                  benchmark_mse = mean(benchmark_se),
                  benchmark_q95 = unname(quantile(benchmark_se, .95, type = 8)),
                  n_rep = nrow(se), stringsAsFactors = FALSE)
      }))
    }
    raw_path <- file.path(root, sprintf('raw_errors_n%s.rds', n))
    t2_atomic_save(raw_entries, raw_path)
    raw_manifest[[length(raw_manifest) + 1L]] <- data.frame(
      family = family, confirm_seed = as.integer(confirm_seed), sample_n = n,
      raw_path = raw_path, raw_sha256 = t2_sha256(raw_path), n_scenarios = length(raw_entries),
      stringsAsFactors = FALSE)
  }
  scores <- do.call(rbind, score_rows); raw_index <- do.call(rbind, raw_manifest)
  t2_write_csv(scores, file.path(root, 'scores.csv'))
  t2_write_csv(raw_index, file.path(root, 'raw_errors_manifest.csv'))
  t2_write_csv(data.frame(family = family, confirm_seed = confirm_seed, mode = mode,
                          version = t2_confirmatory_version(),
                          model_manifest_sha256 = t2_sha256(file.path('config', 'confirmatory_frozen_models.csv')),
                          stringsAsFactors = FALSE), file.path(root, 'provenance.csv'))
  writeLines(sprintf('confirmatory_score %s seed%02d COMPLETE', family, confirm_seed),
             file.path(root, 'score.status'))
  invisible(scores)
}

t2_confirmatory_block_test <- function(x, B = 2000L, seed = 101L) {
  x <- as.numeric(x); x <- x[is.finite(x)]
  if (length(x) < 4L) {
    # Contract/smoke runs may contain one block, but they must never emit a
    # scientific confirmation. Full mode always supplies eight blocks.
    if (!length(x)) stop('No confirmatory blocks are available')
    return(c(difference = mean(x), ci_low = NA_real_, ci_high = NA_real_,
              p_value = NA_real_, bootstrap_B = B, n_blocks = length(x)))
  }
  point <- mean(x); set.seed(seed)
  boot <- replicate(B, mean(sample(x, length(x), replace = TRUE)))
  ci <- as.numeric(quantile(boot, c(.025, .975), type = 8))
  p <- if (sd(x) == 0) if (point < 0) 0 else 1 else t.test(x, alternative = 'less')$p.value
  c(difference = point, ci_low = ci[1L], ci_high = ci[2L], p_value = p,
    bootstrap_B = B, n_blocks = length(x))
}

t2_confirmatory_inference <- function(family, mode = 'full') {
  models <- t2_confirmatory_load_models(family)
  seeds <- t2_confirmatory_seeds(mode); ns <- t2_confirmatory_sizes(mode)
  reps <- t2_confirmatory_reps(mode); block_rows <- list(); stability <- list()
  for (cs in seeds) {
    by_engine <- list()
    for (engine in names(models$by_engine)) {
      engine_models <- models$by_engine[[engine]]
      records <- list()
      for (n in ns) {
        raw_path <- file.path(t2_confirmatory_score_root(family, cs), sprintf('raw_errors_n%s.rds', n))
        if (!file.exists(raw_path)) stop('Missing confirmatory raw errors: ', raw_path)
        entries <- t2_read_rds(raw_path)
        for (entry in entries) {
          for (model_id in names(engine_models)) {
            j <- match(model_id, entry$candidate_ids)
            cse <- entry$candidate_se[, j]; bse <- entry$benchmark_se
            records[[length(records) + 1L]] <- data.frame(
              model_id = model_id, training_seed = as.integer(sub('.*_train', '', model_id)),
              mse_difference = mean(cse) - mean(bse),
              q95_difference = unname(quantile(cse, .95, type = 8) -
                                      quantile(bse, .95, type = 8)),
              benchmark_mse = mean(bse), benchmark_q95 = unname(quantile(bse, .95, type = 8)),
              stringsAsFactors = FALSE)
          }
        }
      }
      rr <- do.call(rbind, records)
      # Equal weight for each frozen training vector, then equal weight for
      # each fresh confirmatory seed. No seed is selected using results.
      per_model <- aggregate(cbind(mse_difference, q95_difference, benchmark_mse, benchmark_q95) ~
                               model_id + training_seed, rr, mean)
      block <- aggregate(cbind(mse_difference, q95_difference, benchmark_mse, benchmark_q95) ~ 1,
                         per_model, mean)
      block_rows[[length(block_rows) + 1L]] <- data.frame(
        family = family, engine = engine, confirm_seed = as.integer(cs),
        mse_difference = block$mse_difference, q95_difference = block$q95_difference,
        benchmark_mse = block$benchmark_mse, benchmark_q95 = block$benchmark_q95,
        n_training_models = nrow(per_model), stringsAsFactors = FALSE)
      stability[[length(stability) + 1L]] <- transform(per_model,
        family = family, engine = engine, confirm_seed = as.integer(cs))
    }
  }
  blocks <- do.call(rbind, block_rows); stable <- do.call(rbind, stability)
  primary <- do.call(rbind, lapply(split(blocks, blocks$engine), function(z) {
    a <- t2_confirmatory_block_test(z$mse_difference, t2_confirmatory_bootstrap_B(mode),
                                    t2_seed(paste(family, unique(z$engine), 'mse'), 8101L))
    b <- t2_confirmatory_block_test(z$q95_difference, t2_confirmatory_bootstrap_B(mode),
                                    t2_seed(paste(family, unique(z$engine), 'q95'), 8102L))
    data.frame(family = family, engine = unique(z$engine),
      mse_difference = a[['difference']], mse_ci_low = a[['ci_low']], mse_ci_high = a[['ci_high']],
      mse_p_value = a[['p_value']], q95_difference = b[['difference']],
      q95_ci_low = b[['ci_low']], q95_ci_high = b[['ci_high']], q95_p_value = b[['p_value']],
      benchmark_mse = mean(z$benchmark_mse), benchmark_q95 = mean(z$benchmark_q95),
      n_confirmatory_blocks = nrow(z), n_training_models = unique(z$n_training_models),
      stringsAsFactors = FALSE)
  }))
  primary$mse_q_value <- p.adjust(primary$mse_p_value, 'BH')
  primary$q95_q_value <- p.adjust(primary$q95_p_value, 'BH')
  primary$mse_gain_pct <- -100 * primary$mse_difference / pmax(primary$benchmark_mse, 1e-12)
  primary$q95_gain_pct <- -100 * primary$q95_difference / pmax(primary$benchmark_q95, 1e-12)
  primary$mse_confirmed <- primary$mse_difference < 0 & primary$mse_ci_high < 0 &
    primary$mse_q_value <= as.numeric(t2_confirmatory_value('fdr_alpha'))
  primary$q95_confirmed <- primary$q95_difference < 0 & primary$q95_ci_high < 0 &
    primary$q95_q_value <= as.numeric(t2_confirmatory_value('fdr_alpha'))
  primary$both_confirmed <- primary$mse_confirmed & primary$q95_confirmed
  primary$evidence_type <- 'confirmatory_prespecified'
  root <- file.path(t2_confirmatory_root(), 'inference', family)
  dir.create(root, recursive = TRUE, showWarnings = FALSE)
  t2_write_csv(primary, file.path(root, 'primary_inference.csv'))
  t2_write_csv(stable, file.path(root, 'training_seed_stability.csv'))
  t2_write_csv(blocks, file.path(root, 'confirmatory_seed_blocks.csv'))
  writeLines(sprintf('confirmatory_inference %s COMPLETE', family), file.path(root, 'inference.status'))
  invisible(primary)
}

t2_confirmatory_realworld_manifest <- function(
    path = file.path('config', 'confirmatory_public_datasets.csv')) {
  if (!file.exists(path)) stop('Independent confirmatory real-world manifest is missing: ', path)
  x <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  required <- c('dataset_id', 'path', 'sha256', 'license', 'variable', 'transform',
                'family_hint', 'independence_group', 'raw_path', 'raw_sha256',
                'source_object', 'source_r_version', 'source_url')
  if (!all(required %in% names(x)) || !nrow(x)) stop('Confirmatory real-world manifest is incomplete')
  if (anyDuplicated(x$dataset_id) || anyDuplicated(x$independence_group))
    stop('Confirmatory real-world manifest must contain unique parent datasets')
  old_path <- file.path('config', 'public_datasets.csv')
  if (file.exists(old_path)) {
    old <- read.csv(old_path, stringsAsFactors = FALSE, check.names = FALSE)
    if (any(x$dataset_id %in% old$dataset_id))
      stop('Confirmatory real-world manifest overlaps the exploratory battery')
  }
  if (any(grepl('fixture|nonredistributable|pending|unknown', x$license, ignore.case = TRUE)))
    stop('Confirmatory real-world manifest contains unreviewed inputs')
  if (any(x$family_hint != 'all'))
    stop('Confirmatory real-world inputs must be evaluated against all families')
  if (any(!file.exists(x$path))) stop('Confirmatory real-world dataset cache is incomplete')
  if (any(!file.exists(x$raw_path))) stop('Confirmatory real-world raw cache is incomplete')
  actual <- vapply(x$path, t2_sha256, character(1))
  if (any(tolower(actual) != tolower(x$sha256))) stop('Confirmatory real-world checksum mismatch')
  raw_actual <- vapply(x$raw_path, t2_sha256, character(1))
  if (any(tolower(raw_actual) != tolower(x$raw_sha256)))
    stop('Confirmatory real-world raw checksum mismatch')
  x$sha256_actual <- actual
  x$raw_sha256_actual <- raw_actual
  x
}

t2_confirmatory_realworld_root <- function() file.path(t2_confirmatory_root(), 'realworld')

t2_confirmatory_realworld_score <- function(mode = 'full') {
  tab <- t2_confirmatory_realworld_manifest()
  ns <- t2_confirmatory_sizes(mode); reps <- t2_confirmatory_reps(mode)
  manifest <- t2_confirmatory_model_manifest()
  families <- t2_families()
  out_root <- t2_confirmatory_realworld_root()
  dir.create(file.path(out_root, 'raw_errors'), recursive = TRUE, showWarnings = FALSE)
  bundle_path <- Sys.getenv('T2_REALWORLD_BUNDLE', unset = '')
  bundle <- NULL
  if (nzchar(bundle_path) && file.exists(bundle_path)) {
    bundle <- t2_read_rds(bundle_path)
    if (!identical(bundle$mode, mode) ||
        !identical(as.integer(bundle$reps), as.integer(reps)) ||
        !identical(as.integer(bundle$sample_sizes), as.integer(ns)) ||
        !identical(as.character(bundle$manifest_sha256), as.character(tab$sha256)))
      stop('Real-world prepared bundle provenance/configuration mismatch')
    if (!identical(as.character(bundle$dataset_ids), as.character(tab$dataset_id)))
      stop('Real-world prepared bundle dataset order mismatch')
  }
  score_rows <- list(); raw_rows <- list()
  for (i in seq_len(nrow(tab))) {
    row <- tab[i, , drop = FALSE]
    data <- t2_realworld_load_vector(row)
    prepared <- if (is.null(bundle)) {
      realworld_prepare(data$x, sample_sizes = ns, R = reps,
                        seed = t2_seed(paste('confirmatory_realworld', row$dataset_id), 9001L))
    } else {
      bundle$prepared[[as.character(row$dataset_id)]]
    }
    if (is.null(prepared) || length(prepared) != length(ns))
      stop('Real-world prepared bundle lacks sample sizes for ', row$dataset_id)
    entries <- list()
    for (fam in families) {
      models <- t2_confirmatory_load_models(fam, manifest)
      for (j in seq_along(prepared)) {
        z <- prepared[[j]]
        bse <- (model_predict(z$T, models$reference[[1L]]) - z$target)^2
        se <- do.call(cbind, lapply(models$candidates, function(m)
          (model_predict(z$T, m) - z$target)^2))
        colnames(se) <- names(models$candidates)
        entries[[length(entries) + 1L]] <- list(
          dataset_id = data$dataset_id, family = fam, sample_n = z$sample_n,
          target = z$target, benchmark_id = 'mean', benchmark_se = bse,
          candidate_ids = colnames(se), candidate_se = se,
          replications = nrow(se))
        score_rows[[length(score_rows) + 1L]] <- do.call(rbind, lapply(seq_len(ncol(se)), function(k) {
          data.frame(dataset_id = data$dataset_id, family = fam,
            engine = sub(sprintf('^%s_', fam), '', sub('_train[0-9]+$', '', colnames(se)[k])),
            model_id = colnames(se)[k], training_seed = as.integer(sub('.*_train', '', colnames(se)[k])),
            sample_n = z$sample_n, mse = mean(se[, k]), q95 = unname(quantile(se[, k], .95, type = 8)),
            benchmark_mse = mean(bse), benchmark_q95 = unname(quantile(bse, .95, type = 8)),
            n_rep = nrow(se), stringsAsFactors = FALSE)
        }))
      }
    }
    raw_path <- file.path(out_root, 'raw_errors', paste0(data$dataset_id, '.rds'))
    t2_atomic_save(entries, raw_path)
    raw_rows[[length(raw_rows) + 1L]] <- data.frame(
      dataset_id = data$dataset_id, family = fam, independence_group = row$independence_group,
      raw_path = raw_path, raw_sha256 = t2_sha256(raw_path),
      stringsAsFactors = FALSE)
  }
  scores <- do.call(rbind, score_rows); raw_index <- do.call(rbind, raw_rows)
  t2_write_csv(scores, file.path(out_root, 'scores.csv'))
  t2_write_csv(raw_index, file.path(out_root, 'raw_errors_manifest.csv'))
  t2_write_csv(tab, file.path(out_root, 'manifest_verified.csv'))
  writeLines('confirmatory_realworld_score COMPLETE', file.path(out_root, 'score.status'))
  invisible(scores)
}

t2_confirmatory_realworld_inference <- function(mode = 'full') {
  tab <- t2_confirmatory_realworld_manifest()
  root <- t2_confirmatory_realworld_root()
  if (!file.exists(file.path(root, 'score.status')))
    stop('Confirmatory real-world scores are missing')
  B <- t2_confirmatory_bootstrap_B(mode)
  rows <- list(); dataset_rows <- list()
  for (i in seq_len(nrow(tab))) {
    row <- tab[i, , drop = FALSE]
    entries <- t2_read_rds(file.path(root, 'raw_errors', paste0(row$dataset_id, '.rds')))
    # A dataset contributes one independent parent block to every family and
    # engine.  The family is read from each raw entry, never inferred from the
    # observed outcome or chosen after scoring.
    for (fam in t2_families()) for (engine in c('ga', 'nsga2', 'de', 'dirichlet')) {
      selected <- Filter(function(entry) identical(as.character(entry$family), fam), entries)
      if (length(selected) != length(t2_confirmatory_sizes(mode)))
        stop('Expected one raw entry per sample size for ', row$dataset_id, '/', fam)
      engine_rows <- lapply(selected, function(entry) {
        ids <- entry$candidate_ids
        j <- grep(sprintf('^%s_%s_train', fam, engine), ids)
        if (length(j) != 8L) stop('Expected eight frozen models for ', fam, '/', engine)
        cse <- rowMeans(entry$candidate_se[, j, drop = FALSE])
        bse <- entry$benchmark_se
        list(mse = cse - bse, q95 = cse, b = bse,
             mse_difference = mean(cse) - mean(bse),
             q95_difference = unname(quantile(cse, .95, type = 8) -
                                     quantile(bse, .95, type = 8)))
      })
      mse_d <- vapply(engine_rows, `[[`, numeric(1), 'mse_difference')
      q95_d <- vapply(engine_rows, `[[`, numeric(1), 'q95_difference')
      # Dataset-level record: equal weight for the three sample sizes.
      block <- data.frame(dataset_id = row$dataset_id, family = fam, engine = engine,
                          mse_difference = mean(mse_d), q95_difference = mean(q95_d),
                          benchmark_mse = mean(vapply(engine_rows, function(z) mean(z$b), numeric(1))),
                          benchmark_q95 = mean(vapply(engine_rows, function(z) unname(quantile(z$b, .95, type = 8)), numeric(1))),
                          stringsAsFactors = FALSE)
      dataset_rows[[length(dataset_rows) + 1L]] <- block
    }
  }
  dataset_level <- do.call(rbind, dataset_rows)
  # Primary external hypotheses are the 4 engine comparisons pooled over the
  # independent parent datasets; parent datasets, not repeated subsamples,
  # are the inferential blocks.
  primary <- do.call(rbind, lapply(split(dataset_level,
                                        interaction(dataset_level$family,
                                                    dataset_level$engine,
                                                    drop = TRUE)), function(z) {
    a <- t2_confirmatory_block_test(z$mse_difference, B,
                                    t2_seed(paste('confirmatory_realworld', unique(z$family),
                                                  unique(z$engine), 'mse'), 9301L))
    b <- t2_confirmatory_block_test(z$q95_difference, B,
                                    t2_seed(paste('confirmatory_realworld', unique(z$family),
                                                  unique(z$engine), 'q95'), 9302L))
    data.frame(family = unique(z$family), engine = unique(z$engine),
      mse_difference = a[['difference']],
      mse_ci_low = a[['ci_low']], mse_ci_high = a[['ci_high']], mse_p_value = a[['p_value']],
      q95_difference = b[['difference']], q95_ci_low = b[['ci_low']], q95_ci_high = b[['ci_high']],
      q95_p_value = b[['p_value']], benchmark_mse = mean(z$benchmark_mse),
      benchmark_q95 = mean(z$benchmark_q95), n_parent_datasets = nrow(z),
      stringsAsFactors = FALSE)
  }))
  # The external confirmatory family is the same 24 family-by-engine family
  # used for Monte Carlo confirmation; BH is therefore applied over 24 tests
  # separately for MSE and q95.
  primary$mse_q_value <- p.adjust(primary$mse_p_value, 'BH')
  primary$q95_q_value <- p.adjust(primary$q95_p_value, 'BH')
  primary$mse_gain_pct <- -100 * primary$mse_difference / pmax(primary$benchmark_mse, 1e-12)
  primary$q95_gain_pct <- -100 * primary$q95_difference / pmax(primary$benchmark_q95, 1e-12)
  alpha <- as.numeric(t2_confirmatory_value('fdr_alpha'))
  primary$mse_confirmed <- primary$mse_difference < 0 & primary$mse_ci_high < 0 & primary$mse_q_value <= alpha
  primary$q95_confirmed <- primary$q95_difference < 0 & primary$q95_ci_high < 0 & primary$q95_q_value <= alpha
  primary$both_confirmed <- primary$mse_confirmed & primary$q95_confirmed
  primary$evidence_type <- 'confirmatory_prespecified_independent_parents'
  t2_write_csv(dataset_level, file.path(root, 'dataset_level.csv'))
  t2_write_csv(primary, file.path(root, 'primary_inference.csv'))
  writeLines('confirmatory_realworld_inference COMPLETE', file.path(root, 'inference.status'))
  invisible(primary)
}

t2_confirmatory_report <- function(mode = 'full') {
  families <- t2_families()
  mc_paths <- file.path(t2_confirmatory_root(), 'inference', families,
                        'primary_inference.csv')
  if (any(!file.exists(mc_paths)))
    stop('One or more family-level confirmatory inference files are missing')
  mc <- do.call(rbind, lapply(seq_along(families), function(i) {
    z <- read.csv(mc_paths[i], stringsAsFactors = FALSE, check.names = FALSE)
    if (nrow(z) != 4L) stop('Expected four engines in ', mc_paths[i])
    z$family <- families[i]
    z
  }))
  rw_path <- file.path(t2_confirmatory_root(), 'realworld', 'primary_inference.csv')
  if (!file.exists(rw_path)) stop('Confirmatory real-world inference is missing')
  rw <- read.csv(rw_path, stringsAsFactors = FALSE, check.names = FALSE)
  if (nrow(rw) != length(families) * 4L)
    stop('Expected 24 real-world family-engine rows')
  key <- c('family', 'engine')
  mc$key <- paste(mc$family, mc$engine, sep = '/')
  rw$key <- paste(rw$family, rw$engine, sep = '/')
  if (anyDuplicated(mc$key) || anyDuplicated(rw$key) || !setequal(mc$key, rw$key))
    stop('Monte Carlo and real-world family-engine keys do not agree')
  names(mc)[names(mc) == 'mse_confirmed'] <- 'mc_mse_confirmed'
  names(mc)[names(mc) == 'q95_confirmed'] <- 'mc_q95_confirmed'
  names(mc)[names(mc) == 'both_confirmed'] <- 'mc_both_confirmed'
  names(rw)[names(rw) == 'mse_confirmed'] <- 'realworld_mse_confirmed'
  names(rw)[names(rw) == 'q95_confirmed'] <- 'realworld_q95_confirmed'
  names(rw)[names(rw) == 'both_confirmed'] <- 'realworld_both_confirmed'
  keep_mc <- c('key', 'family', 'engine', 'mse_difference', 'mse_ci_low',
               'mse_ci_high', 'mse_p_value', 'mse_q_value', 'mse_gain_pct',
               'q95_difference', 'q95_ci_low', 'q95_ci_high', 'q95_p_value',
               'q95_q_value', 'q95_gain_pct', 'mc_mse_confirmed',
               'mc_q95_confirmed', 'mc_both_confirmed', 'n_confirmatory_blocks')
  keep_rw <- c('key', 'mse_difference', 'mse_ci_low', 'mse_ci_high',
               'mse_p_value', 'mse_q_value', 'mse_gain_pct', 'q95_difference',
               'q95_ci_low', 'q95_ci_high', 'q95_p_value', 'q95_q_value',
               'q95_gain_pct', 'realworld_mse_confirmed',
               'realworld_q95_confirmed', 'realworld_both_confirmed',
               'n_parent_datasets')
  final <- merge(mc[keep_mc], rw[keep_rw], by = 'key', suffixes = c('_mc', '_realworld'))
  final$final_both_confirmed <- final$mc_both_confirmed & final$realworld_both_confirmed
  final$final_mse_confirmed <- final$mc_mse_confirmed & final$realworld_mse_confirmed
  final$final_q95_confirmed <- final$mc_q95_confirmed & final$realworld_q95_confirmed
  final$evidence_type <- 'confirmatory_mc_plus_independent_realworld'
  root <- file.path(t2_confirmatory_root(), 'report')
  dir.create(root, recursive = TRUE, showWarnings = FALSE)
  t2_write_csv(mc, file.path(root, 'montecarlo_primary_all.csv'))
  t2_write_csv(rw, file.path(root, 'realworld_primary_all.csv'))
  t2_write_csv(final, file.path(root, 'final_family_engine_summary.csv'))
  winners <- final[final$final_both_confirmed, c('family', 'engine',
                                                  'mse_gain_pct_mc',
                                                  'q95_gain_pct_mc',
                                                  'mse_gain_pct_realworld',
                                                  'q95_gain_pct_realworld'),
                  drop = FALSE]
  t2_write_csv(winners, file.path(root, 'final_joint_confirmed_winners.csv'))
  lines <- c(
    '# T2 confirmatory report', '',
    paste0('- mode: ', mode),
    paste0('- family-engine hypotheses: ', nrow(final)),
    paste0('- independent real-world parent datasets: ',
           unique(rw$n_parent_datasets)),
    paste0('- joint MSE+q95 confirmations in both layers: ', nrow(winners)),
    '',
    'The joint-confirmed table is empty unless a family-engine passes the',
    'prespecified MSE and q95 criteria in both the fresh Monte Carlo layer',
    'and the independent real-world parent-dataset layer.'
  )
  writeLines(lines, file.path(root, 'confirmatory_report.md'))
  writeLines('confirmatory_report COMPLETE', file.path(root, 'report.status'))
  invisible(final)
}

t2_confirmatory_preflight <- function(mode = 'full') {
  p <- t2_confirmatory_protocol(); m <- t2_confirmatory_model_manifest()
  if (!identical(t2_confirmatory_seeds(mode), if (mode == 'smoke') 9L else 9:16))
    stop('Confirmatory seed policy mismatch')
  if (any(m$training_seed %in% t2_confirmatory_seeds(mode)))
    stop('Training and confirmatory seeds overlap')
  if (any(m$family %in% character(0))) stop('Empty family manifest')
  list(status = 'PASS', protocol_id = t2_confirmatory_value('protocol_id', p),
       models = nrow(m), confirmatory_seeds = t2_confirmatory_seeds(mode),
       sample_sizes = t2_confirmatory_sizes(mode), replications = t2_confirmatory_reps(mode))
}
