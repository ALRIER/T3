#!/usr/bin/env python3
"""Read-only forensic audit of the published T3 research archive.
Compares recorded source identities to live GitHub Actions inventory;
verifies all original/part manifests and Git LFS pointer IDs without downloading
the 45 GB archive; writes a ranked list of independent LFS download spot checks.
"""
import csv,hashlib,json,os,pathlib,re,subprocess,sys,time,urllib.error,urllib.request,collections

ROOT=pathlib.Path(__file__).resolve().parents[2]
STORE=ROOT/"data-archive"
OUT=ROOT/"audit-output"
REPO=os.environ.get("GITHUB_REPOSITORY","ALRIER/T3")
TOKEN=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
STAGES={"montecarlo","discovery","heldout","stress","realworld","provenance","misc"}
def api_json(url):
    if not TOKEN:raise RuntimeError("Missing GITHUB_TOKEN")
    last=None
    for retry in range(5):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"T3-independent-forensic-audit/1.0",
               "Authorization":"Bearer "+TOKEN,
               "Accept":"application/vnd.github+json",
               "X-GitHub-Api-Version":"2022-11-28"})
            with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as e:
            last=e
            time.sleep(min(12,2**retry))
    raise RuntimeError(f"API failed {url}: {last}")
def sha256_path(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(8*1024*1024),b""):h.update(block)
    return h.hexdigest()

def audit():
    OUT.mkdir(exist_ok=True)
    catalog=json.loads((STORE/"catalog"/"sources.json").read_text())
    archived_status=json.loads((STORE/"catalog"/"status.json").read_text())
    sources=catalog["sources"]
    keys={x["key"]:x for x in sources}
    errors=[];warn=[];manifest_count=0;part_count=0
    manifest_bytes=0;part_bytes=0
    seen_paths=set()
    sample_options=collections.defaultdict(list)
    for item in sources:
        stem=re.sub(r"[^A-Za-z0-9._-]","_",item["name"])[:90]
        d=STORE/item["stage"]/item["source"]/(item["key"]+"_"+stem)
        manifest=d/"manifest.json"
        if not manifest.is_file():
            errors.append("MISSING_MANIFEST "+item["key"]);continue
        try:m=json.loads(manifest.read_text())
        except Exception as e:
            errors.append("UNREADABLE_MANIFEST "+item["key"]+" "+str(e));continue
        manifest_count+=1
        manifest_bytes+=m["size_bytes"]
        if m["source"]["key"]!=item["key"]:
            errors.append("SOURCE_ID_MISMATCH "+item["key"])
        if m["size_bytes"]!=item.get("size_bytes",0) and item.get("size_bytes",0):
            errors.append("SOURCE_BYTES_MISMATCH "+item["key"])
        if m.get("chunk_size")!=32*1024*1024:
            errors.append("CHUNK_SIZE_UNEXPECTED "+item["key"])
        if not m.get("complete"):
            errors.append("MANIFEST_INCOMPLETE "+item["key"])
        if not re.fullmatch("[a-f0-9]{64}",m.get("sha256","")):
            errors.append("INVALID_ARCHIVE_SHA "+item["key"])
        if sum(p["bytes"] for p in m.get("parts",[]))!=m["size_bytes"]:
            errors.append("CHUNK_SUM_MISMATCH "+item["key"])
        if item["stage"] not in STAGES:
            errors.append("UNKNOWN_STAGE "+item["key"])
        for p in m.get("parts",[]):
            f=d/p["name"];name=str(f.relative_to(ROOT))
            if name in seen_paths:errors.append("DUPLICATE_PART "+name)
            seen_paths.add(name);part_count+=1
            if not f.exists():
                errors.append("MISSING_PART "+name);continue
            # Checkout uses lfs:false; these are 129-byte pointer files.
            content=f.read_bytes()
            expected=(f"version https://git-lfs.github.com/spec/v1\n"
                f"oid sha256:{p['sha256']}\nsize {p['bytes']}\n").encode()
            if content!=expected:
                errors.append("LFS_POINTER_MISMATCH "+name)
            if p["bytes"]<=0 or p["bytes"]>32*1024*1024:
                errors.append("INVALID_PART_SIZE "+name)
            part_bytes+=p["bytes"]
        # Choose a moderate sized object in each stage for actual LFS-byte verification.
        if m["parts"] and 100_000<=m["size_bytes"]<=20_000_000:
            sample_options[item["stage"]].append((m["size_bytes"],item["key"],str(d.relative_to(ROOT))))
    # Walk manifest and parts in repository to find orphans, uncatalogued members.
    actual_manifests={str(x.relative_to(ROOT)) for x in STORE.glob("*/**/manifest.json")}
    actual_parts={str(x.relative_to(ROOT)) for x in STORE.glob("*/**/part-*.lfs")}
    if len(actual_manifests)!=manifest_count:
        errors.append(f"ORPHAN_OR_MISSING_MANIFESTS actual={len(actual_manifests)} expected={manifest_count}")
    orphans=actual_parts-seen_paths
    if orphans:errors.extend("ORPHAN_CHUNK "+x for x in sorted(orphans)[:200])
    missing=seen_paths-actual_parts
    if missing:errors.extend("MISSING_CHUNK "+x for x in sorted(missing)[:200])
    if manifest_bytes!=archived_status["archived_original_bytes"]:
        errors.append("STATUS_SUM_DIFFERENT")
    if len(sources)!=archived_status["archived_sources"]:
        errors.append("STATUS_COUNT_DIFFERENT")
    if manifest_count!=len(sources):
        errors.append("INVENTORY_NOT_FULLY_PRESENT")

    # Compare live remote source list with frozen inventory, page until exhaustion.
    current={};page=1
    while True:
        q=api_json(f"https://api.github.com/repos/{REPO}/actions/artifacts?per_page=100&page={page}")
        batch=q.get("artifacts",[])
        for a in batch:
            if a["name"].startswith("t3-complete-archive-"):continue
            current["actions-"+str(a["id"])]={"name":a["name"],
                "expired":a.get("expired"),"size_bytes":a.get("size_in_bytes")}
        if len(batch)<100:break
        page+=1
        if page>200:raise RuntimeError("Unexpected 20,000+ Actions artifacts")
    recorded={k for k in keys if k.startswith("actions-")}
    latest=set(current)
    new=sorted(latest-recorded)
    vanished=sorted(recorded-latest)
    if new:warn.append(f"NEW_ACTIONS_ARTIFACTS_NOT_IN_FROZEN_CATALOG {len(new)}")
    if vanished:warn.append(f"FROZEN_ARTIFACTS_NO_LONGER_IN_ACTIONS {len(vanished)}")
    expired_current=[k for k,v in current.items() if v["expired"]]
    if expired_current:warn.append(f"CURRENTLY_EXPIRED_ACTIONS_ARTIFACTS {len(expired_current)}")
    if len(orphans)==0 and len(missing)==0 and not errors:
        print("ALL_LOCAL_MANIFESTS_AND_LFS_POINTERS_PASS",manifest_count,part_count,flush=True)
    samples=[]
    for stage in sorted(STAGES):
        choices=sorted(sample_options[stage])
        if choices:
            # Select median-sized moderate original ZIP for reproducible spot check.
            size,key,path=choices[len(choices)//2]
            samples.append({"stage":stage,"key":key,"path":path,"size_bytes":size})
    (OUT/"spotcheck_targets.json").write_text(json.dumps(samples,indent=2)+"\n")
    with (OUT/"new_since_frozen_inventory.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["key","name","bytes","expired"])
        for key in new:w.writerow([key,current[key]["name"],current[key]["size_bytes"],current[key]["expired"]])
    report={
        "audit_type":"independent_structure_and_live_source_crosscheck",
        "archived_manifests":manifest_count,"archived_parts":part_count,
        "archived_bytes_from_manifests":manifest_bytes,
        "part_bytes":part_bytes,
        "status_complete":archived_status["complete"],
        "current_actions_sources":len(current),
        "frozen_actions_sources":len(recorded),
        "new_actions_since_frozen_inventory":len(new),
        "recorded_actions_now_absent":len(vanished),
        "live_expired":len(expired_current),
        "new_action_examples":new[:35],"absent_examples":vanished[:35],
        "stage_counts":archived_status["by_stage"],
        "sample_targets":samples,
        "errors":errors[:200],
        "warnings":warn,
        "structural_pass":len(errors)==0,
        "NOTE":"This checks all manifests and LFS Git pointer hashes/sizes, not underlying LFS object availability. Separate staged download/reconstruction required."
    }
    (OUT/"audit_summary.json").write_text(json.dumps(report,indent=2)+"\n")
    print("INDEPENDENT_AUDIT_REPORT",json.dumps({k:v for k,v in report.items() if k not in ("sample_targets","stage_counts","errors","warnings")}),flush=True)
    if errors:raise SystemExit("STRUCTURAL_ERRORS "+str(errors[:15]))

if __name__=="__main__":audit()
