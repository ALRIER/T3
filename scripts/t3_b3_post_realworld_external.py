#!/usr/bin/env python3
"""Outcome-blind empirical-family assignment and source-domain robustness.

All contrasts are descriptive sensitivity analyses on independent parent
datasets. Family matches are empirical approximate labels, not population truth.
"""
import argparse,collections,csv,gzip,hashlib,json,math,pathlib
import numpy as np
from scipy import stats

def check(condition,message):
 if not condition:raise ValueError(message)
def load(path):
 p=pathlib.Path(path);op=gzip.open if p.suffix=='.gz' else open
 with op(p,'rt',newline='') as f:return list(csv.DictReader(f))
def write(path,rows):
 check(rows,'Refusing empty robustness output')
 p=pathlib.Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 with open(p,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def compute(args):
 effects=load(args.effects);features=load(args.features)
 required_effect={'parent_dataset_id','sample_n','training_seed','engine','comparator',
                  'reference_policy','mse_difference','q95_difference'}
 required_features={'parent_dataset_id','sample_n','source_family','data_source',
                    'profile_fit_confidence','family_assignment_status',
                    'empirical_family_assignment','family_assignment_margin'}
 check(effects and required_effect<=effects[0].keys(),'Parent effect input schema mismatch')
 check(features and required_features<=features[0].keys(),'Outcome-blind feature schema mismatch')
 profiles={}
 for f in features:
  key=(f['parent_dataset_id'],f['sample_n'])
  check(key not in profiles,'Duplicate independent-parent/sample-size feature key')
  profiles[key]=f
 # Do not multiply independent sample size by ten training seeds.
 within_parent=collections.defaultdict(list)
 for e in effects:
  if e['reference_policy']!='holdout_half_mean' or e['comparator']!='mean':continue
  key=(e['parent_dataset_id'],e['sample_n'],e['engine'])
  within_parent[key].append(e)
 reduced=[]
 for (pid,n,engine),rows in sorted(within_parent.items()):
  seeds={int(z['training_seed']) for z in rows}
  check(seeds==set(range(10)) and len(rows)==10,'Incomplete ten frozen training units for parent')
  f=profiles.get((pid,n));check(f is not None,'Missing parent source profile')
  conf=float(f['profile_fit_confidence'])
  check(0<=conf<=1,'Invalid original outcome-blind assignment confidence')
  src=f['source_family'];dst=f['empirical_family_assignment']
  assignment=('undetermined' if not dst or ';' in dst or dst.lower() in ('none','na','nan')
              else ('same' if dst==src else 'different'))
  strata=('high_confidence' if conf>=args.minimum_confidence else 'low_confidence')
  mse=float(np.mean([float(z['mse_difference']) for z in rows]))
  q95=float(np.mean([float(z['q95_difference']) for z in rows]))
  check(math.isfinite(mse) and math.isfinite(q95),'Nonfinite parent contrast')
  reduced.append(dict(parent_dataset_id=pid,sample_n=n,engine=engine,source_family=src,
   data_source=f['data_source'],assignment=str(assignment),
   confidence_stratum=strata,assignment_status=f['family_assignment_status'],
   assignment_margin=f['family_assignment_margin'],
   mse_difference=mse,q95_difference=q95))
 # Every group first pools sample sizes/engine identities inside parent, then
 # reports parent as the independent unit.
 by_group=collections.defaultdict(lambda:collections.defaultdict(list))
 for r in reduced:
  for type_,name in (('source_family',r['source_family']),
                     ('data_source',r['data_source']),
                     ('assignment',r['assignment']),
                     ('confidence',r['confidence_stratum']),
                     ('assignment_status',r['assignment_status'])):
   by_group[(type_,name)][r['parent_dataset_id']].append(r)
 rows=[]
 for (type_,name),parents in sorted(by_group.items()):
  if len(parents)<5:continue
  avg=np.array([[np.mean([float(z[m+'_difference']) for z in rr]) for m in ('mse','q95')]
                for rr in parents.values()])
  row=dict(stratification=type_,stratum=name,independent_parents=len(parents),
           inferential_status='exploratory_descriptive_parent_independent')
  for j,m in enumerate(('mse','q95')):
   x=avg[:,j];row[m+'_mean_difference']=float(x.mean())
   row[m+'_parent_win_share']=float(np.mean(x<0))
   if len(x)>=10 and x.std(ddof=1)>0:
    lo,hi=stats.t.interval(.95,len(x)-1,loc=float(x.mean()),scale=float(stats.sem(x)))
    row[m+'_parent_t95_low']=float(lo);row[m+'_parent_t95_high']=float(hi)
   else:
    row[m+'_parent_t95_low']=row[m+'_parent_t95_high']=''
  rows.append(row)
 out=pathlib.Path(args.output)
 write(out/'source_domain_and_family_assignment_sensitivity.csv',rows)
 write(out/'source_domain_parent_paired_effects.csv',reduced)
 (out/'source_domain_and_assignment_scope.json').write_text(json.dumps(dict(
  parent_unit='parent_dataset_id',source_names='original_observed_public_dataset_domains',
  empirical_family_assignment_is_outcome_blind_approximation=True,
  sensitivity_threshold=args.minimum_confidence,
  provenance='frozen_processed_profiles_not_rescored_or_fit_to_outcomes',
  primary_source_BH='untouched',destination_policy_BH='untouched',
  supplementary_hypothesis_family='descriptive_only_no_claim_of_new_FDR_discoveries'),indent=2)+'\n')
 print('POST_RW_EXTERNAL_PARENT_DOMAIN_ASSIGNMENT_SENSITIVITY_PASS',len(rows))
def main():
 p=argparse.ArgumentParser();p.add_argument('--effects',required=True)
 p.add_argument('--features',required=True);p.add_argument('--output',required=True)
 p.add_argument('--minimum-confidence',type=float,default=.75)
 a=p.parse_args();check(0<a.minimum_confidence<1,'Invalid predeclared confidence cutoff')
 compute(a)
if __name__=='__main__':main()
