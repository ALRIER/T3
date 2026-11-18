# Full cost accounting: archived input feasibility

All 720 frozen optimizer evaluation counts are already present in R1. They are **not** equivalent to total cost: Dirichlet and evolutionary methods may differ in actual evaluations, and hyperparameter tuning overhead must be accounted for separately. Possible original HPO metadata archives have been indexed by name only; their runtime records are not yet verified.

Next: identify original run/job duration metadata and nested-HPO costs, preserve provenance for every comparison, and avoid treating nominal budgets as measured compute expense. No optimizer rerun is required for this inventory.
