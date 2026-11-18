#!/usr/bin/env python3
"""R1 follow-up: verified archived Discovery, matched Held Out, and reviewer audits.

No training, optimizer tuning, or reselection of the frozen W vectors occurs.
Original R1 Held Out inference remains immutable; new inferential checks are
separate, conservatively labeled sensitivity panels.
"""
import argparse
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import re
import tarfile
import zipfile
import numpy as np
import pandas as pd
from scipy import stats
from t3_b3_rq1_analysis import METHODS, load

FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
SIZES=(200,1000,3000)
PRIOR_RUN="44307352615"
def die(message):
    raise ValueError(message)
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def archive_bytes(folder):
    meta=json.loads((folder/"manifest.json").read_text())
    if meta.get("complete") is not True or meta.get("schema_version")!=1:
        die("Incomplete split-backup manifest: "+str(folder))
    chunks=[]
    for spec in meta["parts"]:
        p=folder/spec["name"]
        block=p.read_bytes()
        if len(block)!=spec["bytes"] or hashlib.sha256(block).hexdigest()!=spec["sha256"]:
            die("LFS part corruption/unhydrated pointer: "+str(p))
        chunks.append(block)
    blob=b"".join(chunks)
    if len(blob)!=meta["size_bytes"] or hashlib.sha256(blob).hexdigest()!=meta["sha256"]:
        die("Recovered archive checksum failed: "+str(folder))
    return blob,meta
def restore_discovery(a):
    rx=re.compile(r"actions-\d+_t3-b3-discovery-bundle-n"+str(a.n)+r"-run41487091262\.zip$")
    dirs=[d for d in a.archive_root.iterdir() if rx.fullmatch(d.name)]
    if len(dirs)!=1: die("Expected exactly one frozen Discovery bundle for n="+str(a.n))
    blob,meta=archive_bytes(dirs[0])
    a.output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        tarpaths=[p for p in z.namelist() if p.endswith("discovery-n"+str(a.n)+".tar.gz")]
        if len(tarpaths)!=1: die("Discovery bundle is missing its only tar.gz payload")
        target=z.read(tarpaths[0])
        checks=[p for p in z.namelist() if p.endswith("discovery-n"+str(a.n)+".tar.gz.sha256")]
        if len(checks)!=1: die("No archived tar digest")
        if hashlib.sha256(target).hexdigest()!=z.read(checks[0]).decode().split()[0].lower():
            die("Discovery tar checksum mismatch")
        with tarfile.open(fileobj=io.BytesIO(target),mode="r:gz") as tf:
            tf.extractall(a.output,filter="data")
    rds=list(a.output.rglob("discovery.rds"))
    if len(rds)!=60: die("Expected exactly 60 archived Discovery fits, got "+str(len(rds)))
    (a.output/"R1_SOURCE_MANIFEST.json").write_text(json.dumps({
        "origin":"verified repository split archive","archive":dirs[0].name,
        "archive_sha256":meta["sha256"],"tar_sha256":hashlib.sha256(target).hexdigest(),
        "sample_n":a.n,"rds_count":len(rds)},indent=2))
    print("R1_DISCOVERY_RESTORE_PASS",a.n,len(rds))
def heldout_block(a):
    df,lineage=load(a.archive_root,a.family,a.n)
    keys=["training_seed","scenario_id","eval_seed","method"]
    raw=df.groupby(keys,as_index=False)[["mse","q95"]].mean()
    if len(raw)!=10*241*10*4: die("Incomplete Held Out candidate grid for "+a.family+str(a.n))
    if sorted(raw.eval_seed.unique().tolist())!=list(range(10,20)) or sorted(raw.training_seed.unique().tolist())!=list(range(10)):
        die("Unexpected Held Out independent/training seeds")
    if raw.scenario_id.nunique()!=241 or set(raw.method.unique())!=set(METHODS):
        die("Wrong Held Out support scenario or method coverage")
    full=raw.groupby(["training_seed","eval_seed","method"],as_index=False)[["mse","q95"]].mean()
    if len(full)!=400:die("Expected 400 candidate by evaluation-seed records")
    per_scenario=raw.groupby(["scenario_id","method"],as_index=False)[["mse","q95"]].mean()
    out=a.output;out.mkdir(parents=True,exist_ok=True)
    full.to_csv(out/"candidate_by_eval.csv",index=False)
    per_scenario.to_csv(out/"scenario_descriptive.csv",index=False)
    # Verify that the previously published Held Out seed summaries are reproduced.
    old=pd.read_csv(a.prior/"heldout"/(a.family+"-n"+str(a.n))/"seed_metrics.csv")
    new=full.groupby(["method","eval_seed"],as_index=False)[["mse","q95"]].mean()
    verified=old.merge(new,on=["method","eval_seed"],suffixes=("_old","_new"),validate="one_to_one")
    if len(verified)!=40:die("Missing prior R1 Held Out seeds")
    for m in ("mse","q95"):
        if not np.allclose(verified[m+"_old"],verified[m+"_new"],rtol=1e-9,atol=1e-12):
            die("R1 run reproduction check failed: "+m)
    (out/"lineage.json").write_text(json.dumps({
        "family":a.family,"sample_n":a.n,"original_r1_run":PRIOR_RUN,
        "archived_scores":lineage,"independent_eval_seeds":list(range(10,20)),
        "training_seeds":list(range(10))},indent=2))
    print("R1_HELDOUT_BLOCK_PASS",a.family,a.n)
def holm(p):
    p=np.asarray(p,dtype=float)
    if (not np.isfinite(p).all()) or (p<0).any() or (p>1).any():die("Invalid p-values")
    order=np.argsort(p);out=np.empty(len(p));prev=0.
    for i,j in enumerate(order):
        prev=max(prev,min(1.,p[j]*(len(p)-i)));out[j]=prev
    return out
def exact_signflip(x):
    x=np.asarray(x,dtype=float)
    if x.shape!=(10,) or not np.isfinite(x).all():die("Sign-flip sensitivity requires 10 finite seeds")
    observed=abs(np.mean(x))
    if observed==0:return 1.
    signs=np.array(list(itertools.product([-1.,1.],repeat=10)))
    simulated=np.abs((signs*x).mean(axis=1))
    return float(np.mean(simulated >= observed-1e-12*max(1.,observed)))
def finish(a):
    root=a.root
    frames=[]
    for f in FAMILIES:
        for n in SIZES:
            sub=root/"heldout"/(f+"-n"+str(n))
            p=sub/"candidate_by_eval.csv"
            if not p.exists():die("Missing one of 18 Held Out blocks: "+str(p))
            d=pd.read_csv(p);d.insert(0,"family",f);d.insert(1,"sample_n",n)
            if len(d)!=400:die("Held Out candidate table has unexpected size")
            frames.append(d)
    held=pd.concat(frames,ignore_index=True)
    training=[];controls=[];budget=[]
    for n in SIZES:
        sub=root/"discovery"/("n"+str(n))
        t=sub/"training_method_scores.csv.gz"
        b=sub/"training_optimizer_costs.csv"
        c=sub/"training_deterministic_controls.csv.gz"
        for f in (t,b,c):
            if not f.exists():die("Missing Discovery result: "+str(f))
        training.append(pd.read_csv(t));budget.append(pd.read_csv(b));controls.append(pd.read_csv(c))
    train=pd.concat(training,ignore_index=True);cost=pd.concat(budget,ignore_index=True)
    control=pd.concat(controls,ignore_index=True)
    if len(train)!=180*4*241:die("Training candidate/scenario grid is incomplete")
    if len(cost)!=720 or cost[["family","sample_n","training_seed","method"]].duplicated().any():
        die("Frozen optimizer accounting is incomplete")
    expected=held[["family","sample_n","training_seed","method"]].drop_duplicates()
    if len(expected)!=720 or len(expected.merge(cost,on=["family","sample_n","training_seed","method"],validate="one_to_one"))!=720:
        die("Held Out and frozen Discovery identities differ")
    out=root/"synthesis";out.mkdir(exist_ok=True)
    # Discovery ranks are computed strictly from training data, never used to reselect W.
    trainmean=train.groupby(["family","sample_n","training_seed","method"],as_index=False)[["mse","q95"]].mean()
    heldmean=held.groupby(["family","sample_n","training_seed","method"],as_index=False)[["mse","q95"]].mean()
    joined=trainmean.merge(heldmean,on=["family","sample_n","training_seed","method"],suffixes=("_discovery","_heldout"),validate="one_to_one")
    for metric in ("mse","q95"):
        joined[metric+"_train_rank"]=joined.groupby(["family","sample_n","training_seed"])[metric+"_discovery"].rank(method="average")
        joined[metric+"_held_rank"]=joined.groupby(["family","sample_n","training_seed"])[metric+"_heldout"].rank(method="average")
        joined[metric+"_rank_shift"]=joined[metric+"_held_rank"]-joined[metric+"_train_rank"]
        joined[metric+"_gap_ratio"]=joined[metric+"_heldout"]/joined[metric+"_discovery"].clip(lower=1e-15)
    joined.to_csv(out/"discovery_vs_heldout_rank_and_gap.csv",index=False)
    winner=[]
    for (f,n,seed),g in joined.groupby(["family","sample_n","training_seed"]):
        for metric in ("mse","q95"):
            a0=g.loc[g[metric+"_discovery"].idxmin(),"method"]
            b0=g.loc[g[metric+"_heldout"].idxmin(),"method"]
            rho=float(stats.spearmanr(g[metric+"_train_rank"],g[metric+"_held_rank"]).statistic)
            winner.append(dict(family=f,sample_n=n,training_seed=seed,metric=metric,
              discovery_winner=a0,heldout_winner=b0,preserved=a0==b0,spearman_rho=rho))
    pd.DataFrame(winner).to_csv(out/"ranking_preservation.csv",index=False)
    # Across original independent evaluation seeds, with 10 training vectors
    # averaged within each seed: descriptive tradeoff and ranking uncertainty.
    seedavg=held.groupby(["family","sample_n","eval_seed","method"],as_index=False)[["mse","q95"]].mean()
    rng=np.random.default_rng(20261118)
    best=[];frontier=[];uncertainty=[]
    for (f,n),g in seedavg.groupby(["family","sample_n"]):
        means=g.groupby("method")[["mse","q95"]].mean().reindex(METHODS)
        if means.isna().any().any():die("Missing independent method means")
        for m in METHODS:
            dominated=any((means.loc[j].values<=means.loc[m].values).all() and
                (means.loc[j].values<means.loc[m].values).any() for j in METHODS if j!=m)
            frontier.append(dict(family=f,sample_n=n,method=m,mse=float(means.loc[m,"mse"]),
                q95=float(means.loc[m,"q95"]),pareto_nondominated=not dominated))
        for metric in ("mse","q95"):
            arr=g.pivot(index="eval_seed",columns="method",values=metric).reindex(columns=METHODS)
            if len(arr)!=10 or arr.isna().any().any():die("Incomplete ranking bootstrap data")
            samples=arr.to_numpy();counts=np.zeros(4)
            for _ in range(2000):
                indices=rng.integers(0,10,size=10);average=samples[indices].mean(axis=0)
                indices_best=np.flatnonzero(np.isclose(average,average.min(),rtol=1e-12,atol=1e-14))
                counts[indices_best]+=1/len(indices_best)
            for i,m in enumerate(METHODS):
                best.append(dict(family=f,sample_n=n,metric=metric,method=m,
                    bootstrap_probability_best=counts[i]/2000,bootstrap_iterations=2000,
                    independent_evaluation_seeds=10))
    pd.DataFrame(frontier).to_csv(out/"mse_q95_pareto_tradeoff.csv",index=False)
    pd.DataFrame(best).to_csv(out/"rank_probability_seed_bootstrap.csv",index=False)
    stability=heldmean.groupby(["family","sample_n","method"])[["mse","q95"]].agg(["mean","std","min","max"]).reset_index()
    stability.columns=["family","sample_n","method","mse_mean","mse_sd_across_training_seeds",
                       "mse_min","mse_max","q95_mean","q95_sd_across_training_seeds","q95_min","q95_max"]
    stability["mse_cv"]=stability["mse_sd_across_training_seeds"]/stability["mse_mean"].clip(lower=1e-15)
    stability["q95_cv"]=stability["q95_sd_across_training_seeds"]/stability["q95_mean"].clip(lower=1e-15)
    stability.to_csv(out/"optimizer_training_seed_stability.csv",index=False)
    # Budget-efficient effects are descriptive, not wall-clock comparisons.
    eff=joined.merge(cost,on=["family","sample_n","training_seed","method"],validate="one_to_one")
    for metric in ("mse","q95"):
        base=joined[joined.method=="dirichlet"][["family","sample_n","training_seed",metric+"_heldout"]].rename(
            columns={metric+"_heldout":metric+"_dirichlet"})
        eff=eff.merge(base,on=["family","sample_n","training_seed"],validate="many_to_one")
        eff[metric+"_relative_gain_pct_vs_dirichlet"]=100*(eff[metric+"_dirichlet"]-eff[metric+"_heldout"])/eff[metric+"_dirichlet"].clip(lower=1e-15)
        eff[metric+"_pct_gain_per_1000_evaluations"]=eff[metric+"_relative_gain_pct_vs_dirichlet"]*1000/eff.actual_evaluations
    eff.to_csv(out/"compute_budget_vs_independent_improvement.csv",index=False)
    # Independent evaluation-seed exact sign-flip sensitivity; not a replacement
    # for original confirmatory CI/Holm family or for selection-aware calibration.
    prior=pd.read_csv(a.prior/"all_pairwise_global_holm.csv")
    sensitivity=[]
    for (f,n),g in seedavg.groupby(["family","sample_n"]):
        for a0,b0 in itertools.combinations(METHODS,2):
            for metric in ("mse","q95"):
                pivot=g.pivot(index="eval_seed",columns="method",values=metric)
                delta=(pivot[a0]-pivot[b0]).sort_index().to_numpy()
                if delta.shape!=(10,):die("Incomplete paired seed sensitivity")
                loo=np.array([(delta.sum()-v)/9 for v in delta])
                sensitivity.append(dict(family=f,sample_n=n,method_a=a0,method_b=b0,metric=metric,
                  p_signflip_exact_two_sided=exact_signflip(delta),
                  mean_seed_difference=float(delta.mean()),
                  leave_one_seed_out_all_favor_a=bool((loo<0).all()),
                  leave_one_seed_out_all_favor_b=bool((loo>0).all()),
                  leave_one_out_min_mean=float(loo.min()),leave_one_out_max_mean=float(loo.max())))
    sensitivity=pd.DataFrame(sensitivity)
    if len(sensitivity)!=216:die("Sensitivity contrast count mismatch")
    sensitivity["holm_signflip_global"]=holm(sensitivity.p_signflip_exact_two_sided.values)
    reference=prior[["family","sample_n","method_a","method_b","metric","p","holm_p_global"]]
    sensitivity=sensitivity.merge(reference,on=["family","sample_n","method_a","method_b","metric"],validate="one_to_one")
    if len(sensitivity)!=216:die("Original R1 contrasts mismatch")
    sensitivity.to_csv(out/"reviewer_exact_signflip_loo_global_holm.csv",index=False)
    # Deterministic optimization controls, when present, are strictly training-only.
    if len(control):
        control.to_csv(out/"deterministic_training_only_controls.csv",index=False)
    else:
        (out/"deterministic_training_only_controls_NOT_AVAILABLE.txt").write_text(
            "No deterministic control rows were found in restored training_score panels. "
            "Independent constrained-quadratic-program comparison requires separate frozen control evaluation.\n")
    # Generate publication figures from aggregated independent evidence.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rank=pd.DataFrame(winner)
    fig,ax=plt.subplots(figsize=(8,4))
    ratio=rank.groupby(["metric","discovery_winner"])["preserved"].mean().unstack(fill_value=0).reindex(columns=METHODS)
    ratio.plot.bar(ax=ax,rot=0)
    ax.set_ylabel("Fraction retaining Discovery winner on Held Out")
    ax.set_xlabel("Metric");ax.set_ylim(0,1);fig.tight_layout()
    fig.savefig(out/"figure_r1_rank_retention.svg");fig.savefig(out/"figure_r1_rank_retention.png",dpi=220);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,5))
    pareto=pd.DataFrame(frontier)
    for m,g in pareto.groupby("method"):
        ax.scatter(g.mse,g.q95,label=m,alpha=.7,s=20)
    ax.set(xlabel="Independent mean MSE",ylabel="Independent mean Q95",title="RQ1 method tradeoff across family × sample-size blocks")
    ax.legend();fig.tight_layout()
    fig.savefig(out/"figure_r1_tradeoff.svg");fig.savefig(out/"figure_r1_tradeoff.png",dpi=220);plt.close(fig)
    # Source hash inventory excludes Git-LFS payload duplicates but includes
    # provenance stored within each 21-block artifact.
    files=sorted(p for p in root.rglob("*") if p.is_file() and p.name!="R1_FINAL_MANIFEST.json")
    digest=[dict(path=str(p.relative_to(root)),sha256=sha(p),bytes=p.stat().st_size) for p in files]
    manifest={
       "source_original_r1_run":PRIOR_RUN,
       "independent_heldout_seeds":10,"training_seeds":10,"scenario_count":241,
       "source_families":list(FAMILIES),"sample_sizes":list(SIZES),
       "frozen_candidate_count":720,"training_discovery_units":180,
       "no_retraining":True,"primary_confirmatory_comparisons_reused":216,
       "additional_signflip_tests":"sensitivity_only_not_selection_aware",
       "deterministic_control":"Discovery training scores only; no Held Out optimization superiority claim",
       "computational_cost":"actual candidate evaluations; excludes wall time and tuning overhead",
       "files":digest}
    (root/"R1_FINAL_MANIFEST.json").write_text(json.dumps(manifest,indent=2))
    print("R1_FOLLOWUP_PASS",len(train),len(held),len(sensitivity),len(digest))
def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    d=sub.add_parser("restore-discovery");d.add_argument("--archive-root",type=Path,required=True)
    d.add_argument("--n",type=int,required=True);d.add_argument("--output",type=Path,required=True)
    h=sub.add_parser("heldout-block");h.add_argument("--archive-root",type=Path,required=True)
    h.add_argument("--family",required=True);h.add_argument("--n",type=int,required=True)
    h.add_argument("--prior",type=Path,required=True);h.add_argument("--output",type=Path,required=True)
    f=sub.add_parser("finalize");f.add_argument("--root",type=Path,required=True);f.add_argument("--prior",type=Path,required=True)
    a=p.parse_args()
    if a.mode=="restore-discovery":restore_discovery(a)
    elif a.mode=="heldout-block":heldout_block(a)
    else:finish(a)
if __name__=="__main__":main()
