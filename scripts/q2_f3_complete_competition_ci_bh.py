#!/usr/bin/env python3
"""Produce comprehensive Q2 competition + 95% CI + BH-FDR tables.

Scientific level: family x n x engine x benchmark x contamination mechanism,
with original ten training and ten independent Held Out evaluation seeds and
forty already-observed contamination cells held fixed. Output is not an
individual-training-seed CI, not per-scenario inference, and not selection-aware
full-pipeline error calibration. No new scoring/training/inference.
"""
from __future__ import annotations
import csv
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Q2/F3/runs/44622921203/publication"
OUTPUT = ROOT / "Q2/F3/leaderboards"
OUTPUT.mkdir(parents=True, exist_ok=True)
INFILES = {
    "Q2_F3_ALL_1728_EXPLORATORY_BH_METRICS.csv": "11dfe6dc1506ad1579969c3877abe028c798d67d4a2e82aa577fdf286124369f",
    "Q2_F3_ALL_864_MECHANISM_EVIDENCE.csv": "aead9cef49fa3f931723a58e294856236064d2b3c8ddc67d44d8b8d7c189c3bf",
    "Q2_F3_TABLE_FOUR_ENGINE_EXPLORATORY_BH.csv": "29ecf26ebe24408aa43748c8ab88184dae1195b393c23fc20a80119433fc8486",
}
for name,expected in INFILES.items():
    found = hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()
    if found != expected:
        raise AssertionError(f"Original input checksum mismatch: {name}, {found}")

def read(name: str) -> list[dict[str,str]]:
    with (SOURCE/name).open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))
raw = read("Q2_F3_ALL_1728_EXPLORATORY_BH_METRICS.csv")
original_flags = read("Q2_F3_ALL_864_MECHANISM_EVIDENCE.csv")
original_engine = read("Q2_F3_TABLE_FOUR_ENGINE_EXPLORATORY_BH.csv")
assert len(raw)==1728 and len(original_flags)==864 and len(original_engine)==8

def flag(x):
    if str(x).lower() in ("true","1"): return True
    if str(x).lower() in ("false","0"): return False
    raise ValueError("Unexpected Boolean: "+str(x))
keycols=("family","sample_n","method","benchmark_role","mechanism")
grouped=defaultdict(dict)
for r in raw:
    key=tuple(r[c] for c in keycols)
    assert r["metric"] in ("mse_gain_pct","q95_gain_pct")
    assert r["metric"] not in grouped[key]
    grouped[key][r["metric"]]=r
assert len(grouped)==864 and all(len(t)==2 for t in grouped.values())
original_lookup={tuple(r[c] for c in keycols):r for r in original_flags}
assert len(original_lookup)==864 and set(original_lookup)==set(grouped)
def cname(m,q):
    if m and q:return "joint"
    if m:return "MSE-only"
    if q:return "Q95-only"
    return "neither"
def is_favorable(r):
    lo=float(r["ci95_low"])
    hi=float(r["ci95_high"])
    val=float(r["average_gain_pct"])
    assert lo <= hi, r
    return lo>0
def bh_positive(r):
    return is_favorable(r) and float(r["BH_q_all864_per_metric"])<=.05
def signed_point(r):
    return float(r["average_gain_pct"])>0

detailed=[]
for key,t in sorted(grouped.items()):
    fam,n,engine,policy,mechanism=key
    mse=t["mse_gain_pct"];q95=t["q95_gain_pct"]
    old=original_lookup[key]
    for r in (mse,q95):
        assert int(r["original_training_seeds"])==10
        assert int(r["independent_evaluation_seeds"])==10
        assert int(r["scenarios_in_mechanism"])==40
        assert flag(r["posthoc_inference"]) is True
        assert flag(r["scenario_resampling"]) is False
        assert flag(r["positive_CI"])==is_favorable(r)
        assert flag(r["positive_BH_CI"])==bh_positive(r)
        qval=float(r["BH_q_all864_per_metric"])
        assert 0<=qval<=1
    ocols=(("positive_CI_mse_gain_pct",mse,is_favorable),
           ("positive_CI_q95_gain_pct",q95,is_favorable),
           ("positive_BH_CI_mse_gain_pct",mse,bh_positive),
           ("positive_BH_CI_q95_gain_pct",q95,bh_positive))
    for field,r,fn in ocols:
        assert flag(old[field])==fn(r), (key,field)
    assert flag(old["joint_CI"])==(is_favorable(mse) and is_favorable(q95))
    assert flag(old["joint_BH"])==(bh_positive(mse) and bh_positive(q95))
    detailed.append({
        "family":fam,"sample_n":n,"engine":engine,"reference":policy,"mechanism":mechanism,
        "observed_scenarios":40,"training_seeds":10,"heldout_evaluation_seeds":10,
        "MSE_gain_pct":mse["average_gain_pct"],"MSE_CI95_lower_pct":mse["ci95_low"],
        "MSE_CI95_upper_pct":mse["ci95_high"],
        "MSE_original_bootstrap_p_exploratory":mse["exploratory_bootstrap_p"],
        "MSE_original_BH_q_all864":mse["BH_q_all864_per_metric"],
        "MSE_CI_positive":int(is_favorable(mse)),
        "MSE_BH_and_CI_positive":int(bh_positive(mse)),
        "Q95_gain_pct":q95["average_gain_pct"],"Q95_CI95_lower_pct":q95["ci95_low"],
        "Q95_CI95_upper_pct":q95["ci95_high"],
        "Q95_original_bootstrap_p_exploratory":q95["exploratory_bootstrap_p"],
        "Q95_original_BH_q_all864":q95["BH_q_all864_per_metric"],
        "Q95_CI_positive":int(is_favorable(q95)),
        "Q95_BH_and_CI_positive":int(bh_positive(q95)),
        "point_estimate_class":cname(signed_point(mse),signed_point(q95)),
        "conditional_CI_class":cname(is_favorable(mse),is_favorable(q95)),
        "exploratory_BH_plus_CI_class":cname(bh_positive(mse),bh_positive(q95)),
        "candidate_level_CI":"NOT_DERIVED_FROM_ENGINE_LEVEL_PANEL",
        "original_BH_scope":"864_mechanism_contrasts_per_metric_across_both_references",
        "full_nested_selection_calibrated":"NO",
    })
assert len(detailed)==864
counts=Counter((r["engine"],r["reference"]) for r in detailed)
assert set(counts.values())=={108} and len(counts)==8
for r in original_engine:
    k=(r["method"],r["benchmark_role"])
    rows=[x for x in detailed if (x["engine"],x["reference"])==k]
    assert len(rows)==int(r["mechanism_tests"])==108
    checks={
       "joint_CI":sum(x["conditional_CI_class"]=="joint" for x in rows),
       "joint_BH_exploratory":sum(x["exploratory_BH_plus_CI_class"]=="joint" for x in rows),
       "MSE_BH_exploratory":sum(x["MSE_BH_and_CI_positive"] for x in rows),
       "Q95_BH_exploratory":sum(x["Q95_BH_and_CI_positive"] for x in rows)}
    for name,n in checks.items():
        assert n==int(r[name]),(k,name,n,r[name])

def write_csv(name,items):
    path=OUTPUT/name
    with path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(items[0]),lineterminator="\n")
        writer.writeheader()
        writer.writerows(items)
    return path
write_csv("Q2_F3_COMPLETE_864_TOURNAMENT_CI_BH_EVIDENCE.csv",detailed)

family_bins=defaultdict(list)
for r in detailed:
    family_bins[(r["family"],r["reference"],r["engine"])].append(r)
summary=[]
for (fam,reference,engine),rows in sorted(family_bins.items()):
    assert len(rows)==18
    tally=Counter(r["point_estimate_class"] for r in rows)
    ci_joint=sum(r["conditional_CI_class"]=="joint" for r in rows)
    fdr_joint=sum(r["exploratory_BH_plus_CI_class"]=="joint" for r in rows)
    fdr_mse=sum(r["MSE_BH_and_CI_positive"] for r in rows)
    fdr_q95=sum(r["Q95_BH_and_CI_positive"] for r in rows)
    assert sum(tally.values())==18
    summary.append({
       "family":fam,"reference":reference,"engine":engine,"mechanism_panels":18,
       "joint_point_effects":tally["joint"],
       "MSE_only_point_effects":tally["MSE-only"],
       "Q95_only_point_effects":tally["Q95-only"],
       "neither_point_effects":tally["neither"],
       "median_MSE_gain_pct":f"{statistics.median(float(r['MSE_gain_pct']) for r in rows):.3f}",
       "median_Q95_gain_pct":f"{statistics.median(float(r['Q95_gain_pct']) for r in rows):.3f}",
       "joint_favorable_95CI":ci_joint,
       "MSE_BH_plus_CI_positive_count":fdr_mse,
       "Q95_BH_plus_CI_positive_count":fdr_q95,
       "joint_BH_plus_CI_positive_count":fdr_joint,
       "MSE_BH_plus_CI_positive_pct":f"{100*fdr_mse/18:.2f}",
       "Q95_BH_plus_CI_positive_pct":f"{100*fdr_q95/18:.2f}",
       "joint_BH_plus_CI_positive_pct":f"{100*fdr_joint/18:.2f}",
       "interpretation":"original_mechanism_level_crossed_seed_conditional_exploratory_BH",
    })
assert len(summary)==48
write_csv("Q2_F3_COMPLETE_48_FAMILY_ENGINE_REFERENCE_SUMMARY.csv",summary)

by_method_ref=defaultdict(list)
for r in detailed:
    by_method_ref[(r["engine"],r["reference"])].append(r)
engines=[]
for (engine,ref),rows in sorted(by_method_ref.items()):
    tally=Counter(r["point_estimate_class"] for r in rows)
    engines.append({
      "engine":engine,"reference":ref,"mechanism_panels":len(rows),
      "joint_point":tally["joint"],"MSE_only_point":tally["MSE-only"],
      "Q95_only_point":tally["Q95-only"],"neither_point":tally["neither"],
      "joint_conditional_CI":sum(r["conditional_CI_class"]=="joint" for r in rows),
      "joint_exploratory_BH_CI":sum(r["exploratory_BH_plus_CI_class"]=="joint" for r in rows),
      "MSE_BH_CI":sum(r["MSE_BH_and_CI_positive"] for r in rows),
      "Q95_BH_CI":sum(r["Q95_BH_and_CI_positive"] for r in rows),
    })
write_csv("Q2_F3_COMPLETE_8_ENGINE_REFERENCE_EVIDENCE.csv",engines)

audit={
    "schema":"PUB1_Q2_F3_COMPREHENSIVE_TOURNAMENT_CI_BH_V1",
    "status":"PASS_REUSE_COMPLETE_ORIGINAL_Q2_MECHANISM_INFERENCE",
    "source_run":44622921203,
    "source_SHA256":INFILES,
    "complete_paired_metric_rows":len(raw),
    "complete_joint_mechanism_panels":len(detailed),
    "family_engine_reference_summary_rows":len(summary),
    "engine_reference_summary_rows":len(engines),
    "independent_training_seed_axis":10,
    "independent_heldout_seed_axis":10,
    "fixed_observed_scenarios_per_mechanism":40,
    "original_mechanism_inferential_unit":"10_crossed_training_by_10_heldout_seeds_conditional_on_40_original_scenarios",
    "full_BH_family_per_metric":864,
    "MSE_Q95_objectives":"lower_synthetic_loss_is_better; positive_gain_pct_favors_candidate",
    "point_estimate_class_logic":"MSE>0,Q95>0 => joint; only one positive => corresponding only; neither => neither",
    "favorable_CI_logic":"lower_effect_95CI_bound_strictly_greater_than_zero",
    "exploratory_BH_CI_logic":"favorable_95CI_and_original_BH_q_at_most_0.05",
    "full_selection_aware_calibration":"UNVERIFIED",
    "surrogate_null_rejection_at_nominal_5_pct":"5.3223%",
    "cross_stage_exact_frozen_weight_RDS_SHA_matching":"NOT_PROVED_BY_THIS_OUTPUT",
    "distinct_original_single_candidate_rank_rows":1440,
    "individual_candidate_inference_intervals_available":"NO; do not reassign engine_mechanism_intervals_to_individual_weight",
    "new_optimizer_training":False,"new_statistical_inference":False,"new_BH_multiplicity_correction":False,
    "new_contamination_scenarios":False,
    "source_claim_reconciliation":"Matched original flags for all 864 units and original 8-row BH summary",
}
audit_path=OUTPUT/"Q2_F3_COMPLETE_COMPETITION_CI_BH_AUDIT.json"
audit_path.write_text(json.dumps(audit,sort_keys=True,indent=2)+"\n",encoding="utf-8")
files=[OUTPUT/x for x in (
    "Q2_F3_COMPLETE_864_TOURNAMENT_CI_BH_EVIDENCE.csv",
    "Q2_F3_COMPLETE_48_FAMILY_ENGINE_REFERENCE_SUMMARY.csv",
    "Q2_F3_COMPLETE_8_ENGINE_REFERENCE_EVIDENCE.csv",
    "Q2_F3_COMPLETE_COMPETITION_CI_BH_AUDIT.json"
)]
manifest={p.name:{"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in files}
(OUTPUT/"Q2_F3_COMPLETE_COMPETITION_CI_BH_SHA256_MANIFEST.json").write_text(
    json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({
    "status":audit["status"],
    "full_mechanism_rows":len(detailed),
    "main_table_rows":len(summary),
    "engines":engines,
    "manifest":manifest,
},indent=2))
