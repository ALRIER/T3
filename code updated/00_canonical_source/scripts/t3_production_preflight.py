#!/usr/bin/env python3
"""T3 preflight: fail closed until full 321-scenario producer and consumers exist."""
import ast, pathlib, re, sys
root=pathlib.Path('.')
needed=[
 'docker/Dockerfile.r-runtime','scripts/run_r_in_container.sh',
 'scripts/v3_montecarlo_stage.R','scripts/v3_discovery_production.R',
 'scripts/t2_v3_b3_generate_grid321.py',
 'scripts/t2_v3_b3_nested_optuna_trial.R',
 'R/02_discovery/t2_v3_b3_nested_folds.R',
 'R/02_discovery/t2_v3_b3_mad_detection.R'
]
missing=[p for p in needed if not (root/p).exists()]
assert not missing, f'Missing T3 components: {missing}'
mc=(root/'scripts/v3_montecarlo_stage.R').read_text()
adapter=(root/'R/00_shared/v3_scientific_adapter.R').read_text()
discovery=(root/'scripts/v3_discovery_production.R').read_text()
problems=[]
if re.search(r'0:120|121L',mc+adapter+discovery):
 problems.append('MC/discovery/adapter still enforce historical 121-scenario grid')
for f in (root/'.github/workflows').glob('*.yml'):
 s=f.read_text()
 if '40053612297' in s or '40132811105' in s:
  problems.append(f'{f}: hardcoded historical T2 run id')
 if 't2-hpo-redesign-v1' in s:
  problems.append(f'{f}: hardcoded historical branch')
print('T3_PREFLIGHT_FILES_PASS')
if problems:
 print('T3_NOT_PRODUCTION_READY')
 for p in problems: print('BLOCK:',p)
 sys.exit(2)
print('T3_FULL_PRODUCTION_PREFLIGHT_PASS')
