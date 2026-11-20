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
