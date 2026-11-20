#!/usr/bin/env python3
"""Inventory original T3 Held Out and Real World family-transfer science archives.

Data are downloaded via official actions/download-artifact with original artifact
IDs. Provenance is checked against T3's permanent original archive catalog.
No optimizer fitting, retuning, outcome selection, or statistical testing.
"""
import csv,gzip,hashlib,io,json,sys
from pathlib import Path
SOURCES=(
("heldout_global",13178442769,"17b8501d7017d7b131bb6ec81b9b483df3782e315f94d7df6591f55847066a4a",
 "data-archive/heldout/actions/actions-13178442769_t3-b3-pairwise-global-heldout-run41502642569.zip/manifest.json"),
("realworld_destination",13542889733,"3e7c28d685a8778cc4d70391e5b8433b14b97178e015bcb262e9280a6611e132",
 "data-archive/realworld/actions/actions-13542889733_t3-rw-v3-destination-global-taxonomy-run42299685581.zip/manifest.json"),
("realworld_final_four_module",13901031141,"c10edf560c8e1f8f6ccec910f6f8185d667df807900cbbcea2687b6615151f34",
 "data-archive/realworld/actions/actions-13901031141_t3-rw-pub-four-module-global-validation-run43098925126.zip/manifest.json")
)
def require(x,msg):
    if not x:raise RuntimeError("CROSS_FAMILY_ORIGINAL_RECOVERY_GATE: "+str(msg))
def check_manifest(m,label,aid,sha):
    z=json.loads(Path(m).read_text())
    require(z["complete"] is True and int(z["source"]["artifact_id"])==aid,"original catalog identity "+label)
    require(z["sha256"]==sha,"original catalog digest mismatch "+label)
    return z
def peek(path):
    n=path.name.lower()
    delim="\t" if ".tsv" in n else ","
    if not n.endswith((".csv",".csv.gz",".tsv",".tsv.gz",".json",".jsonl",".md")):
        return "",""
    try:
        openfunc=gzip.open if n.endswith(".gz") else open
        with openfunc(path,"rt",encoding="utf-8",errors="replace",newline="") as f:
            if n.endswith((".csv",".csv.gz",".tsv",".tsv.gz")):
                head=f.readline().strip()[:4000]
                cols="|".join(next(csv.reader([head],delimiter=delim)))[:3300]
                sample=f.readline().strip()[:1200]
                return cols,sample
            return "",f.readline().strip()[:1200]
    except (OSError,ValueError,EOFError,UnicodeError) as e:return "","ERROR:"+str(e)[:150]
def main(output):
    out=Path(output);require(not out.exists(),"append-only original-source recovery")
    out.mkdir(parents=True)
    original=[];contents=[]
    for label,aid,digest,manifest in SOURCES:
        a=check_manifest(manifest,label,aid,digest)
        folder=Path("incoming")/label
        require(folder.is_dir(),"official original artifact missing "+label)
        fs=sorted(p for p in folder.rglob("*") if p.is_file())
        require(fs,"download did not extract anything "+label)
        source=dict(artifact=label,artifact_id=aid,original_catalog_zip_sha256=digest,
                    original_catalog_size_bytes=a["size_bytes"],original_catalog_path=manifest,
                    downloaded_via="actions/download-artifact@v5",
                    extracted_file_count=len(fs),original_zip_sha256_independently_rechecked=False,
                    download_authenticity="GitHub Actions original artifact ID and preserved catalog checksum")
        original.append(source)
        for f in fs:
            cols,sample=peek(f)
            contents.append(dict(artifact=label,artifact_id=aid,file_name=str(f.relative_to(folder)),
                original_extracted_file_bytes=f.stat().st_size,fields=cols,example=sample))
        print("ORIGINAL_GITHUB_ARTIFACT_CATALOG_ID_VERIFIED",label,aid,"files",len(fs),flush=True)
    def dump(name,rows,fields):
        with (out/name).open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    cols=["artifact","artifact_id","file_name","original_extracted_file_bytes","fields","example"]
    dump("ORIGINAL_CROSS_FAMILY_ARCHIVE_FILES.csv",contents,cols)
    cross=[r for r in contents if "source_family" in r["fields"] and ("evaluation_family" in r["fields"] or "transfer_scope" in r["fields"])]
    parents=[r for r in contents if "parent_dataset_id" in r["fields"] or "independent_parent_datasets" in r["fields"]]
    dump("SCIENCE_CROSS_FAMILY_SOURCE_TABLES.csv",cross,cols)
    dump("SCIENCE_REALWORLD_PARENT_TABLES.csv",parents,cols)
    audit=dict(status="PASS_ARCHIVED_ORIGINAL_ARTIFACT_IDENTITIES_AND_SCHEMA_INVENTORY",
               source_archives=original,extracted_source_files=len(contents),
               source_family_transfer_data_files=len(cross),
               realworld_parent_scientific_files=len(parents),
               original_archive_zip_hash_independently_reverified=False,
               inventory_not_full_inference_reproduction=True,
               original_archive_backups_preserved=True,
               archived_original_source_sha256_claim="T3 original archival inventory, not independently rehashed on re-download",
               no_retraining_or_simulation=True)
    (out/"TRANSFER_RECOVERY_AUDIT.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n")
    checks={}
    for f in sorted(out.iterdir()):
        if f.is_file():checks[f.name]={"bytes":f.stat().st_size,"sha256":hashlib.sha256(f.read_bytes()).hexdigest()}
    (out/"RECOVERY_OUTPUT_SHA256_MANIFEST.json").write_text(json.dumps(checks,indent=2,sort_keys=True)+"\n")
    require(len(cross)>0,"No cross-family/source-scope result files recovered")
    print("T3_CROSS_FAMILY_ARTIFACT_TABLE_INVENTORY_PASS",len(cross),len(parents),flush=True)
if __name__=="__main__":
    require(len(sys.argv)==2,"usage: output");main(sys.argv[1])
