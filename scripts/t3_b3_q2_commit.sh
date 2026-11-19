#!/usr/bin/env bash
# Persist one unique Q2 block (or synthesis) directly in Git, retrying races.
# No temporary Actions artifact storage and no overwrite of scientific sources.
set -euo pipefail
path="$1"
test -d "$path"
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add -- "$path"
if git diff --cached --quiet; then
  echo 'No new Q2 scientific files to commit' >&2
  exit 1
fi
git commit -m "Preserve original-data Q2 analysis $path from Actions $GITHUB_RUN_ID"
for attempt in $(seq 1 25); do
  if git push origin HEAD:main; then
    echo "Q2_PERMANENT_GIT_BACKUP_PASS $path attempt=$attempt"
    exit 0
  fi
  git fetch origin main
  git rebase origin/main
  sleep $((1+(attempt%7)))
done
echo "Q2 Git retention failure after 25 retries: $path" >&2
exit 1
