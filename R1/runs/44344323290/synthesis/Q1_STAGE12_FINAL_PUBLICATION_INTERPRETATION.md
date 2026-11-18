# Q1 Stage 12 final calibration decision

The nominal crossed-seed t9+Holm test failed a synthetic global-null FWER calibration audit. We corrected the known-truth synthetic inference on the archived **frozen method estimands** using empirically calibrated null distributions and a conservative order-statistic global minP threshold. The original 4,096 training-null replicates were supplemented with 16,384 **new, separately seeded** null calibration replicates for each of 18 population/sample-size blocks, providing 20,480 null replicates for 216 contrasts. The prior, disjoint 4,096-replicate validation set was reused without re-running, independently testing global and mixed nulls, and original-effect alternatives.

Within-model global and mixed-null independent 5% FWER gate: **PASS**. Independent pointwise 95% coverage gate: **PASS**.

Interpretation must remain conditional: model-based synthetic checks do **not** validate nominal error/coverage for the full original optimizer training, nested HPO and weight-selection process. Original R1 confirmatory tests were not changed; all 216 adjusted original-contrast sensitivity flags are explicitly posthoc. Do not claim distribution-free FWER or fully selection-aware coverage in the journal manuscript.

Use the accompanying 216-contrast, 648-contrast, global table, and exact source lineage for transparent Methods/Results reporting.
