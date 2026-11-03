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
   outcome-based candidate selection. Every score is paired against the
   Discovery-frozen best non-mean classical estimator for that scenario and
   against the sample mean.
3. `scripts/t3_b3_parametric_transfer_inference.R` averages repeated Discovery
   fits within each independent transfer seed, tests the complete seed panel
   40–49, reports paired confidence intervals and the MSE/q95 winner taxonomy,
   and applies one BH adjustment over the entire prespecified
   family × parameter-row × sample-size × scenario × model × metric panel.

The workflow covers 2,490 identities across six families, non-base parameter
rows, ten seeds, and three sample sizes. `n=3000` is divided into two disjoint
scenario checkpoints; `n=200` and `n=1000` each retain the full scenario panel
in one checkpoint. This yields 3,320 score shards. The stage runs after
Discovery has uploaded all frozen W artifacts, using the pinned T3 R container
and `max-parallel: 32` per workflow matrix.

This is a transfer audit, not another optimizer comparison and not evidence
that one weight vector should work for all family parameterizations. Simulation
estimands and replication should be specified before interpreting results
(Morris et al., 2019); the intervals use paired resampling and the multiplicity
panel uses the original BH procedure (Efron & Tibshirani, 1993; Benjamini &
Hochberg, 1995).
