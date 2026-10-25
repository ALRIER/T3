# T3 — canonical development repository for T2 V3 B3 / prospective B4

**Source of truth for all new work:** [ALRIER/T3](https://github.com/ALRIER/T3). Historical and already executed experiments remain immutable in [ALRIER/T2](https://github.com/ALRIER/T2).

## Migration
- Copied the latest B3 scientific source, experiment scripts, current B3 workflows, runtime Dockerfile, and core configuration from T2 branch `t2-v3-contract-adapter-20261024` (snapshot 2026-10-25).
- Source modules include Monte Carlo, four optimization motors (GA / NSGA-II / DE / Dirichlet), full estimator library, nested 5x3 splits, MAD 2.5 sensitivity, candidate evaluation and Real World inference.
- New pinned R container **image recipe** resides in `docker/Dockerfile.r-runtime`; publish to GHCR using `.github/workflows/t3-publish-r-runtime.yml` as `ghcr.io/alrier/t3-r:4.3.3-statmod-v1`.
- Prospective contamination grid **metadata** generator: `scripts/t2_v3_b3_generate_grid321.py`.

## CRITICAL production blockade
**T3 is not yet approved for full Monte Carlo / Discovery / Held-out / Stress / Real World execution.** Migrated production workflows include historical T2 `run-id` references and B3 scientific input code still asserts 121 scenarios. Generating the 321-design CSV does **not** update Monte Carlo generation, input schemas, frozen model interfaces or downstream artifacts. Never dispatch a full inherited workflow as the new experiment.

See `docs/T3_READINESS_AND_MIGRATION.md` for the precise gates and remediation. The old 121-scenario Discovery run #40153358036 must remain archival; do not mix old W or Monte Carlo shards with the forthcoming 321-scenario experimental release.

## Verification
- The prospective method gate runs the MAD cutoff, partition separation, full benchmark Pareto, stability and ablation synthetic smoke tests.
- The image build is an isolated publishing task, **not** scientific Monte Carlo.
- Before any full run, the 321-scenario end-to-end smoke, provenance checks, versioned outputs, storage capacity and scientific comparability requirements must pass.
