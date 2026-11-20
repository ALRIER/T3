# Q2/F3 — Cross-family evidence recovery and scientific correction

## Corrected premise
The original study DID explicitly test family transfer: original Discovery-frozen W trained only on a source family are evaluated on new independently generated Held Out and Stress samples from the other five families without refitting. Within-family Q2 neighborhood fragility does NOT imply no cross-family successes. One frozen candidate can have partial, local or destination-specific improvements without being jointly superior in all original supported within-family scenarios.

## Direct code/data lineage in T3
- Discovery source models: scripts/v3_discovery_production.R (freezes ten W per source family and n, each with four engines).
- Cross-family scorer: scripts/v3_cross_family_frozen_production.R. Explicit setdiff(families, eval_family), original Discovery model-file SHA-256 check, independent evaluation MC SHA-256, and source_family / evaluation_family / transfer_scope columns.
- Launch workflow: .github/workflows/t3-b3-cross-family-transfer.yml.
- Original global Held Out artifact: data-archive/heldout/actions/actions-13178442769_t3-b3-pairwise-global-heldout-run41502642569.zip/.
- Original manuscript: tables tab:results_scope_rates and tab:results_transfer_matrix, plus figure fig:results_transfer.

## Original Held Out joint BH+CI evidence (original selected classical comparator)
- Same-family eligible: 173,520, supported wins: 877 (0.505%).
- Cross-family eligible: 867,600, supported wins: 5,069 (0.584%).
- The original directed six-by-six source-to-destination matrix accounts for both categories; the off-diagonal successes ARE original out-of-source-distribution tests.
- Counts are repeated candidate/scenario contrasts, NOT independent source-family scientific replications; original BH error guarantees remain conditional on its testing assumptions.
- Original historical Stress: 0 / 57,600 same-family, 6 / 288,000 cross-family.
- Original fresh Stress: 1,799 / 57,600 same-family, 4,913 / 288,000 cross-family.
- Different Stress panels involve different designs/seeds and must retain distinct testing families, not be directly attributed to one changed factor.

## Real World — original transfer design; numerical outcome retrieval is separate
- docs/T3_REALWORLD_PARENT_CHILD_PROTOCOL.md freezes and profiles 642 independent parent datasets (200 finance, 442 other) before candidate outcome scoring.
- Each parent is evaluated using original Discovery weights from all six source-family registries, with scopes within_regime, within_family_neighborhood, cross_family_transfer.
- scripts/t3_b3_realworld_full_consolidation.py confirms 720 original frozen W, original parent-level source- and destination-benchmark policies, 4,080 primary versus 14,880 secondary family-transfer contrasts per comparator-policy panel, and 642 parent clusters as the independent inferential unit.
- Empirical destination families are outcome-blind APPROXIMATE profile labels, not known true generating families; external validation targets a full-sample mean proxy, not a known true mean.
- Original Real World destination global taxonomy artifact ID 13542889733 and four-module validation artifact ID 13901031141 are preserved in T3 data-archive/realworld. Actual cross-family winning counts must be independently read and checked before manuscript reporting; do not invent numbers.

## Manuscript disposition
- Q2 within-family: 720 fixed candidates, 240 observed contaminated scenario support per family-size panel, and observed one-hop neighborhood retention.
- Broader generalization: directed source-family by unseen destination family Held Out and Stress, plus real-world source-family by empirical-destination profile and parent-level test.
- Strongest defensible conclusion: success is conditional but cross-family success EXISTS in original independently evaluated data; lack of universal within-support joint winners cannot be rephrased as universal failure to transfer.
- Discovery is training; independent Held Out/Stress establish test evidence; Real World is out-of-domain parent-level empirical evidence with different estimand and assigned family proxy.

## Audit status
Original Held Out transfer totals and code are confirmed. Source-catalog archive reconstruction and empirical family-scope numerical row accounting are being independently recovered by public T3 Actions. The archival recovery workflow is not a new simulation, optimizer fit or additional statistical test; any new Real World result numbers require a separate successful scientific source-table gate.
