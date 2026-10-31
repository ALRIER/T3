#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${T3_NESTED_RUN_IDS:?T3_NESTED_RUN_IDS is required}"
: "${T3_FAMILY:?T3_FAMILY is required}"
: "${T3_SEED:?T3_SEED is required}"
: "${T3_SAMPLE_N:?T3_SAMPLE_N is required}"

[[ "$T3_FAMILY" =~ ^(normal|lognormal|weibull|invgauss|exgaussian|exwald)$ ]]
[[ "$T3_SEED" =~ ^[0-9]$ ]]
[[ "$T3_SAMPLE_N" =~ ^(200|1000|3000)$ ]]

mkdir -p artifacts
pattern="t3-nested-${T3_FAMILY}-seed${T3_SEED}-n${T3_SAMPLE_N}-fold*"
IFS=',' read -r -a run_ids <<< "$T3_NESTED_RUN_IDS"
found=0

for run_id in "${run_ids[@]}"; do
  [[ -n "$run_id" ]] || continue
  [[ "$run_id" =~ ^[0-9]+$ ]] || { echo "Invalid Actions run id: $run_id" >&2; exit 2; }
  stage="$(mktemp -d "${RUNNER_TEMP:-/tmp}/t3-hpo-${run_id}.XXXXXX")"
  log="$stage/download.log"
  if gh run download "$run_id" --repo "$GITHUB_REPOSITORY" --pattern "$pattern" --dir "$stage" >"$log" 2>&1; then
    while IFS= read -r -d '' artifact_dir; do
      cp -a "$artifact_dir/." artifacts/
      found=$((found + 1))
    done < <(find "$stage" -mindepth 1 -maxdepth 1 -type d -name 't3-nested-*' -print0)
  elif grep -Fq 'no artifact matches any of the names or patterns provided' "$log"; then
    : # This source run may not contain a repaired key; later runs can supply it.
  else
    cat "$log" >&2
    rm -rf "$stage"
    exit 1
  fi
  rm -rf "$stage"
done

echo "T3_NESTED_ARTIFACT_DIRS_MERGED=$found"
