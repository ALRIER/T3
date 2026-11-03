#!/usr/bin/env python3
"""Emit one bounded Actions matrix from the predeclared transfer shard plan."""
import json
import math
import sys

ROWS = {'normal': 8, 'lognormal': 6, 'weibull': 12, 'invgauss': 9,
        'exgaussian': 27, 'exwald': 27}
all_shards = [dict(family=f, parameter_row=r, seed=s, n=n)
           for f, k in ROWS.items() for r in range(2, k + 1)
           for s in range(40, 50) for n in (200, 1000, 3000)]
assert len(all_shards) == 2490
batch_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
batch_count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
if batch_count < 1 or batch_index < 0 or batch_index >= batch_count:
    raise SystemExit('batch_index must be in [0, batch_count)')
batch_size = math.ceil(len(all_shards) / batch_count)
start = batch_index * batch_size
include = all_shards[start:start + batch_size]
if not include:
    raise SystemExit(f'Empty shard batch {batch_index}/{batch_count}')
print(json.dumps({'include': include, 'batch_index': batch_index,
                  'batch_count': batch_count, 'expected_shards': len(include)},
                 separators=(',', ':')))
