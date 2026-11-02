# T3 B3 Real-world parent-checkpoint runbook

## Frozen inputs

- Parent catalog: Actions run `40508641708`.
- Discovery weight bundles: Actions run `41487091262`.
- Discovery own-benchmark map: Actions run `41478038812`.
- Original Real-world scores: run `41208956012`; retain its 128 successful artifacts.
- Missing work: the other 52 family × seed cells at `n=3000` (seeds 30–39).
- Monte Carlo is not regenerated.

## Empirical family proximity

Before scoring, `t3-b3-realworld-family-proximity.R` assigns each unique child profile to its nearest standardized skewness/excess-kurtosis manifold among the six frozen families. Positive-support families are considered only when every observation is positive. A deterministic 99-resample bootstrap reports assignment stability, runner-up, compatible family set, margin, and status. A constant profile is marked `degenerate_nearest_normal_limit`.

This is an outcome-blind proximity descriptor, not a test that recovers the unknown data-generating family. `family_assignment_confidence` is the share of bootstrap resamples selecting the same nearest family; it is a stability score, not a posterior probability or a goodness-of-fit p-value. Reports retain both `training_family` and `empirical_family_assignment`; `empirical_family_relation` distinguishes same-family from cross-family evaluation. Existing `transfer_scope` remains the catalog's frozen within-regime / neighborhood / cross-family profile-match label. Both dimensions are reported together.

The current catalog gives 743 unique child profiles. The local classifier audit found 646 stable assignments, 96 ambiguous assignments, and one degenerate profile. Assignment confidence is carried into the score rows and the parent-level tournament output.

## Score workflow

1. Dispatch `T3 B3 Prepare immutable Real-world parent blocks` with catalog run `40508641708`, Discovery-bundle run `41487091262`, and target child count 55.
2. The workflow freezes 84 family-specific parent blocks (14 per family), packages verified source/vector/license evidence, and embeds the immutable Discovery bundle. All child profiles from one parent remain in one block.
3. Dispatch `T3 B3 Resume Real-world n3000 in parent checkpoints` four times with `batch_index=0,1,2,3`, the original run `41208956012`, and the successful preparation run ID. Each batch plans 182 bounded score jobs. Each job scores all ten frozen Discovery seeds and creates one score artifact plus a hash manifest. If a batch is interrupted, pass its successful run ID(s) to `prior_repair_run_ids`; already-uploaded parent blocks are excluded from the next plan.
4. The workflow refuses to proceed unless the original 128 artifacts and exactly 52 missing cells are present. A completed block is immutable and can be skipped during a later repair by its artifact key.

Each score job has a 90-minute cap and a target of approximately 30–40 minutes. The 55-row target is based on the observed 90–104 child profiles per hour. The runner ceiling is 32; actual GitHub concurrency is account-controlled.

## Reduction and final inference

After all score work succeeds, combine `41208956012` with every successful repair-run ID and dispatch `T3 B3 Reduce complete Real-world tournament inputs` for batches 0–4. Its preflight requires exactly 856 score artifacts: 128 original and 728 parent-block repairs. It verifies every raw score CSV against its immutable score manifest, adds the frozen empirical-family map to legacy score rows, reduces parent-linked outcomes, and bundles each reducer batch.

Then dispatch `T3 B3 Real-world global parent tournament and taxonomy` with the five successful reducer run IDs, benchmark map run `41478038812`, and preparation run ID. It runs one global inference over the complete predeclared panel, so BH-FDR is adjusted after all score blocks are combined. `parent_dataset_id` remains the independent unit. Children, depths, bootstrap replicates, and frozen training seeds are not counted as independent datasets.

The final tables retain comparisons against the best frozen classical benchmark for the assigned evaluation family and against the mean separately. They report the four winner tiers, intervals, q-values, transfer scope, source/evaluation family relation, and family-assignment confidence. No candidate is required to beat all 26 estimators.

## Distinct transfer experiment

The parametric-transfer workflow for seeds 40–49 is separate from the 642-parent Real-world audit. It currently has 2,490 generated/scored shards and its own inference code. It is not a replacement for the Real-world parent-block tournament and is not dispatched by this runbook.
