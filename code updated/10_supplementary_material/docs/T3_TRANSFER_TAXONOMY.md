# T3 transfer taxonomy

Every score carries `source_family`, `evaluation_family`, and
`transfer_scope`.  These labels are descriptive strata fixed before scoring;
they never select W or alter a p-value.

| Scope | Meaning | Evidential role |
|---|---|---|
| `within_family_training_descriptive` | Discovery portfolio | descriptive only |
| `within_family_independent_replication` | same portfolio, independent held-out seeds | confirmatory |
| `within_family_neighborhood_shift` | excluded near-bimodal mechanism | confirmatory stress |
| `within_family_structural_shift` | excluded far-bimodal mechanism | confirmatory stress |
| `cross_family_*` | frozen W evaluated on another generating family | confirmatory transfer, after independent scoring |
| `realworld_profile_matched_transfer` | frozen W evaluated on a pre-profiled parent dataset | parent-level BH-FDR |

Cross-family scoring is intentionally a separate matrix (`source_family ×
evaluation_family`) rather than an accidental merge of within-family results.
It uses frozen W only and does not refit, retune, or select models.
