# Q2 / F3 — Independent robust reconstruction and calibration follow-up

All F3 scientific computation runs in **ALRIER/T3**, branch **main**.
The immutable primary Q2-A–E data remain at `Q2/runs/44599590079/`.
No F3 action writes to `ALRIER/Genetic_Algorithms` or modifies any existing Q1/Q2 result.

## Original input lineage
- 18 original family/sample-size blocks in `Q2/runs/44599590079/blocks/`.
- 180 SHA-256 verified original Held Out archives already recovered by the initial Q2 job.
- The 10 original training seeds crossed with 10 independent Held Out evaluation seeds, four optimizers, 241 support scenarios, and two reference policies.
- Q1 original matched family/sample size summary in `R1/runs/44324757704/synthesis/table_RQ1_72_method_family_sample_integrated.csv`.

## Automatic permanent output
`Q2/F3/runs/<github.run_id>/blocks/<family>-n<sample_n>/` contains 18 individual independently committed reconstructed blocks, each with source hash inventory, robust paired loss summaries, local observed-neighbor comparisons, and a crossed 10 x 10 DE own-reference loss matrix.

After **all** 18 shards have committed, `Q2/F3/runs/<github.run_id>/synthesis/` contains the Q1–Q2 benchmark policy crosswalk, robust result tables, synthetic conditional crossed-null calibration and independent validation, scientific caveats, and SHA-256 inventory.

All outputs are durable **Git commits to T3/main**, not expiring Actions uploads. No original scientific outputs are overwritten.

## Inferential boundary
The Q2 global-null calibration is an exploratory, centered **fitted surrogate** conditional on fixed selected scenarios and candidate weights. The model assumes independence across 18 simulated family-size blocks and does not re-estimate the full original optimizer or account for HPO selection. Surrogate-level 5% checks are not proof of actual full-pipeline coverage or familywise error. The Q1 convex-MSE contrast and Q2 Discovery-selected classical reference were evaluated under different policies; the crosswalk shows both without inventing a matched counterfactual.

Workflow: [T3 Q2 F3 robust analysis](../../.github/workflows/t3-q2-f3-robust-reconstruction.yml).
