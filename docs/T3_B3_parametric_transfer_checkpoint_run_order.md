# T3 B3 parametric transfer: two-part checkpoint run order

The full panel has 2,490 transfer identities: 830 each at `n=200`, `n=1000`,
and `n=3000`. Each identity covers 241 Discovery-support scenarios and 500
replications. The 80 mixture stress-only scenarios remain excluded.

## Work unit and exact merge

Each identity is split into two disjoint, deterministic scenario halves:

- checkpoint `0`: 121 scenarios;
- checkpoint `1`: 120 scenarios.

Both halves retain the original sample size and all 500 replications. In
particular, the heavy pass remains `n=3000`; the method does not split a sample
into two `n=1500` samples. The score rows from both halves are reunited by the
global inference script, which verifies complete 241-scenario coverage before
the single global BH adjustment.

## Dispatch plan

For each `sample_n` value, dispatch six balanced batches (`batch_index` 0–5,
`batch_count` 6) and both scenario halves (`scenario_block_index` 0 and 1).
That is 12 workflow runs per sample size. Start with `sample_n=3000`: its 830
identities become 1,660 checkpoint jobs, about 138–139 jobs in each workflow
matrix. Run `sample_n=1000` and `sample_n=200` the same way to complete the full
panel: 36 workflow runs and 4,980 checkpoint jobs overall. Every workflow keeps
`max-parallel: 32` and uses the pinned R container and prepared Discovery inputs.

## Recovery and inference

Each successful worker uploads an immutable Monte Carlo checkpoint and score
checkpoint with hashes. Use GitHub's **Re-run failed jobs** for a partial run;
the coverage step checks the expected shard identities, half assignment,
scenario IDs, and hashes across run attempts. Avoid **Re-run all jobs**, which
would duplicate immutable artifacts.

After all 36 runs pass coverage, collect the 4,980 score manifests and CSVs and
run `scripts/t3_b3_parametric_transfer_inference.R`. It verifies exact identity
coverage, reunites the two scenario halves, and then performs global BH.

The earlier transfer failures were setup/code failures (`t2_seed` was undefined)
and a skipped dependency gate. Those have been corrected. The canceled 80-run
attempt did not validate this revised two-half implementation.
