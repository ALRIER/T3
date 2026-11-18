#!/usr/bin/env python3
"""R1 Q1 Stage 12C: independent holdout for simulation-calibrated inference.

PRE-SPECIFIED DECISION:
* Calibration source is frozen original Stage 12B global-null draws (4096).
* Test set uses independently seeded 4096 new crossed-effect synthetic draws
  for each original block, in global null, mixed null and observed-effect modes.
* Compare uncalibrated t9+Holm, empirically calibrated marginal Holm/BH,
  and conservative global minP single-step simultaneous inference.
* Report 95% pointwise and 95% simultaneous known-truth interval coverage.
* Apply calibrated thresholds posthoc to ORIGINAL frozen crossed-seed scores,
  explicitly as conditional sensitivity only, never confirmatory correction.
* No new original DGP Monte Carlo, no reoptimization, no original HPO reselection.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from scipy.stats import binom
from t3_b3_r1_stage12_unified_calibration import (
    FAMILIES,SIZES,METHODS,METRICS,PAIRS,MODES,ALPHA,PRIMARY,need,hashfile,
    components_from_source,known_truth_means,draw_panel,verify_sources,
    crossed_t9,paired_results,adjust,wilson,dump_json,csvout
)

A=np.asarray([p[0] for p in PAIRS]);B=np.asarray([p[1] for p in PAIRS])
BASE=Path("R1/runs/44340092503")
TCRIT=float(student_t.ppf(.975,9))
REPS=4096
PREREG_SHA="stage12c-calibrated-inference-holdout-v1-20261118"

def deterministic_seed(*parts):
    payload=":".join([PREREG_SHA,*[str(x) for x in parts]])
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8],"little")

def require_baseline():
    need((BASE/"STAGE12B_SHA256_MANIFEST.json").is_file(),
         "Stage12B preserved baseline absent")
    meta=json.loads((BASE/"STAGE12B_SHA256_MANIFEST.json").read_text())
    need(meta["status"]=="PASS_SURROGATE_CONDITIONAL_WITH_FULL_HPO_SELECTION_LIMITATION"
         and meta["independent_synthetic_replays_per_mode"]==4096,
         "Original Stage 12B source is not the fixed predeclared calibration set")
    need((BASE/"synthesis/STAGE12B_SCIENTIFIC_SCOPE.json").is_file(),
         "Original coverage limitations not preserved")
    return meta

def block(args):
    require_baseline()
    x,source,sha=verify_sources(args.family,args.n)
    mu,tr,ev,inter=components_from_source(x)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    results={}
    for mode in MODES:
        truth=known_truth_means(mu,mode)
        rng=np.random.default_rng(deterministic_seed(args.family,args.n,mode))
        zero=abs((truth[A]-truth[B]).reshape(12))<=1e-13
        ps=[];cs=[];selections=[]
        completed=0
        while completed<REPS:
            k=min(128,REPS-completed)
            validation=draw_panel(rng,truth,tr,ev,inter,k)
            p,cover,null=paired_results(validation,truth)
            need(np.array_equal(null,zero),"Known-truth null map changed within block")
            d=(validation[:,:,:,A,:]-validation[:,:,:,B,:]).reshape(k,10,10,12)
            estimates,se,_=crossed_t9(d)
            effects=(truth[A,:]-truth[B,:]).reshape(12)
            normalized=np.divide(np.abs(estimates-effects),se,
                 out=np.where(np.abs(estimates-effects)<=1e-14,0.,np.inf),
                 where=se>0)
            pcenter=2*student_t.sf(normalized,9)
            assert np.array_equal(cover,(normalized<=TCRIT+1e-8).astype(np.uint8)), (
                "Inconsistent original 95 percent CI coverage computation",mode)
            ps.append(p);cs.append(pcenter)
            completed+=k
        p=np.concatenate(ps);pcenter=np.concatenate(cs)
        need(p.shape==(REPS,12) and pcenter.shape==(REPS,12)
             and np.isfinite(p).all() and np.isfinite(pcenter).all(),
             "Invalid independent test-set matrix")
        results[mode+"_p_nominal"]=p
        results[mode+"_p_centered"]=pcenter
        results[mode+"_null"]=zero
    np.savez_compressed(out/"INDEPENDENT_VALIDATION_REPLICATIONS.npz",**results)
    dump_json(out/"INDEPENDENT_VALIDATION_PROVENANCE.json",dict(
        stage="12C",status="INDEPENDENT_HOLDOUT_PASS",source=source,sha256=sha,
        family=args.family,sample_n=args.n,validation_reps_per_mode=REPS,
        modes=list(MODES),seed_rule=PREREG_SHA,
        calibration_draw_source=str(BASE),
        calibration_and_validation_independent_random_generators=True,
        frozen_original_HPO_and_weights_untouched=True,
        selection_scope="fixed four engines; training HPO not replayed"))
    print("STAGE12C_INDEPENDENT_BLOCK_PASS",args.family,args.n,REPS,flush=True)

def cal_from_stage12b():
    require_baseline()
    matrices=[];checks=[]
    for f in FAMILIES:
        for n in SIZES:
            sub=BASE/"blocks"/f"{f}-n{n}"
            provenance=json.loads((sub/"PROVENANCE.json").read_text())
            _,source,sha=verify_sources(f,n)
            need(provenance["sha256"]==sha, "Stage 12B archived original source checksum mismatch")
            with np.load(sub/"CALIBRATION_REPLICATIONS.npz",allow_pickle=False) as z:
                a=z["global_null_p"]
                null=z["global_null_null"]
            need(a.shape==(REPS,12) and np.sum(null)==12 and
                 np.isfinite(a).all(), "Stage 12B null calibration missing")
            matrices.append(a.copy())
            checks.append(dict(family=f,n=n,source_sha256=sha,
                               calibration_file_sha256=hashfile(sub/"CALIBRATION_REPLICATIONS.npz")))
    matrix=np.concatenate(matrices,axis=1)
    need(matrix.shape==(REPS,216),"Stage12B global calibration missing source strata")
    return matrix,checks

def get_validation(root):
    result={m:[] for m in MODES}
    lineage=[]
    for f in FAMILIES:
        for n in SIZES:
            sub=root/"blocks"/f"{f}-n{n}"
            p=json.loads((sub/"INDEPENDENT_VALIDATION_PROVENANCE.json").read_text())
            _,_,sha=verify_sources(f,n)
            need(p["sha256"]==sha and p["status"]=="INDEPENDENT_HOLDOUT_PASS",
                 "Stage12C validation source not found or wrong")
            lineage.append(p)
            with np.load(sub/"INDEPENDENT_VALIDATION_REPLICATIONS.npz",allow_pickle=False) as d:
                for m in MODES:
                    nominal=d[m+"_p_nominal"]
                    centered=d[m+"_p_centered"]
                    null=d[m+"_null"]
                    need(nominal.shape==(REPS,12) and centered.shape==(REPS,12)
                        and null.shape==(12,), "Missing Stage12C synthetic validation row")
                    result[m].append(dict(p=nominal.copy(),pcenter=centered.copy(),null=null.copy()))
    return result,lineage

def empirical_marginal_p(values,sorted_null):
    """Independent calibration: p=(1+#calibration null p <= observed p)/(B+1)."""
    need(values.ndim==2 and sorted_null.shape==(REPS,216) and values.shape[1]==216,
         "Global marginal calibration shape mismatch")
    ans=np.empty(values.shape,float)
    for col in range(216):
        ans[:,col]=(1+np.searchsorted(sorted_null[:,col],values[:,col],side="right"))/(REPS+1)
    return ans

def calibrate_cutoffs(pnull):
    """One-sided 95% order-stat guarantee for estimated 5% global-null FWER."""
    need(pnull.shape==(REPS,216),"Wrong fixed global-null data")
    minimum=np.sort(pnull.min(axis=1))
    k=int(binom.ppf(.05,REPS,ALPHA))
    need(k>0 and k<REPS*.05,"Conservative order-stat calibration invalid")
    # k-th smallest order statistic: with at least 95% confidence, its true
    # lower-tail cumulative probability is <= .05 under independent null draws.
    cutoff=float(minimum[k-1])
    sorted_cols=np.sort(pnull,axis=0)
    return cutoff,k,sorted_cols,minimum

def observed_sensitivity(sorted_cols,minima,global_threshold):
    r=Path("R1/runs/44318493492/analysis/crossed_hierarchical_inference_216.csv")
    source=pd.read_csv(r)
    need(len(source)==216,"Original crossed-seed inferences incomplete")
    rows=[];pvals=[]
    for f in FAMILIES:
        for n in SIZES:
            for a,b in PAIRS:
                for metric in METRICS:
                    match=source[(source.family==f)&(source.sample_n==n)&
                        (source.method_a==METHODS[a])&
                        (source.method_b==METHODS[b])&(source.metric==metric)]
                    need(len(match)==1,"Missing original crossed-seed inference contrast")
                    rows.append(match.iloc[0].to_dict())
                    pvals.append(float(match.crossed_t9_p_sensitivity.iloc[0]))
    original=np.array(pvals)[None,:]
    p_cal=empirical_marginal_p(original,sorted_cols)
    holm=adjust(p_cal,"holm")[0]
    bh=adjust(p_cal,"bh")[0]
    global_minp_adjusted=(1+np.searchsorted(minima,original[0],side="right"))/(REPS+1)
    minpreject=original[0]<=global_threshold
    corrected_crit=sorted_cols[max(0,int(math.floor(.05*REPS))-1),:]
    # Global pointwise critical values are q0.05 of nominal null p-values.
    # A pooled familywise CI uses the conservative minP threshold.
    cal_tcrit=student_t.isf(np.maximum(corrected_crit,1e-15)/2,9)
    global_tcrit=float(student_t.isf(max(global_threshold,1e-15)/2,9))
    final=[]
    for i,row in enumerate(rows):
        se=float(row["crossed_se"])
        delta=float(row["mean_difference"])
        need(np.isfinite(se) and se>0 and np.isfinite(delta),"Original crossed uncertainty malformed")
        rec=dict(family=row["family"],sample_n=int(row["sample_n"]),
                 method_a=row["method_a"],method_b=row["method_b"],metric=row["metric"],
                 original_crossed_mean_difference=delta,
                 original_crossed_se=se,
                 original_t9_unadjusted_p=float(original[0,i]),
                 empirical_surrogate_marginal_p=float(p_cal[0,i]),
                 empirical_surrogate_holm_supported=bool(holm[i]),
                 empirical_surrogate_BH_supported=bool(bh[i]),
                 empirical_global_minP_supported=bool(minpreject[i]),
                 empirical_global_minP_adjusted_p=float(global_minp_adjusted[i]),
                 posthoc_pointwise_calibrated_CI95_low=delta-cal_tcrit[i]*se,
                 posthoc_pointwise_calibrated_CI95_high=delta+cal_tcrit[i]*se,
                 posthoc_familywise_CI95_low=delta-global_tcrit*se,
                 posthoc_familywise_CI95_high=delta+global_tcrit*se,
                 statistical_scope="surrogate conditional diagnostic, not original confirmatory inference")
        final.append(rec)
    return final,dict(observed_method_contrasts=216,
         empirically_calibrated_holm_supported=int(sum(holm)),
         empirically_calibrated_BH_supported=int(sum(bh)),
         globally_calibrated_minP_supported=int(sum(minpreject)),
         scope="posthoc original frozen contrasts, conditional on synthetic DGP only")

def mean_cov_ci(value):
    # 4096 independent aligned synthetic experiments across 216 contrasts,
    # respecting across-contrast dependence when estimating uncertainty.
    a=np.asarray(value,float)
    need(a.ndim==2 and a.shape==(REPS,216),"Wrong pooled coverage shape")
    per_experiment=a.mean(axis=1)
    mean=float(per_experiment.mean())
    se=float(per_experiment.std(ddof=1)/np.sqrt(REPS))
    return mean,max(0.,mean-1.96*se),min(1.,mean+1.96*se)

def finale(args):
    root=Path(args.root)
    pnull,checks=cal_from_stage12b()
    validate,lineage=get_validation(root)
    threshold,rank,sorted_cols,sorted_minima=calibrate_cutoffs(pnull)
    results=[];detailed=[]
    for mode in MODES:
        vals=validate[mode]
        nominal=np.concatenate([d["p"] for d in vals],axis=1)
        pcenter=np.concatenate([d["pcenter"] for d in vals],axis=1)
        true_null=np.concatenate([d["null"] for d in vals])
        need(nominal.shape==(REPS,216) and pcenter.shape==(REPS,216)
              and len(true_null)==216 and np.isfinite(nominal).all()
              and np.isfinite(pcenter).all(),"Invalid holdout total")
        empirical=empirical_marginal_p(nominal,sorted_cols)
        need(np.all((empirical>=0)&(empirical<=1)), "Out of range calibrated p-values")
        expected={"global_null":216,"mixed_null":36,"observed_effect":0}[mode]
        need(int(true_null.sum())==expected,"Incorrect known-truth null subset")
        for policy, decisions in (
            ("original_t9_plus_Holm",adjust(nominal,"holm")),
            ("empirical_marginal_plus_Holm",adjust(empirical,"holm")),
            ("empirical_marginal_plus_BH",adjust(empirical,"bh")),
            ("conservative_single_step_global_minP",nominal<=threshold),
        ):
            false=(decisions & true_null).sum(axis=1)
            true=(decisions & ~true_null).sum(axis=1)
            total=decisions.sum(axis=1)
            false_event=(false>0)
            error_rate=float(np.mean(false_event))
            lo,hi=wilson(int(false_event.sum()),REPS)
            results.append(dict(mode=mode,method=policy,validation_replicates=REPS,
                comparison_count=216,true_null_hypotheses=expected,
                FWER=error_rate,FWER_Wilson95_low=lo,FWER_Wilson95_high=hi,
                FDR=float(np.mean(false/np.maximum(total,1))),
                mean_true_discoveries=float(np.mean(true)),
                mean_false_discoveries=float(np.mean(false)),
                mean_total_discoveries=float(np.mean(total)),
                mean_power=float(np.mean(true)/(216-expected)) if expected<216 else np.nan,
                nominal_alpha=.05,within_surrogate=False if policy=="original_t9_plus_Holm" else True,
                preregistered_calibration_source=str(BASE),scope="independently validated synthetic crossed seed surrogate"))
        calib_cols=np.maximum(sorted_cols[int(math.floor(.05*REPS))-1,:],0)
        calibrated_coverage=np.less_equal(pcenter,1) & (pcenter>=calib_cols[None,:])
        nominal_coverage=pcenter>=.05
        familywise_coverage=(pcenter>=threshold).all(axis=1)
        for label,coverage in [("nominal_t9_pointwise95",nominal_coverage),
                               ("empirical_pointwise95",calibrated_coverage)]:
            m,lo,hi=mean_cov_ci(coverage)
            results.append(dict(mode=mode,method=label,validation_replicates=REPS,
              comparison_count=216,true_null_hypotheses=expected,
              mean_empirical_CI95_coverage=m,
              across_independent_experiments_CI95_low=lo,
              across_independent_experiments_CI95_high=hi,
              scope="independent known-truth verification, empirical surrogate only"))
        cov_rate=float(np.mean(familywise_coverage))
        results.append(dict(mode=mode,method="global_minP_simultaneous95_CI",
            validation_replicates=REPS,comparison_count=216,
            true_null_hypotheses=expected,
            empirical_simultaneous_CI95_coverage=cov_rate,
            simultaneous_CI95_Wilson_low=wilson(int(familywise_coverage.sum()),REPS)[0],
            simultaneous_CI95_Wilson_high=wilson(int(familywise_coverage.sum()),REPS)[1],
            scope="simultaneous fixed-contrast intervals, empirical surrogate only"))
        for i,(f,n) in enumerate(itertools.product(FAMILIES,SIZES)):
            for j,(a,b) in enumerate(PAIRS):
                for metric_i,metric in enumerate(METRICS):
                    z=12*i+2*j+metric_i
                    detailed.append(dict(mode=mode,family=f,sample_n=n,
                       method_a=METHODS[a],method_b=METHODS[b],metric=metric,
                       known_true_null=bool(true_null[z]),replications=REPS,
                       original_t9_CI95_coverage=float(nominal_coverage[:,z].mean()),
                       calibrated_empirical_pointwise_CI95_coverage=
                           float(calibrated_coverage[:,z].mean()),
                       original_t9_false_positive=float((nominal[:,z]<=.05).mean()) if true_null[z] else np.nan,
                       calibrated_marginal_false_positive=float((empirical[:,z]<=.05).mean()) if true_null[z] else np.nan))
    original_rows,original_counts=observed_sensitivity(sorted_cols,sorted_minima,threshold)
    out=root/"synthesis";out.mkdir(parents=True,exist_ok=True)
    csvout(out/"table_RQ1_stage12c_independent_FWER_FDR_and_CI_coverage.csv",results)
    csvout(out/"table_RQ1_stage12c_original_frozen_216_surrogate_corrected.csv",original_rows)
    csvout(out/"table_RQ1_stage12c_individual_648_validation_coverage.csv",detailed)
    critical_summary=dict(
      original_source="R1/runs/44310024979",
      calibration_run="44340092503",calibration_draws=REPS,
      validation_reps_per_regime=REPS,validation_regimes=list(MODES),
      total_family_n_blocks=18,global_comparisons=216,
      conservative_global_minP_critical_p=threshold,
      conservative_null_order_statistic_rank=rank,
      confidence_of_nominal_FWER_cutoff_bound=.95,
      method="Empirical null minimum nominal t9 p; independent calibration and validation",
      original_frozen_contrast_sensitivity=original_counts,
      original_optimizer_and_HPO_reselection_replayed=False,
      fully_selection_aware_original_pipeline_CI_coverage_established=False,
      independence_assumptions="Independent synthetic block innovations conditional on original fitted empirical crossed-effects DGP",
      all_18_calibration_source_hashes=checks,
      source_lineage_sha256={p["family"]+"-"+str(p["sample_n"]):p["sha256"] for p in lineage})
    dump_json(out/"STAGE12C_FINAL_METHOD_AND_LIMITATIONS.json",critical_summary)
    (out/"STAGE12C_RESULTS_FOR_MANUSCRIPT.md").write_text(
      "# Q1 Stage 12C — Independent calibration verification\n\n"
      "This final **frozen-estimand synthetic** calibration compares the original "
      "crossed-t9/Holm method with empirical-null recalibration. "
      "A fixed 4,096-draw global-null calibration panel from Stage 12B and "
      "an independently seeded 4,096-draw Stage 12C holdout panel in each of "
      "three regimes are used, with 18 family/sample-size blocks and 216 tests. "
      "We report pointwise and familywise interval coverage, FWER, FDR, and "
      "the effect on the original frozen contrasts as exploratory sensitivity. "
      "The minP cutoff uses a conservative one-sided 95% binomial order-statistic bound "
      "on its nominal 5% global-null tail, rather than tuning a cutoff against the validation set.\n\n"
      "**Scope boundary:** The surrogate's known truth is constructed from the fixed "
      "original crossed-seed score cells. Its heldout draws have independent innovations "
      "conditional on that fitted empirical distribution. This is NOT a replication of "
      "nested hyperparameter optimization, candidate weight discovery, optimizer training, "
      "nor an empirical proof of full end-to-end selection-aware inference. "
      "The calibrated original significance flags are posthoc and must not supersede "
      "the archived prespecified tests. The original method may be reported as a "
      "sensitivity with its demonstrated null-calibration weakness.\n\n"
      "The numerical outcomes are in the adjacent CSV tables, "
      "and full calibration/validation lineage is preserved in the run manifest.\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d=pd.DataFrame(results)
    keys=["original_t9_plus_Holm","empirical_marginal_plus_Holm",
          "empirical_marginal_plus_BH","conservative_single_step_global_minP"]
    blocks=[d[(d["mode"]==mode)&(d["method"].isin(keys))].set_index("method").reindex(keys)
            for mode in ("global_null","mixed_null")]
    fig,ax=plt.subplots(figsize=(9.2,4.8))
    x=np.arange(4)
    ax.bar(x-.18,blocks[0].FWER.to_numpy(),width=.36,color="#486780",label="Global null")
    ax.bar(x+.18,blocks[1].FWER.to_numpy(),width=.36,color="#8A9B70",label="Mixed null")
    ax.axhline(.05,color="#333333",linestyle="--",linewidth=1.5,label="Nominal 5%")
    ax.set_xticks(x,["Uncalibrated\nHolm","Calibrated\nHolm","Calibrated\nBH","Conservative\nminP"])
    ax.set_ylabel("Independent validation FWER")
    ax.set_title("Familywise error under known-truth surrogate calibration")
    ax.legend();fig.tight_layout()
    fig.savefig(out/"figure_RQ1_stage12c_FWER_calibration.svg")
    fig.savefig(out/"figure_RQ1_stage12c_FWER_calibration.png",dpi=180)
    plt.close(fig)
    coverage=d[(d["mode"]=="global_null")&
              (d["method"].isin(["nominal_t9_pointwise95","empirical_pointwise95"]))]
    fig,ax=plt.subplots(figsize=(7.5,4.2))
    ax.bar(["Nominal t9","Empirically calibrated"],
            coverage.mean_empirical_CI95_coverage.to_numpy(),
            color=["#486780","#8A9B70"])
    ax.axhline(.95,color="#333333",linestyle="--",label="Nominal 95%")
    ax.set_ylim(.85,1.0);ax.set_ylabel("Independent validation CI coverage")
    ax.set_title("Pointwise interval coverage, synthetic global null")
    ax.legend();fig.tight_layout()
    fig.savefig(out/"figure_RQ1_stage12c_pointwise_coverage.svg")
    fig.savefig(out/"figure_RQ1_stage12c_pointwise_coverage.png",dpi=180)
    plt.close(fig)
    manifest=[]
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name!="STAGE12C_SHA256_MANIFEST.json" and p.name!="RUN_STATUS.md":
            manifest.append(dict(path=p.relative_to(root).as_posix(),
                bytes=p.stat().st_size,sha256=hashfile(p)))
    dump_json(root/"STAGE12C_SHA256_MANIFEST.json",dict(
      status="INDEPENDENT_SURROGATE_CALIBRATION_COMPLETE",
      phase="12C",calibration_source="44340092503",files=manifest,
      full_original_nested_HPO_replayed=False,
      original_source_results_unchanged=True))
    print("STAGE12C_FINAL_INDEPENDENT_VALIDATION_PASS",
          "threshold",threshold,"outcomes",len(results),"files",len(manifest),flush=True)

def selftest():
    rng=np.random.default_rng(789)
    null=rng.uniform(size=(REPS,216))
    c,rank,sorted_cols,minima=calibrate_cutoffs(null)
    need(0<c<.05 and 1<rank<REPS*.05,"Bad conservative null quantile")
    pp=np.array([[0.00002,.5]*108])
    empir=empirical_marginal_p(pp,sorted_cols)
    need(empir.shape==(1,216) and np.all(empir>=1/(REPS+1)),"Bad empirical p-values")
    need(empir[0,0]<empir[0,1],"Empirical p inversion")
    need(wilson(200,400)[0]<.5<wilson(200,400)[1],"Wilson CI broken")
    print("STAGE12C_STATISTICAL_SELFTEST_PASS",rank,c,flush=True)

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="action",required=True)
    sub.add_parser("selftest")
    a=sub.add_parser("block")
    a.add_argument("--family",choices=FAMILIES,required=True)
    a.add_argument("--n",choices=SIZES,type=int,required=True)
    a.add_argument("--output",required=True)
    a=sub.add_parser("finalize");a.add_argument("--root",required=True)
    args=parser.parse_args()
    if args.action=="selftest":selftest()
    elif args.action=="block":block(args)
    else:finale(args)

if __name__=="__main__":main()
