#!/usr/bin/env python3
"""RQ1 independent Held Out comparisons from immutable split archive backups."""
import argparse, csv, hashlib, io, json, math, pathlib, re, zipfile
import numpy as np
import pandas as pd
from scipy import stats

METHODS = ("ga", "nsga2", "de", "dirichlet")
def engine(model):
    tokens = re.split(r"[^a-z0-9]+", str(model).lower())
    for m in ("dirichlet", "nsga2", "de", "ga"):
        if m in tokens:
            return m
    return None

def restore(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["complete"] is True and manifest["schema_version"] == 1
    pieces = []
    for part in manifest["parts"]:
        p = directory / part["name"]
        raw = p.read_bytes()
        if len(raw) != part["bytes"] or hashlib.sha256(raw).hexdigest() != part["sha256"]:
            raise ValueError("Backup part checksum mismatch: " + str(p))
        pieces.append(raw)
    data = b"".join(pieces)
    if len(data) != manifest["size_bytes"] or hashlib.sha256(data).hexdigest() != manifest["sha256"]:
        raise ValueError("Backup archive checksum mismatch: " + str(directory))
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        scores = [n for n in z.namelist() if n.endswith("scores.csv") and not n.endswith("control_scores.csv")]
        if len(scores) != 1:
            raise ValueError("Expected exactly one scores.csv in " + str(directory))
        return pd.read_csv(z.open(scores[0])), manifest["sha256"]

def load(root, family, n):
    pattern = re.compile(r"actions-\d+_t3-b3-heldout-"+family+r"-s(\d+)-n"+str(n)+r"-run\d+\.zip")
    entries = []
    for d in root.iterdir():
        m = pattern.fullmatch(d.name)
        if m:
            entries.append((int(m.group(1)), d))
    if sorted(s for s,_ in entries) != list(range(10,20)):
        raise ValueError("Incomplete/duplicated Held Out seeds for "+family+" n="+str(n))
    parts=[]; lineage=[]
    for seed,d in entries:
        df,sha=restore(d)
        needed={"model","mse","q95","scenario_id","training_seed"}
        if not needed.issubset(df.columns):
            raise ValueError("Missing score columns: "+str(needed-set(df.columns)))
        df["eval_seed"]=seed
        df["method"]=df["model"].map(engine)
        df=df[df["method"].isin(METHODS)].copy()
        if df.empty: raise ValueError("No optimizer rows in "+str(d))
        parts.append(df)
        lineage.append({"seed":seed,"archive":d.name,"sha256":sha})
    return pd.concat(parts,ignore_index=True),lineage

def summarize(df, out, family, n):
    # A candidate is matched by its training seed, scenario and evaluation seed.
    keys=["training_seed","scenario_id","eval_seed"]
    group=df.groupby(keys+["method"],dropna=False)[["mse","q95"]].mean().reset_index()
    if group.duplicated(keys+["method"]).any(): raise ValueError("Duplicate matched unit")
    paired=group.pivot(index=keys,columns="method",values=["mse","q95"])
    paired=paired.dropna(subset=pd.MultiIndex.from_product([["mse","q95"],METHODS]))
    if paired.empty: raise ValueError("No fully matched optimizer observations")
    records=[]
    import itertools
    for a,b in itertools.combinations(METHODS,2):
        for metric in ("mse","q95"):
            # Each training seed/scenario comparison is averaged within each independent evaluation seed.
            delta=(paired[(metric,a)]-paired[(metric,b)]).groupby(level="eval_seed").mean()
            if len(delta)!=10: raise ValueError("Incomplete independent evaluation seeds")
            mean=float(delta.mean()); sd=float(delta.std(ddof=1)); se=sd/math.sqrt(10)
            tcrit=float(stats.t.ppf(.975,9))
            p=float(stats.ttest_1samp(delta,0).pvalue) if sd>0 else (1.0 if mean==0 else 0.0)
            baseline=float(paired[(metric,b)].mean())
            records.append(dict(family=family,sample_n=n,method_a=a,method_b=b,metric=metric,
              difference=mean,ci_low=mean-tcrit*se,ci_high=mean+tcrit*se,p=p,
              percent_vs_b=(-100*mean/baseline if baseline>0 else float("nan")),
              independent_seeds=10,matched_units=len(paired)))
    res=pd.DataFrame(records)
    # Holm correction across all 12 pairwise metric tests in this family/sample-size block.
    p=res.p.to_numpy(); order=np.argsort(p); adj=np.empty(len(p)); running=0.
    for rank,i in enumerate(order):
        running=max(running,min(1.,float(p[i])*(len(p)-rank)))
        adj[i]=running
    res["holm_p_block"]=adj
    out.mkdir(parents=True,exist_ok=True)
    res.to_csv(out/"pairwise.csv",index=False)
    long=group.groupby(["method","eval_seed"])[["mse","q95"]].mean().reset_index()
    long.to_csv(out/"seed_metrics.csv",index=False)
    ranks=long.copy()
    ranks["mse_rank"]=ranks.groupby("eval_seed")["mse"].rank()
    ranks["q95_rank"]=ranks.groupby("eval_seed")["q95"].rank()
    ranks.to_csv(out/"rank_tradeoff.csv",index=False)
    return {"family":family,"sample_n":n,"paired_units":len(paired),"seed_count":10,
            "methods":list(METHODS),"note":"Holm adjustment is within block; global correction must be calculated after aggregation."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive-root",required=True,type=pathlib.Path)
    p.add_argument("--family",required=True,choices=("normal","lognormal","weibull","invgauss","exgaussian","exwald"))
    p.add_argument("--n",required=True,type=int,choices=(200,1000,3000))
    p.add_argument("--output",required=True,type=pathlib.Path)
    a=p.parse_args()
    df,lineage=load(a.archive_root,a.family,a.n)
    meta=summarize(df,a.output,a.family,a.n)
    (a.output/"provenance.json").write_text(json.dumps({"analysis":meta,"input_archives":lineage},indent=2))
if __name__=="__main__": main()
