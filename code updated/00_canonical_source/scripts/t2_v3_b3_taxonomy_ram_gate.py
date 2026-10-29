from pathlib import Path
w=Path('.github/workflows/t2-v3-b3-heldout-stress-full.yml').read_text()
assert 'false-positive-calibration:' in w
assert 'needs: inference' in w
assert 't2_v3_b3_null_calibration_aggregate.py' in w
a=Path('scripts/t2_v3_b3_null_calibration_aggregate.py').read_text()
assert 'diagnostic_only' in a
r=Path('scripts/t2_v3_b3_realworld_scoring.R').read_text()
assert 'candidate_cache<-new.env' in r
assert 'assign(cache_key' in r
d=Path('scripts/v3_discovery_winner_report.R').read_text()
assert 'candidate_taxonomy_T2_V3_B3.csv' in d
assert 'discovery_descriptive_candidate_role_only' in d
print('T2_V3_B3_TAXONOMY_NULL_RAM_CONTRACT_PASS')
