#!/usr/bin/env python3
"""T3 Q2 A-D: immutable Held Out archive audit, regime-level paired analyses.

Within-source-family confirmation only; cross-family belongs to Q3.
Original W are FROZEN. No optimizer training or Monte Carlo rerun.
All original archived ZIPs are reconstructed from SHA-256 verified Git LFS.
Python standard library only, allowing execution in pinned T3 R image.
"""
import argparse,csv,gzip,hashlib,io,json,math,statistics,sys,zipfile
from pathlib import Path
from collections import defaultdict,Counter

FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
SIZES=(200,1000,3000)
METHODS=("ga","nsga2","de","dirichlet")
SEEDS=tuple(range(10,20))
BENCH=("own","mean")
ROOT=Path("data-archive")
GRID=Path("config/T2_V3_B3_prospective_321_grid.csv")
REF_PATTERN="actions-*_t3-b3-discovery-own-benchmark-map-run41478038812.zip"
RUN=41208513291

def check(cond,message):
    if not cond:raise RuntimeError("Q2 scientific gate failed: "+message)

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as z:
        for part in iter(lambda:z.read(1024*1024),b""):h.update(part)
    return h.hexdigest()

def find_archive(stage,pattern):
    matches=sorted((ROOT/stage/"actions").glob(pattern))
    check(len(matches)==1,"missing/ambiguous immutable archive "+stage+"/"+pattern)
    return matches[0]

def manifest(folder,run_id):
    p=folder/"manifest.json"
    check(p.is_file(),"missing archive manifest "+str(folder))
    m=json.loads(p.read_text())
    check(m.get("schema_version")==1 and m.get("complete") is True,
          "unverified or partial original source "+str(folder))
    check(int(m["source"]["run_id"])==run_id,"unexpected original source run "+str(folder))
    check(m.get("parts") and all(int(z["bytes"])>200 and len(z["sha256"])==64 for z in m["parts"]),
          "missing or invalid archive part inventory")
    return m

def unzip_verified(directory,expected_run):
    m=manifest(directory,expected_run)
    data=io.BytesIO()
    for p in m["parts"]:
        f=directory/p["name"]
        check(f.is_file(),"unhydrated archive "+str(f))
        check(f.stat().st_size==p["bytes"] and digest(f)==p["sha256"],
              "LFS pointer or corrupted bytes "+str(f))
        with f.open("rb") as fin:
            while True:
                b=fin.read(1024*1024)
                if not b:break
                data.write(b)
    blob=data.getvalue()
    check(len(blob)==m["size_bytes"] and hashlib.sha256(blob).hexdigest()==m["sha256"],
          "original ZIP SHA256 mismatch "+str(directory))
    z=zipfile.ZipFile(io.BytesIO(blob))
    return z,m["sha256"]

def csv_from_zip(z,filename):
    files=[x for x in z.namelist() if x.endswith(filename) and not x.endswith("control_"+filename)]
    check(len(files)==1,"expected exactly one "+filename+" in original ZIP, got "+repr(files))
    return io.TextIOWrapper(z.open(files[0]),encoding="utf-8-sig",newline="")

def grid_read():
    rows=list(csv.DictReader(GRID.open(newline="")))
    check(len(rows)==321,"scenario grid must contain exactly 321 IDs")
    grid={}
    for r in rows:
        sid=int(r["scenario_id"])
        check(sid not in grid,"duplicate scenario")
        r["contamination"]=float(r["contamination"])
        r["mad_scale"]=float(r["mad_scale"])
        grid[sid]=r
    check(set(grid)==set(range(321)),"scenario ID coverage")
    support={i:r for i,r in grid.items() if not r["mechanism"].startswith("mixture_bimodal_")}
    cnt=Counter(r["mechanism"] for r in support.values())
    check(len(support)==241 and cnt["clean"]==1 and len(cnt)==7
          and all(v==40 for k,v in cnt.items() if k!="clean"),
          "241-support/80-reserved design and 6x40 contamination coverage")
    check(len(grid)-len(support)==80,"reserved Stress count")
    return support

def ref_read():
    folder=find_archive("discovery",REF_PATTERN)
    z,sha=unzip_verified(folder,41478038812)
    with z,csv_from_zip(z,"own_benchmark_map.csv") as f:
        rows=list(csv.DictReader(f))
    needed={"evaluation_family","sample_n","scenario_id","own_benchmark"}
    check(len(rows)==6*3*241 and needed.issubset(rows[0]),"benchmark selection map schema/coverage")
    seen={}
    for r in rows:
        k=(r["evaluation_family"],int(r["sample_n"]),int(r["scenario_id"]))
        check(k not in seen and r["own_benchmark"]!="mean" and r["own_benchmark"],"benchmark map duplicates")
        seen[k]=r["own_benchmark"]
    return seen,{"folder":str(folder),"original_sha256":sha}

def adjacency(grid):
    pairs=[]
    bymech=defaultdict(list)
    for i,r in grid.items():
        if r["mechanism"]!="clean":bymech[r["mechanism"]].append(i)
    for mechanism,ids in sorted(bymech.items()):
        frac=sorted(set(grid[i]["contamination"] for i in ids))
        sev=sorted(set(grid[i]["mad_scale"] for i in ids))
        xfi={x:i for i,x in enumerate(frac)}
        xsi={x:i for i,x in enumerate(sev)}
        for ii,i in enumerate(ids):
            for j in ids[ii+1:]:
                x,y=grid[i],grid[j]
                if x["contamination"]==y["contamination"] and abs(xsi[x["mad_scale"]]-xsi[y["mad_scale"]])==1:
                    axis="severity"
                    lo,hi=sorted((i,j),key=lambda t:grid[t]["mad_scale"])
                elif x["mad_scale"]==y["mad_scale"] and abs(xfi[x["contamination"]]-xfi[y["contamination"]])==1:
                    axis="fraction"
                    lo,hi=sorted((i,j),key=lambda t:grid[t]["contamination"])
                else:continue
                pairs.append(dict(mechanism=mechanism,axis=axis,low=lo,high=hi))
    check(len(pairs)>200,"insufficient outcome-blind local paired grid edges")
    return pairs

def scan_preflight():
    support=grid_read()
    adj=adjacency(support)
    bench_dir=find_archive("discovery",REF_PATTERN)
    manifest(bench_dir,41478038812)
    count=0
    for family in FAMILIES:
        for n in SIZES:
            for seed in SEEDS:
                d=find_archive("heldout",f"actions-*_t3-b3-heldout-{family}-s{seed}-n{n}-run{RUN}.zip")
                manifest(d,RUN)
                count+=1
    check(count==180,"expected 180 original Held Out score ZIPs")
    print(json.dumps(dict(status="PASS",heldout_original_archives=count,benchmark_map=True,
          design_scenarios=321,support=241,reserved=80,local_adjacency_edges=len(adj),
          no_retraining=True,source="original Git LFS ZIP manifests"),sort_keys=True))
    return True

def score_read(z,family,n,seed,support,bench_map):
    with csv_from_zip(z,"scores.csv") as f:
        rd=csv.DictReader(f)
        required={"model","mse","q95","scenario_id","training_seed","sample_n",
                  "source_family","evaluation_family"}
        check(required.issubset(rd.fieldnames),"original score CSV missing columns")
        candidates={}
        refs={}
        for r in rd:
            sid=int(r["scenario_id"])
            if sid not in support:continue
            src=r["source_family"]
            check(r["evaluation_family"]==family and int(r["sample_n"])==n,
                  "original score family/sample ID mismatch")
            check(int(r.get("heldout_seed") or r.get("seed_index") or -1)==seed,
                  "original Held Out evaluation seed mismatch")
            if src!=family:continue
            train=int(r["training_seed"])
            check(0<=train<=9,"unexpected training seed")
            model=r["model"]
            own=bench_map[(family,n,sid)]
            if model not in METHODS and model not in ("mean",own):continue
            v=(float(r["mse"]),float(r["q95"]))
            check(all(math.isfinite(x) and x>=0 for x in v),"negative or non-finite squared loss")
            if model in METHODS:
                key=(train,model,sid)
                check(key not in candidates,"duplicate frozen candidate row "+str(key))
                candidates[key]=v
            if model in ("mean",own):
                key=(sid,model)
                if key in refs:
                    check(all(abs(x-y)<1e-8*max(1,abs(x),abs(y)) for x,y in zip(refs[key],v)),
                          "repeated classical benchmark scores disagree")
                refs[key]=v
    check(len(candidates)==10*4*241 and len(refs)==241*2,
          f"incomplete original candidate/reference grid {family} n{n} seed{seed}: {len(candidates)},{len(refs)}")
    return candidates,refs

def write_csv(path,fields,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with (gzip.open(path,"wt",encoding="utf8",newline="",compresslevel=5) if path.suffix==".gz"
          else path.open("w",encoding="utf8",newline="")) as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader()
        for row in rows:w.writerow(row)

def block(family,n,output):
    support=grid_read()
    edges=adjacency(support)
    benchmarks,bmmeta=ref_read()
    output.mkdir(parents=True,exist_ok=False)
    panel=output/"paired_seed_cells.csv.gz"
    fields=["family","sample_n","scenario_id","mechanism","contamination","mad_scale","band",
            "method","training_seed","evaluation_seed","benchmark_role","benchmark",
            "mse_candidate","q95_candidate","mse_reference","q95_reference",
            "mse_difference","q95_difference","mse_gain_pct","q95_gain_pct"]
    # Block outputs remain small while preserving the crossed 10x10 seed structure.
    # Aggregation keys: method, scenario, reference role, independent evaluation seed.
    by_eval=defaultdict(lambda:[0.,0.,0.,0.,0])
    by_cell=defaultdict(lambda:[0.,0.,0.,0.,0])
    originals=[]
    count=0
    with gzip.open(panel,"wt",newline="",encoding="utf8",compresslevel=5) as fout:
        writer=csv.DictWriter(fout,fieldnames=fields)
        writer.writeheader()
        for seed in SEEDS:
            d=find_archive("heldout",f"actions-*_t3-b3-heldout-{family}-s{seed}-n{n}-run{RUN}.zip")
            z,sha=unzip_verified(d,RUN)
            with z:
                candidates,refs=score_read(z,family,n,seed,support,benchmarks)
            originals.append(dict(evaluation_seed=seed,archive=str(d),sha256=sha))
            for train in range(10):
                for method in METHODS:
                    for sid,spec in support.items():
                        cm,cq=candidates[(train,method,sid)]
                        for role in BENCH:
                            base=benchmarks[(family,n,sid)] if role=="own" else "mean"
                            bm,bq=refs[(sid,base)]
                            dm=cm-bm;dq=cq-bq
                            gm=100*(bm-cm)/max(abs(bm),1e-14)
                            gq=100*(bq-cq)/max(abs(bq),1e-14)
                            row=dict(family=family,sample_n=n,scenario_id=sid,
                                mechanism=spec["mechanism"],contamination=spec["contamination"],
                                mad_scale=spec["mad_scale"],band=spec["band"],
                                method=method,training_seed=train,evaluation_seed=seed,
                                benchmark_role=role,benchmark=base,mse_candidate=cm,q95_candidate=cq,
                                mse_reference=bm,q95_reference=bq,mse_difference=dm,
                                q95_difference=dq,mse_gain_pct=gm,q95_gain_pct=gq)
                            writer.writerow(row);count+=1
                            a=by_eval[(method,sid,role,seed)]
                            for i,val in enumerate((gm,gq,dm,dq)):a[i]+=val
                            a[4]+=1
                            b=by_cell[(method,sid,role)]
                            for i,val in enumerate((gm,gq,dm,dq)):b[i]+=val
                            b[4]+=1
    check(count==10*10*4*241*2 and len(by_eval)==4*241*2*10,
          "complete 10x10 original crossing and both benchmark panels")
    scenario=[]
    fields2=["family","sample_n","scenario_id","mechanism","contamination","mad_scale","band",
             "method","benchmark_role","n_training_seeds","n_evaluation_seeds",
             "mse_gain_pct","q95_gain_pct","mse_difference","q95_difference",
             "joint_positive","joint_5pct","any_worsening",
             "both_CI_positive_descriptive"]
    for method in METHODS:
        for sid,spec in sorted(support.items()):
            for role in BENCH:
                a=by_cell[(method,sid,role)]
                means=[a[i]/a[4] for i in range(4)]
                independent=[by_eval[(method,sid,role,seed)] for seed in SEEDS]
                gmseeds=[v[0]/v[4] for v in independent]
                gqseeds=[v[1]/v[4] for v in independent]
                # Approximate t9 intervals only, NOT multiplicity-calibrated inference.
                t9=2.2621571627409915
                lom=statistics.mean(gmseeds)-t9*statistics.stdev(gmseeds)/math.sqrt(10)
                loq=statistics.mean(gqseeds)-t9*statistics.stdev(gqseeds)/math.sqrt(10)
                scenario.append(dict(family=family,sample_n=n,scenario_id=sid,
                    mechanism=spec["mechanism"],contamination=spec["contamination"],
                    mad_scale=spec["mad_scale"],band=spec["band"],
                    method=method,benchmark_role=role,n_training_seeds=10,n_evaluation_seeds=10,
                    mse_gain_pct=means[0],q95_gain_pct=means[1],mse_difference=means[2],
                    q95_difference=means[3],joint_positive=int(means[0]>0 and means[1]>0),
                    joint_5pct=int(means[0]>=5 and means[1]>=5),
                    any_worsening=int(means[0]<0 or means[1]<0),
                    both_CI_positive_descriptive=int(lom>0 and loq>0)))
    check(len(scenario)==4*241*2,"scenario-level completeness")
    write_csv(output/"scenario_effects.csv",fields2,scenario)
    sidx={(r["method"],r["scenario_id"],r["benchmark_role"]):r for r in scenario}
    pairs=[]
    for p in edges:
        for method in METHODS:
            for role in BENCH:
                a=sidx[(method,p["low"],role)]
                b=sidx[(method,p["high"],role)]
                pairs.append(dict(family=family,sample_n=n,mechanism=p["mechanism"],axis=p["axis"],
                    scenario_low=p["low"],scenario_high=p["high"],method=method,benchmark_role=role,
                    mse_gain_change=float(b["mse_gain_pct"])-float(a["mse_gain_pct"]),
                    q95_gain_change=float(b["q95_gain_pct"])-float(a["q95_gain_pct"])))
    write_csv(output/"local_neighbors.csv",
      ["family","sample_n","mechanism","axis","scenario_low","scenario_high","method",
       "benchmark_role","mse_gain_change","q95_gain_change"],pairs)
    # Block factors are descriptive; only observed scenario cells contribute.
    groups=defaultdict(list)
    for r in scenario:
        for factor in ("mechanism","contamination","mad_scale","band"):
            groups[(r["method"],r["benchmark_role"],factor,str(r[factor]))].append(r)
        groups[(r["method"],r["benchmark_role"],"mechanism_by_fraction",
                str(r["mechanism"])+"|"+str(r["contamination"]))].append(r)
        groups[(r["method"],r["benchmark_role"],"mechanism_by_severity",
                str(r["mechanism"])+"|"+str(r["mad_scale"]))].append(r)
    factors=[]
    for (method,role,factor,level),rs in sorted(groups.items()):
        factors.append(dict(family=family,sample_n=n,method=method,benchmark_role=role,
            factor=factor,level=level,eligible_scenarios=len(rs),
            mean_mse_gain_pct=statistics.mean(float(x["mse_gain_pct"]) for x in rs),
            mean_q95_gain_pct=statistics.mean(float(x["q95_gain_pct"]) for x in rs),
            joint_positive=sum(int(x["joint_positive"]) for x in rs),
            joint_5pct=sum(int(x["joint_5pct"]) for x in rs),
            any_worsening=sum(int(x["any_worsening"]) for x in rs)))
    write_csv(output/"factor_profiles.csv",
      ["family","sample_n","method","benchmark_role","factor","level","eligible_scenarios",
       "mean_mse_gain_pct","mean_q95_gain_pct","joint_positive","joint_5pct","any_worsening"],factors)
    manifest_data=dict(schema="Q2-v1",analysis="Q2 A-D within-family independent confirmation",
      family=family,sample_n=n,original_heldout_archive_count=10,original_evaluation_seeds=list(SEEDS),
      original_training_seeds=list(range(10)),original_frozen_candidates_per_block=40,
      supported_scenarios=241,paired_benchmark_metric_records=count,scenario_rows=len(scenario),
      local_neighbor_edges=len(edges),mechanisms=sorted(set(x["mechanism"] for x in support.values())),
      design_is_incomplete_factorial=True,no_optimizer_training=True,no_new_monte_carlo=True,
      benchmark_lineage=bmmeta,original_archive_lineage=originals,
      scientific_scope="WITHIN-family original frozen weights, 241 supported scenarios; Q3 cross-family excluded",
      inference_scope="Descriptive t9 flags are not multiplicity calibrated; no confirmatory claims.",
      outputs={x.name:dict(sha256=digest(x),bytes=x.stat().st_size)
               for x in output.iterdir() if x.is_file()})
    (output/"Q2_BLOCK_MANIFEST.json").write_text(json.dumps(manifest_data,indent=2)+"\n")
    print("Q2_BLOCK_PASS",family,n,"rows",count,"original sources",len(originals),
          "scenario rows",len(scenario),"local edges",len(edges),flush=True)

def selftest():
    support=grid_read()
    edges=adjacency(support)
    check(len(support)==241 and len(edges)>200,"incomplete outcome-blind design")
    check(statistics.mean([1.,2.,3.])==2,"simple deterministic scientific arithmetic")
    print("Q2_SELFTEST_PASS",len(edges),"outcome-blind neighbor edges; original data untouched")

def main():
    p=argparse.ArgumentParser()
    sp=p.add_subparsers(dest="cmd",required=True)
    sp.add_parser("selftest");sp.add_parser("preflight")
    b=sp.add_parser("block")
    b.add_argument("--family",choices=FAMILIES,required=True)
    b.add_argument("--n",choices=SIZES,type=int,required=True)
    b.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.cmd=="selftest":selftest()
    elif a.cmd=="preflight":scan_preflight()
    else:block(a.family,a.n,a.output)
if __name__=="__main__":main()
