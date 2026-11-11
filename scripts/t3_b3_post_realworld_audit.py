#!/usr/bin/env python3
"""T3 B3 post-Real-World publication checks.

Inputs MUST be independent-parent aggregates with frozen candidate/model identities;
no evaluation on a child-level row or a validation-trained policy.
This script does not claim a complete optimizer null replay.
"""
import argparse,csv,gzip,hashlib,json,math,pathlib,collections,random
import numpy as np
from scipy import stats

FAMILIES=('normal','lognormal','weibull','invgauss','exgaussian','exwald')
METRICS=('mse','q95')
def require(c,m):
 if not c:raise ValueError(m)
def read_rows(p):
 p=pathlib.Path(p)
 opener=gzip.open if p.suffix=='.gz' else open
 with opener(p,'rt',newline='') as f:return list(csv.DictReader(f))
def save_rows(p,rows):
 require(len(rows)>0,'Refusing empty scientific output '+str(p))
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with open(p,'w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def seed(*parts):
 return int.from_bytes(hashlib.sha256('|'.join(map(str,parts)).encode()).digest()[:8],'big')
def bh(values):
 p=np.asarray(values,float)
 require(np.isfinite(p).all() and np.logical_and(p>=0,p<=1).all(),'Invalid p-values')
 n=len(p);o=np.argsort(p,kind='stable');q=np.empty(n)
 q[o]=np.minimum(1,np.minimum.accumulate((p[o]*n/np.arange(1,n+1))[::-1])[::-1])
 return q.tolist()
def check_recovery_manifest(p):
 x=json.loads(pathlib.Path(p).read_text())
 require(x.get('score_jobs_expected')==1260,'Expected complete 1260-scoring-shard lineage')
 require(x.get('original_individual_frozen_W')==720,'Original 720 frozen W incomplete')
 require(x.get('replications_per_fold')==500,'Unexpected scoring budget')
 require(x.get('score_evaluation_seeds')==list(range(30,40)),'Missing independent scoring seeds')
 require(x.get('independent_unit')=='parent_dataset_id','Parent unit mismatch')
 require(x.get('original_primary_BH_not_recomputed') is True,'Primary BH unexpectedly modified')
 require(x.get('separate_BH_panels') and len(x['separate_BH_panels'])==6,'Missing auxiliary BH panels')
 return x
def bootstrap_ci(x,reps,s):
 a=np.asarray(x,float)
 require(a.size>=5 and np.isfinite(a).all(),'Parent bootstrap requires >=5 finite independent parents')
 rng=np.random.default_rng(s);n=len(a)
 means=np.empty(reps)
 for i in range(0,reps,128):
  j=min(i+128,reps)
  ix=rng.integers(0,n,size=(j-i,n))
  means[i:j]=a[ix].mean(axis=1)
 return [float(z) for z in np.quantile(means,[.025,.975])]
def parent_inference(args):
 check_recovery_manifest(args.manifest)
 data=read_rows(args.parent_effects)
 required={'source_family','parent_dataset_id','sample_n','training_seed','reference_policy',
           'engine','comparator','mse_difference','q95_difference'}
 require(data and required<=set(data[0]),'Missing parent-independent score fields')
 keys=set();panels=collections.defaultdict(list)
 for r in data:
  require(r['source_family'] in FAMILIES,'Unexpected family')
  key=tuple(r[k] for k in ('source_family','parent_dataset_id','sample_n','training_seed',
                            'reference_policy','engine','comparator'))
  require(key not in keys,'Duplicate parent/candidate score; hidden pseudoreplication')
  keys.add(key)
  for metric in METRICS:
   require(math.isfinite(float(r[metric+'_difference'])),'Nonfinite parent effect')
  panel=tuple(r[k] for k in ('source_family','sample_n','training_seed','reference_policy','engine','comparator'))
  panels[panel].append(r)
 output=[]
 for key,rs in sorted(panels.items()):
  parents=[r['parent_dataset_id'] for r in rs]
  require(len(set(parents))==len(parents),'Independence violation: parent repeated within panel')
  if len(rs)<5:continue
  row=dict(zip(('source_family','sample_n','training_seed','reference_policy','engine','comparator'),key))
  row['independent_parents']=len(rs)
  for met in METRICS:
   x=np.array([float(r[met+'_difference']) for r in rs])
   p=float(stats.ttest_1samp(x,0,alternative='less').pvalue) if x.std(ddof=1)>0 else float(x.mean()>=0)
   lo,hi=bootstrap_ci(x,args.bootstrap,seed('parent',*key,met))
   row[met+'_mean_difference']=float(x.mean())
   row[met+'_one_sided_p']=p
   row[met+'_bootstrap95_low']=lo
   row[met+'_bootstrap95_high']=hi
   row[met+'_parent_win_share']=float(np.mean(x<0))
  output.append(row)
 require(output,'No inferentially eligible parent-level panels')
 # Supplementary panel adjustment across candidate identities and both metrics,
 # separately for each empirical target/comparator policy.
 groups=collections.defaultdict(list)
 for i,row in enumerate(output):
  for met in METRICS:groups[(row['reference_policy'],row['comparator'])].append((i,met))
 for members in groups.values():
  q=bh([output[i][met+'_one_sided_p'] for i,met in members])
  for (i,met),v in zip(members,q):output[i][met+'_supplementary_bh_q']=v
 for r in output:
  r['supported_joint_supplementary']=int(all(
   r[met+'_supplementary_bh_q']<=.05 and r[met+'_bootstrap95_high']<0 for met in METRICS))
 save_rows(pathlib.Path(args.output)/'parent_cluster_bootstrap_and_BH.csv',output)
 (pathlib.Path(args.output)/'inference_scope.json').write_text(json.dumps(dict(
  independent_unit='parent_dataset_id',panels=len(output),bootstrap_reps=args.bootstrap,
  adjustment='BH across both metrics and all W within each target/reference comparator panel',
  original_confirmatory_BH='untouched',supplementary_only=True,
  selection_conditioned_uncertainty_not_eliminated=True),indent=2)+'\n')
 print('POST_RW_PARENT_CLUSTER_INFERENCE_PASS',len(output))
def coverage(args):
 # Synthetic diagnostic of *interval procedure coverage* for a paired
 # within-parent average effect; does not re-estimate frozen estimator W.
 require(args.repetitions>=100 and args.parents>=10 and args.bootstrap>=300,
         'Coverage experiment too small')
 rng=np.random.default_rng(seed('heavy_tailed_ci_coverage',args.repetitions,args.parents))
 results=[]
 for dependence in (0.0,0.65):
  for distribution in ('gaussian','student_t3','contaminated'):
   total={'normal':0,'cluster_bootstrap':0,'wrong_independent_rows':0}
   lengths=collections.defaultdict(list)
   for sim in range(args.repetitions):
    parent=rng.normal(size=args.parents)*dependence
    if distribution=='gaussian':noise=rng.normal(size=(args.parents,5))
    elif distribution=='student_t3':noise=rng.standard_t(3,size=(args.parents,5))/math.sqrt(3)
    else:
     noise=rng.normal(size=(args.parents,5))
     flags=rng.random((args.parents,5))<.04
     noise[flags]*=12.
    z=parent[:,None]+noise*math.sqrt(1-dependence*dependence)
    effects=z.mean(axis=1);n=len(effects)
    loc=float(effects.mean());se=float(stats.sem(effects))
    a,b=stats.t.interval(.95,n-1,loc=loc,scale=se)
    total['normal']+=a<=0<=b;lengths['normal'].append(b-a)
    a,b=bootstrap_ci(effects,args.bootstrap,seed('coverage',dependence,distribution,sim))
    total['cluster_bootstrap']+=a<=0<=b;lengths['cluster_bootstrap'].append(b-a)
    # Deliberately invalid benchmark (all repeated child scores treated as independent).
    flat=z.ravel();loc=float(flat.mean())
    a,b=stats.t.interval(.95,len(flat)-1,loc=loc,scale=float(stats.sem(flat)))
    total['wrong_independent_rows']+=a<=0<=b;lengths['wrong_independent_rows'].append(b-a)
   for method in total:
    p=total[method]/args.repetitions
    low,high=stats.binomtest(total[method],args.repetitions).proportion_ci(.95,method='exact')
    results.append(dict(distribution=distribution,within_parent_shared_effect=dependence,
      interval_method=method,replications=args.repetitions,independent_parents=args.parents,
      coverage=p,coverage_binomial_low=low,coverage_binomial_high=high,
      mean_ci_width=float(np.mean(lengths[method])),
      status='diagnostic_not_full_pipeline_coverage'))
 save_rows(pathlib.Path(args.output)/'synthetic_parent_ci_coverage.csv',results)
 print('POST_RW_SYNTHETIC_CLUSTER_CI_COVERAGE_PASS',len(results))
def hyperparams(args):
 # Read audited frozen Discovery metadata; never infer optimizer stability
 # solely from Real World scores.
 rows=read_rows(args.registry)
 required={'family','sample_n','training_seed','engine','frozen_weight_sha256',
           'objective_budget','tuning_signature','termination_reason'}
 require(rows and required<=set(rows[0]),'Discovery HPO audit registry missing fields')
 seen=set();out=[]
 groups=collections.defaultdict(list)
 for r in rows:
  require(r['family'] in FAMILIES and r['engine'] in ('ga','nsga2','de','dirichlet'),'Unknown engine')
  k=tuple(r[x] for x in ('family','sample_n','training_seed','engine'))
  require(k not in seen,'Repeated trained unit');seen.add(k)
  require(len(r['frozen_weight_sha256'])==64,'Unverifiable frozen W hash')
  require(int(r['objective_budget'])>0,'Missing optimization budget')
  groups[(r['family'],r['sample_n'],r['engine'])].append(r)
 require(len(seen)==720,'720 individually frozen trained units not verified')
 for key,v in sorted(groups.items()):
  require(len(v)==10 and {int(z['training_seed']) for z in v}==set(range(10)),
          'Missing ten training seeds in hyperparameter cell '+str(key))
  budgets={int(z['objective_budget']) for z in v}
  signatures=collections.Counter(z['tuning_signature'] for z in v)
  term=collections.Counter(z['termination_reason'] for z in v)
  out.append(dict(family=key[0],sample_n=key[1],engine=key[2],
    independent_training_seeds=len(v),unique_frozen_weight_hashes=len({z['frozen_weight_sha256'] for z in v}),
    unique_optimizer_budgets=len(budgets),minimum_budget=min(budgets),maximum_budget=max(budgets),
    selected_tuning_signatures=len(signatures),modal_tuning_fraction=max(signatures.values())/len(v),
    termination_reasons=json.dumps(term,sort_keys=True),stable_budget=int(len(budgets)==1),
    inferential_status='descriptive_training_seed_robustness'))
 save_rows(pathlib.Path(args.output)/'discovery_hpo_budget_stability.csv',out)
 print('POST_RW_FROZEN_DISCOVERY_HPO_AUDIT_PASS',len(out))
def audit_null_manifest(args):
 x=json.loads(pathlib.Path(args.manifest).read_text())
 # Gate: a full-pipeline null must rerun fitting, tuning, frozen selection,
 # and external confirmation in each independently generated null world.
 require(x.get('train_under_each_null') is True,'Null replay must refit every null world')
 require(x.get('retune_hyperparameters_under_each_null') is True,'Null replay must retune under each null')
 require(x.get('rescore_independent_holdout_under_each_null') is True,'Null replay needs separate evaluation')
 require(x.get('all_720_candidates_and_26_baselines') is True,'Null replay cannot drop candidate families')
 require(int(x.get('null_worlds',0))>=100,'Require >=100 independent null-world replications')
 require(x.get('null_generator_documented') and x.get('runner_source_sha256'),'Missing null model provenance')
 require('observed_false_discoveries' in x and isinstance(x['observed_false_discoveries'],list),
         'Null replay has no recorded empirical false discoveries')
 obs=x['observed_false_discoveries']
 require(len(obs)==int(x['null_worlds']),'Null world result count mismatch')
 require(all(isinstance(z,int) and 0<=z<=720 for z in obs),'Invalid false-discovery count')
 any_false=sum(z>0 for z in obs)
 low,high=stats.binomtest(any_false,len(obs)).proportion_ci(.95,method='exact')
 pathlib.Path(args.output).mkdir(parents=True,exist_ok=True)
 (pathlib.Path(args.output)/'null_replay_empirical_error.json').write_text(json.dumps(dict(
  false_discovery_probability=any_false/len(obs),confidence95=[low,high],
  null_worlds=len(obs),mean_false_discoveries=float(np.mean(obs)),
  full_pipeline_provenance_required=True),indent=2)+'\n')
 print('POST_RW_FULL_PIPELINE_NULL_REPLAY_AUDIT_PASS',len(obs))
def smoke(args):
 q=bh([.02,.04,.25]);require(q[0]<=q[1]<=q[2],'BH unexpectedly nonmonotone')
 a=bootstrap_ci(np.array([-1,0,1,2,3],float),300,seed('smoke'))
 require(len(a)==2 and a[0]<=a[1],'Cluster CI broken')
 # Full-pipeline null replay intentionally fails closed if training metadata absent.
 try:check_recovery_manifest(pathlib.Path(args.output)/'missing-not-present.json')
 except FileNotFoundError:pass
 else:raise ValueError('Missing input manifest unexpectedly accepted')
 print('POST_RW_AUDIT_SMOKE_PASS')
def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='stage',required=True)
 q=sub.add_parser('parent-inference');q.add_argument('--manifest',required=True);q.add_argument('--parent-effects',required=True)
 q.add_argument('--output',required=True);q.add_argument('--bootstrap',type=int,default=1000)
 q=sub.add_parser('interval-coverage');q.add_argument('--output',required=True)
 q.add_argument('--bootstrap',type=int,default=500);q.add_argument('--parents',type=int,default=30)
 q.add_argument('--repetitions',type=int,default=500)
 q=sub.add_parser('hyperparameters');q.add_argument('--registry',required=True);q.add_argument('--output',required=True)
 q=sub.add_parser('null-provenance');q.add_argument('--manifest',required=True);q.add_argument('--output',required=True)
 q=sub.add_parser('smoke');q.add_argument('--output',required=True)
 a=p.parse_args();{'parent-inference':parent_inference,'interval-coverage':coverage,
 'hyperparameters':hyperparams,'null-provenance':audit_null_manifest,'smoke':smoke}[a.stage](a)
if __name__=='__main__':main()
