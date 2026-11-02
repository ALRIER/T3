# T3 B3 paired benchmark tournament

This analysis reuses the frozen Discovery weights and the score artifacts already
produced by Actions. It does not regenerate Monte Carlo data or retrain Discovery.
The scoring target remains the known population mean in synthetic stages and the
frozen sample-mean proxy in Real-world. The arithmetic-mean estimator is also one
of the 26 benchmark contestants, so it is compared once as part of that panel.

## What is compared

For each of the four frozen evolutionary weight vectors, the tournament compares
its paired MSE and q95 losses only against two references: the own-regime
classical benchmark frozen from Discovery and `mean`. The own benchmark is the
best non-mean classical estimator for that source family and sample size under
Discovery's equal-weight normalized MSE/q95 criterion. It is selected before
Held-out, Stress, or Real-world evaluation. It uses evaluation seeds as independent units in
Held-out and Stress, and `parent_dataset_id` as the independent unit in
Real-world. Repeated training seeds, scenario cells, child series, and depth
slices are collapsed within those units before inference.

The primary BH-FDR family is the complete candidate × (own benchmark or mean) × metric ×
transfer-stratum panel for each stage. The output retains every evolutionary
candidate and attaches four layers to each candidate/benchmark/stratum row:

1. Joint MSE and q95 improvement with global BH-FDR support.
2. Joint MSE and q95 improvement with paired 95% intervals, before FDR.
3. MSE-only or q95-only Pareto improvement, with both FDR-supported and
   interval-supported flags.
4. The full retained candidate row, regardless of whether it wins.

Each stratum also reports `beats_own_and_mean_tier1` and
`beats_own_and_mean_tier2`: these are true only when the candidate passes the
corresponding joint criterion against both references.

Real-world scopes are empirical profile matches, not known generative-family
labels. The synthetic cross-family workflow supplies the explicit
source-family × evaluation-family transfer matrix.

## Run order using frozen Actions artifacts

1. Run **T3 B3 Discovery own-benchmark freeze** with the original and repair
   Discovery run IDs. It freezes one non-mean classical benchmark per family
   and sample size using Discovery data only; training comparisons remain
   descriptive and do not compute confirmatory p-values or select new W*.
2. Run **T3 B3 Frozen Cross-Family Transfer** for `heldout`, then for `stress`.
   Supply the Monte Carlo run ID and both Discovery artifact run IDs. Each run
   evaluates every source-family W on the other evaluation families.
3. Run **T3 B3 Pairwise own-benchmark confirmation** once for `heldout` and
   once for `stress`, pairing the completed within-family score run with the
   corresponding cross-family score run, and supply the own-benchmark freeze
   run ID.
4. Let the currently active Real-world repair finish. Then run **T3 B3
   Real-world own-benchmark parent tournament** with the original Real-world
   run, the repair run, and the own-benchmark freeze run. It reduces each score artifact separately, so one
   Actions runner never downloads the full raw score archive.

The new tournament outputs are additive and versioned. Existing raw scores,
checkpoints, manifests, legacy summaries, and backups remain available for
reproducibility. The new output paths are `v3_confirmatory_pairwise/*_v2`.
