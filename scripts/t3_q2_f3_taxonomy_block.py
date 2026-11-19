#!/usr/bin/env python3
"""Q2/F3 publication: full candidate-level objectives, Pareto and observed-neighborhood breadth.
Reads ORIGINAL frozen HeldOut paired seed records; no W refit or simulation.
"""
import argparse,csv,gzip,hashlib,json,math
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
NS=(200,1000,3000)
METHODS=("ga","nsga2","de","dirichlet")
ROLES=("own","mean")
MECHS=("upper_tail","lower_tail","symmetric_t","point_mass","clustered_upper","clustered_symmetric")
ORIGINAL=Path("Q2/runs/44599590079/blocks")
F3=Path("Q2/F3/runs/44613985618/blocks")
def check(x,message):
    if not x:raise RuntimeError("Q2_TAXONOMY_BLOCK_GATE: "+message)
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for z in iter(lambda:f.read(1<<20),b""):h.update(z)
    return h.hexdigest()
def categorise(m,c):
    t=1e-12*max(1.0,abs(m),abs(c))
    return 1 if (m<c-t) else (-1 if m>c+t else 0)
def cat(a,b):
    if a==1 and b==1:return "joint"
    if a==1:return "mse_only"
    if b==1:return "q95_only"
    if a==0 and b==0:return "tied"
    return "neither"
def dominance(a,b):
    if a>=0 and b>=0 and (a>0 or b>0):return "candidate_dominates_reference"
    if a<=0 and b<=0 and (a<0 or b<0):return "reference_dominates_candidate"
    if a==b==0:return "identical"
    return "tradeoff"
def save_table(data,path,compress=False):
    if compress:data.to_csv(path,index=False,compression={"method":"gzip","compresslevel":6})
    else:data.to_csv(path,index=False)
def frontier(sub):
    """Mark each frozen candidate relative to other engines within SAME training seed/scenario."""
    vals=sub[["mse_candidate_mean","q95_candidate_mean"]].to_numpy(dtype=float)
    dominated=np.zeros(len(vals),dtype=bool)
    for i in range(len(vals)):
        for j in range(len(vals)):
            if i==j:continue
            eps=np.array([1e-12*max(1,abs(q),abs(w)) for q,w in zip(vals[i],vals[j])])
            if bool(np.all(vals[j]<=vals[i]+eps) and np.any(vals[j]<vals[i]-eps)):
                dominated[i]=True;break
    return pd.Series(~dominated,index=sub.index)
def largest_cc(wins,adj):
    seen=set();best=0;comps=0
    for start in wins:
        if start in seen:continue
        comps+=1; stack=[start];seen.add(start);count=0
        while stack:
            a=stack.pop();count+=1
            for b in adj.get(a,()):
                if b in wins and b not in seen:seen.add(b);stack.append(b)
        best=max(best,count)
    return best,comps
def run(family,n,out):
    check(family in FAMILIES and n in NS,"invalid analysis block")
    source=ORIGINAL/(f"{family}-n{n}")
    base=F3/(f"{family}-n{n}")
    sm=json.loads((source/"Q2_BLOCK_MANIFEST.json").read_text())
    fm=json.loads((base/"F3_BLOCK_MANIFEST.json").read_text())
    check(sm["family"]==fm["family"]==family and sm["sample_n"]==fm["sample_n"]==n,"mismatched original source lineage")
    check(sm["paired_benchmark_metric_records"]==192800 and fm["original_paired_cells"]==192800,"missing paired records")
    for name,d in sm["outputs"].items():
        p=source/name
        check(p.is_file() and p.stat().st_size==d["bytes"] and sha(p)==d["sha256"],"original Q2 input SHA gate "+name)
    for name,d in fm["files"].items():
        p=base/name
        check(p.is_file() and p.stat().st_size==d["bytes"] and sha(p)==d["sha256"],"original F3 input SHA gate "+name)
    cols=["family","sample_n","scenario_id","mechanism","contamination","mad_scale",
          "method","training_seed","evaluation_seed","benchmark_role","benchmark",
          "mse_candidate","mse_reference","q95_candidate","q95_reference"]
    d=pd.read_csv(source/"paired_seed_cells.csv.gz",usecols=cols)
    check(len(d)==192800 and set(d.method)==set(METHODS) and set(d.benchmark_role)==set(ROLES),"complete original score cells")
    check(set(d.training_seed)==set(range(10)) and set(d.evaluation_seed)==set(range(10,20)),"original independent seed contract")
    check(d.scenario_id.nunique()==241 and len(d.loc[d.mechanism!="clean","scenario_id"].unique())==240,"original support identities")
    meta=d.groupby("scenario_id",sort=False)[["mechanism","contamination","mad_scale"]].first().reset_index()
    key=["method","benchmark_role","training_seed","scenario_id"]
    group=d.groupby(key,sort=False,observed=True)
    sizes=group.size()
    check(len(sizes)==19280 and (sizes==10).all(),"one independent evaluation per original seed")
    c=group[["mse_candidate","mse_reference","q95_candidate","q95_reference"]].mean().reset_index()
    c=c.merge(meta,on="scenario_id",validate="many_to_one")
    for metric in ("mse","q95"):
        diff=c[metric+"_candidate"]-c[metric+"_reference"]
        reference=c[metric+"_reference"]
        c[metric+"_candidate_mean"]=c[metric+"_candidate"]
        c[metric+"_reference_mean"]=reference
        c[metric+"_difference"]=diff
        c[metric+"_ratio"]=c[metric+"_candidate"]/np.maximum(reference,1e-14)
        c[metric+"_sign"]=[categorise(a,b) for a,b in zip(c[metric+"_candidate"],reference)]
    c["winner_class"]=[cat(a,b) for a,b in zip(c.mse_sign,c.q95_sign)]
    c["reference_relation"]=[dominance(a,b) for a,b in zip(c.mse_sign,c.q95_sign)]
    c["frozen_candidate_key"]=[f"{family}|n{n}|{m}|train{int(t):02d}" for m,t in zip(c.method,c.training_seed)]
    c["individual_weight_sha_verified_in_this_job"]=False
    c["original_training_seeds"]=10
    c["independent_evaluation_seeds"]=10
    c["pareto_nondominated_vs_other_3_engines"]=False
    for _,sub in c.groupby(["benchmark_role","training_seed","scenario_id"],sort=False):
        check(len(sub)==4,"four matched frozen engines in candidate Pareto panel")
        c.loc[sub.index,"pareto_nondominated_vs_other_3_engines"]=frontier(sub)
    check(len(c)==19280 and c.frozen_candidate_key.nunique()==40,"candidate retained identifiability")

    # Verify the exact per-candidate averages recover F3 engine-level absolute losses.
    e=c.groupby(["scenario_id","method","benchmark_role"],as_index=False,sort=False)[
      ["mse_candidate_mean","mse_reference_mean","q95_candidate_mean","q95_reference_mean"]].mean()
    b=pd.read_csv(base/"ROBUST_SCENARIO_EFFECTS.csv")
    check(len(b)==1928 and len(e)==1928,"original robust engine schema")
    x=e.merge(b,on=["scenario_id","method","benchmark_role"],validate="one_to_one",suffixes=("_now","_original"))
    check(len(x)==1928,"exact key match of original Q2/F3")
    for metric in ("mse","q95"):
        for side in ("candidate","reference"):
            name=f"{metric}_{side}_mean"
            must=np.abs(x[name+"_now"].values-x[name+"_original"].values)
            check(bool(np.all(must<1e-8*np.maximum(1,np.abs(x[name+"_original"].values)))),
                  "reconstructed score mismatch with immutable F3 "+name)
    e=e.merge(meta,on="scenario_id",validate="many_to_one")
    for metric in ("mse","q95"):
        e[metric+"_sign"]=[categorise(a,b) for a,b in zip(e[metric+"_candidate_mean"],e[metric+"_reference_mean"])]
        e[metric+"_ratio"]=e[metric+"_candidate_mean"]/np.maximum(e[metric+"_reference_mean"],1e-14)
    e["winner_class"]=[cat(a,b) for a,b in zip(e.mse_sign,e.q95_sign)]
    e["reference_relation"]=[dominance(a,b) for a,b in zip(e.mse_sign,e.q95_sign)]
    e["pareto_nondominated_among_4_engine_means"]=False
    for _,sub in e.groupby(["benchmark_role","scenario_id"],sort=False):
        check(len(sub)==4,"four engine means in same scenario and reference")
        vals=sub.rename(columns={"mse_candidate_mean":"mse_candidate_mean","q95_candidate_mean":"q95_candidate_mean"})
        e.loc[sub.index,"pareto_nondominated_among_4_engine_means"]=frontier(vals)

    # Original outcome-blind observed graph (no synthetic interpolation of absent cells).
    edges=pd.read_csv(source/"local_neighbors.csv",usecols=["mechanism","axis","scenario_low","scenario_high"])
    edges=edges.drop_duplicates()
    check(len(edges)==205 and set(edges.mechanism)==set(MECHS),"original audited adjacency 205 edges/block")
    check(not bool(edges.scenario_low.eq(edges.scenario_high).any()),"self-loop in neighborhood design")
    graph=defaultdict(set)
    for row in edges.itertuples(index=False):
        a=int(row.scenario_low);b0=int(row.scenario_high)
        graph[a].add(b0);graph[b0].add(a)
    universal=[];per_mech=[]
    for (method,role,training),group in c.groupby(["method","benchmark_role","training_seed"],sort=False):
        contaminated=group[group.mechanism!="clean"]
        check(len(contaminated)==240 and contaminated.scenario_id.nunique()==240,"frozen candidate across 240 support cells")
        wins=set(contaminated.loc[contaminated.winner_class=="joint","scenario_id"].astype(int))
        connected,component_count=largest_cc(wins,graph)
        denom=sum(len(graph[sid]) for sid in wins)
        both_edge=sum(int(row.scenario_low in wins and row.scenario_high in wins) for row in edges.itertuples(index=False))
        isolated=sum(not(bool(graph[sid]&wins)) for sid in wins)
        k=f"{family}|n{n}|{method}|train{int(training):02d}"
        universal.append(dict(family=family,sample_n=n,method=method,benchmark_role=role,
          training_seed=int(training),frozen_candidate_key=k,eligible_scenarios=240,
          count_joint=len(wins),count_mse_only=int((contaminated.winner_class=="mse_only").sum()),
          count_q95_only=int((contaminated.winner_class=="q95_only").sum()),
          count_neither=int((contaminated.winner_class=="neither").sum()),
          count_tied=int((contaminated.winner_class=="tied").sum()),
          pareto_nondominated_count=int(contaminated.pareto_nondominated_vs_other_3_engines.sum()),
          original_outcome_blind_edges=len(edges),joint_winner_to_all_neighbor_directions=denom,
          joint_winner_to_joint_neighbor_directions=both_edge*2,
          observed_one_hop_joint_retention=(both_edge*2/denom if denom else float("nan")),
          largest_joint_winner_connected_component=connected,
          number_of_joint_winner_components=component_count,
          isolated_joint_winners=isolated,
          universal_within_tested_family_size_support=int(len(wins)==240),
          across_family_or_unseen_regime_universality="NOT_EVALUATED_HERE",
          full_original_weight_sha_identity="NOT_VERIFIED_HERE"))
        for mech in MECHS:
            sub=contaminated[contaminated.mechanism==mech]
            check(len(sub)==40,"40 supported cells per original contamination mechanism")
            positives=set(sub.loc[sub.winner_class=="joint","scenario_id"].astype(int))
            maxcomp,ncomp=largest_cc(positives,graph)
            per_mech.append(dict(family=family,sample_n=n,method=method,benchmark_role=role,
              training_seed=int(training),frozen_candidate_key=k,mechanism=mech,
              eligible=40,joint=len(positives),mse_only=int((sub.winner_class=="mse_only").sum()),
              q95_only=int((sub.winner_class=="q95_only").sum()),
              no_joint=40-len(positives),largest_connected_joint_pocket=maxcomp,
              number_connected_joint_pockets=ncomp,
              all_40_tested_settings_joint=int(len(positives)==40)))
    check(len(universal)==80 and len(per_mech)==480,"all forty frozen candidates per block across two policies")

    out.mkdir(parents=True,exist_ok=False)
    save_table(c,out/"CANDIDATE_SCENARIO_TAXONOMY.csv.gz",compress=True)
    save_table(e,out/"ENGINE_SCENARIO_TAXONOMY.csv")
    save_table(pd.DataFrame(universal),out/"CANDIDATE_BREADTH_AND_UNIVERSALITY.csv")
    save_table(pd.DataFrame(per_mech),out/"CANDIDATE_MECHANISM_POCKETS.csv")
    files={p.name:{"bytes":p.stat().st_size,"sha256":sha(p)} for p in out.iterdir() if p.is_file()}
    manifest={"status":"PASS_Q2_F3_ALL_FOUR_ENGINES_CANDIDATE_TAXONOMY","source_family":family,
       "sample_n":n,"original_Q2_AE":"44599590079","original_Q2_F3":"44613985618",
       "original_source_archive_count":10,"original_crossed_score_rows":len(d),
       "candidate_scenario_rows":len(c),"engine_scenario_rows":len(e),
       "frozen_candidate_policy_rows":len(universal),"frozen_candidate_mechanism_rows":len(per_mech),
       "original_observed_neighbors_per_block":len(edges),
       "fixed_frozen_candidate_key":"source_family|sample_n|method|training_seed",
       "cross_stage_weight_sha_verified":False,
       "observed_within_family_support_only":True,
       "source_Q2_manifest_sha256":sha(source/"Q2_BLOCK_MANIFEST.json"),
       "source_F3_manifest_sha256":sha(base/"F3_BLOCK_MANIFEST.json"),
       "source_files":files}
    (out/"Q2_F3_TAXONOMY_BLOCK_AUDIT.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print("Q2_F3_TAXONOMY_BLOCK_PASS",family,n,len(c),len(e),len(universal),flush=True)
def selftest():
    assert [cat(1,1),cat(1,-1),cat(-1,1),cat(-1,-1)]==["joint","mse_only","q95_only","neither"]
    assert dominance(1,1)=="candidate_dominates_reference"
    assert largest_cc({1,2,4},{1:{2},2:{1},4:set()})==(2,2)
    print("Q2_F3_TAXONOMY_SELFTEST_PASS")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("mode",choices=["block","selftest"])
    p.add_argument("--family");p.add_argument("--n",type=int);p.add_argument("--output")
    a=p.parse_args()
    if a.mode=="selftest":selftest()
    else:check(a.output is not None,"missing output");run(a.family,a.n,Path(a.output))
