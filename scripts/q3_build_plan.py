#!/usr/bin/env python3
"""Q3 single-dispatch parameter-transfer plan with recoverable original shards.

No optimizer is fitted here. The original T3 frozen-weight scorer, originally
authored for 830 full scenario shards per sample size, is reused unchanged.
"""
from __future__ import annotations
import argparse,csv,json,os,re,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FAMILIES={"normal":8,"lognormal":6,"weibull":12,"invgauss":9,"exgaussian":27,"exwald":27}
SIZES=(200,1000,3000)
SOURCE_RUN_WORKFLOW="T3 B3 Frozen Parametric Transfer"
PATTERN=re.compile(r"^t3-b3-parametric-score-(normal|lognormal|weibull|invgauss|exgaussian|exwald)-p(\d+)-s(\d+)-n(\d+)-run(\d+)-a(\d+)$")

def run_gh(endpoint:str)->dict:
    result=subprocess.run(["gh","api",endpoint],text=True,capture_output=True)
    if result.returncode: raise RuntimeError("GitHub API failed "+endpoint+": "+result.stderr[:600])
    return json.loads(result.stdout)

def all_shards():
    return [(fam,row,seed,n)
            for fam,last in FAMILIES.items()
            for row in range(2,last+1)
            for seed in range(40,50)
            for n in SIZES]

def validate_frozen_scenarios():
    path=ROOT/"config/T2_V3_B3_prospective_321_grid.csv"
    with path.open(newline="",encoding="utf-8-sig") as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==321
    ids=[int(x["scenario_id"]) for x in rows
         if x["mechanism"] not in ("mixture_bimodal_near","mixture_bimodal_far")]
    if len(ids)!=241 or len(set(ids))!=241:
        raise RuntimeError("Original 241-scenario Discovery support has changed")
    return ",".join(map(str,ids))

def sources(run_csv):
    run_ids=[int(x.strip()) for x in run_csv.split(",") if x.strip()]
    if len(set(run_ids))!=len(run_ids):
        raise RuntimeError("Duplicate artifact recovery runs")
    recovered={}
    catalog=[]
    for run_id in run_ids:
        meta=run_gh(f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{run_id}")
        if meta.get("name")!=SOURCE_RUN_WORKFLOW or meta.get("repository",{}).get("full_name")!=os.environ["GITHUB_REPOSITORY"]:
            raise RuntimeError("Refusing to trust a non-original parametric-transfer workflow: "+str(run_id))
        page=1;matched=0
        while True:
            response=run_gh(f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{run_id}/artifacts?per_page=100&page={page}")
            entries=response.get("artifacts",[])
            for a in entries:
                if a.get("expired"):continue
                m=PATTERN.fullmatch(a.get("name",""))
                if not m or int(m.group(5))!=run_id:continue
                identity=(m.group(1),int(m.group(2)),int(m.group(3)),int(m.group(4)))
                if identity not in set(all_shards()):continue
                # Reused sharded ZIP must still pass per-shard content SHA and identity
                # audit after its actual bytes are downloaded by each runner.
                candidate={"name":a["name"],"run_id":run_id,"attempt":int(m.group(6)),
                           "artifact_id":a["id"]}
                old=recovered.get(identity)
                if old is None or candidate["attempt"]>old["attempt"]:
                    recovered[identity]=candidate
                matched+=1
            if len(entries)<100:break
            page+=1
            if page>150: raise RuntimeError("Unreasonably large artifact inventory; stop rather than silently drop pages")
        catalog.append({"run_id":run_id,"nonexpired_score_artifact_matches":matched})
    return recovered,catalog

def plan(reused,n):
    expected=[i for i in all_shards() if i[3]==n]
    if len(expected)!=830:raise RuntimeError("Expected exactly 830 full transfer shards for each sample size")
    groups=[]
    for ix in range(0,len(expected),4):
        group={"group_index":ix//4}
        for slot in range(4):
            if ix+slot<len(expected):
                fam,row,seed,size=expected[ix+slot]
                reuse=reused.get((fam,row,seed,size),{})
            else:
                fam,row,seed,size="",0,0,n
                reuse={}
            group.update({f"shard{slot}_family":fam,
                          f"shard{slot}_parameter_row":row,
                          f"shard{slot}_seed":seed,
                          f"shard{slot}_n":size,
                          f"shard{slot}_reuse_run":str(reuse.get("run_id","")),
                          f"shard{slot}_reuse_name":reuse.get("name","")})
        groups.append(group)
    if len(groups)!=208 or len({tuple((v[f"shard{i}_family"],v[f"shard{i}_parameter_row"],v[f"shard{i}_seed"],v[f"shard{i}_n"]) for i in range(4)) for v in groups})!=208:
        raise RuntimeError("Incorrect finite GitHub Actions matrix plan")
    return {"include":groups}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reuse-runs",default="")
    p.add_argument("--output",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    assert len(all_shards())==2490
    for n in SIZES:assert len(plan({},n)["include"])==208
    ids=validate_frozen_scenarios()
    if a.self_test:
        print("Q3_PLAN_SELFTEST_PASS 2490 complete 241-scenario shards; 208 jobs per size, four sequential shards each")
        return
    rec,run_catalog=sources(a.reuse_runs)
    out={"schema":"T3_Q3_RECOVERY_PLAN_V1",
         "stage":"A_G_SINGLE_WORKFLOW",
         "reused_score_shards_from_explicit_prior_runs":len(rec),
         "original_shard_identities":2490,
         "missing_shard_identities":2490-len(rec),
         "original_evaluation_seeds":"40:49",
         "scenario_ids":ids,
         "original_241_scenario_support_count":241,
         "original_500_replicates_per_scenario":True,
         "source_runs":run_catalog,
         "matrices":{str(n):plan(rec,n) for n in SIZES}}
    if not a.output: print(json.dumps(out,separators=(",",":")))
    else:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(f"Q3_RECOVERY_PLAN_PASS reused={len(rec)} missing={2490-len(rec)}")

if __name__=="__main__":main()
