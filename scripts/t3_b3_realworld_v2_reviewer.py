#!/usr/bin/env python3
"""Reviewer layer for T3/B3 Real World V2 immutable inference.

Never alters p-values or BH families. Profiles and scenario neighbors are
observational, and unknown population means cannot be inferred from these data.
"""
import argparse,collections,csv,gzip,hashlib,json,math,re
from pathlib import Path

FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
METRICS=("mse","q95")
TIER1="tier1_joint_mse_q95_bh_fdr"
def stop(s):raise ValueError(s)
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def csv_rows(p):
 with gzip.open(p,"rt",newline="") as f:
  yield from csv.DictReader(f)
def finite(v):
 x=float(v)
 if not math.isfinite(x):stop("Nonfinite inferential quantity")
 return x
def candidate(row):
 cid=row["candidate_id"]
 if not re.fullmatch(r"(normal|lognormal|weibull|invgauss|exgaussian|exwald)\|(ga|nsga2|de|dirichlet)\|seed0[0-9]\|n(200|1000|3000)",cid):
  stop("Invalid original 720-W candidate identity: "+cid)
 source,engine,seed,n=cid.split("|")
 if source!=row["source_family"] or int(n[1:])!=int(row["sample_n"]) or int(seed[4:])!=int(row["training_seed"]):
  stop("Candidate identity differs from its row")
 return cid
def write(p,rows,keys):
 with open(p,"w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=keys)
  w.writeheader();w.writerows(rows)
def inspect(a):
 global_root=Path(a.global_root)
 mpath=global_root/"scientific_provenance.json"
 meta=json.loads(mpath.read_text())
 if meta["original_candidate_count"]!=720 or meta["alpha"]!=.05:
  stop("Not the frozen 720-W Real World V2 inference")
 if meta["realworld_seeds"]!=list(range(30,40)):
  stop("Incorrect evaluation seed panel")
 out=Path(a.output)
 if out.exists():stop("Review output exists (immutable)")
 out.mkdir(parents=True)
 paths={"primary":global_root/"primary_parent_BH_taxonomy.csv.gz",
        "secondary":global_root/"secondary_family_transfer_BH_taxonomy.csv.gz"}
 ledgers=[{"kind":"original_global_manifest","path":str(mpath),"sha256":sha(mpath)}]
 stats=collections.defaultdict(lambda:collections.Counter())
 family_cov=collections.defaultdict(lambda:collections.defaultdict(set))
 primary_records=0;secondary_records=0
 breakdown=collections.Counter();unique_candidates=set()
 for panel,path in paths.items():
  if not path.is_file():stop("Missing complete primary / secondary taxonomy: "+str(path))
  ledgers.append({"kind":panel,"path":str(path),"sha256":sha(path)})
  for r in csv_rows(path):
   cid=candidate(r);unique_candidates.add(cid)
   role=r["benchmark_role"];scope=r["transfer_scope"]
   if role not in ("own","mean") or scope not in ("within_regime","within_family_neighborhood","cross_family_transfer"):
    stop("Invalid Real-World benchmark role or migration scope")
   tier=r["highest_tier"]
   if tier not in (TIER1,"tier2_joint_ci_only","tier3_mse_bh_only","tier3_q95_bh_only","tier4_retained_no_bh_win"):
    stop("Unexpected four-tier taxonomy")
   mse_q=finite(r["mse_global_bh_q"]);q95_q=finite(r["q95_global_bh_q"])
   mse_u=finite(r["mse_ci_upper"]);q95_u=finite(r["q95_ci_upper"])
   expected=(mse_q<=.05 and q95_q<=.05 and mse_u<0 and q95_u<0)
   if (tier==TIER1)!=expected:stop("Tier1 cannot be reproduced from frozen global q and CIs")
   parents=int(r["independent_parent_datasets"])
   if parents<5:stop("Parent-unit inference below n=5")
   key=(panel,role,scope,tier)
   breakdown[key]+=1
   s=stats[cid]
   s[f"{panel}_{role}_comparisons"]+=1
   s[f"{panel}_{role}_tier1"]+=int(expected)
   if panel=="primary":primary_records+=1
   else:
    secondary_records+=1
    dst=r["evaluation_family"]
    if dst not in FAMILIES:stop("Unrecognized empirical destination family")
    family_cov[(cid,role)]["tested"].add(dst)
    if expected:family_cov[(cid,role)]["won"].add(dst)
   s["largest_independent_parent_panel"]=max(s["largest_independent_parent_panel"],parents)
   s["smallest_independent_parent_panel"]=min(s.get("smallest_independent_parent_panel",parents),parents)
   s[f"{panel}_{role}_mse_gain_pct_sum"]+=finite(r["mse_gain_pct"])
   s[f"{panel}_{role}_q95_gain_pct_sum"]+=finite(r["q95_gain_pct"])
 if primary_records*2!=meta["primary_hypotheses"] or secondary_records*2!=meta["secondary_hypotheses"]:
  stop("Original reported BH family size disagrees with complete taxonomy")
 if len(unique_candidates)!=720:stop(f"Expected 720 original candidate IDs, got {len(unique_candidates)}")
 report=[]
 for cid in sorted(unique_candidates):
  s=stats[cid];src,engine,seed,n=cid.split("|")
  row=dict(candidate_id=cid,source_family=src,engine=engine,training_seed=seed,sample_n=n[1:],
   min_independent_parent_panel=s["smallest_independent_parent_panel"],
   max_independent_parent_panel=s["largest_independent_parent_panel"])
  for panel in ("primary","secondary"):
   for role in ("own","mean"):
    row[panel+"_"+role+"_contrasts"]=s[f"{panel}_{role}_comparisons"]
    row[panel+"_"+role+"_tier1"]=s[f"{panel}_{role}_tier1"]
    den=s[f"{panel}_{role}_comparisons"]
    row[panel+"_"+role+"_mean_panel_gain_pct_mse"]=round(s[f"{panel}_{role}_mse_gain_pct_sum"]/den,7) if den else ""
    row[panel+"_"+role+"_mean_panel_gain_pct_q95"]=round(s[f"{panel}_{role}_q95_gain_pct_sum"]/den,7) if den else ""
  for role in ("own","mean"):
   tested=family_cov[(cid,role)]["tested"]
   won=family_cov[(cid,role)]["won"]
   row["secondary_"+role+"_evaluation_families_tested"]=";".join(sorted(tested))
   row["secondary_"+role+"_evaluation_families_with_tier1"]=";".join(sorted(won))
   row["secondary_"+role+"_cross_family_tier1_coverage"]=len(won-{src})
  report.append(row)
 write(out/"individual_candidate_generalization.csv",report,list(report[0]))
 write(out/"tier1_primary_secondary_by_scope.csv",
       [dict(panel=p,benchmark_role=b,transfer_scope=s,highest_tier=t,contrasts=n)
        for (p,b,s,t),n in sorted(breakdown.items())],
       ["panel","benchmark_role","transfer_scope","highest_tier","contrasts"])
 neighbor_files=sorted(Path(a.neighborhood_root).rglob("neighborhood_scope.json"))
 if len(neighbor_files)!=6:stop("Require six independently produced destination-family neighborhood artifacts")
 summary=[];observed=set()
 for mf in neighbor_files:
  v=json.loads(mf.read_text());f=v["source_family"]
  if f in observed or f not in FAMILIES:stop("Duplicated or unknown neighborhood source family")
  observed.add(f)
  file=mf.parent/"adjacent_observed_scenario_transfer_descriptive.csv.gz"
  if not file.is_file():stop("Missing neighbor-edge descriptive data")
  edge_total=0;both=0;both_adequate=0;coverage=[]
  for r in csv_rows(file):
   if r["source_family"]!=f:stop("Neighborhood source family mixing")
   candidate(r)
   edge_total+=1
   good=r["both_scenarios_mean_improve_mse_q95"].lower()=="true"
   adequate=min(int(r["a_independent_parents"]),int(r["b_independent_parents"]))>=5
   both+=int(good);both_adequate+=int(good and adequate)
   coverage.append(int(adequate))
  summary.append({"source_family":f,"observed_neighbor_edges":edge_total,
   "both_nodes_joint_direction_positive":both,
   "adequate_five_parent_coverage_at_both_nodes":sum(coverage),
   "both_nodes_positive_and_at_least_five_parents":both_adequate,
   "paired_parent_transfer_verified":False,
   "statistical_scope":"descriptive_only; different parent datasets may populate neighboring scenario nodes"})
  ledgers.append({"kind":"neighbor_"+f,"path":str(file),"sha256":sha(file)})
 if set(observed)!=set(FAMILIES):stop("Missing family neighborhood evidence")
 write(out/"neighbor_coverage_and_limits.csv",summary,list(summary[0]))
 (out/"reviewer_scientific_scope.json").write_text(json.dumps({
  "protocol":"T3_B3_RW_V2_REVIEWER_AUDIT_FROM_FROZEN_OUTPUTS",
  "source_full_run":a.source_run,"original_frozen_W":720,"primary_parent_contrasts":primary_records,
  "secondary_destination_contrasts":secondary_records,
  "bh_primary_and_secondary_separate":True,"alpha":.05,
  "individual_candidate_training_seeds_not_averaged":True,
  "unit_of_inference":"parent_dataset_id",
  "matched_scenario_not_identified_true_DGP":True,
  "neighbor_edges_descriptive_not_matched_parent_transitions":True,
  "realworld_target":"within_child_depth_full_sample_empirical_mean_proxy",
  "selection_after_realworld_results_exploratory":True,
  "input_ledger":ledgers},indent=2)+"\n")
 print("REALWORLD_V2_REVIEWER_WIDE_AUDIT_PASS",len(report),"individual_W",primary_records,"primary contrasts",secondary_records,"secondary contrasts",flush=True)

def selftest():
 assert len(FAMILIES)==6
 assert candidate({"candidate_id":"normal|ga|seed00|n200","source_family":"normal","sample_n":"200","training_seed":"0"})=="normal|ga|seed00|n200"
 print("REALWORLD_V2_REVIEWER_SELFTEST_PASS",flush=True)

if __name__=="__main__":
 p=argparse.ArgumentParser()
 sub=p.add_subparsers(dest="mode",required=True)
 sub.add_parser("selftest")
 s=sub.add_parser("inspect")
 s.add_argument("--global-root",required=True)
 s.add_argument("--neighborhood-root",required=True)
 s.add_argument("--output",required=True)
 s.add_argument("--source-run",required=True)
 a=p.parse_args()
 {"selftest":lambda a:selftest(),"inspect":inspect}[a.mode](a)
