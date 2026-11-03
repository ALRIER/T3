#!/usr/bin/env python3
"""Check one bounded parametric-transfer Actions batch without trusting filenames."""
import csv
import hashlib
import sys
from pathlib import Path

ROWS = {'normal': 8, 'lognormal': 6, 'weibull': 12, 'invgauss': 9,
        'exgaussian': 27, 'exwald': 27}

root = Path(sys.argv[1])
batch_index, batch_count, expected_count = map(int, sys.argv[2:5])
all_shards = [
    (fam, row, seed, n)
    for fam, maxrow in ROWS.items()
    for row in range(2, maxrow + 1)
    for seed in range(40, 50)
    for n in (200, 1000, 3000)
]
batch_size = (len(all_shards) + batch_count - 1) // batch_count
expected = set(all_shards[batch_index * batch_size:(batch_index + 1) * batch_size])
if len(expected) != expected_count:
    raise SystemExit(f"Plan/output mismatch: {len(expected)} != {expected_count}")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

seen = {}
for manifest_path in root.rglob("score_manifest.csv"):
    with manifest_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise SystemExit(f"Expected one score manifest: {manifest_path}")
    row = rows[0]
    key = (row["family"], int(row["parameter_row"]), int(row["seed"]), int(row["n"]))
    if key in seen:
        raise SystemExit(f"Duplicate score shard manifest: {key}")
    score_path = manifest_path.with_name("scores.csv")
    if not score_path.is_file() or sha256(score_path) != row["scores_sha256"]:
        raise SystemExit(f"Score file missing or SHA mismatch: {score_path}")
    if int(row["scenario_count"]) != 241 or int(row["training_seed_count"]) != 10:
        raise SystemExit(f"Unexpected score contract: {manifest_path}")
    seen[key] = (manifest_path, score_path)

if set(seen) != expected:
    missing = sorted(expected - set(seen))
    extra = sorted(set(seen) - expected)
    raise SystemExit(f"Batch coverage mismatch; missing={missing[:5]}, extra={extra[:5]}")

out = root / "parametric_batch_coverage.csv"
with out.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream)
    writer.writerow(["family", "parameter_row", "seed", "n", "score_manifest", "score_sha256"])
    for key in sorted(seen):
        manifest_path, score_path = seen[key]
        writer.writerow([*key, manifest_path.relative_to(root), sha256(score_path)])
print(f"PARAMETRIC_TRANSFER_BATCH_COVERAGE_PASS {batch_index}/{batch_count}: {len(seen)}/{expected_count}")
