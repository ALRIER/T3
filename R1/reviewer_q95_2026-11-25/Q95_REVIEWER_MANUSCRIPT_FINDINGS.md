# Q95 reviewer evidence: original 500-replicate precision vs conditional between-method uncertainty

**Source:** original T3/R1 verified archives only. No new Monte Carlo, bootstrap, optimizer, or HPO runs.

The per-scenario type-8 Q95 estimate is based on 500 original MC replicate errors. Its order-statistic interval width is a *within-MC loss-quantile precision diagnostic*, not a confidence interval for the paired DE-versus-control gain or any other between-method contrast.

In the 18 original family-size blocks, DE has 13 descriptive MSE-and-Q95 improvements over the frozen convex-MSE control. 5 DE Q95 improvements are positive but smaller than 5%.

The original paired-control intervals and Holm labels have not been recalibrated for full optimizer selection. The 108 matched method-pair Q95 contrasts are separately examined against the existing **post hoc fixed-score surrogate** pointwise and simultaneous CI bounds, with a descriptive <5% effect-size split.

### Descriptive Q95 method-pair comparison

| Magnitude of symmetric original Q95 contrast | Contrasts | Surrogate pointwise 95% CI excludes 0 | Surrogate simultaneous 216-contrast 95% CI excludes 0 |
| --- | ---: | ---: | ---: |
| <5% | 29 | 12 | 0 |
| >=5% | 79 | 76 | 42 |

### Interpretation constraints

1. A small descriptive block gain can coexist with broad scenario-level Q95 quantile uncertainty. Their percentage scales have different denominators and **are not** interchangeable inferential intervals.
2. The original control CI uses ten independent evaluation seeds. It must be labeled *original conditional paired inference*, not fully calibrated selection-aware inference.
3. The fixed-score surrogate calibration applies only to archived frozen method scores, not the original nested optimizer/HPO weight selection. It cannot be transferred to control or Q2--Q4 panels.
4. No new results justify a new claim of confirmatory optimizer superiority or a prospective universal weight selector.

### Reproducibility

Input hashes, all 18 DE-versus-convex original CI comparisons, and the complete 108 crossed method-pair Q95 results are published alongside this summary.
