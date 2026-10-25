#!/usr/bin/env python3
"""Optuna inner-fold tuner for the strict B3 5x3 CV design."""
import argparse,csv,json,math,os,pathlib,subprocess,tempfile
from collections import defaultdict
import optuna
p=argparse.ArgumentParser()
p.add_argument('family');p.add_argument('seed',type=int);p.add_argument('outer',type=int)
p.add_argument('n',type=int)
p.add_argument('--trials',type=int,default=8)
a=p.parse_args()
if a.n not in (200,1000,3000): raise SystemExit('Invalid sample n')
if a.seed not in range(10) or a.outer not in range(1,6) or a.trials<1:raise SystemExit('Invalid nested CV configuration')
out=pathlib.Path('artifacts/T2_V3_B3_nested_optuna')/a.family/f'seed{a.seed:02d}'/f'fold{a.outer:02d}'/f'n{a.n}'
out.mkdir(parents=True,exist_ok=True)
# Audit every completed inner-fold execution; never impute failed trials.
LEDGER_FIELDS=('family','seed','outer_fold','sample_n','engine','trial','inner_fold',
 'score','objective_evaluations','maximum_objective_evaluations',
 'training_scenarios','scenario_evaluations','elapsed_seconds','early_stop_saved',
 'budget_policy')
def atomic_csv(path,rows,fields):
 path=pathlib.Path(path)
 with tempfile.NamedTemporaryFile('w',dir=path.parent,prefix='.audit_',suffix='.csv',
                                  delete=False,newline='') as fh:
  temp=pathlib.Path(fh.name)
  writer=csv.DictWriter(fh,fieldnames=fields,extrasaction='ignore')
  writer.writeheader()
  writer.writerows(rows)
 os.replace(temp,path)
def validated_fold(raw,engine,trial,inner):
 needed=('score','objective_evaluations','maximum_objective_evaluations',
         'training_scenarios','scenario_evaluations','elapsed_seconds',
         'early_stop_saved','budget_policy')
 if any(k not in raw for k in needed):
  raise ValueError('Missing observed objective cost in Optuna fold')
 used=int(raw['objective_evaluations']);maximum=int(raw['maximum_objective_evaluations'])
 scenarios=int(raw['training_scenarios']);calls=int(raw['scenario_evaluations'])
 elapsed=float(raw['elapsed_seconds']);score=float(raw['score'])
 if not(0<used<=maximum and scenarios>=1 and calls==used*scenarios
        and int(raw['early_stop_saved'])==maximum-used
        and elapsed>=0 and math.isfinite(elapsed) and math.isfinite(score)
        and raw['budget_policy']=='B3_EQUAL_MAX_BUDGET_ADAPTIVE_V2'):
  raise ValueError('Inconsistent Optuna objective accounting')
 return dict(family=a.family,seed=a.seed,outer_fold=a.outer,sample_n=a.n,
             engine=engine,trial=trial,inner_fold=inner,score=score,
             objective_evaluations=used,maximum_objective_evaluations=maximum,
             training_scenarios=scenarios,scenario_evaluations=calls,
             elapsed_seconds=elapsed,early_stop_saved=maximum-used,
             budget_policy=raw['budget_policy'])
all_rows=[]
summary=[]
for engine in ('ga','nsga2','de','dirichlet'):
 study=optuna.create_study(direction='minimize',
   sampler=optuna.samplers.TPESampler(seed=12000+a.seed*15+a.outer*3+
                                     (200,1000,3000).index(a.n)))
 rows=[]
 def objective(trial):
  params=dict(population=trial.suggest_categorical('population',[75,100,150]),
    generations=trial.suggest_categorical('generations',[50,80]),
    mutation_rate=trial.suggest_float('mutation_rate',.08,.28),
    crossover_probability=trial.suggest_float('crossover_probability',.65,.95),
    regularization_lambda=trial.suggest_categorical('regularization_lambda',[.0001,.001,.01]),
    F=trial.suggest_float('F',.4,.85),CR=trial.suggest_float('CR',.55,.95),
    alpha=trial.suggest_float('alpha',.25,2.5,log=True))
  trialpath=out/f'{engine}_trial{trial.number:03d}.json'
  trialpath.write_text(json.dumps(params))
  scores=[]
  for inner in (1,2,3):
   cmd=['bash','scripts/run_r_in_container.sh','Rscript',
        'scripts/t2_v3_b3_nested_optuna_trial.R',
        a.family,str(a.seed),str(a.outer),str(inner),engine,str(trialpath),str(a.n)]
   result=subprocess.run(cmd,capture_output=True,text=True)
   if result.returncode:
    raise RuntimeError('Inner-fold execution failed; no cost imputed: '+result.stderr[-2000:])
   lines=[line for line in result.stdout.splitlines() if line.strip()]
   if not lines:raise RuntimeError('Inner-fold result absent')
   raw=json.loads(lines[-1])
   if raw.get('engine')!=engine or int(raw.get('inner',-1))!=inner:
    raise ValueError('Optuna child output identifies a different engine/inner fold')
   row=validated_fold(raw,engine,trial.number,inner)
   rows.append(row)
   atomic_csv(out/f'{engine}_fold_costs.csv',rows,LEDGER_FIELDS)
   scores.append(row['score'])
  return sum(scores)/len(scores)
 study.optimize(objective,n_trials=a.trials)
 completed={t.number for t in study.trials if t.state==optuna.trial.TrialState.COMPLETE}
 expected={(t,i) for t in completed for i in (1,2,3)}
 if {(x['trial'],x['inner_fold']) for x in rows if x['trial'] in completed}!=expected:
  raise RuntimeError('Completed Optuna trials lack inner-fold cost records')
 if len(completed)!=a.trials:
  raise RuntimeError('Not all requested Optuna trials completed')
 best=study.best_trial
 result={'version':'T3_B3_40_SEEDS','family':a.family,'seed':a.seed,'outer_fold':a.outer,
         'sample_n':a.n,'inner_folds':3,'engine':engine,'trial_count':len(completed),
         'best_score':best.value,
         'best_params':json.loads((out/f'{engine}_trial{best.number:03d}.json').read_text()),
         'scope':'Nested inner-fold model selection; outer fold never used for HPO'}
 (out/f'{engine}_best.json').write_text(json.dumps(result,indent=2))
 observed=[x for x in rows if x['trial'] in completed]
 actual=sum(x['objective_evaluations'] for x in observed)
 maximum=sum(x['maximum_objective_evaluations'] for x in observed)
 summary.append(dict(engine=engine,completed_trials=len(completed),
   inner_fold_runs=len(observed),objective_evaluations=actual,
   maximum_objective_evaluations=maximum,
   early_stop_saved=maximum-actual,
   scenario_evaluations=sum(x['scenario_evaluations'] for x in observed),
   elapsed_seconds=sum(x['elapsed_seconds'] for x in observed)))
 all_rows.extend(observed)
 atomic_csv(out/'all_inner_fold_costs.csv',all_rows,LEDGER_FIELDS)
 atomic_csv(out/'optuna_budget_summary.csv',summary,
  ('engine','completed_trials','inner_fold_runs','objective_evaluations',
   'maximum_objective_evaluations','early_stop_saved','scenario_evaluations',
   'elapsed_seconds'))
 print(engine,best.value,flush=True)
