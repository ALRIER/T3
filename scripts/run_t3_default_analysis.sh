#!/usr/bin/env bash
# Single entry point for all new T3 R analyses, including R1-R4.
# Reuses immutable GHCR image already used by successful T3 workflows.
set -euo pipefail
source config/T3_DEFAULT_ANALYSIS_RUNTIME.env
if [[ -z "${T3_ANALYSIS_R_IMAGE:-}" ]] || [[ ! "$T3_ANALYSIS_R_IMAGE" =~ ^ghcr[.]io/.+@sha256:[0-9a-f]{64}$ ]]; then
  echo "Invalid immutable T3 analytical R image configuration" >&2
  exit 2
fi
# No mutable tags, image rebuilds, apt installs, or on-run R setup.
if [[ -n "${T2_R_IMAGE:-}" && "$T2_R_IMAGE" != "$T3_ANALYSIS_R_IMAGE" ]]; then
  echo "T2_R_IMAGE conflicts with the canonical pinned T3 analysis image" >&2
  exit 2
fi
export T2_R_IMAGE="$T3_ANALYSIS_R_IMAGE"
if [[ "$#" -lt 2 ]]; then
  echo "Usage: bash scripts/run_t3_default_analysis.sh Rscript <R_SCRIPT> [args...]" >&2
  exit 2
fi
exec bash scripts/run_r_in_container.sh "$@"
