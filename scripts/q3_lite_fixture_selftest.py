#!/usr/bin/env python3
"""Dry-run all Q3-D/F/G aggregation and plotting paths on synthetic, disposable fixtures.

This script MUST NEVER publish its 249 synthetic panels or claim original
parameter-transfer evidence. It tests schema, coverage, artifact generation,
CI/BH tier reconciliation, and publication-manifest logic only.
"""
from __future__ import annotations
import csv,gzip,importlib.util,json,tempfile
from itertools import product
from pathlib import Path

SOURCE=Path(__file__).resolve().with_name("q3_lite_complete_science.py")
spec=importlib.util.spec_from_file_location("q3_complete_science",SOURCE)
science=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(science)
with tempfile.TemporaryDirectory(prefix="q3_disposable_fixture_") as tmp:
    tmp=Path(tmp)
    science.BASE=tmp/"Q3"
    science.baseline("SYNTHETIC_FIXTURE_NEVER_PUBLISH")
    root=tmp/"mock_original_parameter_output"
    out=root/"aggregate/taxonomy_by_panel"
    out.mkdir(parents=True)
    req=["family","parameter_row","sample_n","candidate_engine",
         "benchmark_role","difference.mse","difference.q95","ci_upper.mse",
         "ci_upper.q95","q_value_global.mse","q_value_global.q95",
         "tier1_joint_mse_q95_bh_fdr","gain_pct.mse","gain_pct.q95"]
    count=0
    for fam,last in science.__dict__.get("FAMILIES",{
         "normal":8,"lognormal":6,"weibull":12,"invgauss":9,
         "exgaussian":27,"exwald":27}).items():
        for param,n in product(sorted(set((2,(2+last)//2,last))),(200,1000,3000)):
            records=[]
            for engine,policy in product(science.ENGINES,("own","mean")):
                records.append({"family":fam,"parameter_row":param,"sample_n":n,
                    "candidate_engine":engine,"benchmark_role":policy,
                    "difference.mse":-1.0,"difference.q95":-1.2,
                    "ci_upper.mse":-0.1,"ci_upper.q95":-0.2,
                    "q_value_global.mse":.004,"q_value_global.q95":.005,
                    "tier1_joint_mse_q95_bh_fdr":"TRUE",
                    "gain_pct.mse":12.0,"gain_pct.q95":13.5})
            path=out/f"{fam}_parameter{param}_n{n}.csv.gz"
            with gzip.open(path,"wt",newline="") as f:
                w=csv.DictWriter(f,fieldnames=req,lineterminator="\n")
                w.writeheader();w.writerows(records)
            count+=1
    assert count==54
    science.summarize_parametric(root)
    science.finalize("SYNTHETIC_FIXTURE_NEVER_PUBLISH")
    audit=json.loads((science.BASE/"G_publication_audit/Q3_G_COMPLETE_MANIFEST.json").read_text())
    assert audit["status"]=="COMPLETE_SCIENTIFIC_ANALYSIS_A_TO_G_PASS"
    assert len(list((science.BASE/"F_synthesis").glob("*.png")))==3
    assert len(science.rows(science.BASE/"D_parameter_transfer/Q3_D_144_FAMILY_N_ENGINE_REFERENCE.csv"))==144
    assert len(science.rows(science.BASE/"D_parameter_transfer/Q3_D_432_PARAMETER_ROW_N_ENGINE_REFERENCE.csv"))==432
print("Q3_COMPACT_SYNTHETIC_FIXTURE_54_PANEL_F_G_PLOTTING_VALIDATION_PASS; NO REAL ANALYSIS WAS RUN")
