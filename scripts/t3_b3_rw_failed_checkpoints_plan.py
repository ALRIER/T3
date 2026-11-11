#!/usr/bin/env python3
"""Identify exactly failed Real World source-block/seed-pair checkpoints without touching live jobs."""
import json,os,re,subprocess,time,collections
ORIGINAL=42390283887
pattern=re.compile(r'^frozen-score-seeds-(30-31|32-33|34-35|36-37|38-39) \((normal|lognormal|weibull|invgauss|exgaussian|exwald), (b[0-9]{2}), (t3-b3-realworld-parentblock-[a-z]+-b[0-9]{2}-run41514871500), (200|1000|3000)\)$')
groups={'30-31':0,'32-33':1,'34-35':2,'36-37':3,'38-39':4}
def api(path):
 for attempt in range(8):
  p=subprocess.run(['gh','api',path],text=True,capture_output=True)
  if p.returncode==0:return json.loads(p.stdout)
  if not any(t in p.stderr.lower() for t in ('rate limit','http 502','http 503','timeout')):raise RuntimeError(p.stderr[:900])
  time.sleep(min(20*(attempt+1),90))
 raise RuntimeError('Persistent GitHub API installation quota: '+path)
def main():
 repo=os.environ['GITHUB_REPOSITORY']
 original=api(f'repos/{repo}/actions/runs/{ORIGINAL}')
 if original['head_sha']!='5799cd212e1df312abdbe022900b507c6466e601':
  raise RuntimeError('Original Real World frozen scoring commit differs')
 jobs=[];page=1
 while True:
  body=api(f'repos/{repo}/actions/runs/{ORIGINAL}/jobs?per_page=100&page={page}')
  jobs.extend(body['jobs'])
  if len(body['jobs'])<100:break
  page+=1
 if len(jobs)<1262:raise RuntimeError('Original Actions job list incomplete; preserve current run')
 failed=[j for j in jobs if j.get('conclusion')=='failure']
 missing=[];seen=set()
 for j in failed:
  m=pattern.fullmatch(j['name'])
  if not m:raise RuntimeError('Non-scoring job failure requires separate inspection: '+j['name'])
  grp,family,block,artifact,n=m.groups()
  key=(grp,family,block,int(n))
  if key in seen:raise RuntimeError('Duplicate failed checkpoint')
  seen.add(key)
  low,high=map(int,grp.split('-'))
  missing.append(dict(seed_group=groups[grp],seeds=f'{low},{high}',family=family,block=block,
    artifact=artifact,n=int(n),original_job_id=j['id']))
 if not missing:raise RuntimeError('No failed checkpoint jobs found; do not launch redundant scoring')
 if len(missing)>100:raise RuntimeError('Unusually many failed jobs; require manual audit: '+str(len(missing)))
 os.makedirs('artifacts/realworld_recovery',exist_ok=True)
 with open('artifacts/realworld_recovery/failed_original_job_ledger.json','w') as f:
  json.dump(dict(original_run=ORIGINAL,failed_count=len(missing),failed=missing,
   live_jobs=[dict(id=j['id'],name=j['name']) for j in jobs if j['status']=='in_progress'],
   keep_successful_artifacts_immutable=True),f,indent=2)
 with open(os.environ['GITHUB_OUTPUT'],'a') as f:
  print('matrix='+json.dumps({'include':missing},separators=(',',':')),file=f)
  print('missing='+str(len(missing)),file=f)
  print('families='+','.join(sorted({z['family'] for z in missing})),file=f)
 print('REALWORLD_FAILED_CHECKPOINTS_ISOLATED',len(missing),
       'original_running',sum(j['status']=='in_progress' for j in jobs),flush=True)
if __name__=='__main__':main()
