# Q2 / F3 — Independent robust reconstruction and calibration follow-up

All F3 scientific computation runs in **ALRIER/T3**, branch **main**.
The immutable primary Q2-A–E data remain at `Q2/runs/44599590079/`.
No F3 action writes to `ALRIER/Genetic_Algorithms` or modifies any existing Q1/Q2 result.

## Latest full Q2 taxonomy and manuscript-ready figure package — run 44622921203

[Successful T3-only scientific workflow](https://github.com/ALRIER/T3/actions/runs/44622921203). All 18 frozen-candidate blocks passed independently; one failed synthesis attempt was corrected without rerunning those successful blocks, and the final synthesis passed. The [immutable publication directory](runs/44622921203/publication/) contains five SVG+PNG figures, all four-engine taxonomy and statistical evidence tables, candidate-level neighborhood robustness, exhaustive mechanism tables, an audit, and SHA-256 manifests.

**Preserved counts:** 34,704 original engine-scenario/reference rows including clean; 347,040 candidate-scenario/reference rows; 1,440 candidate-reference breadth rows; 8,640 candidate-mechanism summaries. Descriptive joint MSE/Q95 gains versus the original Discovery-selected classical reference: GA 18, NSGA-II 18, DE 40, Dirichlet 13, out of 4,320 originally supported contaminated scenario summaries per engine. Versus the sample mean: GA 2,421, NSGA-II 2,421, DE 2,379, Dirichlet 2,615. These are distinct reference policies and descriptive estimands.

The original Q2 mechanism-level bootstrap results were fully retained for all four engines and two policies, with separate exploratory BH correction across 864 effects per metric. **All selected-classical joint BH+CI counts are zero** in those complete exploratory 108-mechanism-per-engine panels; this does not establish a fully calibrated negative finding or imply every scenario individually fails. The fitted-null Q2 error-rate status remains unverified for the full optimizer/reselection pipeline. Zero frozen candidates met the strict criterion of beating the unchanged reference on both losses in all 240 within-family observed contaminated scenarios in their own family-size panel.

The new manuscript-ready figures were copied byte-identically into the established canonical private paper directory `ALRIER/Genetic_Algorithms/main/manuscript/figures/`, with the Results and Q2 appendix integrated into the single `manuscript/main.tex` in commit `87e1b76456bd1ad704ee790674c9d2b3de32f4b5`. Canonical PDF recompilation is checked separately and must not be assumed complete from this scientific receipt.

## Q2 taxonomy and manuscript argumentation

The agreed objective × evidence × breadth framework, observed-neighborhood extension rules, strict within-tested-support universality criterion, four-engine candidate identity and Q3/Q4 handoff are documented in [Q2 Scientific Argument and Taxonomy Blueprint](Q2_SCIENTIFIC_ARGUMENT_AND_TAXONOMY_BLUEPRINT.md). This is a planning document, **not** a new inference PASS or a launched workflow.

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
