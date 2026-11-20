# Q3 — Independent transfer, changed regimes, and original-frozen estimator generalization

## Single-dispatch scientific workflow

**Prepared:** 2026-11-20. **Status: implementation committed; original 2,490-shard full Q3 experiment has NOT been dispatched by this manuscript-preparation task.** Only the code/source-data and no-compute archival-integrity readiness smoke has been executed.

- [Complete one-run GitHub Actions workflow](../../.github/workflows/t3-q3-one-run-a-g.yml): **Q3 A–G in one workflow-dispatch event**. Launch from GitHub Actions when ready to commit compute resources.
- [Source-complete original analysis and publication code](../../scripts/q3_complete_science.py).
- [Full 2,490-shard original-design planner and recovery discovery](../../scripts/q3_build_plan.py).
- [Byte-verified reuse of original partial parameter-transfer score artifacts](../../scripts/q3_recover_shard.py).
- [No-compute source/plan/backup readiness test](../../.github/workflows/t3-q3-smoke.yml).

### Scientific division of labor

| Analysis | Direct action within the *same* workflow | Persistent output |
| --- | --- | --- |
| A | Original source SHA, seed, design, target, and recovery provenance | \`Q3/A_provenance/\` |
| B | Directional six-source × six-destination original Held Out transfer by search method, plus original separate individual-weight rates | \`Q3/B_cross_family/\` |
| C | Distinct original historical/fresh structural Stress transfer rates without an invalid one-factor causal interpretation | \`Q3/C_structural_stress/\` |
| D | Verify original complete 241-scenario score checkpoint for each non-base family parameter row, seed 40–49 and n=200,1000,3000, using all previous reusable score artifacts first. Full original \`t3_b3_parametric_transfer_inference.R\` inference and one globally adjusted BH panel across the full Q3 D family | \`Q3/D_parameter_transfer/\` |
| E | Original empirical source-selected/destination-selected benchmark policies, outcome-blind assigned empirical destination profiles, and parent-level inferential support | \`Q3/E_real_world/\` |
| F | Complete original-source and original-inference-unit transfer tables, parameter-shift summary, source–destination matrix, three manuscript-ready PNGs and limitations | \`Q3/F_synthesis/\` |
| G | Full integrity manifest, objective/inference-unit audit, and permanent GitHub publication gate | \`Q3/G_publication_audit/\` |

### Compute and recovery contract

The existing predeclared parameter grid has **83 non-base parameter rows**, 3 sample sizes, **ten independent parametric evaluation seeds (40–49)** and 241 original Discovery-support scenarios per identity, producing **2,490 original complete score shards**. Each shard originally generates 500 Monte Carlo replicates per scenario and applies the Discovery-frozen 720 weights without fitting a new estimator. **No extra scenario combinations or unobserved weights are invented.**

GitHub Actions accepts at most 256 jobs in a single matrix. Each sample size is therefore 208 matrix jobs, each handling up to four entire shards sequentially. The three sample-size matrices are **dependent and sequential**, each with \`max-parallel: 20\`, so the three phases never multiply the active concurrency to 60. Every candidate score matrix keeps the full original 241 scenarios intact. All already-complete earlier original results identified in the \`reuse_original_parametric_runs\` input are checked for exact source identity and SHA-256, then reused rather than recomputed. If needed, add a comma-separated successful-partial original run ID at dispatch.

Existing reusable original-discovery archives default to \`41487091262\`, the Discovery-frozen comparator map to \`41478038812\`, and the previous partial parametric checkpoint archive to \`41748369299\`. These are original GitHub Actions resources, not copies of newly fitted weights. The launch job fails if these artifacts have expired or cannot be verified.

**Time/resource caution:** the full first-time D panel consists of 2,490 complete 241-scenario × 500-replicate identities; many existing checkpoint artifacts are partial. GitHub-hosted runner job execution is limited to six hours and overall runtime is not guaranteed to be short. The workflow is designed to fail with an explicit provenance/coverage error rather than label a partial panel complete. Successfully saved score artifacts can be reused on a follow-up run.

### Permanent backup contract

- Original historical Held Out, Stress and Real World source ZIPs and lineage already reside under \`data-archive/\` and its ~45 GB source inventory. The Q3 workflow references their original immutable source checksums; it does not copy them again.
- All **new scored parameter-shift CSVs and their immutable SHA-256 source manifests** are gathered by complete sample-size set and permanently committed in Git LFS-backed, ~30 MiB binary pieces under \`Q3/D_parameter_transfer/n{200,1000,3000}/archive/\`. The exact member/part SHA-256 manifests are checked before inference.
- All **original full-panel parameter-inference outputs** (metric CIs, original bootstrap/test results, global adjusted q-values and candidate-level per-panel taxonomy), plus summary tables, PNGs, and SHA inventories are likewise permanently committed under \`Q3/D_parameter_transfer/inference_archive/\`, \`Q3/F_synthesis/\`, and \`Q3/G_publication_audit/\`.
- Each newly computed *raw parametric Monte Carlo RDS checkpoint* is hashed and uploaded to GitHub Actions artifacts for 90 days. **The potentially tens of gigabytes of raw regenerated RDS matrices are NOT silently claimed as permanently stored** in the T3 Git repository. The permanent score archive retains reproducible source identity, seeds, output scores and original raw MC SHA provenance. Archiving those raw RDS bytes beyond artifact expiration would require separately approved large-volume LFS or external storage.

### Scientific constraints and manuscript policy

The evidence concerns MSE and the 95th-percentile squared error. The Benjamini–Hochberg-adjusted **positive evidence fraction is not an empirically measured type-I false-positive rate**. Original independent seed panels, original empirical-parent clusters and original conditional inferential limits remain separate. The complete nested optimizer/reselection null calibration was deliberately deferred. Under the same-family new-parameter protocol, the original R script (not the writeup script) computes paired CIs and the global BH correction. The final read-only synthesis is prohibited from reallocating confidence intervals across inferential units.

The single-run workflow creates **scientific results and manuscript-ready figures only**. As requested, interpretation and scientific manuscript writing begin **after** reviewing its A–G findings; the private canonical \`ALRIER/Genetic_Algorithms/manuscript/main.tex\` and PDF are not rewritten automatically. No duplicate paper or manuscript folder is created.

## How to launch

Open [T3 GitHub Actions](https://github.com/ALRIER/T3/actions/workflows/t3-q3-one-run-a-g.yml), choose **Run workflow** on \`main\`, confirm original source run IDs, and launch once. Inspect the final \`q3_g\` PASS gate before relying on an integrated Q3 conclusion.
