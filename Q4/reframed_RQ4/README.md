# RQ4 — Complete original parent-level empirical and benchmark-policy retabulation

**Status:** Exactly the original completed Real World evidence; no new simulations, fitting, independently rerun empirical statistics, altered target, benchmark reselection, or split-half target experiment.

## Source audit

- Original source file `Q3/E_real_world/Q3_E_COMPLETE_ORIGINAL_24_COMPARATOR_SCOPE_TABLE.csv` has **24** independently recorded summary combinations: source/destination benchmark-family indexing × primary/secondary destination-profile panel × three transfer scopes (cross-family, within-family neighborhood, within regime) × two reference comparators (Discovery-frozen classical and sample mean).
- Every one of the 24 count groups reconciles **exactly** to `Q3/E_real_world/Q3_E_COMPLETE_ORIGINAL_ENGINE_SOURCE_DESTINATION.csv`, which contains **1,264** original engine/source/destination subgroup summary rows.
- All **8** original cross-family source/destination-policy × primary/secondary × classical/sample-mean entries are reconciled with `Q3/E_real_world/Q3_E_ORIGINAL_8_POLICY_PARENT_LEVEL_EVIDENCE.csv`.
- `RQ4_ORIGINAL_24_POLICY_SCOPE_AUDITED.csv` retains each original claim, full original denominator, minimum contributing independent-parent count, and adds *only* calculated descriptive and supported percentages plus correct unit labels.
- `RQ4_ORIGINAL_12_SOURCE_DESTINATION_POLICY_PAIRS.csv` displays all 24 original entries as 12 same-panel/scope/comparator pairs, with separate source-indexed and approximate destination-indexed classical-reference counts. It does not report an invented paired significance test of the policy difference.
- Original blob hashes, counts and interpretation stop conditions are preserved in `Q3_Q4_EXISTING_EVIDENCE_AUDIT.json`; all original outputs remain untouched.

## Scientific units and supported claims

The independent empirical inferential unit is one original parent dataset; the inventory has **642** parents. The original response profiles can yield multiple child variables, subset depths, seeds and candidate contrasts per parent. Therefore 600, 720, 2,040, 2,400 and 3,000 are **parent-aggregated candidate-contrast denominators, NOT independent parent counts**. The original `independent_parent_count_min` is the recorded minimum number of contributing independent parents in a stratum, not a new parent-level inference computed by this retabulation. Some secondary strata have only **6** independent parents and their original normal-theory inference is correspondingly limited.

The external target is the arithmetic mean of the observed subset fixed before resampling, **not** a known population mean. Empirical destination-family assignment is an outcome-blind approximate proxy for family, **not** a known data-generating distribution. Source-indexed versus destination-indexed policies change the original classical comparator, not candidate weights, samples, or the empirical target.

In primary cross-family transfer: selected classical comparator **591/600** descriptive joint wins under both indexings; sample mean **40/600**. In secondary destination-profile cross-family transfer: source-indexed classical **1,661/2,040**; destination-indexed classical **1,563/2,040**; sample mean **200/2,040** under both indexing labels. Their difference is descriptive; the original aggregate summaries do not supply a valid matched-significance test of the change.

**All 24** original policy/scope combinations have **zero** jointly favorable original parent-level 95% interval and **zero** jointly favorable original BH+CI tests. This does not establish zero effect or equality of model performance. It means that the original completed evidence is descriptive rather than independently confirmatory for a joint MSE/Q95 advantage in those panels. The original full-pipeline optimizer-selection FDR/coverage guarantee is also unverified.

## Manuscript linkage and remaining future work

The canonical paper is `ALRIER/Genetic_Algorithms/main/manuscript/main.tex`, subsection `sec:q4_results`, original Real World table `tab:rw_xfamily_recovered`, complete paired 24-cell policy table `tab:q4_full_24_policies`, and original assigned-profile figure `fig:rw_xfamily_profiles`. The opposite-half external target and isolated within-family parameter transfer are separately documented **future** validation options, not primary Q4 or Q3 evidence.

**Audit limitation:** The original parent-level CI/BH labels and minimum-parent counts are checked for consistency across independently stored summary tables and their source metadata. This does not amount to reconstructing every original individual parent observation or independently rerunning its statistical test. Claiming so would exceed what this retabulation verifies.
