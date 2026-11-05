#!/usr/bin/env python3
"""T3 B3 Held-out recovery: immutable scores -> individual frozen W inference.
No Monte Carlo, Discovery optimization, or model scoring is executed here.
"""
import argparse,csv,gzip,hashlib,json,math,re
from pathlib import Path
from collections import Counter
import numpy as np
from scipy import stats

FAMILIES=('normal','lognormal','weibull','invgauss','exgaussian','exwald')
ENGINES=('ga','nsga2','de','dirichlet')
SIZES=(200,1000,3000)
RUNS={'within':'41208513291','partial':'41476736420','repair':'41487179284'}
PAT=re.compile(r't3-b3-(crossfamily-)?heldout-(normal|lognormal|weibull|invgauss|exgaussian|exwald)-s(1\d)-n(200|1000|3000)-run(\d+)$')
COLUMNS=['candidate_id','engine','source_family','evaluation_family','training_seed','sample_n','scenario_id','benchmark_role','benchmark','metric','independent_units','difference','ci_lower','ci_upper','gain_pct','gain_pct_lower','gain_pct_upper','p_value','weights_sha256','discovery_sha256']

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def registry_read(path):
 rows=list(csv.DictReader(open(path,newline='')))
 if len(rows)!=720:raise ValueError('Expected exactly 720 Discovery W candidates')
 out={}
 for r in rows:
  key=(r['source_family'],r['engine'],int(r['training_seed']),int(r['sample_n']))
  if key in out or key[0] not in FAMILIES or key[1] not in ENGINES or key[2] not in range(10) or key[3] not in SIZES:raise ValueError('Invalid/duplicate candidate identity')
  if int(r['weight_count'])!=26 or abs(float(r['weight_sum'])-1)>1e-8 or len(r['weights_sha256'])!=64 or len(r['discovery_sha256'])!=64:raise ValueError('Invalid frozen W provenance')
  if r['candidate_id']!=f'{key[0]}|{key[1]}|seed{key[2]:02d}|n{key[3]}':raise ValueError('Candidate ID mismatch')
  out[key]=r
 return out

def benchmark_read(path):
 m={}
 for r in csv.DictReader(open(path,newline='')):
  key=(r['evaluation_family'],int(r['sample_n']),int(r['scenario_id']))
  if key in m or r['own_benchmark']=='mean' or not r['own_benchmark']:raise ValueError('Invalid frozen reference')
  m[key]=r['own_benchmark']
 if len(m)!=6*3*241:raise ValueError('Discovery own benchmark map must cover 6 x 3 x 241')
 return m

def artifact_info(path):
 m=next((PAT.fullmatch(p) for p in path.parts if PAT.fullmatch(p)),None)
 if m is None:raise ValueError('Raw artifact name absent: '+str(path))
 kind='cross' if m.group(1) else 'within'
 permitted=(RUNS['partial'],RUNS['repair']) if kind=='cross' else (RUNS['within'],)
 if m.group(5) not in permitted:raise ValueError('Unexpected source run: '+str(path))
 return kind,m.group(2),int(m.group(3)),int(m.group(4)),m.group(5)

def finite(v):
 x=float(v)
 if not math.isfinite(x):raise ValueError('Nonfinite loss')
 return x

def sample_stats(v,one_sided=True):
 n=len(v);mean=float(np.mean(v))
 if n<3:return mean,float('nan'),float('nan'),float('nan')
 sd=float(np.std(v,ddof=1))
 if sd<=1e-14*max(1,abs(mean)):
  return mean,mean,mean,(2**(-n) if mean<0 else 1.0) if one_sided else float('nan')
 se=sd/math.sqrt(n);tcrit=float(stats.t.ppf(.975,n-1))
 return mean,mean-tcrit*se,mean+tcrit*se,float(stats.t.cdf(mean/se,n-1)) if one_sided else float('nan')

def paired_pct(v):
 m,lo,hi,_=sample_stats(v,False)
 return m,lo,hi

def reduce(a):
 reg=registry_read(a.registry);byid={r['candidate_id']:r for r in reg.values()}
 bench=benchmark_read(a.benchmark);files=sorted(Path(a.input).rglob('scores.csv'))
 expected_seeds=([10] if a.smoke else list(range(10,20)))
 if len(files)!=(1 if a.smoke else 20):raise ValueError('Expected 20 immutable own/cross scoring artifacts (or 1 smoke)')
 seen=set();pairs={};sources=[]
 for path in files:
  typ,family,seed,n,run=artifact_info(path)
  if family!=a.family or n!=a.n or seed not in expected_seeds or (typ,seed) in seen:raise ValueError('Unexpected/duplicate evaluation cell: '+str(path))
  seen.add((typ,seed))
  score_sha=digest(path)
  for mname,hashkey in (('score_manifest.csv','score_sha256'),('transfer_manifest.csv','scores_sha256')):
   mp=path.parent/mname
   if mp.exists():
    meta=next(csv.DictReader(mp.open(newline='')))
    if hashkey in meta and meta[hashkey].lower()!=score_sha:raise ValueError('Raw score SHA mismatch: '+str(path))
  reference={};candidates={};classic=set()
  with path.open(newline='') as f:
   rd=csv.DictReader(f)
   need={'model','mse','q95','scenario_id','training_seed','sample_n','source_family','evaluation_family'}
   if not need.issubset(rd.fieldnames):raise ValueError('Raw-score fields incomplete: '+str(path))
   for r in rd:
    model=r['model'];sid=int(r['scenario_id']);train=int(r['training_seed']);src=r['source_family'];dst=r['evaluation_family']
    if dst!=family or int(r['sample_n'])!=n or train not in range(10) or sid<0 or sid>320:raise ValueError('Raw score identity mismatch')
    if (typ=='within')!=(src==dst):raise ValueError('Source/evaluation family mismatch')
    if int(r.get('heldout_seed') or r.get('seed_index') or -1)!=seed:raise ValueError('Evaluation seed mismatch')
    val=(finite(r['mse']),finite(r['q95']))
    own=bench.get((dst,n,sid))
    if own is None:raise ValueError('Score has unregistered scenario')
    if model in ('mean',own):
     key=(sid,model)
     if key in reference and any(abs(x-y)>1e-10*max(1,abs(x),abs(y)) for x,y in zip(val,reference[key])):raise ValueError('Inconsistent repeated classical baseline')
     reference[key]=val
    if model in ENGINES:
     identity=reg.get((src,model,train,n))
     if identity is None:raise ValueError('Unregistered frozen W')
     input_sha=r.get('discovery_sha256') or r.get('source_discovery_sha256')
     if input_sha!=identity['discovery_sha256']:raise ValueError('Frozen Discovery RDS hash mismatch')
     key=(identity['candidate_id'],sid)
     if key in candidates:raise ValueError('Duplicate individual W score')
     candidates[key]=val
    elif model not in ('convex_mse','local_deterministic'):classic.add((src,train,sid,model))
  cnt=5 if typ=='cross' else 1
  if len(candidates)!=cnt*10*4*241 or len(classic)!=cnt*10*26*241 or len(reference)!=241*2:raise ValueError('Incomplete candidate/classical source scoring grid: '+str(path))
  for (cid,sid),value in candidates.items():
   for role,ref_model in (('own',bench[(family,n,sid)]),('mean','mean')):
    base=reference[(sid,ref_model)]
    key=(cid,sid,role)
    item=pairs.setdefault(key,{'benchmark':ref_model,'mse':{},'q95':{},'gmse':{},'gq95':{}})
    if seed in item['mse']:raise ValueError('Evaluation seed reused')
    item['mse'][seed]=value[0]-base[0];item['q95'][seed]=value[1]-base[1]
    item['gmse'][seed]=100*(base[0]-value[0])/max(abs(base[0]),np.finfo(float).eps)
    item['gq95'][seed]=100*(base[1]-value[1])/max(abs(base[1]),np.finfo(float).eps)
  sources.append({'kind':typ,'family':family,'evaluation_seed':seed,'n':n,'run_id':run,'score_sha256':score_sha,'raw_path':str(path),'candidate_rows':len(candidates)})
 if seen!=({('cross',10)} if a.smoke else {(kind,s) for kind in ('within','cross') for s in expected_seeds}):raise ValueError('Own/cross source coverage incomplete')
 if len(pairs)!=(5 if a.smoke else 6)*10*4*241*2:raise ValueError('Individual candidate x scenario x benchmark incomplete')
 out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
 with gzip.open(out/'metrics_unadjusted.csv.gz','wt',newline='') as f,gzip.open(out/'paired_seed_differences.csv.gz','wt',newline='') as g:
  w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader()
  u=csv.DictWriter(g,fieldnames=['candidate_id','scenario_id','benchmark_role','benchmark','eval_seeds','differences_mse','differences_q95']);u.writeheader()
  for (cid,sid,role),v in sorted(pairs.items()):
   meta=byid[cid];base={'candidate_id':cid,'engine':meta['engine'],'source_family':meta['source_family'],'evaluation_family':a.family,'training_seed':meta['training_seed'],
    'sample_n':a.n,'scenario_id':sid,'benchmark_role':role,'benchmark':v['benchmark'],'independent_units':len(expected_seeds),
    'weights_sha256':meta['weights_sha256'],'discovery_sha256':meta['discovery_sha256']}
   d1=[v['mse'][s] for s in expected_seeds];d2=[v['q95'][s] for s in expected_seeds]
   u.writerow({'candidate_id':cid,'scenario_id':sid,'benchmark_role':role,'benchmark':v['benchmark'],'eval_seeds':';'.join(map(str,expected_seeds)),
      'differences_mse':';'.join(f'{z:.17g}' for z in d1),'differences_q95':';'.join(f'{z:.17g}' for z in d2)})
   for metric,d,gains in (('mse',d1,[v['gmse'][s] for s in expected_seeds]),('q95',d2,[v['gq95'][s] for s in expected_seeds])):
    mu,lo,hi,p=sample_stats(d);pct,pl,pu=paired_pct(gains)
    w.writerow(dict(base,metric=metric,difference=mu,ci_lower=lo,ci_upper=hi,gain_pct=pct,gain_pct_lower=pl,gain_pct_upper=pu,p_value=p))
 report={'protocol':'T3_HELDOUT_SEEDWISE_V1','stage':'heldout','family':a.family,'n':a.n,'eval_seeds':expected_seeds,
  'candidate_scenario_benchmark_groups':len(pairs),'metric_rows':len(pairs)*2,'original_sources':sources,
  'registry_sha256':digest(a.registry),'benchmark_map_sha256':digest(a.benchmark),'training_seed_averaging':False,'scoring_reexecuted':False,'smoke':a.smoke}
 (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
 print('HELDOUT_SEEDWISE_REDUCE_PASS',a.family,a.n,len(pairs)*2,flush=True)

def finalize(a):
 files=sorted(Path(a.input).rglob('metrics_unadjusted.csv.gz'))
 if len(files)!=18:raise ValueError(f'Expected 18 complete Held-out blocks; got {len(files)}')
 pairs=set();pvals=[];lens=[];common_registry=set();common_benchmark=set()
 for path in files:
  meta=json.loads((path.parent/'manifest.json').read_text());ident=(meta['family'],int(meta['n']))
  if ident in pairs or meta['smoke'] or meta['eval_seeds']!=list(range(10,20)) or meta['metric_rows']!=231360 or len(meta['original_sources'])!=20:raise ValueError('Invalid block coverage/manifest')
  pairs.add(ident);common_registry.add(meta['registry_sha256']);common_benchmark.add(meta['benchmark_map_sha256'])
  length=0
  with gzip.open(path,'rt',newline='') as f:
   for row in csv.DictReader(f):
    p=float(row['p_value']);pvals.append(p);length+=1
  if length!=231360:raise ValueError('Metric row count mismatch')
  lens.append(length)
 if pairs!={(f,n) for f in FAMILIES for n in SIZES} or len(common_registry)!=1 or len(common_benchmark)!=1:raise ValueError('18 blocks do not share the same frozen sources')
 pv=np.array(pvals,np.float64)
 if len(pv)!=4164480 or np.any(~np.isfinite(pv)) or np.any((pv<0)|(pv>1)):raise ValueError('Global BH hypothesis family invalid')
 order=np.argsort(pv,kind='stable');size=len(pv)
 qv=np.empty(size,dtype=np.float64)
 qv[order]=np.minimum.accumulate((pv[order]*size/np.arange(1,size+1,dtype=np.float64))[::-1])[::-1]
 np.minimum(qv,1.0,out=qv)
 out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
 counts=Counter();offset=0;tax_count=0
 taxonomy_cols=['candidate_id','engine','source_family','evaluation_family','training_seed','sample_n','scenario_id','benchmark_role','benchmark',
    'mse_gain_pct','q95_gain_pct','mse_q_BH','q95_q_BH','mse_CI_upper','q95_CI_upper','tier1_joint_FDR','tier2_joint_CI',
    'tier3_mse_FDR','tier3_q95_FDR','highest_tier']
 for path,length in zip(files,lens):
  dest=out/path.parent.name;dest.mkdir()
  with gzip.open(path,'rt',newline='') as f,gzip.open(dest/'individual_candidate_inference.csv.gz','wt',newline='') as g,gzip.open(dest/'individual_winner_taxonomy.csv.gz','wt',newline='') as h:
   reader=csv.DictReader(f);w=csv.DictWriter(g,fieldnames=reader.fieldnames+['q_value_global','passes_bh']);w.writeheader()
   tw=csv.DictWriter(h,fieldnames=taxonomy_cols);tw.writeheader();first=None
   for j,row in enumerate(reader):
    val=float(qv[offset+j]);row['q_value_global']=f'{val:.17g}';row['passes_bh']=str(val<=.05);w.writerow(row)
    if first is None:
     if row['metric']!='mse':raise ValueError('Unpaired MSE/Q95 output')
     first=row
    else:
     if row['metric']!='q95' or any(row[k]!=first[k] for k in ('candidate_id','evaluation_family','scenario_id','benchmark_role')):raise ValueError('Metric row order corrupted')
     wm=float(first['ci_upper'])<0;wq=float(row['ci_upper'])<0
     fm=wm and float(first['q_value_global'])<=.05;fq=wq and val<=.05
     t1=fm and fq;t2=wm and wq and not t1;t3m=fm and not(t1 or t2);t3q=fq and not(t1 or t2)
     tier='tier1_joint_FDR' if t1 else 'tier2_joint_CI' if t2 else 'tier3_mse_FDR' if t3m else 'tier3_q95_FDR' if t3q else 'tier4_no_supported_win'
     record={k:row[k] for k in ('candidate_id','engine','source_family','evaluation_family','training_seed','sample_n','scenario_id','benchmark_role','benchmark')}
     record.update(mse_gain_pct=first['gain_pct'],q95_gain_pct=row['gain_pct'],mse_q_BH=first['q_value_global'],q95_q_BH=row['q_value_global'],
       mse_CI_upper=first['ci_upper'],q95_CI_upper=row['ci_upper'],tier1_joint_FDR=t1,tier2_joint_CI=t2,tier3_mse_FDR=t3m,tier3_q95_FDR=t3q,highest_tier=tier)
     tw.writerow(record);counts[(row['candidate_id'],row['benchmark_role'],tier)]+=1;tax_count+=1;first=None
   if first is not None:raise ValueError('Incomplete paired metric rows')
  offset+=length
 with (out/'candidate_tier_summary.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['candidate_id','benchmark_role','highest_tier','scenario_count'])
  for key,v in sorted(counts.items()):w.writerow([*key,v])
 (out/'global_panel_manifest.json').write_text(json.dumps({'protocol':'T3_HELDOUT_SEEDWISE_V1','hypotheses_BH':size,'taxonomy_rows':tax_count,
    'blocks':18,'frozen_candidates':720,'scoring_reexecuted':False,'training_seed_averaging':False,'global_BH':'all_candidates_all_scenarios_own_mean_both_metrics',
    'registry_sha256':next(iter(common_registry)),'benchmark_map_sha256':next(iter(common_benchmark))},indent=2)+'\n')
 print('HELDOUT_SEEDWISE_GLOBAL_PASS',size,tax_count,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='op',required=True)
 x=sub.add_parser('reduce');x.add_argument('--input',required=True);x.add_argument('--registry',required=True)
 x.add_argument('--benchmark',required=True);x.add_argument('--family',required=True,choices=FAMILIES);x.add_argument('--n',required=True,type=int,choices=SIZES)
 x.add_argument('--output',required=True);x.add_argument('--smoke',action='store_true')
 x=sub.add_parser('finalize');x.add_argument('--input',required=True);x.add_argument('--output',required=True)
 a=p.parse_args()
 reduce(a) if a.op=='reduce' else finalize(a)