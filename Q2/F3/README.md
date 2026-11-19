# Q2 / F3 — Independent robust reconstruction and calibration follow-up

All F3 scientific computation runs in **ALRIER/T3**, branch **main**.
The immutable primary Q2-A–E data remain at `Q2/runs/44599590079/`.
No F3 action writes to `ALRIER/Genetic_Algorithms` or modifies any existing Q1/Q2 result.

## Completed F3 run — 44613985618 (2026-11-19)

**GitHub Actions workflow: SUCCESS**, including all 18 independently committed reconstruction blocks and final synthesis.
- [Successful Actions run](https://github.com/ALRIER/T3/actions/runs/44613985618)
- [Permanent 18 reconstructed block directories](runs/44613985618/blocks/)
- [Permanent full scientific synthesis and SHA-256 audit](runs/44613985618/synthesis/)
- [Final scientific audit](runs/44613985618/synthesis/Q2_F3_SCIENTIFIC_AUDIT.json)

**Verified source and output accounting:** 3,470,400 original paired-seed candidate/reference records; 34,704 robust scenario/method/reference rows; 1,008 mechanism/method/reference summary rows; 29,520 observed local-neighbor records; 144 Q1/Q2 side-by-side benchmark-policy rows; 216 original DE-own source-mechanism contrasts; 4,096 centered synthetic calibration and 4,096 disjoint validation replicates.

**Important estimator-change warning:** The robust ratio-of-mean-loss scenario criterion reports 40/4,320 DE joint wins versus the frozen selected-classical benchmark and 2,379/4,320 versus the sample mean. Earlier Q2 A–E used **means of per-pair percentage gains**, which yielded 39/4,320 and 2,376/4,320. These are different, valid descriptive aggregations of the preserved underlying loss data. Never equate them without declaring the estimand.

**Important inferential limitation:** The centered crossed-seed fitted surrogate produced a global 216-contrast maxT threshold of 8.2825 and an independent synthetic global-null rejection rate of **5.3223%**, slightly **above** the nominal 5% target (original uncalibrated t9 threshold: 99.3652%). Therefore the strict 5% surrogate validation gate is **not** shown to pass. The workflow's SUCCESS status certifies successful computation, manifests and permanent backups, **not** successful nominal error-rate calibration. Full original selection-aware confidence-interval coverage and Q2 error control remain unverified. The 144-row crosswalk is NOT an exact seed/scenario-matched comparison of Q1 convex-MSE and Q2 'own' references.

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
