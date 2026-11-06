#!/usr/bin/env python3
"""Retry GitHub Actions artifact downloads through transient installation API limits.
No scientific data changes, no artifact substitutions, and never silent skip.
"""
import argparse,hashlib,subprocess,sys,time

def download(run,repo,dest,name=None,pattern=None,max_attempts=16):
 if bool(name)==bool(pattern):raise ValueError('Specify exactly one of name or pattern')
 cmd=['gh','run','download',str(run),'--repo',repo]
 cmd+=['--name',name] if name else ['--pattern',pattern]
 cmd+=['--dir',str(dest)]
 target=name or pattern
 # Requests for a particular immutable name/pattern always use original run.
 for attempt in range(1,max_attempts+1):
  result=subprocess.run(cmd,capture_output=True,text=True,timeout=420)
  if result.returncode==0:
   print('RW_ARTIFACT_DOWNLOAD_COMPLETE',run,target,'attempt',attempt,flush=True)
   return
  msg=(result.stderr or '')+' '+(result.stdout or '')
  transient=any(t.lower() in msg.lower() for t in (
   'API rate limit exceeded','secondary rate limit','403: API rate limit',
   'egress is over the account limit','http 429','http 502','http 503','http 504',
   'rate limit exceeded for installation','502 Bad Gateway','503 Service Unavailable'))
  if not transient:
   raise RuntimeError('Nonretryable artifact acquisition failure for '+str(target)+': '+msg[:1300])
  if attempt==max_attempts:
   raise RuntimeError('GitHub API/egress quota remains blocked after '+str(max_attempts)+' attempts for '+str(target)+'. Previously finished checkpoints are preserved. '+msg[:900])
  entropy=int.from_bytes(hashlib.sha256((str(run)+str(target)).encode()).digest()[:2],'big')%22
  pause=min(45*attempt,360)+entropy
  print('RW_GITHUB_INSTALLATION_API_RATE_LIMIT_BACKOFF',run,target,'attempt',attempt,'sleep',pause,flush=True)
  time.sleep(pause)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--repo',required=True)
 p.add_argument('--dir',required=True);p.add_argument('--name');p.add_argument('--pattern')
 x=p.parse_args();download(x.run,x.repo,x.dir,x.name,x.pattern)
