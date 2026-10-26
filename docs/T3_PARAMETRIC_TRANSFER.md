# Secondary intrafamily parametric-transfer study

This is not a retrospective reinterpretation of the core B3 claim.  The core
claim is regime-specific: a W is optimized on its declared base regime and
contamination portfolio.  The secondary study asks the stricter question of
whether that frozen W transfers to other base-parameter rows of the same
family.

`scripts/t3_b3_parametric_transfer_mc.R` generates only rows 2..K of
`build_param_grids()`; row 1 remains the core B3 training regime.  It uses
previously unused seeds 40..49 and the same predeclared Grid321.  The scoring
consumer must use frozen Discovery W and must not invoke fitting, Optuna, or
candidate selection.  Results are to be reported as transfer performance by
parameter row, never as proof of a universal estimator.
