#!/usr/bin/env python3
"""Fetch the archived public-data pool and build a fresh T3 parent catalog.

The 664 archived source vectors are used as a candidate pool only. T3 will
re-profile them and freeze a new parent sample using the T3 Discovery grid.
The Zenodo CC-BY assertion applies to the archived package; upstream rights
metadata are retained separately and are not represented as independently
cleared by this script.
"""
import argparse, csv, hashlib, io, json, tarfile, urllib.request
from pathlib import Path, PurePosixPath

ZENODO = "https://zenodo.org/api/records/23602795"
ARCHIVE_KEY = "T2_rw2_external_catalog_664.tar"
PARENTS_KEY = "realworld_v2_664_parent_manifest.csv"
CCBY = "https://creativecommons.org/licenses/by/4.0/"

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"T3-realworld-catalog/1.0"})
    with urllib.request.urlopen(req,timeout=90) as r: return r.read()
def sha(data): return hashlib.sha256(data).hexdigest()
def md5(data): return hashlib.md5(data).hexdigest()
def safe_extract_rds(blob, out):
    out.mkdir(parents=True,exist_ok=True)
    paths={}
    with tarfile.open(fileobj=io.BytesIO(blob),mode="r:*") as tf:
        for m in tf.getmembers():
            p=PurePosixPath(m.name)
            if not m.isfile() or p.suffix.lower()!=".rds" or "raw" not in p.parts: continue
            if p.is_absolute() or ".." in p.parts: raise ValueError("Unsafe archive member path")
            dest=out/p.name
            if dest.exists(): raise ValueError(f"Duplicate archived child filename: {p.name}")
            src=tf.extractfile(m)
            if src is None: raise ValueError(f"Cannot read archive member: {m.name}")
            data=src.read();dest.write_bytes(data);paths[p.stem]=dest
    return paths

p=argparse.ArgumentParser()
p.add_argument("--out",type=Path,default=Path("artifacts/T3_B3_realworld_catalog"))
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
record_blob=fetch(ZENODO);record=json.loads(record_blob)
a.out.joinpath("zenodo_record_metadata.json").write_bytes(record_blob)
metadata=record.get("metadata",{})
license_id=(metadata.get("license") or {}).get("id","").lower()
if license_id!="cc-by-4.0": raise SystemExit(f"Archive license changed; expected cc-by-4.0, got {license_id!r}")
files={x["key"]:x for x in record.get("files",[])}
if ARCHIVE_KEY not in files or PARENTS_KEY not in files: raise SystemExit("Required Zenodo archive files missing")
archive=fetch(files[ARCHIVE_KEY]["links"].get("content") or files[ARCHIVE_KEY]["links"]["self"])
with open("config/realworld_v2_zenodo.csv",newline="",encoding="utf-8-sig") as f:
    source_record=next(csv.DictReader(f))
expected=source_record["archive_sha256"].strip().lower()
if not expected or sha(archive)!=expected: raise SystemExit("Zenodo archive SHA-256 verification failed")
parents_blob=fetch(files[PARENTS_KEY]["links"].get("content") or files[PARENTS_KEY]["links"]["self"])
parents_md5=files[PARENTS_KEY].get("checksum","").removeprefix("md5:")
if not parents_md5 or md5(parents_blob)!=parents_md5: raise SystemExit("Parent manifest MD5 verification failed")
(a.out/ARCHIVE_KEY).write_bytes(archive)
(a.out/PARENTS_KEY).write_bytes(parents_blob)
raw_dir=a.out/"raw_archive_vectors";vector_paths=safe_extract_rds(archive,raw_dir)
rows=list(csv.DictReader(io.StringIO(parents_blob.decode("utf-8-sig"))))
rows=[r for r in rows if str(r.get("load_ok","")).lower()=="true"]
if len(rows)!=664 or len({r["parent_dataset_id"] for r in rows})!=664:
    raise SystemExit(f"Expected 664 valid independent parents, found {len(rows)}")
out=[]
for r in rows:
    did=r["dataset_id"]
    if did not in vector_paths: raise SystemExit(f"Archived vector absent for {did}")
    original_url=(r.get("source_url","") or "").lower()
    # UCI is recollected from its own API; omit old UCI copies to avoid counting
    # the same underlying parent once from each source inventory.
    if "uci.edu" in original_url or did.lower().startswith("uci_"):
        continue
    finance=r.get("domain")=="financial_macro_series"
    out.append({
      "dataset_id":did,"parent_dataset_id":r["parent_dataset_id"],
      "source_path":str(vector_paths[did].resolve()),
      "source_url":r.get("source_url","") or f"https://zenodo.org/records/23602795",
      "domain":r.get("domain",""),"source_sector":"finance" if finance else "other",
      "source_group":"archived_public_catalog",
      "variable":"__archived_numeric_vector__","transform":"raw",
      "child_selection_rule":"one archived numeric child per independent parent",
      "license_name":"CC-BY-4.0 (Zenodo archived candidate package)",
      "license_basis":"Zenodo_archive_record_CC-BY-4.0",
      "license_url":CCBY,"license_review_status":"verified",
      "upstream_license_status":"not_independently_reviewed",
      "upstream_source_url":r.get("source_url",""),
      "source_archive_doi":"10.5281/zenodo.23602795",
      "license_evidence":"Zenodo record metadata declares cc-by-4.0 for the archived package",
      "license_evidence_sha256":sha(record_blob),
      "license_evidence_path":str((a.out/"zenodo_record_metadata.json").resolve()),
    })
catalog=a.out/"candidate_catalog.csv"
with catalog.open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
summary={"candidate_parents":len(out),"source_archive_valid_parents":len(rows),
 "excluded_old_uci_duplicates":len(rows)-len(out),
 "finance_parents":sum(x["source_sector"]=="finance" for x in out),
 "other_parents":sum(x["source_sector"]!="finance" for x in out),
 "archive_doi":"10.5281/zenodo.23602795","archive_sha256":sha(archive),
 "parent_manifest_sha256":sha(parents_blob),"catalog_sha256":sha(catalog.read_bytes()),
 "archive_license":license_id,"upstream_license_policy":"not_independently_reviewed; original source URLs retained",
 "sampling":"candidate pool only; fresh T3 outcome-blind profile and parent freeze follows"}
(a.out/"candidate_catalog_manifest.json").write_text(json.dumps(summary,indent=2)+"\n")
print("T3_B3_REALWORLD_CANDIDATE_CATALOG_PASS",json.dumps(summary,sort_keys=True))
