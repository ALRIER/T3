#!/usr/bin/env python3
"""Freeze a fresh parent/child real-world profile map against the T3 family grid.

Input is a completed, outcome-blind profile catalog. Multiple variables/series
may belong to one parent; they remain child evaluations and are never counted
as independent parents. Model scores are not read by this selector.
"""
import argparse, csv, hashlib, json, math, random, re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

FAMILIES=('normal','lognormal','weibull','invgauss','exgaussian','exwald')
DIRECT={
 'normal':{'normal_like','heavy_tail_symmetric'},
 'lognormal':{'lognormal_like'},
 'weibull':{'weibull_like'},
 'invgauss':{'lognormal_like','weibull_like'},
 'exgaussian':{'normal_like','heavy_tail_symmetric','lognormal_like'},
 'exwald':{'weibull_like','lognormal_like'},
}
NEAR={
 'normal':{'empirical_unknown'}, 'lognormal':{'weibull_like'},
 'weibull':{'lognormal_like'}, 'invgauss':{'empirical_unknown'},
 'exgaussian':{'weibull_like','empirical_unknown'},
 'exwald':{'empirical_unknown'},
}
REQUIRED={'dataset_id','parent_dataset_id','source_path','source_sha256',
          'processed_path','processed_sha256','profile_sha256','source_url',
          'domain','empirical_profile','n','skewness','excess_kurtosis',
          'support_sign','outlier_fraction_3mad','license_name','license_url',
          'license_review_status','source_sector','catalog_commit',
          'upstream_license_status','upstream_source_url','source_archive_doi',
          'license_evidence','license_evidence_sha256','license_evidence_path',
          'source_group','license_basis','child_selection_rule'}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def re_sha(x):
 import re
 return bool(re.fullmatch(r'[0-9a-f]{64}',x.strip().lower()))

p=argparse.ArgumentParser()
p.add_argument('profiles',type=Path)
p.add_argument('--grid',type=Path,default=Path('config/T2_V3_B3_prospective_321_grid.csv'))
p.add_argument('--out',type=Path,default=Path('artifacts/T3_B3_realworld_freeze'))
p.add_argument('--target-candidate-parents',type=int,default=642)
p.add_argument('--minimum-finance-parents',type=int,default=199)
p.add_argument('--sample-seed',type=int,default=642026)
a=p.parse_args()
rows=list(csv.DictReader(a.profiles.open(newline='',encoding='utf-8-sig')))
if not rows: raise SystemExit('BLOCKED: fresh candidate profile catalog is empty')
missing=REQUIRED-set(rows[0])
if missing: raise SystemExit('BLOCKED: profile schema missing '+', '.join(sorted(missing)))
parents=defaultdict(list); seen_children=set()
for i,r in enumerate(rows,2):
 if not r['dataset_id'].strip() or not r['parent_dataset_id'].strip():
  raise SystemExit(f'BLOCKED: missing parent/child id at row {i}')
 key=(r['parent_dataset_id'],r['dataset_id'])
 if key in seen_children: raise SystemExit(f'BLOCKED: duplicate parent-child key at row {i}')
 seen_children.add(key)
 for pathfield,hashfield in (('source_path','source_sha256'),('processed_path','processed_sha256')):
  if not re_sha(r[hashfield]): raise SystemExit(f'BLOCKED: invalid {hashfield} at row {i}')
  path=Path(r[pathfield])
  if not path.is_file(): raise SystemExit(f'BLOCKED: missing {pathfield}: {path}')
  if sha(path)!=r[hashfield].lower(): raise SystemExit(f'BLOCKED: {pathfield} hash mismatch: {path}')
 if not re_sha(r['profile_sha256']): raise SystemExit(f'BLOCKED: invalid profile hash at row {i}')
 if not re_sha(r['license_evidence_sha256']): raise SystemExit(f'BLOCKED: invalid license evidence hash at row {i}')
 if not Path(r['license_evidence_path']).is_file() or sha(r['license_evidence_path'])!=r['license_evidence_sha256'].lower():
  raise SystemExit(f'BLOCKED: missing or changed license evidence file at row {i}')
 if r['license_review_status'].strip().lower()!='verified' or not r['license_name'].strip():
  raise SystemExit(f'BLOCKED: source license not individually verified at row {i}')
 if not re.fullmatch(r'[0-9a-f]{40,64}',r['catalog_commit'].strip().lower()):
  raise SystemExit(f'BLOCKED: invalid catalog commit at row {i}')
 for field in ('source_url','license_url'):
  u=urlparse(r[field].strip())
  if u.scheme!='https' or not u.netloc: raise SystemExit(f'BLOCKED: invalid {field} at row {i}')
 for f in ('n','skewness','excess_kurtosis','outlier_fraction_3mad'):
  try: val=float(r[f])
  except ValueError: raise SystemExit(f'BLOCKED: invalid {f} at row {i}')
  if not math.isfinite(val): raise SystemExit(f'BLOCKED: nonfinite {f} at row {i}')
 if float(r['n'])<150 or not 0<=float(r['outlier_fraction_3mad'])<=1:
  raise SystemExit(f'BLOCKED: insufficient or invalid profile at row {i}')
 parents[r['parent_dataset_id']].append(r)
if len(parents)<a.target_candidate_parents:
 raise SystemExit(f'BLOCKED: {len(parents)} independent candidate parents; need {a.target_candidate_parents}')
profiled_parent_ids=set(parents)
finance=sorted(pid for pid,children in parents.items()
                if pid in profiled_parent_ids and any(c['source_sector'].strip().lower()=='finance' for c in children))
other=sorted(pid for pid in profiled_parent_ids if pid not in set(finance))
if len(finance)<a.minimum_finance_parents or len(other)<a.target_candidate_parents-a.minimum_finance_parents:
 raise SystemExit(f'BLOCKED: need {a.minimum_finance_parents} finance and '
  f'{a.target_candidate_parents-a.minimum_finance_parents} non-finance parents; '
  f'candidate parents; found {len(finance)} finance and {len(other)} non-finance')
sampler=random.Random(a.sample_seed)
sampled=sorted(sampler.sample(finance,a.minimum_finance_parents)+
               sampler.sample(other,a.target_candidate_parents-a.minimum_finance_parents))
grid=list(csv.DictReader(a.grid.open(newline='',encoding='utf-8-sig')))
if len(grid)!=321 or len({int(x['scenario_id']) for x in grid})!=321:
 raise SystemExit('BLOCKED: expected the frozen 321-row T3 Discovery grid')
out=[]
for pid in sampled:
 children=parents[pid]
 for child in children:
  profile=child['empirical_profile']
  for source_family in FAMILIES:
   if profile in DIRECT[source_family]: scope='within_regime'
   elif profile in NEAR[source_family]: scope='within_family_neighborhood'
   else: scope='cross_family_transfer'
   # Outcome-blind nearest structural cell. Mechanism is recorded as a proxy
   # from profile shape; it is not treated as observed ground-truth corruption.
   contamination_proxy=min(.30,max(0.,float(child['outlier_fraction_3mad'])))
   tail=max(0.,float(child['excess_kurtosis']))
   mad_proxy=min((1.5,3,4.5,6,9,12,15,20,30),
                 key=lambda m:abs(math.log1p(m)-math.log1p(1.5+tail)))
   eligible_grid=[g for g in grid if g['mechanism']!='mixture_bimodal_near' and g['mechanism']!='mixture_bimodal_far']
   cell=min(eligible_grid,key=lambda g:abs(float(g['contamination'])-contamination_proxy)/.30+
            abs(math.log1p(float(g['mad_scale']))-math.log1p(mad_proxy))/math.log1p(30))
   out.append({
    'protocol':'T3_B3_realworld_parent_child_v1','parent_dataset_id':pid,
    'dataset_id':child['dataset_id'],'training_family':source_family,
    'empirical_profile':profile,'transfer_scope':scope,
    'matched_scenario_id':cell['scenario_id'],'matched_mechanism_proxy':cell['mechanism'],
    'contamination_proxy':contamination_proxy,'mad_scale_proxy':mad_proxy,
    'skewness':child['skewness'],'excess_kurtosis':child['excess_kurtosis'],
    'support_sign':child['support_sign'],'outlier_fraction_3mad':child['outlier_fraction_3mad'],
    'source_url':child['source_url'],'domain':child['domain'],'source_sector':child['source_sector'],
    'source_path':child['source_path'],'source_sha256':child['source_sha256'],
    'processed_path':child['processed_path'],'processed_sha256':child['processed_sha256'],
    'profile_sha256':child['profile_sha256'],'catalog_commit':child['catalog_commit'],
    'license_name':child['license_name'],
    'license_url':child['license_url'],'license_review_status':child['license_review_status'],
    'upstream_license_status':child['upstream_license_status'],
    'upstream_source_url':child['upstream_source_url'],
    'source_archive_doi':child['source_archive_doi'],
    'license_evidence':child['license_evidence'],
    'license_evidence_sha256':child['license_evidence_sha256'],
    'license_evidence_path':child['license_evidence_path'],
    'source_group':child['source_group'],
    'license_basis':child['license_basis'],
    'child_selection_rule':child['child_selection_rule'],
    'variable':child['variable'],
    'feature_index':child.get('feature_index',''),
    'selection':'outcome_blind_profile_match_to_T3_Discovery_family_grid'})
if not out: raise SystemExit('BLOCKED: no parents match any Discovery family profile')
a.out.mkdir(parents=True,exist_ok=True)
path=a.out/'frozen_parent_child_family_manifest.csv'
with path.open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
payload={'protocol':'T3_B3_realworld_parent_child_v1','candidate_parent_count':len(parents),
 'profiled_candidate_parent_count':len(profiled_parent_ids),
 'frozen_sample_parent_count':len(sampled),'frozen_finance_parent_count':a.minimum_finance_parents,
 'frozen_nonfinance_parent_count':len(sampled)-a.minimum_finance_parents,
 'sample_seed':a.sample_seed,
 'selected_parent_count':len({r['parent_dataset_id'] for r in out}),
 'child_profile_count':len({(r['parent_dataset_id'],r['dataset_id']) for r in out}),
 'frozen_family_evaluations':len(out),'source_profile_sha256':sha(a.profiles),
 'discovery_grid_sha256':sha(a.grid),'frozen_manifest_sha256':sha(path),
 'selection_uses_model_outcomes':False,'inference_unit':'parent_dataset_id',
 'license_gate':'separate_individual_license_verification_required'}
(a.out/'freeze_manifest.json').write_text(json.dumps(payload,indent=2)+'\n')
print('T3_B3_REALWORLD_PARENT_CHILD_FREEZE_PASS',json.dumps(payload,sort_keys=True))
