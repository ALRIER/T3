# T3 B3 — External Generalization, Inferential Robustness, and Regime Identification

**Scope:** This is the post–Real World stage described in [T3 issue #1](https://github.com/ALRIER/T3/issues/1). It does **not** replace or restart Real World scoring, Discovery, Held Out, or Stress. Every scientific phase is subject to an immutable-input verification gate. The code preflight may execute independently; publication evidence must await the final Real World reviewer.

## Implemented reproducible modules

| Module | Executable code | Scientific contract |
| --- | --- | --- |
| Independent-parent replication and inference | `scripts/t3_b3_post_realworld_audit.py parent-inference` | Requires all 1,260 supplemental scorer checkpoints merged by original recovery final reviewer, exact 720 W and parent-ID provenance. Produces paired parent bootstrap intervals, effect sizes, supplementary BH scopes separate by empirical target and comparator. |
| CI coverage / multiplicity diagnostic | `scripts/t3_b3_post_realworld_audit.py interval-coverage` | Runs Gaussian, heavy-tailed t3, contaminated and parent-dependent synthetic coverage worlds. Compares parent-t, cluster bootstrap and demonstrably invalid child-independent intervals. This is a **diagnostic of the inference procedure** and NOT full-pipeline selected-W coverage. |
| Hyperparameter stability audit | `scripts/t3_b3_post_realworld_audit.py hyperparameters` | Requires an **audited export** from the original frozen Discovery RDS for all 720 individually trained units with `family,sample_n,training_seed,engine,frozen_weight_sha256,objective_budget,tuning_signature,termination_reason`. The export must be generated from frozen training metadata, never reconstructed from Real World outcomes. |
| Regime identification and recommendation | `scripts/t3_b3_post_realworld_regime.py crossfit` | Requires paired independent-parent holdout effects and outcome-blind parent covariates. Uses disjoint 5-fold parent splits; uncertainty and abstention revert to mean; reports parent-level regret and coverage. **Exploratory engine-level policy only**; before publication-grade recommendation, replace engine averages with a predeclared single frozen W/benchmark per regime and test on additional untouched parent sources. |
| Full-pipeline null replay | `scripts/t3_b3_post_realworld_null_replay.py` and `scripts/t3_b3_post_realworld_audit.py null-provenance` | An **execution adapter and strict verifier** for an experiment-native runner. Each null world MUST regenerate null data and rerun training, tuning, frozen W selection, all 26 classics, independent confirmation and original selection/BH. The adapter refuses a fixed-W shuffle or unverifiable fake output. **Native null-world generative and optimizer runner still requires scientifically justified configuration before this expensive test can run.** |

## Complete experiment gates

0. Real World recovery **must be complete**: original run 42390283887 retained 1,248 immutable valid score artifacts; recovery run 43098925126 is expected to add exactly 12 missing score artifacts, then produce six source-family analyses, global supplemental inference and a final reviewer. This is a checkpoint claim, not a claim that the reviewer has already passed.
1. Before using any Real World-derived outcome in a policy, freeze the parent IDs, source domain, analytic split, target policy, leakage prohibitions, candidate universe, practical gain threshold, uncertainty/abstention thresholds and multiplicity plan. Use the population-independent parent as the inferential unit. Keep a separate manuscript claim table for confirmatory vs supplementary/exploratory evidence.
2. Coverage under known-mean simulation: executed diagnostic supports a test of interval mechanics, **not** a complete assessment of the learned estimator process. If selected-model coverage is claimed, use the original Monte Carlo generator with all training/selection steps within each replicate.
3. Null calibration is a separate expensive computational module: generation under a justified null and **full training and tuning** are mandatory. The native per-null training/scoring command must be pinned and scientifically audited before adding a full Actions matrix (at most 22 parallel, less than 6 hours per world). Merely setting an environment variable on the existing scorer is NOT enough.
4. Automatic recommendation requires an additional **untouched external-parent test** to confirm an actual frozen W or frozen classical fallback policy. Current cross-fitting is a development diagnostic; source-domain transfer and regret claims should not be overstated.
5. Only after these gates pass should Methods/Results and the issue #1 checklist be updated; manuscript changes go to the one canonical manuscript repo, never to a new copy in this public T3 repo.

## CLI smoke and local analysis

```bash
python -m pip install numpy==2.3.5 scipy==1.17.0 scikit-learn==1.7.2
python scripts/t3_b3_post_realworld_audit.py smoke --output /tmp/t3-b3-post-rw-smoke
python scripts/t3_b3_post_realworld_regime.py smoke
python scripts/t3_b3_post_realworld_audit.py interval-coverage --output /tmp/t3-b3-post-rw-coverage --repetitions 100 --bootstrap 300
```

Raw output CSVs and JSONs are reproducible artifacts. Do not publish inference with fabricated input contracts, substitute missing evaluation data, or treat repeated seeds/children as independent observations.

## Reproducible artifact input names for manual gated workflow

The full post–Real World workflow is **manual-only**. It requires (a) final successful Real World run ID with artifact `t3-rw-pub-four-module-global-validation-run<RUN_ID>`; (b) a separate verified frozen Discovery registry artifact; and (c) parent covariate features compiled without inspecting validation outcomes. The candidate universe and parent IDs are checked and missing sources fail closed. A separate native full-pipeline null protocol must be reviewed before dispatch. The lightweight **preflight** on code commit is safe and runs independently of Real World.

This stage is designed to address the shortcomings listed in issue #1, but authoring a gate or a diagnostic is **not** evidence that a test has been completed.

## Immutable input preparation available in this repository

- **Frozen Discovery HPO export**: `.github/workflows/t3-b3-postrealworld-frozen-discovery-hpo-export.yml` extracts the training-only budget, original selected 26-component W SHA256, and training metadata from the three original Discovery bundles in run `41487091262`. It produces the audited artifact `t3-b3-frozen-discovery-hpo-registry-run<RUN_ID>` and can run independently from the Real World recovery.
- **Outcome-blind external parent profile export**: `.github/workflows/t3-b3-postrealworld-outcome-blind-parent-features.yml` is *manual only*. Its 84 small source-block jobs (maximum two in parallel) verify the original parent vector hashes from `41514871500` and produce one feature row per independent parent and n policy (642 parents, 1,926 parent/n rows). This does not read estimator scores or independently validate the classifier.
- **Empirical family-assignment sensitivity by data source**: `scripts/t3_b3_post_realworld_external.py` aggregates the frozen parent-level MSE/Q95 differences within parents, stratifies by source domain and outcome-blind original family assignment confidence/status, and reports descriptive sensitivity without treating training seeds as independent parents. The gated post–Real World workflow contains a separate job for this module.
- The frozen HPO extractor reports an unknown early-stop reason as `early_stop_reason_not_recorded` rather than inventing an explanation. Missing original optimizer/selection metadata causes the extraction to fail.
- The genuine **full-pipeline null-world native optimizer/selection runner is not implemented yet**. The null adapter validates and executes such a runner once the correct original fitting and null-generating procedure is specified and frozen; merely including this adapter does not complete null calibration. A journal claim of fully calibrated selection-adjusted false-positive control would be premature.
