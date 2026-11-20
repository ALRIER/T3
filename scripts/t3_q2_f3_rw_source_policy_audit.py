#!/usr/bin/env python3
"""Recover prespecified original Real World SOURCE classical-reference policy.

Use original source-policy BH taxonomy scores (no new p-values/BH). Compare
source vs archived destination policy without pooling distinct error families.
All calculations and outputs occur in T3 Actions.
"""
import collections,csv,gzip,hashlib,json,sys
from pathlib import Path
ART_ID=13519858091
ART_SHA="01dd67cce8879c2b2b665bd88f1baf18df14a71a8bc7429cbab1b9ee5bf5e678"
CATALOG=Path("data-archive/realworld/actions/actions-13519858091_t3-rw-v2-recovered-720W-global-BH-taxonomy-run42251598557.zip/manifest.json")
FAMILIES={"normal","lognormal","weibull","invgauss","exgaussian","exwald"}
METHODS={"ga","nsga2","de","dirichlet"}
SCOPES={"within_regime","within_family_neighborhood","cross_family_transfer"}
FILES={"primary":"primary_parent_BH_taxonomy.csv.gz",
       "secondary":"secondary_family_transfer_BH_taxonomy.csv.gz"}
def check(x,s):
 if not x:raise RuntimeError("T3_REALWORLD_SOURCE_POLICY_RECOVERY_GATE:"+str(s))
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def csvout(path,rows,fields):
 with open(path,"w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def recover(out):
 cat=json.loads(CATALOG.read_text())
 check(cat["sha256"]==ART_SHA and cat["complete"] and cat["source"]["artifact_id"]==ART_ID,
      "original catalog identity")
 root=Path("incoming/realworld_source")
 originals={}
 grouped=collections.defaultdict(lambda:collections.Counter())
 seen=[]
 for label,filename in FILES.items():
  paths=list(root.rglob(filename))
  check(len(paths)==1,"Missing or duplicate original "+filename)
  p=paths[0]
  original=set();total=0
  with gzip.open(p,"rt",newline="") as f:
   reader=csv.DictReader(f)
   required={"source_family","candidate_id","engine","training_seed","sample_n",
        "transfer_scope","benchmark_role","highest_tier","mse_difference",
        "q95_difference","mse_global_bh_q","q95_global_bh_q",
        "mse_ci_upper","q95_ci_upper","independent_parent_datasets"}
   check(required<=set(reader.fieldnames),"Original schema missing "+str(required-set(reader.fieldnames)))
   for r in reader:
    src=r["source_family"];eng=r["engine"];scope=r["transfer_scope"]
    ref=r["benchmark_role"];dest=r.get("evaluation_family","")
    check(src in FAMILIES and eng in METHODS and scope in SCOPES and ref in ("own","mean"),
          "original source identity")
    check(int(r["independent_parent_datasets"])>=5,"too few independent parents")
    if label=="secondary":check(dest in FAMILIES,"Original empirical destination missing")
    k=(label,ref,scope,src,dest,eng)
    c=grouped[k]
    c["eligible"]+=1
    ci= float(r["mse_ci_upper"])<0 and float(r["q95_ci_upper"])<0
    q=float(r["mse_global_bh_q"])<=.05 and float(r["q95_global_bh_q"])<=.05
    strict=(float(r["mse_difference"])<0 and float(r["q95_difference"])<0)
    tier=r["highest_tier"]=="tier1_joint_mse_q95_bh_fdr"
    check(tier==(ci and q),"Original published BH taxonomy disagrees with source raw CI and q")
    c["tier1_joint_BH_CI"]+=int(tier)
    c["joint_descriptive_both_negative"]+=int(strict)
    c["joint_CI_favorable"]+=int(ci)
    original.add(r["candidate_id"]);total+=1
  check(len(original)==720 and total==(4080 if label=="primary" else 14880),
      "original full 720W Real World panel")
  originals[label]={"file":filename,"sha256":sha(p),"rows":total,"distinct_frozen_candidates":len(original)}
  print("REALWORLD_ORIGINAL_SOURCE_PANEL_PASS",label,total,flush=True)
 # Save a complete source-family engine and scope panel, with destination estimates separate.
 rows=[]
 for k,c in sorted(grouped.items()):
  rows.append(dict(panel=k[0],reference=k[1],transfer_scope=k[2],
    source_family=k[3],empirical_assigned_evaluation_family=k[4],engine=k[5],
    eligible_contrasts=c["eligible"],original_tier1_joint_BH_CI=c["tier1_joint_BH_CI"],
    original_CI_both_favorable=c["joint_CI_favorable"],
    original_descriptive_joint_both_negative=c["joint_descriptive_both_negative"]))
 fields=list(rows[0]);csvout(out/"REALWORLD_SOURCE_POLICY_ORIGINAL_FAMILY_ENGINE.csv",rows,fields)
 agg=collections.defaultdict(lambda:collections.Counter())
 for z in rows:
  key=(z["panel"],z["reference"],z["transfer_scope"])
  for k in ("eligible_contrasts","original_tier1_joint_BH_CI","original_CI_both_favorable",
            "original_descriptive_joint_both_negative"):agg[key][k]+=int(z[k])
 summary=[dict(panel=k[0],reference=k[1],transfer_scope=k[2],**c) for k,c in sorted(agg.items())]
 csvout(out/"REALWORLD_SOURCE_POLICY_ORIGINAL_SCOPE_SUMMARY.csv",summary,list(summary[0]))
 # Cross-check the recovered original DESTINATION policy as a separate scientific panel.
 dest=Path("Q2/F3/transfer_recovery/synthesis/runs/44747159779/REALWORLD_ORIGINAL_TRANSFER_SCOPE_BH_SUMMARY.csv")
 check(dest.is_file(),"Missing prior destination-policy verified synthesis")
 destination=[]
 with dest.open(newline="") as f:destination=list(csv.DictReader(f))
 status=dict(original_source_classical_policy=originals,
    original_source_level_642_independent_parent_datasets=True,
    destination_policy_original_scoped_rows=len(destination),
    destination_policy_tier1_total=sum(int(x["original_tier1_joint_BH_CI"]) for x in destination),
    original_source_policy_tier1_total=sum(c["tier1_joint_BH_CI"] for c in agg.values()),
    original_source_policy_joint_descriptive_total=sum(c["joint_descriptive_joint_both_negative"] for c in agg.values()) if False else sum(c["original_descriptive_joint_both_negative"] for c in agg.values()),
    empirical_family_labels_true_generating_distribution=False,
    full_nested_optimizer_null_selection_calibration=False,
    distinct_source_and_destination_classical_benchmark_policy_BH_scope=True,
    no_new_BH_or_pvalues_computed=True)
 (out/"REALWORLD_SOURCE_VS_DESTINATION_POLICY_AUDIT.json").write_text(json.dumps(status,indent=2,sort_keys=True)+"\n")
 manifest={}
 for p in out.iterdir():
  if p.is_file():manifest[p.name]={"sha256":sha(p),"bytes":p.stat().st_size}
 (out/"SHA256_OUTPUT_MANIFEST.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
 print("REALWORLD_FROZEN_SOURCE_AND_DESTINATION_POLICIES_AUDITED",status["original_source_policy_tier1_total"],flush=True)
if __name__=="__main__":
 check(len(sys.argv)==2,"output dir");d=Path(sys.argv[1]);check(not d.exists(),"immutable result directory");d.mkdir(parents=True);recover(d)
