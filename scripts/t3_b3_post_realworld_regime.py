#!/usr/bin/env python3
"""Independent-parent cross-fitted regime recommendation.

Feature inputs must be outcome-blind, extracted without looking at scores.
The recommendation is evaluated on withheld parents, not on training parents.
Any unsupported empirical source/domain transfer is an explicit abstention.
"""
import argparse,collections,csv,gzip,hashlib,json,math,pathlib
import numpy as np
from scipy import stats
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

FEATURES=('sample_n','skewness','kurtosis','coefficient_variation','outlier_fraction',
          'positive_support_share','tail_ratio','median_mean_ratio')
FAMILIES=('normal','lognormal','weibull','invgauss','exgaussian','exwald')
def fail(ok,s):
 if not ok:raise ValueError(s)
def csv_rows(p):
 p=pathlib.Path(p);op=gzip.open if p.suffix=='.gz' else open
 with op(p,'rt',newline='') as f:return list(csv.DictReader(f))
def save(p,rows):
 fail(rows,'No scientific records to export')
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with open(p,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def sha(s):return int.from_bytes(hashlib.sha256(str(s).encode()).digest()[:8],'big')
def numeric(x):
 try:return float(x)
 except (ValueError,TypeError):return float('nan')
def fit_predict(xtr,ytr,xte):
 if len(set(ytr))<2:return np.tile(np.array([1.,0.]),(len(xte),1)),[ytr[0],'__unseen__']
 model=make_pipeline(SimpleImputer(strategy='median',add_indicator=True),
  HistGradientBoostingClassifier(max_iter=80,max_leaf_nodes=9,learning_rate=.05,
    l2_regularization=10,random_state=307))
 model.fit(xtr,ytr)
 p=model.predict_proba(xte);classes=list(model[-1].classes_)
 return p,classes
def crossfit(args):
 effects=csv_rows(args.effects);feat=csv_rows(args.features)
 required={'parent_dataset_id','source_family','sample_n','training_seed','engine','comparator',
  'reference_policy','mse_difference','q95_difference'}
 fail(effects and required<=effects[0].keys(),'Invalid frozen independent-parent effects')
 fail(feat and {'parent_dataset_id','sample_n','source_family','data_source','profile_fit_confidence'}<=feat[0].keys()
      and set(FEATURES)<=feat[0].keys(),'Missing outcome-blind parent regime descriptors')
 # The policy is trained only on TRAIN parents; outcomes held out strictly by parent.
 # Each parent must have exactly one outcome-blind profile per sample size.
 featuremap={}
 for r in feat:
  key=(r['parent_dataset_id'],r['sample_n'])
  fail(key not in featuremap,'Duplicated parent feature row; child attributes must be aggregated first')
  fail(r['source_family'] in FAMILIES,'Unknown family')
  featuremap[key]=r
 # Pool repeated W training seeds within parent ONLY to learn descriptive
 # expected potential gain, never as independent parents.
 d=collections.defaultdict(list)
 for r in effects:
  fail(r['reference_policy']=='holdout_half_mean' or r['reference_policy']=='full_sample_mean',
       'Unrecognized empirical reference')
  if r['reference_policy']!='holdout_half_mean':continue
  if r['comparator']!='mean':continue
  key=(r['parent_dataset_id'],r['sample_n'],r['source_family'],r['engine'])
  fail(r['engine'] in ('ga','nsga2','de','dirichlet'),'Unexpected frozen W policy candidate')
  d[key].append(r)
 units=collections.defaultdict(dict)
 for (pid,n,src,engine),rr in d.items():
  fail(len(rr)==10 and {int(z['training_seed']) for z in rr}==set(range(10)),
       'Incomplete ten independently frozen W train-seed identities')
  units[(pid,n,src)][engine]=(
   float(np.mean([numeric(z['mse_difference']) for z in rr])),
   float(np.mean([numeric(z['q95_difference']) for z in rr])))
 parents=sorted({x[0] for x in units})
 fail(len(parents)>=60,'Insufficient independent parents for evaluation')
 folds={p:sha('T3_POST_RW_POLICY_PARENT_SPLIT|'+p)%5 for p in parents}
 results=[];audit=[]
 for fold in range(5):
  train=[k for k in units if folds[k[0]]!=fold]
  test=[k for k in units if folds[k[0]]==fold]
  fail(train and test,'Empty independent fold')
  # Candidate policy is trained as a regime-level expected-gain classifier.
  # Source family is NOT supplied as a predictor, since it is unknown at deployment.
  xtrain=[];ytrain=[];xval=[];valkeys=[];truth=[]
  for k in train:
   rr=units[k];f=featuremap.get((k[0],k[1]))
   fail(f is not None,'Missing frozen train parent descriptor')
   fail(set(rr)=={'ga','nsga2','de','dirichlet'},'Incomplete four engines')
   # Only choose an evolutionary engine if BOTH MSE and Q95 improve by
   # the prespecified absolute effect threshold and a single engine dominates.
   eligible={engine:max(v) for engine,v in rr.items() if all(x <= -args.minimum_gain for x in v)}
   winner=min(eligible,key=eligible.get) if eligible else 'mean'
   xtrain.append([numeric(f[z]) for z in FEATURES]);ytrain.append(winner)
  for k in test:
   rr=units[k];f=featuremap.get((k[0],k[1]))
   fail(f is not None,'Missing frozen external parent descriptor')
   fail(set(rr)=={'ga','nsga2','de','dirichlet'},'Incomplete four engines')
   xval.append([numeric(f[z]) for z in FEATURES]);valkeys.append(k);truth.append(rr)
  xtrain=np.asarray(xtrain,float);xval=np.asarray(xval,float)
  # No outcome-derived features are supplied to policy fit or prediction.
  p,classes=fit_predict(xtrain,ytrain,xval)
  for i,(key,rr) in enumerate(zip(valkeys,truth)):
   f=featuremap[(key[0],key[1])]
   selected=classes[int(np.argmax(p[i]))]
   confidence=float(max(p[i]))
   margin=float(np.sort(p[i])[-1]-np.sort(p[i])[-2]) if len(classes)>1 else 0.
   abstain=(confidence<args.confidence or margin<args.margin or
       numeric(f['profile_fit_confidence'])<args.profile_confidence)
   # Unknown domain or insufficient classifier confidence => benchmark.
   deploy='mean' if abstain or selected not in rr else selected
   dm,dq=(0.,0.) if deploy=='mean' else rr[deploy]
   # Oracle is DESCRIPTIVE only, evaluated for regret; never fit on test.
   oracle=min((e for e in rr if rr[e][0]<0 and rr[e][1]<0),
              key=lambda e:sum(rr[e]),default='mean')
   best=rr[oracle] if oracle!='mean' else (0.,0.)
   results.append(dict(parent_dataset_id=key[0],sample_n=key[1],source_family=key[2],
    data_source=f['data_source'],fold=fold,selected_candidate=selected,
    deployed_candidate=deploy,abstained=int(abstain),confidence=confidence,
    margin=margin,profile_fit_confidence=f['profile_fit_confidence'],
    mse_gain_against_mean=-dm,q95_gain_against_mean=-dq,
    oracle_mse_gain=-best[0],oracle_q95_gain=-best[1],
    mse_regret=dm-best[0],q95_regret=dq-best[1],
    frozen_no_outcome_features=True))
  audit.append(dict(fold=fold,training_parent_count=len({k[0] for k in train}),
   independent_holdout_parent_count=len({k[0] for k in test}),
   training_rows=len(train),test_rows=len(test),training_classes=json.dumps(sorted(set(ytrain)))))
 # Evaluate parent as inferential unit; sample-size repeated measures stay inside parent.
 pooled=collections.defaultdict(list)
 for r in results:pooled[r['parent_dataset_id']].append(r)
 sums=[]
 for pid,rr in sorted(pooled.items()):
  sums.append(dict(parent_dataset_id=pid,
   mse_gain=float(np.mean([z['mse_gain_against_mean'] for z in rr])),
   q95_gain=float(np.mean([z['q95_gain_against_mean'] for z in rr])),
   mse_regret=float(np.mean([z['mse_regret'] for z in rr])),
   q95_regret=float(np.mean([z['q95_regret'] for z in rr])),
   abstention_fraction=float(np.mean([z['abstained'] for z in rr]))))
 out=pathlib.Path(args.output);out.mkdir(parents=True,exist_ok=True)
 save(out/'crossfit_independent_parent_policy_decisions.csv',results)
 save(out/'crossfit_independent_parent_regret.csv',sums)
 save(out/'crossfit_parent_partition_audit.csv',audit)
 summary={'independent_parents':len(sums),'five_parent_disjoint_folds':True,
  'features':list(FEATURES),'minimum_gain':args.minimum_gain,'confidence':args.confidence,
  'margin':args.margin,'profile_confidence':args.profile_confidence,
  'reference_policy':'holdout_half_mean','mean_parent_abstention':float(np.mean([x['abstention_fraction'] for x in sums])),
  'outcome_blind_deployment':True,'policy_type':'exploratory_crossfit_classifier',
  'external_new_domain_validation':'NOT_PERFORMED','all_720_W_deployment':'ENGINE_AVERAGED_TRAINING_SEED_POLICY_NOT_FROZEN_ONE_W',
  'publication_claim':'SUPPLEMENTARY_EXPLORATORY_ONLY'}
 (out/'regime_policy_scope.json').write_text(json.dumps(summary,indent=2)+'\n')
 print('POST_RW_REGIME_PARENT_CROSSFIT_EXPLORATORY_PASS',len(sums))
def smoke(args):
 sample=np.array([[0,1],[1,0],[2,1],[3,0],[5,4],[0,1],[1,3],[3,1],[2,0],[9,0]],float)
 y=['mean','ga','ga','mean','ga','ga','mean','ga','mean','mean']
 p,cl=fit_predict(sample,y,sample)
 fail(p.shape==(10,2) and len(cl)==2,'Regime classifier smoke failed')
 print('POST_RW_REGIME_POLICY_SMOKE_PASS')
def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='stage',required=True)
 q=sub.add_parser('crossfit');q.add_argument('--effects',required=True);q.add_argument('--features',required=True)
 q.add_argument('--output',required=True);q.add_argument('--minimum-gain',type=float,default=0.0)
 q.add_argument('--confidence',type=float,default=.8);q.add_argument('--margin',type=float,default=.2)
 q.add_argument('--profile-confidence',type=float,default=.6)
 sub.add_parser('smoke')
 a=p.parse_args()
 if a.stage=='smoke':smoke(a)
 else:
  fail(a.minimum_gain>=0 and .5<=a.confidence<1 and 0<=a.margin<1
       and 0<=a.profile_confidence<1,'Invalid prespecified policy thresholds')
  crossfit(a)
if __name__=='__main__':main()
