#!/usr/bin/env bash
# Original data only; neither Monte Carlo simulation nor training is permitted.
set -euo pipefail
MODE="$1"
FAMILY="$2"
N="$3"
[[ "$N" == "200" || "$N" == "1000" || "$N" == "3000" ]] || { echo "Invalid sample size"; exit 2; }
git lfs install --local
case "$MODE" in
  controls)
    [[ "$FAMILY" != "all" ]]
    git lfs pull --include="data-archive/heldout/actions/actions-*_t3-b3-heldout-$FAMILY-s*-n$N-run41208513291.zip/part-*.lfs" --exclude=""
    for s in {10..19}; do
      python scripts/t3_b3_r1_restore_sources.py controls "$FAMILY" "$N" "$s" "incoming/controls/seed$s"
    done
    python scripts/t3_b3_r1_deterministic_from_original.py block \
      --family "$FAMILY" --n "$N" \
      --source incoming/controls --output "out/controls/$FAMILY-n$N"
    ;;
  q95)
    [[ "$FAMILY" != "all" ]]
    git lfs pull --include="data-archive/montecarlo/actions/actions-*_b3-mc-heldout-$FAMILY-s*-n$N-run40239277660.zip/part-*.lfs" --exclude=""
    git lfs pull --include="data-archive/discovery/actions/actions-*_t3-b3-discovery-bundle-n$N-run41487091262.zip/part-*.lfs" --exclude=""
    for s in {10..19}; do
      python scripts/t3_b3_r1_restore_sources.py mc "$FAMILY" "$N" "$s" "incoming/mc/seed$s"
    done
    python scripts/t3_b3_rq1_followup.py restore-discovery \
      --archive-root data-archive/discovery/actions --n "$N" --output incoming/discovery
    bash scripts/run_t3_default_analysis.sh Rscript \
      scripts/t3_b3_r1_q95_from_original_mc.R "$FAMILY" "$N" \
      incoming/discovery incoming/mc "out/q95/$FAMILY-n$N"
    ;;
  cost)
    [[ "$FAMILY" == "all" ]]
    git lfs pull --include="data-archive/discovery/actions/actions-*_t3-b3-discovery-bundle-n$N-run41487091262.zip/part-*.lfs" --exclude=""
    python scripts/t3_b3_rq1_followup.py restore-discovery \
      --archive-root data-archive/discovery/actions --n "$N" --output incoming/discovery
    bash scripts/run_t3_default_analysis.sh Rscript \
      scripts/t3_b3_r1_full_cost_from_original.R \
      incoming/discovery "$N" "out/cost/n$N"
    ;;
  *) echo "Unknown immutable evidence analysis $MODE" >&2;exit 2;;
esac
