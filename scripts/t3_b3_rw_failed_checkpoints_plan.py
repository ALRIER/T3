#!/usr/bin/env python3
"""Freeze missing checkpoints from original completed Real World artifact inventory.

Avoid Actions job.name: GitHub truncates long matrix labels with ellipses.
Only exact immutable scoring-artifact presence determines missing coverage.
"""
import collections,json,os,re,subprocess,time
ORIGINAL=42390283887
SHA="5799cd212e1df312abdbe022900b507c6466e601"
FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
GROUPS=((30,31),(32,33),(34,35),(36,37),(38,39))
SUFFIX="-run"+str(ORIGINAL)
REGEX=re.compile(r"t3-rw-pub-validated-(normal|lognormal|weibull|invgauss|exgaussian|exwald)-(b[0-9]{2})-n(200|1000|3000)-g([0-4])-run42390283887")
def api(repo,route):
 for i in range(9):
  z=subprocess.run(["gh","api",f"repos/{repo}/{route}"],capture_output=True,text=True,timeout=150)
  if z.returncode==0:
   return json.loads(z.stdout)
  if not any(x in (z.stderr or "").lower() for x in ("rate limit","http 50","timeout","connection reset","connection refused")):
   raise RuntimeError("GitHub API hard failure: "+(z.stderr or "")[:1200])
  pause=min(25*(i+1),120)
  print("RETRY_GITHUB_ARTIFACT_INVENTORY_API",route,pause,flush=True)
  time.sleep(pause)
 raise RuntimeError("GitHub API unavailable after retries: "+route)
def main():
 repo=os.environ["GITHUB_REPOSITORY"]
 run=api(repo,f"actions/runs/{ORIGINAL}")
 if run["head_sha"]!=SHA or run["status"]!="completed":
  raise RuntimeError("Original source run not complete or is different SHA; leave active runs alone")
 listed=[];total=None
 for page in range(1,18):
  r=api(repo,f"actions/runs/{ORIGINAL}/artifacts?per_page=100&page={page}")
  if total is None:total=r["total_count"]
  listed.extend(r["artifacts"])
  if len(r["artifacts"])<100:break
 if len(listed)!=total:raise RuntimeError(f"Incomplete immutable artifact inventory: {len(listed)} / {total}")
 existing=set()
 for art in listed:
  m=REGEX.fullmatch(art["name"])
  if m:
   if art["expired"] or art["size_in_bytes"]<=0:
    raise RuntimeError("Expired/empty original successful scoring artifact "+art["name"])
   family,block,n,g=m.groups();key=(family,block,int(n),int(g))
   if key in existing:raise RuntimeError("Duplicate completed checkpoint "+art["name"])
   existing.add(key)
 expected={(family,f"b{block:02d}",n,g)
  for family in FAMILIES for block in range(1,15) for n in (200,1000,3000) for g in range(5)}
 if not existing<=expected:raise RuntimeError("Unexpected checkpoint ID in source run")
 missing=sorted(expected-existing)
 if not missing:
  raise RuntimeError("No missing checkpoint artifacts: original 1260 complete; do not rerun scoring")
 if len(missing)>100:
  raise RuntimeError("Unexpected broad recovery scope; review before launching "+str(len(missing)))
 rows=[]
 for family,block,n,g in missing:
  lo,hi=GROUPS[g]
  rows.append(dict(family=family,block=block,n=n,seed_group=g,seeds=f"{lo},{hi}",
   artifact=f"t3-b3-realworld-parentblock-{family}-{block}-run41514871500",
   original_expected_artifact=f"t3-rw-pub-validated-{family}-{block}-n{n}-g{g}{SUFFIX}"))
 os.makedirs("artifacts/realworld_recovery",exist_ok=True)
 ledger=dict(original_run=ORIGINAL,original_sha=SHA,source_run_conclusion=run["conclusion"],
  expected_scoring_checkpoints=len(expected),preserved_scoring_checkpoints=len(existing),
  missing_scoring_checkpoints=len(rows),non_scoring_artifacts=total-len(existing),
  all_original_successful_artifacts_immutable=True,missing=rows)
 with open("artifacts/realworld_recovery/failed_original_job_ledger.json","w") as f:
  json.dump(ledger,f,indent=2)
 with open(os.environ["GITHUB_OUTPUT"],"a") as f:
  print("matrix="+json.dumps({"include":rows},separators=(",",":")),file=f)
  print("missing="+str(len(rows)),file=f)
  print("families="+",".join(sorted({z["family"] for z in rows})),file=f)
 print("REALWORLD_COMPLETED_ORIGINAL_ARTIFACT_RECONCILIATION_PASS",
       "preserved",len(existing),"missing",len(rows),"other_artifacts",total-len(existing),flush=True)
 for r in rows:print("RETRY_EXACT_MISSING_CHECKPOINT",r["original_expected_artifact"],flush=True)
if __name__=="__main__":main()
