# T2 V3 B3 — Prospective methodology amendment (not a restatement of frozen runs)

## Outlier threshold, Section 3.5
Historical thesis V10 external empirical calibration used **unscaled** median absolute deviation, directional flags at z=3, and fallback IQR/1.349 and SD. It explicitly stated no sensitivity at 2.5/4 and that the rule was fixed before external calibration. These results must remain labeled as historical and cannot be reinterpreted as Leys' scaled MAD.

For the **new, versioned prospective experiment**, define MAD0 = median(|x-median(x)|), MAD_N = 1.4826 MAD0, and z_i=(x_i-median(x))/MAD_N. Flag abs(z_i)>2.5 (or signed upper/lower according to the preregistered tail). Use thresholds 2 and 3 *only* as sensitivity analysis. Report flagged observations, fractions, direction, status of undefined scale, and downstream changes in MSE/q95. Do not discard observations by default; distinguish diagnostic flags from simulated contamination. If MAD_N=0, report undefined and use an explicitly designated secondary diagnostic, not automatic claims of outliers. Make no retroactive changes to previous empirical findings.

Rationale: Leys, C. et al. (2013), Journal of Experimental Social Psychology 49(4):764–766, https://doi.org/10.1016/j.jesp.2013.03.013. The paper recommends MAD and a 2.5 scaled-MAD default, while acknowledging that cutoffs are ultimately judgmental. No threshold is universally optimal in skewed/heavy-tail settings.

## Prospective 321 grid
Clean anchor: 1; contaminated scenarios: 320 selected deterministically from 7 rates (1%, 2%, 5%, 10%, 15%, 20%, 30%) × 9 MAD severities (1.5,3,4.5,6,9,12,15,20,30) × 8 mechanisms. Each mechanism occurs 40 times; rates occur 45–46 times; MAD scales 35–36 times. Six generating families, training n=1000 and 500 Monte Carlo replications per scenario are preserved as a proposed *new* protocol. The prospective 321 grid is **not a superset of historical 121 scenario IDs until a mapping is verified**; do not claim exact historical continuity.

## Gates required before any new production
1. Generate and audit immutable 321-grid metadata and real Monte Carlo matrices before using new IDs.
2. Compare 121 versus 321 using *the same independently generated* evaluation panel; avoid exploiting the test panel for selection.
3. Nested 5 outer × 3 inner CV: fold refits and inner-only hyperparameter selection; stratify on contamination band, mechanism and MAD severity when metadata are present. Group related synthetic scenarios as needed to avoid dependent duplicates crossing folds.
4. Reserve a distinct, predeclared block-transfer and nearest-neighbor evaluation: mechanisms and/or MAD/severity bands held out entirely. Do not use that gate to optimize W.
5. Include all 26 benchmark estimators in scoring and full-panel Pareto; distinguish descriptive local MSE, q95, joint, Pareto, and near-gate winners from BH/FDR-confirmed winners.
6. Analyze regularization strength, weight stability, component ablation, negative controls, and DRO tail losses as separate predeclared analyses.
7. Compare algorithms on counted objective evaluations and wall-clock/CPU-hours under the same predeclared budget; deterministic simplex optimizer and uniform-weight mixture are mandatory simple controls. Fit these only to training.
8. Preregister primary winner rule, tie tolerances, multiplicity correction, bootstrap unit, and confidence intervals. No winner claims from training-only CV summaries.
9. Keep frozen Discovery run 40153358036 unchanged. The new protocol requires a versioned new Monte Carlo dataset and entirely new production.
10. Store every fit's hyperparameters, W vector, seed, fold assignment, data hashes, software version and machine resource summary.

## Implementation status
- Implemented prospective flags/sensitivity: R/02_discovery/t2_v3_b3_mad_detection.R.
- Implemented prospective design generator (metadata only): scripts/t2_v3_b3_generate_grid321.py.
- Implemented stratified partition diagnostics: R/02_discovery/t2_v3_b3_nested_folds.R.
- Implemented reusable partial diagnostic helpers for 26 benchmarks, Pareto, stability and ablation.
- NOT yet implemented end-to-end: generating 321 actual simulation shards, full group-block transfer gate, controls with common evaluation budgets, calibration of complete selection procedure and 321-based nested refitting/held-out stress. These require new versioned input contracts and execution.
