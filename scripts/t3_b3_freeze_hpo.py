#!/usr/bin/env python3
"""Freeze one production HPO registry from five outer-fold inner-CV choices."""
import argparse, json, pathlib, statistics
from collections import Counter

p=argparse.ArgumentParser()
p.add_argument('family'); p.add_argument('seed',type=int); p.add_argument('n',type=int)
p.add_argument('--root',default='artifacts/T2_V3_B3_nested_optuna')
p.add_argument('--out',required=True)
a=p.parse_args()
if a.seed not in range(10) or a.n not in (200,1000,3000): raise SystemExit('invalid registry key')
continuous={'mutation_rate','crossover_probability','F','CR','alpha','regularization_lambda'}
BUDGET_DESIGNS={'p75_g67':(75,67),'p100_g50':(100,50),'p150_g33':(150,33)}
engines={}
for engine in ('ga','nsga2','de','dirichlet'):
    rows=[]
    for fold in range(1,6):
        f=pathlib.Path(a.root)/a.family/f'seed{a.seed:02d}'/f'fold{fold:02d}'/f'n{a.n}'/f'{engine}_best.json'
        if not f.exists(): raise SystemExit(f'Missing complete nested HPO fold: {f}')
        z=json.loads(f.read_text())
        if z.get('family')!=a.family or z.get('seed')!=a.seed or z.get('sample_n')!=a.n or z.get('engine')!=engine or z.get('inner_folds')!=3:
            raise SystemExit(f'Invalid nested HPO provenance: {f}')
        rows.append(z['best_params'])
    keys=set().union(*(x.keys() for x in rows))
    chosen={}
    for key in sorted(keys):
        values=[r[key] for r in rows]
        if key in continuous:
            chosen[key]=statistics.median(values)
        else:
            counts=Counter(values); chosen[key]=sorted(counts,key=lambda v:(-counts[v],str(v)))[0]
    design=chosen.get('budget_design')
    if design not in BUDGET_DESIGNS: raise SystemExit(f'Invalid equal-budget design for {engine}: {design}')
    chosen['population'],chosen['generations']=BUDGET_DESIGNS[design]
    if chosen['population']*(chosen['generations']+1)!=5100:
        raise SystemExit(f'Unequal objective budget in frozen registry for {engine}')
    engines[engine]=chosen
out={'protocol':'T3_B3_nested_5x3_hpo_freeze_v2_equal_budget','family':a.family,'seed':a.seed,
     'sample_n':a.n,'outer_folds':5,'inner_folds':3,
     'selection':'median_continuous_mode_discrete_across_outer_fold_inner_CV',
     'engines':engines}
target=pathlib.Path(a.out); target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print('T3_B3_FROZEN_HPO_REGISTRY_PASS',target)
