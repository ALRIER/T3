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
scenario_block = int(sys.argv[5]) if len(sys.argv) > 5 else 0
grid_path = Path(__file__).resolve().parents[1] / 'config/T2_V3_B3_prospective_321_grid.csv'
with grid_path.open(newline='', encoding='utf-8-sig') as stream:
    support_ids = [int(row['scenario_id']) for row in csv.DictReader(stream)
                   if row['mechanism'] not in {'mixture_bimodal_near', 'mixture_bimodal_far'}]
if len(support_ids) != 241 or not 0 <= scenario_block < 8:
    raise SystemExit('Invalid frozen transfer scenario-block plan')
block_size = (len(support_ids) + 7) // 8
expected_scenarios = set(support_ids[scenario_block * block_size:(scenario_block + 1) * block_size])
all_shards = [
    (fam, row, seed, n)
    for fam, maxrow in ROWS.items()
    for row in range(2, maxrow + 1)
    for seed in range(40, 50)
    for n in (200, 1000, 3000)
]
batch_size = (len(all_shards) + batch_count - 1) // batch_count
expected = { (x['family'],x['parameter_row'],x['seed'],x['n'],scenario_block)
             for x in all_shards[batch_index * batch_size:(batch_index + 1) * batch_size] }
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
    key = (row["family"], int(row["parameter_row"]), int(row["seed"]), int(row["n"]),
           int(row.get('scenario_block', -1)))
    if key in seen:
        raise SystemExit(f"Duplicate score shard manifest: {key}")
    score_path = manifest_path.with_name("scores.csv")
    if not score_path.is_file() or sha256(score_path) != row["scores_sha256"]:
        raise SystemExit(f"Score file missing or SHA mismatch: {score_path}")
    if not 1 <= int(row["scenario_count"]) <= 31 or int(row["training_seed_count"]) != 10:
        raise SystemExit(f"Unexpected score contract: {manifest_path}")
    try:
        manifest_scenarios = {int(x) for x in row['scenario_ids'].split(';') if x}
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"Invalid scenario ID list in {manifest_path}") from exc
    if manifest_scenarios != expected_scenarios or len(manifest_scenarios) != int(row['scenario_count']):
        raise SystemExit(f"Scenario coverage mismatch in {manifest_path}")
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
print(f"PARAMETRIC_TRANSFER_BLOCK_COVERAGE_PASS batch={batch_index}/{batch_count} block={scenario_block}: {len(seen)}/{expected_count}")
