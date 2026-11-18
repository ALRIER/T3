# R1 reviewer replication and inference audit

Reference Held Out run: 44307352615. Full Discovery/Held Out synthesis: 44310024979.

- Independent R reconstructions: **216/216** pairwise optimizer/metric/stratum contrasts.
- The paired contrasts use 10 independent Held Out evaluation seeds; correlated training-seed candidate results are averaged within seed.
- Original globally Holm-corrected paired t comparisons at 0.05: **216/216**.
- Exact sign-flip sensitivity contrasts after global Holm at 0.05: **0/216**.
- These are different inferential approaches; an apparent discrepancy is a sensitivity finding, not permission to ignore either.
- Original 720 candidates and 360 Discovery-to-Held Out ranking cells were checked for complete coverage.
- The independent exact sign-flip test has discrete resolution with only ten seeds; Holm across 216 comparisons is conservative.
- Neither test is a complete selection-aware null replay, a proof of optimizer superiority across every regime, or independent validation of deterministic controls.
- No Monte Carlo, Discovery training, or Held Out scoring was rerun.

Execution: canonical pinned T3 R container from config/T3_DEFAULT_ANALYSIS_RUNTIME.env.
Input provenance is linked by the immutable run IDs above.
