# T3 B3 paired benchmark tournament

This analysis reuses the frozen Discovery weights and the score artifacts already
produced by Actions. It does not regenerate Monte Carlo data or retrain Discovery.
The scoring target remains the known population mean in synthetic stages and the
frozen sample-mean proxy in Real-world. The arithmetic-mean estimator is also one
of the 26 benchmark contestants, so it is compared once as part of that panel.

## What is compared

For each of the four frozen evolutionary weight vectors, the tournament compares
its paired MSE and q95 losses separately against every one of the 26 classical
estimators, including `mean`. It uses evaluation seeds as independent units in
Held-out and Stress, and `parent_dataset_id` as the independent unit in
Real-world. Repeated training seeds, scenario cells, child series, and depth
slices are collapsed within those units before inference.

The primary BH-FDR family is the complete candidate × benchmark × metric ×
transfer-stratum panel for each stage. The output retains every evolutionary
candidate and attaches four layers to each candidate/benchmark/stratum row:

1. Joint MSE and q95 improvement with global BH-FDR support.
2. Joint MSE and q95 improvement with paired 95% intervals, before FDR.
3. MSE-only or q95-only Pareto improvement, with both FDR-supported and
   interval-supported flags.
4. The full retained candidate row, regardless of whether it wins.

Real-world scopes are empirical profile matches, not known generative-family
labels. The synthetic cross-family workflow supplies the explicit
source-family × evaluation-family transfer matrix.

## Run order using frozen Actions artifacts

1. Run **T3 B3 Discovery all-benchmark training audit** with the original and
   repair Discovery run IDs. This is descriptive training evidence only; it
   does not compute confirmatory p-values or select new weights.
2. Run **T3 B3 Frozen Cross-Family Transfer** for `heldout`, then for `stress`.
   Supply the Monte Carlo run ID and both Discovery artifact run IDs. Each run
   evaluates every source-family W on the other evaluation families.
3. Run **T3 B3 Pairwise all-benchmark confirmation** once for `heldout` and
   once for `stress`, pairing the completed within-family score run with the
   corresponding cross-family score run.
4. Let the currently active Real-world repair finish. Then run **T3 B3
   Real-world all-benchmark parent tournament** with the original Real-world
   run and the repair run. It reduces each score artifact separately, so one
   Actions runner never downloads the full raw score archive.

The new tournament outputs are additive and versioned. Existing raw scores,
checkpoints, manifests, legacy summaries, and backups remain available for
reproducibility. The new output paths are `v3_confirmatory_pairwise/*_v2`.
