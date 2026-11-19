#!/usr/bin/env python3
"""T3 Q2 E-F synthesis and scientific manuscript-ready report.

Original within-family 241 supported scenario data; 18 independent evaluation
family/sample-size blocks; 4 frozen search methods; 2 frozen reference policies.
Uncertainty: two-way training/evaluation seed bootstrap, scenario identities fixed.
This is EXPLORATORY, posthoc, not Stage12-calibrated Q2 error control.
"""
import argparse,csv,hashlib,json,math,os,sys
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
METHODS=("ga","nsga2","de","dirichlet")
SIZES=(200,1000,3000)
M=("upper_tail","lower_tail","symmetric_t","point_mass","clustered_upper","clustered_symmetric")
DISP={"normal":"Normal","lognormal":"Lognormal","weibull":"Weibull",
      "invgauss":"Inverse Gaussian","exgaussian":"Ex Gaussian","exwald":"Ex Wald",
      "upper_tail":"Upper-tail","lower_tail":"Lower-tail","symmetric_t":"Symmetric t",
      "point_mass":"Point mass","clustered_upper":"Clustered upper","clustered_symmetric":"Clustered symmetric"}
EXPECTED=10*10*4*241*2
BOOT=2048

def check(ok,m):
    if not ok:raise RuntimeError("Q2 synthesis gate FAILED: "+m)

def sha(f):
    h=hashlib.sha256()
    with f.open("rb") as i:
        for chunk in iter(lambda:i.read(1048576),b""):h.update(chunk)
    return h.hexdigest()

def save_csv(df,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(path,index=False,float_format="%.10g")
    check(path.stat().st_size>60,"empty output "+str(path))

def pct_bootstrap(matrix,seed):
    check(matrix.shape==(10,10) and np.isfinite(matrix).all(),"crossed seed matrix")
    rng=np.random.default_rng(seed)
    ti=rng.integers(0,10,size=(BOOT,10))
    ei=rng.integers(0,10,size=(BOOT,10))
    draws=matrix[ti[:,:,None],ei[:,None,:]].mean(axis=(1,2))
    mean=float(matrix.mean())
    lo,hi=np.quantile(draws,[.025,.975])
    min_tail=min(np.sum(draws<=0),np.sum(draws>=0))
    # Correct finite-bootstrap +1 support; this p is posthoc/exploratory.
    p=min(1.,2*(1+int(min_tail))/(BOOT+1))
    return mean,float(lo),float(hi),float(p),float(np.mean(draws>0))

def bh_adjust(p):
    p=np.asarray(p,dtype=float);check(np.isfinite(p).all() and np.all((0<=p)&(p<=1)),"invalid p-values")
    order=np.argsort(p,kind="stable");adj=np.empty(len(p));cur=1.
    for k in range(len(p)-1,-1,-1):
        idx=order[k];cur=min(cur,len(p)*p[idx]/(k+1));adj[idx]=cur
    return adj

def build(root):
    root=Path(root);out=root/"synthesis";out.mkdir(parents=True,exist_ok=True)
    manifest=[];scenario_frames=[];factor_frames=[];neighbor_frames=[];tests=[]
    lineages=set()
    for fi,f in enumerate(FAMILIES):
        for ni,n in enumerate(SIZES):
            b=root/"blocks"/f"{f}-n{n}"
            mp=b/"Q2_BLOCK_MANIFEST.json"
            check(mp.is_file(),"missing one of 18 completed blocks: "+str(b))
            m=json.loads(mp.read_text())
            check(m["analysis"].startswith("Q2 A-D") and m["family"]==f and m["sample_n"]==n,
                  "block provenance changed "+str(b))
            check(m["paired_benchmark_metric_records"]==EXPECTED and
                  m["scenario_rows"]==4*241*2 and m["original_heldout_archive_count"]==10,
                  "block expected coverage mismatch")
            for name,p in m["outputs"].items():
                source=b/name
                check(source.is_file() and sha(source)==p["sha256"] and source.stat().st_size==p["bytes"],
                      "block output SHA mismatch "+str(source))
            for z in m["original_archive_lineage"]:
                token=(f,n,z["evaluation_seed"])
                check(token not in lineages,"duplicate original Held Out seed lineage")
                check(len(z["sha256"])==64,"original source hash missing")
                lineages.add(token)
            manifest.append(dict(family=f,sample_n=n,block_manifest_sha256=sha(mp),
                  original_zip_sha256=[z["sha256"] for z in m["original_archive_lineage"]]))
            x=pd.read_csv(b/"scenario_effects.csv")
            check(len(x)==4*241*2 and
                  not x.duplicated(["method","scenario_id","benchmark_role"]).any(),
                  "scenario index duplicates")
            check(set(x.method)==set(METHODS) and set(x.benchmark_role)=={"own","mean"},"methods/reference coverage")
            scenario_frames.append(x)
            factors=pd.read_csv(b/"factor_profiles.csv")
            factor_frames.append(factors)
            neighbors=pd.read_csv(b/"local_neighbors.csv")
            neighbor_frames.append(neighbors)
            # Recovery of the original crossed training x independent evaluation seed
            # structure for 10x10 two-way bootstrap. Scenario identity is fixed.
            cells=pd.read_csv(b/"paired_seed_cells.csv.gz",usecols=[
                "method","training_seed","evaluation_seed","scenario_id","mechanism",
                "benchmark_role","mse_gain_pct","q95_gain_pct"])
            check(len(cells)==EXPECTED,"original crossed cell count")
            check(set(cells.training_seed)==set(range(10)) and
                  set(cells.evaluation_seed)==set(range(10,20)),
                  "training/evaluation seed identities")
            check(not cells.duplicated(["method","training_seed","evaluation_seed",
                                        "scenario_id","benchmark_role"]).any(),
                  "duplicate within-family crossed score")
            check(np.isfinite(cells[["mse_gain_pct","q95_gain_pct"]].to_numpy()).all(),
                  "nonfinite primary percent gain")
            groups=cells.groupby(["method","benchmark_role","mechanism","training_seed",
                                  "evaluation_seed"],sort=False,observed=True)[
                                      ["mse_gain_pct","q95_gain_pct"]].mean().reset_index()
            # Include clean reference as a clearly distinct comparator, not mechanism H2.
            for method_i,method in enumerate(METHODS):
                for role_i,role in enumerate(("own","mean")):
                    for mech_i,mech in enumerate(("clean",)+M):
                        sub=groups[(groups.method==method)&
                                   (groups.benchmark_role==role)&(groups.mechanism==mech)]
                        check(len(sub)==100,"missing original crossed panel "+repr((f,n,method,role,mech)))
                        for metric_i,metric in enumerate(("mse_gain_pct","q95_gain_pct")):
                            mat=sub.pivot(index="training_seed",columns="evaluation_seed",values=metric)
                            check(mat.shape==(10,10),"crossed seed matrix must be 10x10")
                            seed=20261119+fi*99991+ni*10007+method_i*1009+role_i*101+mech_i*11+metric_i
                            mean,lo,hi,p,prob=pct_bootstrap(mat.to_numpy(dtype=float),seed)
                            tests.append(dict(family=f,sample_n=n,method=method,
                                benchmark_role=role,mechanism=mech,metric=metric,
                                average_gain_pct=mean,ci95_low=lo,ci95_high=hi,
                                exploratory_bootstrap_p=p,bootstrap_probability_gain=prob,
                                original_training_seeds=10,independent_evaluation_seeds=10,
                                scenarios_in_mechanism=1 if mech=="clean" else 40,
                                scenario_resampling=False,posthoc_inference=True))
            del cells
    check(len(lineages)==180 and len(tests)==18*4*2*7*2,
          "original 180 source lineage and 2016 crossed-bootstrap target panels")
    sc=pd.concat(scenario_frames,ignore_index=True)
    check(len(sc)==18*4*241*2,"all Q2 scenario effect profiles preserved")
    fac=pd.concat(factor_frames,ignore_index=True)
    nbr=pd.concat(neighbor_frames,ignore_index=True)
    bs=pd.DataFrame(tests)
    de_own=bs[(bs.method=="de")&(bs.benchmark_role=="own")&
              (bs.mechanism!="clean")].copy()
    check(len(de_own)==216,"Q2 primary analysis is 18 x six mechanisms x two losses")
    de_own["bh_q_exploratory_216"]=bh_adjust(de_own.exploratory_bootstrap_p)
    # Reattach exactly these 216 exploratory q-values; other panels have no
    # multiplicity claims.
    bs=bs.merge(de_own[["family","sample_n","method","benchmark_role","mechanism","metric",
                        "bh_q_exploratory_216"]],
                on=["family","sample_n","method","benchmark_role","mechanism","metric"],how="left",
                validate="one_to_one")
    save_csv(bs,out/"Q2_ALL_TWO_WAY_BOOTSTRAP_EFFECTS.csv")
    save_csv(de_own,out/"Q2_PRIMARY_DE_216_EXPLORATORY_CONTRASTS.csv")
    save_csv(sc,out/"Q2_ALL_SCENARIO_EFFECTS.csv.gz") if False else None
    save_csv(fac,out/"Q2_ALL_FACTOR_PROFILES.csv")
    save_csv(nbr,out/"Q2_ALL_OBSERVED_LOCAL_NEIGHBORS.csv")
    # Main reader-first table: 6 source/evaluation families x 6 mechanisms,
    # averaged over all 3 n and 40 original observed settings each.
    primary=sc[(sc.method=="de")&(sc.benchmark_role=="own")&
               (sc.mechanism!="clean")]
    agg=primary.groupby(["family","mechanism"],sort=False,observed=True).agg(
        n_sample_sizes=("sample_n","nunique"),eligible_scenarios=("scenario_id","count"),
        avg_mse_gain_pct=("mse_gain_pct","mean"),avg_q95_gain_pct=("q95_gain_pct","mean"),
        joint_positive=("joint_positive","sum"),joint_5pct=("joint_5pct","sum"),
        any_worsening=("any_worsening","sum")).reset_index()
    check(len(agg)==36 and (agg.eligible_scenarios==120).all(),"Q2 6x6 family/mechanism accounting")
    agg["joint_positive_rate"]=agg.joint_positive/agg.eligible_scenarios
    agg["joint_5pct_rate"]=agg.joint_5pct/agg.eligible_scenarios
    save_csv(agg,out/"Q2_TABLE_FAMILY_BY_MECHANISM_DE_OWN.csv")
    # Distribution x n variation of the 6 supported mechanisms, descriptive.
    by_n=primary.groupby(["family","sample_n"],sort=False).agg(
       eligible_scenarios=("scenario_id","count"),mean_mse_gain_pct=("mse_gain_pct","mean"),
       mean_q95_gain_pct=("q95_gain_pct","mean"),joint_positive=("joint_positive","sum"),
       joint_5pct=("joint_5pct","sum")).reset_index()
    check(len(by_n)==18 and (by_n.eligible_scenarios==240).all(),"Q2 family/sample table")
    save_csv(by_n,out/"Q2_TABLE_FAMILY_BY_SAMPLE_SIZE_DE_OWN.csv")
    # Composition sensitivity: all 4 methods and both pre-frozen benchmarks.
    engine=sc[sc.mechanism!="clean"].groupby(["method","benchmark_role"]).agg(
       observations=("scenario_id","count"),mean_mse_gain_pct=("mse_gain_pct","mean"),
       mean_q95_gain_pct=("q95_gain_pct","mean"),joint_positive=("joint_positive","sum"),
       joint_5pct=("joint_5pct","sum")).reset_index()
    save_csv(engine,out/"Q2_TABLE_FOUR_METHOD_BENCHMARK_SENSITIVITY.csv")
    # Matched neighboring chosen grid cells: never extrapolate across 138 unchosen
    # fraction x severity combinations.
    local=nbr.groupby(["method","benchmark_role","axis","mechanism"],sort=False).agg(
       observed_neighbor_edges=("scenario_low","count"),
       mean_mse_gain_change=("mse_gain_change","mean"),
       mean_q95_gain_change=("q95_gain_change","mean"),
       positive_mse_change=("mse_gain_change",lambda x:int((x>0).sum())),
       positive_q95_change=("q95_gain_change",lambda x:int((x>0).sum()))).reset_index()
    save_csv(local,out/"Q2_TABLE_LOCAL_NEIGHBOR_SENSITIVITY.csv")
    # Cross-check all mechanism averages against their input source.
    check(abs(float(agg.avg_mse_gain_pct.mean())-float(primary.mse_gain_pct.mean()))<1e-8,
          "mechanism mean reconciliation")
    # Publication figure. Plot only actual original levels, including unfavorable
    # cases, and show both MSE and Q95 with the exact same color scale.
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.3,
                         "svg.fonttype":"none","axes.titlesize":11})
    fig,axes=plt.subplots(1,2,figsize=(11.8,4.8),sharey=True,
                           gridspec_kw={"wspace":.1})
    zmax=max(5.,np.percentile(np.abs(agg[["avg_mse_gain_pct","avg_q95_gain_pct"]].to_numpy()),98))
    zmax=min(200.,zmax)
    from matplotlib.colors import TwoSlopeNorm
    for ax,metric,title in zip(axes,("avg_mse_gain_pct","avg_q95_gain_pct"),
                               ("Mean squared error","95th-percentile squared error")):
        matrix=np.array([[float(agg[(agg.family==f)&(agg.mechanism==m)][metric].iloc[0])
                          for m in M] for f in FAMILIES])
        im=ax.imshow(matrix,cmap="RdYlGn",norm=TwoSlopeNorm(vmin=-zmax,vcenter=0,vmax=zmax),aspect="auto")
        ax.set_xticks(range(6),[DISP[x] for x in M],rotation=37,ha="right")
        ax.set_yticks(range(6),[DISP[x] for x in FAMILIES])
        ax.set_title(title,pad=12)
        for i in range(6):
            for j in range(6):
                v=matrix[i,j]
                ax.text(j,i,f"{v:+.1f}",ha="center",va="center",fontsize=7.4,
                        color="#181818" if abs(v)<zmax*.45 else "#fff")
    cb=fig.colorbar(im,ax=axes,fraction=.022,pad=.02)
    cb.set_label("Average gain vs frozen classical control (%)")
    fig.suptitle("Where optimized DE improves two estimation losses",fontsize=12,y=1.01)
    fig.text(.5,-.10,"Within-family independent Held Out; six support mechanisms; "
             "3 sample sizes and 40 original scenarios per mechanism. Descriptive gains, not calibrated significance.",
             ha="center",fontsize=8)
    for ext in ("png","svg"):
        fig.savefig(out/f"figure_Q2_DE_family_mechanism.{ext}",dpi=240,bbox_inches="tight",pad_inches=.2)
    plt.close(fig)
    # Proportion x severity panel: explicit selection counts, not misleading full factorial.
    r=primary.copy()
    r=r[r.contamination>0]
    fracs=sorted(r.contamination.unique());sev=sorted(r.mad_scale.unique())
    t=r.groupby(["contamination","mad_scale"]).agg(
       mse=("mse_gain_pct","mean"),q95=("q95_gain_pct","mean"),
       n=("scenario_id","count")).reset_index()
    mat=np.full((len(fracs),len(sev)),np.nan);ct=np.zeros(mat.shape,dtype=int)
    for x in t.itertuples(index=False):
        i=fracs.index(x.contamination);j=sev.index(x.mad_scale)
        mat[i,j]=(x.mse+x.q95)/2
        ct[i,j]=x.n
    fig,ax=plt.subplots(figsize=(9.6,4.8))
    z=np.ma.masked_invalid(mat)
    extent=max(10,float(np.nanpercentile(np.abs(mat),96)))
    im=ax.imshow(z,cmap="RdYlGn",vmin=-extent,vmax=extent,aspect="auto")
    ax.set_yticks(range(len(fracs)),[f"{int(x*100)}%" for x in fracs])
    ax.set_xticks(range(len(sev)),[str(x).rstrip("0").rstrip(".") for x in sev])
    ax.set_xlabel("MAD-scaled severity");ax.set_ylabel("Contamination fraction")
    ax.set_title("Observed fraction × severity cells: DE average of MSE and Q95 gains")
    for i in range(len(fracs)):
        for j in range(len(sev)):
            ax.text(j,i,f"{mat[i,j]:+.1f}\n(n={ct[i,j]})" if ct[i,j] else "not\nsampled",
                    va="center",ha="center",fontsize=7)
    cb=fig.colorbar(im,ax=ax);cb.set_label("Descriptive average of two gains (%)")
    fig.text(.5,-.04,"Counts are observed source-scenario combinations across 6 families × 3 sizes; "
             "only cells selected in the original outcome-blind design are shown.",
             ha="center",fontsize=8)
    for ext in ("png","svg"):
        fig.savefig(out/f"figure_Q2_DE_fraction_severity.{ext}",dpi=230,bbox_inches="tight",pad_inches=.18)
    plt.close(fig)
    # Publication-ready narrative (English KBS prose). Avoid interpreting BH as calibrated
    # inferential support or suggesting previously unrun independent Q2 selection replays.
    winner=agg.sort_values("avg_mse_gain_pct",ascending=False).iloc[0]
    losing=agg.sort_values("avg_mse_gain_pct").iloc[0]
    overall=engine[(engine.method=="de")&(engine.benchmark_role=="own")].iloc[0]
    positives=int(overall.joint_positive)
    obs=int(overall.observations)
    practical=int(overall.joint_5pct)
    readme=f"""# Q2 — Independent within-family regime analysis

## Status
All 18 original family × sample-size blocks passed completeness and SHA-256
checks. Exactly 180 original archived Held Out score ZIPs, the frozen original
Discovery benchmark map and 241 prospective supported scenario IDs were used.
**No new Discovery, score simulation or optimizer training was performed.**

## Primary question
How do distribution family, sample size, original contamination mechanism,
fraction and MAD-scaled severity affect the matched two-loss performance of
the original frozen composites relative to classical estimators?

## Scope and estimand
The principal analysis uses DE candidates trained and independently evaluated
WITHIN THE SAME distribution family; this is distinct from cross-family transfer
(Q3). Ten original training seeds are crossed with ten independent Held Out
evaluation seeds. Four engines and both original frozen reference policies are
retained as sensitivity, not conflated with the primary DE/own-reference analysis.

The original source grid contains six contamination mechanisms with 40 selected
fraction × severity settings each, plus one clean reference. It is NOT a full
seven-fraction by nine-severity factorial per mechanism: 23 of 63 possibilities
per mechanism were never sampled (138 missing mechanism-specific combinations).
Any interactions are descriptive/local within the observed design.

## Initial descriptive finding — NOT a new confirmatory Q2 claim
The DE vs original frozen classical benchmark panel includes {obs} independently
evaluated regime summaries at the original supported non-clean scenario level,
of which {positives} ({100*positives/obs:.2f}%) show positive gains in BOTH
MSE and Q95 and {practical} ({100*practical/obs:.2f}%) show at least 5%
descriptive gain on both metrics. The 5% practical threshold is exploratory.
The most favorable family/mechanism average for MSE is {winner.family} /
{winner.mechanism} ({winner.avg_mse_gain_pct:+.2f}%), and the least favorable
is {losing.family} / {losing.mechanism} ({losing.avg_mse_gain_pct:+.2f}%).
These are observed associations, not causal effects or calibrated discoveries.

## Uncertainty audit
There are {len(tests)} two-way crossed training/evaluation bootstrap panels
(2,048 replays each), including the clean reference. The prespecified analysis
inventory for this *posthoc* Q2 investigation contains 216 DE-vs-own mechanism
metric comparisons. The reported 216-family BH q-values are exploratory.
Uncertainties are conditional on the 40 fixed selected scenarios per mechanism.
They do not incorporate full original HPO selection, a validated Q2 global
dependency calibration, or a new evaluation sample. Q1 Stage 12 error-rate
calibration does NOT transfer to these Q2 panels.

## Scientific interpretation
Regime differences should be reported as a continuous two-objective response,
including adverse performance. Mechanism/fraction/severity interactions are
not identified over the 138 unobserved mechanism-specific cells. Comparisons
of model robustness under new parameters/contamination mechanisms and across
source families remain within Q3, not Q2.

## Permanent outputs
- Q2_TABLE_FAMILY_BY_MECHANISM_DE_OWN.csv
- Q2_TABLE_FAMILY_BY_SAMPLE_SIZE_DE_OWN.csv
- Q2_TABLE_FOUR_METHOD_BENCHMARK_SENSITIVITY.csv
- Q2_TABLE_LOCAL_NEIGHBOR_SENSITIVITY.csv
- Q2_PRIMARY_DE_216_EXPLORATORY_CONTRASTS.csv
- Q2_ALL_TWO_WAY_BOOTSTRAP_EFFECTS.csv
- Q2_ALL_FACTOR_PROFILES.csv
- Q2_ALL_OBSERVED_LOCAL_NEIGHBORS.csv
- 2 publication figures in both SVG and PNG, tied to the above original values
- SHA-256 verified block data in ../blocks, audit JSON and original lineage

## Q2-F manuscript integration
The publication integration job must use authorized write access to
ALRIER/Genetic_Algorithms. If such authorization is not present, these
manuscript-ready outputs are retained in Q2 and the Q2-F job fails visibly.
No duplicate canonical manuscript is created in T3.
"""
    (out/"Q2_RESULTS_AND_LIMITATIONS.md").write_text(readme)
    gate=dict(scientific_scope="Q2 within-family 241 original supported scenarios",
        status="PASS_Q2_A_TO_E_REUSE_ORIGINAL",all_18_blocks_verified=True,
        recovered_original_archives=len(lineages),scenario_rows=len(sc),bootstrap_panels=len(bs),
        primary_de_mechanism_contrasts=len(de_own),bootstrap_replays_per_panel=BOOT,
        counts=dict(positive=positives,eligible=obs,practical_5pct=practical),
        complete_factorial=False,source_hash_audited=True,no_retraining=True,
        independent_validation="10 original Held Out evaluation seeds 10–19",
        inference_status="Exploratory, crossed-bootstrap conditional on fixed selected scenarios; no familywise calibrated Q2 error-rate guarantee",
        source_blocks=manifest)
    (out/"Q2_SCIENTIFIC_AUDIT.json").write_text(json.dumps(gate,indent=2)+"\n")
    manifest_sha={p.name:dict(sha256=sha(p),bytes=p.stat().st_size)
                  for p in out.iterdir() if p.is_file()}
    (out/"Q2_SYNTHESIS_SHA256_MANIFEST.json").write_text(json.dumps(manifest_sha,indent=2)+"\n")
    check(len(manifest_sha)>=11,"missing one of Q2 A-E publication objects")
    print("Q2_SYNTHESIS_SCIENTIFIC_PASS",json.dumps({
        "blocks":18,"original_source_archives":len(lineages),"bootstrap_panels":len(bs),
        "primary_panels":len(de_own),"DE_own_joint_positive":positives,
        "DE_own_eligible":obs,"output_files":len(manifest_sha)},sort_keys=True),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("root",type=Path)
    a=p.parse_args()
    build(a.root)
if __name__=="__main__":main()
