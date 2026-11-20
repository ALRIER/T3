# Q2 / F3 — Independent robust reconstruction and calibration follow-up

## Audited 720-candidate individual leaderboard (2026-11-20)

Original-data candidate-level evidence was reconstructed and permanently committed in [the single F3 leaderboards folder](leaderboards/) by successful [GitHub Actions run 44763334662](https://github.com/ALRIER/T3/actions/runs/44763334662). The new source script is [scripts/q2_f3_candidate_leaderboards.py](../../scripts/q2_f3_candidate_leaderboards.py); it reads the original SHA-256-checked F3 candidate-breadth and mechanism-pocket CSVs, does not rerun the four optimizers or held-out scoring, and emits exactly three publication-ready PNG figures directly inside the leaderboards folder.

The archive preserves 1,440 per-candidate-per-benchmark descriptive rank rows across 720 original frozen identities, 36 family-size-reference joint leader summaries, 180 objective-specific block leader rows, 216 family-size-mechanism-reference leader rows, and 10 overall taxonomy extrema, plus a machine-readable source/output SHA-256 audit. Scientific ties and the distinction between own-classical versus sample-mean references are preserved. The highest observed single-weight joint-win coverage is 11/240 (four tied vectors) versus own classical and 217/240 (four tied) versus the mean; 0/720 candidates win all 240 scenarios under either policy.

These are descriptive, within-original-support comparisons. Cross-family Held Out, Stress and Real World inference is retained in the separate original [transfer recovery](transfer_recovery/) folder. The candidate key preserves family, sample size, search engine and training seed, but this source-derived publication does **not** certify byte-identical RDS weights across every test stage. The full nested optimizer-selection-aware error-rate calibration remains unresolved; the Q2 fitted-null 5.3223% estimated rejection at nominal 5% did not pass the stringent point-estimate gate. All figures and 18-block/mechanism leader tables are incorporated or explicitly indexed in the **existing single canonical private** \`manuscript/main.tex\`, with verified PNG copies under its existing \`manuscript/figures/\` folder.

All F3 scientific computation runs in **ALRIER/T3**, branch **main**.
The immutable primary Q2-A–E data remain at `Q2/runs/44599590079/`.
No F3 action writes to `ALRIER/Genetic_Algorithms` or modifies any existing Q1/Q2 result.

## Recovered original cross-family generalization and canonical correction (2026-11-20)

The complete original source-versus-evaluation-family transfer validation was recovered and audited without retraining or changing existing inference. See [scientific findings](transfer_recovery/CROSS_FAMILY_RECOVERY_FINDINGS.md), [original source/destination Real World panels](transfer_recovery/two_policy/runs/44748009646/), [verified Real World PNG and source tables](transfer_recovery/publication/runs/44748368642/), and the [canonical publication audit receipt](transfer_recovery/Q2_CROSSFAMILY_PUBLICATION_RECEIPT.json).

Original synthetic Held Out source-unseen-family wins **do exist**. Source-selected-classical candidate-level BH+CI: 5,069/867,600 cross-family versus 877/173,520 within-family; the original pooled four-engine matrix is a distinct estimand (357/86,760 cross and 73/17,352 within). Empirical Real World preserves 642 independent parent datasets, 720 original frozen W, and separate source/destination classical-reference policies. Cross-family Real World descriptive comparisons exist, but no recovered cross-family panel passes joint original CI/BH criteria. Within-family Q2 240/240 universal winners remain absent. These claims are complementary, not contradictory.

The corresponding revised manuscript and new transfer PNG are in the canonical private paper repo; the permanent 74-page PDF was verified in [publication Actions 44749669402](https://github.com/ALRIER/Genetic_Algorithms/actions/runs/44749669402). All analysis and figures were computed in public T3.

## Latest full Q2 taxonomy and manuscript-ready figure package — run 44622921203

[Successful T3-only scientific workflow](https://github.com/ALRIER/T3/actions/runs/44622921203). All 18 frozen-candidate blocks passed independently; one failed synthesis attempt was corrected without rerunning those successful blocks, and the final synthesis passed. The [immutable publication directory](runs/44622921203/publication/) contains five SVG+PNG figures, all four-engine taxonomy and statistical evidence tables, candidate-level neighborhood robustness, exhaustive mechanism tables, an audit, and SHA-256 manifests.

**Preserved counts:** 34,704 original engine-scenario/reference rows including clean; 347,040 candidate-scenario/reference rows; 1,440 candidate-reference breadth rows; 8,640 candidate-mechanism summaries. Descriptive joint MSE/Q95 gains versus the original Discovery-selected classical reference: GA 18, NSGA-II 18, DE 40, Dirichlet 13, out of 4,320 originally supported contaminated scenario summaries per engine. Versus the sample mean: GA 2,421, NSGA-II 2,421, DE 2,379, Dirichlet 2,615. These are distinct reference policies and descriptive estimands.

The original Q2 mechanism-level bootstrap results were fully retained for all four engines and two policies, with separate exploratory BH correction across 864 effects per metric. **All selected-classical joint BH+CI counts are zero** in those complete exploratory 108-mechanism-per-engine panels; this does not establish a fully calibrated negative finding or imply every scenario individually fails. The fitted-null Q2 error-rate status remains unverified for the full optimizer/reselection pipeline. Zero frozen candidates met the strict criterion of beating the unchanged reference on both losses in all 240 within-family observed contaminated scenarios in their own family-size panel.

The new manuscript-ready figures were copied byte-identically into the established canonical private paper directory `ALRIER/Genetic_Algorithms/main/manuscript/figures/`, with the Results and Q2 appendix integrated into the single `manuscript/main.tex` in commit `87e1b76456bd1ad704ee790674c9d2b3de32f4b5`. The canonical PDF build **passed** in [private manuscript workflow 44624356324](https://github.com/ALRIER/Genetic_Algorithms/actions/runs/44624356324). The sole canonical PDF is 69 pages and 3,693,213 bytes, committed to the manuscript repository at `46db0d6cddd568b6d8d2bca68b41346fc0515405`, with all five Q2 PNGs present. The complete source-to-paper publication receipt is permanently recorded in [Q2_F3_MANUSCRIPT_PUBLICATION_RECEIPT.json](runs/44622921203/Q2_F3_MANUSCRIPT_PUBLICATION_RECEIPT.json).

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
