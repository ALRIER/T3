#!/usr/bin/env python3
"""Q2 F3 tables and figures from original archived four-engine taxonomy, no retraining."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
F=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
N=(200,1000,3000)
M=("ga","nsga2","de","dirichlet")
R=("own","mean")
MECH=("upper_tail","lower_tail","symmetric_t","point_mass","clustered_upper","clustered_symmetric")
CL=("joint","mse_only","q95_only","neither","tied")
MN={"ga":"GA","nsga2":"NSGA-II","de":"DE","dirichlet":"Dirichlet"}
FN={"normal":"Normal","lognormal":"Lognormal","weibull":"Weibull","invgauss":"Inverse Gaussian","exgaussian":"Ex Gaussian","exwald":"Ex Wald"}
CM={"joint":"#007F76","mse_only":"#397BB6","q95_only":"#E69F00","neither":"#A9ADB5","tied":"#7060A5"}
ROOT=Path("Q2/F3/runs/44613985618")
BOOT=Path("Q2/runs/44599590079/synthesis/Q2_ALL_TWO_WAY_BOOTSTRAP_EFFECTS.csv")
def must(ok,msg):
    if not ok:raise RuntimeError("Q2_F3_PAPER_GATE: "+msg)
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for x in iter(lambda:f.read(1<<20),b""):h.update(x)
    return h.hexdigest()
def write(x,p):x.to_csv(p,index=False,float_format="%.12g")
def bh(x):
    p=np.asarray(x,dtype=float)
    order=np.argsort(p)
    q=np.empty(len(p))
    q[order]=np.minimum(1,np.minimum.accumulate((p[order]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1])
    return q
def saveplot(fig,out,name):
    fig.savefig(out/(name+".png"),dpi=210,bbox_inches="tight",facecolor="white")
    fig.savefig(out/(name+".svg"),bbox_inches="tight",facecolor="white")
    plt.close(fig)
def main(root):
    src=root/"blocks";out=root/"publication"
    must(src.is_dir() and not out.exists(),"Original taxonomy shards required; never overwrite a published run")
    out.mkdir(parents=True)
    engines=[];models=[];pockets=[];blocks=[]
    for f in F:
      for n in N:
        d=src/(f+"-n"+str(n))
        m=json.loads((d/"Q2_F3_TAXONOMY_BLOCK_AUDIT.json").read_text())
        must(m["status"]=="PASS_Q2_F3_ALL_FOUR_ENGINES_CANDIDATE_TAXONOMY" and m["source_family"]==f and m["sample_n"]==n,"source manifest identity")
        for name,z in m["source_files"].items():
            p=d/name
            must(p.is_file() and p.stat().st_size==z["bytes"] and sha(p)==z["sha256"],"source SHA "+name)
        en=pd.read_csv(d/"ENGINE_SCENARIO_TAXONOMY.csv")
        ca=pd.read_csv(d/"CANDIDATE_BREADTH_AND_UNIVERSALITY.csv")
        po=pd.read_csv(d/"CANDIDATE_MECHANISM_POCKETS.csv")
        must((len(en),len(ca),len(po))==(1928,80,480),"four-engine block dimensional gate")
        en["family"]=f
        en["sample_n"]=n
        engines.append(en);models.append(ca);pockets.append(po)
        blocks.append(dict(family=f,sample_n=n,sha256_of_block_manifest=sha(d/"Q2_F3_TAXONOMY_BLOCK_AUDIT.json")))
    e=pd.concat(engines,ignore_index=True)
    b=pd.concat(models,ignore_index=True)
    pockets=pd.concat(pockets,ignore_index=True)
    must(len(e)==34704 and len(b)==1440 and len(pockets)==8640,"original total observations")
    e=e[e.mechanism!="clean"].copy()
    must(len(e)==34560,"contaminated original observations")
    rows=[]
    for (method,ref),x in e.groupby(["method","benchmark_role"],sort=False):
        counts=x.winner_class.value_counts()
        z=dict(method=method,benchmark_role=ref,eligible=len(x))
        for cls in CL:z[cls]=int(counts.get(cls,0))
        z["pareto_nondominated_against_other_engine_means"]=int(x.pareto_nondominated_among_4_engine_means.sum())
        z["median_mse_loss_ratio"]=float(np.median(x.mse_ratio))
        z["median_q95_loss_ratio"]=float(np.median(x.q95_ratio))
        z["upper95_mse_loss_ratio"]=float(np.quantile(x.mse_ratio,.95))
        z["upper95_q95_loss_ratio"]=float(np.quantile(x.q95_ratio,.95))
        must(len(x)==4320 and sum(z[c] for c in CL)==4320,"complete classification")
        rows.append(z)
    total=pd.DataFrame(rows).sort_values(["benchmark_role","method"])
    write(total,out/"Q2_F3_TABLE_FOUR_ENGINE_FULL_TAXONOMY.csv")
    fsize=e.groupby(["family","sample_n","method","benchmark_role","winner_class"]).size().unstack(fill_value=0).reset_index()
    for cls in CL:
        if cls not in fsize:fsize[cls]=0
    fsize["eligible"]=fsize[list(CL)].sum(axis=1)
    must(len(fsize)==144,"family-size engine benchmark strata")
    write(fsize,out/"Q2_F3_TABLE_FAMILY_SIZE_ENGINE.csv")
    mech=e.groupby(["family","mechanism","method","benchmark_role","winner_class"]).size().unstack(fill_value=0).reset_index()
    for cls in CL:
        if cls not in mech:mech[cls]=0
    mech["eligible"]=mech[list(CL)].sum(axis=1)
    must(len(mech)==288 and (mech.eligible==120).all(),"six families six mechanisms and four engines")
    write(mech,out/"Q2_F3_TABLE_FAMILY_MECHANISM_ENGINE.csv")
    b["any_joint"]=b.count_joint>0
    candidate_summary=b.groupby(["method","benchmark_role"],as_index=False).agg(
        eligible_candidates=("frozen_candidate_key","size"),any_joint_candidates=("any_joint","sum"),
        within_Q2_support_universal=("universal_within_tested_family_size_support","sum"),
        mean_joint_scenarios_per_candidate=("count_joint","mean"),
        median_largest_joint_component=("largest_joint_winner_connected_component","median"),
        total_neighbor_win_start_directions=("joint_winner_to_all_neighbor_directions","sum"),
        total_neighbor_retained_win_directions=("joint_winner_to_joint_neighbor_directions","sum"))
    candidate_summary["one_hop_retention_conditional"]=candidate_summary.total_neighbor_retained_win_directions / candidate_summary.total_neighbor_win_start_directions.clip(lower=1)
    must((candidate_summary.eligible_candidates==180).all(),"candidate identities pooled only within engine")
    write(candidate_summary,out/"Q2_F3_TABLE_FOUR_ENGINE_NEIGHBORHOOD.csv")
    write(b,out/"Q2_F3_ALL_FROZEN_CANDIDATE_BREADTH.csv")
    write(pockets,out/"Q2_F3_ALL_FROZEN_CANDIDATE_POCKETS.csv")
    write(pd.DataFrame(blocks),out/"Q2_F3_BLOCK_SOURCE_SHA256.csv")
    source=pd.read_csv(BOOT)
    source=source[source.mechanism.isin(MECH)].copy()
    must(len(source)==1728 and not source.duplicated(["family","sample_n","method","benchmark_role","mechanism","metric"]).any(),"1728 original mechanism-level contrasts")
    for metric in ("mse_gain_pct","q95_gain_pct"):
        sub=source.metric==metric
        must(int(sub.sum())==864,"full 864 candidate mechanisms per metric")
        source.loc[sub,"BH_q_all864_per_metric"]=bh(source.loc[sub,"exploratory_bootstrap_p"].values)
    source["positive_CI"]=(source.ci95_low>0)&(source.average_gain_pct>0)
    source["positive_BH_CI"]=source.positive_CI&(source.BH_q_all864_per_metric<=.05)
    pivot=source.pivot(index=["family","sample_n","method","benchmark_role","mechanism"],
        columns="metric",values=["positive_CI","positive_BH_CI"])
    pivot.columns=["_".join(z) for z in pivot.columns]
    pivot=pivot.reset_index()
    pivot["joint_CI"]=pivot["positive_CI_mse_gain_pct"]&pivot["positive_CI_q95_gain_pct"]
    pivot["joint_BH"]=pivot["positive_BH_CI_mse_gain_pct"]&pivot["positive_BH_CI_q95_gain_pct"]
    ev=pivot.groupby(["method","benchmark_role"],as_index=False).agg(
        mechanism_tests=("joint_CI","size"),joint_CI=("joint_CI","sum"),
        joint_BH_exploratory=("joint_BH","sum"),
        MSE_BH_exploratory=("positive_BH_CI_mse_gain_pct","sum"),
        Q95_BH_exploratory=("positive_BH_CI_q95_gain_pct","sum"))
    must(len(pivot)==864 and (ev.mechanism_tests==108).all(),"complete 108 effects per engine/reference")
    write(source,out/"Q2_F3_ALL_1728_EXPLORATORY_BH_METRICS.csv")
    write(pivot,out/"Q2_F3_ALL_864_MECHANISM_EVIDENCE.csv")
    write(ev,out/"Q2_F3_TABLE_FOUR_ENGINE_EXPLORATORY_BH.csv")

    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9.5,"axes.titlesize":11})
    # Figure 1: full taxonomy
    fig,ax=plt.subplots(2,1,figsize=(10.4,6),sharex=True)
    look=total.set_index(["method","benchmark_role"])
    for a,ref in zip(ax,R):
        left=np.zeros(4)
        for cls in CL:
            values=np.array([look.loc[(m,ref),cls]/4320*100 for m in M])
            a.barh(np.arange(4),values,left=left,height=.67,color=CM[cls],label=cls.replace("_"," ").title())
            left+=values
        a.set_yticks(np.arange(4),[MN[m] for m in M]);a.invert_yaxis()
        a.set_xlim(0,100);a.set_axisbelow(True);a.grid(axis="x",alpha=.16)
        a.set_title("Discovery-selected classical reference" if ref=="own" else "Sample mean reference",loc="left")
        a.spines[["top","right"]].set_visible(False)
    ax[1].set_xlabel("Percentage of 4,320 eligible scenario summaries")
    fig.legend(*ax[0].get_legend_handles_labels(),loc="lower center",ncol=5,frameon=False,bbox_to_anchor=(.5,-.025))
    fig.tight_layout(rect=(0,.075,1,1))
    saveplot(fig,out,"results_q2_f3_winner_taxonomy")
    # Figure 2: family-mechanism heatmaps, all four original engines against own
    fig,axes=plt.subplots(2,2,figsize=(12.4,8),sharex=True,sharey=True)
    for a,method in zip(axes.flat,M):
        z=mech[(mech.method==method)&(mech.benchmark_role=="own")]
        mat=np.array([[z.loc[(z.family==f)&(z.mechanism==mm),"joint"].iloc[0]/120*100
             for mm in MECH]for f in F])
        im=a.imshow(mat,cmap="YlGnBu",vmin=0,vmax=100,aspect="auto")
        a.set_title(MN[method],loc="left")
        a.set_xticks(np.arange(6),[mm.replace("_"," ") for mm in MECH],rotation=31,ha="right",fontsize=8)
        a.set_yticks(np.arange(6),[FN[f] for f in F],fontsize=9)
        for i in range(6):
            for j in range(6):
                a.text(j,i,f"{int(round(mat[i,j]*1.2))}/120",ha="center",va="center",fontsize=6.5,
                       color="white" if mat[i,j]>65 else "#27313C")
    fig.colorbar(im,ax=axes.ravel().tolist(),fraction=.025,pad=.015,label="Joint scenario wins (%)")
    fig.subplots_adjust(left=.17,right=.90,bottom=.12,top=.94,hspace=.36,wspace=.12)
    saveplot(fig,out,"results_q2_f3_four_engine_regimes")
    # Figure 3: reference policy effects
    fig,axes=plt.subplots(1,2,figsize=(12.5,4),sharey=True)
    for a,ref in zip(axes,R):
        z=e[e.benchmark_role==ref].groupby(["method","family"]).winner_class.agg(
          lambda q:int((q=="joint").sum())).reset_index()
        mat=np.array([[z.loc[(z.method==method)&(z.family==f),"winner_class"].iloc[0]/720*100 for f in F]for method in M])
        im=a.imshow(mat,cmap="YlGnBu",vmin=0,vmax=100,aspect="auto")
        a.set_xticks(range(6),[FN[f] for f in F],rotation=34,ha="right",fontsize=8)
        a.set_yticks(range(4),[MN[m] for m in M])
        a.set_title("Discovery-selected classical" if ref=="own" else "Sample mean")
        for i in range(4):
            for j in range(6):
                a.text(j,i,f"{mat[i,j]:.1f}",ha="center",va="center",fontsize=8,
                        color="white" if mat[i,j]>60 else "#253440")
    fig.colorbar(im,ax=axes.ravel().tolist(),fraction=.025,pad=.02,label="Joint win rate (%)")
    fig.subplots_adjust(left=.10,right=.87,bottom=.26,top=.88,wspace=.14)
    saveplot(fig,out,"results_q2_f3_benchmark_sensitivity")
    # Figure 4: same model neighborhood breadth
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    z=candidate_summary.set_index(["method","benchmark_role"])
    for a,ref in zip(axes,R):
        X=np.arange(4)
        has=np.array([z.loc[(m,ref),"any_joint_candidates"]/180*100 for m in M])
        retain=np.array([z.loc[(m,ref),"one_hop_retention_conditional"]*100 for m in M])
        a.bar(X-.18,has,.35,label="Candidates with any joint win",color="#397BB6")
        a.bar(X+.18,retain,.35,label="Observed 1-hop joint retention",color="#007F76")
        a.set_xticks(X,[MN[m] for m in M]);a.set_ylim(0,105)
        a.set_title("Selected classical" if ref=="own" else "Sample mean")
        a.grid(axis="y",alpha=.15);a.set_axisbelow(True)
        a.spines[["top","right"]].set_visible(False)
    axes[0].set_ylabel("Percent of candidates / winning-neighbor directions")
    fig.legend(*axes[0].get_legend_handles_labels(),loc="lower center",ncol=2,frameon=False,bbox_to_anchor=(.5,-.03))
    fig.tight_layout(rect=(0,.09,1,1))
    saveplot(fig,out,"results_q2_f3_neighborhood_breadth")
    # Figure 5: exploratory BH caveat
    fig,axes=plt.subplots(1,2,figsize=(10.8,4.3))
    z=ev.set_index(["method","benchmark_role"])
    for a,ref in zip(axes,R):
        x=np.arange(4)
        a.bar(x-.18,[z.loc[(m,ref),"joint_CI"] for m in M],.35,
              color="#397BB6",label="Both conditional CIs favorable")
        a.bar(x+.18,[z.loc[(m,ref),"joint_BH_exploratory"] for m in M],.35,
              color="#E69F00",label="Both exploratory BH + CIs")
        a.set_xticks(x,[MN[m] for m in M]);a.set_ylim(0,110)
        a.set_title("Selected classical" if ref=="own" else "Sample mean")
        a.grid(axis="y",alpha=.15);a.set_axisbelow(True)
        a.spines[["top","right"]].set_visible(False)
    axes[0].set_ylabel("Mechanism-level contrasts / 108 eligible")
    fig.legend(*axes[0].get_legend_handles_labels(),loc="lower center",ncol=2,frameon=False,bbox_to_anchor=(.5,-.03))
    fig.tight_layout(rect=(0,.09,1,1))
    saveplot(fig,out,"results_q2_f3_exploratory_evidence")
    expected=("results_q2_f3_winner_taxonomy","results_q2_f3_four_engine_regimes","results_q2_f3_benchmark_sensitivity",
              "results_q2_f3_neighborhood_breadth","results_q2_f3_exploratory_evidence")
    for name in expected:must((out/(name+".png")).stat().st_size>10000 and (out/(name+".svg")).stat().st_size>2000,"figures "+name)
    audit={"status":"PASS_Q2_F3_FOUR_ENGINE_PUBLICATION_PACKAGE","source_Q2_run":44599590079,
       "source_F3_run":44613985618,"original_engine_scenarios_including_clean":34704,
       "contaminated_engine_scenario_panels":34560,"candidate_scenario_panels":18*19280,
       "candidate_policy_breadth_panels":len(b),"candidate_mechanism_panels":len(pockets),
       "eligible_original_observed_edges_per_block":205,
       "BH_test_family_per_metric":864,"BH_inferential_status":"EXPLORATORY_NOT_SELECTION_AWARE",
       "independent_full_pipeline_calibration_pass":False,
       "no_new_optimizer_training":True,"original_Q2_and_F3_immutable":True,
       "four_engine_selected_classical_joint_scenario_counts":{
           m:int(look.loc[(m,"own"),"joint"])for m in M},
       "four_engine_sample_mean_joint_scenario_counts":{
           m:int(look.loc[(m,"mean"),"joint"])for m in M},
       "figures_png":list(expected),"files":{}}
    for f in sorted(out.iterdir()):
        if f.is_file():audit["files"][f.name]={"sha256":sha(f),"bytes":f.stat().st_size}
    (out/"Q2_F3_PUBLICATION_SCIENTIFIC_AUDIT.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n")
    (out/"Q2_F3_PUBLICATION_SHA256_MANIFEST.json").write_text(json.dumps(
      {p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()},indent=2,sort_keys=True)+"\n")
    print("Q2_F3_PAPER_PACKAGE_PASS",json.dumps(audit["four_engine_selected_classical_joint_scenario_counts"]),flush=True)
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--root",required=True)
    main(Path(parser.parse_args().root))
