#!/usr/bin/env python3
"""Scientifically prespecified Q3-D compact parameter-transfer plan.

Prespecification is outcome-blind: for each family use the first, midpoint,
and final non-base parameter grid row; evaluate the original clean scenario
and 8 maximin-farthest scenarios from each of the six original contamination
mechanisms, holding 10 independent evaluation seeds and 500 replicates.
Archive recovery is based only on SHA-verified source score checkpoints.
"""
from __future__ import annotations
import argparse,csv,json,os,re,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LAST={"normal":8,"lognormal":6,"weibull":12,"invgauss":9,"exgaussian":27,"exwald":27}
FAMS=tuple(LAST)
SIZES=(200,1000,3000)
OLD=re.compile(r"^t3-b3-parametric-score-(normal|lognormal|weibull|invgauss|exgaussian|exwald)-p(\d+)-s(\d+)-n(\d+)-run(\d+)-a(\d+)$")
GROUP=re.compile(r"^q3-parametric-group-(200|1000|3000)-(\d+)-run(\d+)$")
LITE=re.compile(r"^q3-lite-score-(normal|lognormal|weibull|invgauss|exgaussian|exwald)-p(\d+)-s(\d+)-n(\d+)-run(\d+)-a(\d+)$")

def param_rows(fam):
    hi=LAST[fam]
    out=(2,(2+hi)//2,hi)
    assert len(set(out))==3
    return out

def grid():
    with (ROOT/"config/T2_V3_B3_prospective_321_grid.csv").open(newline="",encoding="utf-8-sig") as fd:
        records=list(csv.DictReader(fd))
    support=[r for r in records if r["mechanism"] not in ("mixture_bimodal_near","mixture_bimodal_far")]
    if len(records)!=321 or len(support)!=241 or sum(r["mechanism"]=="clean" for r in support)!=1:
        raise RuntimeError("Unexpected original frozen 321-scenario support")
    mechanisms=sorted({r["mechanism"] for r in support}-{"clean"})
    if len(mechanisms)!=6 or any(sum(r["mechanism"]==m for r in support)!=40 for m in mechanisms):
        raise RuntimeError("Unexpected six times 40 originally supported mechanism identities")
    chosen=[int(next(r["scenario_id"] for r in support if r["mechanism"]=="clean"))]
    manifest=[]
    for mechanism in mechanisms:
        region=[r for r in support if r["mechanism"]==mechanism]
        cont=[float(r["contamination"]) for r in region]
        mad=[float(r["mad_scale"]) for r in region]
        lo_c,hi_c=min(cont),max(cont)
        lo_m,hi_m=min(mad),max(mad)
        def xy(row):
            return ((float(row["contamination"])-lo_c)/(hi_c-lo_c),
                    (float(row["mad_scale"])-lo_m)/(hi_m-lo_m))
        def distance(a,b):
            x,y=xy(a);xx,yy=xy(b)
            return (x-xx)**2+(y-yy)**2
        # Start from the predeclared lowest contamination/MAD combination and
        # apply coverage-oriented, deterministic outcome-blind maximin selection.
        selected=[min(region,key=lambda r:(float(r["contamination"]),float(r["mad_scale"]),int(r["scenario_id"])))]
        while len(selected)<8:
            left=[r for r in region if r not in selected]
            far=max(left,key=lambda r:(min(distance(r,s) for s in selected),-int(r["scenario_id"])))
            selected.append(far)
        for r in selected:
            chosen.append(int(r["scenario_id"]))
            manifest.append({"mechanism":mechanism,"scenario_id":int(r["scenario_id"]),
                             "contamination":r["contamination"],"mad_scale":r["mad_scale"],
                             "band":r["band"],"selection_policy":"outcome_blind_2d_maximin"})
    if len(chosen)!=49 or len(set(chosen))!=49:
        raise RuntimeError("Prespecified selected support invalid")
    return chosen,manifest

def identities():
    return [(fam,p,s,n) for fam in FAMS for p in param_rows(fam)
            for s in range(40,50) for n in SIZES]

def gh(endpoint):
    p=subprocess.run(["gh","api",endpoint],capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError("GitHub source-artifact inventory failed: "+endpoint+" "+p.stderr[:300])
    return json.loads(p.stdout)

def recovery(runs):
    expected=set(identities());recovered={};sources=[]
    if not runs:return recovered,sources
    for runid in [int(v) for v in runs.split(",") if v.strip()]:
        meta=gh(f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{runid}")
        name=meta.get("name","")
        kind="full" if name=="T3 B3 Frozen Parametric Transfer" else (
            "exhaustive_q3" if name=="Q3 A-G | One-dispatch frozen-weight transfer, complete analysis and permanent backup" else (
                "compact_q3" if name=="Q3 A-G | Compact prespecified independent parameter transfer and permanent scientific backup" else None))
        if not kind or meta.get("repository",{}).get("full_name")!=os.environ["GITHUB_REPOSITORY"]:
            raise RuntimeError("Invalid or non-original source artifact run "+str(runid))
        page=1;matches=0
        while True:
            arr=gh(f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{runid}/artifacts?per_page=100&page={page}")["artifacts"]
            for art in arr:
                if art.get("expired"):continue
                name=art["name"];ident=None;kind_art="original"
                m=OLD.fullmatch(name)
                if m and int(m.group(5))==runid:ident=(m.group(1),int(m.group(2)),int(m.group(3)),int(m.group(4)))
                lite=LITE.fullmatch(name)
                if lite and int(lite.group(5))==runid:
                    ident=(lite.group(1),int(lite.group(2)),int(lite.group(3)),int(lite.group(4)))
                    kind_art="lite"
                gm=GROUP.fullmatch(name)
                if gm and int(gm.group(3))==runid:
                    n=int(gm.group(1));group=int(gm.group(2))
                    original_n=[i for i in [(f,p,s,n) for f,l in LAST.items() for p in range(2,l+1) for s in range(40,50)]]
                    group_members=original_n[group*4:group*4+4]
                    for x in group_members:
                        if x in expected:
                            candidate={"run":runid,"name":name,"kind":"group","artifact_id":art["id"]}
                            # Per-shard records take priority over group archives.
                            if x not in recovered:recovered[x]=candidate
                            matches+=1
                    continue
                if ident not in expected:continue
                candidate={"run":runid,"name":name,"kind":kind_art,"artifact_id":art["id"]}
                previous=recovered.get(ident)
                # An artifact name is a recovery *candidate*, not verified scientific
                # evidence. Prefer the original immutable full 241-scenario score
                # over a later possibly incomplete 49-scenario always()-upload.
                # The downstream worker verifies all score/manifests and recomputes
                # only when the candidate does not pass that audit.
                if (previous is None or previous["kind"]=="group" or
                    (kind_art=="original" and previous["kind"]!="original")):
                    recovered[ident]=candidate
                matches+=1
            if len(arr)<100:break
            page+=1
            if page>150:raise RuntimeError("Too many Actions artifact pages")
        sources.append({"run_id":runid,"kind":kind,"matched_prespecified_original_shards":matches})
    return recovered,sources

def plan(reused):
    shards=identities()
    assert len(shards)==540
    jobs=[]
    for i in range(0,len(shards),4):
        row={"group_index":i//4}
        for slot in range(4):
            x=shards[i+slot] if i+slot<len(shards) else ("",0,0,0)
            rec=reused.get(x,{})
            row.update({f"shard{slot}_family":x[0],f"shard{slot}_parameter_row":x[1],
                f"shard{slot}_seed":x[2],f"shard{slot}_n":x[3],
                f"shard{slot}_reuse_run":str(rec.get("run","")),
                f"shard{slot}_reuse_name":rec.get("name",""),
                f"shard{slot}_reuse_kind":rec.get("kind","")})
        jobs.append(row)
    if len(jobs)!=135:raise RuntimeError("Incorrect bounded GitHub matrix plan")
    return {"include":jobs}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-runs",default="")
    ap.add_argument("--out",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    ids,scenarios=grid()
    if args.self_test:
        assert len(plan({})["include"])==135
        assert len(identities())==540
        print("Q3_COMPACT_PRESPEC_TEST_PASS 6 families, 3 changed-parameter configurations, 3 n, 10 reserved independent seeds, 49 outcome-blind scenarios, 500 Monte Carlo reps")
        return
    found,src=recovery(args.source_runs)
    manifest={"schema":"T3_Q3_COMPACT_PRESPEC_V1",
        "design_frozen_before_conditional_outcomes":True,
        "parameter_row_policy":"first_middle_last_alternative_by_original_grid_order",
        "selected_parameter_rows":{f:list(param_rows(f)) for f in FAMS},
        "scenario_selection_policy":"one clean, 8 maximin-covering fixed original support cells per 6 mechanisms, entirely outcome-blind",
        "scenario_ids":ids,"scenario_definitions":scenarios,
        "full_design_shards":540,"reusable_preexisting_full_shards":len(found),
        "needed_shards":540-len(found),
        "original_full_shard_total":2490,
        "evaluation_seed_axis":"40:49","replications_per_scenario":500,
        "source_run_catalog":src,"matrix":plan(found)}
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
        print("Q3_COMPACT_PLAN_PASS",len(found),"reusable",540-len(found),"new")
    else:print(json.dumps(manifest,separators=(",",":")))
if __name__=="__main__":main()
