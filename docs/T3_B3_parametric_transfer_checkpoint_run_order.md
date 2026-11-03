# T3 B3 parametric transfer: checkpointed run order

The transfer plan is split into immutable scenario checkpoints so a timeout only
puts one eighth of a shard at risk. Each checkpoint contains a disjoint subset of
the 241 Discovery-support scenarios, its Monte Carlo RDS, its score CSV, and SHA
manifests. The 80 mixture stress-only scenarios remain excluded.

## Dispatch plan

The workflow matrix holds at most 249 base identities per dispatch, below the
GitHub Actions matrix limit. Run all combinations of:

- `batch_index`: `0` through `9`;
- `scenario_block_index`: `0` through `7`;
- `batch_count`: `10`;
- `prepared_inputs_run_id`: the successful run containing the frozen benchmark
  map and all 18 family/sample-size Discovery input bundles.

This is 80 dispatches total. Each dispatch uses `max-parallel: 32`; each worker
has a 90-minute hard timeout. The 241 scenarios are split into seven blocks of
31 and one block of 24, in the frozen grid order. The largest block therefore
does one eighth of the former per-shard Monte Carlo and scoring work.

The 90-minute timeout is a conservative execution cap, not a measured runtime:
the previous transfer attempts failed during setup and produced no valid timing
observations. A block that exceeds the cap can be retried without repeating
completed blocks.

## Recovery

Use GitHub's **Re-run failed jobs** on a partially failed dispatch. Successful
checkpoint artifacts from earlier attempts are retained; the coverage job
collects artifacts across attempts for that run and checks every expected shard
identity, block number, scenario ID set, and SHA. Do not use **Re-run all jobs**:
it would intentionally encounter duplicate immutable checkpoint artifacts.

After all 80 dispatches pass coverage, collect all 19,920 score checkpoints
before running `scripts/t3_b3_parametric_transfer_inference.R`. That script now
requires the complete block identity set and performs the single global BH pass.
