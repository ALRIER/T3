# Frozen within-family parameter transfer

Discovery optimizes weights on the declared base parameterization for each
family. This add-on estimates whether those exact frozen W vectors carry to
other base-parameter rows of the same family. It does not redefine the core
regime-specific objective or select a universal estimator.

## Procedure

1. `scripts/t3_b3_parametric_transfer_mc.R` generates non-base parameter rows
   from `build_param_grids()`, using only reserved seeds 40–49 and the frozen
   321-scenario contamination grid.
2. `scripts/t3_b3_parametric_transfer_score.R` checks the MC shard and
   Discovery stage-contract hashes, then scores the four frozen engine weights
   from each of the ten Discovery seeds. It performs no tuning, refitting, or
   outcome-based candidate selection. Every score is paired against the sample
   mean component.
3. `scripts/t3_b3_parametric_transfer_inference.R` averages repeated Discovery
   fits within each independent transfer seed, tests the complete seed panel
   40–49, reports paired confidence intervals and the MSE/q95 winner taxonomy,
   and applies one BH adjustment over the entire prespecified
   family × parameter-row × sample-size × scenario × model × metric panel.

The workflow expands to 2,490 shard workloads across six families, non-base
parameter rows, ten seeds, and three sample sizes. It is intentionally a later
stage, after Discovery has produced and uploaded all frozen W artifacts. The
workflow uses the pinned T3 R container and a bounded Actions parallelism of
four so each runner remains within the six-hour job limit.

This is a transfer audit, not another optimizer comparison and not evidence
that one weight vector should work for all family parameterizations. Simulation
estimands and replication should be specified before interpreting results
(Morris et al., 2019); the intervals use paired resampling and the multiplicity
panel uses the original BH procedure (Efron & Tibshirani, 1993; Benjamini &
Hochberg, 1995).
