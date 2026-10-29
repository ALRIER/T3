#!/usr/bin/env python3
"""Fail-closed static integration contract for T2 V3 B3. No scientific inputs changed."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
def src(p):
    path=root/p
    assert path.exists(), f'Missing B3 dependency: {p}'
    return path.read_text()
def need(p, *tokens):
    content=src(p)
    for token in tokens:
        assert token in content, f'B3 CONTRACT FAIL {p}: {token}'
    return content
plan=need('R/00_shared/config.R','discovery=0:9','heldout=10:14','stress=15:19')
adapter=need('R/00_shared/v3_scientific_adapter.R','t2_v3_read_scenario','scenario_%04d.rds','t2_v3_validate_scenario')
resource=need('R/00_shared/t2_v3_b3_resources.R','t2_b3_ram_guard','t2_b3_inputs_manifest','memory.current','memory.peak')
inference=need('scripts/v3_confirmatory_inference.R','t2_b3_inputs_manifest','t2_b3_ram_guard','t2_v3_read_scenario','t2_v3_null_fpr','t2_v3_adjust_inference','t2_b3_publish','write.table','rm(sc,z)')
statistics=need('R/00_shared/v3_inference.R','q95','p.adjust','BH','holm','ci_lower','ci_upper','joint_familywise_fpr')
real=need('scripts/t2_v3_b3_realworld_scoring.R','t2_b3_inputs_manifest','t2_b3_ram_guard','t2_v3_infer_scenario','t2_v3_null_fpr','parent_dataset_id')
parent=need('scripts/t2_v3_b3_realworld_parent_inference.R','parent_dataset_id','p.adjust','q_BH','parent_inference_T2_V3_B3.csv')
discovery=need('R/00_shared/v3_downstream.R',"lapply(ids,function(id)t2_v3_read_scenario")
for stage,p,role in [
 ('heldout','.github/workflows/v3-heldout-production.yml','heldout'),
 ('stress','.github/workflows/v3-stress-production.yml','stress')]:
    text=need(p,'scripts/v3_confirmatory_inference.R',f' {role} ')
    assert 'scripts/v3_'+stage+'_frozen_production.R' not in text, 'Old non-inferential runner'
need('.github/workflows/t2-v3-b3-realworld-full.yml','t2_v3_b3_realworld_scoring.R','t2_v3_b3_realworld_parent_inference.R')
need('.github/workflows/t2-v3-b3-heldout-stress-full.yml','scripts/v3_confirmatory_inference.R','max-parallel: 4')
# Known, unresolved constraints must not be treated as satisfied:
assert 'FPR_scope=diagnostic_not_procedure_wide' in inference
assert 'empirical' in real.lower()
print('T2_V3_B3_STATIC_CONTRACT_PASS')
print('WARN: Monte Carlo role integration passes structure, but full statistical null calibration is NOT certified.')
print('WARN: archived confirmatory_v3_protocol.csv documents seed 21:26; B3 Monte Carlo role-specific seed plan uses 0:19.')
