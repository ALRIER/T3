#!/usr/bin/env python3
"""T3 B3 Real-World V2: immutable RAW individual-W score recovery.

One input is one historical score shard; the primary statistical unit is the
parent dataset. These files are *intermediate paired descriptive effects*:
no child, depth, bootstrap draw or repeated seed is an independent parent.
"""
import argparse,csv,gzip,hashlib,collections,json,math,re
from pathlib import Path

FAMILIES={'normal','lognormal','weibull','invgauss','exgaussian','exwald'}
CLASSICS=('mean','median','trimmed20','trimmed10','winsorized_0.15','mode_hsm',
'mode_parzen','trimean','huber','biweight','winsorized_0.05','winsorized_0.1',
'winsorized_0.2','mom_k5','mom_k10','mom_k20','catoni_a0.05','catoni_a0.1',
'catoni_a0.2','catoni_a0.35','catoni_a0.5','huber_k0.75','huber_k1',
'huber_k1.345','huber_k1.75','huber_k2')
MODEL_RE=re.compile(r'^(normal|lognormal|weibull|invgauss|exgaussian|exwald)_(ga|nsga2|de|dirichlet)_train(0[0-9])$')
FIELDS=('source_family','candidate_id','engine','training_seed','sample_n',
 'realworld_seed','parent_dataset_id','transfer_scope','evaluation_family',
 'benchmark_role','benchmark','mse_difference','q95_difference',
 'mse_gain_pct','q95_gain_pct','n_children','n_depths','candidate_discovery_sha256')
NEIGHBOR_FIELDS=FIELDS+('matched_scenario_id','depth', 'dataset_id')
EPS=2.220446049250313e-16

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()

def die(s):raise RuntimeError(s)

def read_benchmark(p):
 rows=list(csv.DictReader(open(p,newline='')))
 out={}
 for r in rows:
  key=(r['evaluation_family'],int(r['scenario_id']),int(r['sample_n']))
  if key in out:die('Duplicated pre-frozen benchmark cell: '+str(key))
  if r['own_benchmark'] not in CLASSICS or r['own_benchmark']=='mean':
   die('Nonclassic or mean own comparator')
  out[key]=r['own_benchmark']
 if len(out)!=6*241*3:die('Incomplete Discovery-frozen 241-support-scenario benchmark map')
 return out

def read_family_map(p):
 rows=list(csv.DictReader(open(p,newline='')))
 m={}
 for r in rows:
  d=r['dataset_id']
  if d in m:die('Duplicated outcome-blind family assignment')
  if r['empirical_family_assignment'] not in FAMILIES:die('Invalid empirical destination class')
  m[d]=r
 if len(m)!=743:die('Expected 743 frozen empirical child profiles')
 return m

def read_input(path,family_map,bench):
 path=Path(path);mp=path.parent/'score_manifest.csv'
 if not mp.exists():die('Missing original immutable manifest '+str(path))
 man=list(csv.DictReader(mp.open(newline='')))
 if len(man)!=1 or man[0]['score_sha256'].lower()!=sha(path):die('Original score SHA differs from manifest')
 manifest=man[0]
 source_family=manifest['family'];n=int(manifest['sample_n']);eval_seed=int(manifest['realworld_seed'])
 if source_family not in FAMILIES or n not in (200,1000,3000) or eval_seed not in range(30,40):
  die('Invalid real-world evaluation source/seed/n')
 # A profile key is a child-depth within one independent bootstrap-seed shard.
 # The 26 classical score rows are redundantly emitted for all ten training seeds.
 refs={};learned={};identity={};seen_train=collections.defaultdict(set)
 count=0
 with path.open(newline='') as f:
  rd=csv.DictReader(f)
  req={'model','dataset_id','parent_dataset_id','depth','transfer_scope','matched_scenario_id',
    'training_seed','mse','q95','discovery_sha256','realworld_seed','sample_n'}
  if not req.issubset(rd.fieldnames):die('Missing original Real-World scoring columns')
  for r in rd:
   count+=1
   if int(r['realworld_seed'])!=eval_seed or int(r['sample_n'])!=n or r['family']!=source_family:die('Evaluation-shard seed/family/n collision')
   pid=r['parent_dataset_id'];did=r['dataset_id'];depth=r['depth'];tr=int(r['training_seed'])
   if tr not in range(10):die('Training seed outside frozen Discovery 0:9')
   mapping=family_map.get(did)
   if not mapping or mapping['parent_dataset_id']!=pid:die('Child not in outcome-blind frozen family map')
   dst=mapping['empirical_family_assignment'];sid=int(r['matched_scenario_id'])
   role=r['transfer_scope']
   if role not in ('within_regime','within_family_neighborhood','cross_family_transfer'):
    die('Unknown frozen transfer scope')
   expected=bench.get((source_family,sid,n))
   if not expected:die('Missing frozen own benchmark')
   key=(pid,did,depth,role,dst,sid)
   z=(float(r['mse']),float(r['q95']))
   if not all(math.isfinite(x) for x in z):die('Nonfinite raw score')
   model=r['model']
   if model in CLASSICS:
    if model in ('mean',expected):
     refkey=(key,model)
     if refkey in refs and refs[refkey]!=z:
      die('Classical benchmark changed between training seeds (raw score corruption)')
     refs[refkey]=z
   else:
    mm=MODEL_RE.fullmatch(model)
    if not mm or mm[1]!=source_family or int(mm[3])!=tr:
     die('Original evolutionary seed/model identity mismatch: '+model)
    cid=f'{source_family}|{mm[2]}|seed{tr:02d}|n{n}'
    learnkey=(key,cid)
    if learnkey in learned:die('Duplicate individual W score for child-depth')
    learned[learnkey]=z
    discovery=r['discovery_sha256']
    if len(discovery)!=64:die('Missing frozen individual Discovery RDS SHA')
    if cid in identity and identity[cid]!=discovery:die('Frozen W provenance inconsistent across children')
    identity[cid]=discovery
    seen_train[key].add(cid)
 if len(identity)!=40:die('Missing one of 40 distinct W per source family/n')
 if any(len(v)!=40 for v in seen_train.values()):die('Incomplete 10x4 candidate per child-depth')
 if any((key,'mean') not in refs or (key,bench[(source_family,key[5],n)]) not in refs for key in seen_train):
  die('Missing own / mean paired references')
 if len(learned)!=len(seen_train)*40:die('Unexpected raw score coverage')
 print('REALWORLD_V2_RAW_CONTRACT_PASS',source_family,eval_seed,n,
       'rows',count,'child-depths',len(seen_train),'individual_W',len(identity),flush=True)
 return (manifest,source_family,n,eval_seed,refs,learned,identity)

def reduce(a):
 map_=read_family_map(a.family_map);bench=read_benchmark(a.benchmark)
 path=Path(a.input);man,family,n,ev,refs,learned,identity=read_input(path,map_,bench)
 output=Path(a.output)
 if output.exists():die('Refusing to overwrite existing Real-World V2 reduction')
 output.parent.mkdir(parents=True,exist_ok=True)
 # First average depth within *each child* to avoid reweighting a child that has
 # an additional upper-tail slice. Then average children within their parent.
 children=collections.defaultdict(lambda:[0.,0.,0.,0.,0,set()])
 neighbors=[]
 for (key,cid),val in learned.items():
  pid,did,depth,scope,dst,sid=key
  for role,ref in (('own',bench[(family,sid,n)]),('mean','mean')):
   baseline=refs[(key,ref)]
   mse=val[0]-baseline[0];q95=val[1]-baseline[1]
   gm=100*(baseline[0]-val[0])/max(abs(baseline[0]),EPS)
   gq=100*(baseline[1]-val[1])/max(abs(baseline[1]),EPS)
   group=(pid,did,scope,dst,cid,role)
   z=children[group];z[0]+=mse;z[1]+=q95;z[2]+=gm;z[3]+=gq;z[4]+=1;z[5].add(depth)
   engine=cid.split('|')[1]
   # Destination scenario + depth remain descriptive, never claim independent tests.
   neighbors.append((family,cid,engine,int(cid.split('seed')[1][:2]),n,ev,pid,scope,dst,
      role,ref,mse,q95,gm,gq,1,1,identity[cid],sid,depth,did))
 parent=collections.defaultdict(lambda:[0.,0.,0.,0.,0,0])
 for (pid,did,scope,dst,cid,role),z in children.items():
  if not z[4]:die('Empty child effect')
  k=(pid,scope,dst,cid,role)
  q=parent[k]
  for i in range(4):q[i]+=z[i]/z[4]
  q[4]+=1;q[5]+=z[4]
 with gzip.open(output,'wt',newline='') as out:
  w=csv.writer(out);w.writerow(FIELDS)
  for (pid,scope,dst,cid,role),z in sorted(parent.items()):
   engine=cid.split('|')[1];train=int(cid.split('seed')[1][:2])
   ref='mean' if role=='mean' else 'frozen_discovery_scenario_specific'
   w.writerow([family,cid,engine,train,n,ev,pid,scope,dst,role,ref,
     *(z[i]/z[4] for i in range(4)),int(z[4]),int(z[5]),identity[cid]])
 if a.neighbor_output:
  neighbor=Path(a.neighbor_output)
  if neighbor.exists():die('Refusing overwrite neighbor effects')
  neighbor.parent.mkdir(parents=True,exist_ok=True)
  with gzip.open(neighbor,'wt',newline='') as f:
   w=csv.writer(f);w.writerow(NEIGHBOR_FIELDS);w.writerows(neighbors)
 meta={'protocol':'T3_B3_RW_V2_40_W_PER_SOURCE_FAMILY_N',
  'raw_score_sha256':sha(path),'source_score_manifest_sha256':sha(path.parent/'score_manifest.csv'),
  'frozen_family_map_sha256':sha(a.family_map),'frozen_benchmark_map_sha256':sha(a.benchmark),
  'source_family':family,'sample_n':n,'realworld_seed':ev,
  'distinct_candidate_weights':len(identity),'primary_effect_rows':len(parent),
  'primary_reduced_sha256':sha(output),
  'neighbor_descriptive_only':True,'parent_dataset_id_is_only_independent_unit':True,
  'target_caveat':'full_sample_child_depth_mean_proxy_not_known_population_truth'}
 output.with_suffix('.manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
 print('REALWORLD_V2_INDIVIDUAL_PARENT_REDUCER_PASS',family,ev,n,len(parent),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--input',required=True)
 p.add_argument('--family-map',required=True)
 p.add_argument('--benchmark',required=True)
 p.add_argument('--output',required=True)
 p.add_argument('--neighbor-output')
 a=p.parse_args()
 reduce(a)
