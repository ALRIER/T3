#!/usr/bin/env python3
"""Aggregate independent pinned-container R1 reviewer checks; fail closed."""
import csv, hashlib, json, pathlib, sys
FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
RUN_R1="44310024979"
PRIMARY="44307352615"
def read(p):
    with pathlib.Path(p).open(newline="") as f:return list(csv.DictReader(f))
def num(x):return float(x)
def holm(ps):
    order=sorted(range(len(ps)),key=lambda i:ps[i])
    result=[0.]*len(ps);prev=0.
    for rank,i in enumerate(order):
        prev=max(prev,min(1.,ps[i]*(len(ps)-rank)))
        result[i]=prev
    return result
def main():
    root=pathlib.Path(sys.argv[1])
    inputs=[];allrows=[]
    for f in FAMILIES:
        p=root/"reviewer"/f/"independent_r_paired_reaudit.csv"
        if not p.exists():raise RuntimeError("Missing independent reviewer audit: "+str(p))
        rows=read(p)
        if len(rows)!=36 or {r["family"] for r in rows}!={f}:raise RuntimeError("Bad reviewer family coverage")
        allrows.extend(rows);inputs.append(p)
    if len(allrows)!=216:raise RuntimeError("Expected 216 independently re-audited contrasts")
    keys=["family","sample_n","method_a","method_b","metric"]
    hashes={tuple(r[k] for k in keys) for r in allrows}
    if len(hashes)!=216:raise RuntimeError("Repeated R1 test key")
    originals=read("R1/runs/"+PRIMARY+"/all_pairwise_global_holm.csv")
    if len(originals)!=216:raise RuntimeError("Original R1 hypothesis panel incomplete")
    primary={tuple(r[k] for k in keys):r for r in originals}
    if set(primary)!=hashes:raise RuntimeError("Hypothesis families or keys changed")
    expected_holm=holm([num(r["p_paired_t"]) for r in allrows])
    expected_signflip_holm=holm([num(r["p_signflip_exact"]) for r in allrows])
    for i,r in enumerate(allrows):
        src=primary[tuple(r[k] for k in keys)]
        for name,got,expected in [
          ("original Holm",num(r["original_holm_global"]),num(src["holm_p_global"])),
          ("computed Holm",num(r["original_holm_global"]),expected_holm[i]),
          ("sign-flip Holm",num(r["reviewer_holm_global"]),expected_signflip_holm[i])]:
            if abs(got-expected)>1e-8:
                raise RuntimeError(name+" mismatch: "+repr(tuple(r[k] for k in keys)))
    ranking=read("R1/runs/"+RUN_R1+"/synthesis/ranking_preservation.csv")
    if len(ranking)!=360:raise RuntimeError("Expected complete 6 x 3 x 10 x 2 ranking preservation")
    frontier=read("R1/runs/"+RUN_R1+"/synthesis/mse_q95_pareto_tradeoff.csv")
    if len(frontier)!=72:raise RuntimeError("Expected 18 x 4 Pareto method blocks")
    budget=read("R1/runs/"+RUN_R1+"/synthesis/compute_budget_vs_independent_improvement.csv")
    if len(budget)!=720:raise RuntimeError("Expected all 720 frozen optimizer identities")
    import collections
    original_sig=sum(num(r["original_holm_global"])<=.05 for r in allrows)
    signflip_sig=sum(num(r["reviewer_holm_global"])<=.05 for r in allrows)
    families_summary=[]
    for f in FAMILIES:
        subset=[r for r in allrows if r["family"]==f]
        families_summary.append(dict(family=f,contrasts=len(subset),
          paired_t_global_holm_supported=sum(num(r["original_holm_global"])<=.05 for r in subset),
          exact_signflip_global_holm_supported=sum(num(r["reviewer_holm_global"])<=.05 for r in subset),
          lower_mse_method_a=sum(r["metric"]=="mse" and num(r["difference"])<0 for r in subset)))
    out=root/"scientific_gate";out.mkdir(parents=True,exist_ok=True)
    with (out/"family_reviewer_evidence.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(families_summary[0]));w.writeheader();w.writerows(families_summary)
    report=[
      "# R1 reviewer replication and inference audit",
      "",
      f"Reference Held Out run: {PRIMARY}. Full Discovery/Held Out synthesis: {RUN_R1}.",
      "",
      f"- Independent R reconstructions: **216/216** pairwise optimizer/metric/stratum contrasts.",
      "- The paired contrasts use 10 independent Held Out evaluation seeds; correlated training-seed candidate results are averaged within seed.",
      f"- Original globally Holm-corrected paired t comparisons at 0.05: **{original_sig}/216**.",
      f"- Exact sign-flip sensitivity contrasts after global Holm at 0.05: **{signflip_sig}/216**.",
      "- These are different inferential approaches; an apparent discrepancy is a sensitivity finding, not permission to ignore either.",
      "- Original 720 candidates and 360 Discovery-to-Held Out ranking cells were checked for complete coverage.",
      "- The independent exact sign-flip test has discrete resolution with only ten seeds; Holm across 216 comparisons is conservative.",
      "- Neither test is a complete selection-aware null replay, a proof of optimizer superiority across every regime, or independent validation of deterministic controls.",
      "- No Monte Carlo, Discovery training, or Held Out scoring was rerun.",
      "",
      "Execution: canonical pinned T3 R container from config/T3_DEFAULT_ANALYSIS_RUNTIME.env.",
      "Input provenance is linked by the immutable run IDs above.",
    ]
    (out/"README_R1_REVIEWER_GATE.md").write_text("\n".join(report)+"\n")
    hashes_manifest={}
    for p in inputs+[out/"family_reviewer_evidence.csv",out/"README_R1_REVIEWER_GATE.md"]:
        hashes_manifest[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
    manifest={"status":"pass","input_original_r1":PRIMARY,
      "input_discovery_heldout_synthesis":RUN_R1,
      "original_comparisons":216,"independent_r_reaudited":216,
      "globally_holm_supported_original":original_sig,
      "globally_holm_supported_exact_signflip_sensitivity":signflip_sig,
      "repeated_original_training":False,"repeated_heldout_scoring":False,
      "source_hashes":hashes_manifest}
    (out/"SCIENTIFIC_GATE_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("R1_REVIEWER_SCIENTIFIC_GATE_PASS",original_sig,signflip_sig,len(allrows))
if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("Usage: python scripts/t3_b3_r1_audit_finalize.py OUTPUT_DIR")
    main()
