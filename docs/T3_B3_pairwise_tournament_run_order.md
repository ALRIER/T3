# T3 B3 paired benchmark tournament

This analysis reuses the frozen Discovery weights and the score artifacts already
produced by Actions. It does not regenerate Monte Carlo data or retrain Discovery.
The scoring target remains the known population mean in synthetic stages and the
frozen sample-mean proxy in Real-world. The arithmetic-mean estimator is also one
of the 26 benchmark contestants, so it is compared once as part of that panel.

## What is compared

For each of the four frozen evolutionary weight vectors, the tournament compares
its paired MSE and q95 losses only against two references: the best non-mean
classical benchmark frozen for the target family × scenario × sample-size cell,
and `mean`. Discovery selects that classical estimator using its equal-weight
normalized MSE/q95 criterion; the map is fixed before Held-out and Real-world
scoring. Stress selects its scenario-specific comparator from Stress seeds
20–24 and confirms only on disjoint seeds 25–29.

Held-out and Stress use independent evaluation seeds as units. Real-world keeps
`depth` (`full`, `body_10_90`, and, when eligible, `upper_tail`) as an explicit
stratum. It produces two views: (1) a conditional within-parent/child × depth
analysis across independently seeded bootstrap draws, and (2) a between-parent
analysis that averages repeated seeds and child series within each
`parent_dataset_id` before inference. The second view uses independent parent
datasets as units. Neither view counts the 500 inner bootstrap draws, child
series, depths, nor repeated Discovery training seeds as independent datasets.
The within-dataset conditional panel uses the ten independent Real-world seed
summaries for uncertainty conditional on that parent/child; its `bh_panel_id` is
separate from the primary between-parent panel because it answers a different
question. The parent-cluster panel is the inferential basis for claims across
datasets. A parent/scenario/depth cell with fewer than three independent parents
retains descriptive gains but has no p-value, confidence interval, or BH claim.
Real-world family names identify the outcome-blind Discovery family used for
profile matching; the empirical profile and matched scenario are reported as
destinations/proxies, not as known data-generating families.

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
   Discovery run IDs. It freezes one non-mean classical benchmark per family,
   scenario, and sample size using Discovery data only; training comparisons remain
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
reproducibility. The new output paths are `v3_confirmatory_pairwise/*_v3`. The
Real-world output includes `within_dataset_depth_inference.csv` and
`within_dataset_depth_taxonomy.csv` for conditional parent/child analyses,
plus `four_tier_winner_matrix.csv` for parent-cluster inference. The latter is
the table to use for generalization claims across independent datasets. Both
retain source family, matched destination/profile, transfer scope, scenario,
sample size, depth, benchmark identity, effect/gain, confidence interval, and
BH-FDR q-value for cells with enough independent units.
