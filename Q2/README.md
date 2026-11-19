# Q2 — Regime-specific estimator performance

**Single canonical Q2 results directory:** `ALRIER/T3/Q2/` on `main`.

The unified Q2-A–F workflow uses the archived original Held Out results and
frozen Discovery classical benchmarks. No Discovery, Monte Carlo, or optimizer
retraining is performed. Q2 concerns within-family independently evaluated
supported scenarios; cross-family/structural transfer remains Q3.

## Latest verified run: 44599590079

**Q2-A–E completed successfully:** all 18 original support blocks and the scientific
synthesis were validated and saved in
[`Q2/runs/44599590079/`](runs/44599590079/).
The primary workflow's cross-repository Q2-F step lacked the private-repository
`PUB1_MANUSCRIPT_TOKEN` secret and failed without modifying the paper.
Q2-F was subsequently **recovered and completed** in the authorized canonical
paper repository using
[private paper Actions run 44601166188](https://github.com/ALRIER/Genetic_Algorithms/actions/runs/44601166188).
The updated 61-page PDF and one canonical `main.tex` were committed to
`ALRIER/Genetic_Algorithms/main` at
`49a01d09634467f845acc00dbb2405e8d5e9853f`.

See [Q2-F cross-repository completion receipt](runs/44599590079/Q2_F_MANUSCRIPT_INTEGRATION.json).
The 18 scientific blocks and original archives were **not** rerun for this recovery.

## Run outputs

Each GitHub Actions execution commits **each** of its 18 family×sample-size
blocks to `Q2/runs/<run_id>/blocks/<family>-n<n>/`, including:

- all original paired per-training/per-evaluation seed score differences,
  241 scenario IDs, four engines, and the frozen own/mean reference policies;
- checksum-verified original source ZIP lineage;
- scenario effects, factor profiles, observed local scenario neighbors;
- an independently run R 4.3.3/statmod 1.5.2 validation gate.

Once all 18 blocks pass, `Q2/runs/<run_id>/synthesis/` contains the scientific
review, two-way seed bootstrap panels, exploratory BH sensitivity, all tables,
two PNG/SVG figures, and SHA-256 manifest. GitHub Actions artifact uploads are
**never used**; completed block outputs are committed directly to Git so a
single failed job does not erase successfully recovered data.

The workflow's final Q2-F step updates the **existing** canonical manuscript
`ALRIER/Genetic_Algorithms/manuscript/main.tex` on that repository's
`main` and copies new figures into its established `manuscript/figures/`
directory. This step requires an authorized `PUB1_MANUSCRIPT_TOKEN` Actions
secret in T3 with access to the private manuscript repository. If missing,
the workflow fails Q2-F explicitly without falsely claiming a finished
article; scientifically completed A–E outputs remain permanently in Q2.

## Scientific guardrails

- All analyses use original independent Held Out evaluation seeds 10–19,
  original training seeds 0–9, and the prespecified 241 support scenarios.
- Main RQ2 analysis uses DE versus the frozen Discovery-selected classical
  reference within-family; all four engines and the sample mean are retained
  as sensitivity comparisons.
- The selected support grid contains six contamination mechanisms with
  40 original factor combinations each, **not** a 7×9 complete factorial.
- Model-selection, multiplicity and crossed bootstrap limitations are stated
  prominently. Q1 Stage 12's 216 method-pair calibration cannot be transferred
  to the different Q2 candidate-regime contrasts.

Workflow: [Q2 A–F one-pass](../.github/workflows/t3-b3-q2-regime-unified-full.yml)

For provenance and the distinction between raw backups and results, see
[R1 source index](../R1/README.md).
