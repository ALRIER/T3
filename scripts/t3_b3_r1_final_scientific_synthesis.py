#!/usr/bin/env python3
"""RQ1 final, strictly archive-backed reviewer synthesis.

Family stage: reduce original independently evaluated 10x10 candidate scores,
Q95 conditional Monte Carlo precision, frozen non-evolutionary comparisons,
optimizer cost, and training-to-HeldOut transfer.

Final stage: globally studentized maxT sign-flip diagnostic preserving method/
metric pairing per (family,n,evaluation seed), and manuscript-ready evidence.

This is POSTHOC sensitivity. It does not establish nominal CI coverage,
selection-aware error control or causal/equivalent optimization budgets.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
SIZES=(200,1000,3000)
METHODS=("ga","nsga2","de","dirichlet")
PAIRS=tuple(itertools.combinations(METHODS,2))
METRICS=("mse","q95")
RBASE=Path("R1/runs")
SOURCE_R1="44310024979"
ORIG_R1="44307352615"
CROSSED_R1="44318493492"
RECOVERED_R1="44322411124"
REPS=8192

def require(ok,why):
    if not ok:raise RuntimeError(why)
def hashfile(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    require(Path(p).is_file(),"Missing previously preserved scientific file: "+str(p))
    return pd.read_csv(p)
def boolval(x):
    if isinstance(x,str):return x.strip().lower() in ("true","1")
    return bool(x)

def family_stage(family,out):
    require(family in FAMILIES,"Unregistered family")
    differences=[];tiles=[];checked={}
    prior=read(RBASE/ORIG_R1/"all_pairwise_global_holm.csv")
    controls=read(RBASE/RECOVERED_R1/"reviewer_synthesis"/"deterministic_controls_original_heldout_global_holm.csv")
    q95=read(RBASE/RECOVERED_R1/"reviewer_synthesis"/"q95_mc_uncertainty_all_108_method_strata.csv")
    cost=read(RBASE/RECOVERED_R1/"reviewer_synthesis"/"original_frozen_optimizer_cost_720.csv")
    gap=read(RBASE/SOURCE_R1/"synthesis"/"discovery_vs_heldout_rank_and_gap.csv")
    pareto=read(RBASE/SOURCE_R1/"synthesis"/"mse_q95_pareto_tradeoff.csv")
    joint=read(RBASE/CROSSED_R1/"analysis"/"two_metric_joint_practical_216_directions.csv")
    crossed=read(RBASE/CROSSED_R1/"analysis"/"crossed_hierarchical_inference_216.csv")
    for n in SIZES:
        candidate_path=RBASE/SOURCE_R1/"heldout"/f"{family}-n{n}"/"candidate_by_eval.csv"
        candidates=read(candidate_path)
        require(len(candidates)==400 and
            not candidates.duplicated(["method","training_seed","eval_seed"]).any() and
            set(candidates.method)==set(METHODS) and
            set(candidates.training_seed)==set(range(10)) and
            set(candidates.eval_seed)==set(range(10,20)),
            "Incorrect original immutable 10 x 10 candidate panel: "+family+" "+str(n))
        require(np.isfinite(candidates[list(METRICS)].to_numpy(dtype=float)).all(),
            "Nonfinite archived losses")
        checked[str(candidate_path)]=hashfile(candidate_path)
        seedmeans=candidates.groupby(["eval_seed","method"],as_index=False)[list(METRICS)].mean()
        for a,b in PAIRS:
            for metric in METRICS:
                x=seedmeans.pivot(index="eval_seed",columns="method",values=metric)
                for eval_seed,v in zip(x.index,x[a].to_numpy()-x[b].to_numpy()):
                    differences.append(dict(family=family,sample_n=n,method_a=a,method_b=b,
                        metric=metric,eval_seed=int(eval_seed),difference=float(v)))
                pr=prior[(prior.family==family)&(prior.sample_n==n)&
                         (prior.method_a==a)&(prior.method_b==b)&(prior.metric==metric)]
                require(len(pr)==1 and abs(float(pr.difference.iloc[0])-float((x[a]-x[b]).mean()))<=
                  1e-8*max(1.,abs(float(pr.difference.iloc[0]))),
                  "Original R1 pairwise mean failed seed-level reproducibility")
        for method in METHODS:
            sub=candidates[candidates.method==method]
            c=controls[(controls.family==family)&(controls.sample_n==n)&(controls.candidate==method)]
            q=q95[(q95.family==family)&(q95.sample_n==n)&(q95.method==method)]
            ct=cost[(cost.family==family)&(cost.sample_n==n)&(cost.method==method)]
            g=gap[(gap.family==family)&(gap.sample_n==n)&(gap.method==method)]
            p=pareto[(pareto.family==family)&(pareto.sample_n==n)&(pareto.method==method)]
            require(len(c)==4 and len(q)==1 and len(ct)==10 and len(g)==10 and len(p)==1,
                "Unmatched method provenance or control comparison: "+str((family,n,method)))
            one=dict(family=family,sample_n=n,method=method,
                mse_heldout=float(sub.mse.mean()),q95_heldout=float(sub.q95.mean()),
                avg_mse_discovery=float(g.mse_discovery.mean()),
                avg_q95_discovery=float(g.q95_discovery.mean()),
                mse_mean_gap_ratio=float(g.mse_gap_ratio.mean()),
                q95_mean_gap_ratio=float(g.q95_gap_ratio.mean()),
                mse_ranking_shift_abs_avg=float(g.mse_rank_shift.abs().mean()),
                q95_ranking_shift_abs_avg=float(g.q95_rank_shift.abs().mean()),
                pareto_nondominated=boolval(p.pareto_nondominated.iloc[0]),
                original_MC_q95_mean_relative_interval_width=float(
                    q.average_q95_interval_relative_width.iloc[0]),
                fraction_scenarios_q95_MC_interval_width_gt_20percent=float(
                    q.frac_scenarios_mc_q95_width_gt20.iloc[0]),
                original_optimizer_mean_objective_evaluations=float(ct.actual_evaluations.mean()),
                original_optimizer_evaluation_budget=float(ct.declared_budget.mean()),
                measured_wallclock_available_count=int(sum(ct.wall_time_verified.map(boolval))))
            for controller in ("convex_mse","local_deterministic"):
                for metric in METRICS:
                    z=c[(c.control==controller)&(c.metric==metric)]
                    require(len(z)==1,"Missing original independent deterministic direction")
                    tag=f"{controller}_{metric}"
                    one[f"{tag}_relative_gain_pct"]=float(z.relative_improvement_pct.iloc[0])
                    one[f"{tag}_holm_significant"]=float(z.holm_p_global_288.iloc[0])<.05
                    one[f"{tag}_favors_optimizer"]=float(z.difference_candidate_minus_control.iloc[0])<0
                    one[f"{tag}_holm_supported_optimizer_advantage"]=(
                        one[f"{tag}_holm_significant"] and one[f"{tag}_favors_optimizer"])
            tiles.append(one)
    x=pd.DataFrame(differences)
    require(len(x)==360 and not x.duplicated(
        ["family","sample_n","method_a","method_b","metric","eval_seed"]).any(),
        "Expect 3 sample sizes x 6 method pairs x 2 metrics x 10 evaluation seeds")
    y=pd.DataFrame(tiles)
    require(len(y)==12,"Expect exactly 12 family method/sample cells")
    out.mkdir(parents=True,exist_ok=True)
    x.to_csv(out/"independent_eval_seed_paired_differences.csv",index=False)
    y.to_csv(out/"rq1_family_scientific_panel.csv",index=False)
    (out/"SOURCE_CHECKSUMS.json").write_text(json.dumps({
        "family":family,"original_R1":ORIG_R1,"followup_R1":SOURCE_R1,
        "frozen_deterministic_R1":RECOVERED_R1,"crossed_R1":CROSSED_R1,
        "original_independent_eval_seeds":list(range(10,20)),
        "original_train_seeds":list(range(10)),
        "read_only_source_sha256":checked,
        "no_new_sampling_or_retraining":True},indent=2)+"\n")
    print("R1_FAMILY_FINAL_SCIENCE_PASS",family,len(x),len(y),flush=True)

def maxT(panel,B=REPS):
    """Global studentized sign flip, preserving 12 contrasts within each of 18 strata.

    Conditional on joint sign symmetry and independence of evaluation seed
    vectors within a stratum, diagnostic global maxT p-values. Not a
    selection-aware or nested-training-seed test, and no coverage guarantee.
    """
    strata=list(itertools.product(FAMILIES,SIZES))
    keys=list(itertools.product(PAIRS,METRICS))
    data=np.empty((18,12,10),dtype=float)
    testkeys=[]
    for block,(family,n) in enumerate(strata):
        chunk=panel[(panel.family==family)&(panel.sample_n==n)]
        for col,(pair,metric) in enumerate(keys):
            s=chunk[(chunk.method_a==pair[0])&(chunk.method_b==pair[1])&
                    (chunk.metric==metric)].sort_values("eval_seed")
            require(len(s)==10 and list(s.eval_seed)==list(range(10,20)),
                    "Missing required original seed vector for a maxT contrast")
            data[block,col,:]=s.difference.to_numpy(float)
            testkeys.append((family,n,pair[0],pair[1],metric))
    require(np.isfinite(data).all() and np.all(data.std(axis=2,ddof=1)>0),
            "Nonfinite or degenerate original paired seed differences")
    mean=data.mean(axis=2)
    observed=np.abs(mean)/(data.std(axis=2,ddof=1)/np.sqrt(10))
    obs=observed.ravel()
    rng=np.random.default_rng(20261118)
    counts=np.zeros(len(obs),dtype=np.int64)
    nullmax=[]
    # Shared signs within each family/sample stratum retain every comparison's
    # covariance, including joint MSE/Q95 and all four methods.
    for start in range(0,B,256):
        size=min(256,B-start)
        signs=rng.integers(0,2,size=(size,18,10),dtype=np.int8)*2-1
        values=data[None,:,:,:]*signs[:,:,None,:]
        avg=values.mean(axis=-1)
        sd=values.std(axis=-1,ddof=1)
        stats=np.abs(avg)/np.maximum(sd/np.sqrt(10),1e-15)
        maxima=stats.max(axis=(1,2))
        nullmax.extend(maxima.tolist())
        counts+=np.sum(maxima[:,None]>=obs[None,:]-1e-10,axis=0)
    adjusted=(counts+1)/(B+1)
    result=pd.DataFrame(testkeys,columns=["family","sample_n","method_a","method_b","metric"])
    result["abs_studentized_t_stat"]=obs
    result["global_maxT_signflip_p_sensitivity"]=adjusted
    result["exploratory_global_maxT_supported"]=adjusted<.05
    result["signflip_randomizations"]=B
    return result,dict(B=B,min_adjusted_p=float(adjusted.min()),
        adjusted_supported=int(sum(adjusted<.05)),
        assumption="joint sign symmetry for paired eval-seed vectors, independent across distinct family-n strata; not established",
        resample_unit="ten original evaluation seeds per family/sample block, all method/metric contrasts jointly signed",
        no_new_MC_draws=True)

def finalize(root,out):
    families=[];models=[]
    for f in FAMILIES:
        p=root/"family"/f
        x=read(p/"independent_eval_seed_paired_differences.csv")
        y=read(p/"rq1_family_scientific_panel.csv")
        require(len(x)==360 and len(y)==12 and set(x.family)=={f} and set(y.family)=={f},
            "Family evidence artifact missing or incomplete")
        provenance=json.loads((p/"SOURCE_CHECKSUMS.json").read_text())
        require(provenance["family"]==f and provenance["no_new_sampling_or_retraining"],
                "Missing immutable family provenance")
        families.append(x);models.append(y)
    paired=pd.concat(families,ignore_index=True)
    model=pd.concat(models,ignore_index=True)
    require(len(paired)==2160 and len(model)==72,
            "Incomplete independent seed-level RQ1 panel")
    res,meta=maxT(paired)
    orig=read(RBASE/ORIG_R1/"all_pairwise_global_holm.csv")
    cross=read(RBASE/CROSSED_R1/"analysis"/"crossed_hierarchical_inference_216.csv")
    columns=["family","sample_n","method_a","method_b","metric"]
    require(len(orig)==216 and len(cross)==216 and len(res)==216,
            "Previous complete R1 inferential sources missing")
    evidence=res.merge(orig[columns+["difference","p","holm_p_global"]],
                       on=columns,validate="one_to_one")
    evidence=evidence.merge(cross[columns+["crossed_t9_holm_sensitivity",
       "bootstrap_CI95_lower_absolute","bootstrap_CI95_upper_absolute"]],
       on=columns,validate="one_to_one")
    require(len(evidence)==216 and
       np.isfinite(evidence[["difference","holm_p_global","crossed_t9_holm_sensitivity"]]
             .to_numpy(float)).all(),
       "Unmatched original R1 versus corrected reviewer inferential panel")
    evidence["direction_favors_a"]=evidence.difference<0
    evidence["t_holm_supported"]=evidence.holm_p_global<.05
    evidence["crossed_t9_holm_supported"]=evidence.crossed_t9_holm_sensitivity<.05
    evidence["joint_estimation_bootstrap_CI_excludes_zero"]=(
        (evidence.bootstrap_CI95_lower_absolute>0)|
        (evidence.bootstrap_CI95_upper_absolute<0))
    model["q95_MC_relative_interval_width_pct"]=100*model.original_MC_q95_mean_relative_interval_width
    model["both_metrics_better_than_convex_mse"]=(
        (model.convex_mse_mse_relative_gain_pct>0)&
        (model.convex_mse_q95_relative_gain_pct>0))
    model["both_metrics_holm_supported_vs_convex_mse"]=(
        model.convex_mse_mse_holm_supported_optimizer_advantage&
        model.convex_mse_q95_holm_supported_optimizer_advantage)
    model["both_metrics_holm_supported_vs_local_deterministic"]=(
        model.local_deterministic_mse_holm_supported_optimizer_advantage&
        model.local_deterministic_q95_holm_supported_optimizer_advantage)
    out.mkdir(parents=True,exist_ok=True)
    evidence.to_csv(out/"table_RQ1_216_global_inference_sensitivity.csv",index=False)
    model.to_csv(out/"table_RQ1_72_method_family_sample_integrated.csv",index=False)
    original_joint=read(RBASE/CROSSED_R1/"analysis"/"two_metric_joint_practical_216_directions.csv")
    original_joint.to_csv(out/"table_RQ1_216_joint_MSE_Q95_exploratory.csv",index=False)
    agg=[]
    for method in METHODS:
        rows=model[model.method==method]
        require(len(rows)==18,"Missing method strata")
        agg.append(dict(method=method,strata=18,
          pareto_frontier_cells=int(rows.pareto_nondominated.sum()),
          both_metrics_gain_vs_convex_mse=int(rows.both_metrics_better_than_convex_mse.sum()),
          both_metrics_global_holm_advantage_vs_convex_mse=int(rows.both_metrics_holm_supported_vs_convex_mse.sum()),
          both_metrics_global_holm_advantage_vs_local_deterministic=
            int(rows.both_metrics_holm_supported_vs_local_deterministic.sum()),
          median_mse_percent_gain_vs_convex_mse=float(rows.convex_mse_mse_relative_gain_pct.median()),
          median_q95_percent_gain_vs_convex_mse=float(rows.convex_mse_q95_relative_gain_pct.median()),
          mean_objective_evaluations=float(rows.original_optimizer_mean_objective_evaluations.mean()),
          mean_original_q95_MC_relative_interval_width_pct=
             float(rows.q95_MC_relative_interval_width_pct.mean()),
          avg_abs_discovery_to_heldout_mse_rank_shift=
             float(rows.mse_ranking_shift_abs_avg.mean()),
          avg_abs_discovery_to_heldout_q95_rank_shift=
             float(rows.q95_ranking_shift_abs_avg.mean())))
    summary=pd.DataFrame(agg)
    summary.to_csv(out/"table_RQ1_four_method_scientific_summary.csv",index=False)
    total=[
        dict(metric="original_paired_t_Holm_216",count=int(sum(evidence.t_holm_supported)),denominator=216,
             interpretation="original paired-t assumptions, 10 independent evaluation seeds"),
        dict(metric="crossed_training_and_eval_t9_Holm_216",count=int(sum(evidence.crossed_t9_holm_supported)),
             denominator=216,interpretation="approximate random effects moments and t9, reviewer sensitivity"),
        dict(metric="joint_signflip_maxT_216",count=meta["adjusted_supported"],denominator=216,
             interpretation="posthoc dependence-preserving seed signflip conditional on strong joint symmetry"),
        dict(metric="two_way_seed_bootstrap_95_CI_excludes_zero",
             count=int(evidence.joint_estimation_bootstrap_CI_excludes_zero.sum()),denominator=216,
             interpretation="pointwise bootstrap, unadjusted across 216; descriptive only"),
        dict(metric="original_frozen_controls_Holm_288",
             count=int(sum(read(RBASE/RECOVERED_R1/"reviewer_synthesis"/
                 "deterministic_controls_original_heldout_global_holm.csv").holm_p_global_288<.05)),
             denominator=288,interpretation="two-sided adjusted differences can favor the CONTROL, not the optimizer"),
        dict(metric="joint_direction_both_metrics_gt_0_within_pair",
             count=int(sum(original_joint.joint_positive_bonferroni_95_within_pair.map(boolval))),
             denominator=216,interpretation="two-metric within-pair only; exploratory, not global across pairs")
    ]
    pd.DataFrame(total).to_csv(out/"table_RQ1_inferential_evidence_and_scope.csv",index=False)
    # Journal-ready figures; no hard-coded benchmark numeric results.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    plot=out/"figures";plot.mkdir(exist_ok=True)
    main=summary.set_index("method").loc[list(METHODS)]
    fig,axs=plt.subplots(1,2,figsize=(11,4.2),dpi=160)
    axs[0].bar(main.index,main.pareto_frontier_cells)
    axs[0].set(title="Held Out Pareto frontier",ylabel="Non-dominated family × sample blocks")
    axs[0].set_ylim(0,18);axs[0].yaxis.set_major_locator(MaxNLocator(integer=True))
    axs[1].bar(main.index,main.both_metrics_global_holm_advantage_vs_convex_mse)
    axs[1].set(title="Independent frozen convex control",ylabel="Strata favoring method on both metrics")
    axs[1].set_ylim(0,18);axs[1].yaxis.set_major_locator(MaxNLocator(integer=True))
    fig.suptitle("RQ1: direction-aware evidence on 18 original Held Out strata")
    fig.tight_layout()
    fig.savefig(plot/"figure_RQ1_pareto_and_deterministic_control.svg",bbox_inches="tight")
    fig.savefig(plot/"figure_RQ1_pareto_and_deterministic_control.png",bbox_inches="tight")
    plt.close(fig)
    evidence_count=pd.DataFrame(total).iloc[:4]
    fig,ax=plt.subplots(figsize=(10,4),dpi=160)
    ax.barh(evidence_count.metric[::-1],evidence_count["count"][::-1])
    ax.set(xlabel="Number of contrasts flagged (each column has different assumptions)",
           title="RQ1: inferential sensitivity across 216 optimizer contrasts")
    ax.set_xlim(0,216)
    for i,v in enumerate(evidence_count["count"][::-1]):ax.text(v+2,i,str(v),va="center")
    fig.tight_layout()
    fig.savefig(plot/"figure_RQ1_inferential_sensitivity.svg",bbox_inches="tight")
    fig.savefig(plot/"figure_RQ1_inferential_sensitivity.png",bbox_inches="tight")
    plt.close(fig)
    audit={
        "stage":"RQ1 final original-backup scientific synthesis",
        "status":"ARCHIVED_SCIENTIFIC_SENSITIVITY_COMPLETE",
        "original_R1_runs":[ORIG_R1,SOURCE_R1,CROSSED_R1,RECOVERED_R1],
        "independent_evaluation_seeds":10,"training_seeds":10,
        "sample_strata":18,"original_method_comparisons":216,
        "deterministic_control_comparisons":288,
        "maxT_approximate_randomizations":REPS,
        "original_monte_carlo_replications":500,
        "original_trained_weight_candidates":720,
        "original_optimizer_timing_metadata_available":0,
        "new_Monte_Carlo_or_training":False,
        "maxT_sensitivity":meta,
        "scientific_limitations":{
           "true_nominal_CI_coverage":"NOT_ESTIMABLE_WITHOUT_INDEPENDENT_KNOWN_TRUTH_REPLAY",
           "full_end_to_end_measured_walltime":"NOT_RECORDED_IN_FROZEN_DISCOVERY_FITS",
           "fully_selection_aware_FWER":"NOT_ESTIMATED",
           "joint_practical_thresholds":"POSTHOC_1_AND_5_PERCENT",
           "do_not_claim":"general domination across untested datasets or exact independence of 241 scenario cells"}}
    (out/"RQ1_FINAL_SCIENTIFIC_MANIFEST.json").write_text(json.dumps(audit,indent=2)+"\n")
    (out/"RQ1_MANUSCRIPT_RESULTS_AND_CAVEATS.md").write_text(
        "# RQ1 final evidence synthesis (original archived experiment)\n\n"
        "**Data**: 6 families × 3 sample sizes, 10 frozen training seeds × 10 independent "
        "evaluation seeds, 241 support scenarios and four search methods. "
        "Original model weights were never refitted or reselected.\n\n"
        "**Baseline**: original independently scored frozen Discovery deterministic "
        "convex_mse and local_deterministic methods; 288 posthoc pairwise contrasts "
        "with global Holm across 288. A significant contrast can indicate the "
        "deterministic control is BETTER; directional signs are mandatory.\n\n"
        "**Joint outcomes**: MSE and Q95 are evaluated together, with Pareto dominance "
        "and original two-way bootstrap. The 0, 1% and 5% thresholds were posthoc "
        "sensitivity probes; the joint uncertainty correction holds only within "
        "a single candidate pair/direction, not all 216 comparisons.\n\n"
        "**Inference**: the original global Holm-adjusted paired t results, crossed "
        "training/evaluation seed t9 sensitivity, and global maxT signflip sensitivity "
        "are reported side by side without replacing the original prespecified "
        "test. The maxT diagnostic shares all 12 per-stratum comparison signs "
        "to preserve within-seed metric/method dependence; its joint-sign-symmetry "
        "and cross-stratum independence assumptions are UNVERIFIED, and it is "
        "not proof of familywise or selection-aware error control.\n\n"
        "**Monte Carlo**: original per-scenario Q95 order-statistic intervals "
        "were reconstructed from the 500-replicate component matrices and six frozen "
        "method sets. This is conditional Q95 precision, not inferential "
        "coverage for an optimizer difference.\n\n"
        "**Compute**: all 720 objective evaluation counts are verified, but "
        "original elapsed-time fields and total nested HPO runtimes are absent. "
        "Unequal actual objective evaluations, especially Dirichlet, must be "
        "addressed as an experimental fairness limitation. Do not equate "
        "evaluation-count efficiency with measured wall-clock efficiency.\n\n"
        "**Remaining before stronger inferential claims**: independent known-truth "
        "coverage/selection-aware calibration and verified whole-pipeline runtime "
        "would require source records or a separately declared external replay. "
        "They are not manufactured or classified as successful here.\n\n"
        "Tables and source-ready SVG+PNG figures accompany this report under the "
        "same SHA256-backed repository run directory.\n"
    )
    files=sorted(p for p in out.rglob("*") if p.is_file())
    (out/"R1_FINAL_SHA256_INVENTORY.json").write_text(json.dumps({
        "source_R1_runs":[ORIG_R1,SOURCE_R1,CROSSED_R1,RECOVERED_R1],
        "read_only":True,"new_simulations":False,"files":[{
            "name":str(p.relative_to(out)),"bytes":p.stat().st_size,"sha256":hashfile(p)}
            for p in files]},indent=2)+"\n")
    print("RQ1_MANUSCRIPT_READY_SCIENTIFIC_SYNTHESIS_PASS",
          len(evidence),meta["adjusted_supported"],len(files),flush=True)

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    f=sub.add_parser("family");f.add_argument("--family",choices=FAMILIES,required=True)
    f.add_argument("--output",type=Path,required=True)
    z=sub.add_parser("finalize");z.add_argument("--input",type=Path,required=True)
    z.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.mode=="family":family_stage(a.family,a.output)
    else:finalize(a.input,a.output)
if __name__=="__main__":main()
