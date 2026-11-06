# T3/B3 Real-World V2: frozen individual-W reconstruction

## Why the prior Real-World stage needs reanalysis

The original Real-World scoring script `scripts/t3_b3_realworld_scoring.R` scored each of the ten Discovery training seeds **separately** and recorded labels such as `normal_ga_train00`. Original models were not numerically averaged before scoring. The downstream legacy reducer `scripts/t3_b3_reduce_tournament_shard.R` stripped that seed identity, renamed every evolutionary score by its optimizer engine, and averaged the ten distinct weights. The older global tournament `scripts/t3_b3_tournament_from_reduced.R` cannot provide independent conclusions for individual W vectors. Its successful run **41699936409** stays as a historical reference, never merged into the new inferential table.

## Immutable inputs (no new Monte Carlo or Discovery training)

- Original scoring: **128 complete per-family/seed/n artifacts** from run **41208956012**.
- Corrected scoring of the remaining n=3000 parent-intact blocks: **728 artifacts** across runs **41516493389**, **41516493415**, **41516493453**, **41516494076**, and **41688526789**.
- **856 unique raw scoring artifacts** altogether. The V2 planner verifies completeness and exactly one source artifact per family × evaluation seed × n × parent block, with no duplication.
- Original Discovery candidate seeds **0–9**: 6 source families × 3 sample sizes × 10 training seeds × 4 engines = **720 frozen candidate identities**; no refitting.
- Real-World independent bootstrap evaluation seeds **30–39**, with **500 Monte Carlo replications** per child/depth/scenario original scoring, unchanged.
- Frozen Real-World outcome-blind empirical destination labels and parent-block plan: run **41514871500**. These are *estimated family compatibility*, not known generating distributions.
- Discovery-frozen non-mean classical comparator per supported training scenario/family/n: run **41478038812**, containing 241 support scenarios, not the full 321 grid.
- Real-World sample target: each child/depth's full-sample arithmetic mean proxy. It is not independent ground truth.

## V2 pipeline and provenance

Primary Actions workflow: `.github/workflows/t3-b3-realworld-v2-unified.yml`, run **42249952933**. Verified 856-source inventory and **216** completed bounded reducer jobs, each processing at most four original scoring shards with `max-parallel: 22`, checking the raw SHA-256 and re-emitting both original weight identities and original frozen parent/source labels. The first actual raw score pilot, run **42249242302**, passed.

The source-family analysis was verified independently in normal-family pilot **42250898429** (134 immutable reductions and all ten evaluation seeds). The original full workflow accidentally declared a family count lower bound of 130; the `lognormal` family has **121** valid source artifacts and thus fails only this *incorrect coverage gate*, despite the global source inventory being complete. Other family counts are normal 134, invgauss 134, exgaussian 147, weibull 160, exwald 160. The lower bound was corrected in subsequent code.

The automatic one-time continuation, `.github/workflows/t3-b3-realworld-v2-recover-finalize.yml`, is triggered by completion of run 42249952933. It validates the complete prior 216 reduction checkpoint inventory and reuses any already-successful family parent and neighborhood analysis artifacts. It recomputes **only missing family analyses**, performs global inference and uploads a final Codex lineage manifest. The original 856 scoring jobs are *never* repeated.

## Scientific panels and migration

1. **Primary parent-cluster:** Each of the 720 candidates remains identified by source family, optimizer, Discovery training seed and sample size. Both MSE and Q95 losses are paired against the frozen classic for each matched scenario and against `mean`. Within a child, the valid depth slices are equal weighted; children and ten evaluation seed summaries are pooled *inside the independent parent*. Inference (paired 95% intervals and BH-FDR at 0.05) uses distinct parent dataset IDs only.
2. **Secondary empirical-family transfer:** The outcome-blind empirical `evaluation_family`, transfer scope, source family and n are retained. Parent clusters are reconstructed within each destination, and a *separate* global BH-FDR panel is run. Because the destination class is estimated and there is multiple testing, these conclusions require the appropriate caveats.
3. **Neighbor migration and cross-scenario diagnostics:** The observed 241 training-support scenario grid is linked by immediate adjacent contamination or adjacent MAD within the same mechanism; no mechanism is fabricated for a child. Report candidate consistency, sign of gains, parent coverage, near-neighbor gradients, and transfer between observed matched-scenario profiles. These windows can overlap parent datasets, so **no p-value, false-discovery claim or causal migration claim** is made.
4. **Four-tier taxonomy:** Tier 1 joint MSE and Q95 BH-FDR+IC95% success; Tier 2 both IC95% but not joint BH; Tier 3 single-metric BH success; Tier 4 retained candidate without supported win. Report deterioration of the secondary metric and both benchmark references explicitly.

## Resource and publication rules

Raw scoring material stays immutable and recoverable by source run ID and original manifest SHA. Reducer jobs download only four raw archives at a time, process one, write compressed, hash-traceable summaries, delete the large raw payload, and never load all 856 raw shards into one container. Family inference uses disk-backed SQLite aggregation and six bounded source-family jobs. The final BH-FDR is applied only after all families pass completeness checks, with distinct primary and secondary hypothesis families.

Real-World profiles that share a parent, overlapping depths, children, seeds, and nearby scenario matches are not treated as independent sources. A successful Actions job proves successful implementation, not that any evolutionary W necessarily wins. The manuscript should not claim winners until the final V2 taxonomy is audited. Neither the prior engine-averaged table nor conditional within-dataset resampling should be presented as independent across-parent evidence.
