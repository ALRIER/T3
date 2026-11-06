# T3/B3 Real World: checkpointed benchmark reconciliation

This is a non-destructive post-scoring extension of the November 6 recovery, not a new Real World experiment. All original Discovery models, 642 independent external parent datasets, 743 classified child profiles, 856 immutable original score artifacts, ten Discovery training seeds (0–9), and ten Real World evaluation seeds (30–39) remain unchanged.

## Source of truth

- Frozen score inputs: runs 41208956012, 41516493389, 41516493415, 41516493453, 41516494076, 41688526789. The immutable source inventory is in run 42251598557 and originated in reducer run 42249952933.
- Outcome-blind empirical family map and parent-block plan: 41514871500.
- Frozen Discovery classical benchmark map: 41478038812, 241 supported scenarios across six families and three sizes.
- Preserved 720-W source-family benchmark inference: successful run 42251598557. Never overwrite or concatenate its BH-adjusted results with the new destination-policy hypothesis panel.
- The older engine-averaged tournament run 41699936409 is archival only.

## Why a second benchmark policy is needed

The November 3 V3 tournament selected the frozen non-mean classical comparator by estimated empirical destination family, while the November 6 corrected source-family reducer selected it by the training source family. Both keep all 720 candidate W separate when correctly reconstructed. The destination labels are outcome-blind approximate matches; neither choice identifies the unknown true generating family.

The original source-family benchmark is the frozen primary analysis. The alternative empirical destination-family benchmark is a separately labeled sensitivity analysis, not a retrospectively selected winner or replacement. Comparing its results with the primary can quantify the consequences of benchmark choice without changing the 856 original score files.

## Execution steps

1. A one-time safe push of config/T3_B3_REALWORLD_RECONCILIATION_AUDIT_ONCE.txt triggers the audit-only job. Alternatively, manually dispatch the workflow with phase=audit. It downloads the successful source-policy results, the six family neighborhood outputs, and the frozen benchmark map. It re-runs the independent 720-candidate reviewer and reports exactly which observed source/destination/scenario/n cells use different classical comparators.
2. Only after a successful audit, explicitly dispatch the same workflow with phase=rebuild, its successful audit_run_id, and paired parent-bootstrap replicates (500, 2000 or 5000). The source inventory is verified as the same 856 artifact IDs. If the benchmark map is identical everywhere, rebuilding is blocked as unnecessary.
3. The rebuild performs 216 bounded reducer jobs, no more than four old raw score shards each, at most 22 concurrent. Each job verifies original raw SHA-256, preserves candidate and parent identities, substitutes only the pre-frozen empirical destination-family comparator, uploads checkpointed paired effects and deletes large local raw payloads. The original source-family output remains untouched.
4. Six source-family jobs verify exact shard coverage, independently pool children, depths, and all ten evaluation seeds within each parent, and run separate primary parent-level and secondary destination-family inference. Secondary parent/seed groups must explicitly contain all ten evaluation seeds. New paired parent-bootstrap intervals are *sensitivity outputs only*: original t-test p-values, global Benjamini–Hochberg FDR and four-tier taxonomy remain prespecified.
5. A global job applies two distinct full-panel BH adjustments only after all six families pass. The final reviewer validates all 720 individual W, both benchmark roles, the four-tier taxonomy and descriptive-only neighbor labels. A separate Codex handoff records original source runs, preserved primary result, audit run and new sensitivity run.

## Scientific restrictions and omissions

The 26 classical estimator scores and four frozen evolutionary engines exist in the original raw scorer artifacts. The old V3 production entrypoint describes two non-evolutionary controls, but the executed parent-block scorer did not store them. They **must not** be represented as evaluated Real World competitors without a separate, auditable supplementary scoring protocol. This workflow deliberately does not add an unapproved scorer.

The target remains a full-sample child/depth arithmetic mean proxy, not known population truth. Matched scenarios and empirical family assignments are proxies. Adjacent-scenario migration remains descriptive because parent sets can overlap. Bootstrap confidence limits are not new independent hypothesis families. Selection or claims based on observing Real World outcomes are exploratory. No Actions job silently repeats the old 856 scores or trains additional W.

## Export contract for Codex

Download and preserve the historical original score ledger and manifest SHA values; the source-policy result and reviewer audit from run 42251598557; the new audit artifact; and, if the destination sensitivity is run, its six family summaries, six neighborhood summaries, one global taxonomy, reviewer output, and exact Codex lineage. Join by source_family, engine, training_seed, sample_n, evaluation_seed, parent_dataset_id, dataset_id and original raw SHA as appropriate. Keep **primary source benchmark** and **supplementary destination benchmark** as independent named data tables. Do not combine their p-values, hypothesis counts, row IDs, or BH q-values.
