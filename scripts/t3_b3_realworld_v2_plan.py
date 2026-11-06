#!/usr/bin/env python3
"""T3 B3 Real-World V2 immutable 856-shard scoring inventory and 4-shard job plan.
No Download or score rerun at this stage; freeze original source run and artifact.
"""
import argparse,json,os,re,subprocess,collections,hashlib
from pathlib import Path

RUNS=(41208956012,41516493389,41516493415,41516493453,41516494076,41688526789)
FAMILIES=('normal','lognormal','weibull','invgauss','exgaussian','exwald')
PAT=re.compile(r'^t3-b3-realworld-(repair-)?(normal|lognormal|weibull|invgauss|exgaussian|exwald)-s(3[0-9])-n(200|1000|3000)(?:-(b[0-9]{2}))?-run([0-9]+)$')

def api(repo,id,page):
 return json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/actions/runs/{id}/artifacts?per_page=100&page={page}'],text=True))

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--output',required=True)
 p.add_argument('--github-output',required=True)
 a=p.parse_args()
 repo=os.environ['GITHUB_REPOSITORY']
 found=[];keys=set();runs={}
 for rid in RUNS:
  seen=0
  for page in range(1,20):
   body=api(repo,rid,page);batch=body['artifacts']
   for artifact in batch:
    m=PAT.fullmatch(artifact['name'])
    if not m:continue
    rep,fam,seed,n,block,run=m.groups()
    if int(run)!=rid:raise ValueError('Artifact run name does not agree with origin')
    if artifact.get('expired'):raise ValueError('Original source score artifact expired: '+artifact['name'])
    key=(fam,int(seed),int(n),block or '')
    if key in keys:raise ValueError('Overlapping original / repaired family-seed-n-block identity')
    if bool(rep)!=(block is not None):raise ValueError('Repair identity/block tag mismatch')
    if not rep and block is not None or rep and int(n)!=3000:raise ValueError('Source scoring identity invalid')
    keys.add(key);seen+=1
    found.append({'family':fam,'seed':int(seed),'n':int(n),'block_id':block or '',
      'run_id':rid,'artifact_name':artifact['name'],'artifact_id':artifact['id'],
      'artifact_size':artifact['size_in_bytes'],'created_at':artifact['created_at']})
   if len(batch)<100:break
  runs[rid]=seen
 if len(found)!=856 or runs[RUNS[0]]!=128 or sum(runs[rid] for rid in RUNS[1:])!=728:
  raise ValueError('Original Real-World complete source coverage violated: '+str((len(found),runs)))
 for family in FAMILIES:
  for seed in range(30,40):
   for n in (200,1000):
    if (family,seed,n,'') not in keys:raise ValueError('Missing full original Real-World source sample')
   if (family,seed,3000,'') not in keys:
    needed={(family,seed,3000,f'b{i:02d}') for i in range(1,15)}
    if not needed.issubset(keys):raise ValueError(f'Missing parent-intact n3000 repair blocks {family} seed {seed}')
   else:
    if any((family,seed,3000,f'b{i:02d}') in keys for i in range(1,15)):
     raise ValueError('Duplicated n3000 original full shard and repaired block')
 groups=[]
 for family in FAMILIES:
  source=sorted((z for z in found if z['family']==family),
     key=lambda z:(z['seed'],z['n'],z['block_id'],z['run_id']))
  for i in range(0,len(source),4):
   groups.append({'family':family,'block':i//4,
                  'sources':source[i:i+4]})
 if len(groups)>256:raise ValueError('GitHub Actions dynamic matrix limit exceeded')
 plan={'protocol':'T3_B3_REALWORLD_RAW_856_INDIVIDUAL_W_V2',
  'original_source_runs':list(RUNS),'per_run_counts':runs,
  'source_shards':len(found),'all_artifacts':found,
  'reduction_jobs':len(groups),'max_shards_per_reduction_job':4,
  'training_seeds':list(range(10)),'evaluation_seeds':list(range(30,40)),
  'source_candidate_identity':'source_family|engine|training_seed|n',
  'source_parent_clusters':642,
  'frozen_parent_plan_run':41514871500,
  'frozen_classic_benchmark_run':41478038812,
  'no_new_scoring_or_model_training':True}
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(plan,indent=2)+'\n')
 with open(a.github_output,'a') as f:
  print('matrix='+json.dumps({'include':groups},separators=(',',':')),file=f)
  print('n_jobs='+str(len(groups)),file=f)
 print('REALWORLD_V2_ORIGINAL_856_SHARD_PLAN_PASS',len(groups),'jobs, 856 original immutable scoring artifacts',flush=True)

if __name__=='__main__':main()
