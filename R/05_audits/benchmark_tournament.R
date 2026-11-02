# Unified paired tournament for frozen weighted estimators.
# Scores must already be reduced to one row per independent evaluation unit,
# stratum, and model. Positive loss differences favor the benchmark.
t3_pairwise_tournament <- function(unit_scores, stage, unit_col,
                                   group_cols, alpha=0.05) {
  if (!stage %in% c('discovery','heldout','stress','realworld')) stop('Invalid tournament stage')
  required <- unique(c(unit_col, group_cols, 'model', 'mse', 'q95'))
  if (!is.data.frame(unit_scores) || !all(required %in% names(unit_scores)))
    stop('Tournament unit-score schema is incomplete')
  if (any(!is.finite(unit_scores$mse)) || any(!is.finite(unit_scores$q95)))
    stop('Tournament scores must be finite')
  if (!length(ESTIMATOR_NAMES) || length(ESTIMATOR_NAMES) != 26L || !'mean' %in% ESTIMATOR_NAMES)
    stop('Tournament requires the frozen 26-estimator registry including mean')
  if (!is.finite(alpha) || alpha <= 0 || alpha >= 1)
    stop('Invalid tournament inference settings')

  # Candidate engines are the four evolutionary frozen W*. Controls remain in
  # the raw score archive and are not counted as evolutionary winners.
  engine_from_id <- function(x) {
    x <- tolower(as.character(x))
    engines <- c('dirichlet','nsga2','de','ga')
    tokens <- strsplit(gsub('[^a-z0-9]+','_',x), '_', fixed=TRUE)[[1L]]
    tokens <- setdiff(tokens,c('normal','lognormal','weibull','invgauss','exgaussian','exwald'))
    hit <- engines[engines %in% tokens]
    if (length(hit)) hit[[1L]] else NA_character_
  }
  unit_scores$candidate_engine <- vapply(unit_scores$model, function(m)
    if(m %in% ESTIMATOR_NAMES) NA_character_ else engine_from_id(m), character(1))
  candidate_rows <- unit_scores[!is.na(unit_scores$candidate_engine), , drop=FALSE]
  if (!nrow(candidate_rows)) stop('No frozen evolutionary W* candidates found')
  key <- c(group_cols, unit_col, 'model')
  if (anyDuplicated(unit_scores[key])) stop('Duplicate score per independent unit/model/stratum')
  strata <- unique(unit_scores[group_cols])
  results <- list(); ri <- 0L
  for (s in seq_len(nrow(strata))) {
    in_stratum <- rep(TRUE, nrow(unit_scores))
    for (nm in group_cols) in_stratum <- in_stratum & unit_scores[[nm]] == strata[[nm]][s]
    z <- unit_scores[in_stratum, , drop=FALSE]
    candidate_ids <- unique(z$model[!is.na(z$candidate_engine)])
    unit_ids <- unique(z[[unit_col]])
    # Every independent unit must contain all 26 classical benchmarks.
    for (u in unit_ids) {
      have <- as.character(z$model[z[[unit_col]] == u])
      if (!all(ESTIMATOR_NAMES %in% have)) stop('An evaluation unit lacks one or more of the 26 benchmarks')
    }
    for (candidate_id in candidate_ids) {
      candidate <- z[z$model == candidate_id, c(unit_col,'mse','q95'), drop=FALSE]
      if (nrow(candidate) != length(unit_ids)) stop('Candidate missing an independent evaluation unit')
      for (benchmark in ESTIMATOR_NAMES) {
        reference <- z[z$model == benchmark, c(unit_col,'mse','q95'), drop=FALSE]
        pair <- merge(candidate, reference, by=unit_col, suffixes=c('_candidate','_benchmark'), sort=TRUE)
        if (nrow(pair) != length(unit_ids)) stop('Candidate/benchmark pairing is incomplete')
        for (metric in c('mse','q95')) {
          d <- pair[[paste0(metric,'_candidate')]] - pair[[paste0(metric,'_benchmark')]]
          b <- pair[[paste0(metric,'_benchmark')]]
          gain_pct <- 100 * (b - pair[[paste0(metric,'_candidate')]]) / pmax(abs(b), .Machine$double.eps)
          if (length(d) < 3L) stop('At least three independent units are required')
          if (all(d == d[[1L]])) {
            p <- if (d[[1L]] < 0) 0 else 1
            ci <- rep(d[[1L]], 2L)
          } else {
            p <- stats::t.test(d, alternative='less')$p.value
            ci <- stats::t.test(d, conf.level=1-alpha)$conf.int
          }
          gain_ci <- if(all(gain_pct==gain_pct[[1L]])) rep(gain_pct[[1L]],2L) else
            stats::t.test(gain_pct,conf.level=1-alpha)$conf.int
          ri <- ri + 1L
          row <- data.frame(stage=stage, candidate_model=candidate_id,
            candidate_engine=engine_from_id(candidate_id), benchmark=benchmark,
            metric=metric, independent_units=length(d), difference=mean(d),
            ci_lower=ci[[1L]], ci_upper=ci[[2L]], gain_pct=mean(gain_pct),
            gain_pct_lower=gain_ci[[1L]], gain_pct_upper=gain_ci[[2L]],
            p_value=p, all_26_panel=TRUE, mean_in_panel=benchmark=='mean',
            inference_unit=unit_col, ci_method='paired_evaluation_unit_t_interval',
            stringsAsFactors=FALSE)
          for (nm in group_cols) row[[nm]] <- strata[[nm]][s]
          results[[ri]] <- row
        }
      }
    }
  }
  metric_rows <- do.call(rbind, results)
  # This is the sole primary multiplicity family: every frozen W* x each of
  # the 26 benchmarks x both metrics x all reported transfer strata in stage.
  metric_rows$q_value_global <- stats::p.adjust(metric_rows$p_value, method='BH')
  metric_rows$passes_bh <- metric_rows$q_value_global <= alpha
  ids <- c('stage','candidate_model','candidate_engine','benchmark',group_cols,
           'independent_units','inference_unit','all_26_panel','mean_in_panel')
  wide <- reshape(metric_rows[,c(ids,'metric','difference','ci_lower','ci_upper',
    'gain_pct','gain_pct_lower','gain_pct_upper','p_value','q_value_global','passes_bh')],
    idvar=ids, timevar='metric', direction='wide')
  if (!all(c('ci_upper.mse','ci_upper.q95','passes_bh.mse','passes_bh.q95') %in% names(wide)))
    stop('Incomplete paired MSE/q95 tournament panel')
  win_mse <- wide$ci_upper.mse < 0
  win_q95 <- wide$ci_upper.q95 < 0
  fdr_mse <- win_mse & wide$passes_bh.mse
  fdr_q95 <- win_q95 & wide$passes_bh.q95
  wide$tier1_joint_mse_q95_bh_fdr <- fdr_mse & fdr_q95
  wide$tier2_joint_mse_q95_ci <- win_mse & win_q95
  wide$tier3_mse_only_bh_fdr <- fdr_mse & !win_q95 & wide$difference.q95 >= 0
  wide$tier3_q95_only_bh_fdr <- fdr_q95 & !win_mse & wide$difference.mse >= 0
  wide$tier3_mse_only_ci <- win_mse & !win_q95 & wide$difference.q95 >= 0
  wide$tier3_q95_only_ci <- win_q95 & !win_mse & wide$difference.mse >= 0
  wide$tier3_pareto_bh_fdr <- wide$tier3_mse_only_bh_fdr | wide$tier3_q95_only_bh_fdr
  wide$tier3_pareto_ci <- wide$tier3_mse_only_ci | wide$tier3_q95_only_ci
  # Tier 4 means every frozen evolutionary candidate remains in the reporting
  # universe; it is never a retrospective winner filter.
  wide$tier4_retained_candidate <- TRUE
  wide$practical_mse <- wide$gain_pct.mse >= ga_config$practical_gain_pct
  wide$practical_q95 <- wide$gain_pct.q95 >= ga_config$practical_gain_pct
  list(metrics=metric_rows, taxonomy=wide,
       manifest=data.frame(stage=stage,unit=unit_col,benchmarks=26L,
         candidate_engines=paste(sort(unique(wide$candidate_engine)),collapse=';'),
         primary_bh_family='all candidate x benchmark x metric x transfer strata',
         alpha=alpha,ci_method='paired_evaluation_unit_t_interval',
         code_revision=Sys.getenv('GITHUB_SHA','unverified-local'),
         workflow_run_id=Sys.getenv('GITHUB_RUN_ID','local'),
         stringsAsFactors=FALSE))
}
