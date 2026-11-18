#!/usr/bin/env python3
"""R1 Q1 Stage 12 calibration replay of original archived frozen candidates.

This is a *new* controlled synthetic replay using a known-truth empirical
crossed-effects surrogate fitted to preserved 10x10 frozen candidate scores.
It tests CI coverage, FWER, FDR and posthoc candidate-choice sensitivity.
It does NOT rerun nested HPO, refit W, or demonstrate fully selection-aware
coverage of the original optimizer training and model-selection pipeline.
Do not replace original confirmatory p-values with these diagnostics.
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
from scipy.stats import t as student_t

FAMILIES = ("normal", "lognormal", "weibull", "invgauss", "exgaussian", "exwald")
SIZES = (200, 1000, 3000)
METHODS = ("ga", "nsga2", "de", "dirichlet")
METRICS = ("mse", "q95")
PAIRS = tuple(itertools.combinations(range(4), 2))
A = np.asarray([v[0] for v in PAIRS])
B = np.asarray([v[1] for v in PAIRS])
MODES = ("global_null", "mixed_null", "observed_effect")
PRIMARY = Path("R1/runs/44310024979")
MANIFEST = Path("R1/runs/44331514516/R1_STAGE5_12A_SHA256_MANIFEST.json")
TCRIT = float(student_t.ppf(.975, 9))
ALPHA = .05

def need(condition, message):
    if not condition:
        raise RuntimeError(message)

def hashfile(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+"\n")

def csvout(path, data):
    pd.DataFrame(data).to_csv(path, index=False)

def seed_for(*items):
    return int.from_bytes(hashlib.sha256(("r1-q1-12b-v1:"+
             ":".join(str(i) for i in items)).encode()).digest()[:8], "little")

def verify_sources(family, n):
    source = PRIMARY/"heldout"/f"{family}-n{n}"/"candidate_by_eval.csv"
    lineage = Path("R1/runs/44324757704")/"family"/family/"SOURCE_CHECKSUMS.json"
    need(source.is_file() and lineage.is_file(), "Missing original frozen score panel or source lineage")
    meta = json.loads(lineage.read_text())
    expected = meta.get("read_only_source_sha256", {}).get(str(source))
    need(expected is not None and hashfile(source) == expected, "Original R1 source digest mismatch: "+str(source))
    table = pd.read_csv(source)
    required = {"training_seed","eval_seed","method","mse","q95"}
    need(required <= set(table.columns) and len(table)==400, "Original score schema/length mismatch")
    need(not table.duplicated(["training_seed","eval_seed","method"]).any(), "Duplicate frozen candidate cells")
    need(set(table.method)==set(METHODS) and set(table.training_seed)==set(range(10))
         and set(table.eval_seed)==set(range(10,20)), "Original independent seed identities are not intact")
    need(np.isfinite(table[["mse","q95"]].to_numpy()).all(), "Invalid original observed metrics")
    data = np.empty((10,10,4,2), dtype=float)
    for mi,m in enumerate(METHODS):
        ordered = table[table.method==m].sort_values(["training_seed","eval_seed"])
        need(list(zip(ordered.training_seed,ordered.eval_seed)) ==
             list(itertools.product(range(10),range(10,20))), "Misaligned source candidate panel")
        data[:,:,mi,:] = ordered[["mse","q95"]].to_numpy().reshape(10,10,2)
    original = pd.read_csv("R1/runs/44307352615/all_pairwise_global_holm.csv")
    for ai,bi in PAIRS:
        for metric_i,metric in enumerate(METRICS):
            r = original[(original.family==family)&(original.sample_n==n)&
                         (original.method_a==METHODS[ai])&
                         (original.method_b==METHODS[bi])&(original.metric==metric)]
            need(len(r)==1 and abs(float(r.difference.iloc[0]) -
                 float(np.mean(data[:,:,ai,metric_i]-data[:,:,bi,metric_i])))<1e-9,
                 "Source panel cannot reproduce original confirmatory mean effect")
    return data, str(source), hashfile(source)

def components_from_source(x):
    """Balanced, deterministic 10x10 empirical additive random-effects surrogate."""
    mean = x.mean(axis=(0,1))                 # 4 methods x 2 metrics
    train = x.mean(axis=1)-mean                # 10 x 4 x 2
    evalu = x.mean(axis=0)-mean                # 10 x 4 x 2
    inter = x-mean-train[:,None,:,:]-evalu[None,:,:,:]
    need(np.max(np.abs(train.mean(axis=0)))<1e-10 and
         np.max(np.abs(evalu.mean(axis=0)))<1e-10 and
         np.max(np.abs(inter.mean(axis=(0,1))))<1e-10,
         "Reference DGP does not have an exactly known mean")
    return mean,train,evalu,inter.reshape(100,4,2)

def known_truth_means(original, mode):
    means=original.copy()
    if mode=="global_null":
        means[:]=original.mean(axis=0)
    elif mode=="mixed_null":
        means[0]=means[1]=(original[0]+original[1])/2
    elif mode!="observed_effect":
        raise ValueError("Invalid surrogate mode")
    return means

def draw_panel(rng, mu, tr, ev, it, reps):
    train_idx=rng.integers(10,size=(reps,10))
    eval_idx=rng.integers(10,size=(reps,10))
    interaction_idx=rng.integers(100,size=(reps,10,10))
    return (mu[None,None,None,:,:]+tr[train_idx][:,:,None,:,:]+
            ev[eval_idx][:,None,:,:,:]+it[interaction_idx])

def crossed_t9(d):
    """Balanced random-intercept method-of-moments, same 9-df sensitivity as R1.

    d is (replicates, training=10, evaluation=10, contrasts).
    Values for zero-variance ties are conservatively assigned p=1.
    """
    need(d.ndim==4 and d.shape[1:3]==(10,10), "Invalid 10x10 crossed replay")
    center=d.mean(axis=(1,2))
    rm=d.mean(axis=2)
    cm=d.mean(axis=1)
    resid=d-rm[:,:,None,:]-cm[:,None,:,:]+center[:,None,None,:]
    mstr=10*np.sum((rm-center[:,None,:])**2,axis=1)/9
    msev=10*np.sum((cm-center[:,None,:])**2,axis=1)/9
    msres=np.sum(resid**2,axis=(1,2))/81
    vtrain=np.maximum(0,(mstr-msres)/10)
    veval=np.maximum(0,(msev-msres)/10)
    se=np.sqrt(vtrain/10+veval/10+msres/100)
    ratio=np.divide(np.abs(center),se,out=np.zeros_like(center),where=se>0)
    p=2*student_t.sf(ratio,df=9)
    p=np.where(se>0,p,np.where(np.abs(center)<=1e-14,1.,0.))
    need(np.isfinite(p).all() and np.all((p>=0)&(p<=1)), "Nonfinite inferential replay p-values")
    return center,se,p

def paired_results(panel, truth):
    difference=(panel[:,:,:,A,:]-panel[:,:,:,B,:]).reshape(len(panel),10,10,12)
    truthd=(truth[A,:]-truth[B,:]).reshape(12)
    mean,se,p=crossed_t9(difference)
    covered=(np.abs(mean-truthd[None,:])<=TCRIT*se+1e-14)
    null=(np.abs(truthd)<=1e-13)
    return p.astype(np.float64),covered.astype(np.uint8),null

def selected_coverage(panel, method, means, control=3):
    # Method selection among frozen candidates, not optimizer/HPO model training.
    chosen=np.broadcast_to(method[:,None,None,None,None],
                            (len(panel),10,10,1,2))
    picked=np.take_along_axis(panel,chosen,axis=3)[:,:,:,0,:]
    d=picked-panel[:,:,:,control,:]
    mean,se,_=crossed_t9(d)
    truth=means[method,:]-means[control,:]
    result=(np.abs(mean-truth)<=TCRIT*se+1e-14).astype(np.float64)
    result[method==control]=np.nan
    return result

def block(args):
    family,n,reps=args.family,args.n,args.reps
    need(reps>=1000, "At least 1000 independent replays per mode required")
    x, source, source_sha = verify_sources(family,n)
    origin,tr,ev,inter=components_from_source(x)
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    arrays={}
    metrics=[]
    for mode in MODES:
        mu=known_truth_means(origin,mode)
        rng=np.random.default_rng(seed_for(family,n,mode))
        store_p,store_coverage,store_sel_ind,store_sel_naive=[],[],[],[]
        nulls=None
        completed=0
        while completed<reps:
            k=min(128,reps-completed)
            evaluated=draw_panel(rng,mu,tr,ev,inter,k)
            p,cover,is_null=paired_results(evaluated,mu)
            if nulls is None: nulls=is_null
            else: need(np.array_equal(nulls,is_null), "Changed synthetic known-truth hypothesis map")
            # Candidate choice on an INDEPENDENT synthetic training panel.
            heldout_training=draw_panel(rng,mu,tr,ev,inter,k)
            trained_choice=heldout_training.mean(axis=(1,2))[:,:,0].argmin(axis=1)
            same_data_choice=evaluated.mean(axis=(1,2))[:,:,0].argmin(axis=1)
            select_ind=selected_coverage(evaluated,trained_choice,mu)
            select_naive=selected_coverage(evaluated,same_data_choice,mu)
            store_p.append(p);store_coverage.append(cover)
            store_sel_ind.append(select_ind);store_sel_naive.append(select_naive)
            completed+=k
        pp=np.concatenate(store_p)
        cc=np.concatenate(store_coverage)
        si=np.concatenate(store_sel_ind)
        sn=np.concatenate(store_sel_naive)
        need(pp.shape==(reps,12) and cc.shape==(reps,12), "Invalid number of calibration replicates")
        arrays[mode+"_p"]=pp
        arrays[mode+"_covered"]=cc
        arrays[mode+"_null"]=nulls
        arrays[mode+"_selected_independent"]=si
        arrays[mode+"_selected_naive"]=sn
        metrics.append(dict(family=family,sample_n=n,mode=mode,
            independent_synthetic_replications=reps,comparisons=12,
            known_true_null_contrasts=int(nulls.sum()),
            mean_95pct_CI_coverage=float(cc.mean()),
            candidate_selection_coverage_independent=float(np.nanmean(si)),
            candidate_selection_coverage_naive=float(np.nanmean(sn)),
            independent_selection_repetitions=int(np.isfinite(si[:,0]).sum()),
            naive_selection_repetitions=int(np.isfinite(sn[:,0]).sum()),
            original_panel_sha256=source_sha))
    np.savez_compressed(out/"CALIBRATION_REPLICATIONS.npz",**arrays)
    csvout(out/"calibration_block_summary.csv",metrics)
    dump_json(out/"PROVENANCE.json",dict(stage="12B",scope="empirical_crossed_effects_surrogate",
         frozen_original_candidate_panel=source,sha256=source_sha,
         family=family,sample_n=n,repetitions_per_mode=reps,modes=list(MODES),
         original_training_seeds=list(range(10)),original_eval_seeds=list(range(10,20)),
         cross_method_metric_dependence="joint resampling of 8 dimensional original row, column and interaction residual vectors",
         independent_surrogate_replicates=True,controlled_known_effects=True,
         optimizer_HPO_fits_recomputed=False,trained_weights_reestimated=False,
         selection_scope="posthoc frozen-method candidate choice, not original nested HPO/W selection",
         original_results_modified=False))
    print("R1_Q1_STAGE12B_SURROGATE_BLOCK_PASS",family,n,reps,flush=True)

def adjust(p, mode):
    """Apply global Holm or BH across all 216 comparisons per synthetic experiment."""
    count=p.shape[1]
    order=np.argsort(p,axis=1)
    ps=np.take_along_axis(p,order,axis=1)
    if mode=="holm":
        threshold=np.arange(count,0,-1)
        adjusted=np.maximum.accumulate(ps*threshold[None,:],axis=1)
        sorted_rej=adjusted<=ALPHA
    elif mode=="bh":
        mask=ps<=ALPHA*(np.arange(count)+1)[None,:]/count
        maximum=np.where(mask,np.arange(count)[None,:],-1).max(axis=1)
        sorted_rej=(np.arange(count)[None,:]<=maximum[:,None])
    else:
        raise ValueError(mode)
    result=np.empty_like(sorted_rej,dtype=bool)
    np.put_along_axis(result,order,sorted_rej,axis=1)
    return result

def wilson(success,trials):
    if trials==0: return [None,None]
    p=success/trials;z=1.959963984540054
    denominator=1+z*z/trials
    center=(p+z*z/(2*trials))/denominator
    radius=(z/denominator)*math.sqrt(p*(1-p)/trials+z*z/(4*trials*trials))
    return [max(0.,center-radius),min(1.,center+radius)]

def finalize(args):
    root=Path(args.root); blocks=root/"blocks"
    all_data={mode:[] for mode in MODES}
    summaries=[]
    digests=[]
    reps=None
    for f in FAMILIES:
        for n in SIZES:
            sub=blocks/f"{f}-n{n}"
            provenance=json.loads((sub/"PROVENANCE.json").read_text())
            need(provenance["family"]==f and provenance["sample_n"]==n and
                 provenance["trained_weights_reestimated"] is False,
                 "Missing or invalid original calibration block")
            _,_,expected_sha=verify_sources(f,n)
            need(provenance["sha256"]==expected_sha, "A source archive changed after simulation")
            with np.load(sub/"CALIBRATION_REPLICATIONS.npz",allow_pickle=False) as z:
                for mode in MODES:
                    pp=z[mode+"_p"]; covered=z[mode+"_covered"]
                    null=z[mode+"_null"]
                    sel_ind=z[mode+"_selected_independent"]
                    sel_naive=z[mode+"_selected_naive"]
                    need(pp.ndim==2 and pp.shape[1]==12 and
                         pp.shape==covered.shape and len(null)==12,
                         "Missing 12 original contrasts in a surrogate block")
                    need(np.all(np.isfinite(pp)) and np.all((pp>=0)&(pp<=1)),
                         "Invalid synthetic P-values")
                    need(np.all((covered==0)|(covered==1)), "Invalid synthetic CI coverage flags")
                    need(sel_ind.shape==(len(pp),2) and sel_naive.shape==(len(pp),2),
                         "Missing candidate choice replay")
                    if reps is None: reps=len(pp)
                    need(len(pp)==reps and reps>=1000, "Inconsistent independent replication count")
                    all_data[mode].append(dict(p=pp.copy(),covered=covered.copy(),
                                               null=null.copy(),sel_ind=sel_ind.copy(),
                                               sel_naive=sel_naive.copy()))
            local=pd.read_csv(sub/"calibration_block_summary.csv")
            need(len(local)==3 and set(local["mode"])==set(MODES),
                 "Block summary does not include all 3 known-truth data regimes")
            summaries.append(local)
    need(sum(map(len,all_data.values()))==54,"Incomplete original 18x3 synthetic panels")
    out=root/"synthesis"
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    detailed=[]
    for mode in MODES:
        data=all_data[mode]
        p=np.concatenate([a["p"] for a in data],axis=1)
        cov=np.concatenate([a["covered"] for a in data],axis=1)
        null=np.concatenate([a["null"] for a in data],axis=0)
        need(p.shape==(reps,216) and cov.shape==(reps,216) and null.shape==(216,),
             "Global R1 216-comparison calibration shape mismatch")
        need(int(null.sum())==({"global_null":216,"mixed_null":36}.get(mode,int(null.sum()))),
             "Incorrect known-truth null count")
        selection_ind=np.concatenate([a["sel_ind"] for a in data],axis=0)
        selection_naive=np.concatenate([a["sel_naive"] for a in data],axis=0)
        for policy in ("holm","bh"):
            reject=adjust(p,policy)
            false=(reject & null[None,:]).sum(axis=1)
            true=(reject & ~null[None,:]).sum(axis=1)
            total=reject.sum(axis=1)
            fwer=(false>0)
            fdp=false/np.maximum(total,1)
            fdr=float(fdp.mean())
            power=float((true/(~null).sum()).mean()) if (~null).sum()>0 else None
            count_error=int(fwer.sum())
            r=dict(mode=mode,multiplicity=policy,independent_surrogate_replays=reps,
                   original_comparison_count=216,known_true_nulls=int(null.sum()),
                   familywise_false_positive_probability=float(fwer.mean()),
                   familywise_95pct_wilson_lower=wilson(count_error,reps)[0],
                   familywise_95pct_wilson_upper=wilson(count_error,reps)[1],
                   false_discovery_rate=fdr,mean_false_discoveries=float(false.mean()),
                   mean_total_discoveries=float(total.mean()),
                   power_per_true_nonnull_contrast=power,
                   nominal_alpha=ALPHA,scope="synthetic crossed-effect surrogate; not complete optimizer HPO reselection")
            results.append(r)
        for j,(f,n) in enumerate(itertools.product(FAMILIES,SIZES)):
            for k,(ai,bi) in enumerate(PAIRS):
                for mi,metric in enumerate(METRICS):
                    idx=12*j+2*k+mi
                    successes=int(cov[:,idx].sum())
                    lo,hi=wilson(successes,reps)
                    detailed.append(dict(family=f,sample_n=n,method_a=METHODS[ai],method_b=METHODS[bi],
                        metric=metric,mode=mode,known_true_null=bool(null[idx]),
                        surrogate_CI95_coverage=successes/reps,coverage_CI95_lower=lo,
                        coverage_CI95_upper=hi,surrogate_replications=reps,
                        marginal_unadjusted_rejection_rate=float((p[:,idx]<ALPHA).mean())))
        cov_sum=int(cov.sum()); all_n=cov.size
        lo,hi=wilson(cov_sum,all_n)
        summary=dict(mode=mode,multiplicity="unadjusted_CI95",
            independent_surrogate_replays=reps, original_comparison_count=216,
            known_true_nulls=int(null.sum()),
            nominal_interval_coverage=.95,empirical_interval_coverage=cov_sum/all_n,
            empirical_coverage_wilson_lower=lo,empirical_coverage_wilson_upper=hi,
            independent_method_selection_coverage=float(np.nanmean(selection_ind)),
            naive_same_sample_method_selection_coverage=float(np.nanmean(selection_naive)),
            nonbaseline_selections_independent=int(np.isfinite(selection_ind[:,0]).sum()),
            nonbaseline_selections_naive=int(np.isfinite(selection_naive[:,0]).sum()),
            scope="frozen candidate selection on synthetic panels; original nested HPO not replayed")
        results.append(summary)
    csvout(out/"table_RQ1_stage12_global_replay_coverage_multiplicity.csv",results)
    csvout(out/"table_RQ1_stage12_per_contrast_coverage_648.csv",detailed)
    csvout(out/"table_RQ1_stage12_block_summary_54.csv",pd.concat(summaries,ignore_index=True))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch
        rows=[x for x in results if x["multiplicity"]=="unadjusted_CI95"]
        fig,ax=plt.subplots(figsize=(8.4,4.4))
        names=["Global null","Mixed null/alternative","Observed effect"]
        ys=[r["empirical_interval_coverage"] for r in rows]
        ax.bar(names,ys,color=["#486780","#70958A","#B19665"])
        ax.axhline(.95,linestyle="--",color="#303030",linewidth=1.3,label="Nominal 95%")
        ax.set_ylim(0,1.04);ax.set_ylabel("Empirical 95% interval coverage")
        ax.set_title("Known-truth calibration within the fitted synthetic surrogate")
        ax.legend(loc="lower left");fig.tight_layout()
        fig.savefig(out/"figure_RQ1_stage12_surrogate_coverage.svg")
        fig.savefig(out/"figure_RQ1_stage12_surrogate_coverage.png",dpi=180)
        plt.close(fig)
    except Exception as exc:
        raise RuntimeError("Publication figure render failure") from exc
    limits=[
        "This replay samples new synthetic datasets from an additive empirical crossed-effects surrogate estimated from 10 original training and 10 evaluation seed cells per block.",
        "Within this explicitly defined surrogate, true method effects are known by construction; all resampled random-effect component vectors are centered.",
        "The synthetic training/evaluation component distributions and Gaussian t9 variance reference are not guaranteed to match the actual experiment's true data-generating process.",
        "Independent synthetic repeats estimate nominal CI coverage and Holm/BH errors conditional on this surrogate and its cross-block independence assumption.",
        "Candidate selection chooses the lowest training-only MSE among four ALREADY FROZEN engines on an independently generated synthetic training panel; this does NOT rerun nested 5x3 HPO, optimizer selection of weight vectors, or their original scientific selection pathway.",
        "Therefore empirical fully selection-aware interval coverage of the original end-to-end optimization pipeline remains OUTSTANDING.",
        "Original R1 comparisons, their p-values and all previously reported scientific outcomes remain unchanged.",
        "The Stage 5A HPO cost and Stage 5B Actions runtime records are already permanently archived; they are reused, never recomputed.",
    ]
    dump_json(out/"STAGE12B_SCIENTIFIC_SCOPE.json",dict(status="KNOWN_TRUTH_SURROGATE_REPLAY_COMPLETE",
        independent_synthetic_replications_per_mode=reps,original_family_n_blocks=18,
        original_metric_contrasts=216, original_frozen_candidate_panels=18,
        exact_known_truth_within_surrogate=True,
        null_type1_calibration_within_surrogate=True,
        full_original_pipeline_selection_aware_coverage_established=False,
        new_synthetic_resamples=True,new_original_MC_simulations=False,new_optimizer_fit=False,
        source_stage5_cost_archive="R1/runs/44331514516",
        notes=limits))
    (out/"RQ1_STAGE12_MANUSCRIPT_INTERPRETATION.md").write_text(
        "# RQ1 Stage 12 — Known-truth calibration and inferential limits\n\n"
        "The frozen originally scored 10×10 method grids for 18 population/sample-size blocks "
        "were used to construct a centered empirical crossed-effects surrogate. "
        f"For each of three known-truth regimes, {reps:,} independent synthetic outer "
        "replays were generated per block. We evaluated crossed 9-df 95% "
        "interval coverage and global Holm/BH error rates for 216 contrasts. "
        "Original predeclared results were not modified.\n\n"
        "The global-null and mixed-null regimes provide **surrogate-conditional**, "
        "not distribution-free, calibration estimates. A separate frozen-method "
        "selection diagnostic compares independent training-only candidate choice "
        "with same-evaluation-sample choice. Neither reproduces the original "
        "nested HPO or full weight-selection pathway. The manuscript must not "
        "claim full selection-aware coverage, exact small-sample type-I control, "
        "or empirical full-pipeline FWER from this experiment.\n\n"
        "Numeric tables, 648 per-contrast coverage rows, and SVG/PNG figures are in this folder. "
        "No original optimization or Monte Carlo simulations were rerun.\n")
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name!="STAGE12B_SHA256_MANIFEST.json" and p.name!="RUN_STATUS.md":
            digests.append(dict(path=p.relative_to(root).as_posix(),
                                sha256=hashfile(p),bytes=p.stat().st_size))
    dump_json(root/"STAGE12B_SHA256_MANIFEST.json",dict(
         independent_synthetic_replays_per_mode=reps,
         source_original_R1="44310024979",
         status="PASS_SURROGATE_CONDITIONAL_WITH_FULL_HPO_SELECTION_LIMITATION",
         stages5a5b12a_preserved="R1/runs/44331514516",
         files=digests))
    print("R1_Q1_STAGE12_SYNTHESIS_AND_HASHES_PASS",reps,len(detailed),len(digests),flush=True)

def selftest():
    rng=np.random.default_rng(44)
    source=rng.normal(size=(10,10,4,2))*.02+1
    mu,tr,ev,inter=components_from_source(source)
    for mode in MODES:
        truth=known_truth_means(mu,mode)
        panel=draw_panel(rng,truth,tr,ev,inter,17)
        p,cover,null=paired_results(panel,truth)
        need(p.shape==(17,12) and cover.shape==(17,12), "Synthetic replay shape failure")
        need(int(null.sum())==({"global_null":12,"mixed_null":2}.get(mode,int(null.sum()))),
             "Incorrect synthetic known truth")
        choice=panel.mean(axis=(1,2))[:,:,0].argmin(axis=1)
        covered=selected_coverage(panel,choice,truth)
        need(covered.shape==(17,2), "Selection-aware sensitivity shape failure")
    p=np.array([[.001,.012,.91],[.08,.19,.7]])
    need(adjust(p,"holm").shape==p.shape and adjust(p,"bh").shape==p.shape,
         "Global multiplicity routine failure")
    need(adjust(p,"holm")[0,:].tolist()==[True,True,False],
         "Holm stepdown logic is incorrect")
    need(adjust(p,"bh")[0,:].tolist()==[True,True,False],
         "BH stepup logic is incorrect")
    need(wilson(0,100)[0]==0, "Wilson CI boundary invalid")
    print("R1_STAGE12B_SYNTHETIC_UNIT_TEST_PASS")

def main():
    p=argparse.ArgumentParser()
    commands=p.add_subparsers(dest="command",required=True)
    commands.add_parser("selftest")
    q=commands.add_parser("preflight");q.add_argument("--output",required=True)
    q=commands.add_parser("block")
    q.add_argument("--family",choices=FAMILIES,required=True)
    q.add_argument("--n",type=int,choices=SIZES,required=True)
    q.add_argument("--reps",type=int,default=4096)
    q.add_argument("--output",required=True)
    q=commands.add_parser("finalize");q.add_argument("--root",required=True)
    a=p.parse_args()
    if a.command=="selftest": selftest()
    elif a.command=="block": block(a)
    elif a.command=="finalize": finalize(a)
    else:
        manifest=json.loads(MANIFEST.read_text())
        need(manifest["verified_original_HPO_archives"]==900 and
             manifest["verified_original_HPO_inner_trial_rows"]==86400,
             "Stage 5A cost recovery not yet fully archived")
        need(manifest["stage5B_scope"]=="COMPLETE_API_HISTORY",
             "Stage 5B Actions runtime audit not confirmed")
        preflight=[]
        for f in FAMILIES:
            for n in SIZES:
                _,path,digest=verify_sources(f,n)
                preflight.append(dict(family=f,sample_n=n,source_file=path,
                                      source_sha256=digest))
        dump_json(a.output,dict(stage12A_archive="R1/runs/44331514516",
            stage12B_blocks=len(preflight),score_sources=preflight,
            stage5A_verified_archive_files=900,stage5B_complete=True,
            interpretation="Known-truth crossed-effects surrogate only; full HPO selection remains untested"))
        print("R1_STAGE12B_INPUTS_AND_5A_5B_VALIDATION_PASS",len(preflight),flush=True)

if __name__=="__main__":main()
