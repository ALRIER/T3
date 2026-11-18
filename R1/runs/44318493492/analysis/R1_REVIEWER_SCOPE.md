# R1 crossed-seed reviewer analysis

Input: the 18 immutable per-candidate R1 Held Out panels from run 44310024979. Each 10-by-10 training/evaluation grid is paired across methods, and both seed dimensions are resampled jointly by axis, with the 241 support scenarios fixed.

The balanced crossed random-intercept moment estimate uses ten seed groups per axis. Its t(9) p-values and global Holm column are approximate **sensitivity** diagnostics, not guaranteed nominal familywise calibration. Percentile bootstrap CIs are also exploratory with only ten seed groups. A negative estimated variance component is truncated to zero and flagged per contrast.

Joint uncertainty compares MSE and Q95 on the SAME bootstrapped seed cells. Two one-sided lower bounds at 97.5% are Bonferroni-corrected only **within each pair and direction**. Thresholds 0%, 1%, and 5% were proposed after earlier results existed and are not preregistered. They cannot substitute for globally corrected multi-pair, selection-aware testing.

Monte Carlo replicate-level Q95 error, true nominal CI coverage, and deterministic controls cannot be established from this aggregate panel. The archive-inspection stage maps available source material for those questions.

No original simulation, weight optimization, frozen model selection, or scoring is repeated.
