# Q2 — Scientific argument, winner taxonomy, and manuscript integration blueprint
Status: AUTHORING BLUEPRINT (not a completed inferential claim)
Date: 2026-11-19
Canonical science repository: ALRIER/T3, branch main, Q2/
Canonical article: ALRIER/Genetic_Algorithms, branch main, manuscript/main.tex
Run policy: no new workflows launched by this document. Computation and backups must occur in T3; the private manuscript repository is for final writing only.

## One-sentence RQ2 answer to test
Within the prospectively selected within-family contamination support, the usefulness of each frozen composite depends jointly on the distribution, sample size, mechanism, contamination fraction, severity, and original classical-reference policy. A positive outcome needs separate characterization of its loss trade-off, strength of statistical evidence, and persistence across the observed neighborhood.

**Do not write a conclusion claiming any method is universally superior; that is not the research premise.**

## Immutable original evidence and known limitations
- Original scientific Q2 A–E: `Q2/runs/44599590079/`; 18 original 6-family × 3-sample-size blocks; 180 source Held Out score archives; 241 supported scenario IDs per block (one clean, 240 contaminated); four engines; 10 frozen training weights per family-size-engine crossed with 10 independent evaluation seeds; two original benchmark policies (`own` = original Discovery-selected classical estimator, `mean` = sample mean).
- Q2 F3 follow-up: `Q2/F3/runs/44613985618/`; 18 recovered and SHA-256-audited blocks; 3,470,400 paired candidate/reference score cells, 34,704 mechanism/scenario/engine/reference summaries, 29,520 original observed local-edge outcomes, 144 side-by-side Q1–Q2 benchmark-policy rows.
- Q1 independent benchmark summary: `R1/runs/44324757704/synthesis/table_RQ1_72_method_family_sample_integrated.csv`. Its convex-MSE classical benchmark cannot be silently equated with Q2's scenario-dependent `own` reference.
- The clean condition is a distinct reference, NOT a seventh contamination mechanism. Six contamination mechanisms have 40 observed settings apiece. Each mechanism is only a subset of a 7×9 candidate grid; 23 combinations per mechanism were not evaluated, totaling 138 absent mechanism-specific cells.
- Prior Q2 A–E mean-of-cell-percent-gain definition gave DE 39/4320 two-loss descriptive wins versus own, 2376/4320 versus mean. F3 ratio-of-mean-loss definition gives 40/4320 and 2379/4320 respectively. Both are valid yet DIFFERENT descriptive estimands, not evidence of changed data. State the selected estimand and disclose sensitivity.
- F3 surrogate global-null exercise had 5.3223% independent estimated rejection under a nominal 5% threshold, with only 4096 validation worlds; no verified 5% full-pipeline familywise guarantee. Synthetic calibration conditions on fixed weights and selected support, does not repeat original nested HPO/reselection or recover original cross-block dependence.
- Existing `R/05_audits/hierarchical_taxonomy.R` declares `t2_taxonomy_v1`, BH adjustment by stage/level/benchmark/metric and an **absolute cross-stage** notion requiring Held Out, Stress and Real World. Preserve its meaning when importing the stage taxonomy: do not relabel a within-Q2 dual-loss descriptive win as an absolute historical winner.

## Four-dimensional reporting system

### Axis A — Identity and matching unit (who won?)
Every outcome must retain:
`source_family, evaluation_family, sample_n, method, training_seed, frozen_weight_id_or_verified_hash, evaluation_seed, scenario_id, benchmark_id, stage, metric, provenance`.
For Q2 use `source_family == evaluation_family`. Keep each original trained weight distinct (10 per family×sample×engine; 720 frozen models across all blocks); do not invent one "winning estimator" by pooling different training-seed candidates. Aggregated engine outcomes are summaries of members of an engine's candidate cohort, not necessarily properties of one model.

Verify that original candidate-to-weight identifiers are stable across Held Out, Stress, transfer and Real World *before* any cross-stage intersections. Do not treat an output-level engine label as proof of identical W across studies. Benchmark choice and original scenario identity must also match when a direct paired contrast is claimed.

### Axis B — Objective / Pareto class (what kind of win?)
Use the *same original candidate, benchmark, scenario, family, sample size and independent evaluation support* for each MSE/Q95 comparison.

Define gain for each metric from matched candidate/reference losses, with negative `candidate-reference` indicating improvement. State aggregation policy; use the ratio of mean losses for the new principal descriptive scenario layer, supplemented by original means of per-cell percentage gains.
Create mutually exclusive descriptive signs:
- `joint_strict`: MSE decrease AND Q95 decrease.
- `mse_only`: MSE decrease and Q95 not decreased (distinguish Q95 ties from losses).
- `q95_only`: Q95 decrease and MSE not decreased (distinguish MSE ties from losses).
- `neither`: no strict decrease in either.
- Report zero/tolerance ties separately using a declared numerical tolerance.
- Preserve two *independent* Pareto statuses:
  - candidate dominates benchmark if not worse on both, strictly better on ≥1;
  - benchmark dominates candidate if not worse on both, strictly better on ≥1;
  - neither dominates when outcomes trade off; equal if both tied.
- For competition among GA/NSGA-II/DE/Dirichlet, recompute frontier/nondominance under the same family-size-scenario-reference panel and declare whether engine values are per-frozen-candidate or prespecified aggregates. Non-dominated is not synonymous with "MSE-only winner." Do not confuse DE vs a reference with DE vs other engines.

### Axis C — Evidence strength (how confidently?)
Publish *two layers that do not overwrite each other*:
1. **Descriptive**: above sign/Pareto categories at original supported scenario resolution, with exact numerator, denominator, magnitude, relative loss, adverse-tail exposure, and ties.
2. **Inferential**: CI direction, original fixed-candidate adjusted BH q-values, Q2-specific null-surrogate calibration status, and whether the appropriate error-rate check passed.

BH-FDR is a multiple-testing error-control policy, NOT a third estimation objective and NOT an observed false-positive rate for a candidate. The original taxonomy uses favorable CIs plus per-metric BH adjustment to label supported MSE-only, Q95-only and joint wins. Do not convert global mechanism-level 216 exploratory contrasts into per-scenario significance: they have different statistical units. Recompute a declared candidate/mechanism-level family for four engines, two references and two metrics only when valid independent units and multiplicity definitions are explicitly established. Report all tests and correction scope, not a wins-selected subset. If a future empirical null calibration fails or has insufficient power, label the associated inference *exploratory/not independently calibrated*.

Possible evidence flags, not necessarily mutually exclusive: `descriptive_sign`, `favorable_95ci`, `BH_FDR_0p05_conditional`, `surrogate_null_calibration_status`, `full_pipeline_selection_adjusted_status`. A statistically nonsignificant contrast is **inconclusive**, not proof of no benefit. A joint-MSE/Q95 win with BH evidence is not automatically an independently validated null-error-control "absolute" winner.

### Axis D — Breadth and generalization (how far does the same success extend?)
The breadth dimension is orthogonal to objective and statistical strength:
- **Scenario-local**: original specific observed fraction×severity×mechanism cell.
- **Observed 1-hop neighborhood**: graph edges already defined *from original design covariates only*, while holding mechanism and one axis fixed. Check whether the **same fixed weight** retains its outcome in both cells, not whether a different seed/model wins nearby.
- **Observed multi-hop neighborhood**: largest connected component, maximum graph-distance extension, supported-neighbor retention and denominator of eligible observed neighbors; same candidate identity and reference policy. No interpolation over missing cells.
- **Within-family**: persistence across observed scenarios/mechanisms and replicated evaluation seeds in the same evaluation family; separate models fitted for different n. Across-n evidence is engine-level consistency, NOT identical-W universality unless original weights really match.
- **Within-tested-support universal**: exceptionally strict 100% coverage by a *single* frozen candidate over a clearly enumerated, fixed eligible original support (e.g., all 240 contaminated cells of its own family-size panel), under one predeclared metric/evidence/benchmark policy. A nonuniversal candidate may still have meaningful localized stability. Never call this universal across unseen support or all distributions.
- **Cross-family, unseen structural shifts, real-world parents, cross-stage absolute**: Q3/Q4/external Results evidence. The existing `docs/T3_TRANSFER_TAXONOMY.md` distinguishes independent within-family replication, withheld near/far-bimodal shifts, source×destination transfer and real-world profile-matched parent units. Include a brief boundary handoff in Q2, with references to Q3 or the generalization section, not duplicated Q2 counts.

Conservatively distinguish coverage from inference: a high neighborhood win fraction is a descriptive stability metric, not another BH hypothesis. If neighborhood search itself becomes a posthoc selector for only favorable regions, report it as exploratory and avoid claiming prespecified significance.

## Recommended Q2 Results argument — seven movements

**Q2.1 What counts as a win?** Lead with the original scientific question and the tested support. Explain unit of comparison, frozen estimator identity, same-origin benchmark, two estimation losses, the objective × evidence × breadth taxonomy and why BH handles false discoveries rather than adding a third loss. Define original `own` as primary and `mean` as sensitivity.

**Q2.2 Who wins and at what strength?** Present four engines with the full mutually exclusive MSE-only/Q95-only/joint/neither distribution per benchmark, Pareto dominance/nondominance separately, and actual benefit magnitudes. Keep every negative and neutral case in the denominator. Show per-model counts and engine summaries without blending different weights into a fictitious universal model.

**Q2.3 Where do victories occur?** Factor results by six generating families, three n values, six contamination operators, observed fractions and MAD-scaled severities. Show primary selected-classical and secondary sample-mean references. Lead with robust ratios and actual loss differences; retain adverse tails and benchmark-dependent counterexamples. Distinguish 40-vs-39 descriptive estimand choices in notes, not as competing datasets.

**Q2.4 Do winners survive neighboring conditions?** Use the pre-outcome adjacency graph, 1-hop and multi-hop retention of the *same frozen W*, and graph-component summaries. Separate stability of point estimates from statistical evidence. Identify fragile isolated favorable cells and contiguous pockets without extrapolating to 138 absent settings.

**Q2.5 Are any winners broadly or universally robust?** Show eligible denominators, whether any **same candidate** covers all its original Q2 support under the same benchmark, mechanism and loss criterion. Distinguish method-level consistency across n from model-level universality. Universal counts of zero are scientifically informative; do not force a winner.

**Q2.6 What survives inference scrutiny?** Present conditional crossed-seed CIs, observed BH-FDR tiers where valid, calibration/rejection and Q95 MC uncertainty limitations. Explicitly disclose original selection effects and the unverified full-pipeline error guarantees. Distinguish uncertainty in the fixed score panels from independent stage generalization.

**Q2.7 What does Q2 establish—and not establish?** Provide a restrained conditional-estimator-use principle: method choice depends on tested regime and benchmark. Do not advertise an outcome-trained selector as an externally validated decision rule. Hand off new families, withheld contamination, Stress, real-world and cross-stage absolute evidence to Q3/Q4.

## Manuscript objects / priority

Main paper:
1. **Q2 Table A — Taxonomy and reference policy**: four engines × two references; columns eligible, MSE-only, Q95-only, joint, neither, candidate/benchmark Pareto relation, with descriptive and inferential denominators kept distinct.
2. **Q2 Table B — Regime and breadth**: 18 family×sample blocks, joint/MSE/Q95 win rates, robust loss magnitudes, candidate-level observed-neighborhood retention, and stringent tested-support coverage.
3. **Q2 Figure A — Mechanism×family winner classes**, paired with MSE/Q95 magnitude and a separate reference-policy comparison, not a saturating average-% heatmap.
4. **Q2 Figure B — Observed-grid neighborhood stability**, with only sampled points and adjacent edges; label connected pockets, no fabricated cells.
5. **Q2 Figure C — Evidence tiers/uncertainty and heavy adverse tails**, cleanly indicating descriptive outcomes versus valid BH and synthetic-only calibration.

Supplement:
- full individual frozen-candidate 720-W identity and per-scenario taxonomy (with checksum manifests);
- Q2 comparator crosswalk (Q1 convex-MSE vs Q2 own vs mean), explicitly side-by-side until exactly matched benchmark values become available;
- complete regime×mechanism×n×engine tables; original local adjacency, graph-component counts and uncertainty panels; error-rate calibration assumptions;
- provenance for all original 241 scenario IDs, 180 input archives, and 138 unobserved mechanism-specific combinations.

Existing canonical LaTeX targets:
- keep exactly one `\label{sec:q2_results}` and preserve existing Q2 appendix `\label{app:q2_detail}`;
- replace or expand existing family-size table `\label{tab:q2_family_size}`, with fully recomputed values and definition changes declared; don't silently overwrite primary original evidence;
- revise the existing Q2 figures, captions, and Discussion after science gates pass.
- Never create a duplicate manuscript; prepare source+figures in T3 and make one controlled publication update in `ALRIER/Genetic_Algorithms/main/manuscript/`. No new private-repo Actions-based scientific analysis.

## Exact computation/back-up sequence for the next agreed T3 follow-up
Gate 0: Freeze the four reporting axes, numerical tolerance, primary aggregation, eligible denominators, candidate ID matching, original BH family scopes and independent unit; document any posthoc choices as exploratory.
Gate 1: Reconstruct original 720 distinct candidate weight identities from original preserved Q2 score records; compare to available original Discovery registries where required. For each family/sample block, verify 10 candidate training seeds × 10 independent eval seeds and 241 scenario values.
Gate 2: Enumerate per-W and per-engine descriptive sign/Pareto categories using both original reference policies. Independent comparison to Q1 is a separate crosswalk, not exact matched contrast without reference-level scores.
Gate 3: Evaluate 1-hop/multi-hop adjacency and within-support universality, reporting eligible-universe/coverage of same W, preserving the 138 unsupported cells as missing.
Gate 4: Reuse BH-FDR procedures at compatible independent analysis units; do not transfer the 216 DE-own mechanism panel q-values to 34,704 scenario summaries or assert a predeclared global family retrospectively. Use new Q2-specific null/coverage sensitivity analysis as diagnostics, not full-pipeline guarantees.
Gate 5: Independently audit R/Python numerical categories and source hashes, verify all 18 blocks, publish tables, figures, scientific limitations and checksum manifest to a **new** unique `Q2/F3/runs/<run_id>/taxonomy/` location on T3/main. Preserve original Q2/F3 blocks and synthesis without rewriting.
Gate 6: Only when all source/scientific gates are verified, integrate the polished Q2 Results, Discussion, appendix, figures and captions into the one canonical private paper. Q3/Q4 carry cross-family, reserved Stress and external/outcome-blind generalization.

## Scientific stop conditions
Stop the specific claimed analysis (not the entire recovered experiment) if model identity across stages cannot be verified; if a benchmark switches without an explicit policy; if a candidate with a different W is used to claim one model's neighborhood extension; if cross-stage parent/evaluation units are mixed; if BH family and independent units are undefined; if unmatched original data are represented as exactly paired; or if any synthetic surrogate validation is advertised as fully selection-adjusted inferential confirmation.

## Editorial bottom line
The Q2 narrative is not "DE won X scenarios." It is "the original four fixed search methods give different, regime-local loss trade-offs; the strength, statistical support, and neighborhood breadth of those effects vary with distribution, contamination and benchmark. Strict universal/cross-stage claims require additional distinct evidence." A large, statistically careful Q2 is justified, but do not duplicate Q3 transfer or Q4 external validation findings.
