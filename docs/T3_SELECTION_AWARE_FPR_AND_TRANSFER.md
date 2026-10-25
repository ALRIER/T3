# T3: full-pipeline false-positive calibration and out-of-neighborhood transfer

## Mandatory design
1. Freeze the discovery training data, family/seed/fold boundaries, candidate hyperparameter search space, 26 classical baselines, common W-selection criterion, decision threshold and excluded transfer scenarios before looking at confirmation data.
2. For each **null replay**, generate independent null training and confirmation samples; rerun all optimizer tuning, Discovery model selection, common W choice and winner selection. Record model statistics on the replay's independent null confirmation data. Pass `reselected=TRUE` and `independent_confirmation=TRUE` only when the execution manifests prove these steps. Reusing original W invalidates the test.
3. Pass each replay's full list of model statistics to `t3_calibrate_selection_fpr`. It uses empirical +1 Monte Carlo p values and familywise maxT adjustment over the candidate models. An observed statistic must increase with evidence against the null. The minimum 19 replays is only a smoke threshold; scientific reporting should predefine much larger replication counts (e.g. 999 or more) for useful 0.05 resolution.
4. Define excluded mechanisms and (rate, scale) contamination neighborhoods *prospectively*. Use `t3_transfer_partition` before fitting and fit on `in_training=TRUE` only. Keep disjoint clean/held-out sampling seeds. Score all excluded group scenarios and call `t3_transfer_score`.
5. Report each mechanism-only, neighborhood-only and both-excluded group separately, with MSE and q95, by sample size, family and seed. Predeclare pass/fail and uncertainty methodology before examining performance. Include all 26 baselines on the same confirmation samples.
6. This module is fail-closed analysis infrastructure, **not proof** that expensive null-discovery replays or out-of-support training have run. Production approval requires the replay runner, provenance receipts, workload budget and CI integration, plus passing full 321-scenario contract gate. Never silently use old 121-scenario artifacts.

## Known restrictions
The `t3_calibrate_selection_fpr` caller is responsible for recording and verifying proof of refitting, data independence and null validity. Two Boolean flags cannot establish provenance; production gate must independently check hashes/seeds and selection receipts.
The procedures must be validated under the scientifically stated composite null; maxT calibration only provides the intended familywise guarantee if null-generation and dependence assumptions are satisfied.
