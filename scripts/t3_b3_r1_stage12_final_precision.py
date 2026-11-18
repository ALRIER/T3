#!/usr/bin/env python3
"""Q1 Stage 12 FINAL frozen-estimand calibration precision, with independent holdout.

Augments fixed earlier 4096 null calibration draws with 16384 new null draws.
Retains without re-running the separately seeded Stage 12C independent 4096
validation replicates in three known-truth regimes for all 18 blocks.
Empirical p-value resolution rises from ~2.44e-4 to ~4.88e-5, sufficient
to evaluate a global Holm gate across 216 comparisons. The minP and
selection-scope limitations remain explicitly archived.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import binom
from t3_b3_r1_stage12_unified_calibration import (
  FAMILIES,SIZES,METHODS,METRICS,PAIRS,MODES,ALPHA,need,hashfile,
  components_from_source,known_truth_means,draw_panel,verify_sources,
  paired_results,adjust,wilson,dump_json,csvout)
from t3_b3_r1_stage12c_independent_calibration import (
  BASE,cal_from_stage12b,get_validation,mean_cov_ci)

CALIBRATION_EXTRA=16384
ORIGINAL_CALIBRATION=4096
TOTAL_CALIBRATION=20480
VALIDATION=4096
VALIDATION_RUN=Path("R1/runs/44343019150")
SEED_SCHEME="R1-stage12-final-null-extension-v1-20261118-fixed"
A=np.array([x for x,y in PAIRS]);B=np.array([y for x,y in PAIRS])

def saved_sources():
    need((VALIDATION_RUN/"STAGE12C_SHA256_MANIFEST.json").is_file(),
         "Independent test set must be completely archived before precision extension")
    obj=json.loads((VALIDATION_RUN/"STAGE12C_SHA256_MANIFEST.json").read_text())
    need(obj["status"]=="INDEPENDENT_SURROGATE_CALIBRATION_COMPLETE",
         "Previous stage 12C scientific validation was not complete")

def null_block(args):
    saved_sources()
    x,path,sha=verify_sources(args.family,args.n)
    source_mean,tr,ev,inter=components_from_source(x)
    nullmu=known_truth_means(source_mean,"global_null")
    rng=np.random.default_rng(int.from_bytes(hashlib.sha256(
        (SEED_SCHEME+":"+args.family+":"+str(args.n)).encode()).digest()[:8],"little"))
    batches=[]
    for beginning in range(0,CALIBRATION_EXTRA,128):
        k=min(128,CALIBRATION_EXTRA-beginning)
        p,_,is_null=paired_results(draw_panel(rng,nullmu,tr,ev,inter,k),nullmu)
        need(is_null.all() and p.shape==(k,12),"Unexpected null signature")
        batches.append(p)
    a=np.concatenate(batches,axis=0)
    need(a.shape==(CALIBRATION_EXTRA,12) and np.isfinite(a).all() and
         np.all((a>=0)&(a<=1)),"Null precision extension lacks required rows")
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/"EXTRA_INDEPENDENT_NULL_DRAWS.npz",nominal_p=a)
    dump_json(out/"CALIBRATION_LINEAGE.json",dict(
      stage="12_FINAL_PRECISION",family=args.family,n=args.n,
      original_sha256=sha,original_frozen_score=path,
      new_null_calibration_replicates=CALIBRATION_EXTRA,
      previous_calibration_replicates=ORIGINAL_CALIBRATION,
      previous_calibration_run=str(BASE),
      independent_validation_run=str(VALIDATION_RUN),
      seed_scheme=SEED_SCHEME,
      no_HPO_training_or_original_model_reexecution=True))
    print("STAGE12_GLOBAL_NULL_PRECISION_16384_PASS",args.family,args.n,flush=True)

def full_null_calibration(root):
    old,old_sources=cal_from_stage12b()
    saved_sources()
    extended=[];checks=[]
    for f in FAMILIES:
        for n in SIZES:
            sub=root/"blocks"/f"{f}-n{n}"
            meta=json.loads((sub/"CALIBRATION_LINEAGE.json").read_text())
            _,_,sha=verify_sources(f,n)
            need(meta["original_sha256"]==sha and meta["seed_scheme"]==SEED_SCHEME,
                 "Unverified new null source")
            with np.load(sub/"EXTRA_INDEPENDENT_NULL_DRAWS.npz",allow_pickle=False) as npz:
                p=npz["nominal_p"]
            need(p.shape==(CALIBRATION_EXTRA,12) and np.isfinite(p).all(),
                 "Missing extended original family sample null calibration")
            extended.append(p.copy())
            checks.append(dict(family=f,n=n,original_sha256=sha,
                               extension_sha256=hashfile(sub/"EXTRA_INDEPENDENT_NULL_DRAWS.npz")))
    extra=np.concatenate(extended,axis=1)
    full=np.concatenate([old,extra],axis=0)
    need(full.shape==(TOTAL_CALIBRATION,216),"Wrong original 216-test calibration size")
    return full,old_sources,checks

def empirical_p(p,sorted_null):
    need(sorted_null.shape==(TOTAL_CALIBRATION,216) and p.shape[1]==216,
         "Invalid 20,480-draw empirical marginal calibration")
    out=np.empty(p.shape,float)
    for i in range(216):
        out[:,i]=(np.searchsorted(sorted_null[:,i],p[:,i],side="right")+1)/(TOTAL_CALIBRATION+1)
    return out

def cutoffs(pnull):
    need(pnull.shape==(TOTAL_CALIBRATION,216),"Incomplete null calibration matrix")
    null_min=np.sort(pnull.min(axis=1))
    rank=int(binom.ppf(.05,TOTAL_CALIBRATION,.05))
    need(1<rank<int(TOTAL_CALIBRATION*.05),"Global conservative familywise cutoff rank invalid")
    cutoff=float(null_min[rank-1])
    sort_cols=np.sort(pnull,axis=0)
    need(0<cutoff<.05,"Original 216-test null cutoff invalid")
    return cutoff,rank,sort_cols,null_min

def observed_216(nullcols,minima,globalcut):
    source=Path("R1/runs/44318493492/analysis/crossed_hierarchical_inference_216.csv")
    x=pd.read_csv(source)
    need(len(x)==216,"Original independent crossed-seed evidence not complete")
    found=[]
    for f in FAMILIES:
        for n in SIZES:
            for a,b in PAIRS:
                for metric in METRICS:
                    one=x[(x.family==f)&(x.sample_n==n)&
                         (x.method_a==METHODS[a])&(x.method_b==METHODS[b])&
                         (x.metric==metric)]
                    need(len(one)==1,"Missing original 216 contrast")
                    found.append(one.iloc[0].to_dict())
    pp=np.array([float(v["crossed_t9_p_sensitivity"]) for v in found])[None,:]
    empirical=empirical_p(pp,nullcols)[0]
    holm=adjust(empirical[None,:],"holm")[0]
    bh=adjust(empirical[None,:],"bh")[0]
    minp=pp[0]<=globalcut
    minp_adj=(1+np.searchsorted(minima,pp[0],side="right"))/(TOTAL_CALIBRATION+1)
    critical=np.sort(nullcols,axis=0)[int(.05*TOTAL_CALIBRATION)-1,:]
    import scipy.stats as ss
    tcrit=ss.t.isf(np.clip(critical,1e-14,1.0)/2,df=9)
    tcrit_global=float(ss.t.isf(globalcut/2,df=9))
    result=[]
    for i,row in enumerate(found):
        mean=float(row["mean_difference"]);se=float(row["crossed_se"])
        need(np.isfinite(mean) and np.isfinite(se) and se>0,"Original crossed SE not measurable")
        result.append(dict(family=row["family"],sample_n=int(row["sample_n"]),
          method_a=row["method_a"],method_b=row["method_b"],metric=row["metric"],
          original_crossed_mean_difference=mean,original_crossed_se=se,
          original_unadjusted_t9_p=float(pp[0,i]),
          surrogate_empirical_marginal_p=float(empirical[i]),
          posthoc_empirical_marginal_Holm_support=bool(holm[i]),
          posthoc_empirical_marginal_BH_support=bool(bh[i]),
          posthoc_empirical_global_minP_support=bool(minp[i]),
          posthoc_empirical_global_minP_adjusted_p=float(minp_adj[i]),
          calibrated_pointwise_CI95_low=mean-tcrit[i]*se,
          calibrated_pointwise_CI95_high=mean+tcrit[i]*se,
          calibrated_simultaneous_216_CI95_low=mean-tcrit_global*se,
          calibrated_simultaneous_216_CI95_high=mean+tcrit_global*se,
          estimated_from_independent_null_calibration_draws=TOTAL_CALIBRATION,
          original_experiment_confirmatory_inference=False,
          note="Frozen-estimand synthetic surrogate sensitivity; original HPO and weights not reselected"))
    flags=dict(contrasts=216,empirical_marginal_holm_supported=int(np.sum(holm)),
               empirical_marginal_BH_supported=int(np.sum(bh)),
               conservative_global_minP_supported=int(np.sum(minp)))
    return result,flags

def aggregate(args):
    root=Path(args.root)
    null,old_checks,new_checks=full_null_calibration(root)
    cutoff,rank,nullcols,nullmin=cutoffs(null)
    val,validation_lineage=get_validation(VALIDATION_RUN)
    output=[];detailed=[]
    for mode in MODES:
        parts=val[mode]
        p=np.concatenate([r["p"] for r in parts],axis=1)
        center=np.concatenate([r["pcenter"] for r in parts],axis=1)
        nullmask=np.concatenate([r["null"] for r in parts])
        need(p.shape==(VALIDATION,216) and center.shape==p.shape and
             nullmask.shape==(216,),"Independent validation input corrupt")
        need(int(np.sum(nullmask))=={"global_null":216,"mixed_null":36,"observed_effect":0}[mode],
             "Known-truth regime mismatch")
        calibrated=empirical_p(p,nullcols)
        policies=[
          ("original_nominal_t9_Holm",adjust(p,"holm")),
          ("empirical_marginal_Holm",adjust(calibrated,"holm")),
          ("empirical_marginal_BH",adjust(calibrated,"bh")),
          ("conservative_global_minP",p<=cutoff),
        ]
        for label,decision in policies:
            false=np.sum(decision & nullmask,axis=1)
            true=np.sum(decision & (~nullmask),axis=1)
            fwer=float(np.mean(false>0))
            discoveries=np.sum(decision,axis=1)
            fdp=false/np.maximum(discoveries,1)
            lo,hi=wilson(int(np.sum(false>0)),VALIDATION)
            fdr=float(np.mean(fdp))
            sefdp=float(np.std(fdp,ddof=1)/np.sqrt(VALIDATION))
            output.append(dict(regime=mode,method=label,
              calibration_draws=TOTAL_CALIBRATION,independent_validation_draws=VALIDATION,
              original_contrasts=216,known_true_nulls=int(np.sum(nullmask)),
              false_discovery_rate=fdr,FDR_95CI_low=max(0.,fdr-1.96*sefdp),
              FDR_95CI_high=min(1.,fdr+1.96*sefdp),
              familywise_error_rate=fwer,FWER_Wilson95_low=lo,FWER_Wilson95_high=hi,
              mean_true_discoveries=float(np.mean(true)),
              mean_false_discoveries=float(np.mean(false)),
              power=float(np.mean(true)/(216-int(np.sum(nullmask)))) if int(np.sum(nullmask))<216 else np.nan,
              science_scope="Known-truth surrogate conditional on fixed archived candidate score grids"))
        pointwise_empirical_cutoff=nullcols[int(TOTAL_CALIBRATION*.05)-1,:]
        corrected=(center>=pointwise_empirical_cutoff[None,:])
        nominal=(center>=.05)
        simultaneous=np.all(center>=cutoff,axis=1)
        for name,cov in [("original_nominal_pointwise95_CI",nominal),
                         ("calibrated_pointwise95_CI",corrected)]:
            mean,lo,hi=mean_cov_ci(cov)
            output.append(dict(regime=mode,method=name,
              calibration_draws=TOTAL_CALIBRATION,independent_validation_draws=VALIDATION,
              original_contrasts=216,known_true_nulls=int(np.sum(nullmask)),
              average_true_95CI_coverage=mean,coverage_CI95_lower=lo,coverage_CI95_upper=hi,
              science_scope="Known-truth surrogate conditional on fixed archived candidate score grids"))
        sim=float(np.mean(simultaneous))
        lo,hi=wilson(int(np.sum(simultaneous)),VALIDATION)
        output.append(dict(regime=mode,method="global_minP_simultaneous_216_CI95",
          calibration_draws=TOTAL_CALIBRATION,independent_validation_draws=VALIDATION,
          original_contrasts=216,known_true_nulls=int(np.sum(nullmask)),
          familywise_simultaneous_CI_coverage=sim,simultaneous_CI_Wilson95_low=lo,
          simultaneous_CI_Wilson95_high=hi,
          science_scope="Known-truth surrogate conditional on fixed archived candidate score grids"))
        for bidx,(f,n) in enumerate(itertools.product(FAMILIES,SIZES)):
            for pidx,(a,b) in enumerate(PAIRS):
                for midx,metric in enumerate(METRICS):
                    ix=12*bidx+2*pidx+midx
                    detailed.append(dict(regime=mode,family=f,sample_n=n,
                        method_a=METHODS[a],method_b=METHODS[b],metric=metric,
                        known_true_null=bool(nullmask[ix]),replications=VALIDATION,
                        nominal_pointwise_CI95_coverage=float(np.mean(nominal[:,ix])),
                        calibrated_pointwise_CI95_coverage=float(np.mean(corrected[:,ix])),
                        independent_source_SHA256=next(v["sha256"] for v in validation_lineage
                            if v["family"]==f and v["sample_n"]==n)))
    orig_rows,orig_summary=observed_216(nullcols,nullmin,cutoff)
    data=pd.DataFrame(output)
    gate=data[(data.regime.isin(["global_null","mixed_null"]))&
              (data.method=="conservative_global_minP")]
    need(len(gate)==2,"Missing global and mixed-null independent FWER checks")
    coverage=data[(data.method=="calibrated_pointwise95_CI")]
    need(len(coverage)==3,"Missing independently validated 3 regime CI coverage")
    # Strict pass gate uses upper 95% Wilson for FWER and calibrated
    # coverage within ±1 percentage point of nominal under independent replay.
    corrected_FWER_gate=bool((gate.FWER_Wilson95_high<=.05).all())
    corrected_CI_gate=bool(coverage.average_true_95CI_coverage.between(.94,.96).all())
    out=root/"synthesis";out.mkdir(parents=True,exist_ok=True)
    csvout(out/"Q1_STAGE12_FINAL_independent_FWER_FDR_CI_validation.csv",output)
    csvout(out/"Q1_STAGE12_FINAL_original_216_frozen_contrasts_calibrated.csv",orig_rows)
    csvout(out/"Q1_STAGE12_FINAL_648_contrast_pointwise_coverage.csv",detailed)
    meta=dict(stage="Q1_12_FINAL_PRECISION_VERIFIED",
      source_original_scores="R1/runs/44310024979",
      stage12B_calibration_source=str(BASE),stage12C_independent_validation=str(VALIDATION_RUN),
      earlier_null_calibration_draws=ORIGINAL_CALIBRATION,
      additional_null_calibration_draws=CALIBRATION_EXTRA,
      total_null_calibration_draws=TOTAL_CALIBRATION,
      independent_holdout_validation_draws_per_regime=VALIDATION,
      original_contrasts=216,family_n_blocks=18,
      conservative_minP_cutoff_p=cutoff,
      conservative_one_sided_95pct_order_statistic_rank=rank,
      validation_global_and_mixed_null_FWER_95CI_upper_at_most_5pct=corrected_FWER_gate,
      calibrated_pointwise_95CI_coverage_within_94_96pct=corrected_CI_gate,
      original_frozen_contrast_sensitivity=orig_summary,
      full_original_HPO_and_weight_selection_inference_calibrated=False,
      conditional_surrogate_inference_calibration_complete=
          bool(corrected_FWER_gate and corrected_CI_gate),
      original_primary_R1_results_unmodified=True,
      hypothesis_scope="Preexisting fixed four-method contrast estimands only",
      assumptions=[
        "Independent synthetic trials at global experiment level conditional on empirical crossed-effects surrogate",
        "Subset-pivotal joint distribution of t9 null contrast vectors under null and mixed-null shifts in this DGP",
        "No repeat of original nested hyperparameter search or optimizer-selected weight vectors",
        "Calibrated p-values reported as exploratory original-data sensitivity not preregistered confirmatory tests",
        "No causal generalization beyond 241 observed support scenarios or unstudied distributions",
        "Holm and BH operate on empirical marginal calibration p-values; minP controls global family under surrogates"],
      lineage_original_sha256=old_checks,precision_extension_sha256=new_checks)
    dump_json(out/"Q1_STAGE12_FINAL_AUDIT_AND_DECISION.json",meta)
    (out/"Q1_STAGE12_FINAL_PUBLICATION_INTERPRETATION.md").write_text(
      "# Q1 Stage 12 final calibration decision\n\n"
      "The nominal crossed-seed t9+Holm test failed a synthetic global-null "
      "FWER calibration audit. We corrected the known-truth synthetic inference "
      "on the archived **frozen method estimands** using empirically calibrated "
      "null distributions and a conservative order-statistic global minP "
      "threshold. The original 4,096 training-null replicates were supplemented "
      "with 16,384 **new, separately seeded** null calibration replicates for "
      "each of 18 population/sample-size blocks, providing 20,480 null "
      "replicates for 216 contrasts. The prior, disjoint 4,096-replicate "
      "validation set was reused without re-running, independently testing "
      "global and mixed nulls, and original-effect alternatives.\n\n"
      f"Within-model global and mixed-null independent 5% FWER gate: "
      f"**{'PASS' if corrected_FWER_gate else 'NOT PASS'}**. "
      f"Independent pointwise 95% coverage gate: "
      f"**{'PASS' if corrected_CI_gate else 'NOT PASS'}**.\n\n"
      "Interpretation must remain conditional: model-based synthetic checks "
      "do **not** validate nominal error/coverage for the full original "
      "optimizer training, nested HPO and weight-selection process. "
      "Original R1 confirmatory tests were not changed; all 216 adjusted "
      "original-contrast sensitivity flags are explicitly posthoc. "
      "Do not claim distribution-free FWER or fully selection-aware "
      "coverage in the journal manuscript.\n\n"
      "Use the accompanying 216-contrast, 648-contrast, global table, "
      "and exact source lineage for transparent Methods/Results reporting.\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sel=data[(data.regime=="global_null")&
             (data.method.isin(["original_nominal_t9_Holm","empirical_marginal_Holm",
                                "empirical_marginal_BH","conservative_global_minP"]))]
    names=["Original t9\nHolm","Calibrated\nHolm","Calibrated\nBH","Calibrated\nglobal minP"]
    fig,ax=plt.subplots(figsize=(8.3,4.4))
    ax.bar(names,sel.familywise_error_rate.to_numpy(),color=["#7D726D","#486780","#9DAE8B","#647F76"])
    ax.axhline(.05,color="#333333",linestyle="--",label="Nominal 5% FWER")
    ax.set_ylabel("Independent global-null false-positive probability")
    ax.set_title("Q1 Stage 12 — Calibrating global statistical error")
    ax.legend();fig.tight_layout()
    fig.savefig(out/"Q1_STAGE12_FINAL_FWER.svg")
    fig.savefig(out/"Q1_STAGE12_FINAL_FWER.png",dpi=180)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.7,4.3))
    sub=data[(data.regime=="global_null")&
       (data.method.isin(["original_nominal_pointwise95_CI","calibrated_pointwise95_CI"]))]
    ax.bar(["Original t9","Calibrated empirical"],
           sub.average_true_95CI_coverage.to_numpy(),color=["#486780","#647F76"])
    ax.axhline(.95,color="#333333",linestyle="--",label="Nominal 95%")
    ax.set_ylim(.88,1.00);ax.set_ylabel("Independent known-truth CI coverage")
    ax.set_title("Q1 Stage 12 — Calibrated marginal interval coverage")
    ax.legend();fig.tight_layout()
    fig.savefig(out/"Q1_STAGE12_FINAL_POINTWISE_COVERAGE.svg")
    fig.savefig(out/"Q1_STAGE12_FINAL_POINTWISE_COVERAGE.png",dpi=180)
    plt.close(fig)
    files=[]
    for file in sorted(root.rglob("*")):
        if file.is_file() and file.name not in ("Q1_STAGE12_FINAL_SHA256_MANIFEST.json","RUN_STATUS.md"):
            files.append(dict(path=file.relative_to(root).as_posix(),
                         sha256=hashfile(file),bytes=file.stat().st_size))
    dump_json(root/"Q1_STAGE12_FINAL_SHA256_MANIFEST.json",dict(
       stage="12_FINAL_PRECISION",status="PASS" if corrected_FWER_gate and corrected_CI_gate
                                else "FINISHED_WITH_SCIENTIFIC_GATE_NOT_PASSED",
       validation_complete=True,conditional_only=True,
       original_optimizer_training_and_HPO_selection_not_replayed=True,
       files=files))
    print("R1_Q1_STAGE12_PRECISION_VALIDATION_FINISHED",
          "minP",cutoff,"FWER_gate",corrected_FWER_gate,
          "CI_gate",corrected_CI_gate,orig_summary,flush=True)

def selftest():
    test=np.random.default_rng(74).uniform(size=(TOTAL_CALIBRATION,216))
    cutoff,rank,sorted_cols,minima=cutoffs(test)
    need(rank>900 and rank<1050 and 0<cutoff<.01,
         "Conservative finite-calibration order-statistic rule failed")
    values=np.array([[1e-10]+[.7]*215])
    p=empirical_p(values,sorted_cols)
    need(p.shape==(1,216) and p[0,0]<=1/(TOTAL_CALIBRATION+1)+1e-10,
         "Calibrated 216-test Holm resolution remains insufficient")
    need(p[0,0]<.05/216,
         "Insufficient Monte Carlo p resolution for 216 global Holm contrasts")
    print("Q1_STAGE12_FINAL_20480_CALIBRATION_TEST_PASS",rank,flush=True)

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="action",required=True)
    sub.add_parser("selftest")
    c=sub.add_parser("block")
    c.add_argument("--family",choices=FAMILIES,required=True)
    c.add_argument("--n",type=int,choices=SIZES,required=True)
    c.add_argument("--output",required=True)
    c=sub.add_parser("finalize");c.add_argument("--root",required=True)
    a=parser.parse_args()
    if a.action=="selftest":selftest()
    elif a.action=="block":null_block(a)
    else:aggregate(a)
if __name__=="__main__":main()
