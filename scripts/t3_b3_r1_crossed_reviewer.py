#!/usr/bin/env python3
"""RQ1 crossed-seed and joint-metric reviewer diagnostics on frozen R1 data.

Inputs are immutable, already archived candidate-by-eval loss panels.
No new simulation, training, scoring, hyperparameter search or W selection.
Crossed bootstrap and random-effects t checks are sensitivity analyses,
not new preregistered confirmatory tests or proof of CI coverage.
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as t_distribution

FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
METHODS=("ga","nsga2","de","dirichlet")
SIZES=(200,1000,3000)
PRIMARY="44307352615"
SOURCE="44310024979"
AUDIT="44313738898"
PAIRS=tuple(itertools.combinations(METHODS,2))
BOOTSTRAP_ITERATIONS=4000

def require(ok,msg):
    if not ok: raise ValueError(msg)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def holm(values):
    values=np.asarray(values,float)
    require(np.isfinite(values).all() and ((values>=0)&(values<=1)).all(),"Invalid sensitivity p-values")
    index=np.argsort(values)
    output=np.empty(len(values))
    prior=0.
    for i,j in enumerate(index):
        prior=max(prior,min(1.,float(values[j])*(len(values)-i)))
        output[j]=prior
    return output

def variance_components(x):
    """Balanced crossed random-intercept method of moments for 10×10 cells.

    Two independent random factors: training-seed and evaluation-seed.
    Fixed averaging over the predeclared 241 supported scenarios.
    Truncated negative variance components are marked explicitly.
    """
    x=np.asarray(x,float)
    require(x.shape==(10,10) and np.isfinite(x).all(),"Expected 10×10 finite crossed matrix")
    mu=float(x.mean())
    row=x.mean(axis=1)
    col=x.mean(axis=0)
    residual=x-row[:,None]-col[None,:]+mu
    ms_t=10*float(((row-mu)**2).sum())/9
    ms_e=10*float(((col-mu)**2).sum())/9
    ms_r=float((residual**2).sum())/81
    raw_t=(ms_t-ms_r)/10
    raw_e=(ms_e-ms_r)/10
    vt=max(0.,raw_t)
    ve=max(0.,raw_e)
    # Residual interaction component is retained even if main effects truncate.
    vr=ms_r
    variance=vt/10+ve/10+vr/100
    return dict(mean_difference=mu,crossed_se=math.sqrt(variance),
      training_variance=vt,evaluation_variance=ve,residual_variance=vr,
      truncated_training_component=raw_t<0,truncated_evaluation_component=raw_e<0,
      training_fraction=vt/(vt+ve+vr) if (vt+ve+vr)>0 else None,
      evaluation_fraction=ve/(vt+ve+vr) if (vt+ve+vr)>0 else None)

def matrices(df):
    needed={"training_seed","eval_seed","method","mse","q95"}
    require(needed.issubset(df.columns),"Missing original candidate-by-evaluation fields")
    require(len(df)==400 and not df.duplicated(["training_seed","eval_seed","method"]).any(),
      "Original 400 candidate cells missing or duplicated")
    require(set(df.method)==set(METHODS) and set(df.training_seed)==set(range(10))
      and set(df.eval_seed)==set(range(10,20)),"Frozen candidate/evaluation identities differ")
    require(np.isfinite(df[["mse","q95"]].to_numpy(float)).all(),"Nonfinite original R1 losses")
    result={}
    for method in METHODS:
        z=df[df.method==method].sort_values(["training_seed","eval_seed"])
        require(len(z)==100 and list(zip(z.training_seed,z.eval_seed))==
          list(itertools.product(range(10),range(10,20))),"Misaligned pair grid")
        result[method]=z[["mse","q95"]].to_numpy(float).reshape(10,10,2)
        require((result[method]>=0).all(),"Negative MSE/Q95 in original scored data")
    return result

def score_pair(f,n,a,b,arrays,B):
    x=arrays[a]
    y=arrays[b]
    rng=np.random.default_rng(int.from_bytes(hashlib.sha256(
      f"r1-20261118-crossed-{f}-{n}-{a}-{b}".encode()).digest()[:8],"little"))
    ti=rng.integers(0,10,(B,10),dtype=np.int16)
    ei=rng.integers(0,10,(B,10),dtype=np.int16)
    xmean=x[ti[:,:,None],ei[:,None,:],:].mean(axis=(1,2))
    ymean=y[ti[:,:,None],ei[:,None,:],:].mean(axis=(1,2))
    # Paired resampling of both method outcomes across BOTH crossed factors.
    forward=100*(ymean-xmean)/np.maximum(ymean,1e-15)
    reverse=100*(xmean-ymean)/np.maximum(xmean,1e-15)
    observed_f=100*(y.mean(axis=(0,1))-x.mean(axis=(0,1)))/np.maximum(y.mean(axis=(0,1)),1e-15)
    observed_r=100*(x.mean(axis=(0,1))-y.mean(axis=(0,1)))/np.maximum(x.mean(axis=(0,1)),1e-15)
    directional={}
    for name,sample,point in (("a_over_b",forward,observed_f),("b_over_a",reverse,observed_r)):
        lows=np.quantile(sample,.025,axis=0)
        highs=np.quantile(sample,.975,axis=0)
        rec={"family":f,"sample_n":n,"method_a":a,"method_b":b,
             "direction":name,"mse_gain_pct":float(point[0]),"q95_gain_pct":float(point[1]),
             "mse_ci95_low_pct":float(lows[0]),"mse_ci95_high_pct":float(highs[0]),
             "q95_ci95_low_pct":float(lows[1]),"q95_ci95_high_pct":float(highs[1]),
             "bootstrap_prob_both_positive":float(np.mean((sample[:,0]>0)&(sample[:,1]>0))),
             "joint_positive_bonferroni_95_within_pair":bool(np.all(lows>0)),
             "joint_onepct_bonferroni_95_within_pair":bool(np.all(lows>1)),
             "joint_fivepct_bonferroni_95_within_pair":bool(np.all(lows>5)),
             "bootstrap_replicates":B,"exploratory_thresholds_not_preregistered":True}
        directional[name]=rec
    metric=[]
    for j,m in enumerate(("mse","q95")):
        diff=x[:,:,j]-y[:,:,j]
        components=variance_components(diff)
        se=components["crossed_se"]
        if se>0:
            # Deliberately conservative fixed 9 df (minimum marginal cluster df).
            p=float(2*t_distribution.sf(abs(components["mean_difference"]/se),df=9))
        else:
            p=1. if components["mean_difference"]==0 else None
        loo_t=[float(np.delete(diff,i,axis=0).mean()) for i in range(10)]
        loo_e=[float(np.delete(diff,i,axis=1).mean()) for i in range(10)]
        lo,hi=np.quantile((xmean-ymean)[:,j],[.025,.975])
        metric.append(dict(family=f,sample_n=n,method_a=a,method_b=b,
          metric=m,bootstrap_CI95_lower_absolute=float(lo),
          bootstrap_CI95_upper_absolute=float(hi),
          crossed_t9_p_sensitivity=p,
          leave_train_one_out_all_same_sign=bool(all(v>0 for v in loo_t) or all(v<0 for v in loo_t)),
          leave_eval_one_out_all_same_sign=bool(all(v>0 for v in loo_e) or all(v<0 for v in loo_e)),
          training_loo_min=float(min(loo_t)),training_loo_max=float(max(loo_t)),
          evaluation_loo_min=float(min(loo_e)),evaluation_loo_max=float(max(loo_e)),
          **components))
    return metric,list(directional.values())

def block(f,n,root,out,B):
    require(f in FAMILIES and n in SIZES,"Invalid frozen R1 block identity")
    path=root/"heldout"/f"{f}-n{n}"/"candidate_by_eval.csv"
    require(path.exists(),"Absent original R1 block: "+str(path))
    arrays=matrices(pd.read_csv(path))
    rows=[];joint=[]
    for a,b in PAIRS:
        r,j=score_pair(f,n,a,b,arrays,B)
        rows.extend(r);joint.extend(j)
    require(len(rows)==12 and len(joint)==12,"Incomplete crossed sensitivity block")
    out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(out/"crossed_inference.csv",index=False)
    pd.DataFrame(joint).to_csv(out/"joint_mse_q95.csv",index=False)
    (out/"provenance.json").write_text(json.dumps({
       "source":str(path),"source_sha256":digest(path),"family":f,"sample_n":n,
       "original_heldout_seeds":list(range(10,20)),"frozen_training_seeds":list(range(10)),
       "bootstrap_replicates":B,"bootstrap_axes":"training_seed_and_evaluation_seed_paired",
       "training_seed_new_samples_generated":False,
       "heldout_scoring_reexecuted":False,
       "notes":["Posthoc sensitivity, original confirmatory inference unchanged.",
                "Crossed variance components are balanced random-intercept moments; small cluster n limits accuracy.",
                "Joint lower bounds are Bonferroni for two metrics within ONE direction/pair, not global 216-test FWER.",
                "Thresholds 1% and 5% are posthoc sensitivity probes, not prespecified success rules.",
                "Scenarios are fixed; inference does not generalize to unstudied scenarios.",
                "Crossed bootstrap quantifies between-seed sampling only, NOT replicate-level Q95 Monte Carlo uncertainty.",
                "Nominal CI coverage cannot be estimated without known-truth independent null/outer replay."]},indent=2)+"\n")
    print("R1_CROSSED_BLOCK_PASS",f,n,len(rows),len(joint),flush=True)

def finalize(root,out):
    parts=[];joints=[];inputs=[]
    for f in FAMILIES:
        for n in SIZES:
            sub=root/"blocks"/f"{f}-n{n}"
            for name in ("crossed_inference.csv","joint_mse_q95.csv","provenance.json"):
                require((sub/name).stat().st_size>0,"Missing sensitivity shard: "+str(sub/name))
                inputs.append(sub/name)
            v=pd.read_csv(sub/"crossed_inference.csv")
            j=pd.read_csv(sub/"joint_mse_q95.csv")
            require(len(v)==12 and len(j)==12 and set(v.family)=={f} and set(v.sample_n)=={n},
               "Incomplete block output")
            parts.append(v);joints.append(j)
    main=pd.concat(parts,ignore_index=True);joint=pd.concat(joints,ignore_index=True)
    require(len(main)==216 and len(joint)==216,"Expected 216 metric and 216 directional joint panels")
    k=["family","sample_n","method_a","method_b","metric"]
    require(not main.duplicated(k).any(),"Duplicate 216 comparison identity")
    reference=pd.read_csv("R1/runs/"+PRIMARY+"/all_pairwise_global_holm.csv")
    require(len(reference)==216,"Reference confirmatory comparison missing")
    joined=main.merge(reference[k+["difference","p","holm_p_global"]],on=k,validate="one_to_one",suffixes=("","_original"))
    require(len(joined)==216,"Original R1 contrasts not reproducibly matched")
    require(np.allclose(joined.mean_difference,joined.difference,rtol=1e-9,atol=1e-12),
      "Crossed cell-wise contrast disagrees with preserved R1 mean")
    require(joined.crossed_t9_p_sensitivity.notna().all(),"Zero/invalid crossed variance in one or more contrasts")
    main["crossed_t9_holm_sensitivity"]=holm(main.crossed_t9_p_sensitivity.to_numpy())
    require(len(main)==216,"Missing adjusted crossed effects")
    out.mkdir(parents=True,exist_ok=True)
    main.to_csv(out/"crossed_hierarchical_inference_216.csv",index=False)
    joint.to_csv(out/"two_metric_joint_practical_216_directions.csv",index=False)
    diagnostics={
      "frozen_weight_vectors":720,"crossed_training_seeds":10,"crossed_heldout_seeds":10,
      "scenario_support_count":241,"strata":18,"compared_metric_contrasts":216,
      "joint_pair_directions":216,"bootstrap_iterations_per_pair":BOOTSTRAP_ITERATIONS,
      "original_parametric_holm_supported":int((joined.holm_p_global<.05).sum()),
      "crossed_t9_holm_supported_sensitivity":int((main.crossed_t9_holm_sensitivity<.05).sum()),
      "crossed_variance_components_with_training_zero_boundary":int(main.truncated_training_component.sum()),
      "crossed_variance_components_with_eval_zero_boundary":int(main.truncated_evaluation_component.sum()),
      "within_pair_joint_Bonferroni_both_gt_0":int(joint.joint_positive_bonferroni_95_within_pair.sum()),
      "within_pair_joint_Bonferroni_both_gt_1pct":int(joint.joint_onepct_bonferroni_95_within_pair.sum()),
      "within_pair_joint_Bonferroni_both_gt_5pct":int(joint.joint_fivepct_bonferroni_95_within_pair.sum()),
      "note":"Sensitivity only; joint thresholds post hoc; do not treat as confirmatory familywise inference.",
      "CI_coverage_status":"NOT_ESTIMABLE_FROM_EXISTING_10X10_PANEL_WITHOUT_KNOWN_TRUTH_REPLAYS",
      "Q95_replicate_MC_uncertainty_status":"NEEDS_REPLICATE_LEVEL_ARCHIVE_PROBE",
      "deterministic_independent_controls_status":"NEEDS_ARCHIVE_PROBE",
      "full_runtime_tuning_cost_status":"NEEDS_ARCHIVE_PROBE",
    }
    (out/"R1_REVIEWER_SCOPE.md").write_text(
      "# R1 crossed-seed reviewer analysis\n\n"
      "Input: the 18 immutable per-candidate R1 Held Out panels from run "+SOURCE+". "
      "Each 10-by-10 training/evaluation grid is paired across methods, and "
      "both seed dimensions are resampled jointly by axis, with the 241 support scenarios fixed.\n\n"
      "The balanced crossed random-intercept moment estimate uses ten seed groups per axis. "
      "Its t(9) p-values and global Holm column are approximate **sensitivity** diagnostics, "
      "not guaranteed nominal familywise calibration. Percentile bootstrap CIs are also "
      "exploratory with only ten seed groups. A negative estimated variance component "
      "is truncated to zero and flagged per contrast.\n\n"
      "Joint uncertainty compares MSE and Q95 on the SAME bootstrapped seed cells. "
      "Two one-sided lower bounds at 97.5% are Bonferroni-corrected only **within each pair and direction**. "
      "Thresholds 0%, 1%, and 5% were proposed after earlier results existed and are not preregistered. "
      "They cannot substitute for globally corrected multi-pair, selection-aware testing.\n\n"
      "Monte Carlo replicate-level Q95 error, true nominal CI coverage, and "
      "deterministic controls cannot be established from this aggregate panel. "
      "The archive-inspection stage maps available source material for those questions.\n\n"
      "No original simulation, weight optimization, frozen model selection, or scoring is repeated.\n"
    )
    audit_inputs={str(p.relative_to(root)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in inputs}
    diagnostics["inputs"]=audit_inputs
    (out/"SUMMARY.json").write_text(json.dumps(diagnostics,indent=2)+"\n")
    print("R1_CROSSED_SYNTHESIS_PASS",diagnostics["crossed_t9_holm_supported_sensitivity"],flush=True)

def selftest():
    data=np.arange(100,dtype=float).reshape(10,10)*.0001
    z=variance_components(data)
    require(z["crossed_se"]>0 and z["training_variance"]>=0 and z["evaluation_variance"]>=0,
            "Crossed variance formula selftest failure")
    df=pd.DataFrame([dict(training_seed=t,eval_seed=e,method=m,
      mse=1+.002*t+.0001*e+i*.3,q95=2+.004*t+.0001*e+i*.5)
      for t in range(10) for e in range(10,20) for i,m in enumerate(METHODS)])
    arrays=matrices(df)
    r,j=score_pair("normal",200,"ga","de",arrays,200)
    require(len(r)==2 and len(j)==2 and r[0]["mean_difference"]<0,
            "Matched simultaneous metrics selftest failure")
    print("R1_CROSSED_SELFTEST_PASS",flush=True)

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    b=sub.add_parser("block")
    b.add_argument("--family",required=True,choices=FAMILIES)
    b.add_argument("--n",required=True,type=int,choices=SIZES)
    b.add_argument("--source",type=Path,default=Path("R1/runs/"+SOURCE))
    b.add_argument("--output",type=Path,required=True)
    b.add_argument("--bootstrap",type=int,default=BOOTSTRAP_ITERATIONS)
    f=sub.add_parser("finalize")
    f.add_argument("--root",type=Path,required=True)
    f.add_argument("--output",type=Path,required=True)
    sub.add_parser("selftest")
    a=p.parse_args()
    if a.mode=="block":
        require(a.bootstrap>=1000,"At least 1000 crossed resampling replicates required")
        block(a.family,a.n,a.source,a.output,a.bootstrap)
    elif a.mode=="finalize":finalize(a.root,a.output)
    else:selftest()

if __name__=="__main__":main()
