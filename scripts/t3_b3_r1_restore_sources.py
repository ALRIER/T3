#!/usr/bin/env python3
"""Restore only verified immutable T3 source artifacts from repository Git LFS.

All bytes and Git LFS chunk digests are checked against the original archive manifest.
Read-only source recovery: never triggers Monte Carlo generation or optimizer fitting.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
MC_RUN=40239277660
SCORES_RUN=41208513291

def die(s):raise RuntimeError(s)
def sha(data):return hashlib.sha256(data).hexdigest()
def folder(stage,globexpr):
    p=Path("data-archive")/stage/"actions"
    matches=list(p.glob(globexpr))
    if len(matches)!=1:die(f"Expected exactly one archived {stage} source for {globexpr}; got {len(matches)}")
    return matches[0]
def restored_blob(directory):
    meta=json.loads((directory/"manifest.json").read_text())
    if meta.get("complete") is not True or meta.get("schema_version")!=1:die("Unverified original source: "+str(directory))
    raw=[]
    for spec in meta["parts"]:
        p=directory/spec["name"]
        b=p.read_bytes()
        if len(b)!=spec["bytes"] or sha(b)!=spec["sha256"]:die("Source LFS hash mismatch: "+str(p))
        raw.append(b)
    blob=b"".join(raw)
    if len(blob)!=meta["size_bytes"] or sha(blob)!=meta["sha256"]:die("Archived source envelope hash mismatch")
    return blob,meta
def select_entries(z,kind):
    names=[p for p in z.namelist() if not p.endswith("/")]
    if kind=="controls":
        matches=[p for p in names if p.endswith("non_evolutionary_control_scores.csv")]
        if len(matches)!=1:die("Original Held Out source is missing the separately scored deterministic controls: "+str(matches))
    elif kind=="mc":
        matches=[p for p in names if p.endswith("/canonical.rds") or p=="canonical.rds"]
        if len(matches)!=1:
            scenarios=[p for p in names if re.search(r"scenario_\d{4}[.]rds$",p)]
            if len(scenarios)!=321:die("Neither one canonical.rds nor 321 original scenario matrices in MC ZIP")
            matches=scenarios
    else:die("Unsupported archive entry type")
    return matches
def restore(kind,family,n,seed,out):
    if family not in FAMILIES or n not in (200,1000,3000) or seed not in range(10,20):
        die("Invalid immutable source identity")
    if kind=="mc":
        src=folder("montecarlo",f"actions-*_b3-mc-heldout-{family}-s{seed}-n{n}-run{MC_RUN}.zip")
    else:
        src=folder("heldout",f"actions-*_t3-b3-heldout-{family}-s{seed}-n{n}-run{SCORES_RUN}.zip")
    blob,meta=restored_blob(src)
    if int(meta["source"]["run_id"])!=(MC_RUN if kind=="mc" else SCORES_RUN):
        die("Source metadata points to wrong original scientific run")
    out.mkdir(parents=True,exist_ok=True)
    paths=[]
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in select_entries(z,kind):
            destination=out/Path(name).name
            if destination.exists():die("Refusing overwrite of source "+str(destination))
            with z.open(name) as r,destination.open("wb") as w:
                while True:
                    block=r.read(1048576)
                    if not block:break
                    w.write(block)
            if destination.stat().st_size<200:die("Empty recovered source file "+str(destination))
            paths.append(dict(name=destination.name,bytes=destination.stat().st_size,sha256=sha(destination.read_bytes())))
    lineage=dict(kind=kind,source_run=meta["source"]["run_id"],family=family,sample_n=n,
                 evaluation_seed=seed,archive=str(src),archive_sha256=meta["sha256"],files=paths)
    (out/"SOURCE_LINEAGE.json").write_text(json.dumps(lineage,indent=2)+"\n")
    print("R1_VERIFIED_SOURCE_RESTORE",kind,family,n,seed,len(paths),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("kind",choices=("controls","mc"))
    p.add_argument("family",choices=FAMILIES)
    p.add_argument("n",type=int,choices=(200,1000,3000))
    p.add_argument("seed",type=int)
    p.add_argument("output",type=Path)
    a=p.parse_args();restore(a.kind,a.family,a.n,a.seed,a.output)
if __name__=="__main__":main()
