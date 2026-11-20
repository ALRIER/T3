#!/usr/bin/env python3
"""Publication-grade descriptive cross-family Real World figure from ORIGINAL T3 tiers.
No empirical-family truth assumption, no BH or optimizer recomputation.
"""
import argparse,csv,json,hashlib,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
LABELS={"normal":"Normal","lognormal":"Lognormal","weibull":"Weibull","invgauss":"Inv. Gauss",
        "exgaussian":"Ex Gaussian","exwald":"Ex Wald"}
BASE=Path("Q2/F3/transfer_recovery/two_policy/runs/44748009646")
def check(x,msg):
 if not x:raise RuntimeError("T3_XFAMILY_FIGURE_GATE:"+msg)
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def read(p):
 with p.open(newline="",encoding="utf8") as f:return list(csv.DictReader(f))
def main(out):
 out=Path(out);check(not out.exists(),"Publication output immutable");out.mkdir(parents=True)
 a=json.loads((BASE/"REALWORLD_TWO_POLICY_SCIENTIFIC_AUDIT.json").read_text())
 check(a["status"]=="PASS_ORIGINAL_RW_SOURCE_VS_DESTINATION_TRANSFER_RECONCILIATION",
       "source and destination policy original audit")
 p=BASE/"REALWORLD_TWO_ORIGINAL_POLICIES_ENGINE_SOURCE_DEST_TABLE.csv"
 rows=read(p);check(rows,"missing source-by-estimated-destination science")
 cases=[r for r in rows if r["benchmark_policy"]=="source" and
        r["original_inferential_panel"]=="secondary" and
        r["transfer_scope"]=="cross_family_transfer"]
 check(cases,"cross-family profile rows")
 plt.rcParams.update({"font.size":9,"font.family":"DejaVu Sans"})
 fig,axes=plt.subplots(1,2,figsize=(13,5),sharex=True,sharey=True)
 stats=[]
 for ax,role in zip(axes,("own","mean")):
  group=[r for r in cases if r["comparator"]==role]
  obs={};num={};wins={}
  for f in FAMILIES:
   for d in FAMILIES:
    x=[r for r in group if r["source_family"]==f and r["empirical_destination_family"]==d]
    denom=sum(int(r["eligible"]) for r in x)
    success=sum(int(r["original_descriptive_joint"]) for r in x)
    infer=sum(int(r["original_joint_BH_CI"]) for r in x)
    if denom:
     obs[f,d]=100*success/denom;num[f,d]=denom;wins[f,d]=success
     stats.append(dict(reference_policy="source",original_panel="secondary",comparator=role,
       source_family=f,empirically_assigned_destination_family=d,
       original_scored_candidate_contrasts=denom,original_descriptive_joint_contrasts=success,
       original_joint_BH_CI=infer,descriptive_joint_pct=100*success/denom))
  mat=np.array([[obs.get((f,d),np.nan) for d in FAMILIES]for f in FAMILIES])
  im=ax.imshow(mat,vmin=0,vmax=100,cmap="YlGnBu",aspect="equal")
  ax.set_title("Source-selected classical benchmark" if role=="own" else "Sample mean benchmark")
  ax.set_xticks(range(6),[LABELS[f] for f in FAMILIES],rotation=30,ha="right",fontsize=8)
  ax.set_yticks(range(6),[LABELS[f] for f in FAMILIES],fontsize=9)
  for i,f in enumerate(FAMILIES):
   for j,d in enumerate(FAMILIES):
    if (f,d) not in obs:continue
    score=obs[f,d]
    ax.text(j,i,f"{score:.0f}%\n{wins[f,d]}/{num[f,d]}",
         ha="center",va="center",fontsize=6.8,
         color="white" if score>68 else "#26333C")
  ax.set_xlabel("Outcome-blind estimated empirical destination family")
 axes[0].set_ylabel("Original frozen candidate's training family")
 fig.colorbar(im,ax=axes.ravel().tolist(),shrink=.72,pad=.016,label="Original descriptive dual-loss wins (%)")
 fig.subplots_adjust(left=.12,right=.91,bottom=.20,top=.88,wspace=.1)
 for fmt in ("png","svg"):
  kw={"dpi":220} if fmt=="png" else {}
  fig.savefig(out/f"results_q2_crossfamily_realworld_original_profiles.{fmt}",
              bbox_inches="tight",facecolor="white",**kw)
 plt.close(fig)
 check(len(stats)>0,"No observed destination family profile cells")
 with (out/"REALWORLD_ORIGINAL_SOURCE_DESTINATION_FIGURE_CELLS.csv").open("w",newline="") as h:
  w=csv.DictWriter(h,fieldnames=list(stats[0]));w.writeheader();w.writerows(stats)
 # Enumerate original scope accounting, not a new significance calculation.
 src=read(BASE/"REALWORLD_TWO_ORIGINAL_CLASSICAL_POLICIES_SCOPE_TABLE.csv")
 subset=[r for r in src if r["transfer_scope"]=="cross_family_transfer"]
 check(len(subset)==8 and len({(r["benchmark_policy"],r["original_inferential_panel"],r["comparator"]) for r in subset})==8,
       "8 original cross family scopes")
 with (out/"REALWORLD_ORIGINAL_CROSSFAMILY_8_POLICY_PANELS.csv").open("w",newline="") as h:
  w=csv.DictWriter(h,fieldnames=list(subset[0]));w.writeheader();w.writerows(subset)
 paths={}
 for f in out.iterdir():
  if f.is_file():paths[f.name]={"bytes":f.stat().st_size,"sha256":digest(f)}
 audit={"status":"PASS_ORIGINAL_CROSSFAMILY_PUBLICATION_PANELS",
      "source_original_realworld_full_science":str(BASE),
      "original_two_policy_audit_sha256":digest(BASE/"REALWORLD_TWO_POLICY_SCIENTIFIC_AUDIT.json"),
      "figure_cells":len(stats),"original_stages":["primary","secondary"],
      "original_reference_policies":["source_classical","destination_classical","mean"],
      "independent_unit":"642 empirical parent clusters",
      "original_empirical_destination_is_true_DGP":False,
      "descriptive_count_is_independent_parents":False,
      "original_BH_favorable_CI_counts_recomputed":False,
      "no_original_optimizer_or_score_rerun":True,"files":paths}
 (out/"Q2_CROSSFAMILY_PUBLICATION_AUDIT.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n")
 (out/"Q2_CROSSFAMILY_OUTPUT_SHA256_MANIFEST.json").write_text(json.dumps(
  {p.name:{"sha256":digest(p),"bytes":p.stat().st_size}for p in out.iterdir()if p.is_file()},indent=2,sort_keys=True)+"\n")
 print("REALWORLD_SOURCE_TO_EMPIRICAL_DESTINATION_PUBLICATION_PASS",len(stats),flush=True)
if __name__=="__main__":
 parser=argparse.ArgumentParser();parser.add_argument("--out",required=True)
 main(parser.parse_args().out)
