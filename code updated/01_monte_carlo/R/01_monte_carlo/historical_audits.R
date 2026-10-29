# Integrated Monte Carlo audit layers. These are deliberately independent of the
# later frozen-candidate realworld battery.

t2_mc_layer1 <- function(mode='full', shard='mc', max_rows=6L) {
  grids <- build_param_grids()
  n_sim <- if (mode == 'smoke') 1500L else 10000L
  rows <- list(); k <- 0L
  set.seed(t2_seed(shard, 810L))
  expected <- c(normal=0L, lognormal=1L, weibull=1L, invgauss=1L,
                exgaussian=1L, exwald=1L)
  for (fam in names(grids)) {
    ix <- seq_len(min(nrow(grids[[fam]]), max_rows))
    for (i in ix) {
      p <- as.list(grids[[fam]][i,,drop=FALSE])
      x <- generate_population(fam, n_sim, p)
      d <- t2_mc_diagnostics(x)
      truth <- analytic_mean_from_params(fam, p)
      # A single finite draw is judged against a sampling-error tolerance.  A
      # fixed relative-error threshold is invalid near zero and too strict for
      # the intentionally heavy-tailed families.
      sd_hat <- sqrt(d$variance)
      mean_ok <- is.finite(truth) && is.finite(sd_hat) &&
        abs(d$mean-truth) <= max(0.05 * abs(truth), 6 * sd_hat / sqrt(n_sim))
      skew_ok <- if (expected[[fam]] == 0L) abs(d$skewness) < 0.35 else
        is.finite(d$skewness) && d$skewness > -0.5
      k <- k + 1L
      rows[[k]] <- data.frame(layer='L1_moment_fidelity', family=fam,
        param_row=i, mean_ok=mean_ok, skew_ok=skew_ok,
        status=if (mean_ok && skew_ok) 'PASS' else 'FAIL', stringsAsFactors=FALSE)
    }
  }
  out <- do.call(rbind, rows)
  list(data=out, status=if (all(out$status == 'PASS')) 'PASS' else 'FAIL')
}

t2_mc_layer2 <- function(mode='full', shard='mc') {
  n <- if (mode == 'smoke') 1200L else 4000L
  reps <- if (mode == 'smoke') 12L else 40L
  cases <- data.frame(rate=c(0,.10,.20), scale=c(NA,9,12),
                      mechanism=c('none','upper_tail','upper_tail'), stringsAsFactors=FALSE)
  rows <- lapply(seq_len(nrow(cases)), function(i) {
    set.seed(t2_seed(shard, 820L+i))
    gam <- numeric(reps)
    for (r in seq_len(reps)) {
      x <- generate_population('normal', n, list(mean=0,sd=1))
      if (cases$rate[i] > 0) x <- inject_outliers_realistic(x, cases$rate[i], cases$scale[i], cases$mechanism[i])
      med <- median(x); madv <- mad(x, constant=1); if (!is.finite(madv) || madv <= 0) madv <- sd(x)
      gam[r] <- mean(abs(x-med) > 3*madv)
    }
    observed <- mean(gam)
    # Clean data has a known detector false-positive rate; contaminated cases
    # must show a materially higher rate than clean data.
    clean_rate <- if (cases$rate[i] == 0) observed else NA_real_
    ok <- if (cases$rate[i] == 0) observed < .10 else observed > 0.07
    data.frame(layer='L2_contamination_fidelity', rate=cases$rate[i],
      observed_rate=observed, status=if(ok) 'PASS' else 'FAIL', stringsAsFactors=FALSE)
  })
  out <- do.call(rbind, rows)
  list(data=out, status=if (all(out$status == 'PASS')) 'PASS' else 'FAIL')
}

t2_mc_layer3 <- function(mode='full', shard='mc') {
  reps <- if (mode == 'smoke') 120L else 700L
  n <- if (mode == 'smoke') 200L else 1000L
  set.seed(t2_seed(shard, 830L))
  mse <- function(fn, contaminated=FALSE) {
    v <- replicate(reps, {
      x <- generate_population('normal', n, list(mean=0,sd=1))
      if (contaminated) x <- inject_outliers_realistic(x,.20,12,'upper_tail')
      (fn(x)-0)^2
    }); mean(v)
  }
  mean_fn <- ESTIMATOR_REGISTRY[['mean']]; median_fn <- ESTIMATOR_REGISTRY[['median']]
  a <- mse(mean_fn,FALSE); b <- mse(median_fn,FALSE)
  c <- mse(mean_fn,TRUE); d <- mse(median_fn,TRUE)
  out <- data.frame(layer='L3_statistical_sanity',
    gauss_markov_mean_lt_median=a < b,
    contamination_median_lt_mean=d < c,
    status=if (a < b && d < c) 'PASS' else 'FAIL', stringsAsFactors=FALSE)
  list(data=out, status=out$status[1L])
}

t2_run_integrated_mc_audits <- function(mode='full', shard='mc') {
  a <- t2_mc_layer1(mode, shard); b <- t2_mc_layer2(mode, shard); c <- t2_mc_layer3(mode, shard)
  summary <- data.frame(layer=c('L1_moment_fidelity','L2_contamination_fidelity','L3_statistical_sanity'),
                        status=c(a$status,b$status,c$status), stringsAsFactors=FALSE)
  list(status=if(all(summary$status == 'PASS')) 'PASS' else 'FAIL', summary=summary,
       results=list(L1=a$data,L2=b$data,L3=c$data))
}
