#!/usr/bin/env python3
"""T3 cross-stage artifact compatibility gate; refuse old IDs and mismatched n."""
from pathlib import Path
import re,csv
root=Path('.')
grid=list(csv.DictReader((root/'config/T2_V3_B3_prospective_321_grid.csv').open()))
assert len(grid)==321 and [int(x['scenario_id']) for x in grid]==list(range(321))
paths={
 'producer':'R/01_monte_carlo/v3_generation.R',
 'adapter':'R/00_shared/v3_scientific_adapter.R',
 'downstream':'R/00_shared/v3_downstream.R',
 'discovery':'scripts/v3_discovery_production.R',
 'heldout':'scripts/v3_heldout_frozen_production.R',
 'stress':'scripts/v3_stress_frozen_production.R',
 'nested':'scripts/t2_v3_b3_discovery_cv5_refit.R',
 'nested_inner':'scripts/t2_v3_b3_nested_optuna_trial.R',
 'realworld':'scripts/t2_v3_b3_realworld_scoring.R'}
data={k:(root/p).read_text() for k,p in paths.items()}
for name in ('producer','adapter','downstream','discovery','heldout','stress','nested','nested_inner'):
 assert '0:120' not in data[name],f'{name} still consumes 121 IDs'
assert 't3_b3_grid321_v1' in data['producer'] and 't3_b3_grid321_v1' in data['adapter']
assert '321L' in data['adapter'] and '321L' in data['discovery']
assert "sprintf('n%d',n)" in data['discovery']
for stage in ('heldout','stress'):
 assert "sprintf('n%d',n)" in data[stage],f'{stage} reads unscoped W'
 assert '0:320' in data[stage]
assert 't2_v3_stream_scores' in data['heldout'] and 't2_v3_stream_scores' in data['stress']
assert 't2_v3_read_scenario' in data['adapter'] and 't2_v3_discovery_input' in data['downstream']
print('T3_321_CROSS_STAGE_PATH_AND_SCHEMA_GATE_PASS')
