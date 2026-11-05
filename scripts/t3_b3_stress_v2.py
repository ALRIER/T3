#!/usr/bin/env python3
"""T3 B3 unified Stress V2: original per-W recovery and independent paired inference.
Scientific contract: 20:24 selects the classic comparator on original Stress;
25:29 is its historical confirmation; 50:59 is independent NEW confirmation.
Adapted training has separate RNG streams 60:69 and is exploratory/post-hoc.
No metrics from a training seed may be pooled between independent W candidates.
"""
import argparse,csv,gzip,json,hashlib,math,re,collections
from pathlib import Path
import numpy as np
from scipy import stats

FAMILIES=('normal','lognormal','weibull','invgauss','exgaussian','exwald')
ENGINES=('ga','nsga2','de','dirichlet')
SIZES=(200,1000,3000)
CLASSICS=('mean','median','trimmed20','trimmed10','winsorized_0.15','mode_hsm',
'mode_parzen','trimean','huber','biweight','winsorized_0.05','winsorized_0.1',
'winsorized_0.2','mom_k5','mom_k10','mom_k20','catoni_a0.05','catoni_a0.1',
'catoni_a0.2','catoni_a0.35','catoni_a0.5','huber_k0.75','huber_k1',
'huber_k1.345','huber_k1.75','huber_k2')
PAT=re.compile(r't3-b3-(crossfamily-)?stress-(normal|lognormal|weibull|invgauss|exgaussian|exwald)-s(2\d)-n(200|1000|3000)-run(\d+)$')
RUNS={'within':'41208513291','cross_partial':'41476743557','cross_repair':'41487292889'}
METRIC_COLUMNS=('candidate_id','engine','source_family','evaluation_family','training_seed',
 'sample_n','scenario_id','mechanism','benchmark_role','benchmark','metric','independent_units',
 'difference','ci_lower','ci_upper','p_value','gain_pct','gain_pct_lower',
 'gain_pct_upper','weights_sha256','discovery_sha256','experiment')
PAIRED_COLUMNS=('candidate_id','source_family','evaluation_family','training_seed','sample_n',
 'scenario_id','mechanism','benchmark_role','benchmark','evaluation_seeds',
 'differences_mse','differences_q95','gains_mse','gains_q95','weights_sha256','discovery_sha256','experiment')

def fail(msg):raise ValueError(msg)
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def numeric(x):
 y=float(x)
 if not math.isfinite(y):fail('Nonfinite result')
 return y
def check_registry(path):
 rows=list(csv.DictReader(open(path,newline='')))
 reg={}
 for r in rows:
  key=(r['source_family'],r['engine'],int(r['training_seed']),int(r['sample_n']))
  if key in reg or key[0] not in FAMILIES or key[1] not in ENGINES or key[2] not in range(10) or key[3] not in SIZES:fail('Frozen registry identity collision')
  if len(r['weights_sha256'])!=64 or len(r['discovery_sha256'])!=64 or abs(float(r['weight_sum'])-1)>1e-8:fail('Invalid frozen registry')
  reg[key]=r
 if len(rows)!=720 or len(reg)!=720:fail('Expected all 720 distinct frozen W identities')
 return reg

def raw_info(path):
 m=next((PAT.fullmatch(part) for part in path.parts if PAT.fullmatch(part)),None)
 if m is None:fail('Cannot identify historical source: '+str(path))
 scope='cross' if m[1] else 'within'
 run=m[5]
 if (scope=='within' and run!=RUNS['within']) or (scope=='cross' and run not in (RUNS['cross_partial'],RUNS['cross_repair'])):
  fail('Unapproved historical run: '+run)
 return scope,m[2],int(m[3]),int(m[4]),run

def ci_p(values):
 x=np.asarray(values,np.float64);n=len(x)
 if n<3:fail('Insufficient evaluation seeds')
 m=float(np.mean(x));sd=float(np.std(x,ddof=1))
 if sd<=1e-14*max(1,abs(m)):
  return m,m,m,2.0**(-n) if m<0 else 1.0
 se=sd/math.sqrt(n)
 c=float(stats.t.ppf(.975,n-1))
 return m,m-c*se,m+c*se,float(stats.t.cdf(m/se,n-1))

def effect_ci(values):
 m,lo,hi,_=ci_p(values)
 return m,lo,hi

def emit_panel(out,pairs,reg_by_id,bench_map,eval_seeds,scope,manifest):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 n_eval=len(eval_seeds)
 with gzip.open(out/'paired_seed_differences.csv.gz','wt',newline='') as g,gzip.open(out/'metrics_unadjusted.csv.gz','wt',newline='') as f:
  w=csv.DictWriter(f,fieldnames=METRIC_COLUMNS);w.writeheader()
  pw=csv.DictWriter(g,fieldnames=PAIRED_COLUMNS);pw.writeheader()
  for (cid,sid,role),unit in sorted(pairs.items()):
   meta=reg_by_id[cid]
   if set(unit['mse'])!=set(eval_seeds) or set(unit['q95'])!=set(eval_seeds):fail('Missing paired unit '+str((cid,sid,role)))
   labels={'candidate_id':cid,'engine':meta['engine'],'source_family':meta['source_family'],
    'evaluation_family':manifest['family'],'training_seed':meta['training_seed'],
    'sample_n':manifest['sample_n'],'scenario_id':sid,'mechanism':unit['mechanism'],
    'benchmark_role':role,'benchmark':bench_map[sid] if role=='own' else 'mean',
    'weights_sha256':meta['weights_sha256'],'discovery_sha256':meta['discovery_sha256'],
    'experiment':scope}
   dm=[unit['mse'][s] for s in eval_seeds];dq=[unit['q95'][s] for s in eval_seeds]
   gm=[unit['gmse'][s] for s in eval_seeds];gq=[unit['gq95'][s] for s in eval_seeds]
   pw.writerow({**{k:labels[k] for k in PAIRED_COLUMNS if k in labels},'evaluation_seeds':';'.join(map(str,eval_seeds)),
    'differences_mse':';'.join(f'{x:.17g}' for x in dm),'differences_q95':';'.join(f'{x:.17g}' for x in dq),
    'gains_mse':';'.join(f'{x:.17g}' for x in gm),'gains_q95':';'.join(f'{x:.17g}' for x in gq)})
   for metric,d,gain in (('mse',dm,gm),('q95',dq,gq)):
    m,lo,hi,p=ci_p(d);pct,pl,pu=effect_ci(gain)
    w.writerow({**labels,'metric':metric,'independent_units':n_eval,'difference':m,'ci_lower':lo,'ci_upper':hi,
      'p_value':p,'gain_pct':pct,'gain_pct_lower':pl,'gain_pct_upper':pu})
 manifest.update(experiment=scope,calibration_seeds=list(range(20,25)),inference_seeds=eval_seeds,
    hypothesis_count=len(pairs)*2,paired_cells=len(pairs),candidate_count=len(set(x[0] for x in pairs)),
    scoring_reexecuted=False if scope=='original' else True,
    original_score_shards_reused=(scope=='original'),training_seed_averaging=False)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('T3_STRESS_V2_BLOCK_PASS',scope,manifest['family'],manifest['sample_n'],len(pairs),flush=True)

def read_original(a):
 reg=check_registry(a.registry);by_id={r['candidate_id']:r for r in reg.values()}
 paths=sorted(Path(a.input).rglob('scores.csv'))
 if len(paths)!=20:fail('Expected exactly ten own and ten cross-family scoring artifacts per block')
 seen=set();baseline={};candidate={};mechs={}
 for path in paths:
  scope,family,s,n,run=raw_info(path)
  if family!=a.family or n!=a.n or s not in range(20,30) or (scope,s) in seen:fail('Source identity outside original Stress grid')
  seen.add((scope,s))
  manifest=path.parent/('score_manifest.csv' if scope=='within' else 'transfer_manifest.csv')
  if not manifest.exists():fail('Original score manifest missing: '+str(path))
  m=next(csv.DictReader(manifest.open(newline='')))
  sha=m.get('score_sha256') or m.get('scores_sha256')
  if sha and sha.lower()!=digest(path):fail('Immutable score SHA mismatch: '+str(path))
  count_candidates=set();count_classic=set()
  with path.open(newline='') as f:
   rd=csv.DictReader(f)
   required={'model','mse','q95','training_seed','source_family','evaluation_family','sample_n','scenario_id'}
   if not required.issubset(rd.fieldnames):fail('Source scoring columns are incomplete')
   for row in rd:
    src=row['source_family'];dst=row['evaluation_family'];tr=int(row['training_seed']);sid=int(row['scenario_id'])
    if (src==dst)!=(scope=='within') or dst!=family or tr not in range(10) or int(row['sample_n'])!=n:
     fail('Frozen candidate identity corruption: '+str(path))
    if sid<0 or sid>320:fail('Invalid Stress scenario ID')
    actual_seed=int(row.get('stress_seed') or row.get('seed_index') or -1)
    if actual_seed!=s:fail('Mismatched independent Stress evaluation seed')
    mechanism=row.get('mechanism')
    if mechanism not in ('mixture_bimodal_near','mixture_bimodal_far'):fail('Stress contains a training mechanism')
    if sid in mechs and mechs[sid]!=mechanism:fail('Scenario mechanism differs across shards')
    mechs[sid]=mechanism
    values=(numeric(row['mse']),numeric(row['q95']))
    model=row['model']
    if model in CLASSICS:
     key=(s,sid,model)
     if key in baseline and any(abs(x-y)>1e-9*max(1,abs(x),abs(y)) for x,y in zip(baseline[key],values)):fail('Classical benchmark changes across training seeds')
     baseline[key]=values;count_classic.add((tr,sid,model,src))
    elif model in ENGINES:
     k=(src,model,tr,n)
     if k not in reg:fail('Candidate absent from frozen Discovery registry')
     entry=reg[k]
     rowsha=row.get('source_discovery_sha256') or row.get('discovery_sha256')
     if rowsha!=entry['discovery_sha256']:fail('Discovery RDS provenance mismatch')
     key=(entry['candidate_id'],sid,s)
     if key in candidate:fail('Duplicate candidate x scenario x evaluation seed')
     candidate[key]=values;count_candidates.add((entry['candidate_id'],sid))
  origin_count=1 if scope=='within' else 5
  if len(count_candidates)!=origin_count*10*4*80 or len(count_classic)!=origin_count*10*26*80:
   fail('Incomplete 80-scenario source score coverage: '+str(path))
 if seen!={(typ,s) for typ in ('within','cross') for s in range(20,30)}:fail('Incomplete original 360-shard Stress coverage')
 if len(mechs)!=80 or len(baseline)!=10*80*26 or len(candidate)!=240*80*10:
  fail('Incorrect 80-cell/26-classic/240-candidate original score coverage')
 # Calibration is completely disjoint from evaluation. Match original normalized MSE/Q95 policy.
 bench={}
 for sid in sorted(mechs):
  refs=[x for x in CLASSICS if x!='mean']
  scale_m=np.mean([min(baseline[(s,sid,model)][0] for model in CLASSICS) for s in range(20,25)])
  scale_q=np.mean([min(baseline[(s,sid,model)][1] for model in CLASSICS) for s in range(20,25)])
  vals={model:.5*(np.mean([baseline[(s,sid,model)][0] for s in range(20,25)])/scale_m+
                      np.mean([baseline[(s,sid,model)][1] for s in range(20,25)])/scale_q)
        for model in refs}
  bench[sid]=min(refs,key=lambda x:(vals[x],CLASSICS.index(x)))
 pairs={}
 for (cid,sid,seed),vals in candidate.items():
  if seed not in range(25,30):continue
  for role,benchmark in (('own',bench[sid]),('mean','mean')):
   b=baseline[(seed,sid,benchmark)]
   entry=pairs.setdefault((cid,sid,role),{'mse':{},'q95':{},'gmse':{},'gq95':{},'mechanism':mechs[sid]})
   if seed in entry['mse']:fail('Duplicate paired evaluation')
   entry['mse'][seed]=vals[0]-b[0];entry['q95'][seed]=vals[1]-b[1]
   entry['gmse'][seed]=100*(b[0]-vals[0])/max(abs(b[0]),np.finfo(float).eps)
   entry['gq95'][seed]=100*(b[1]-vals[1])/max(abs(b[1]),np.finfo(float).eps)
 if len(pairs)!=240*80*2:fail('Original Stress panel lost individual candidates')
 out=Path(a.output)
 emit_panel(out,pairs,by_id,bench,list(range(25,30)),'original',{'family':a.family,'sample_n':a.n,
  'original_seed_set':list(range(20,30)),'input_raw_scores':20,'frozen_registry_sha256':digest(a.registry)})
 with (out/'benchmark_map.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['evaluation_family','sample_n','scenario_id','mechanism','own_benchmark','calibration_seeds','confirmation_seeds'])
  for sid,ref in sorted(bench.items()):
   w.writerow([a.family,a.n,sid,mechs[sid],ref,'20;21;22;23;24','25;26;27;28;29'])

def read_new(a):
 paths=sorted(Path(a.input).rglob('scores.csv'))
 if len(paths)!=10:fail('Expected exactly ten NEW, immutable Stress scoring shards 50:59')
 original_registry=check_registry(a.registry);by_id={r['candidate_id']:r for r in original_registry.values()}
 benchmark={}
 for row in csv.DictReader(open(a.benchmark,newline='')):
  if row['evaluation_family']!=a.family or int(row['sample_n'])!=a.n:fail('Wrong original calibration benchmark map')
  sid=int(row['scenario_id'])
  if sid in benchmark:fail('Duplicate calibration scenario')
  benchmark[sid]=(row['own_benchmark'],row['mechanism'])
 if len(benchmark)!=80:fail('Original Stress calibration map must have 80 scenarios')
 if a.adapted_registry:
  for r in csv.DictReader(open(a.adapted_registry,newline='')):
   cid=r['candidate_id']
   if cid in by_id or not cid.startswith('adapted|'):fail('Adapted W candidate identity invalid')
   if cid in by_id:fail('Duplicate adapted candidate')
   by_id[cid]=r
  if len(by_id)!=1440:fail('Expected 720 original + 720 adapted W')
 seen=set();baseline={};pairs={};expected_candidates=480 if a.adapted_registry else 240
 for path in paths:
  with path.open(newline='') as f:
   rd=csv.DictReader(f)
   required={'candidate_id','scenario_id','model','mse','q95','evaluation_seed','evaluation_family','sample_n','source_family','training_seed','discovery_sha256','weights_sha256'}
   if not required.issubset(rd.fieldnames):fail('New Stress score output is incomplete')
   local_classic={};local_learned={};seed_from_rows=set()
   for row in rd:
    seed=int(row['evaluation_seed']);seed_from_rows.add(seed)
    if row['evaluation_family']!=a.family or int(row['sample_n'])!=a.n:fail('Wrong new confirmation family/size')
    sid=int(row['scenario_id']);model=row['model'];value=(numeric(row['mse']),numeric(row['q95']))
    if sid not in benchmark:fail('New Stress input contains non-Stress scenario')
    if model in CLASSICS:
     k=(sid,model)
     if k in local_classic:fail('Duplicate new classical benchmark')
     local_classic[k]=value
    else:
     cid=row['candidate_id'];key=(cid,sid)
     if cid not in by_id or key in local_learned:fail('Unknown or duplicated individual W')
     meta=by_id[cid]
     if row['source_family']!=meta['source_family'] or int(row['training_seed'])!=int(meta['training_seed']) or row['weights_sha256']!=meta['weights_sha256'] or row['discovery_sha256']!=meta['discovery_sha256']:fail('New score weights identity/provenance mismatch')
     local_learned[key]=value
   if len(seed_from_rows)!=1:fail('New scoring shard mixes evaluation seeds')
   seed=next(iter(seed_from_rows))
   if seed in seen or seed not in range(50,60):fail('Wrong new evaluation seed')
   seen.add(seed)
   if len(local_classic)!=80*26 or len(local_learned)!=80*expected_candidates:fail('New score shard lacks 26 classical and 720 W candidates')
   for (cid,sid),val in local_learned.items():
    for role,ref in (('own',benchmark[sid][0]),('mean','mean')):
     b=local_classic[(sid,ref)]
     z=pairs.setdefault((cid,sid,role),{'mse':{},'q95':{},'gmse':{},'gq95':{},'mechanism':benchmark[sid][1]})
     z['mse'][seed]=val[0]-b[0];z['q95'][seed]=val[1]-b[1]
     z['gmse'][seed]=100*(b[0]-val[0])/max(abs(b[0]),np.finfo(float).eps)
     z['gq95'][seed]=100*(b[1]-val[1])/max(abs(b[1]),np.finfo(float).eps)
 if seen!=set(range(50,60)) or len(pairs)!=expected_candidates*80*2:fail('New independent confirmation coverage incomplete')
 bench={sid:ref for sid,(ref,_) in benchmark.items()}
 emit_panel(a.output,pairs,by_id,bench,list(range(50,60)),'independent_confirmation_v2',
  {'family':a.family,'sample_n':a.n,'new_seed_set':list(range(50,60)),
   'frozen_registry_sha256':digest(a.registry),'original_calibration_benchmark_sha256':digest(a.benchmark)})
 
def finalize(a):
 folders=list(Path(a.input).rglob('metrics_unadjusted.csv.gz'))
 if len(folders)!=18:fail('Expected 18 independent family x n scoring recovery panels')
 indexed={}
 plist=[];sizes=[];meta=[]
 for path in folders:
  m=json.loads((path.parent/'manifest.json').read_text())
  k=(m['family'],int(m['sample_n']))
  if k in indexed or k[0] not in FAMILIES or k[1] not in SIZES:fail('Duplicated panel')
  indexed[k]=path;meta.append(m)
 if set(indexed)!={(f,n) for f in FAMILIES for n in SIZES}:fail('Missing a source/destination family or sample size')
 if len({m['experiment'] for m in meta})!=1:fail('Do not combine historical and new Stress tests in one p-value family')
 for k in sorted(indexed):
  pp=[];path=indexed[k]
  with gzip.open(path,'rt',newline='') as f:
   for r in csv.DictReader(f):pp.append(numeric(r['p_value']))
  expected=(240 if meta[0]['experiment']=='original' else int(next(m['candidate_count'] for m in meta if m['family']==k[0] and int(m['sample_n'])==k[1])))*80*2*2
  if len(pp)!=expected:fail('Incomplete candidate x scenario x reference x metric count')
  plist.extend(pp);sizes.append(len(pp))
 p=np.asarray(plist,dtype=np.float64)
 order=np.argsort(p,kind='stable');N=len(p)
 q=np.empty(N,dtype=np.float64);q[order]=np.minimum.accumulate((p[order]*N/np.arange(1,N+1,dtype=np.float64))[::-1])[::-1];np.minimum(q,1.,out=q)
 out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
 overall=collections.Counter();entries=[];offset=0
 taxcols=('candidate_id','engine','source_family','evaluation_family','training_seed','sample_n','scenario_id','mechanism','benchmark_role','benchmark','weights_sha256','discovery_sha256','experiment','highest_tier',
 'tier1_joint_bh','tier2_joint_ci_only','tier3_mse_bh','tier3_q95_bh','secondary_mse_worse','secondary_q95_worse','mse_gain_pct','q95_gain_pct','mse_gain_ci_lower','mse_gain_ci_upper','q95_gain_ci_lower','q95_gain_ci_upper','mse_q_global','q95_q_global')
 for key in sorted(indexed):
  path=indexed[key];dest=out/(key[0]+'-n'+str(key[1]));dest.mkdir()
  with gzip.open(path,'rt',newline='') as source,gzip.open(dest/'metrics_global_bh.csv.gz','wt',newline='') as f,gzip.open(dest/'winner_taxonomy.csv.gz','wt',newline='') as g:
   r=csv.DictReader(source);w=csv.DictWriter(f,fieldnames=r.fieldnames+['q_value_global','passes_bh']);w.writeheader()
   t=csv.DictWriter(g,fieldnames=taxcols);t.writeheader()
   pair=None;nr=0;nt=0
   for row in r:
    qq=float(q[offset+nr]);nr+=1;row['q_value_global']=f'{qq:.17g}';row['passes_bh']=str(qq<=.05)
    w.writerow(row)
    if pair is None:
     if row['metric']!='mse':fail('MSE/Q95 pairing order failed')
     pair=row
    else:
     if row['metric']!='q95' or tuple(row[c] for c in ('candidate_id','scenario_id','benchmark_role'))!=tuple(pair[c] for c in ('candidate_id','scenario_id','benchmark_role')):fail('Misaligned paired metric rows')
     a1=numeric(pair['ci_upper'])<0;b1=numeric(row['ci_upper'])<0
     aa=a1 and numeric(pair['q_value_global'])<=.05;bb=b1 and qq<=.05
     tier='tier1_joint_BH' if aa and bb else 'tier2_joint_CI_only' if a1 and b1 else 'tier3_MSE_BH' if aa else 'tier3_Q95_BH' if bb else 'tier4_no_BH_joint_or_single'
     record={c:row[c] for c in ('candidate_id','engine','source_family','evaluation_family','training_seed','sample_n','scenario_id','mechanism','benchmark_role','benchmark','weights_sha256','discovery_sha256','experiment')}
     record.update(highest_tier=tier,tier1_joint_bh=aa and bb,tier2_joint_ci_only=a1 and b1 and not(aa and bb),
       tier3_mse_bh=aa and not(a1 and b1),tier3_q95_bh=bb and not(a1 and b1),
       secondary_mse_worse=numeric(pair['difference'])>0,secondary_q95_worse=numeric(row['difference'])>0,
       mse_gain_pct=pair['gain_pct'],q95_gain_pct=row['gain_pct'],
       mse_gain_ci_lower=pair['gain_pct_lower'],mse_gain_ci_upper=pair['gain_pct_upper'],
       q95_gain_ci_lower=row['gain_pct_lower'],q95_gain_ci_upper=row['gain_pct_upper'],
       mse_q_global=pair['q_value_global'],q95_q_global=row['q_value_global'])
     t.writerow(record);nt+=1;overall[(row['experiment'],row['benchmark_role'],row['mechanism'],tier)]+=1;pair=None
   if pair is not None or nr!=sizes[sorted(indexed).index(key)] or nt*2!=nr:fail('Incomplete global BH output')
  offset+=nr;entries.append({'family':key[0],'n':key[1],'hypotheses':nr,'taxonomies':nt,'metrics_sha256':digest(dest/'metrics_global_bh.csv.gz')})
 with (out/'tier_summary.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['experiment','benchmark_role','mechanism','highest_tier','candidate_scenario_contrasts'])
  for row,n in sorted(overall.items()):w.writerow([*row,n])
 (out/'global_manifest.json').write_text(json.dumps({'protocol':'T3_B3_STRESS_V2_FROZEN_INDIVIDUAL',
  'experiment':meta[0]['experiment'],'n_global_BH':N,'alpha':.05,
  'calibration_seed_range':[20,24],'evaluation_seed_range':[25,29] if meta[0]['experiment']=='original' else [50,59],
  'discovery_training_seeds':list(range(10)),'training_seed_averaging':False,
  'cross_family_scope':'retained','adapted_training_seeds':[60,69] if meta[0]['experiment']!='original' else [],
  'new_inference_not_combined_with_original':True,'blocks':entries},indent=2)+'\n')
 print('T3_STRESS_V2_GLOBAL_BH_PASS',meta[0]['experiment'],N,flush=True)

def selftest():
 assert len(CLASSICS)==26
 assert len(FAMILIES)==6 and len(ENGINES)==4
 assert abs(ci_p([-1]*5)[3]-.03125)<1e-15
 assert len(PAIRED_COLUMNS)==17
 assert len(METRIC_COLUMNS)==22
 print('T3_STRESS_V2_UNIT_PASS',flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='operation',required=True)
 for operation in ('original','new'):
  sp=sub.add_parser(operation)
  sp.add_argument('--input',required=True);sp.add_argument('--registry',required=True)
  sp.add_argument('--family',required=True,choices=FAMILIES);sp.add_argument('--n',required=True,type=int,choices=SIZES)
  sp.add_argument('--output',required=True)
  if operation=='new':
   sp.add_argument('--benchmark',required=True);sp.add_argument('--adapted-registry')
 sp=sub.add_parser('finalize');sp.add_argument('--input',required=True);sp.add_argument('--output',required=True)
 sub.add_parser('selftest')
 a=ap.parse_args()
 {'original':read_original,'new':read_new,'finalize':finalize,'selftest':lambda a:selftest()}[a.operation](a)
