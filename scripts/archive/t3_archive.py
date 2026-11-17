#!/usr/bin/env python3
"""Lossless Actions + Zenodo experiment archive inside ALRIER/T3.
Inventory every available Actions artifact, including intermediate and failed-run files.
Publish original ZIP bytes as 32 MiB Git-LFS chunks with SHA-256 manifests.
No experimental calculations are rerun.
"""
import argparse, hashlib, json, os, pathlib, re, shutil, sys, time
import urllib.error, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[2]
STORE=ROOT/"data-archive"
CATALOG=STORE/"catalog"/"sources.json"
REPORT=ROOT/".archive-report"
REPO=os.environ.get("GITHUB_REPOSITORY","ALRIER/T3")
TOKEN=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
ZENODO_ID="24174965"
CHUNK_SIZE=32*1024*1024
MAX_BATCH_BYTES=720*1024*1024
STAGES=["montecarlo","discovery","heldout","stress","realworld","provenance","misc"]
KNOWN_RUNS={
"montecarlo":{40239277660},
"discovery":{41113724413,41487091262,43102984348},
"heldout":{42045005791,42050564002},
"stress":{42062234485,42092352487},
"realworld":{42251598557,42282378329,42285271441,42299685581,42390283887,43098925126,43110499408},
"provenance":{43313187401,43313617900,43314309491,43315500255,43102438703}}
ZENODO_STAGES={"01":"montecarlo","02":"discovery","03":"heldout","04":"heldout","05":"stress","06":"stress","07":"stress","08":"realworld","09":"realworld","10":"realworld"}

def http_json(url,github=False):
    headers={"User-Agent":"T3-complete-archive/1.0"}
    if github:
        if not TOKEN: raise RuntimeError("Missing GH_TOKEN")
        headers.update({"Accept":"application/vnd.github+json",
          "Authorization":"Bearer "+TOKEN,"X-GitHub-Api-Version":"2022-11-28"})
    last=None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=120) as response:
                return json.load(response)
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as e:
            last=e
            if isinstance(e,urllib.error.HTTPError) and e.code in (401,403,404) and attempt>=1:break
            time.sleep(min(16,2**attempt))
    raise RuntimeError(f"Cannot query {url}: {last}")

def stage_for(name,run):
    for stage,ids in KNOWN_RUNS.items():
        if int(run) in ids:return stage
    n=name.lower()
    for stage,pattern in [
      ("montecarlo",r"^b3-mc-|monte.?carlo|grid321|mc-"),
      ("discovery",r"discovery|nested.?hpo|optuna|weights.?registry"),
      ("heldout",r"held.?out"),
      ("stress",r"stress|rediscovery"),
      ("realworld",r"real.?world|^t3-rw-|^t3-b3-rw-"),
      ("provenance",r"zenodo|crosswalk|lineage|provenance|manifest|integrity")]:
        if re.search(pattern,n):return stage
    return "misc"

def source_catalog():
    items=[];page=1
    while True:
        j=http_json(f"https://api.github.com/repos/{REPO}/actions/artifacts?per_page=100&page={page}",True)
        batch=j.get("artifacts",[])
        for a in batch:
            if a["name"].startswith("t3-complete-archive-"):continue
            run=(a.get("workflow_run") or {}).get("id",0)
            items.append({"key":f"actions-{a['id']}","source":"actions",
              "stage":stage_for(a["name"],run),"artifact_id":a["id"],"run_id":run,
              "name":a["name"]+".zip","size_bytes":a["size_in_bytes"],
              "created_at":a.get("created_at"),"expires_at":a.get("expires_at"),
              "expired_at_inventory":bool(a.get("expired")),
              "url":f"https://api.github.com/repos/{REPO}/actions/artifacts/{a['id']}/zip"})
        if len(batch)<100:
            if len(items)>j.get("total_count",len(items)):raise ValueError("Artifact pagination mismatch")
            break
        page+=1
    if not items:raise RuntimeError("Actions artifact listing is empty; refusing incomplete archive")
    try:
        z=http_json(f"https://zenodo.org/api/records/{ZENODO_ID}")
        files=z.get("files",[])
        if isinstance(files,dict):files=list(files.get("entries",files).values())
        if not files:raise ValueError("Zenodo record has no files")
        for f in files:
            name=f.get("key")
            if not name:continue
            m=re.match(r"T3_([0-9]{2})_series.zip$",name)
            stage=ZENODO_STAGES.get(m.group(1),"provenance") if m else "provenance"
            items.append({"key":"zenodo-"+name,"source":"zenodo","stage":stage,
              "record_id":int(ZENODO_ID),"name":name,"size_bytes":f.get("size",0),
              "checksum":f.get("checksum",""),
              "url":f.get("links",{}).get("self") or
                f"https://zenodo.org/api/records/{ZENODO_ID}/files/{name}/content"})
    except Exception as e:
        print("WARNING: Zenodo index unavailable:",e,flush=True)
        for series,stage in ZENODO_STAGES.items():
            name=f"T3_{series}_series.zip"
            items.append({"key":"zenodo-"+name,"source":"zenodo","stage":stage,
              "record_id":int(ZENODO_ID),"name":name,"size_bytes":0,"checksum":"",
              "metadata_lookup_failed":True,
              "url":f"https://zenodo.org/api/records/{ZENODO_ID}/files/{name}/content"})
    keys=[x["key"] for x in items]
    if len(keys)!=len(set(keys)):raise ValueError("Duplicate source identities")
    actions=sorted((i for i in items if i["source"]=="actions"),
      key=lambda x:(x.get("expires_at") or x.get("created_at") or "",x["key"]))
    zenodo=sorted((i for i in items if i["source"]=="zenodo"),key=lambda x:x["key"])
    return {"schema_version":1,"repository":REPO,"zenodo_record_id":int(ZENODO_ID),
      "algorithm":"sha256-lossless-32MiB-git-lfs","sources":actions+zenodo}

def item_dir(item):
    stem=re.sub(r"[^A-Za-z0-9._-]","_",item["name"])[:90]
    return STORE/item["stage"]/item["source"]/(item["key"]+"_"+stem)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def download_url(item):
    if item["source"]=="zenodo":return item["url"]
    headers={"User-Agent":"T3-complete-archive/1.0",
      "Accept":"application/vnd.github+json","Authorization":"Bearer "+TOKEN,
      "X-GitHub-Api-Version":"2022-11-28"}
    req=urllib.request.Request(item["url"],headers=headers)
    try:
        urllib.request.build_opener(NoRedirect).open(req,timeout=90)
    except urllib.error.HTTPError as e:
        if e.code in (301,302,303,307,308) and e.headers.get("Location"):
            return e.headers["Location"]
        raise
    raise RuntimeError("Artifact ZIP endpoint did not return a download redirect")

def stream_parts(item):
    folder=item_dir(item)
    if (folder/"manifest.json").is_file():return False
    if folder.exists():raise RuntimeError("Incomplete target directory: "+str(folder))
    folder.mkdir(parents=True)
    digest=hashlib.sha256();md5=hashlib.md5();parts=[];size=0
    part=None;index=0;part_size=0;part_sha=None
    def open_part():
        nonlocal part,index,part_size,part_sha
        index+=1;part_size=0;part_sha=hashlib.sha256()
        part=(folder/f"part-{index:05d}.lfs").open("wb")
    def close_part():
        nonlocal part
        if part:
            part.close()
            parts.append({"name":f"part-{index:05d}.lfs",
               "bytes":part_size,"sha256":part_sha.hexdigest()})
            part=None
    try:
        request=urllib.request.Request(download_url(item),
            headers={"User-Agent":"T3-complete-archive/1.0"})
        with urllib.request.urlopen(request,timeout=180) as response:
            while True:
                buf=response.read(4*1024*1024)
                if not buf:break
                size+=len(buf);digest.update(buf);md5.update(buf)
                offset=0
                while offset<len(buf):
                    if part is None:open_part()
                    take=min(CHUNK_SIZE-part_size,len(buf)-offset)
                    seg=buf[offset:offset+take]
                    part.write(seg);part_sha.update(seg);part_size+=take;offset+=take
                    if part_size==CHUNK_SIZE:close_part()
        close_part()
        if size==0:raise RuntimeError("Empty source")
        if item.get("size_bytes") and size!=int(item["size_bytes"]):
            raise RuntimeError(f"Size mismatch {size}!={item['size_bytes']}")
        check=item.get("checksum","")
        if check.startswith("md5:") and md5.hexdigest()!=check.split(":",1)[1]:
            raise RuntimeError("Zenodo checksum mismatch")
        manifest={"schema_version":1,"source":item,"sha256":digest.hexdigest(),
          "md5":md5.hexdigest(),"size_bytes":size,"chunk_size":CHUNK_SIZE,
          "parts":parts,"complete":True}
        (folder/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
        print("ARCHIVED",item["key"],size,"bytes",len(parts),"parts",flush=True)
        return True
    except BaseException:
        if part:part.close()
        shutil.rmtree(folder,ignore_errors=True)
        raise

def status(catalog):
    src=catalog["sources"]
    saved=[x for x in src if (item_dir(x)/"manifest.json").exists()]
    missing=[x for x in src if not (item_dir(x)/"manifest.json").exists()]
    expired=[x for x in missing if x.get("expired_at_inventory")]
    x={"total_sources":len(src),"archived_sources":len(saved),
      "pending_sources":len(missing),"expired_unarchived":len(expired),
      "archived_original_bytes":sum(json.loads((item_dir(i)/"manifest.json").read_text())["size_bytes"] for i in saved),
      "expected_original_bytes":sum(int(i.get("size_bytes") or 0) for i in src),
      "by_stage":{s:{"total":sum(i["stage"]==s for i in src),
        "archived":sum(i["stage"]==s for i in saved),
        "expected_bytes":sum(int(i.get("size_bytes") or 0) for i in src if i["stage"]==s)} for s in STAGES},
      "complete":not missing,"scope":"sources in recorded inventory only"}
    CATALOG.parent.mkdir(parents=True,exist_ok=True)
    (CATALOG.parent/"status.json").write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
    return x

def main():
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=["inventory","publish","verify"])
    p.add_argument("--max-items",type=int,default=8)
    args=p.parse_args()
    # Fill each bounded batch efficiently even when an older dispatch passes 8.
    args.max_items=max(args.max_items, 80)
    REPORT.mkdir(exist_ok=True)
    (REPORT/"next.txt").write_text("stop\n")
    if args.mode=="inventory":
        cat=source_catalog()
        CATALOG.parent.mkdir(parents=True,exist_ok=True)
        CATALOG.write_text(json.dumps(cat,indent=2,sort_keys=True)+"\n")
        info=status(cat)
        if info["pending_sources"]:(REPORT/"next.txt").write_text("publish\n")
        print("INVENTORY",json.dumps(info),flush=True)
        return
    if not CATALOG.exists():raise RuntimeError("Run inventory before publication")
    cat=json.loads(CATALOG.read_text())
    if args.mode=="verify":
        errors=[]
        for i in cat["sources"]:
            m=item_dir(i)/"manifest.json"
            if not m.exists():continue
            v=json.loads(m.read_text())
            if sum(p["bytes"] for p in v["parts"])!=v["size_bytes"]:errors.append(i["key"])
            for part in v["parts"]:
                path=item_dir(i)/part["name"]
                if not path.is_file() or path.stat().st_size!=part["bytes"]:errors.append(str(path))
        if errors:raise RuntimeError("Broken part files: "+str(errors[:12]))
        print("ALL_AVAILABLE_LOCAL_PARTS_VERIFIED")
        return
    n=0;bytes_this_batch=0
    for item in cat["sources"]:
        if (item_dir(item)/"manifest.json").exists() or item.get("expired_at_inventory"):continue
        if n>=args.max_items or (n and bytes_this_batch+int(item.get("size_bytes") or 0)>MAX_BATCH_BYTES):
            break
        try:
            if stream_parts(item):
                n+=1;bytes_this_batch+=int(item.get("size_bytes") or 0)
        except Exception as e:
            print("DOWNLOAD_BLOCKED",item["key"],repr(e),file=sys.stderr,flush=True)
            (REPORT/"failed_source.json").write_text(json.dumps(
              {"source":item,"error":str(e)},indent=2))
            break
    info=status(cat)
    print("ARCHIVE_STATUS",json.dumps(info),flush=True)
    if n and info["pending_sources"]>info["expired_unarchived"]:
        (REPORT/"next.txt").write_text("publish\n")
    elif info["complete"]:print("INVENTORIED_ARCHIVE_COMPLETE",flush=True)
    else:print("ARCHIVE_BLOCKED_OR_EXPIRED",flush=True)

if __name__=="__main__":main()
