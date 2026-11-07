#!/usr/bin/env python3
"""Real World supplementary independent-parent publication validation.

Score data use exactly the original frozen Discovery 0:9 and external evaluation
seeds 30:39. No child, split, bootstrap replicate or training seed is an
independent parent. Supplementary BH panels are never merged with the original
source/destination benchmark inference.
"""
import argparse,collections,csv,gzip,json,math,pathlib,re,statistics
import numpy as np
from scipy import stats

FAMILIES=('normal','lognormal','weibull','invgauss','exgaussian','exwald')
ENGINE=('ga','nsga2','de','dirichlet')
CONTROLS=('mean','convex_mse','local_deterministic')
TARGETS=('holdout_half_mean','full_sample_mean')
def check(t,msg):
 if not t:raise ValueError(msg)
def read(p):
 with gzip.open(p,'rt',newline='') as f:yield from csv.DictReader(f)
def write(p,rows):
 check(rows,'Cannot publish empty scientific output: '+str(p))
 p.parent.mkdir(parents=True,exist_ok=True)
 with gzip.open(p,'wt',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def identify(family,name,train):
 if name=='mean':return 'mean'
 prefix=family+'_';end='_train%02d'%train
 check(name.startswith(prefix) and name.endswith(end),'Unexpected original frozen model name: '+name)
 model=name[len(prefix):-len(end)]
 check(model in ENGINE+CONTROLS,'Unexpected scoring candidate '+name)
 return model
def family_stage(args):
 p=pathlib.Path(args.input);data=sorted(p.rglob('replicate_sensitivity.csv.gz'))
 check(len(data)==42,'Exactly 14 independent parent-intact source blocks x three n required: '+str(len(data)))
 check(args.family in FAMILIES,'Invalid source family')
 allscores={};metas=[];characteristics=collections.defaultdict(list);seen=set()
 for f in data:
  mpath=f.parent/'validation_manifest.json'
  m=json.loads(mpath.read_text())
  check(m['source_family']==args.family and m['sample_n'] in (200,1000,3000) and
        m['evaluation_seeds']==list(range(30,40)) and m['models_per_fit']==7 and m['replications']==500,
        'Incomplete 10-seed/7-model validated scoring contract')
  key=(m['block_id'],m['sample_n'])
  check(key not in seen,'Duplicate frozen parent block / n')
  seen.add(key);metas.append(m)
  for row in csv.DictReader((f.parent/'frozen_child_characteristics.csv').open()):
   pkey=(row['parent_dataset_id'],m['sample_n'])
   characteristics[pkey].append(row)
  for r in read(f):
   check(r['source_family']==args.family and int(r['sample_n'])==m['sample_n'] and
         r['block_id']==m['block_id'],'Scoring shard mixup')
   tr=int(r['training_seed']);ev=int(r['realworld_seed'])
   check(tr in range(10) and ev in range(30,40),'Nonfrozen train/eval seed')
   ref=r['reference_policy'];check(ref in TARGETS,'Unknown target reference')
   model=identify(args.family,r['model'],tr)
   k=(r['parent_dataset_id'],m['sample_n'],tr,ev,ref,model)
   check(k not in allscores,'Repeated parent/model/seed scoring unit')
   mse=float(r['mse']);q95=float(r['q95'])
   check(all(map(math.isfinite,(mse,q95))) and mse>=0 and q95>=0,'Invalid empirical loss')
   allscores[k]=(mse,q95)
  print('PUBLICATION_SCORING_BLOCK_VERIFIED',args.family,m['block_id'],m['sample_n'],flush=True)
 check(len(seen)==42 and len({k[0] for k in seen})==14,'Missing source family parent-block/sample-size coverage')
 parents=collections.defaultdict(set)
 for k in allscores:parents[(k[1],k[2],k[4])].add(k[0])
 # Candidate and benchmark models must share identical evaluation seed blocks per parent.
 detail=collections.defaultdict(list)
 for (pid,n,tr,ev,target,model),z in allscores.items():
  if model not in ENGINE:continue
  for comparator in CONTROLS:
   ck=(pid,n,tr,ev,target,comparator)
   check(ck in allscores,'Absent paired reference, do not impute: '+str(ck))
   b=allscores[ck]
   detail[(pid,n,tr,target,model,comparator)].append((ev,z,b))
 # Keep repeated evaluation seeds within parent, never as inferential units.
 parent_results=[];grouped=collections.defaultdict(list)
 for (pid,n,tr,target,model,comp),v in detail.items():
  evs={q[0] for q in v}
  check(evs==set(range(30,40)),'Incomplete ten repeated evaluation seeds in independent parent')
  mse=float(np.mean([z[1][0]-z[2][0] for z in v]))
  q95=float(np.mean([z[1][1]-z[2][1] for z in v]))
  baseline_m=float(np.mean([z[2][0] for z in v]))
  baseline_q=float(np.mean([z[2][1] for z in v]))
  gm=100*mse/max(abs(baseline_m),np.finfo(float).eps)
  gq=100*q95/max(abs(baseline_q),np.finfo(float).eps)
  row=dict(source_family=args.family,parent_dataset_id=pid,sample_n=n,
           training_seed=tr,reference_policy=target,engine=model,
           comparator=comp,mse_difference=mse,q95_difference=q95,
           mse_relative_difference_pct=gm,q95_relative_difference_pct=gq)
  parent_results.append(row);grouped[(n,tr,target,model,comp)].append(row)
 out=pathlib.Path(args.output)
 out.mkdir(parents=True,exist_ok=False)
 write(out/'paired_parent_effects.csv.gz',parent_results)
 infer=[];hetero=[]
 for (n,tr,target,model,comp),rr in sorted(grouped.items()):
  pids={x['parent_dataset_id'] for x in rr}
  check(len(pids)==len(rr),'Duplicate independent parent')
  if len(rr)<5:continue
  rec=dict(source_family=args.family,sample_n=n,training_seed=tr,
           candidate_id=f'{args.family}|{model}|seed{tr:02d}|n{n}',
           reference_policy=target,comparator=comp,independent_parents=len(rr))
  for met in ('mse','q95'):
   arr=np.array([x[met+'_difference'] for x in rr]);lo,hi=stats.t.interval(.95,len(arr)-1,loc=float(arr.mean()),scale=float(stats.sem(arr)))
   if not math.isfinite(lo):
    lo=hi=float(arr.mean())
   one_sided=float(stats.ttest_1samp(arr,0,alternative='less').pvalue) if np.std(arr,ddof=1)>0 else (0 if arr.mean()<0 else 1)
   rec.update({met+'_mean_difference':float(arr.mean()),
               met+'_ci95_low':float(lo),met+'_ci95_high':float(hi),
               met+'_one_sided_p':one_sided,
               met+'_parent_positive_share':float(np.mean(arr<0)),
               met+'_mean_relative_pct':float(np.mean([x[met+'_relative_difference_pct'] for x in rr]))})
  infer.append(rec)
  # Exploratory heterogeneity: parent covariate strata; never present as independent
  # randomized experiments or confirmatory moderator p-values.
  for cov in ('skewness','outlier_fraction','coefficient_variation'):
   eligible=[]
   for row in rr:
    p=(row['parent_dataset_id'],n)
    vals=[float(q[cov]) for q in characteristics[p] if q.get(cov,'') not in ('','NA')]
    if vals and all(math.isfinite(x) for x in vals):
     eligible.append((float(np.mean(vals)),row))
   if len(eligible)<10:continue
   q25,q75=np.quantile([v[0] for v in eligible],[.25,.75])
   for label,rs in [('low', [z for x,z in eligible if x<=q25]),
                    ('high',[z for x,z in eligible if x>=q75])]:
    if len(rs)<5:continue
    hetero.append(dict(**{k:rec[k] for k in
      ('source_family','sample_n','training_seed','candidate_id','reference_policy','comparator')},
      characteristic=cov,quartile=label,independent_parents=len(rs),
      mse_mean_difference=float(np.mean([r['mse_difference'] for r in rs])),
      q95_mean_difference=float(np.mean([r['q95_difference'] for r in rs])),
      mse_positive_share=float(np.mean([r['mse_difference']<0 for r in rs])),
      q95_positive_share=float(np.mean([r['q95_difference']<0 for r in rs])),
      inferential_status='descriptive_exploratory_not_FDR_confirmed'))
 write(out/'unadjusted_parent_level_inference.csv.gz',infer)
 write(out/'parent_heterogeneity_exploratory.csv.gz',hetero)
 (out/'family_provenance.json').write_text(json.dumps(dict(source_family=args.family,original_source_blocks=14,
  frozen_sample_sizes=[200,1000,3000],source_job_artifacts=len(data),
  original_training_seeds=list(range(10)),external_evaluation_seeds=list(range(30,40)),
  source_qualified_parent_ids=len({r['parent_dataset_id'] for r in parent_results}),
  paired_parent_rows=len(parent_results),unadjusted_contrasts=len(infer),
  separate_reference_targets=list(TARGETS),confirmatory_prior_BH_unchanged=True),indent=2)+'\n')
 print('REALWORLD_PUBLICATION_FAMILY_FULL_PASS',args.family,len(data),len(parent_results),len(infer),flush=True)
def bh(p):
 arr=np.asarray(p,dtype=float);order=np.argsort(arr,kind='stable');n=len(arr)
 q=np.empty(n);q[order]=np.minimum.accumulate((arr[order]*n/np.arange(1,n+1))[::-1])[::-1]
 return np.minimum(q,1.)
def global_stage(args):
 root=pathlib.Path(args.input);meta=sorted(root.rglob('family_provenance.json'))
 check(len(meta)==6,'Six independently validated source families required')
 fams=set();rows=[];hetero=[];family_rows=[]
 for p in meta:
  m=json.loads(p.read_text());family=m['source_family']
  check(family in FAMILIES and family not in fams,'Duplicate or unexpected family')
  fams.add(family)
  family_rows+=list(read(p.parent/'paired_parent_effects.csv.gz'))
  rows+=list(read(p.parent/'unadjusted_parent_level_inference.csv.gz'))
  hetero+=list(read(p.parent/'parent_heterogeneity_exploratory.csv.gz'))
 check(fams==set(FAMILIES),'Incomplete six-family global inference')
 # One BH family per target and comparator, across all W and both metrics.
 panels=collections.defaultdict(list)
 for i,r in enumerate(rows):
  for met in ('mse','q95'):
   panels[(r['reference_policy'],r['comparator'])].append((i,met,float(r[met+'_one_sided_p'])))
 for panel,z in panels.items():
  q=bh([v[2] for v in z])
  for (i,metric,_),val in zip(z,q):
   rows[i][metric+'_supplementary_bh_q']=float(val)
 for r in rows:
  r['tier1_joint_supplementary']=bool(
   float(r['mse_supplementary_bh_q'])<=.05 and float(r['q95_supplementary_bh_q'])<=.05 and
   float(r['mse_ci95_high'])<0 and float(r['q95_ci95_high'])<0)
 # Explicit paired-reference stability on the same candidate/family/n/comparator.
 stable=collections.defaultdict(dict)
 for r in rows:
  k=tuple(r[c] for c in ('source_family','candidate_id','sample_n','comparator'))
  stable[k][r['reference_policy']]=r
 stability=[]
 for k,ps in stable.items():
  check(set(ps)==set(TARGETS),'Missing same-candidate target comparison')
  a,b=ps[TARGETS[0]],ps[TARGETS[1]]
  stability.append(dict(source_family=k[0],candidate_id=k[1],sample_n=k[2],comparator=k[3],
   target_sign_concordant_mse=bool(float(a['mse_mean_difference'])*float(b['mse_mean_difference'])>0),
   target_sign_concordant_q95=bool(float(a['q95_mean_difference'])*float(b['q95_mean_difference'])>0),
   both_target_joint_FDR=bool(a['tier1_joint_supplementary'] and b['tier1_joint_supplementary']),
   heldout_joint_FDR=bool(a['tier1_joint_supplementary']),
   full_sample_joint_FDR=bool(b['tier1_joint_supplementary']),
   independent_parents=int(a['independent_parents'])))
 out=pathlib.Path(args.output);out.mkdir(parents=True,exist_ok=False)
 write(out/'supplementary_controls_and_target_BH.csv.gz',rows)
 write(out/'independent_parent_effects_all_families.csv.gz',family_rows)
 write(out/'heterogeneity_exploratory_all_families.csv.gz',hetero)
 write(out/'paired_target_policy_stability.csv.gz',stability)
 panel_counts=[dict(reference_policy=x,comparator=y,n_metric_hypotheses=2*len(z),
   scientific_status='supplementary_separate_from_original_source_and_destination_BH')
   for (x,y),z in sorted(panels.items())]
 (out/'publication_validation_provenance.json').write_text(json.dumps(dict(
  protocol='T3_B3_REALWORLD_PUBLICATION_CONTROLS_AND_EMPIRICAL_TARGET_SENSITIVITY',
  source_families=list(FAMILIES),sample_sizes=[200,1000,3000],
  original_individual_frozen_W=720,additional_frozen_non_evolutionary_controls=list(CONTROLS[1:]),
  extra_fitted_using_realworld=False,paired_split_reference_target='heldout_half_mean',
  secondary_target='full_sample_mean',two_disjoint_folds=True,replications_per_fold=500,
  score_evaluation_seeds=list(range(30,40)),
  independent_unit='parent_dataset_id',separate_BH_panels=panel_counts,
  score_jobs_expected=252,original_primary_BH_not_recomputed=True,
  moderator_results='exploratory_descriptive_not_confirmatory',
  real_population_mean_known=False,results_are_empirical_reference_sensitivity_not_absolute_MSE_truth=True),indent=2)+'\n')
 (out/'interpretation_limits.md').write_text(
  '# Real World supplementary robustness and optimization controls\n\n'
  'Two extra **Discovery-frozen** non-evolutionary weight vectors are scored against '
  'the same empirical component draws as four frozen evolutionary models and sample mean. '
  'No model uses the Real World outcomes to fit weights. Target sensitivity uses '
  'two swapped disjoint half-sample heldout reference means, and the full-sample empirical '
  'mean proxy. The unknown true population mean remains unobserved.\n\n'
  'All ten repeated external evaluation seeds, two folds, children and eligible depths '
  'are pooled inside each independent parent. No p-value treats repeated bootstrap draws '
  'or frozen training seeds as independent parents. Additional BH corrections operate '
  'on separate exploratory target-by-comparator panels. They do not alter the original '
  'predeclared 720-W source-policy or destination-policy conclusions.\n\n'
  'Heterogeneity by empirical skewness, robust outlier fraction and CV quartiles is '
  'exploratory descriptive; no predictive selection rule was trained or independently confirmed.\n')
 check(len(stability)>0 and len(rows)>0 and len(family_rows)>0,'No full evidence')
 print('REALWORLD_PUBLICATION_ALL_FOUR_MODULES_GLOBAL_PASS',len(rows),len(stability),len(family_rows),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();m=p.add_subparsers(dest='mode',required=True)
 f=m.add_parser('family');f.add_argument('--family',required=True)
 f.add_argument('--input',required=True);f.add_argument('--output',required=True)
 g=m.add_parser('global');g.add_argument('--input',required=True);g.add_argument('--output',required=True)
 a=p.parse_args()
 {'family':family_stage,'global':global_stage}[a.mode](a)
