#!/usr/bin/env python3
from pathlib import Path
p=Path('.github/workflows/t2-v3-b3-heldout-stress-full.yml').read_text()
assert 'false-positive-calibration:' in p
assert 'needs: inference' in p
assert "needs.inference.result == 'success'" in p
assert 'T2_V3_B3_Heldout_Null_Calibration' in p
s=Path('scripts/t2_v3_b3_null_calibration_aggregate.py').read_text()
assert 'for seed in range(10,15)' in s
assert 'for n in (200,1000,3000)' in s
assert "if len(groups)!=10" in s
assert "status':'diagnostic_only'" in s
print('T2_V3_B3_POST_HELDOUT_CALIBRATION_CONTRACT_PASS')
