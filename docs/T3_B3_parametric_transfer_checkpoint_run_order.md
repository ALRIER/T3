# T3 B3 parametric transfer: bounded checkpoint run order

The full panel has 2,490 transfer identities: 830 each at `n=200`, `n=1000`,
and `n=3000`. Each identity covers 241 Discovery-support scenarios and 500
replications. The 80 mixture stress-only scenarios remain excluded.

## Work unit and exact merge

Only the heavy `n=3000` identities are split into two disjoint, deterministic
scenario halves:

- checkpoint `0`: 121 scenarios;
- checkpoint `1`: 120 scenarios.

Both halves retain the original sample size and all 500 replications. The
`n=200` and `n=1000` identities each run once over the complete 241-scenario
panel. The method never splits a sample into smaller n values. Global inference
verifies exact scenario coverage before its single global BH adjustment.

## Dispatch plan

Start with `sample_n=3000`: dispatch six balanced batches and both scenario
halves, for 12 workflow runs and 1,660 checkpoint jobs. Each workflow matrix
has about 138–139 jobs. Only after all 12 runs pass coverage, dispatch six
complete-panel batches each for `sample_n=1000` and `sample_n=200`, for 12 more
workflow runs and 1,660 jobs. The complete design has 24 workflow runs and
3,320 score checkpoints. Every workflow keeps `max-parallel: 32` and uses the
pinned R container and prepared Discovery inputs.

## Recovery and inference

Each successful worker uploads an immutable Monte Carlo checkpoint and score
checkpoint with hashes. Use GitHub's **Re-run failed jobs** for a partial run;
the coverage step checks the expected shard identities, half assignment,
scenario IDs, and hashes across run attempts. Avoid **Re-run all jobs**, which
would duplicate immutable artifacts.

After all 24 runs pass coverage, collect the 3,320 score manifests and CSVs and
run `scripts/t3_b3_parametric_transfer_inference.R`. It verifies exact identity
coverage and the appropriate full-panel or split-panel layout before global BH.

The earlier transfer failure was a benchmark-reference vector misalignment;
local scoring now checks the fixed one-benchmark-per-scenario mapping. The
Monte Carlo archive is uploaded and hash-checked before scoring, so a later
scoring failure preserves the expensive simulation work.
