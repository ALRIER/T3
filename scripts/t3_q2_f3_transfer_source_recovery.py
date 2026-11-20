#!/usr/bin/env python3
"""Inspect original verified T3 GitHub Actions archives for cross-family evidence.

No optimizer fitting, resimulation, or hypothesis testing. All original outputs
remain in the existing immutable data-archive; this writes a new source inventory.
"""
import csv,gzip,hashlib,io,json,os,sys,urllib.request,zipfile
from pathlib import Path
SOURCES=(
 ("heldout_global",13178442769,"17b8501d7017d7b131bb6ec81b9b483df3782e315c94d7df6591f55847066a4a","heldout","41502642569"),
 ("realworld_destination",13542889733,"3e7c28d685a8778cc4d70391e5b8433b14b97178e015bcb262e9280a6611e132","realworld","42299685581"),
 ("realworld_final_four_module",13901031141,"c10edf560c8e1f8f6ccec910f6f8185d667df807900cbbcea2687b6615151f34","realworld","43098925126")
)
def check(a,msg):
    if not a:raise RuntimeError("CROSS_FAMILY_RESCUE_GATE: "+msg)
def fetch_one(spec,output):
    label,aid,expected,stage,run=spec
    token=os.environ.get("GH_TOKEN")
    check(token,"GITHUB_TOKEN required")
    target=Path("/tmp")/("t3_transfer_recovery_"+str(aid)+".zip")
    url=f"https://api.github.com/repos/ALRIER/T3/actions/artifacts/{aid}/zip"
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"T3-scientific-archive-recovery"})
    sha=hashlib.sha256()
    with urllib.request.urlopen(req,timeout=120) as stream,target.open("wb") as f:
        while True:
            block=stream.read(1<<20)
            if not block:break
            f.write(block);sha.update(block)
    got=sha.hexdigest()
    check(got==expected,f"original archive hash {aid}: {got} != {expected}")
    result={"artifact":label,"artifact_id":aid,"stage":stage,"original_run":run,
       "original_zip_sha256_verified":got,"bytes":target.stat().st_size}
    files=[]
    with zipfile.ZipFile(target) as z:
        check(z.testzip() is None,"ZIP CRC content failure "+label)
        for ent in z.infolist():
            if ent.is_dir():continue
            name=ent.filename
            row={"artifact":label,"artifact_id":aid,"file_name":name,"uncompressed_bytes":ent.file_size,
                 "zip_crc":ent.CRC,"columns":"","sample":""}
            candidate=name.lower().endswith((".csv",".csv.gz",".json",".jsonl",".tsv",".tsv.gz",".md"))
            if candidate:
                try:
                    with z.open(ent) as raw:
                        stream=gzip.GzipFile(fileobj=raw) if name.lower().endswith(".gz") else raw
                        with io.TextIOWrapper(stream,encoding="utf-8",errors="replace") as txt:
                            first=txt.readline().strip()[:2000]
                            if name.lower().endswith((".csv",".csv.gz",".tsv",".tsv.gz")):
                                delim="\t" if ".tsv" in name.lower() else ","
                                row["columns"]="|".join(next(csv.reader([first],delimiter=delim)))[:2000]
                                row["sample"]=txt.readline().strip()[:1200]
                            else:
                                row["sample"]=first[:1200]
                except (OSError,ValueError,EOFError,UnicodeError) as e:
                    row["sample"]="READ_ERROR:"+str(e)[:120]
            files.append(row)
    result["file_count"]=len(files)
    print("SOURCE_ARTIFACT_SHA256_PASS",label,aid,"files",len(files),"bytes",result["bytes"],flush=True)
    target.unlink()
    return result,files

def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
    summary=[];allfiles=[]
    for spec in SOURCES:
        x,y=fetch_one(spec,out);summary.append(x);allfiles.extend(y)
    mandatory=["source_family","evaluation_family"]
    transfer=[r for r in allfiles if all(k in r["columns"].lower() for k in mandatory)]
    primary=[r for r in allfiles if "source_family" in r["columns"].lower()
      and ("parent_dataset_id" in r["columns"].lower() or "transfer_scope" in r["columns"].lower())]
    audit=dict(status="PASS_ORIGINAL_TRANSFER_SOURCE_ARCHIVE_RECOVERY",
        original_sources=summary,original_zip_files_scanned=len(allfiles),
        files_with_source_and_evaluation_family_columns=len(transfer),
        files_with_realworld_parent_or_transfer_columns=len(primary),
        no_retraining=True,no_original_archive_overwrite=True,
        note="File/column inventory and original archive SHA checks only. No new statistical claims or independent validation of archived BH p-values.")
    def csvwrite(name,rows,keys):
        with (out/name).open("w",newline="",encoding="utf8") as f:
            w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
    csvwrite("ORIGINAL_TRANSFER_ARCHIVE_CONTENTS.csv",allfiles,
             ["artifact","artifact_id","file_name","uncompressed_bytes","zip_crc","columns","sample"])
    csvwrite("SCIENTIFIC_TRANSFER_TABLE_CANDIDATES.csv",transfer,
             ["artifact","artifact_id","file_name","uncompressed_bytes","zip_crc","columns","sample"])
    csvwrite("REALWORLD_PARENT_SCOPE_TABLE_CANDIDATES.csv",primary,
             ["artifact","artifact_id","file_name","uncompressed_bytes","zip_crc","columns","sample"])
    (out/"TRANSFER_SOURCE_RECOVERY_AUDIT.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n")
    hh={}
    for f in sorted(out.iterdir()):
        if f.is_file():hh[f.name]={"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"bytes":f.stat().st_size}
    (out/"TRANSFER_OUTPUT_SHA256_MANIFEST.json").write_text(json.dumps(hh,indent=2,sort_keys=True)+"\n")
    check(len(transfer)>0,"no source-by-destination scientific table found")
    print("CROSS_FAMILY_TRANSFER_INVENTORY_PASS",len(transfer),"cross-family datasets",len(primary),"parent-scope tables",flush=True)
if __name__=="__main__":main()
