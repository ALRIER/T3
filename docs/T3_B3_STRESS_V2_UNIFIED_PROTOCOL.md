# T3/B3 Stress V2 — Unified, checkpointed, seed-safe pipeline

## Scope and provenance

One GitHub Actions workflow: `.github/workflows/t3-b3-stress-v2-unified.yml`.

Completed original-score reconstruction from **run 42062234485** (on main) retains
the **720 independent frozen W vectors** and the original 360 score artifacts
(180 within family plus 32 partial and 148 repaired cross-family). Historical
Stress selection uses evaluation seeds **20–24** to freeze the best classical
competitor for each destination family × scenario × n; seeds **25–29** are
held independent for historical confirmation.

The separate **50–59** role is for freshly simulated independent confirmation
(80 bimodal Stress scenarios × 500 replications). It cannot be substituted with
Discovery 0–9, Held-out 10–19, Real-World 30–39, or parametric 40–49.
The separate **60–69** role is for exploratory adapted Rediscovery training.
The adapted model fits 241 original support scenarios + 40
`mixture_bimodal_near` cells; all 40 `mixture_bimodal_far` cells are excluded
from training. Thus, near is *seen in mechanism but unseen in sample*;
far is *unseen in both mechanism and sample*. Report these categories
separately. New experiments do not overwrite or invalidate original Stress.

## Phases

- `pilot`: Python unit test; restore, SHA-check 180 Discovery RDS files;
  recover 720 independent weight hashes; pack three compact 240-W RDS bundles;
  pack 180 historical frozen HPO JSONs into a small digest-checked tar; score
  near+far sample smoke; smoke-test all four adapted search engines.
- `original`: original per-W 20–29 score recovery and one separate global
  BH-FDR inference (historical test; run 42062234485 already complete).
- `confirm`: generate deterministic independent 50–59 component matrices,
  score original frozen W vectors, and infer using classic benchmarks selected
  only on 20–24. Reuse completed `original_run_id` when run separately.
- `adapt`: 60–69 Rediscovery under frozen HPO and equal search budgets,
  pack all 720 adapted W; evaluate them on the **same** 50–59 Monte Carlo
  matrices used by the original W; apply global BH to the combined
  original+adapted panel. When run separately provide `original_run_id`
  and `confirm_run_id`.
- `all`: all stages within **one** Actions run and SHA, in checkpointed jobs.
  This is the simplest option once all preflight gates pass.

## Resource safeguards

- Per-scenario streaming: no combined 80-scenario × 500 × 26 score tensor.
- One normalized 26×240 W matrix per score job; matrix algebra, no
  cross-training-seed averaging.
- Parent samples shared in four predeclared mechanism folds; independent
  per-scenario contamination seeds; deterministic parallel two-core
  generation with single-thread BLAS. Fork scheduling cannot change random
  observations because each replicate receives its own explicit seed.
- Frozen Discovery compressed to three compact per-n RDS files; only 180
  frozen JSON HPO configurations delivered to adapted training jobs.
- Gzip (not xz) per-scenario MC checkpoints, reusable for adapted re-scoring.
- Garbage collection every ten scenarios, block-limited Actions matrices,
  bounded parallelism, 360-minute job ceilings, and separate 90-day
  immutable run-specific artifacts.
- Per-stage hashes, scenario/seed/candidate identity checks, and exact panel
  coverage. An incomplete upstream job prevents downstream inference.
- Python inferential modules use global BH once after per-family reductions;
  historical and fresh tests never have their p-values conflated.
- An observed improvement, IC95%-only signal, and BH-FDR-supported win are
  separate categories; a gain in one metric does not prove no harm in the
  other. Near and far results are reported separately.

## Scientific limitations

The adapted experiment is a **new intervention**, not a correction of
historical out-of-distribution results. It is not valid to claim its near
evaluation is strictly OOD; `mixture_bimodal_near` was present in its
training, albeit on independent samples. Decisions about adapted design after
viewing historical Stress make the extended trial exploratory; claiming
prospective independent confirmation requires explicit preregistration and a
new frozen test stream. Training with 60–69 and evaluating with 50–59 removes
sample leakage but does not undo the prior analytical choices.

Do not silently reduce `R=500` for scientific confirmation. Any training
budget change needs a new protocol/version and clear model-quality comparison.
The original 20–29 Stress run and its complete source archives must remain
unaltered. This workflow must not be launched at scale if the pilot
adapted-training smoke fails.

## Launch and recovery

Open **Actions → T3 B3 Stress V2 Unified → Run workflow**; on the default
branch choose `all` for the single-run dependency chain, or run named
phases to fix specific failed shards and reuse stored run IDs.
A failed individual matrix job should be inspected and retried without
reprocessing unrelated stages. Before final publication, download the
recovered provenance manifests and preserve them outside Actions'
90-day retention window.
