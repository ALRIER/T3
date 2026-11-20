# Q3 A–G full scientific workflow — one-time authorized launch

Authorized by the project owner on November 20, 2026: **launch Q3 A–G now**.

This immutable launch marker intentionally triggers the existing
`.github/workflows/t3-q3-one-run-a-g.yml` workflow **exactly once** via the
narrow `push` path filter on `main` because the linked GitHub app has no
workflow-dispatch mutation endpoint.

## Original scientific inputs

- Immutable original Discovery source archive: `41487091262`.
- Discovery-frozen classical reference map: `41478038812`.
- Verified previous original parameter-transfer checkpoint archive: `41748369299`
  (the audited smoke run detected **459** reusable original complete score shards).
- Planned complete evaluation: **2,490** transfer shards, including the 459
  recoverable shards and the **2,031** pending identities.
- Full 241 original scenarios per shard, 500 Monte Carlo replicates, 10
  independent transfer seeds (40–49), three sample sizes.
- Maximum **20** parallel runners; sample-size waves run sequentially.
- Original frozen candidate weights without retuning.

## Expected outputs

`Q3/A_provenance/`, `Q3/B_cross_family/`,
`Q3/C_structural_stress/`, `Q3/D_parameter_transfer/`,
`Q3/E_real_world/`, `Q3/F_synthesis/`, and
`Q3/G_publication_audit/`. Complete scientific score and inference archives
are published to Git LFS, with SHA-256 checks, source provenance, numerical
tables, and manuscript-ready graphics. The canonical private manuscript is
left unchanged until the results are reviewed.

**Do not edit this marker again**: changing this exact path causes another
launch by design. The single-run concurrency group protects against
simultaneous duplication, but does not replace user authorization.
