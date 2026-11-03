#!/usr/bin/env python3
"""Partition one sample-size's complete shards into GH-valid matrix groups."""
import json
import sys
import csv
from pathlib import Path

ROWS = {'normal': 8, 'lognormal': 6, 'weibull': 12, 'invgauss': 9,
        'exgaussian': 27, 'exwald': 27}
all_shards = [dict(family=f, parameter_row=r, seed=s, n=n)
           for f, k in ROWS.items() for r in range(2, k + 1)
           for s in range(40, 50) for n in (200, 1000, 3000)]
assert len(all_shards) == 2490
sample_n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
if sample_n not in (200, 1000, 3000):
    raise SystemExit('sample_n must be one of 200, 1000, 3000')
all_shards = [x for x in all_shards if x['n'] == sample_n]
if len(all_shards) != 830:
    raise SystemExit(f'Expected 830 complete identities for n={sample_n}, found {len(all_shards)}')
shards_per_job = 4
grid_path = Path(__file__).resolve().parents[1] / 'config/T2_V3_B3_prospective_321_grid.csv'
with grid_path.open(newline='', encoding='utf-8-sig') as stream:
    support_ids = [int(row['scenario_id']) for row in csv.DictReader(stream)
                   if row['mechanism'] not in {'mixture_bimodal_near', 'mixture_bimodal_far'}]
if len(support_ids) != 241 or len(set(support_ids)) != 241:
    raise SystemExit('Frozen Discovery-support partition must contain 241 unique scenario IDs')
jobs = []
for i in range(0, len(all_shards), shards_per_job):
    job = {}
    for slot, shard in enumerate(all_shards[i:i + shards_per_job]):
        for key, value in shard.items():
            job[f'shard{slot}_{key}'] = value
    jobs.append(job)
if len(jobs) != 208 or len(jobs) > 256:
    raise SystemExit('GitHub matrix must cover 830 complete shards in <=256 runner jobs')
print(json.dumps({'include': jobs, 'sample_n': sample_n,
                  'scenario_ids': support_ids,
                  'expected_shards': len(all_shards),
                  'expected_runner_jobs': len(jobs)},
                 separators=(',', ':')))
