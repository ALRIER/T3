# T3 B3 parametric transfer: full-shard run order

The full panel has 2,490 transfer identities: 830 each at `n=200`, `n=1000`,
and `n=3000`. Each identity covers 241 Discovery-support scenarios and 500
replications. The 80 mixture stress-only scenarios remain excluded.

## Work unit and exact merge

Every identity runs all 241 scenarios and 500 replications intact. No scenario
or sample-size partition is used within a shard. Each GitHub runner job handles
up to four identities sequentially; each identity's Monte Carlo output is
hash-verified and uploaded before its scoring begins.

## Dispatch plan

Run one workflow per sample size (`3000`, then `1000`, then `200`). Each run
contains all 830 identities for that size. GitHub limits a workflow run to 256
matrix jobs, so the plan groups four complete identities sequentially per
runner and creates 208 runner jobs. This does not divide Monte Carlo scenarios
or observations. The matrix uses `max-parallel: 32` and the pinned R container
and prepared Discovery inputs. The complete design has three workflow runs and
2,490 score checkpoints.

## Recovery and inference

Each completed identity uploads an immutable Monte Carlo checkpoint and score
checkpoint with hashes. If a runner job fails, earlier identity artifacts in
that job remain available. The coverage step checks all expected shard
identities, scenario IDs, and hashes. Avoid **Re-run all jobs**, which would
duplicate immutable artifacts.

After all three runs pass coverage, collect the 2,490 score manifests and CSVs
and run `scripts/t3_b3_parametric_transfer_inference.R`. It verifies exact
identity coverage and complete scenario panels before global BH.

The latest run exposed a zero-padding mismatch: R writes `parameter_row03`,
while an earlier workflow verifier looked for `parameter_row3`. All paths now
format row and seed identically, and the local full-shard smoke must pass before
dispatch. The Monte Carlo archive is uploaded and hash-checked before scoring,
so a later scoring failure preserves the expensive simulation work.
