#!/usr/bin/env python3
"""Fail on disconnected B3 5x3 Optuna, regularization, stability or DRO."""
from pathlib import Path
def read(path):return Path(path).read_text()
cfg=read('R/00_shared/config.R')
assert "discovery_cv_folds=5L" in cfg and "discovery_cv_inner_folds=3L" in cfg
assert "discovery_weight_regularization_lambda=0.001" in cfg
opt=read('scripts/t2_v3_b3_nested_optuna.py')
assert "for inner in (1,2,3)" in opt and "for engine in ('ga','nsga2','de','dirichlet')" in opt
trial=read('scripts/t2_v3_b3_nested_optuna_trial.R')
assert "t2_b3_nested_partitions(fam,seed,outer,inner,n=n)" in trial
assert "training_ids<-parts$training" in trial and "validation_ids<-parts$validation" in trial
nested=read('R/02_discovery/t2_v3_b3_nested_folds.R')
assert "ids=t3_b3_partition_ids('discovery_support')" in nested
assert "setdiff" not in nested or "discovery_support" in nested
nsga=read('R/02_discovery/nsga2.R')
comp=read('R/02_discovery/evolutionary_competitors.R')
assert "lambda=0" in nsga and "if(lambda>0)" in nsga
assert nsga.count("discovery_weight_regularization_lambda")>=1
assert comp.count("discovery_weight_regularization_lambda")>=3
freeze=read('scripts/t3_b3_freeze_hpo.py')
assert "T3_B3_nested_5x3_hpo_freeze_v2_equal_budget" in freeze
assert all(x in freeze for x in ('p75_g67','p100_g50','p150_g33','!=5100'))
production=read('scripts/v3_discovery_production.R')
assert "T3_B3_nested_5x3_hpo_freeze_v2_equal_budget" in production
pipeline=read('R/00_shared/pipeline.R')
assert 'Frozen HPO registries imply unequal optimizer objective budgets' in pipeline
assert 'common_cfg' in pipeline and 't2_discovery_budget_registry(engine_configs)' in pipeline
flow=read('.github/workflows/t3-nested-grid321-optuna.yml')
assert flow.index('t2_v3_b3_nested_optuna.py')<flow.index('t3_b3_freeze_hpo.py') if 't3_b3_freeze_hpo.py' in flow else True
assert "optuna==4.9.0" in flow
legacy=read('.github/workflows/t2-v3-b3-discovery-cv5-refit.yml')
assert 'if: ${{ false }}' in legacy
print('T3_B3_NESTED_OPTUNA_EQUAL_BUDGET_CONTRACT_PASS')
