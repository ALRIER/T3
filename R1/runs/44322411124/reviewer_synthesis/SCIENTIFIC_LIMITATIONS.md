# RQ1 preserved archive reviewer evidence

The original successful Held Out run includes separately scored, independently evaluated frozen deterministic controls. Previous scripts omitted that separate CSV; all 18 blocks were recovered with original SHA256-verified archives and the four evolutionary scores reproduced against previous R1 results.

Monte Carlo Q95 uncertainty was assessed by distribution-free binomial order-statistic intervals for the 500 original within-scenario squared losses. This is precision conditional on each scenario, not interval coverage for an optimizer effect. No synthetic samples were regenerated.

Optimizer cost is measured as actual objective evaluations; the included source metadata audit indicates whether independently documented measured optimizer wall-clock seconds exist. Missing HPO runtimes cannot be estimated reliably from nominal budgets and are flagged as not resolved.

The original 216 paired t contrasts and newly recovered 288 candidate-control contrasts use 10 independent evaluation seeds. Methods are averaged within evaluation seed and Holm is computed across the newly defined 288 contrasts. This is posthoc sensitivity, not a replacement confirmatory claim. A two-sided exact sign-flip across 10 seeds has minimum p=2/1024, larger than the first global 216-Holm critical threshold 0.05/216. Consequently absence of exact Holm discoveries is an unavoidable discreteness constraint.

True nominal confidence interval coverage and selection-aware error rates cannot be identified from the preserved selected-candidate aggregates alone; a distinct predeclared null/cross-fit replay would be needed. No such simulation was fabricated or silently represented as complete.
