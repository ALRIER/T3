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
assert "inner_fold!=inner" in trial and "validation_ids<-outer_train[inner_fold==inner]" in trial
assert "outer_train<-ids[(ids %% 5L+1L)!=outer]" in trial
outer=read('scripts/t2_v3_b3_discovery_cv5_refit.R')
assert "Missing nested Optuna configuration" in outer and "chosen<-jsonlite::fromJSON(selected)$best_params" in outer
assert "cfg$discovery_weight_regularization_lambda<-as.numeric(chosen$regularization_lambda)" in outer
assert "t2_adaptive_stop" not in outer
nsga=read('R/02_discovery/nsga2.R')
comp=read('R/02_discovery/evolutionary_competitors.R')
assert "lambda=0" in nsga and "if(lambda>0)" in nsga
assert nsga.count("discovery_weight_regularization_lambda")>=1
assert comp.count("discovery_weight_regularization_lambda")>=3
flow=read('.github/workflows/t2-v3-b3-discovery-cv5-refit.yml')
assert flow.index("t2_v3_b3_nested_optuna.py")<flow.index("t2_v3_b3_discovery_cv5_refit.R")
assert "t2_v3_b3_cv5_stability_dro.R" in flow and 'max-parallel: 4' in flow
print('T2_V3_B3_NESTED_OPTUNA_REGULARIZATION_DRO_CONTRACT_PASS')
