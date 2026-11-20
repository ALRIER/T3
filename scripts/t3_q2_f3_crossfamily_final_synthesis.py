#!/usr/bin/env python3
"""Q2-F3 recovery of EXISTING cross-family Held Out and empirical Real World
statistical taxonomy. Aggregate original tier labels, do NOT recompute BH.
All calculations and persistence performed in T3 Actions.
"""
import csv,hashlib,json,collections,sys
from pathlib import Path
FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
ENGINES=("ga","nsga2","de","dirichlet")
def check(x,msg):
 if not x:raise RuntimeError("T3_CROSS_FAMILY_ORIGINAL_TIER_RECONCILIATION: "+str(msg))
def hashfile(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1<<20),b""):h.update(c)
 return h.hexdigest()
def dump(out,filename,rows):
 check(rows,"Cannot save empty "+filename)
 with (out/filename).open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def original_bool(x):
 check(x in ("TRUE","FALSE","True","False","true","false","1","0"),"Nonboolean original BH winner cell "+str(x))
 return x.lower() in ("true","1")
def heldout(original,output):
 path=Path("incoming/heldout_global/four_tier_winner_matrix.csv")
 check(path.is_file(),"Original 2026 Held Out global winner matrix is not downloaded")
 seen=collections.Counter();win=collections.Counter();tier2=collections.Counter();sumrows=0
 engines=set();source=set();dest=set();roles=set()
 with path.open("r",newline="",encoding="utf-8") as f:
  dr=csv.DictReader(f)
  required={"source_family","evaluation_family","benchmark_role","candidate_engine","tier1_joint_mse_q95_bh_fdr","tier2_joint_mse_q95_ci","scenario_id","sample_n"}
  check(required<=set(dr.fieldnames),"Original independent Held Out source lacks mandatory columns")
  for r in dr:
   a,b=r["source_family"],r["evaluation_family"]
   eng=r["candidate_engine"];role=r["benchmark_role"];scope="within_family" if a==b else "cross_family"
   check(a in FAMILIES and b in FAMILIES and eng in ENGINES and role in ("own","mean"),"source-family model identity invalid")
   key=(role,scope,a,b,eng)
   seen[key]+=1;win[key]+=int(original_bool(r["tier1_joint_mse_q95_bh_fdr"]))
   tier2[key]+=int(original_bool(r["tier2_joint_mse_q95_ci"]))
   engines.add(eng);source.add(a);dest.add(b);roles.add(role);sumrows+=1
 check(engines==set(ENGINES) and source==set(FAMILIES) and dest==set(FAMILIES),"six family four engine original support")
 records=[]
 for k in sorted(seen):
  records.append(dict(reference=k[0],scope=k[1],source_family=k[2],evaluation_family=k[3],
                      engine=k[4],original_eligible_contrasts=seen[k],original_tier1_joint_BH_CI=win[k],
                      original_tier2_joint_CI_only=tier2[k]))
 dump(output,"HELDOUT_ORIGINAL_DIRECTED_FAMILY_ENGINE_MATRIX.csv",records)
 summary=[]
 for role in ("own","mean"):
  for scope in ("within_family","cross_family"):
   elig=sum(v for k,v in seen.items() if k[0]==role and k[1]==scope)
   wins=sum(v for k,v in win.items() if k[0]==role and k[1]==scope)
   summary.append(dict(reference=role,scope=scope,eligible_original_contrasts=elig,
        original_tier1_joint_BH_CI=wins,rate_pct=100*wins/elig if elig else None))
 dump(output,"HELDOUT_ORIGINAL_CROSSFAMILY_SUMMARY.csv",summary)
 own={r["scope"]:r for r in summary if r["reference"]=="own"}
 match_original=((own["within_family"]["eligible_original_contrasts"]==173520 and
                 own["within_family"]["original_tier1_joint_BH_CI"]==877 and
                 own["cross_family"]["eligible_original_contrasts"]==867600 and
                 own["cross_family"]["original_tier1_joint_BH_CI"]==5069))
 return {"original_global_matrix_rows_scanned":sumrows,"row_level_source_sha256":hashfile(path),
    "original_own_policy_matched_published_manuscript":match_original,
    "original_own_within_count":own["within_family"],"original_own_cross_count":own["cross_family"],
    "read_without_recomputing_original_adjusted_pvalues":True}
def realworld(root,out):
 audit=json.loads((root/"TRANSFER_RECOVERY_AUDIT.json").read_text())
 check(audit["status"]=="PASS_ARCHIVED_ORIGINAL_ARTIFACT_IDENTITIES_AND_SCHEMA_INVENTORY","original archive source gate")
 mf=json.loads((root/"RECOVERY_OUTPUT_SHA256_MANIFEST.json").read_text())
 for k,z in mf.items():
  p=root/k
  check(p.is_file() and p.stat().st_size==z["bytes"] and hashfile(p)==z["sha256"],
   "permanent recovered origin SHA mismatch "+k)
 p=root/"ORIGINAL_REPORTED_SCOPE_TIER_COUNTS.csv"
 seen=collections.Counter();wins=collections.Counter();tiers=set()
 with p.open(newline="",encoding="utf-8") as f:
  for r in csv.DictReader(f):
   if r["artifact"]!="realworld_destination":continue
   panel=r["file_name"];scope=r["transfer_scope"];role=r["benchmark_role"]
   src=r["source_family"];dest=r["evaluation_family"];engine=r["engine"]
   tier=r["original_highest_tier"];count=int(r["contrasts"])
   check(src in FAMILIES and engine in ENGINES and count>0,"empirical original source identity")
   check(panel in ("primary_parent_BH_taxonomy.csv.gz","secondary_family_transfer_BH_taxonomy.csv.gz"),
        "unexpected original Real World BH panel")
   check(role in ("own","mean"),"unexpected original Real World reference")
   check(scope in ("within_regime","within_family_neighborhood","cross_family_transfer"),
        "unrecognized empirical transfer scope")
   if panel.startswith("secondary"):check(dest in FAMILIES,"estimated family destination missing")
   k=(panel,role,scope,src,dest,engine)
   seen[k]+=count
   wins[k]+=count if tier=="tier1_joint_mse_q95_bh_fdr" else 0
   tiers.add(tier)
 sums=collections.Counter()
 for k,v in seen.items():sums[k[0]]+=v
 check(sums["primary_parent_BH_taxonomy.csv.gz"]==4080 and
       sums["secondary_family_transfer_BH_taxonomy.csv.gz"]==14880,
       "Real World original primary/secondary candidate hypothesis counts")
 rows=[]
 for k in sorted(seen):
  rows.append(dict(original_panel=k[0],reference=k[1],transfer_scope=k[2],
       source_family=k[3],empirically_assigned_destination_family=k[4],
       engine=k[5],original_parent_inference_contrasts=seen[k],
       original_tier1_joint_BH_CI=wins[k],
       tier1_fraction=wins[k]/seen[k]))
 dump(out,"REALWORLD_ORIGINAL_FAMILY_SCOPE_ENGINE_BH.csv",rows)
 summary=[]
 for panel in ("primary_parent_BH_taxonomy.csv.gz","secondary_family_transfer_BH_taxonomy.csv.gz"):
  for role in ("own","mean"):
   for scope in ("within_regime","within_family_neighborhood","cross_family_transfer"):
    denom=sum(v for k,v in seen.items() if k[0]==panel and k[1]==role and k[2]==scope)
    n=sum(v for k,v in wins.items() if k[0]==panel and k[1]==role and k[2]==scope)
    summary.append(dict(original_panel=panel,reference=role,scope=scope,
               eligible_parent_cluster_tests=denom,original_tier1_joint_BH_CI=n,
               original_tier1_fraction=n/denom if denom else None,
               independent_unit="parent_dataset_id",
               destination_family="empirical_outcome_blind_profile_not_true_DGP"))
 dump(out,"REALWORLD_ORIGINAL_TRANSFER_SCOPE_BH_SUMMARY.csv",summary)
 return {"original_primary_contrasts":sums["primary_parent_BH_taxonomy.csv.gz"],
         "original_secondary_contrasts":sums["secondary_family_transfer_BH_taxonomy.csv.gz"],
         "original_primary_vs_destination_policy":"destination archived panel only; primary/source and destination-classical benchmark policies remain distinct",
         "original_empirical_destination_labels_are_true_distributions":False,
         "original_tiers_seen":sorted(tiers),
         "scientific_units":"642 original independent empirical parents; model-level comparisons are aggregated across parent clusters",
         "BH_recomputed":False}
def main(root,out):
 root=Path(root);out=Path(out)
 check(not out.exists(),"Never overwrite an analysis")
 out.mkdir(parents=True)
 h=heldout(root,out)
 rw=realworld(root,out)
 audit={"status":"PASS_ORIGINAL_TRANSFER_REPORTED_TIER_RECOVERY",
  "heldout":h,"realworld_destination_policy":rw,
  "original_frozen_discovery_training_only":True,
  "heldout_and_realworld_original_BH_values_preserved":True,
  "existing_Q2_F3_source_untouched":True,
  "no_optimizer_rerun_or_new_statistical_testing":True,
  "original_empirical_destination_family_labels_are_approximations":True}
 (out/"CROSS_FAMILY_TRANSFER_SCIENTIFIC_AUDIT.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n")
 files={}
 for p in sorted(out.iterdir()):
  if p.is_file():files[p.name]={"sha256":hashfile(p),"bytes":p.stat().st_size}
 (out/"CROSS_FAMILY_TRANSFER_SHA256_MANIFEST.json").write_text(json.dumps(files,indent=2,sort_keys=True)+"\n")
 print("Q2_F3_ORIGINAL_TRANSFER_TIER_RESULTS_PASS",json.dumps(audit["heldout"]["original_own_cross_count"]),flush=True)
if __name__=="__main__":
 check(len(sys.argv)==3,"usage: RECOVERED_ROOT NEW_OUTPUT_DIR");main(sys.argv[1],sys.argv[2])
