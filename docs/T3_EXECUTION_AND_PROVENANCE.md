# T3 execution and provenance contract

## Execution order

1. Monte Carlo is an immutable input. Downstream workflows identify its successful Actions run ID, download the requested artifact, verify the manifest and SHA-256, then materialize the canonical block. They do not call the generator.
2. Nested hyperparameter selection uses five outer scenario folds and three inner folds. Optuna selects parameters using training-only scenarios. The frozen registry is keyed by family, discovery seed, and sample size. Population/generation pairs are selected from three prespecified configurations, each with exactly 5,100 maximum candidate evaluations; operator-specific parameters remain independently tunable. Production controls inherit the common candidate-evaluation budget, and contracts compare the actual per-engine budgets rather than assuming identical population sizes.
3. Discovery fits each optimizer with the frozen registry, uses the 241-scenario support partition, and freezes one W per engine. Discovery is descriptive; it does not issue confirmatory BH claims.
4. Held-out uses independent seeds 10–19 on the 241-scenario support partition. Stress uses independent seeds 20–29 on the 80 scenarios reserved from fitting by the two bimodal mechanisms.
5. Frozen cross-family scoring evaluates each source-family W on each of the other five evaluation families without refitting. It is a separate workflow and its artifact run ID is required by global aggregation.
6. Real-world scoring is downstream of frozen validation. It must consume a pre-scoring parent/profile manifest and produce parent-level inference. The old recollection and full workflows are disabled because they point to absent legacy source modules.

## Comparisons and claims

- For each metric, the reference is the best eligible member of the predeclared 26-estimator classical/robust panel, selected within the independent evaluation seed. The MSE and q95 references may differ. A learned candidate is paired against that per-seed reference; the reference is never selected after looking at candidate outcomes.
- MSE and q95 are evaluated separately. Reports preserve MSE-only, q95-only, joint MSE+q95, joint BH-FDR, single-metric BH-FDR, Pareto, and practical-improvement indicators with confidence intervals. A joint winner is not required for a candidate to appear in a single-metric category.
- Held-out and stress primary BH correction is applied once to the complete stage reporting panel: candidate × metric × source family × evaluation family × sample size × transfer scope. Within-stratum q-values are secondary. The global aggregation workflow refuses to run without both standard and cross-family score artifacts.
- The frozen practical threshold is a 5% relative reduction in each loss for the `practical` category; `assured_practical` additionally requires both 95% lower confidence bounds to exceed 5%. Statistical significance alone does not imply practical value.
- Real-world independent units are `parent_dataset_id`, never variables, bootstrap children, or repeated depths. The external-catalog validator requires per-row SHA-256 provenance and individually verified HTTPS license references. Generic license labels do not pass.

## Repeatability, retries, and runtime

- Optimizer variability is a separate three-repeat Discovery-only sensitivity audit at n=1000. It reports weight distances and losses; it never replaces production W or uses held-out data. Each repeat is atomically checkpointed with its selected weights and evaluation ledger; retries verify and resume from completed repeats.
- A failed shard may be retried with the same role, family, seed, n, code revision, and source artifact. A completed artifact is immutable; a retry may fill a missing shard but may not overwrite a different checksum. No missing seed or failed dataset is silently replaced.
- Every published stage contract records the role, family, seed, n, replication count, source run, code revision, scenario IDs, and SHA-256. Retain the source artifact and stage output together.
- R workflows use `ghcr.io/alrier/t3-r@sha256:658e61478909fe688bc2d47837f7e09d64b4724ba1ff84bc807e901bf7931e16`. The nested tuner uses Python 3.12.10 and Optuna 4.9.0. The publishing workflow may publish a tag; production consumers use this immutable digest until a reviewed image update changes the manifest.
- `t3-b3-downstream-e2e-smoke.yml` is a bounded, manual smoke that consumes one existing discovery block and three held-out plus three stress blocks. It does not regenerate Monte Carlo, tune production HPO, or produce scientific claims.

## Current external-data gate

`config/confirmatory_public_datasets.csv` does not currently satisfy the parent-level source and license-review schema. The legacy Real-world collector references files absent from this checkout. Consequently the old Real-world workflows are disabled, and a full Real-world run must remain blocked until a frozen catalog has at least 500 independent parents and passes `scripts/t3_validate_realworld_manifest.py --minimum-parents 500`. This is a data-provenance gate, not a license inference from a generic package name.
