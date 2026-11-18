# Q1: Evidence status, scientific narrative and manuscript blueprint

**Verified:** 2026-11-18, current canonical source `ALRIER/T3` on `main`. This document is a planning memo, **not** a change to the manuscript or a claim of full end-to-end statistical validation. Keep original source experiments intact.

## Proposed central answer

**The relative effectiveness of the optimization engine depends on the data-generating regime.** DE is Pareto-nondominated in all 18 original distribution-family/sample-size blocks, and achieves simultaneous MSE and Q95 improvements over the frozen convex-MSE deterministic baseline in 13/18 blocks. The result is generalization-stable across separately evaluated frozen candidates and independent evaluation seeds, but it is **not universal superiority over the deterministic control**: the control is better than DE on both measures in all three normal blocks, and Weibull is mixed.

Thus the paper should describe **reliable multiobjective optimization and principled benchmark choice**, identifying when a more complex optimizer improves surrogate fit and when a classical convex benchmark is preferable. The study tests the **241 supported scenarios**; 80 original reserved Stress scenarios are not automatically part of these Q1 conclusions.

## Status table — 14 research components

| No. | Q1 component | Status | Publication interpretation |
|---:|---|---|---|
| 1 | Original paired Held Out inference, intervals, Holm across 216 | **Computed** | Original calculations available; nominal 5% calibration assumptions were subsequently questioned |
| 2 | Discovery-to-Held-Out generalization | **Complete** | 10 independent Held Out seeds, frozen candidates, no retuning during evaluation |
| 3 | Joint MSE/Q95 and Pareto dominance | **Complete** | DE is nondominated in 18/18 blocks |
| 4 | Training-seed robustness/rank uncertainty | **Complete** | Crossed 10 training ×10 evaluation grid and ranking sensitivities |
| 5 | Computational cost/efficiency | **Partially complete** | Verified 900 nested-HPO archives, 86,400 cost entries, 1,298 historical Actions jobs; **original optimizer-specific final-fit elapsed time unavailable** |
| 6 | Independent reviewer replication | **Complete** | Independent R checks of original contrasts and sign-flip sensitivity |
| 7 | Crossed-seed uncertainty, two-way bootstrap | **Complete as sensitivity** | Approximate 10×10 random-effects and two-way bootstrap; not distribution free |
| 8 | Joint practical significance | **Exploratory complete** | 1% and 5% thresholds are posthoc; joint adjustment within pair/direction only |
| 9 | Independent deterministic benchmarks | **Complete, inferential caveat** | 288 posthoc optimizer/control contrasts; Stage 12's 216-test calibration **does not validate all 288 controls** |
| 10 | Q95 Monte Carlo precision | **Complete** | Recovered original 500 draws per scenario; precision not coverage of between-method inferential CIs |
| 11 | Global multiplicity/maxT permutation sensitivity | **Analysis complete; assumption caveat** | Joint sign symmetry/cross-block dependence not proven |
| 12 | Known-truth CI, null, multiplicity, selection-aware calibration | **Conditional surrogate analysis complete; original full pipeline open** | 20,480 null calibration replicates plus disjoint 4,096 validation replicates in three regimes; calibrated Holm/minP and CI **passed surrogate gates**, but HPO and selected weight fitting were not replayed |
| 13 | Scientific tables, source inventory, publication figures | **Produced; manuscript layout pending** | Immutable CSV, SVG, PNG and SHA manifests in R1 |
| 14 | Manuscript Results integration | **Pending** | Design logical exposition and add sourced findings to **one** canonical paper on `main` only |

## Primary verified results

- Original design: 6 distributions ×3 sample sizes ×4 engines (GA, NSGA-II, DE, Dirichlet); originally frozen 10 training seeds ×10 independently evaluated seeds and 241 supported scenarios. Original results and confirmatory tests were not altered by the follow-ups.
- **DE is Pareto-nondominated in 18/18** blocks, GA in 0, NSGA-II in 1, Dirichlet in 0, according to the preserved results.
- **DE improves both metrics over convex-MSE in 13/18 blocks** (72.2%); gains are original descriptive values. Median relative gains over that benchmark are **3.52% in MSE** and **4.21% in Q95**. The **original** Holm comparison flags these 13 blocks, but should not be advertised as fully calibrated selection-aware inference.
- Distribution detail: lognormal, inverse Gaussian, ex-Gaussian and ex-Wald each show DE's dual-metric advantage at all three sample sizes; Weibull does so only at n=200; normal at none. This is the scientifically useful counterexample.
- Frozen training-to-Held-Out ranking is strongly stable, with DE showing zero mean absolute rank shift in both metrics in the R1 method summary.
- Against the **local deterministic** control, DE's original posthoc Holm table shows joint improvement in 18/18 blocks. Label as the existing posthoc 288-control analysis, **not** as recalibrated Stage 12 evidence.
- Stage 5A verifies original nested-HPO objective evaluations of **110,113,525 GA**, **110,115,200 NSGA-II**, **109,026,425 DE**, and **47,576,975 Dirichlet**, from 900 archives and 86,400 inner-fold trial records. Trials have observed `elapsed_seconds` sums; they must not be interpreted as original optimizer-specific final Discovery fit time.
- Stage 5B recovered **1,298 original Actions jobs** and **18,303 original job steps**. Again, whole-job duration is not unique per-optimizer final-fit cost.
- The original crossed-t9+Holm familywise error in the independent surrogate global null is **22.80%** against the intended 5%. After **20,480** empirical null calibration draws per block, independent holdout results are **2.98% for calibrated Holm**, **4.13% for conservative global minP**, and **4.22% for calibrated BH** in the global null. Under mixed null, calibrated Holm FWER is **1.56%**, while BH FWER is **59.77%** but its mixed-null **FDR is 0.84%**: **never confuse FDR and FWER**.
- Pooled synthetic global-null 95% marginal CI coverage improves from **93.67% nominal t9** to **94.99% empirically calibrated**. Other synthetic regimes show approximately 95.02% and 94.93%.
- Original 216 fixed candidate contrasts yield **130 posthoc surrogate-calibrated Holm support flags**, **82 conservative global minP flags**, **177 calibrated BH flags**. These are *conditional on the fitted empirical surrogate*, NOT a new preregistered confirmation of all original optimizer effects.

## Proposed Results section narrative — exact reader sequence

### RQ1.1 — What we compared and which estimands are fixed

Opening paragraph: explain the 18 factorial distribution/size blocks, four search methods, independent Held Out scoring of 10 frozen candidates per engine, and simultaneous MSE and upper-tail Q95 objectives. Keep it readable; point to Methods rather than repeat implementation internals.

**Presentation:** a small design schematic and one concise source-completeness statement. Main paper Figure 1 should explain data flow; Figure 2 should show selection/training vs genuinely independent evaluation and the 241 support/80 reserved split.

### RQ1.2 — Who performs best on the two objectives?

Show 18-block Pareto classifications and four-method performance summary. Explain DE nondominance in all 18, while other engines sometimes lose one or both metrics. Define nondominance in plain language; identify uncertainty separately.

**Presentation:** compact primary Table 3 with 4 methods × Pareto/joint wins/relative gains; use the existing SVG `figure_RQ1_pareto_and_deterministic_control.svg` after editorial review.

### RQ1.3 — Which regimes warrant optimization rather than a deterministic benchmark?

Make the **normal counterexample** central: convex-MSE wins on both losses in the three normal blocks. Show the lognormal, inverse Gaussian, ex-Gaussian and ex-Wald DE wins; explicitly identify the Weibull boundary.

**Presentation:** primary **6×3 heatmap** colored by DE relative gain over convex-MSE for *both* MSE and Q95 (small two-panel figure), with n=200/1000/3000. Companion Table 4 holds the 18 blockwise values and signs. This heatmap is proposed, **not claimed to exist yet**.

### RQ1.4 — Do relative rankings generalize and persist across independently tested seeds?

Show Discovery-versus-Held-Out rank stability, crossed training/evaluation variance sensitivity, independent paired seeds and original Q95 Monte Carlo precision. Distinguish scenario uncertainty from candidate/seed variation.

**Presentation:** one focused uncertainty plot or compact table; send all 216 original contrasts/216 joint-sensitivity rows to Supplement.

### RQ1.5 — Is additional quality worth the optimization cost?

Compare declared versus actual objective budget and recovered HPO costs from all 900 verified nested archives. State that these represent HPO/tuning costs, **not full end-to-end per-engine final-fit wall-clock efficiency**. Explain cheaper but weaker Dirichlet, tradeoff of computation vs joint accuracy.

**Presentation:** compact main-text table or inline sentence, full original 86,400 costs and Actions timings in Supplement.

### RQ1.6 — What does calibrated inference support, and what does it limit?

Report the original nominal calibration weakness, independent synthetic known-truth correction, calibrated coverage and FWER/FDR, and the stricter posthoc 82 globally-minP-supported original frozen contrasts. Clearly separate empirical calibration within the synthetic crossed-effect reference from nominal claims about the actual optimizer-selection pipeline.

**Presentation:** one main or supplementary Stage 12 FWER/coverage figure and a short main-text caution. Do **not** lead the paper with 216/216 original Holm flags as if they represented validated nominal 5% familywise inference.

### RQ1.7 — Answer and boundary for the next research question

Conclude with method selection depending on regime; DE is a strong frozen multiobjective solution on tested support, deterministic convex-MSE is preferable in normal blocks, and the estimated inferential evidence has an explicit conditional calibration scope. Hand off separate Stress/real-world/generalization claims only where their independent source experiments support them.

## Planned primary paper objects

1. **Methods Figure 1:** experiment inputs → Discovery/selection → frozen candidates → independent evaluation → MSE/Q95/inference.
2. **Methods Figure 2:** training/evaluation split and hierarchical scenario/seed structure, plus 241 support vs 80 reserved Stress scenarios.
3. **Methods Tables 1–2:** factorial design, outcome definitions, engine/budget/reference configuration. Reorganize previously drafted tables without inventing design facts.
4. **Results Table 3:** four method aggregate summary (existing source table).
5. **Results Figure 3:** Pareto frontier + deterministic reference (existing SVG/PNG).
6. **Results Figure 4:** DE regime-dependent family × n heatmap (**to create during manuscript integration**).
7. **Results Table 4:** 18-row DE MSE/Q95 benchmark signs and magnitudes from original frozen scores.
8. **Results Figure 5 / Supplement:** calibrated FWER and 95% interval coverage (Stage 12 final SVG/PNG available).
9. **Supplement:** 72 method-family-sample rows, original 216 comparisons, 288 deterministic controls, 648 known-truth calibration rows, 900 HPO source lineage files, 86,400 HPO costs, job/step timing, checksums and uncertainty assumptions.

## What remains before manuscript readiness

1. **Editorial integration:** write RQ1 in the one canonical KBS manuscript on `main`, reconstruct primary tables/figures, and align all paragraphs, captions, units and citations.
2. **Unresolved full-pipeline inference:** original HPO/W reselection under known-truth repeats **was not performed**; if fully selection-aware nominal coverage is essential to claims, new end-to-end known-truth experiments or a narrower estimand/inferential statement is required. Do not silently relabel surrogate calibration as this missing experiment.
3. **Unresolved optimizer-specific final-fit wall time:** source data do not verify it. Keep compute fairness limited to measured objective work and HPO trial elapsed summaries; never fabricate end-to-end timing.
4. **External validity:** 241 support scenarios and the six families are the relevant scope of these Q1 statements. Stress and Real World belong in independently sourced sections.
5. **Journal polish:** ensure main Results has a causal narrative, not a recitation of all intermediate jobs; tables should explain what evidence means before inferential detail.

## Immutable source paths

- Original paired Held Out: `R1/runs/44307352615/`
- Discovery/Held Out and Pareto: `R1/runs/44310024979/`
- Independent reviewer and crossed-seed sensitivity: `R1/runs/44313738898/`, `R1/runs/44318493492/`
- Original deterministic controls and MC Q95 precision: `R1/runs/44322411124/`
- Integrated four-method scientific result tables and figures: `R1/runs/44324757704/synthesis/`
- Verified HPO costs, historical timings and Stage 12 feasibility: `R1/runs/44331514516/`
- Stage 12 first synthetic known-truth replay: `R1/runs/44340092503/`
- Stage 12 disjoint validation: `R1/runs/44343019150/`
- **Stage 12 final high-precision conditional inference and immutable results:** `R1/runs/44344323290/`

**Decision:** The original Q1 observations and their complete conditional Stage 12 synthetic calibration support a carefully qualified publication narrative. Q1 is **ready for Results drafting with inferential limitations**, not yet for an unqualified assertion of full original selection-aware nominal statistical validation.
