#!/usr/bin/env python3
"""T2 V3 B3 immutable parent-selection gate.
Requires newly collected B3 outcome-blind profiles; V2 catalog is excluded.
No model performance enters selection; no silent fallback to a smaller pool.
"""
import csv,hashlib,json,pathlib,sys
base=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'artifacts/T2_V3_B3_fresh_profiles')
out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else 'artifacts/T2_V3_B3_realworld_freeze')
out.mkdir(parents=True,exist_ok=True)
if 'realworld_regime_matched_v2' in str(base):
 raise RuntimeError('Historical V2 audit directory forbidden for B3 selection')
records=[]
for p in sorted(base.glob('profile_batch_*/profiles.csv')):
 for r in csv.DictReader(p.open(newline='')):
  if r['load_ok'].lower() not in ('true','t','1'):continue
  raw=p.parent/'raw'/(r['dataset_id']+'.rds')
  if not raw.exists():raise RuntimeError(f'Missing parent scientific data: {raw}')
  if not r.get('raw_sha256'):raise RuntimeError(f'Missing source fingerprint: {raw}')
  h=hashlib.md5()
  with raw.open('rb') as stream:
   for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
  if h.hexdigest()!=r['raw_sha256']:raise RuntimeError(f'Parent fingerprint mismatch: {raw}')
  r['batch']=p.parent.name
  records.append(r)
parents={}
for r in records:
 pid=r['parent_dataset_id']
 if pid in parents:
  raise RuntimeError(f'Duplicate parent identifier, needs explicit dependency reconciliation: {pid}')
 parents[pid]=r
if not parents:
 raise RuntimeError('No newly audited B3 parent datasets')
# Freeze only parents with at least one family-compatible regime. Evaluation
# will still score every accepted parent in all six families, including cross
# family transfer; neither model scores nor W participate in parent selection.
direct_profiles={'normal_like','lognormal_like','weibull_like'}
eligible={pid:r for pid,r in parents.items()
          if r['empirical_profile'] in direct_profiles}
if not eligible:raise RuntimeError('No compatible B3 parents; freeze blocked')
parents=eligible
families=['normal','lognormal','weibull','invgauss','exgaussian','exwald']
rows=[]
# Match using frozen Discovery B3 structural bands. Empirical shape fields
# are measured before scoring; matching is explicitly descriptive.
mad_bands=[1.5,3,4.5,6,9,12,15,20,30]
contamination_rates=[0,.01,.05,.10,.20,.30]
for pid in sorted(parents):
 r=parents[pid]
 for family in families:
  profile=r['empirical_profile']
  direct={'normal':['normal_like'],'lognormal':['lognormal_like'],'weibull':['weibull_like'],
   'invgauss':['lognormal_like','weibull_like'],'exgaussian':['normal_like','lognormal_like'],
   'exwald':['lognormal_like','weibull_like']}[family]
  near={'normal':['empirical_unknown'],'lognormal':['weibull_like'],
   'weibull':['lognormal_like'],'invgauss':['empirical_unknown'],
   'exgaussian':['weibull_like','empirical_unknown'],'exwald':['empirical_unknown']}[family]
  layer='direct_intraregime' if profile in direct else ('near_intrfamily' if profile in near else 'crossfamily_transfer')
  # Tail/outlier features are outcome-blind measured proxies, never
  # asserted to be the synthetic generator's true contamination or MAD.
  skew=float(r.get('skewness') or 'nan')
  kurt=float(r.get('excess_kurtosis') or 'nan')
  import math
  if not(math.isfinite(skew) and math.isfinite(kurt)):raise RuntimeError(f'Missing finite B3 shape diagnostics for {pid}')
  tail_proxy=max(0.,kurt)
  mad_proxy=min(mad_bands,key=lambda m:abs(math.log1p(m)-math.log1p(1.5+tail_proxy)))
  contamination_proxy=min(contamination_rates,key=lambda c:abs(c-min(.30,tail_proxy/(20+tail_proxy))))
  rows.append(dict(version='T2_V3_B3',parent_dataset_id=pid,dataset_id=r['dataset_id'],
    family=family,batch=r['batch'],empirical_profile=r['empirical_profile'],
    source_url=r['source_url'],source_hash=r['raw_sha256'],
    proximity_layer=layer,skewness=skew,excess_kurtosis=kurt,
    mad_band_proxy=mad_proxy,contamination_band_proxy=contamination_proxy,
    synthetic_regime_match='descriptive_proxy_only',selection_rule='B3_new_outcome_blind_profile_matching'))
p=out/'frozen_parent_family_manifest_T2_V3_B3.csv'
with p.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
digest=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'freeze_T2_V3_B3.json').write_text(json.dumps(dict(version='T2_V3_B3',
 parent_count=len(parents),evaluation_families=6,rows=len(rows),manifest_sha256=digest,
 provenance='newly collected B3 profiles; source hashes per parent',selection_uses_performance=False,selection_criterion='at least one direct family regime match; full six-family evaluation retained'),indent=2))
print(f'T2_V3_B3_NEW_PARENTS_FROZEN_PASS {len(rows)}')
