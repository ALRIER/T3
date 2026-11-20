#!/usr/bin/env python3
"""Exact-science compact Q3-D completeness gate: 540 × 49 selected scenario
shards, six scored models (four original engines, classical, mean), ten seeds.
"""
from __future__ import annotations
import argparse,csv,hashlib
from collections import defaultdict
from pathlib import Path
from q3_lite_plan import identities,grid

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    ap.add_argument("--sample-n",type=int)
    args=ap.parse_args()
    source=args.root
    ids=set(grid()[0]);expected=set(identities())
    if args.sample_n is not None:
        if args.sample_n not in (200,1000,3000):raise SystemExit("Unknown compact sample size")
        expected={k for k in expected if k[3]==args.sample_n}
    found={};receipts=[]
    for manifest in source.rglob("score_manifest.csv"):
        with manifest.open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
        if len(rows)!=1:raise SystemExit("Score manifest must contain exactly one record")
        r=rows[0];key=(r["family"],int(r["parameter_row"]),int(r["seed"]),int(r["n"]))
        if key not in expected or key in found:
            raise SystemExit("Unknown or duplicate Q3 compact parameter score "+str(key))
        score=manifest.with_name("scores.csv")
        if not score.is_file() or digest(score)!=r["scores_sha256"]:
            raise SystemExit("Q3 compact score SHA mismatch "+str(manifest))
        if (r.get("protocol")!="t3_q3_compact_parametric_score_v1" or
           int(r["scenario_count"])!=49 or int(r["scenario_block"])!=0 or
           int(r["scenario_block_count"])!=1 or int(r["training_seed_count"])!=10):
            raise SystemExit("Q3 compact sampling and frozen-weight contract failure")
        actual={int(x) for x in r["scenario_ids"].split(";") if x}
        if actual!=ids:raise SystemExit("Science scenario selection mismatch")
        with score.open(newline="",encoding="utf-8") as f:
            records=list(csv.DictReader(f))
        if len(records)!=49*6 or {int(x["scenario_id"]) for x in records}!=ids:
            raise SystemExit("Original complete model×scenario score support absent")
        for x in records:
            if (x["family"]!=key[0] or int(x["sample_n"])!=key[3] or
                int(x["parameter_row"])!=key[1] or int(x["parametric_seed"])!=key[2]):
                raise SystemExit("Mixed source-evaluation identity in Q3 compact scores")
        found[key]=manifest
        receipts.append({"family":key[0],"parameter_row":key[1],"seed":key[2],"n":key[3],
            "score_sha256":digest(score),"manifest_sha256":digest(manifest),
            "path":str(manifest.relative_to(source)),
            "recovered_from_original":bool(r.get("source_actions_run_id"))})
    if set(found)!=expected:
        missing=sorted(expected-set(found));extra=sorted(set(found)-expected)
        raise SystemExit(f"Incomplete Q3 compact score panel: {len(found)}/{len(expected)} missing={missing[:8]} extra={extra[:8]}")
    out=source/"q3_compact_coverage.csv"
    with out.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(receipts[0]),lineterminator="\n")
        w.writeheader();w.writerows(sorted(receipts,key=lambda r:(r["family"],r["parameter_row"],r["seed"],r["n"])))
    print("Q3_COMPACT_COVERAGE_PASS",len(found),"shards",49,"scenarios/shard",
          sum(r["recovered_from_original"] for r in receipts),"reuse_from_original")

if __name__=="__main__":main()
