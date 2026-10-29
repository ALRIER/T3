#!/usr/bin/env bash
# Build a journal-grade preservation envelope around an immutable Actions run.
set -euo pipefail
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 OWNER/REPO RUN_ID BACKUP_ROOT" >&2
  exit 2
fi
repo="$1"
run_id="$2"
root="$3"
meta="$root/provenance"
mkdir -p "$meta"

# API responses retain run, job, artifact and retention provenance as received.
gh api "repos/$repo/actions/runs/$run_id" > "$meta/actions_run.json"
gh api "repos/$repo/actions/runs/$run_id/jobs?per_page=100" --paginate --jq '.jobs[] | @json' > "$meta/actions_jobs.ndjson"
gh api "repos/$repo/actions/runs/$run_id/artifacts?per_page=100" --paginate --jq '.artifacts[] | @json' > "$meta/actions_artifacts.ndjson"
gh run view "$run_id" --repo "$repo" --log > "$meta/actions_complete.log"

python3 - "$root" "$repo" "$run_id" <<'PY'
import csv, hashlib, json, pathlib, sys
root=pathlib.Path(sys.argv[1]); meta=root/'provenance'
artifacts=[json.loads(line) for line in (meta/'actions_artifacts.ndjson').read_text().splitlines() if line]
with (meta/'artifact_inventory.csv').open('w',newline='') as h:
    w=csv.DictWriter(h,fieldnames=['artifact_id','artifact_name','size_in_bytes','created_at','expires_at','expired','archive_download_url'])
    w.writeheader()
    for a in artifacts:
        w.writerow({'artifact_id':a['id'],'artifact_name':a['name'],'size_in_bytes':a['size_in_bytes'],'created_at':a['created_at'],'expires_at':a['expires_at'],'expired':a['expired'],'archive_download_url':a['archive_download_url']})
rows=[]
for path in sorted(root.rglob('canonical.rds')):
    manifest=path.with_name('manifest.csv')
    rows.append({'relative_path':str(path.relative_to(root)),'bytes':path.stat().st_size,
                 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                 'manifest_present':manifest.exists()})
with (meta/'canonical_sha256_inventory.csv').open('w',newline='') as h:
    w=csv.DictWriter(h,fieldnames=['relative_path','bytes','sha256','manifest_present'])
    w.writeheader(); w.writerows(rows)
summary={'repository':sys.argv[2],'actions_run_id':sys.argv[3],
         'artifact_count_expected':len(artifacts),'canonical_files_present':len(rows),
         'raw_unit':'immutable canonical.rds plus manifest.csv','status':'in_progress_or_complete'}
(meta/'preservation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
PY

# Preserve the exact committed source without including unrelated current work.
sha=$(gh api "repos/$repo/actions/runs/$run_id" --jq '.head_sha')
gh api "repos/$repo/tarball/$sha" > "$meta/source_${sha}.tar.gz"
printf '%s\n' "$sha" > "$meta/source_commit.txt"
printf 'T3_PRESERVATION_METADATA_PASS %s %s\n' "$repo" "$run_id"
