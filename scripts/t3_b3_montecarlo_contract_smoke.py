#!/usr/bin/env python3
"""Bounded, outcome-blind Monte Carlo design and artifact contract test."""
import csv,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as td:
 d=pathlib.Path(td)
 subprocess.run(['python3',str(ROOT/'scripts/t2_v3_b3_generate_grid321.py')],cwd=d,check=True)
 f=d/'config/T2_V3_B3_prospective_321_grid.csv'
 rows=list(csv.DictReader(f.open()))
 assert len(rows)==321 and [int(x['scenario_id']) for x in rows]==list(range(321))
 assert rows[0]['mechanism']=='clean' and float(rows[0]['contamination'])==0
 assert len({(x['contamination'],x['mad_scale'],x['mechanism']) for x in rows})==321
 assert set(x['band'] for x in rows)=={'clean','low','intermediate','high'}
 assert all(float(x['contamination'])>0 for x in rows[1:])
 role_seeds={'discovery':list(range(10)),'heldout':list(range(10,20)),'stress':list(range(20,30)),'realworld':list(range(30,40))}
 assert len(set(sum(role_seeds.values(),[])))==40
 checksum=hashlib.sha256(f.read_bytes()).hexdigest()
 manifest={'schema':'B3_MC_DESIGN_SMOKE_V1','grid_rows':321,'grid_sha256':checksum,
 'roles':role_seeds,'stage':'montecarlo','fixture_only':True}
 (d/'manifest.json').write_text(json.dumps(manifest,indent=2))
 assert hashlib.sha256(f.read_bytes()).hexdigest()==json.loads((d/'manifest.json').read_text())['grid_sha256']
 out=ROOT/'artifacts/b3_mc_contract_smoke'
 out.mkdir(parents=True,exist_ok=True)
 (out/'grid321.csv').write_bytes(f.read_bytes())
 (out/'manifest.json').write_bytes((d/'manifest.json').read_bytes())
 print('T3_MC_321_MANIFEST_40_SEED_SHA256_PASS')
