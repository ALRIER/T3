# Q2 F3 — Scientific reconstruction and conditional inference

## Scope
Original 18 Q2 blocks: 3,470,400 paired candidate/reference observations,
34,704 scenario–method–reference summaries, 180 original source ZIPs.
No original data simulation, original optimizer re-training, HPO or candidate reselection.
The 241 supported scenarios include one clean and 240 contaminated observations per block.
All inputs checked against original permanent Q2 per-block SHA-256 manifests.

## Primary comparator policy
DE versus Discovery-selected classical reference ('own') is the original Q2 policy.
It yields 40/4320 favorable
two-loss scenarios when comparing the ratios of mean original candidate/reference losses.
Against the sample mean: 2379/4320.
These are descriptive source-scenario classifications, not independent hypothesis tests.

## Q1 reconciliation
The 144-row crosswalk displays original Q1 convex-MSE and local deterministic
family/size contrasts side by side with Q2's original own/mean regime-specific
ratios. **This crosswalk is NOT an exact seed/scenario-matched head-to-head
test between convex-MSE and Q2's own reference.** Do not subtract the
reported percentages or relabel one as another. Deriving a matched
convex-MSE per-scenario reference requires original classical score-level data.

## Conditional Q2-specific null diagnostic
The original 216 DE-vs-own raw-loss effects are re-expressed using a two-way
10 training x 10 evaluation seed variance approximation.
For each block, a centered additive row/column/cell empirical model creates
4,096 synthetic calibration draws and a disjoint 4,096 validation draws.
The global 216-statistic maxT cutoff is 8.2825.
Its held-out synthetic global-null rejection rate is 5.322%;
using the uncalibrated t9 cutoff, 99.365%.
The global model independently generates the 18 blocks and shares both
two-loss and six-mechanism correlation within each block. Original seed reuse
across blocks, source-scenario randomness, weight selection and nested HPO
are not captured. **Synthetic conditional calibration cannot be advertised
as genuine selection-aware nominal error control on original Q2 data.**

## Scientific interpretation
Compare absolute losses and pooled/median ratios together with the
unfavorable tails; the mean of per-pair percent changes explodes when the
classical reference loss is near zero. Fraction and MAD severity results
use only observed original neighbor edges; the six mechanisms do not
form complete 7 x 9 factor grids.

## Permanently retained evidence
Every F3 block contains ROBUST_SCENARIO_EFFECTS.csv,
ROBUST_MECHANISM_SUMMARY.csv, ROBUST_OBSERVED_NEIGHBORS.csv,
DE_OWN_12_CONTRASTS_CROSSED.npz and F3_BLOCK_MANIFEST.json.
The synthesis contains the complete pooled summaries, Q1/Q2 policy
crosswalk, null-surrogate validation, 216 conditional effects, and source hashes.
All are new immutable records under Q2/F3/runs/; original Q2 is untouched.
