#!/usr/bin/env python3
"""Q2/F3 candidate-level publication supplement, using immutable original archived summaries.
No retraining, no new inference, no untested scenario interpolation.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Q2/F3/runs/44622921203/publication"
TARGET = ROOT / "Q2/F3/leaderboards"
TARGET.mkdir(parents=True, exist_ok=True)
BREADTH = SOURCE / "Q2_F3_ALL_FROZEN_CANDIDATE_BREADTH.csv"
POCKETS = SOURCE / "Q2_F3_ALL_FROZEN_CANDIDATE_POCKETS.csv"
SOURCES = {
    BREADTH.name: "464f75ab2a7808df8c360131cd214ed2387b453493cd31b8914c8aeee5bf96c2",
    POCKETS.name: "4ada02a2e3a08c62cb01d87c27764dc3bee6d8ea4b4bf21ae82f8d4c7ad243ff",
}
for path in (BREADTH, POCKETS):
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == SOURCES[path.name], (path,actual)
def read_csv(path):
    with path.open(newline="",encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
def to_int(x):
    return int(x) if x != "" else 0
def clean_float(x):
    return None if x == "" else float(x)
def output_csv(name, rows, columns):
    p=TARGET/name
    with p.open("w",encoding="utf-8",newline="") as handle:
        wr=csv.DictWriter(handle,fieldnames=columns,extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)
    return p
breadth=read_csv(BREADTH)
pockets=read_csv(POCKETS)
assert len(breadth)==1440 and len(pockets)==8640, (len(breadth),len(pockets))
assert len({r["frozen_candidate_key"] for r in breadth})==720
assert {r["benchmark_role"] for r in breadth}=={"own","mean"}
assert all(to_int(r["eligible_scenarios"])==240 for r in breadth)
assert all(to_int(r["universal_within_tested_family_size_support"])==0 for r in breadth)
assert all(r["full_original_weight_sha_identity"]=="NOT_VERIFIED_HERE" for r in breadth)
for r in breadth:
    for c in ("count_joint","count_mse_only","count_q95_only","count_neither","count_tied",
              "pareto_nondominated_count","largest_joint_winner_connected_component"):
        r[c]=to_int(r[c])
    assert sum(r[k] for k in ("count_joint","count_mse_only","count_q95_only","count_neither","count_tied"))==240
    assert r["largest_joint_winner_connected_component"] <= r["count_joint"]
    r["observed_one_hop_joint_retention"]=clean_float(r["observed_one_hop_joint_retention"])
    r["sample_n"]=int(r["sample_n"])
    r["training_seed"]=int(r["training_seed"])
    r["mechanism_joint_max"]=0
grouped=defaultdict(list)
for r in breadth:
    grouped[(r["family"],r["sample_n"],r["benchmark_role"])].append(r)
assert len(grouped)==36 and all(len(v)==40 for v in grouped.values())

# Models evaluated under the same family-size support share denominators and benchmark policy.
# Ranks use a single explicit within-block descriptive joint-coverage axis;
# rank ties remain ties; secondary columns do not silently break scientific ties.
def rank(vals, r, field):
    return 1+sum(x[field]>r[field] for x in vals)
all_rows=[]
for _,rows in sorted(grouped.items()):
    for r in rows:
        x=dict(r)
        x["rank_joint_within_family_size_reference"]=rank(rows,r,"count_joint")
        engine_rows=[v for v in rows if v["method"]==r["method"]]
        x["rank_joint_within_engine_family_size_reference"]=rank(engine_rows,r,"count_joint")
        x["rank_mse_only_within_block"]=rank(rows,r,"count_mse_only")
        x["rank_q95_only_within_block"]=rank(rows,r,"count_q95_only")
        x["rank_pareto_nondominated_within_block"]=rank(rows,r,"pareto_nondominated_count")
        x["rank_largest_connected_pocket_within_block"]=rank(rows,r,"largest_joint_winner_connected_component")
        x["rank_is_cross_family_predictive"]="NO"
        x["stage_weight_sha_match_verified"]="NO"
        all_rows.append(x)
cols=["family","sample_n","benchmark_role","method","training_seed","frozen_candidate_key",
      "eligible_scenarios","count_joint","count_mse_only","count_q95_only","count_neither",
      "pareto_nondominated_count","largest_joint_winner_connected_component",
      "observed_one_hop_joint_retention","original_outcome_blind_edges",
      "rank_joint_within_family_size_reference",
      "rank_joint_within_engine_family_size_reference","rank_mse_only_within_block",
      "rank_q95_only_within_block","rank_pareto_nondominated_within_block",
      "rank_largest_connected_pocket_within_block","rank_is_cross_family_predictive",
      "stage_weight_sha_match_verified"]
output_csv("Q2_F3_ALL_1440_CANDIDATE_DESCRIPTIVE_RANKS.csv",all_rows,cols)

def leaders(rows, field):
    best=max(r[field] for r in rows)
    ties=[r for r in rows if r[field]==best]
    return best, sorted(ties,key=lambda x:x["frozen_candidate_key"])
fields=[
    ("joint","count_joint"),
    ("mse_only","count_mse_only"),
    ("q95_only","count_q95_only"),
    ("pareto_nondominated","pareto_nondominated_count"),
    ("connected_pocket","largest_joint_winner_connected_component"),
]
block_leaders=[]
taxonomy_leaders=[]
for (family,n,ref),rows in sorted(grouped.items()):
    for role,metric in fields:
        best,ties=leaders(rows,metric)
        # If no victories, report NO_WINNER, not a fabricated best candidate.
        taxonomy_leaders.append(dict(family=family,sample_n=n,benchmark_role=ref,
            taxonomy_axis=role,eligible_per_candidate=240,winning_value=best,
            number_of_tied_candidates=len(ties) if best>0 else 0,
            winning_candidate_keys=";".join(x["frozen_candidate_key"] for x in ties) if best>0 else "NO_POSITIVE_WINNER",
            winning_engines=";".join(sorted({x["method"] for x in ties})) if best>0 else "NONE",
            comparison_unit="within_family_size_reference",type="descriptive_not_inferential"))
    best,ties=leaders(rows,"count_joint")
    block_leaders.append(dict(family=family,sample_n=n,benchmark_role=ref,
        block_candidates=len(rows),eligible_scenarios_per_candidate=240,
        joint_victories_max=best,number_of_joint_ties=len(ties) if best>0 else 0,
        leader_candidate_keys=";".join(x["frozen_candidate_key"] for x in ties) if best>0 else "NO_POSITIVE_WINNER",
        leading_engines=";".join(sorted({x["method"] for x in ties})) if best>0 else "NONE",
        universal_candidate_count=0,interpretation="descriptive_count_not_out_of_family_proof"))
output_csv("Q2_F3_36_FAMILY_SIZE_BENCHMARK_LEADERS.csv",block_leaders,list(block_leaders[0]))
output_csv("Q2_F3_180_BLOCK_TAXONOMY_LEADERS.csv",taxonomy_leaders,list(taxonomy_leaders[0]))

pocket_grouped=defaultdict(list)
pocket_agg=defaultdict(int)
for r in pockets:
    key=(r["family"],int(r["sample_n"]),r["benchmark_role"],r["mechanism"])
    pocket_grouped[key].append(r)
    pocket_agg[(r["frozen_candidate_key"],r["benchmark_role"])]+=to_int(r["joint"])
assert len(pocket_grouped)==216 and all(len(rows)==40 for rows in pocket_grouped.values())
for row in breadth:
    assert pocket_agg[(row["frozen_candidate_key"],row["benchmark_role"])]==row["count_joint"]
mechanism_leaders=[]
for (family,n,ref,mechanism),rows in sorted(pocket_grouped.items()):
    maximum=max(to_int(x["joint"]) for x in rows)
    ties=sorted([x for x in rows if to_int(x["joint"])==maximum],key=lambda x:x["frozen_candidate_key"])
    mechanism_leaders.append(dict(family=family,sample_n=n,benchmark_role=ref,
        mechanism=mechanism,eligible_scenarios_per_candidate=40,
        max_joint_wins=maximum,number_of_joint_ties=len(ties) if maximum>0 else 0,
        leaders=";".join(x["frozen_candidate_key"] for x in ties) if maximum>0 else "NO_POSITIVE_WINNER",
        engines=";".join(sorted({x["method"] for x in ties})) if maximum>0 else "NONE",
        no_unobserved_scenarios_imputed="TRUE"))
output_csv("Q2_F3_216_MECHANISM_BLOCK_LEADERS.csv",mechanism_leaders,list(mechanism_leaders[0]))

global_extrema=[]
for ref in ("own","mean"):
    rows=[r for r in breadth if r["benchmark_role"]==ref]
    for role,metric in fields:
        best,ties=leaders(rows,metric)
        global_extrema.append(dict(benchmark_role=ref,taxonomy_axis=role,highest_observed_count=best,
            eligible_per_candidate=240,number_of_tied_candidates=len(ties) if best>0 else 0,
            candidate_keys=";".join(x["frozen_candidate_key"] for x in ties) if best>0 else "NO_POSITIVE_WINNER",
            warning="Cross-block extrema are descriptive, not transferable rankings"))
output_csv("Q2_F3_10_OVERALL_CANDIDATE_EXTREMA.csv",global_extrema,list(global_extrema[0]))

# Visuals are limited to actually observed candidates. Strong baseline vs mean kept separate.
labels={"ga":"GA","nsga2":"NSGA-II","de":"DE","dirichlet":"Dirichlet"}
colors={"ga":"#3685a1","nsga2":"#9c61a0","de":"#e09a38","dirichlet":"#4a9e78"}
fig,axs=plt.subplots(1,2,figsize=(15,6),sharey=True,constrained_layout=True)
for ax,ref in zip(axs,("own","mean")):
    top=sorted([r for r in breadth if r["benchmark_role"]==ref],
        key=lambda x:(-x["count_joint"],x["frozen_candidate_key"]))[:12]
    y=np.arange(len(top))
    ax.barh(y,[x["count_joint"] for x in top],color=[colors[x["method"]] for x in top])
    ax.set_yticks(y,[x["frozen_candidate_key"].replace("|"," / ") for x in top],fontsize=8)
    ax.invert_yaxis()
    ax.set_title("Selected classical" if ref=="own" else "Sample mean")
    ax.set_xlabel("Observed joint-win cells (of 240 per frozen candidate)")
    ax.grid(axis="x",alpha=.2)
fig.suptitle("Q2: Top observed frozen-candidate joint-coverage counts\nSeparate benchmark policies; no cross-family rank implied",fontsize=12)
fig.savefig(TARGET/"results_q2_f3_candidate_top12.png",dpi=200,bbox_inches="tight")
plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(13,5.5),constrained_layout=True)
for ax,ref in zip(axs,("own","mean")):
    rows=[r for r in breadth if r["benchmark_role"]==ref]
    for method in labels:
        rr=[r for r in rows if r["method"]==method]
        ax.scatter([r["count_joint"] for r in rr],
                   [r["largest_joint_winner_connected_component"] for r in rr],
                   color=colors[method],label=labels[method],alpha=.6,s=18)
    ax.set_title("Selected classical" if ref=="own" else "Sample mean")
    ax.set_xlabel("Joint-win cells (0-240)")
    ax.set_ylabel("Largest observed contiguous joint-win pocket")
    ax.grid(alpha=.2)
axs[1].legend(loc="lower right",ncol=2,fontsize=9)
fig.suptitle("Q2: Candidate coverage versus local robustness\n720 fixed weights per reference; all observed scenarios only")
fig.savefig(TARGET/"results_q2_f3_candidate_pockets.png",dpi=210,bbox_inches="tight")
plt.close(fig)

fig, axs=plt.subplots(1,2,figsize=(15,6.5),constrained_layout=True)
family_order=["normal","lognormal","weibull","invgauss","exgaussian","exwald"]
for ax,ref in zip(axs,("own","mean")):
    mat=np.zeros((18,4))
    for fi,fam in enumerate(family_order):
        for ni,n in enumerate((200,1000,3000)):
            b=grouped[(fam,n,ref)]
            for mi,m in enumerate(labels):
                mat[fi*3+ni,mi]=max(x["count_joint"] for x in b if x["method"]==m)
    im=ax.imshow(mat,aspect="auto",interpolation="nearest",cmap="viridis",vmin=0,vmax=240)
    ax.set_xticks(range(4),[labels[m] for m in labels],rotation=20)
    ax.set_yticks(range(18),[f"{fam}, n={n}" for fam in family_order for n in (200,1000,3000)],fontsize=8)
    ax.set_title("Selected classical" if ref=="own" else "Sample mean")
    for i in range(18):
        for j in range(4):
            color="white" if mat[i,j]<35 or mat[i,j]>175 else "black"
            ax.text(j,i,str(int(mat[i,j])),ha="center",va="center",color=color,fontsize=7)
fig.colorbar(im,ax=axs.tolist(),shrink=.7,label="Best individual frozen candidate in block: joint wins / 240")
fig.suptitle("Q2: Best individual per method and family–sample-size block\nDo not read engine maxima as a single universal weight")
fig.savefig(TARGET/"results_q2_f3_candidate_block_maxima.png",dpi=190,bbox_inches="tight")
plt.close(fig)

produced=sorted(p for p in TARGET.iterdir() if p.is_file() and p.name.startswith(("Q2_F3_","results_q2_f3_candidate_")) and p.suffix in (".csv",".png"))
files={p.name:{"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in produced}
audit=dict(schema="PUB1_Q2_F3_CANDIDATE_LEADERBOARDS_V1",
    status="PASS_REUSE_ORIGINAL_FROZEN_CANDIDATE_EVIDENCE",
    source_breadth_sha256=SOURCES[BREADTH.name],
    source_pockets_sha256=SOURCES[POCKETS.name],
    source_run=44622921203,
    unique_weight_keys=720,candidate_benchmark_rows=1440,
    candidate_mechanism_rows=8640,family_sample_benchmark_blocks=36,
    block_taxonomy_leaders=len(taxonomy_leaders),
    mechanism_block_leaders=len(mechanism_leaders),
    within_tested_support_universal_candidates=0,
    candidate_key_definition="family|sample_n|method|training_seed",
    physical_cross_stage_weight_SHA_identity="NOT_VERIFIED_BY_THIS_ANALYSIS",
    inference="DESCRIPTIVE_NOT_SELECTION_AWARE",
    formal_type_I_error_guarantee="NOT_ESTABLISHED",
    no_new_training_or_scoring=True,
    no_multiplicity_recalculation=True,
    no_unobserved_grid_cells_filled=True,
    files=files)
(TARGET/"Q2_F3_CANDIDATE_LEADERBOARD_AUDIT.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n")
files2={p.name:{"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(TARGET.iterdir()) if p.is_file() and p.name!="Q2_F3_CANDIDATE_SHA256_MANIFEST.json"}
(TARGET/"Q2_F3_CANDIDATE_SHA256_MANIFEST.json").write_text(json.dumps(files2,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":audit["status"],"ranked":len(all_rows),"leaderboards":len(taxonomy_leaders),"mechanisms":len(mechanism_leaders),"files":len(files2),"extrema":global_extrema},indent=2))
