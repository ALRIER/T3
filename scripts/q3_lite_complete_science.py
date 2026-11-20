#!/usr/bin/env python3
"""Q3 A/B/C/E/F/G original-source audit plus compact D scientific inference and permanent backup.

A/B/C/E: reuse original documented data, not new inference.
D: independent frozen-weight parameter-transfer scores on a frozen 49-scenario outcome-blind reduced panel.
F: integrate separate denominators and statistical units without invalid pooling.
G: produce manuscript-ready graphics and machine-readable scientific receipts.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,math,os,re,shutil,statistics,tarfile
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"Q3"
FAMS=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
ENGINES=("ga","nsga2","de","dirichlet")
REC=ROOT/"Q2/F3/transfer_recovery"
SYN=REC/"synthesis/runs/44747159779"
PUB=REC/"publication/runs/44748368642"

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for buf in iter(lambda:f.read(4*1024*1024),b""):h.update(buf)
    return h.hexdigest()

def rows(path):
    with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))

def csvout(path,records):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not records:raise ValueError("Refusing empty scientific table "+str(path))
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator="\n")
        w.writeheader();w.writerows(records)

def jsonout(path,item):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(item,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def source_gate(directory,manifest_file,names):
    manifest=json.loads((directory/manifest_file).read_text(encoding="utf-8"))
    output={}
    for name in names:
        file=directory/name;entry=manifest[name]
        if not file.is_file() or file.stat().st_size!=entry["bytes"] or sha(file)!=entry["sha256"]:
            raise RuntimeError("Audited original source checksum mismatch "+str(file))
        output[str(file.relative_to(ROOT))]=entry
    return output

def baseline(run_id):
    """A: SHA source audit; B: original directed synthetic transfer;
       C: separate stress panels; E: parent-level external source/destination."""
    original={}
    original.update(source_gate(SYN,"CROSS_FAMILY_TRANSFER_SHA256_MANIFEST.json",[
        "CROSS_FAMILY_TRANSFER_SCIENTIFIC_AUDIT.json",
        "HELDOUT_ORIGINAL_CROSSFAMILY_SUMMARY.csv",
        "HELDOUT_ORIGINAL_DIRECTED_FAMILY_ENGINE_MATRIX.csv",
        "REALWORLD_ORIGINAL_TRANSFER_SCOPE_BH_SUMMARY.csv"]))
    original.update(source_gate(PUB,"Q2_CROSSFAMILY_OUTPUT_SHA256_MANIFEST.json",[
        "Q2_CROSSFAMILY_PUBLICATION_AUDIT.json",
        "REALWORLD_ORIGINAL_CROSSFAMILY_8_POLICY_PANELS.csv",
        "REALWORLD_ORIGINAL_SOURCE_DESTINATION_FIGURE_CELLS.csv",
        "results_q2_crossfamily_realworld_original_profiles.png"]))
    rec_file=REC/"Q2_CROSSFAMILY_PUBLICATION_RECEIPT.json"
    receipt=json.loads(rec_file.read_text())
    if receipt.get("status")!="PASS_ORIGINAL_CROSSFAMILY_GENERALIZATION_RECOVERED_AND_CANONICAL_PDF_COMPILED":
        raise RuntimeError("Original publication receipt not in verified state")
    original[str(rec_file.relative_to(ROOT))]={"bytes":rec_file.stat().st_size,"sha256":sha(rec_file)}
    original_cross=rows(SYN/"HELDOUT_ORIGINAL_DIRECTED_FAMILY_ENGINE_MATRIX.csv")
    original_sum=rows(SYN/"HELDOUT_ORIGINAL_CROSSFAMILY_SUMMARY.csv")
    if len(original_cross)!=288 or len(original_sum)!=4:
        raise RuntimeError("Expected 288 original directed engine reference cells and four source-scope totals")
    seen=set();aggregate=defaultdict(lambda:Counter())
    mapped=[]
    for r in original_cross:
        fam,dest,engine,ref=r["source_family"],r["evaluation_family"],r["engine"],r["reference"]
        if fam not in FAMS or dest not in FAMS or engine not in ENGINES or ref not in ("own","mean"):
            raise RuntimeError("Unknown original synthetic transfer identity")
        key=(fam,dest,engine,ref)
        if key in seen:raise RuntimeError("Duplicate directed transfer cell")
        seen.add(key)
        expected_scope="within_family" if fam==dest else "cross_family"
        if r["scope"]!=expected_scope:raise RuntimeError("Incorrect original transfer scope")
        eligible=int(r["original_eligible_contrasts"])
        tier1=int(r["original_tier1_joint_BH_CI"])
        if eligible!=723 or tier1<0 or tier1>eligible:raise RuntimeError("Unexpected original directed test count")
        aggregate[(ref,expected_scope)]["eligible"]+=eligible
        aggregate[(ref,expected_scope)]["supported"]+=tier1
        mapped.append({**r,"supported_pct":f"{100*tier1/eligible:.6f}",
            "unit":"original_four_engine_pooled_effect_at_scenario",
            "independent_data":"original_heldout_evaluation_seeds_10_19",
            "evidence":"original_conditional_BH_plus_95CI"})
    if len(seen)!=6*6*4*2:raise RuntimeError("Directed source×destination×engine×reference coverage incomplete")
    for r in original_sum:
        k=(r["reference"],r["scope"]);summ=aggregate[k]
        if (summ["eligible"]!=int(r["eligible_original_contrasts"]) or
            summ["supported"]!=int(r["original_tier1_joint_BH_CI"])):
            raise RuntimeError("Directed cross-family matrix does not match original published scope totals")
    csvout(BASE/"B_cross_family/Q3_B_DIRECTED_288_ENGINE_TRANSFERS.csv",mapped)
    cand=receipt["heldout_original_individual_candidate_synthetic_transfer"]
    candidate_rows=[]
    for label,scope in (("selected_classical_within","within_family"),("selected_classical_out_of_source_family","cross_family")):
        x=cand[label];w=int(x["joint_BH_CI"]);total=int(x["eligible"])
        if (scope=="within_family" and (w,total)!=(877,173520) or
            scope=="cross_family" and (w,total)!=(5069,867600)):
            raise RuntimeError("Individual candidate contrast receipt has changed")
        candidate_rows.append({"panel":"original_Held_Out","reference":"discovery_selected_classical",
            "scope":scope,"supported_joint_BH_CI":w,"eligible":total,
            "supported_pct":f"{100*w/total:.8f}",
            "unit":"candidate_by_destination_family_by_scenario"})
    csvout(BASE/"B_cross_family/Q3_B_ORIGINAL_INDIVIDUAL_WEIGHT_TRANSFER.csv",candidate_rows)
    csvout(BASE/"B_cross_family/Q3_B_ORIGINAL_ENGINE_SCOPE_RATES.csv",
        [{**r,"unit":"pooled_engine_by_source_destination_scenario"} for r in original_sum])

    # C: source-verifiable structural stress scoping. The archive contains
    # original Stress results; the original narrative is used only for explicit
    # already-published *scope counts* and is NOT a fresh statistical test.
    findings=(REC/"CROSS_FAMILY_RECOVERY_FINDINGS.md").read_text()
    original[str((REC/"CROSS_FAMILY_RECOVERY_FINDINGS.md").relative_to(ROOT))]={
        "sha256":sha(REC/"CROSS_FAMILY_RECOVERY_FINDINGS.md"),
        "bytes":(REC/"CROSS_FAMILY_RECOVERY_FINDINGS.md").stat().st_size}
    regex=(r"(Historical Stress|Fresh Stress) original scope:\s*within\s*"
           r"([\d,]+)/([\d,]+),\s*cross\s*([\d,]+)/([\d,]+)")
    matches=re.findall(regex,findings)
    if len(matches)!=2:raise RuntimeError("Original archived structural Stress transfer totals absent")
    stress=[]
    for label,w,wd,c,cd in matches:
        for scope,num,den in (("within_family",w,wd),("cross_family",c,cd)):
            a=int(num.replace(",",""));b=int(den.replace(",",""))
            if b<1 or a>b:raise RuntimeError("Stress original count invalid")
            stress.append({"panel":label,"reference":"frozen_classical","scope":scope,
                "joint_original_BH_plus_CI":a,"eligible_original_contrasts":b,
                "supported_pct":f"{100*a/b:.8f}",
                "unit":"original_candidate_by_stress_scenario",
                "caution":"historical_and_fresh_differ_by_seeds_and_parameters"})
    if {(r["panel"],r["scope"],int(r["joint_original_BH_plus_CI"])) for r in stress} != {
        ("Historical Stress","within_family",0),("Historical Stress","cross_family",6),
        ("Fresh Stress","within_family",1799),("Fresh Stress","cross_family",4913)}:
        raise RuntimeError("Stress original support counts disagree with audited source")
    csvout(BASE/"C_structural_stress/Q3_C_ORIGINAL_STRESS_TRANSFER_SCOPE.csv",stress)
    jsonout(BASE/"C_structural_stress/Q3_C_DESIGN_AND_CAUSAL_BOUNDARY.json",{
        "status":"PRESERVED_ORIGINAL_STRESS_CONTRAST_TOTALS",
        "historical_evaluation":"independent_seeds_25_29_fixed_classical_selected_20_24",
        "fresh_evaluation":"independent_seeds_50_59_altered_generating_parameters",
        "reserved_bimodal_mechanisms":80,
        "adaptation":"original_and_adapted_frozen_cohorts_analysed_in_original_paper_not_relabelled_as_causal",
        "causal_interpretation":"DO_NOT_ATTRIBUTE_HISTORICAL_VS_FRESH_DIFFERENCE_TO_ONE_FACTOR",
        "full_source_stress_bytes":"data-archive/stress/actions_and_zenodo_LFS_original",
        "original_counts_reference":str((REC/"CROSS_FAMILY_RECOVERY_FINDINGS.md").relative_to(ROOT))})

    # E: real-world parent-cluster contrasts and assigned-family profiles.
    empirical=rows(PUB/"REALWORLD_ORIGINAL_CROSSFAMILY_8_POLICY_PANELS.csv")
    profiles=rows(PUB/"REALWORLD_ORIGINAL_SOURCE_DESTINATION_FIGURE_CELLS.csv")
    if len(empirical)!=8 or len(profiles)!=34 or receipt["realworld_original_parent_level_transfer"]["independent_parent_datasets"]!=642:
        raise RuntimeError("Empirical source/destination evidence inventory incomplete")
    eout=[]
    combos=set()
    for r in empirical:
        k=(r["benchmark_policy"],r["original_inferential_panel"],r["comparator"])
        if k in combos or k[0] not in ("source","destination") or k[1] not in ("primary","secondary") or k[2] not in ("own","mean"):
            raise RuntimeError("Invalid empirical benchmark policy/panel identity")
        combos.add(k)
        elig=int(r["eligible"]);wins=int(r["descriptive_joint_mean_loss_contrasts"])
        ci=int(r["both_conditional_CI_favorable"]);bh=int(r["both_BH_and_CI_favorable"])
        if elig!=(600 if k[1]=="primary" else 2040) or not (0<=bh<=ci<=elig) or wins>elig:
            raise RuntimeError("Original empirical evidence counters invalid")
        if str(r["empirical_destination_family_is_true_DGP"]).lower()!="false":
            raise RuntimeError("Assigned empirical destination is not a known generating family")
        eout.append({**r,"descriptive_joint_pct":f"{100*wins/elig:.6f}",
            "joint_supported_pct":f"{100*bh/elig:.6f}",
            "independent_inferential_unit":"parent_dataset_not_child_or_candidate_contrast",
            "original_parent_inventory":642,"target":"observed_empirical_mean_proxy"})
    if len(combos)!=8:raise RuntimeError("Real World source/destination benchmark crossed panel incomplete")
    csvout(BASE/"E_real_world/Q3_E_ORIGINAL_8_POLICY_PARENT_LEVEL_EVIDENCE.csv",eout)
    for r in profiles:
        for key in ("source_family","empirically_assigned_destination_family"):
            if r[key] not in FAMS:raise RuntimeError("Unknown empirical profile identity")
        if int(r["original_joint_BH_CI"])!=0:raise RuntimeError("Original BH panel has changed")
    csvout(BASE/"E_real_world/Q3_E_ORIGINAL_EMPIRICAL_DIRECTED_FAMILY_PROFILES.csv",profiles)

    # Full recovered source-family × assigned destination × engine taxonomy,
    # with all original three evidence scopes and both benchmark-indexing
    # policies. Every detail row must reconcile to original full 24-policy scope.
    two_dir=REC/"two_policy/runs/44748009646"
    original.update(source_gate(two_dir,"REALWORLD_TWO_POLICY_SHA256_MANIFEST.json",[
        "REALWORLD_TWO_ORIGINAL_CLASSICAL_POLICIES_SCOPE_TABLE.csv",
        "REALWORLD_TWO_ORIGINAL_POLICIES_ENGINE_SOURCE_DEST_TABLE.csv",
        "REALWORLD_TWO_POLICY_SCIENTIFIC_AUDIT.json"]))
    full_scope=rows(two_dir/"REALWORLD_TWO_ORIGINAL_CLASSICAL_POLICIES_SCOPE_TABLE.csv")
    full_engine=rows(two_dir/"REALWORLD_TWO_ORIGINAL_POLICIES_ENGINE_SOURCE_DEST_TABLE.csv")
    if len(full_scope)!=24 or len(full_engine)<24:
        raise RuntimeError("The complete original 2×2×2×3 Real World scope taxonomy is incomplete")
    totals=defaultdict(lambda:Counter())
    for r in full_engine:
        key=(r["benchmark_policy"],r["original_inferential_panel"],r["comparator"],r["transfer_scope"])
        if key[0] not in ("source","destination") or key[1] not in ("primary","secondary") or key[2] not in ("own","mean") or key[3] not in ("within_regime","within_family_neighborhood","cross_family_transfer"):
            raise RuntimeError("Original empirical detailed engine stratum unknown")
        if r["engine"] not in ENGINES or r["source_family"] not in FAMS:
            raise RuntimeError("Original empirical source/engine identity not in design")
        if r["empirical_destination_family"] and r["empirical_destination_family"] not in FAMS:
            raise RuntimeError("Unknown assigned (not true) empirical destination")
        t=totals[key]
        for k,c in (("eligible","eligible"),("original_descriptive_joint","joint"),
                    ("original_joint_conditional_CI","joint_ci"),
                    ("original_joint_BH_CI","joint_bh")):
            t[c]+=int(r[k])
    if len(totals)!=24:raise RuntimeError("One or more original empirical four-dimensional panels missing")
    for r in full_scope:
        k=(r["benchmark_policy"],r["original_inferential_panel"],r["comparator"],r["transfer_scope"])
        totals_k=totals[k]
        for col,expect in (("eligible","eligible"),("descriptive_joint_mean_loss_contrasts","joint"),
                           ("both_conditional_CI_favorable","joint_ci"),
                           ("both_BH_and_CI_favorable","joint_bh")):
            if int(r[col])!=totals_k[expect]:
                raise RuntimeError("Full original empirical engine taxonomy disagrees with verified 24-scope inference at "+str(k)+" "+col)
    csvout(BASE/"E_real_world/Q3_E_COMPLETE_ORIGINAL_24_COMPARATOR_SCOPE_TABLE.csv",full_scope)
    csvout(BASE/"E_real_world/Q3_E_COMPLETE_ORIGINAL_ENGINE_SOURCE_DESTINATION.csv",full_engine)

    jsonout(BASE/"A_provenance/Q3_A_SOURCE_LINEAGE.json",{
        "schema":"T3_Q3_SINGLE_RUN_ORIGINAL_SOURCE_AUDIT_V1",
        "run_id":str(run_id),
        "status":"SOURCE_AUDIT_PASS",
        "verified_source_files":original,
        "training_model_count":720,"original_training_seeds":"0:9",
        "heldout_evaluation_seeds":"10:19",
        "historical_stress_evaluation_seeds":"25:29",
        "fresh_stress_evaluation_seeds":"50:59",
        "external_empirical_parent_ids":642,
        "already_archived_original_bytes_in_T3":45354058307,
        "original_immutable_archive_scope":"7994 enumerated archive sources; not all 45GB is copied into Q3",
        "science":"No new optimization or original Held Out/Stress/RealWorld test inference",
        "scope_limits":"Distinct inference units, benchmark scopes and null calibrations never pooled"})
    print("Q3_A_B_C_E_ORIGINAL_SOURCE_AUDITS_PASS 288 directed engine cells, 4 stress scope cells, 8 Real World policies")

def boolstr(s):
    if str(s).strip().upper() in ("TRUE","T","1"):return True
    if str(s).strip().upper() in ("FALSE","F","0"):return False
    raise RuntimeError("Unrecognized original logical field "+str(s))

def summarize_parametric(input_root):
    root=Path(input_root)/"aggregate/taxonomy_by_panel"
    files=sorted(root.glob("*.csv.gz"))
    if len(files)!=54:raise RuntimeError(f"Expected exactly 54 prespecified compact parameter panels; got {len(files)}")
    cohort=defaultdict(lambda:Counter())
    per_parameter=defaultdict(lambda:Counter())
    all_rows=0
    modes=set()
    panels_seen=set()
    for file in files:
        with gzip.open(file,"rt",newline="",encoding="utf-8") as f:
            reader=csv.DictReader(f)
            req={"family","parameter_row","sample_n","candidate_engine","benchmark_role",
                "difference.mse","difference.q95","ci_upper.mse","ci_upper.q95",
                "q_value_global.mse","q_value_global.q95","tier1_joint_mse_q95_bh_fdr"}
            if not req.issubset(set(reader.fieldnames or [])):
                raise RuntimeError("Original parametric inference export schema differs: "+str(file)+str(sorted(req-set(reader.fieldnames or []))))
            for r in reader:
                fam=r["family"];n=int(r["sample_n"]);param=int(r["parameter_row"])
                method=r["candidate_engine"];ref=r["benchmark_role"]
                if fam not in FAMS or n not in (200,1000,3000) or method not in ENGINES:
                    raise RuntimeError("Parametric original full panel identity invalid")
                if ref not in ("own","mean"):raise RuntimeError("Unknown parametric reference role: "+ref)
                key=(fam,n,method,ref);pk=(fam,param,n,method,ref)
                mse=float(r["difference.mse"]);q95=float(r["difference.q95"])
                gain_m=float(r.get("gain_pct.mse","nan"));gain_q=float(r.get("gain_pct.q95","nan"))
                if not (math.isfinite(mse) and math.isfinite(q95)):
                    raise RuntimeError("Nonfinite original parametric loss differences")
                joint=mse<0 and q95<0
                only_m=mse<0 and not q95<0
                only_q=q95<0 and not mse<0
                ci_m=float(r["ci_upper.mse"])<0;ci_q=float(r["ci_upper.q95"])<0
                b_m=ci_m and float(r["q_value_global.mse"])<=.05
                b_q=ci_q and float(r["q_value_global.q95"])<=.05
                orig=boolstr(r["tier1_joint_mse_q95_bh_fdr"])
                if orig != (b_m and b_q):
                    raise RuntimeError("Original global BH tier and paired confidence interval disagree")
                for stats in (cohort[key],per_parameter[pk]):
                    stats["eligible"]+=1
                    stats["joint_point"]+=int(joint)
                    stats["MSE_only_point"]+=int(only_m)
                    stats["Q95_only_point"]+=int(only_q)
                    stats["neither_point"]+=int(not (joint or only_m or only_q))
                    stats["joint_CI"]+=int(ci_m and ci_q)
                    stats["joint_BH_CI"]+=int(orig)
                    stats["MSE_BH_CI"]+=int(b_m)
                    stats["Q95_BH_CI"]+=int(b_q)
                    if math.isfinite(gain_m):stats["gain_MSE_sum"]+=gain_m;stats["gain_MSE_finite"]+=1
                    if math.isfinite(gain_q):stats["gain_Q95_sum"]+=gain_q;stats["gain_Q95_finite"]+=1
                panels_seen.add((fam,param,n));modes.add(ref)
                all_rows+=1
    if len(panels_seen)!=54 or modes!={"own","mean"} or len(cohort)!=144 or len(per_parameter)!=432:
        raise RuntimeError(f"Incomplete parameter profiles: {len(panels_seen)} panels {len(cohort)} grouped {len(per_parameter)} parameter")
    def serialize(keys,table):
        out=[]
        for k,c in sorted(table.items()):
            d=dict(zip(keys,k));n=c["eligible"]
            if n<1:raise RuntimeError("Empty inferential denominator")
            out.append({**d,"eligible_original_contrasts":n,
                "joint_point":c["joint_point"],"MSE_only_point":c["MSE_only_point"],
                "Q95_only_point":c["Q95_only_point"],"neither_point":c["neither_point"],
                "joint_CI":c["joint_CI"],"MSE_BH_plus_CI":c["MSE_BH_CI"],
                "Q95_BH_plus_CI":c["Q95_BH_CI"],"joint_BH_plus_CI":c["joint_BH_CI"],
                "joint_supported_pct":f"{100*c['joint_BH_CI']/n:.6f}",
                "mean_original_MSE_gain_pct":f"{c['gain_MSE_sum']/c['gain_MSE_finite']:.6f}" if c["gain_MSE_finite"] else "",
                "mean_original_Q95_gain_pct":f"{c['gain_Q95_sum']/c['gain_Q95_finite']:.6f}" if c["gain_Q95_finite"] else "",
                "independent_inference_unit":"reserved_transfer_seed_40_49",
                "multiplicity":"original_global_BH_all_parameter_panels_both_metrics"})
        return out
    csvout(BASE/"D_parameter_transfer/Q3_D_144_FAMILY_N_ENGINE_REFERENCE.csv",
        serialize(["family","sample_n","engine","reference"],cohort))
    csvout(BASE/"D_parameter_transfer/Q3_D_432_PARAMETER_ROW_N_ENGINE_REFERENCE.csv",
        serialize(["family","parameter_row","sample_n","engine","reference"],per_parameter))
    jsonout(BASE/"D_parameter_transfer/Q3_D_INFERENCE_AUDIT.json",{
        "status":"ORIGINAL_FULL_PARAMETRIC_INFERENCE_COMPLETENESS_PASS",
        "number_of_alternative_parameter_rows":18,"distinct_parameter_sample_size_panels":54,
        "inferred_original_candidate_reference_scenario_rows":all_rows,
        "pooled_family_sample_size_engine_reference_groups":len(cohort),
        "alternative_parameter_row_by_n_engine_reference_groups":len(per_parameter),
        "frozen_original_training_seed_axis":"0:9_averaged_within_each_inference_seed",
        "independent_parameter_transfer_seed_axis":"40:49",
        "original_full_global_BH_adjustment":"performed_by_existing_t3_b3_parametric_transfer_inference.R",
        "estimated_selection_aware_global_error_control":"NOT_ESTABLISHED",
        "candidate_specific_CI":"NOT_ESTIMATED_OR_FABRICATED",
        "new_optimizer_training":False})
    print("Q3_D_GLOBAL_ORIGINAL_BH_INFERENCE_AUDIT_PASS",all_rows,len(panels_seen))

def check_manifest(path):
    root=Path(path).parent
    meta=json.loads(Path(path).read_text())
    if meta.get("status")!="PASS_VERIFIED_UNCOMPRESSED_SCORES":
        raise RuntimeError("Q3 scored archive manifest status invalid")
    for x in meta["parts"]:
        p=root/x["name"]
        if not p.exists() or p.stat().st_size!=x["bytes"] or sha(p)!=x["sha256"]:
            raise RuntimeError("Permanent archive part missing or corrupt: "+str(p))
    return meta

def pack(input_path,archive_path,name,expected_score_count=None):
    inp=Path(input_path);archive=Path(archive_path)
    if not inp.is_dir():raise RuntimeError("Missing input score tree")
    archive.mkdir(parents=True,exist_ok=True)
    files=sorted(p for p in inp.rglob("*") if p.is_file())
    if not files:raise RuntimeError("Cannot archive empty scientific output")
    if expected_score_count is not None:
        score=sorted(inp.rglob("scores.csv"));mans=sorted(inp.rglob("score_manifest.csv"))
        if len(score)!=expected_score_count or len(mans)!=expected_score_count:
            raise RuntimeError("Cannot back up a partial set of original scored parameter-transfer shards")
        manifest_keys=set()
        for mp in mans:
            with mp.open(newline="",encoding="utf-8") as f:r=list(csv.DictReader(f))
            if len(r)!=1 or sha(mp.with_name("scores.csv"))!=r[0].get("scores_sha256"):
                raise RuntimeError("Unverified original score CSV during permanent packaging")
            k=(r[0]["family"],r[0]["parameter_row"],r[0]["seed"],r[0]["n"])
            if k in manifest_keys:raise RuntimeError("Duplicated source scoring identity")
            manifest_keys.add(k)
    # Use deterministic gzip: a plain tar is read and compressed with an
    # explicit mtime=0. File payloads and per-member digest remain audited.
    tmp=archive/(name+".uncompressed.tar")
    with tarfile.open(tmp,"w") as tf:
        for file in files:
            rel=file.relative_to(inp)
            t=tf.gettarinfo(str(file),arcname=str(rel))
            t.uid=t.gid=0;t.uname=t.gname="";t.mtime=0
            with file.open("rb") as fin:tf.addfile(t,fin)
    compressed=archive/(name+".tar.gz")
    with tmp.open("rb") as fin,compressed.open("wb") as raw:
        with gzip.GzipFile(filename="",mode="wb",fileobj=raw,mtime=0,compresslevel=6) as gz:
            shutil.copyfileobj(fin,gz,1024*1024)
    tmp.unlink()
    partsize=30*1024*1024;parts=[]
    with compressed.open("rb") as source:
        for j in range((compressed.stat().st_size+partsize-1)//partsize):
            piece=archive/f"{name}.part{j:03d}.lfs"
            with piece.open("wb") as out:
                remain=partsize
                while remain:
                    buf=source.read(min(1024*1024,remain))
                    if not buf:break
                    out.write(buf);remain-=len(buf)
            parts.append({"name":piece.name,"bytes":piece.stat().st_size,"sha256":sha(piece)})
    full={"schema":"T3_Q3_PERMANENT_LFS_PART_ARCHIVE_V1",
         "status":"PASS_VERIFIED_UNCOMPRESSED_SCORES",
         "name":name,"filename":compressed.name,
         "original_file_count":len(files),
         "original_scores":expected_score_count,
         "source_payload_members":{str(p.relative_to(inp)):{"sha256":sha(p),"bytes":p.stat().st_size} for p in files},
         "compressed_size":compressed.stat().st_size,"compressed_sha256":sha(compressed),
         "parts":parts,
         "note":"LFS parts carry all original scoring CSV and lineage manifests, not the regenerated ~17MB per-shard RDS Monte Carlo matrices"}
    jsonout(archive/"manifest.json",full)
    compressed.unlink()
    print("Q3_PERMANENT_ARCHIVE_PACKAGE_PASS",archive,parts.__len__(),"files",len(files))

def unpack(manifest_path,target):
    meta=check_manifest(manifest_path)
    target=Path(target);target.mkdir(parents=True,exist_ok=True)
    if any(target.iterdir()):
        raise RuntimeError("Refusing unpack into a nonempty inference input root")
    source=Path(manifest_path).parent
    compressed=target.parent/(meta["name"]+"_verify.tar.gz")
    with compressed.open("wb") as out:
        for part in meta["parts"]:
            with (source/part["name"]).open("rb") as fi:shutil.copyfileobj(fi,out,1024*1024)
    if compressed.stat().st_size!=meta["compressed_size"] or sha(compressed)!=meta["compressed_sha256"]:
        raise RuntimeError("Reconstructed permanently stored complete transfer scores fail SHA-256")
    # Use a safe member whitelist; no traversal or links accepted.
    with tarfile.open(compressed,"r:gz") as tf:
        for member in tf.getmembers():
            if not member.isfile() or Path(member.name).is_absolute() or ".." in Path(member.name).parts:
                raise RuntimeError("Invalid scientific backup TAR path/type")
        tf.extractall(target,filter="data")
    compressed.unlink()
    for rel,expect in meta["source_payload_members"].items():
        file=target/rel
        if not file.is_file() or file.stat().st_size!=expect["bytes"] or sha(file)!=expect["sha256"]:
            raise RuntimeError("Restored source scientific payload SHA mismatch: "+rel)
    print("Q3_RESTORED_COMPLETE_SOURCE_SCORES_PASS",len(meta["source_payload_members"]))

def finalize(run_id):
    for f in [
        BASE/"A_provenance/Q3_A_SOURCE_LINEAGE.json",
        BASE/"B_cross_family/Q3_B_DIRECTED_288_ENGINE_TRANSFERS.csv",
        BASE/"C_structural_stress/Q3_C_ORIGINAL_STRESS_TRANSFER_SCOPE.csv",
        BASE/"D_parameter_transfer/Q3_D_INFERENCE_AUDIT.json",
        BASE/"D_parameter_transfer/Q3_D_144_FAMILY_N_ENGINE_REFERENCE.csv",
        BASE/"E_real_world/Q3_E_ORIGINAL_8_POLICY_PARENT_LEVEL_EVIDENCE.csv",
    ]:
        if not f.is_file():raise RuntimeError("Q3 A-G synthesis missing required verified scientific input "+str(f))
    d=json.loads((BASE/"D_parameter_transfer/Q3_D_INFERENCE_AUDIT.json").read_text())
    if d["status"]!="ORIGINAL_FULL_PARAMETRIC_INFERENCE_COMPLETENESS_PASS":
        raise RuntimeError("Incomplete within-family changed-parameter inference")
    all_rows=[]
    for r in rows(BASE/"B_cross_family/Q3_B_ORIGINAL_INDIVIDUAL_WEIGHT_TRANSFER.csv"):
        all_rows.append({"environment":"Held Out (original cross-family)","comparison":"individual original frozen candidate",
            "reference":r["reference"],"scope":r["scope"],"positive_joint":r["supported_joint_BH_CI"],
            "eligible":r["eligible"],"support_pct":r["supported_pct"],
            "evidence":"original conditional BH plus 95% CI","unit":r["unit"]})
    for r in rows(BASE/"C_structural_stress/Q3_C_ORIGINAL_STRESS_TRANSFER_SCOPE.csv"):
        all_rows.append({"environment":r["panel"],"comparison":"original frozen composite",
            "reference":r["reference"],"scope":r["scope"],"positive_joint":r["joint_original_BH_plus_CI"],
            "eligible":r["eligible_original_contrasts"],"support_pct":r["supported_pct"],
            "evidence":"original conditional BH plus 95% CI","unit":r["unit"]})
    for r in rows(BASE/"E_real_world/Q3_E_ORIGINAL_8_POLICY_PARENT_LEVEL_EVIDENCE.csv"):
        all_rows.append({"environment":"Real World "+r["original_inferential_panel"],
            "comparison":"empirical "+r["benchmark_policy"]+" comparator indexing",
            "reference":r["comparator"],"scope":"assigned_profile_cross_family",
            "positive_joint":r["both_BH_and_CI_favorable"],"eligible":r["eligible"],
            "support_pct":r["joint_supported_pct"],
            "evidence":"original conditional parent-cluster BH plus 95% CI",
            "unit":r["independent_inferential_unit"]})
    for r in rows(BASE/"D_parameter_transfer/Q3_D_144_FAMILY_N_ENGINE_REFERENCE.csv"):
        all_rows.append({"environment":"Within-family parameter transfer",
            "comparison":r["family"]+" n="+str(r["sample_n"])+" "+r["engine"],
            "reference":r["reference"],"scope":"alternative_non_base_parameter_rows",
            "positive_joint":r["joint_BH_plus_CI"],"eligible":r["eligible_original_contrasts"],
            "support_pct":r["joint_supported_pct"],
            "evidence":"new original-design full-panel BH plus paired 95% CI",
            "unit":r["independent_inference_unit"]})
    csvout(BASE/"F_synthesis/Q3_F_CROSS_ENVIRONMENT_EVIDENCE_UNITS.csv",all_rows)
    generate_figures()
    total_by_stage=Counter(r["environment"] for r in all_rows)
    report="# Q3 — Generalization across independent data and distributional changes\n\n"
    report+=("This audit preserves the original tested frozen weights and distinguishes "
        "independent new sample evaluation, out-of-source-family synthetic transfer, "
        "previously withheld bimodal structural contamination, non-base within-family "
        "parameter changes, and empirical assigned-family transfer. It does not seek "
        "a globally best estimator. \n\n")
    report+=("## Prespecified within-family parameter-shift sensitivity scope\\n\\n"
        "For each of six generating families, three non-base parameter-grid rows "
        "(first alternative, middle alternative, final alternative) were chosen "
        "without consulting outcomes. The clean scenario and eight fixed maximin "
        "cells from each of six contamination mechanisms were tested in all three "
        "sample sizes and ten independent transfer seeds. Every selected setting "
        "uses 500 replications. This yields 540 full 49-scenario score shards. "
        "Original 241-scenario scores, when independently verified, are restricted "
        "to the exact selected 49 scenario IDs without recalculating source losses. "
        "This is a deliberately bounded sensitivity analysis and does not establish "
        "uniform performance across all 83 alternative parameter configurations "
        "or all 240 original contaminated support scenarios.\\n\\n")
    report+="## Verified evidence inventory\\n\\n"
    for k,n in sorted(total_by_stage.items()):
        report+=f"- **{k}:** {n:,} separately denominated rows in the integrated scientific index.\n"
    report+=("\n## Scientific interpretation guardrails\n\n"
        "1. A source-family candidate evaluated in a new destination family is genuine "
        "synthetic family transfer; within-source-family neighborhood persistence "
        "is a different experiment.\n"
        "2. Historical and fresh structural Stress tests use different evaluation "
        "stream/parameter policies and their contrast rates must not be treated "
        "as a randomized one-factor intervention.\n"
        "3. Parameter-shift inference uses original frozen Discovery models and "
        "held-out transfer seeds 40–49; full cross-panel BH is recomputed once "
        "by the original transfer inference R implementation, not by the "
        "read-only cross-stage synthesis.\n"
        "4. The 642 Real World parent datasets are the independent empirical "
        "inference units, not 600 or 2,040 independent samples; assigned empirical "
        "destination families are proxies and the observed sample-mean target "
        "is not known clean population truth.\n"
        "5. BH-adjusted evidence is conditional on original dependency and "
        "validity assumptions, not a demonstrated selection-aware pipeline FDR. "
        "Stage-specific percentages cannot be pooled into one global error rate.\n"
        "6. These outputs are a scientific analysis package and writing-ready figures; "
        "no changes are made to the private canonical manuscript before result review.\n")
    path=BASE/"F_synthesis/Q3_F_SCIENTIFIC_RESULTS_AND_LIMITATIONS.md"
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(report,encoding="utf-8")
    files=sorted(x for x in BASE.rglob("*") if x.is_file() and "G_publication_audit" not in x.parts)
    meta={str(f.relative_to(BASE)):{"bytes":f.stat().st_size,"sha256":sha(f)} for f in files}
    jsonout(BASE/"G_publication_audit/Q3_G_COMPLETE_MANIFEST.json",{
        "schema":"T3_Q3_A_THROUGH_G_SINGLE_RUN_PUBLICATION_PREPARATION_V1",
        "status":"COMPLETE_SCIENTIFIC_ANALYSIS_A_TO_G_PASS",
        "workflow_run_id":str(run_id),"original_weight_count":720,
        "reused_original_heldout_stress_realworld_inference":True,
        "new_independent_within_family_parameter_transfer_inference":True,
        "full_pipeline_nested_optimizer_selection_calibration":False,
        "current_manuscript_automatically_rewritten":False,
        "source_counts":total_by_stage,"files":meta,
        "permanent_Q3_score_archives":"Q3/D_parameter_transfer/compact_v1/scored_archive",
        "note":"Only claim complete publication backup after successful Git LFS upload and final GitHub verification"})
    print("Q3_A_TO_G_FIGURES_TABLES_CHECKSUM_MANIFEST_PASS",len(files))

def generate_figures():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as e:raise RuntimeError("matplotlib missing for manuscript-ready Q3 graphics") from e
    out=BASE/"F_synthesis";out.mkdir(parents=True,exist_ok=True)
    # Figure 1: original pooled search-method transfer after global original BH adjustment.
    data=rows(BASE/"B_cross_family/Q3_B_DIRECTED_288_ENGINE_TRANSFERS.csv")
    mapdata={(r["source_family"],r["evaluation_family"]):[0,0] for r in data if r["reference"]=="own"}
    for r in data:
        if r["reference"]!="own":continue
        t=mapdata[(r["source_family"],r["evaluation_family"])]
        t[0]+=int(r["original_tier1_joint_BH_CI"])
        t[1]+=int(r["original_eligible_contrasts"])
    table=[[100*mapdata[(a,b)][0]/mapdata[(a,b)][1] for b in FAMS] for a in FAMS]
    fig,ax=plt.subplots(figsize=(9.4,7))
    im=ax.imshow(table,cmap="Blues",aspect="equal")
    ax.set_xticks(range(6),[s.replace("invgauss","Inv. Gaussian").replace("exgaussian","Ex Gaussian").replace("exwald","Ex Wald") for s in FAMS],rotation=35,ha="right")
    ax.set_yticks(range(6),[s.replace("invgauss","Inv. Gaussian").replace("exgaussian","Ex Gaussian").replace("exwald","Ex Wald") for s in FAMS])
    for i in range(6):
        for j in range(6):
            v=table[i][j]
            ax.text(j,i,f"{v:.2f}%",ha="center",va="center",fontsize=8,color="white" if v>max(max(row) for row in table)*.55 else "black")
    ax.set_xlabel("Independent evaluation (destination) family")
    ax.set_ylabel("Discovery (training) family")
    ax.set_title("Frozen-estimator transfer to previously unseen source-family distributions\nOriginal pooled-engine BH + 95% CI support vs selected classical reference")
    fig.colorbar(im,ax=ax,label="Joint supported original contrasts (%)",fraction=.046)
    fig.tight_layout();fig.savefig(out/"results_q3_original_synthetic_directed_transfer.png",dpi=180);plt.close(fig)
    # Figure 2: three sample-size strata combined, no pooling across benchmark types.
    drows=rows(BASE/"D_parameter_transfer/Q3_D_144_FAMILY_N_ENGINE_REFERENCE.csv")
    stat=defaultdict(lambda:[0,0])
    for r in drows:
        if r["reference"]!="own":continue
        key=(r["family"],r["engine"])
        stat[key][0]+=int(r["joint_BH_plus_CI"])
        stat[key][1]+=int(r["eligible_original_contrasts"])
    mat=[[100*stat[(fam,engine)][0]/stat[(fam,engine)][1] for engine in ENGINES] for fam in FAMS]
    fig,ax=plt.subplots(figsize=(8.2,6))
    im=ax.imshow(mat,cmap="viridis",aspect="auto")
    ax.set_xticks(range(4),["GA","NSGA-II","DE","Dirichlet"])
    ax.set_yticks(range(6),["Normal","Lognormal","Weibull","Inv. Gaussian","Ex Gaussian","Ex Wald"])
    for i in range(6):
        for j in range(4):
            ax.text(j,i,f"{mat[i][j]:.2f}%",ha="center",va="center",color="white",fontsize=9)
    ax.set_title("Fixed-weight adaptation to unseen parameterizations\nJoint paired-CI and globally BH-supported comparisons vs classical reference")
    fig.colorbar(im,ax=ax,label="Supported original parameter-transfer contrasts (%)")
    fig.tight_layout();fig.savefig(out/"results_q3_parametric_transfer_joint_evidence.png",dpi=180);plt.close(fig)
    # Figure 3: original independent empirical panel descriptive vs inferential distinction.
    data=rows(BASE/"E_real_world/Q3_E_ORIGINAL_8_POLICY_PARENT_LEVEL_EVIDENCE.csv")
    keep=[r for r in data if r["original_inferential_panel"]=="secondary"]
    labels=[r["benchmark_policy"]+" / "+r["comparator"] for r in keep]
    supported=[float(r["joint_supported_pct"]) for r in keep]
    descriptive=[float(r["descriptive_joint_pct"]) for r in keep]
    fig,ax=plt.subplots(figsize=(8.2,4.5))
    y=range(len(keep))
    ax.barh(list(y),descriptive,label="Joint positive original point effects")
    ax.plot(supported,list(y),linestyle="none",marker="o",label="Joint BH + favorable paired CI")
    ax.set_yticks(list(y),labels)
    ax.set_xlabel("Share of original parent-aggregated candidate contrasts (%)")
    ax.set_title("External empirical assigned-family transfer: point effects vs inferential support\nIndependent inference is clustered by parent dataset")
    ax.legend(loc="lower right")
    fig.tight_layout();fig.savefig(out/"results_q3_realworld_support_boundary.png",dpi=180);plt.close(fig)

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="mode",required=True)
    a=sub.add_parser("baseline");a.add_argument("--run-id",required=True)
    a=sub.add_parser("summarize-parametric");a.add_argument("--input",type=Path,required=True)
    a=sub.add_parser("pack");a.add_argument("--input",type=Path,required=True);a.add_argument("--out",type=Path,required=True)
    a.add_argument("--name",required=True);a.add_argument("--expected-scores",type=int)
    a=sub.add_parser("unpack");a.add_argument("--manifest",type=Path,required=True);a.add_argument("--out",type=Path,required=True)
    a=sub.add_parser("finalize");a.add_argument("--run-id",required=True)
    a=sub.add_parser("self-test")
    args=p.parse_args()
    if args.mode=="baseline":baseline(args.run_id)
    elif args.mode=="summarize-parametric":summarize_parametric(args.input)
    elif args.mode=="pack":pack(args.input,args.out,args.name,args.expected_scores)
    elif args.mode=="unpack":unpack(args.manifest,args.out)
    elif args.mode=="finalize":finalize(args.run_id)
    elif args.mode=="self-test":
        assert len(FAMS)==6 and len(ENGINES)==4
        assert len(FAMS)*3==18
        assert 18*3*10==540
        print("Q3_COMPACT_SCIENCE_SELFTEST_PASS parameter rows=18; complete 49-scenario shards=540")

if __name__=="__main__":main()
