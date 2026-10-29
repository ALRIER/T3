from pathlib import Path
s=Path('scripts/t2_v3_b3_freeze_parents.py').read_text()
assert 'Historical V2 audit directory forbidden' in s
assert 'B3_new_outcome_blind_profile_matching' in s
assert "if r['empirical_profile'] in direct_profiles" in s
assert 'target!=664' not in s
sc=Path('scripts/t2_v3_b3_realworld_scoring.R').read_text()
assert 'nrow(allowed)!=664L' not in sc
assert 'parent_manifest' in sc
w=Path('.github/workflows/t2-v3-b3-realworld-full.yml').read_text()
assert 'freeze-parents:' in w
assert w.count('needs: [plan, freeze-parents]')==2
assert 'T2_V3_B3_fresh_rw_profile-' in w
assert '40142001843' not in w
assert 'T2_V3_B3_fresh_profiles' in w
assert 'run_id:Number(context.payload.inputs.b3_audit_run_id)' in w
assert 'b3_audit_run_id:' in w
print('T2_V3_B3_FRESH_PARENT_RECOLLECTION_CONTRACT_PASS')
