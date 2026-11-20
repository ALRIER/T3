# Q3 A–G compact workflow — owner-authorized one-time relaunch

The previous exhaustive Q3 workflow, Actions run 44818000158, has been
successfully **canceled**, with original artifacts preserved.

The owner explicitly requested a scientifically defensible lighter
parameter-transfer stage and a **complete new launch** of A–G. The redesigned
workflow was validated by successful smoke run 44821804859, including
simulation/scoring/inference R syntax, real canceled-run score recovery,
predeclared 49-scenario selection, 540-shard coverage planning, and complete
A–G scientific figure/inference output tests.

The compact design has six original families, three original sample sizes,
three selected nonbase parameter configurations per family, ten independent
reserved seeds, 49 predeclared scenario IDs, 500 Monte Carlo replicates,
unchanged original frozen weights and comparator policies, MSE and Q95,
paired 95% intervals, and one global BH correction for the parameter panel.

148 original complete-score checkpoints are reusable under the new design,
with 392 new compact scores required (as of readiness audit). The full Held
Out, Stress, and Real World original evidence is reused and SHA audited.

Output checkpoints and inferences must be permanently backed up under Q3
using Git LFS, with explicit limitations and 90-day raw-RDS artifact retention.

This file is the **one-time launch trigger** for
.github/workflows/t3-q3-compact-a-g.yml.
DO NOT edit this launch marker again.


## Owner-authorized targeted recovery relaunch — November 20, 2026

The original compact workflow run 44822079785 failed in the Q3-D four-shard
matrix because a worker counted Discovery files across sample sizes instead
of validating the ten frozen model files for each (family, sample-size) bundle.
This was a workflow assertion error after successful simulated scores, not an
invalidation of original scientific evidence.

The worker validation has been corrected in commit 27c6d6fc3a467177a04a82f371795473cfcdf175.
The exact source-run recovery list was extended to
41748369299,44818000158,44822079785. A real-sources readiness test
https://github.com/ALRIER/T3/actions/runs/44837051791 succeeded: 420 SHA
verifiable reusable score identities, only 120 score shards outstanding,
source-artifact recovery from failed run, two distinct n bundles in one
worker, original-schema 54-panel statistical figures and all R scripts.

This explicit owner-authorized one-time update of the launch marker triggers
the corrected complete Q3 A–G workflow. Historical run checkpoints and
previously committed Q1, Q2, Q3 evidence must be preserved, not overwritten.
