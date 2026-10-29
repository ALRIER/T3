#!/usr/bin/env python3
"""Emit the predeclared 40..49 x parameter-row x n transfer shard matrix."""
import json

ROWS = {'normal': 8, 'lognormal': 6, 'weibull': 12, 'invgauss': 9,
        'exgaussian': 27, 'exwald': 27}
include = [dict(family=f, parameter_row=r, seed=s, n=n)
           for f, k in ROWS.items() for r in range(2, k + 1)
           for s in range(40, 50) for n in (200, 1000, 3000)]
assert len(include) == 2490
print(json.dumps({'include': include}, separators=(',', ':')))
