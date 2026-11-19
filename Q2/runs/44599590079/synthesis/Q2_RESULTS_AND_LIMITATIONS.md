# Q2 — Independent within-family regime analysis

## Status
All 18 original family × sample-size blocks passed completeness and SHA-256
checks. Exactly 180 original archived Held Out score ZIPs, the frozen original
Discovery benchmark map and 241 prospective supported scenario IDs were used.
**No new Discovery, score simulation or optimizer training was performed.**

## Primary question
How do distribution family, sample size, original contamination mechanism,
fraction and MAD-scaled severity affect the matched two-loss performance of
the original frozen composites relative to classical estimators?

## Scope and estimand
The principal analysis uses DE candidates trained and independently evaluated
WITHIN THE SAME distribution family; this is distinct from cross-family transfer
(Q3). Ten original training seeds are crossed with ten independent Held Out
evaluation seeds. Four engines and both original frozen reference policies are
retained as sensitivity, not conflated with the primary DE/own-reference analysis.

The original source grid contains six contamination mechanisms with 40 selected
fraction × severity settings each, plus one clean reference. It is NOT a full
seven-fraction by nine-severity factorial per mechanism: 23 of 63 possibilities
per mechanism were never sampled (138 missing mechanism-specific combinations).
Any interactions are descriptive/local within the observed design.

## Initial descriptive finding — NOT a new confirmatory Q2 claim
The DE vs original frozen classical benchmark panel includes 4320 independently
evaluated regime summaries at the original supported non-clean scenario level,
of which 39 (0.90%) show positive gains in BOTH
MSE and Q95 and 32 (0.74%) show at least 5%
descriptive gain on both metrics. The 5% practical threshold is exploratory.
The most favorable family/mechanism average for MSE is normal /
symmetric_t (-41.11%), and the least favorable
is invgauss / clustered_symmetric (-3988.85%).
These are observed associations, not causal effects or calibrated discoveries.

## Uncertainty audit
There are 2016 two-way crossed training/evaluation bootstrap panels
(2,048 replays each), including the clean reference. The prespecified analysis
inventory for this *posthoc* Q2 investigation contains 216 DE-vs-own mechanism
metric comparisons. The reported 216-family BH q-values are exploratory.
Uncertainties are conditional on the 40 fixed selected scenarios per mechanism.
They do not incorporate full original HPO selection, a validated Q2 global
dependency calibration, or a new evaluation sample. Q1 Stage 12 error-rate
calibration does NOT transfer to these Q2 panels.

## Scientific interpretation
Regime differences should be reported as a continuous two-objective response,
including adverse performance. Mechanism/fraction/severity interactions are
not identified over the 138 unobserved mechanism-specific cells. Comparisons
of model robustness under new parameters/contamination mechanisms and across
source families remain within Q3, not Q2.

## Permanent outputs
- Q2_TABLE_FAMILY_BY_MECHANISM_DE_OWN.csv
- Q2_TABLE_FAMILY_BY_SAMPLE_SIZE_DE_OWN.csv
- Q2_TABLE_FOUR_METHOD_BENCHMARK_SENSITIVITY.csv
- Q2_TABLE_LOCAL_NEIGHBOR_SENSITIVITY.csv
- Q2_PRIMARY_DE_216_EXPLORATORY_CONTRASTS.csv
- Q2_ALL_TWO_WAY_BOOTSTRAP_EFFECTS.csv
- Q2_ALL_FACTOR_PROFILES.csv
- Q2_ALL_OBSERVED_LOCAL_NEIGHBORS.csv
- 2 publication figures in both SVG and PNG, tied to the above original values
- SHA-256 verified block data in ../blocks, audit JSON and original lineage

## Q2-F manuscript integration
The publication integration job must use authorized write access to
ALRIER/Genetic_Algorithms. If such authorization is not present, these
manuscript-ready outputs are retained in Q2 and the Q2-F job fails visibly.
No duplicate canonical manuscript is created in T3.
