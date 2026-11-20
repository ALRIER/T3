#!/usr/bin/env python3
"""Side-by-side original Real World source/destination classical benchmark policy.

Both inputs are original frozen-W parent-cluster inference tables from
original GitHub Actions artifacts. NO p-values, BH corrections or W are
recomputed. Source and estimated destination family remain distinct.
"""
import csv,gzip,hashlib,json,sys,collections
from pathlib import Path
FAMILIES={"normal","lognormal","weibull","invgauss","exgaussian","exwald"}
METHODS={"ga","nsga2","de","dirichlet"}
SCOPES={"within_regime","within_family_neighborhood","cross_family_transfer"}
ROOTS={"source":Path("incoming/source"),"destination":Path("incoming/destination")}
FILES={"primary":"primary_parent_BH_taxonomy.csv.gz","secondary":"secondary_family_transfer_BH_taxonomy.csv.gz"}
CATALOGS={
"source":("data-archive/realworld/actions/actions-13519858091_t3-rw-v2-recovered-720W-global-BH-taxonomy-run42251598557.zip/manifest.json",
13519858091,"01dd67cce8879c2b2b665bd88f1baf18df14a71a8bc7429cbab1b9ee5bf5e678"),
"destination":("data-archive/realworld/actions/actions-13542889733_t3-rw-v3-destination-global-taxonomy-run42299685581.zip/manifest.json",
13542889733,"3e7c28d685a8778cc4d70391e5b8433b14b97178e015bcb262e9280a6611e132")}
def check(x,msg):
 if not x:raise RuntimeError("T3_RW_TWO_POLICY_DIRECT_TRANSFER_GATE: "+str(msg))
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1<<20),b""):h.update(c)
 return h.hexdigest()
def write(out,name,rows,fields):
 with (out/name).open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def load(label,panel):
 paths=list(ROOTS[label].rglob(FILES[panel]))
 check(len(paths)==1,"original taxonomy source "+label+" "+panel)
 p=paths[0]
 result={}
 with gzip.open(p,"rt",newline="") as f:
  for r in csv.DictReader(f):
   src=r["source_family"];method=r["engine"];ref=r["benchmark_role"];scope=r["transfer_scope"]
   dest=r.get("evaluation_family","") if panel=="secondary" else ""
   check(src in FAMILIES and method in METHODS and ref in ("own","mean") and scope in SCOPES,
       "invalid published original stratum")
   if panel=="secondary":check(dest in FAMILIES,"missing empirical destination family")
   check(int(r["independent_parent_datasets"])>=5,"parent evidence below original minimum")
   key=(src,r["candidate_id"],method,r["training_seed"],int(r["sample_n"]),scope,ref,dest)
   check(key not in result,"duplicate original frozen-W hypothesis")
   q= float(r["mse_global_bh_q"])<=.05 and float(r["q95_global_bh_q"])<=.05
   ci= float(r["mse_ci_upper"])<0 and float(r["q95_ci_upper"])<0
   tier=r["highest_tier"]=="tier1_joint_mse_q95_bh_fdr"
   check(tier==(q and ci),"original BH label invalid")
   result[key]=dict(mse=float(r["mse_difference"]),q95=float(r["q95_difference"]),
                    ci=ci,tier1=tier,parents=int(r["independent_parent_datasets"]))
 expected=4080 if panel=="primary" else 14880
 check(len(result)==expected,"original published panel count "+str(len(result))+"!="+str(expected))
 return result,{"bytes":p.stat().st_size,"sha256":sha(p),"rows":len(result)}
def main(out):
 out=Path(out);check(not out.exists(),"immutable result path");out.mkdir(parents=True)
 for label,(path,aid,sha256) in CATALOGS.items():
  z=json.loads(Path(path).read_text())
  check(z["complete"] and z["source"]["artifact_id"]==aid and z["sha256"]==sha256,
   "original T3 archived provenance "+label)
 totals=collections.Counter();details=collections.defaultdict(lambda:collections.Counter());file_sha={}
 for panel in ("primary","secondary"):
  src,sums=load("source",panel);dst,sumd=load("destination",panel)
  file_sha[panel]={"source":sums,"destination":sumd}
  check(set(src)==set(dst),"both original source/dest original policies have different W/destination records")
  totals[(panel,"source","original_rows")]=len(src)
  for key in sorted(src):
   a,b=src[key],dst[key]
   role=key[6]
   if role=="mean":
    check(abs(a["mse"]-b["mse"])<=1e-7*max(1,abs(a["mse"]),abs(b["mse"])) and
          abs(a["q95"]-b["q95"])<=1e-7*max(1,abs(a["q95"]),abs(b["q95"])),
          "original sample mean paired effects changed by benchmark policy")
   srcfam,_,method,_,n,scope,ref,destfam=key
   for policy,record in (("source",a),("destination",b)):
    group=(policy,panel,ref,scope)
    q=details[group];q["eligible"]+=1
    q["joint_descriptive"]+=int(record["mse"]<0 and record["q95"]<0)
    q["joint_conditional_CI"]+=int(record["ci"])
    q["joint_original_BH_CI"]+=int(record["tier1"])
    q["min_parent_count"]=min(q.get("min_parent_count",record["parents"]),record["parents"])
    enginekey=(policy,panel,ref,scope,method,srcfam,destfam)
    e=details[enginekey];e["eligible"]+=1
    e["joint_descriptive"]+=int(record["mse"]<0 and record["q95"]<0)
    e["joint_conditional_CI"]+=int(record["ci"])
    e["joint_original_BH_CI"]+=int(record["tier1"])
   totals[(panel,"mean_invariant")]+=int(role=="mean")
 summaries=[]
 for k,z in sorted(details.items()):
  if len(k)!=4:continue
  summaries.append(dict(benchmark_policy=k[0],original_inferential_panel=k[1],
      comparator=k[2],transfer_scope=k[3],eligible=z["eligible"],
      descriptive_joint_mean_loss_contrasts=z["joint_descriptive"],
      both_conditional_CI_favorable=z["joint_conditional_CI"],
      both_BH_and_CI_favorable=z["joint_original_BH_CI"],
      independent_parent_count_min=z["min_parent_count"],
      empirical_destination_family_is_true_DGP=False))
 detail=[]
 for k,z in sorted(details.items()):
  if len(k)!=7:continue
  detail.append(dict(benchmark_policy=k[0],original_inferential_panel=k[1],
    comparator=k[2],transfer_scope=k[3],engine=k[4],source_family=k[5],
    empirical_destination_family=k[6],eligible=z["eligible"],
    original_descriptive_joint=z["joint_descriptive"],
    original_joint_conditional_CI=z["joint_conditional_CI"],
    original_joint_BH_CI=z["joint_original_BH_CI"]))
 write(out,"REALWORLD_TWO_ORIGINAL_CLASSICAL_POLICIES_SCOPE_TABLE.csv",summaries,list(summaries[0]))
 write(out,"REALWORLD_TWO_ORIGINAL_POLICIES_ENGINE_SOURCE_DEST_TABLE.csv",detail,list(detail[0]))
 audit={"status":"PASS_ORIGINAL_RW_SOURCE_VS_DESTINATION_TRANSFER_RECONCILIATION",
    "original_source_policy_run":42251598557,
    "original_destination_policy_run":42299685581,
    "source_artifact_id":13519858091,"destination_artifact_id":13542889733,
    "original_file_integrity":file_sha,
    "original_primary_hypotheses_each_policy":4080,
    "original_secondary_destination_hypotheses_each_policy":14880,
    "original_720_frozen_W_identity_preserved":True,
    "original_BH_panel_results_unchanged":True,
    "original_sample_mean_raw_differences_invariant_across_policies":True,
    "independent_inferential_unit":"642 parent_dataset_id clusters, not child profiles or training seeds",
    "empirical_destination_family_known_true_DGP":False,
    "full_training_pipeline_error_calibration_confirmed":False,
    "no_new_optimizer_training_or_new_BH":True}
 (out/"REALWORLD_TWO_POLICY_SCIENTIFIC_AUDIT.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n")
 files={}
 for p in out.iterdir():
  if p.is_file():files[p.name]={"sha256":sha(p),"bytes":p.stat().st_size}
 (out/"REALWORLD_TWO_POLICY_SHA256_MANIFEST.json").write_text(json.dumps(files,indent=2,sort_keys=True)+"\n")
 print("REALWORLD_ORIGINAL_TWO_REFERENCE_POLICIES_TRANSFER_PASS",len(summaries),len(detail),flush=True)
if __name__=="__main__":
 check(len(sys.argv)==2,"output path");main(sys.argv[1])
