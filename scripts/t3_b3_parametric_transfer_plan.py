#!/usr/bin/env python3
"""Emit one bounded matrix of immutable transfer scenario-block checkpoints."""
import json
import math
import sys
import csv
from pathlib import Path

ROWS = {'normal': 8, 'lognormal': 6, 'weibull': 12, 'invgauss': 9,
        'exgaussian': 27, 'exwald': 27}
all_shards = [dict(family=f, parameter_row=r, seed=s, n=n)
           for f, k in ROWS.items() for r in range(2, k + 1)
           for s in range(40, 50) for n in (200, 1000, 3000)]
assert len(all_shards) == 2490
batch_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
batch_count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
block_index = int(sys.argv[3]) if len(sys.argv) > 3 else 0
block_count = int(sys.argv[4]) if len(sys.argv) > 4 else 8
if batch_count < 1 or batch_index < 0 or batch_index >= batch_count:
    raise SystemExit('batch_index must be in [0, batch_count)')
if block_count != 8 or block_index < 0 or block_index >= block_count:
    raise SystemExit('scenario_block_index must be in [0, 8)')
batch_size = math.ceil(len(all_shards) / batch_count)
start = batch_index * batch_size
base = all_shards[start:start + batch_size]
grid_path = Path(__file__).resolve().parents[1] / 'config/T2_V3_B3_prospective_321_grid.csv'
with grid_path.open(newline='', encoding='utf-8-sig') as stream:
    support_ids = [int(row['scenario_id']) for row in csv.DictReader(stream)
                   if row['mechanism'] not in {'mixture_bimodal_near', 'mixture_bimodal_far'}]
if len(support_ids) != 241 or len(set(support_ids)) != 241:
    raise SystemExit('Frozen Discovery-support partition must contain 241 unique scenario IDs')
block_size = math.ceil(len(support_ids) / block_count)
scenario_ids = support_ids[block_index * block_size:(block_index + 1) * block_size]
include = [dict(**shard, scenario_block=block_index,
                scenario_block_count=block_count,
                scenario_ids=','.join(map(str, scenario_ids))) for shard in base]
if not include:
    raise SystemExit(f'Empty shard batch {batch_index}/{batch_count}')
print(json.dumps({'include': include, 'batch_index': batch_index,
                  'batch_count': batch_count, 'scenario_block_index': block_index,
                  'scenario_block_count': block_count,
                  'scenario_ids': scenario_ids,
                  'expected_shards': len(include)},
                 separators=(',', ':')))
