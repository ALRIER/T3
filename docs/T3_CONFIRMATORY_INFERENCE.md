# T3 confirmatory inference boundary

Discovery is a training and model-construction stage.  It may report
optimization diagnostics, but it does not report BH-FDR winners, a
procedure-wide false-positive rate, or confirmatory p-values.

The only primary inferential outputs are created after frozen Discovery
weights are evaluated on disjoint seed roles:

* Held-out: seeds 10--19, on the 241-cell `discovery_support` partition.
* Stress: seeds 20--29, on the 80-cell `stress_exclusive` partition, made of
  the two bimodal mechanisms excluded from all Discovery fitting and tuning.

The same FDR calculation is required for Real-world after its parent-dataset
manifest and profiling map are frozen.  Its independent unit is the declared
parent dataset (with repeated draws/seeds averaged within parent), not a raw
row or bootstrap draw.  A real-world output without these fields is rejected
from final BH-FDR aggregation.

The prospectively fixed practical threshold is a 5% relative loss reduction
in both MSE and q95.  It creates additional `practical` and `assured_practical`
taxonomy labels; it never deletes descriptive or BH-FDR results.  The latter
requires the lower 95% confidence bound to be at least 5% for both metrics.

For each family, sample size, stage, candidate, and metric, the independent
unit is the evaluation seed.  Scenario and training-seed scores are repeated
measurements and are averaged before the paired seed-level comparison.  BH is
then applied to the complete predeclared candidate-by-metric panel in that
family/sample-size/stage group.  A positive result requires positive gain and
an adjusted q-value no larger than the declared alpha.

The former fixed-W label-exchange calculation is retained only as a clearly
labelled sensitivity diagnostic.  It is not used to assert global or
selection-aware false-positive control.  Such a claim would require replaying
the complete tuning, selection, and independent confirmation pipeline under a
null; it is not needed for the primary split-sample BH analysis and must never
be substituted for it.
