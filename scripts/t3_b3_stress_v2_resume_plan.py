#!/usr/bin/env python3
"""Plan safe T3/B3 Stress V2 resume from immutable successful old shards.
Cancel superseded workflows ONLY after the complete artifact inventory is recorded.
The resulting matrix contains only successful-artifact gaps, never completed cells.
"""
import argparse,json,os,re,subprocess,time,sys
from pathlib import Path

FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
SIZES=(200,1000,3000)
TRAINING=tuple((f,n,s) for f in FAMILIES for n in SIZES for s in range(60,70))
SOURCE_RUN=42068731220
SUPERSEDED_RESCUE_RUN=42069857481
PAT=re.compile(r"^stress-v2-adapt-(normal|lognormal|weibull|invgauss|exgaussian|exwald)-s(6\d)-n(200|1000|3000)-run42068731220$")

def gh(endpoint,method=None):
    cmd=["gh","api",endpoint]
    if method:cmd+=["--method",method]
    try:
        return json.loads(subprocess.check_output(cmd,text=True,stderr=subprocess.PIPE) or "{}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"GitHub {method or 'GET'} {endpoint}: {e.stderr.strip()}") from e

def run_status(repo,runid):
    return gh(f"repos/{repo}/actions/runs/{runid}")

def artifacts(repo,runid):
    items=[];page=1
    while True:
        o=gh(f"repos/{repo}/actions/runs/{runid}/artifacts?per_page=100&page={page}")
        batch=o.get("artifacts",[])
        items.extend(batch)
        if len(batch)<100:break
        page+=1
        if page>20:raise RuntimeError("Artifact pagination unexpectedly large")
    return items

def successful_models(repo):
    available={}
    unexpected=[]
    for a in artifacts(repo,SOURCE_RUN):
        name=a["name"]
        if not name.startswith("stress-v2-adapt-"):continue
        m=PAT.fullmatch(name)
        if not m:unexpected.append(name);continue
        key=(m[1],int(m[3]),int(m[2]))
        if key in available:raise ValueError(f"Duplicate source adapted training cell: {key}")
        if a.get("expired"):raise ValueError(f"Expired successful trained model artifact: {name}")
        if int(a.get("size_in_bytes",0))<1000:raise ValueError(f"Empty adapted model artifact: {name}")
        available[key]={"artifact_name":name,"artifact_id":a["id"],"size_bytes":a["size_in_bytes"],"sha256_digest":a.get("digest")}
    if unexpected:raise ValueError("Unexpected existing adapted training names: "+repr(unexpected[:10]))
    if not available:raise ValueError("No successful Rediscovery artifacts; refuse to cancel")
    return available

def safe_cancel(repo,runid):
    initial=run_status(repo,runid)
    if initial["status"]=="completed":
        print("ALREADY_TERMINAL",runid,initial["conclusion"],flush=True)
        return
    print("REQUEST_CANCEL",runid,"status",initial["status"],flush=True)
    # Actions-write permission must be granted. Never ignore an authorization failure.
    gh(f"repos/{repo}/actions/runs/{runid}/cancel","POST")
    for _ in range(70):
        r=run_status(repo,runid)
        if r["status"]=="completed":
            print("CANCEL_TERMINAL",runid,r["conclusion"],flush=True)
            return
        time.sleep(3)
    raise RuntimeError(f"Timed out waiting for run {runid} cancellation; STOP instead of risking duplicate model cells")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    parser.add_argument("--github-output",required=True)
    parser.add_argument("--cancel",action="store_true")
    a=parser.parse_args()
    repo=os.environ["GITHUB_REPOSITORY"]
    initial=successful_models(repo)
    print("PRE_CANCEL_SAVED_ADAPTED_MODELS",len(initial),flush=True)
    if a.cancel:
        # Cancel the queued rescue FIRST, to avoid 180 confirmation jobs starting
        # while the original Rediscovery run is being canceled.
        safe_cancel(repo,SUPERSEDED_RESCUE_RUN)
        safe_cancel(repo,SOURCE_RUN)
    final=successful_models(repo)
    if not set(initial).issubset(final):raise ValueError("Successful adapted artifacts disappeared after cancellation")
    remaining=sorted(set(TRAINING)-set(final))
    if set(TRAINING)!=set(final)|set(remaining):raise ValueError("Training coverage incomplete")
    if set(final)&set(remaining):raise ValueError("Recompute collision with successfully completed Rediscovery")
    if not remaining:raise ValueError("All 180 adapted training cells completed: do not start an empty matrix")
    record={"protocol":"T3_B3_STRESS_V2_INDIVIDUAL_RESUME_20261105",
            "old_rediscovery_run":SOURCE_RUN,
            "superseded_confirmation_rescue_run":SUPERSEDED_RESCUE_RUN,
            "new_run_sha":os.environ.get("GITHUB_SHA"),
            "old_success_count":len(final),"retry_count":len(remaining),
            "old_successful_artifacts":[{"family":f,"n":n,"seed":s,**d} for (f,n,s),d in sorted(final.items())],
            "remaining_jobs":[{"family":f,"n":n,"seed":s} for f,n,s in remaining],
            "frozen_training_role":"near_40_plus_original_support_241_never_far_40",
            "frozen_confirmation_role":"new_independent_seeds_50_to_59",
            "source_frozen_discovery_run":41487091262,
            "source_original_stress_recovery_run":42062234485,
            "invariant":"Never average individual W across training seeds"}
    target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(record,indent=2)+"\n")
    with open(a.github_output,"a") as f:
        print("matrix="+json.dumps({"include":record["remaining_jobs"]},separators=(",",":")),file=f)
        print("reused_models="+str(len(final)),file=f)
        print("rerun_models="+str(len(remaining)),file=f)
    print("STRESS_V2_RESUME_PLAN_PASS",len(final),"preserved",len(remaining),"scheduled at max-parallel 22",flush=True)

if __name__=="__main__":main()
