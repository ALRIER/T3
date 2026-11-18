#!/usr/bin/env python3
"""Independent Held Out deterministic controls from original, separately scored archives."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
SIZES=(200,1000,3000)
METHODS=("ga","nsga2","de","dirichlet")
CONTROLS=("convex_mse","local_deterministic")
ORIGINAL="R1/runs/44310024979"

def check(ok,msg):
    if not ok:raise RuntimeError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def report(family,n,source,out):
    check(family in FAMILIES and n in SIZES,"Unregistered original block")
    seedframes=[];lineage=[]
    for seed in range(10,20):
        path=source/f"seed{seed}"/"non_evolutionary_control_scores.csv"
        manifest=source/f"seed{seed}"/"SOURCE_LINEAGE.json"
        check(path.is_file() and manifest.is_file(),"Missing SHA256 verified original Held Out control scoring")
        m=json.loads(manifest.read_text())
        check((m["kind"],m["sample_n"],m["family"],m["evaluation_seed"],m["source_run"])==
          ("controls",n,family,seed,41208513291),"Original control source identity mismatch")
        d=pd.read_csv(path)
        required={"model","training_seed","heldout_seed","scenario_id","mse","q95"}
        check(required.issubset(d.columns),"Original Held Out controls lack scoring identity")
        check(len(d)==10*241*32,"Expected original 10 training seeds x 241 scenarios x 32 candidates")
        check(set(METHODS+CONTROLS).issubset(set(d.model)),"Original control method identities missing")
        chosen=d[d.model.isin(METHODS+CONTROLS)].copy()
        check(len(chosen)==10*241*6,"One of the original evolutionary or deterministic methods absent")
        check(not chosen.duplicated(["model","training_seed","heldout_seed","scenario_id"]).any(),
              "Repeated original candidate/control evaluation identity")
        check(set(chosen.training_seed)==set(range(10)) and set(chosen.heldout_seed)=={seed},
              "Held Out source violates original independent evaluation seeds")
        check(chosen.scenario_id.nunique()==241 and
              len(chosen.groupby(["training_seed","model"]))==60,
              "Original support scenarios or training models incomplete")
        check(np.isfinite(chosen[["mse","q95"]].to_numpy(float)).all() and
              (chosen[["mse","q95"]].to_numpy(float)>=0).all(),"Invalid score")
        collapsed=chosen.groupby(["training_seed","model"],as_index=False)[["mse","q95"]].mean()
        collapsed.insert(0,"eval_seed",seed)
        seedframes.append(collapsed)
        lineage.append({"eval_seed":seed,"source_archive_sha256":m["archive_sha256"],
                        "original_control_csv_sha256":sha(path)})
    scores=pd.concat(seedframes,ignore_index=True)
    check(len(scores)==10*10*6 and
          not scores.duplicated(["eval_seed","training_seed","model"]).any(),
          "Independent deterministic control candidate panel is incomplete")
    prior=pd.read_csv(Path(ORIGINAL)/"heldout"/f"{family}-n{n}"/"candidate_by_eval.csv")
    matched=scores[scores.model.isin(METHODS)].merge(prior,
       left_on=["training_seed","eval_seed","model"],right_on=["training_seed","eval_seed","method"],
       suffixes=("_raw","_prior"),validate="one_to_one")
    check(len(matched)==400,"Method-level original Held Out scoring reproducibility mismatch")
    for metric in ("mse","q95"):
        check(np.allclose(matched[metric+"_raw"],matched[metric+"_prior"],rtol=1e-7,atol=1e-10),
             "Separate control file does not reproduce original R1 candidate "+metric)
    means=scores.groupby(["eval_seed","model"],as_index=False)[["mse","q95"]].mean()
    records=[]
    for method,control,metric in itertools.product(METHODS,CONTROLS,("mse","q95")):
        pair=means[means.model.isin((method,control))].pivot(index="eval_seed",columns="model",values=metric)
        check(pair.shape==(10,2) and list(pair.index)==list(range(10,20)),"Independent seed pairing failed")
        diff=(pair[method]-pair[control]).to_numpy()
        avg=float(np.mean(diff))
        sd=float(np.std(diff,ddof=1))
        se=sd/np.sqrt(10.)
        p=float(2*stats.t.sf(abs(avg/se),9)) if sd>0 else (1. if avg==0 else 0.)
        q=float(stats.t.ppf(.975,9))
        records.append(dict(family=family,sample_n=n,candidate=method,control=control,metric=metric,
            difference_candidate_minus_control=avg,
            confidence95_lower=float(avg-q*se),confidence95_upper=float(avg+q*se),
            original_paired_t_p=p,
            relative_improvement_pct=100*float(pair[control].mean()-pair[method].mean())/
               max(float(pair[control].mean()),1e-15),
            independent_eval_seeds=10,original_training_seeds_averaged=10,
            independent_seed_favor_candidate=int(sum(diff<0)),
            significant_p_before_global_multiplicity=bool(p<.05)))
    out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(records).to_csv(out/"independent_deterministic_contrasts.csv",index=False)
    scores.to_csv(out/"candidate_control_by_train_eval_seed.csv",index=False)
    (out/"SOURCE_LINEAGE.json").write_text(json.dumps({
        "source":"original separate non_evolutionary_control_scores.csv inside original Held Out archives",
        "source_run":41208513291,"family":family,"sample_n":n,
        "training_seeds":list(range(10)),"independent_eval_seeds":list(range(10,20)),
        "original_evolutionary_scores_confirmed_against_R1":True,
        "same_original_frozen_discovery_W_for_controls":True,
        "no_retraining_or_rescoring":True,"archives":lineage,
        "statistical_caveat":"Evaluation seed is the independent unit; no selection-aware inference claimed"},
        indent=2)+"\n")
    print("R1_ORIGINAL_INDEPENDENT_DETERMINISTIC_CONTROLS_PASS",family,n,len(records),flush=True)

def holm(v):
    x=np.asarray(v,dtype=float)
    check(np.isfinite(x).all() and ((x>=0)&(x<=1)).all(),"Invalid deterministic p-values")
    a=np.empty(len(x));prev=0.
    for ix,k in enumerate(np.argsort(x)):
        prev=max(prev,min(1.,float(x[k])*(len(x)-ix)));a[k]=prev
    return a

def finalize(root,out):
    d=[]
    for f in FAMILIES:
        for n in SIZES:
            p=root/"controls"/f"{f}-n{n}"/"independent_deterministic_contrasts.csv"
            check(p.is_file(),"Missing one original deterministic Held Out block")
            v=pd.read_csv(p)
            check(len(v)==16 and set(v.family)=={f} and set(v.sample_n)=={n},
                  "Missing deterministic 8 candidate-control x 2 metric panel")
            d.append(v)
    x=pd.concat(d,ignore_index=True)
    check(len(x)==288 and not x.duplicated(["family","sample_n","candidate","control","metric"]).any(),
          "Original Held Out deterministic 288 hypotheses incomplete")
    x["holm_p_global_288"]=holm(x.original_paired_t_p.to_numpy(float))
    out.mkdir(parents=True,exist_ok=True)
    x.to_csv(out/"deterministic_controls_original_heldout_global_holm.csv",index=False)
    g=x.groupby(["candidate","control","metric"],as_index=False).agg(
      strata=("family","size"),
      contrasts_favor_candidate=("difference_candidate_minus_control",lambda v:int((v<0).sum())),
      holm_288_supported=("holm_p_global_288",lambda v:int((v<.05).sum())),
      median_relative_improvement_pct=("relative_improvement_pct","median"))
    g.to_csv(out/"deterministic_controls_reviewer_summary.csv",index=False)
    (out/"DETERMINISTIC_README.md").write_text(
      "# RQ1 deterministic control independent evidence\n\n"
      "Original 10 x 10 Discovery training/evaluation seed candidates were recovered from "
      "the separately stored original Held Out non_evolutionary_control_scores.csv, without "
      "fitting controls or rescoring outcomes. Original four evolutionary method losses "
      "were cross-checked against the preserved R1 Held Out candidate panel. "
      "Both deterministic models used the original Discovery frozen weights.\n\n"
      "The 288 candidate-versus-control MSE/Q95 matched contrasts use independent "
      "evaluation seeds and global Holm adjustment. Training-seed candidates are "
      "correlated within evaluation streams; these results are a posthoc reviewer "
      "sensitivity analysis, not a prospectively prespecified confirmatory family.\n")
    print("R1_DETERMINISTIC_GLOBAL_PASS",len(x),int((x.holm_p_global_288<.05).sum()),flush=True)

def main():
    p=argparse.ArgumentParser()
    sp=p.add_subparsers(dest="mode",required=True)
    b=sp.add_parser("block")
    b.add_argument("--family",required=True,choices=FAMILIES)
    b.add_argument("--n",required=True,type=int,choices=SIZES)
    b.add_argument("--source",required=True,type=Path)
    b.add_argument("--output",required=True,type=Path)
    g=sp.add_parser("finalize")
    g.add_argument("--root",required=True,type=Path)
    g.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.mode=="block":report(a.family,a.n,a.source,a.output)
    else:finalize(a.root,a.output)
if __name__=="__main__":main()
