# RQ3 — Verified existing synthetic-transfer retabulation

**Status:** Original completed evidence only. No additional Monte Carlo simulations, optimizer fitting, seed generation, refitting, selection, or new statistical tests.

## Scope of the refined question

The analysis asks how original Discovery-frozen mean-estimator combinations transfer to generating families that each individual source-family model did not train on and to 80 independently reserved near/far-bimodal contamination scenarios. All six generating families are known to the experiment; **source-unseen** refers to the particular frozen model's training exposures, not a previously unknown family in the overall study. Isolated within-family parameter-change inference is excluded from the primary RQ3 scope.

## Permanent retabulation sources and outputs

- `RQ3_SYNTHETIC_TRANSFER_SCOPE_5_VALIDATED.csv` contains 5 unique original panels/analysis units: Held Out individual frozen candidates versus selected classical reference, Held Out four-engine pooled results versus selected classical and versus sample mean, and original historical and fresh Stress candidate-level panels.
- `RQ3_ORIGINAL_DIRECTED_SOURCE_DESTINATION_72.csv` contains all 72 original (reference policy × six training source families × six evaluation destination families) original Held Out engine-aggregated cells reconstructed from **exactly 288 original engine-level ledger rows**, with four engines and 2,892 eligible engine-scenario contrasts per cell.
- Original read-only sources: `Q3/B_cross_family/Q3_B_DIRECTED_288_ENGINE_TRANSFERS.csv`, `Q3/B_cross_family/Q3_B_ORIGINAL_ENGINE_SCOPE_RATES.csv`, `Q3/B_cross_family/Q3_B_ORIGINAL_INDIVIDUAL_WEIGHT_TRANSFER.csv`, `Q3/C_structural_stress/Q3_C_ORIGINAL_STRESS_TRANSFER_SCOPE.csv`.
- Original four-way source SHA/paths and audit conditions are recorded in `Q4/reframed_RQ4/Q3_Q4_EXISTING_EVIDENCE_AUDIT.json`; the original files were not edited.

## Independent aggregation checks

- Each of the six within-family source=destination Held Out engine cells contains 2,892 eligible units; each of the 30 cross-family cells contains 2,892. Therefore within = 17,352 and cross = 86,760 per original benchmark policy.
- Selected classical pooled-engine joint supported contrasts: within 73/17,352 and cross 357/86,760.
- Sample-mean pooled-engine joint supported contrasts: within 9,672/17,352 and cross 48,377/86,760.
- Original individual-candidate joint selected-classical supported contrasts: within 877/173,520 and cross 5,069/867,600. **Do not merge candidate-level and pooled-engine-level denominators or hypotheses.**
- Original historical Stress: 0/57,600 source matched and 6/288,000 cross family. Fresh Stress: 1,799/57,600 source matched and 4,913/288,000 cross family. Different seeds, generating parameters, and correction families prevent a one-factor causal inference.
- Strong-classical pooled-engine off-diagonal counts by destination: Inverse Gaussian 215, Weibull 106, Ex Wald 27, Lognormal 9, Normal 0, Ex Gaussian 0. **The zeros are pooled-engine-scale original conditional evidence, not proof that every individual frozen candidate is unsuccessful at that destination.**

## Claim boundary and manuscript linkage

Original joint CI/BH labels remain conditional on the archived tests and declared adjustment scopes. They are **not** proven fully optimizer-selection-aware error guarantees or independent six-family replications. The complete revised manuscript is `ALRIER/Genetic_Algorithms/main/manuscript/main.tex`, subsection `sec:q3_results`, tables `tab:results_scope_rates` and `tab:q3_directed_engine_matrix`, and existing retained Held Out/Stress figures. This is re-analysis of completed evidence, not a new scientific experiment.
