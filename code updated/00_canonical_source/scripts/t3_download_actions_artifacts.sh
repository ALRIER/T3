#!/usr/bin/env bash
# Download all artifacts from one immutable Actions run into separate folders.
set -euo pipefail
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 OWNER/REPO RUN_ID DESTINATION" >&2
  exit 2
fi
repo="$1"
run_id="$2"
destination="$3"
mkdir -p "$destination"
export repo run_id destination
gh api "repos/$repo/actions/runs/$run_id/artifacts?per_page=100" --paginate \
  --jq '.artifacts[] | [.id,.name] | @tsv' |
  xargs -r -P 6 -n 2 bash -c '
    artifact_id="$0"; artifact_name="$1"
    artifact_dir="$destination/$artifact_name"
    if [ -f "$artifact_dir/.download_complete" ]; then exit 0; fi
    mkdir -p "$artifact_dir"
    temporary_zip="$artifact_dir/.artifact.zip"
    gh api "repos/$repo/actions/artifacts/$artifact_id/zip" > "$temporary_zip"
    unzip -oq "$temporary_zip" -d "$artifact_dir"
    rm -f "$temporary_zip"
    touch "$artifact_dir/.download_complete"
  '
