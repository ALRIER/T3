#!/usr/bin/env python3
"""Fail closed before launching 39 original source analyses; no simulation."""
import io
import json
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,"scripts")
from t3_b3_r1_restore_sources import folder,restored_blob,select_entries

families=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
sizes=(200,1000,3000)
status=json.loads(Path("data-archive/catalog/status.json").read_text())
assert status["complete"] is True and status["scope"]=="sources in recorded inventory only"
tasks=[]
for f in families:
    for n in sizes:
        for stage,stem,run in (("heldout","t3-b3-heldout",41208513291),
                               ("montecarlo","b3-mc-heldout",40239277660)):
            for s in range(10,20):
                paths=list((Path("data-archive")/stage/"actions").glob(
                    f"actions-*_{stem}-{f}-s{s}-n{n}-run{run}.zip/manifest.json"))
                assert len(paths)==1,("Missing/duplicate",stage,f,s,n)
                m=json.loads(paths[0].read_text())
                assert m["complete"] and m["schema_version"]==1 and m["source"]["run_id"]==run
        for mode in ("controls","q95"):
            tasks.append(dict(mode=mode,family=f,n=n))
for n in sizes:
    paths=list(Path("data-archive/discovery/actions").glob(
      f"actions-*_t3-b3-discovery-bundle-n{n}-run41487091262.zip/manifest.json"))
    assert len(paths)==1,("Missing Discovery bundle",n)
    m=json.loads(paths[0].read_text())
    assert m["complete"] and m["schema_version"]==1 and m["source"]["run_id"]==41487091262
    tasks.append(dict(mode="cost",family="all",n=n))
assert len(tasks)==39
# Two exact source samples are fully reconstructed, hash-checked and inspected.
for kind,stage,name in (
    ("controls","heldout","actions-*_t3-b3-heldout-normal-s10-n200-run41208513291.zip"),
    ("mc","montecarlo","actions-*_b3-mc-heldout-normal-s10-n200-run40239277660.zip")):
    d=folder(stage,name)
    data,meta=restored_blob(d)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        entries=select_entries(z,kind)
    assert entries
    print("R1_ORIGINAL_SOURCE_ZIP_CONTENT_PASS",kind,len(entries),meta["sha256"],flush=True)
Path("/tmp/r1_original_matrix.json").write_text(json.dumps({"include":tasks},separators=(",",":")))
print("R1_ORIGINAL_ARCHIVE_COMPLETE_MATRIX_PASS",len(tasks),flush=True)
