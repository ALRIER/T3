#!/usr/bin/env python3
"""Optuna inner-fold tuner for the strict B3 5x3 CV design."""
import argparse,json,pathlib,subprocess
import optuna
p=argparse.ArgumentParser()
p.add_argument('family');p.add_argument('seed',type=int);p.add_argument('outer',type=int)
p.add_argument('--trials',type=int,default=8)
a=p.parse_args()
if a.seed not in range(10) or a.outer not in range(1,6) or a.trials<1:raise SystemExit('Invalid nested CV configuration')
out=pathlib.Path('artifacts/T2_V3_B3_nested_optuna')/a.family/f'seed{a.seed:02d}'/f'fold{a.outer:02d}'
out.mkdir(parents=True,exist_ok=True)
for engine in ('ga','nsga2','de','dirichlet'):
 study=optuna.create_study(direction='minimize',sampler=optuna.samplers.TPESampler(seed=12000+a.seed*5+a.outer))
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
   cmd=['bash','scripts/run_r_in_container.sh','Rscript','scripts/t2_v3_b3_nested_optuna_trial.R',
        a.family,str(a.seed),str(a.outer),str(inner),engine,str(trialpath)]
   result=subprocess.run(cmd,capture_output=True,text=True)
   if result.returncode:raise RuntimeError(result.stderr[-2500:])
   scores.append(float(json.loads(result.stdout.strip().splitlines()[-1])['score']))
  return sum(scores)/3
 study.optimize(objective,n_trials=a.trials)
 best=study.best_trial
 result={'version':'T2_V3_B3','family':a.family,'seed':a.seed,'outer_fold':a.outer,
         'inner_folds':3,'engine':engine,'trial_count':a.trials,
         'best_score':best.value,'best_params':json.loads((out/f'{engine}_trial{best.number:03d}.json').read_text()),
         'scope':'Nested inner-fold model selection; outer fold never used for HPO'}
 (out/f'{engine}_best.json').write_text(json.dumps(result,indent=2))
 print(engine,best.value,flush=True)
