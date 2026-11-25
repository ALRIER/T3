#!/usr/bin/env python3
"""Reviewer point 6: Q95 reliability from immutable ORIGINAL R1 results only.
No Monte Carlo generation, model training, new bootstrap, HPO or selection.
Independent order-statistic precision is NOT a confidence interval for a paired gain.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = {
    "precision_108": "R1/runs/44322411124/reviewer_synthesis/q95_mc_uncertainty_all_108_method_strata.csv",
    "blocks_72": "R1/runs/44324757704/synthesis/table_RQ1_72_method_family_sample_integrated.csv",
    "control_288": "R1/runs/44322411124/reviewer_synthesis/deterministic_controls_original_heldout_global_holm.csv",
    "method_216": "R1/runs/44344323290/synthesis/Q1_STAGE12_FINAL_original_216_frozen_contrasts_calibrated.csv",
}
FAMS = ("normal", "lognormal", "weibull", "invgauss", "exgaussian", "exwald")
SIZES = (200, 1000, 3000)
METHODS = ("ga", "nsga2", "de", "dirichlet")
ALL_METHODS = METHODS + ("convex_mse", "local_deterministic")

def require(ok, msg):
    if not ok:
        raise ValueError(msg)

def rows(file):
    with file.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))

def num(v):
    x = float(v)
    require(x == x and abs(x) < float("inf"), "nonfinite numeric input")
    return x

def positive(v):
    return str(v).strip().lower() in ("true", "1", "yes")

def put_csv(out, name, records):
    require(records, "no records for " + name)
    cols = list(records[0])
    require(all(set(r) == set(cols) for r in records), "inconsistent fields " + name)
    with (out/name).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        writer.writerows(records)

def main(out):
    data = {k:rows(ROOT/p) for k,p in SRC.items()}
    require([len(data[k]) for k in SRC] == [108,72,288,216],
            "immutable source cardinalities unexpected: " + repr({k:len(v) for k,v in data.items()}))
    pr = {(r["family"],int(r["sample_n"]),r["method"]):r for r in data["precision_108"]}
    bl = {(r["family"],int(r["sample_n"]),r["method"]):r for r in data["blocks_72"]}
    ctrl = {(r["family"],int(r["sample_n"]),r["candidate"],r["control"],r["metric"]):
            r for r in data["control_288"]}
    mp = {(r["family"],int(r["sample_n"]),r["method_a"],r["method_b"],r["metric"]):
          r for r in data["method_216"]}
    require(len(pr)==108 and len(bl)==72 and len(ctrl)==288 and len(mp)==216, "duplicate input keys")
    require(set(pr)=={(f,n,m) for f in FAMS for n in SIZES for m in ALL_METHODS},
            "precision strata mismatch")
    require(set(bl)=={(f,n,m) for f in FAMS for n in SIZES for m in METHODS},
            "original integrated strata mismatch")
    out.mkdir(parents=True,exist_ok=False)
    blocks=[]
    for f in FAMS:
        for n in SIZES:
            de=bl[f,n,"de"]
            q=num(de["q95_heldout"])
            c=ctrl[f,n,"de","convex_mse","q95"]
            mse=ctrl[f,n,"de","convex_mse","mse"]
            qdiff=num(c["difference_candidate_minus_control"])
            qgain=num(c["relative_improvement_pct"])
            c95low,c95high=num(c["confidence95_lower"]),num(c["confidence95_upper"])
            prec=pr[f,n,"de"];ref=pr[f,n,"convex_mse"]
            require(abs(qgain-num(de["convex_mse_q95_relative_gain_pct"]))<1e-5,
                    "DE Q95 source crosscheck failed "+f+str(n))
            require(abs(qdiff-(q-num(ref["average_q95_interval_width"])*0+qdiff))<1e-8,
                    "numeric check")
            row={
                "family":f,"sample_n":n,
                "DE_Q95_heldout":q,"DE_vs_convex_Q95_gain_pct":qgain,
                "DE_vs_convex_MSE_gain_pct":num(mse["relative_improvement_pct"]),
                "DE_vs_convex_Q95_difference":qdiff,
                "original_paired_Q95_CI95_low":c95low,
                "original_paired_Q95_CI95_high":c95high,
                "original_conditional_CI_excludes_zero": c95high<0 or c95low>0,
                "original_288_panel_Holm_p":num(c["holm_p_global_288"]),
                "original_288_panel_Holm_supported":num(c["holm_p_global_288"])<=0.05,
                "original_Q95_evaluation_seeds_favor_DE":int(c["independent_seed_favor_candidate"]),
                "DE_MC_Q95_relative_interval_width_pct":100*num(prec["average_q95_interval_relative_width"]),
                "convex_MC_Q95_relative_interval_width_pct":100*num(ref["average_q95_interval_relative_width"]),
                "DE_scenario_fraction_MC_width_gt20pct":num(prec["frac_scenarios_mc_q95_width_gt20"]),
                "DE_Q95_gain_magnitude_lt5pct":abs(qgain)<5,
                "DE_Q95_positive_gain_lt5pct":0<qgain<5,
                "dual_descriptive_gain_vs_convex":qgain>0 and num(mse["relative_improvement_pct"])>0,
                "scope":"Q95 MC order-statistic uncertainty and original paired CI are DIFFERENT estimands; no full selection-aware guarantee"
            }
            blocks.append(row)
    pairs=[]
    for (f,n,a,b,metric),r in sorted(mp.items()):
        if metric!="q95":
            continue
        qa=num(bl[f,n,a]["q95_heldout"])
        qb=num(bl[f,n,b]["q95_heldout"])
        diff=num(r["original_crossed_mean_difference"])
        # Symmetric percentage is a descriptive scale only, NOT an interval.
        pct=100*abs(diff)/((qa+qb)/2)
        lo,hi=num(r["calibrated_pointwise_CI95_low"]),num(r["calibrated_pointwise_CI95_high"])
        sl,sh=num(r["calibrated_simultaneous_216_CI95_low"]),num(r["calibrated_simultaneous_216_CI95_high"])
        pairs.append({
            "family":f,"sample_n":n,"method_a":a,"method_b":b,
            "Q95_original_crossed_difference_a_minus_b":diff,
            "Q95_symmetric_relative_absolute_effect_pct":pct,
            "smaller_than_5pct_symmetric_effect":pct<5,
            "surrogate_conditional_pointwise_CI95_low":lo,
            "surrogate_conditional_pointwise_CI95_high":hi,
            "surrogate_pointwise_CI_excludes_zero":lo>0 or hi<0,
            "surrogate_simultaneous_216_CI95_low":sl,
            "surrogate_simultaneous_216_CI95_high":sh,
            "surrogate_simultaneous_216_CI_excludes_zero":sl>0 or sh<0,
            "surrogate_minP_flag":positive(r["posthoc_empirical_global_minP_support"]),
            "a_MC_Q95_relative_width_pct":100*num(pr[f,n,a]["average_q95_interval_relative_width"]),
            "b_MC_Q95_relative_width_pct":100*num(pr[f,n,b]["average_q95_interval_relative_width"]),
            "scope":"posthoc crossed-effect surrogate conditional, not original optimizer-selection calibration"
        })
    require(len(blocks)==18 and len(pairs)==108, "output count invalid")
    flagged = [r for r in blocks if r["DE_Q95_positive_gain_lt5pct"]]
    pctsmall = [r for r in pairs if r["smaller_than_5pct_symmetric_effect"]]
    group = {}
    for name, rr in (("smaller_than_5pct",pctsmall),("at_least_5pct",[r for r in pairs if not r["smaller_than_5pct_symmetric_effect"]])):
        group[name]={
            "pairs":len(rr),
            "surrogate_pointwise_CI_excludes_zero":sum(r["surrogate_pointwise_CI_excludes_zero"] for r in rr),
            "surrogate_simultaneous_216_CI_excludes_zero":sum(r["surrogate_simultaneous_216_CI_excludes_zero"] for r in rr),
            "surrogate_minP_flags":sum(r["surrogate_minP_flag"] for r in rr)
        }
    summary={
        "status":"PASS_ORIGINAL_ONLY_Q95_REVIEWER_REANALYSIS",
        "original_monte_carlo_runs":0,"optimizer_refits":0,"new_null_simulations":0,
        "n_original_mc_replicates_per_scenario":500,
        "independent_original_heldout_eval_seeds":10,
        "q95_precision_strata":108,
        "DE_vs_convex_blocks":18,
        "method_pair_q95_contrasts":108,
        "DE_dual_descriptive_gains_vs_convex":sum(r["dual_descriptive_gain_vs_convex"] for r in blocks),
        "DE_Q95_positive_gain_below_5pct":len(flagged),
        "DE_Q95_gain_below_5pct_identifiers":[r["family"]+"/n"+str(r["sample_n"]) for r in flagged],
        "DE_original_conditional_Q95_CI_excludes_zero":sum(r["original_conditional_CI_excludes_zero"] for r in blocks),
        "DE_original_288_panel_Holm_supported":sum(r["original_288_panel_Holm_supported"] for r in blocks),
        "method_pair_effect_size_groups":group,
        "scope":"Q95 order-statistic 95pct interval widths quantify within-Monte-Carlo tail-loss precision, NOT the paired gain uncertainty; original t9/Holm and corrected crossed-effect surrogate are not full end-to-end selection-aware guarantees"
    }
    put_csv(out,"Q95_DE_18_BLOCK_ORIGINAL_PRECISION_AND_PAIRED_EFFECTS.csv",blocks)
    put_csv(out,"Q95_108_METHOD_PAIRS_SURROGATE_CONDITIONAL_PRECISION.csv",pairs)
    (out/"Q95_REVIEWER_SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    sources={name:{"path":p,"sha256":hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),"rows":len(data[name])} for name,p in SRC.items()}
    (out/"INPUT_SHA256_MANIFEST.json").write_text(json.dumps(sources,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    lines=[
        "# Q95 reviewer evidence: original 500-replicate precision vs conditional between-method uncertainty",
        "",
        "**Source:** original T3/R1 verified archives only. No new Monte Carlo, bootstrap, optimizer, or HPO runs.",
        "",
        "The per-scenario type-8 Q95 estimate is based on 500 original MC replicate errors. Its order-statistic interval width is a *within-MC loss-quantile precision diagnostic*, not a confidence interval for the paired DE-versus-control gain or any other between-method contrast.",
        "",
        "In the 18 original family-size blocks, DE has "+str(summary["DE_dual_descriptive_gains_vs_convex"])+
        " descriptive MSE-and-Q95 improvements over the frozen convex-MSE control. "+str(len(flagged))+
        " DE Q95 improvements are positive but smaller than 5%.",
        "",
        "The original paired-control intervals and Holm labels have not been recalibrated for full optimizer selection. The 108 matched method-pair Q95 contrasts are separately examined against the existing **post hoc fixed-score surrogate** pointwise and simultaneous CI bounds, with a descriptive <5% effect-size split.",
        "",
        "### Descriptive Q95 method-pair comparison",
        "",
        "| Magnitude of symmetric original Q95 contrast | Contrasts | Surrogate pointwise 95% CI excludes 0 | Surrogate simultaneous 216-contrast 95% CI excludes 0 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name,label in (("smaller_than_5pct","<5%"),("at_least_5pct",">=5%")):
        z=group[name]
        lines.append("| "+label+" | "+str(z["pairs"])+" | "+str(z["surrogate_pointwise_CI_excludes_zero"])+" | "+str(z["surrogate_simultaneous_216_CI_excludes_zero"])+" |")
    lines+=["","### Interpretation constraints","","1. A small descriptive block gain can coexist with broad scenario-level Q95 quantile uncertainty. Their percentage scales have different denominators and **are not** interchangeable inferential intervals.","2. The original control CI uses ten independent evaluation seeds. It must be labeled *original conditional paired inference*, not fully calibrated selection-aware inference.","3. The fixed-score surrogate calibration applies only to archived frozen method scores, not the original nested optimizer/HPO weight selection. It cannot be transferred to control or Q2--Q4 panels.","4. No new results justify a new claim of confirmatory optimizer superiority or a prospective universal weight selector.","","### Reproducibility","","Input hashes, all 18 DE-versus-convex original CI comparisons, and the complete 108 crossed method-pair Q95 results are published alongside this summary.",""]
    (out/"Q95_REVIEWER_MANUSCRIPT_FINDINGS.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps(summary,sort_keys=True))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    main(Path(args.out))
