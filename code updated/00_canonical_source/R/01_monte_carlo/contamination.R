# Original contamination generation. To be validated under the revised MAD protocol.
inject_outliers_realistic <- function(sample,
                                      contamination_rate = 0.05,
                                      outlier_scale_mad = 12,
                                      type = c("upper_tail", "symmetric_t", "lower_tail", "point_mass",
                                               "clustered_upper", "clustered_symmetric",
                                               "mixture_bimodal_near", "mixture_bimodal_far"),
                                      df_t = 3,
                                      # Parameters controlling clustered 
                                      # contamination: instead of IID outlier locations,
                                      # outliers can appear in contiguous blocks
                                      # to mimic batch/systematic corruption (e.g., sensor bursts
                                      # or logging glitches). cluster_min/max 
                                      # set the typical block length and affect dependence structure.
                                      # clustered contamination knobs
                                      cluster_min = 3L,
                                      cluster_max = 12L,
                                      # Parameters controlling bimodal mixture 
                                      # contamination: generates outliers from two
                                      # modes around the median at ±delta, 
                                      # where delta scales with outlier_scale_mad*MAD. “near” vs “far”
                                      # only changes the distance multiplier, 
                                      # allowing controlled tests of moderate vs extreme bimodality.
                                      # mixture knobs (distance multiplier 
                                      #                relative to outlier_scale_mad * MAD)
                                      mixture_near_factor = 0.5,
                                      mixture_far_factor  = 1.5) {
  type <- match.arg(type)
  n <- length(sample)
  if (!n) return(sample)
  k <- ceiling(n * contamination_rate)
  if (k <= 0) return(sample)
  
  # Computes robust location/scale anchors (median and MAD) to parameterize outlier
  # magnitude in a distribution-agnostic way. If MAD is zero/invalid (e.g., constant samples), it falls
  # back to SD, and finally to 1, preventing degenerate scaling and ensuring contamination is applied.
  med  <- stats::median(sample)
  madv <- stats::mad(sample, constant = 1, na.rm = TRUE)
  if (!is.finite(madv) || madv <= 0) {
    # fallback: robust-ish SD (if sd=0, use 1 to avoid fixed-point scaling)
    sdv <- stats::sd(sample)
    madv <- if (is.finite(sdv) && sdv > 0) sdv else 1
  }
  
  # Helper to select which indices will be contaminated. In IID mode, it draws k unique
  # positions uniformly. In clustered mode, it builds one or more contiguous blocks of indices to mimic
  # temporally/spatially correlated corruption, then trims/fills to reach exactly k unique indices.
  # --- helper: pick k indices either IID or in contiguous clusters -------
  pick_indices <- function(n, k, clustered = FALSE,
                           cluster_min = 3L, cluster_max = 12L) {
    if (!clustered) {
      return(base::sample.int(n, size = k, replace = FALSE))
    }
    cluster_min <- max(1L, as.integer(cluster_min))
    cluster_max <- max(cluster_min, as.integer(cluster_max))
    take <- integer(0)
    guard <- 0L
    while (length(take) < k && guard < 2000L) {
      guard <- guard + 1L
      L <- base::sample(seq.int(cluster_min, cluster_max), size = 1L)
      start <- base::sample.int(n, size = 1L)
      idx <- start + seq.int(0L, L - 1L)
      idx <- idx[idx <= n]
      take <- unique(c(take, idx))
    }
    if (length(take) > k) take <- base::sample(take, k, replace = FALSE)
    if (length(take) < k) {
      rest <- setdiff(seq_len(n), take)
      if (length(rest)) take <- c(take, base::sample(rest, min(k - length(take), length(rest))))
    }
    take
  }
  
  # Determines whether clustered index selection is used and draws the final set of
  # contaminated positions. Clustered variants intentionally introduce dependence in the contamination
  # pattern; non-clustered variants keep contamination IID. This separation enables controlled studies
  # of estimator robustness under different corruption structures.
  clustered <- type %in% c("clustered_upper", "clustered_symmetric")
  idx <- pick_indices(n, k, clustered = clustered,
                      cluster_min = cluster_min, cluster_max = cluster_max)
  
  # Generates replacement values for the chosen indices according to the contamination
  # mechanism. Upper/lower tail use one-sided Gaussian magnitudes; symmetric_t uses heavy tails; point
  # mass forces identical extreme values; bimodal mixtures create two outlier modes around ±delta.
  # --- generate replacement values --------------------------------------
  if (type %in% c("upper_tail", "clustered_upper")) {
    bump <- abs(stats::rnorm(length(idx)))
    outlier_values <- med + outlier_scale_mad * madv * bump
    
  } else if (type %in% c("lower_tail")) {
    bump <- abs(stats::rnorm(length(idx)))
    outlier_values <- med - outlier_scale_mad * madv * bump
    
  } else if (type %in% c("symmetric_t", "clustered_symmetric")) {
    bump <- stats::rt(length(idx), df = df_t)
    outlier_values <- med + outlier_scale_mad * madv * bump
    
  } else if (type == "point_mass") {
    outlier_values <- rep(med + outlier_scale_mad * madv, length(idx))
    
  } else if (type %in% c("mixture_bimodal_near", "mixture_bimodal_far")) {
    # Two-mode mixture centered around +/- delta from the median.
    # "near" vs "far" only changes delta (distance between modes).
    factor <- if (type == "mixture_bimodal_near") mixture_near_factor else mixture_far_factor
    delta  <- outlier_scale_mad * madv * factor
    # random sign to pick component
    sgn <- ifelse(stats::runif(length(idx)) < 0.5, -1, 1)
    outlier_values <- stats::rnorm(length(idx), mean = med + sgn * delta, sd = madv)
    
  } else {
    stop(sprintf("inject_outliers_realistic: unsupported type '%s'", type))
  }
  
  # Applies the contamination by overwriting selected sample positions with the
  # generated outlier values. This preserves sample size while altering the empirical distribution in
  # a controlled manner, allowing consistent comparison of estimator behavior under fixed corruption
  # rates and mechanisms.
  sample[idx] <- outlier_values
  sample
}

