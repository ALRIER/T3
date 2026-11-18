# RQ1 final evidence synthesis (original archived experiment)

**Data**: 6 families × 3 sample sizes, 10 frozen training seeds × 10 independent evaluation seeds, 241 support scenarios and four search methods. Original model weights were never refitted or reselected.

**Baseline**: original independently scored frozen Discovery deterministic convex_mse and local_deterministic methods; 288 posthoc pairwise contrasts with global Holm across 288. A significant contrast can indicate the deterministic control is BETTER; directional signs are mandatory.

**Joint outcomes**: MSE and Q95 are evaluated together, with Pareto dominance and original two-way bootstrap. The 0, 1% and 5% thresholds were posthoc sensitivity probes; the joint uncertainty correction holds only within a single candidate pair/direction, not all 216 comparisons.

**Inference**: the original global Holm-adjusted paired t results, crossed training/evaluation seed t9 sensitivity, and global maxT signflip sensitivity are reported side by side without replacing the original prespecified test. The maxT diagnostic shares all 12 per-stratum comparison signs to preserve within-seed metric/method dependence; its joint-sign-symmetry and cross-stratum independence assumptions are UNVERIFIED, and it is not proof of familywise or selection-aware error control.

**Monte Carlo**: original per-scenario Q95 order-statistic intervals were reconstructed from the 500-replicate component matrices and six frozen method sets. This is conditional Q95 precision, not inferential coverage for an optimizer difference.

**Compute**: all 720 objective evaluation counts are verified, but original elapsed-time fields and total nested HPO runtimes are absent. Unequal actual objective evaluations, especially Dirichlet, must be addressed as an experimental fairness limitation. Do not equate evaluation-count efficiency with measured wall-clock efficiency.

**Remaining before stronger inferential claims**: independent known-truth coverage/selection-aware calibration and verified whole-pipeline runtime would require source records or a separately declared external replay. They are not manufactured or classified as successful here.

Tables and source-ready SVG+PNG figures accompany this report under the same SHA256-backed repository run directory.
