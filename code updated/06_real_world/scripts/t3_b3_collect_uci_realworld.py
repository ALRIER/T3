#!/usr/bin/env python3
"""Build an outcome-blind, per-parent UCI candidate catalog.

Only UCI records whose own page declares CC BY 4.0 are admitted. A dataset is
one parent; numeric columns are children and never increase parent n.
"""
import argparse, concurrent.futures, csv, hashlib, json, math, re, time
from pathlib import Path
from urllib.request import Request, urlopen

BASE="https://archive.ics.uci.edu"
NUMERIC={"integer","continuous","real","numeric"}
FINANCE=re.compile(r"\b(financ\w*|stock|equity|credit|bank\w*|currency|forex|loan|mortgage|portfolio|investment|insurance|bankruptcy|bond|yield|share price)\b",re.I)
CCBY=re.compile(r"Creative Commons Attribution 4\.0 International|CC BY 4\.0",re.I)

def get(url,timeout=30):
    req=Request(url,headers={"User-Agent":"T3-realworld-audit/1.0 (research dataset catalog)"})
    with urlopen(req,timeout=timeout) as r:return r.read()
def get_limited(url,limit=50*1024*1024):
    req=Request(url,headers={"User-Agent":"T3-realworld-audit/1.0 (research dataset catalog)"})
    with urlopen(req,timeout=30) as r:
        length=r.headers.get('Content-Length')
        if length and int(length)>limit:raise ValueError(f'data source exceeds {limit} byte cap')
        chunks=[];total=0
        while True:
            block=r.read(1024*1024)
            if not block:break
            total+=len(block)
            if total>limit:raise ValueError(f'data source exceeds {limit} byte cap')
            chunks.append(block)
        return b''.join(chunks)
def jsonget(url):return json.loads(get(url))
def sha(b):return hashlib.sha256(b).hexdigest()
def one_meta(item):
    last=None
    for attempt in range(3):
        try:return jsonget(f"{BASE}/api/dataset?id={item['id']}").get('data',{})
        except Exception as e:
            last=e;time.sleep(.25*(attempt+1))
    return {"uci_id":item['id'],"name":item.get('name',''),"_error":str(last)}
def number(v):
    if v is None:return None
    s=str(v).strip()
    if not s or s.lower() in {"?","nan","na","null"}:return None
    try:x=float(s)
    except (TypeError,ValueError):return None
    return x if math.isfinite(x) else None

p=argparse.ArgumentParser()
p.add_argument('--out',type=Path,default=Path('artifacts/T3_B3_realworld_uci'))
p.add_argument('--workers',type=int,default=6)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
evidence_dir=a.out/'license_evidence';evidence_dir.mkdir(parents=True,exist_ok=True)
items=jsonget(f'{BASE}/api/datasets/list').get('data',[])
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
    metadata=list(pool.map(one_meta,items))
eligible=[];rejects=[]
def verify_parent_page(d):
    variables=d.get('variables') or []
    numeric=[v for v in variables if str(v.get('type','')).lower() in NUMERIC
             and str(v.get('role','')).lower() not in {'id','identifier'}]
    if d.get('_error') or not isinstance(d.get('num_instances'),(int,float)) or d['num_instances']<150 or not numeric:
        return None,(d.get('uci_id'),d.get('name'),'metadata_or_numeric_sample_gate')
    page=d.get('repository_url') or f"{BASE}/dataset/{d['uci_id']}"
    try:page_bytes=get(page);html=page_bytes.decode('utf-8','ignore')
    except Exception as e:return None,(d.get('uci_id'),d.get('name'),f'page_fetch:{e}')
    license_match=CCBY.search(re.sub(r'<[^>]+>',' ',html))
    if not license_match:
        return None,(d.get('uci_id'),d.get('name'),'no_explicit_CC_BY_4.0_on_dataset_page')
    data_url=d.get('data_url','')
    if not data_url or not data_url.lower().endswith('.csv'):
        return None,(d.get('uci_id'),d.get('name'),'no_direct_CSV_download')
    evidence_path=evidence_dir/f"uci_{int(d['uci_id']):04d}.html"
    evidence_path.write_bytes(page_bytes)
    return (d,numeric,page,data_url,license_match.group(0),sha(page_bytes),evidence_path),None
page_candidates=[d for d in metadata if not d.get('_error') and
    isinstance(d.get('num_instances'),(int,float)) and d['num_instances']>=150 and
    any(str(v.get('type','')).lower() in NUMERIC and str(v.get('role','')).lower() not in {'id','identifier'}
        for v in (d.get('variables') or []))]
for d in metadata:
    if d not in page_candidates: rejects.append((d.get('uci_id'),d.get('name'),'metadata_or_numeric_sample_gate'))
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
    checked=list(pool.map(verify_parent_page,page_candidates))
for ok,bad in checked:
    if ok is not None:eligible.append(ok)
    if bad is not None:rejects.append(bad)
print('UCI catalog scan:',len(items),'records;',len(eligible),'parent candidates after n/numeric/license gates')
raw_dir=a.out/'raw';raw_dir.mkdir(parents=True,exist_ok=True)
def download_parent(item):
    d,variables,page,data_url,license_text,license_page_sha,evidence_path=item
    did=int(d['uci_id']);name=str(d.get('name','')).strip()
    try:
        raw=get_limited(data_url)
        if not raw.strip():raise ValueError('empty data payload')
        raw_path=raw_dir/f'uci_{did:04d}.csv';raw_path.write_bytes(raw)
        with raw_path.open(newline='',encoding='utf-8-sig',errors='replace') as f:
            reader=csv.DictReader(f);headers=reader.fieldnames or []
            # UCI tables can repeat a display name (for example, a feature and
            # a target). Preserve the API's positional variable identity rather
            # than collapsing columns into a name-keyed dictionary.
            aligned=[]
            for variable_index,v in enumerate(variables,1):
                if variable_index>len(headers):
                    continue
                if str(headers[variable_index-1]).strip()!=str(v.get('name','')).strip():
                    continue
                if str(v.get('type','')).lower() not in NUMERIC or \
                   str(v.get('role','')).lower() in {'id','identifier'}:
                    continue
                aligned.append((variable_index,v,[]))
            for record in reader:
                if None in record or any(value is None for value in record.values()):
                    raise ValueError('inconsistent CSV row width; source is not profile-safe')
                # DictReader loses duplicate-header values; read each CSV row
                # positionally instead. The reader is reopened below only for
                # sources whose headers contain duplicate names.
                for variable_index,v,vals in aligned:
                    col=headers[variable_index-1]
                    x=number(record.get(col))
                    if x is not None: vals.append(x)
        # DictReader cannot represent duplicate header names. Reparse with
        # csv.reader so each API variable is read from its exact source column.
        if len(set(headers))!=len(headers):
            for _,_,vals in aligned: vals.clear()
            with raw_path.open(newline='',encoding='utf-8-sig',errors='replace') as f:
                positional=csv.reader(f); next(positional,None)
                for record in positional:
                    if len(record)!=len(headers):
                        raise ValueError('inconsistent CSV row width; source is not profile-safe')
                    for variable_index,v,vals in aligned:
                        x=number(record[variable_index-1])
                        if x is not None: vals.append(x)
        valid=[(variable_index,v,len(vals)) for variable_index,v,vals in aligned if len(vals)>=150]
        if not valid:raise ValueError('no numeric child with >=150 finite observations')
        digest=sha(raw)
        text=' '.join((name,str(d.get('abstract','')),str(d.get('area',''))))
        sector='finance' if (str(d.get('area','')).lower() in {'business','economics','finance'} and FINANCE.search(text)) or FINANCE.search(name) else 'other'
        output=[]
        for variable_index,v,n in valid:
            variable_name=str(v['name']).strip()
            safe_name=re.sub(r'[^A-Za-z0-9_.-]+','_',variable_name)
            output.append({
              'dataset_id':f"uci_{did:04d}_v{variable_index:03d}_{safe_name}",
              'parent_dataset_id':f'uci_{did:04d}','source_path':str(raw_path.resolve()),
              'source_url':page,'domain':str(d.get('area','unknown')).lower().replace(' ','_'),
              'source_sector':sector,'source_group':'uci','variable':variable_name,'transform':'raw',
              'license_name':'CC-BY-4.0','license_url':page,
              'license_basis':'UCI_parent_record_CC-BY-4.0',
              'license_review_status':'verified','upstream_license_status':'verified_on_source_record',
              'upstream_source_url':page,'source_archive_doi':str(d.get('dataset_doi','')),
              'source_sha256':digest,'license_evidence':'explicit_CC_BY_4.0_text_on_UCI_dataset_page',
              'license_evidence_sha256':license_page_sha,
              'license_evidence_path':str(evidence_path.resolve()),
              'feature_index':variable_index,
              'child_selection_rule':'first_middle_last_by_UCI_variable_order_max3',
              'source_rows':int(d['num_instances']),'finite_numeric_n':n,
              'creator':'; '.join(d.get('creators') or []),'citation_doi':str(d.get('dataset_doi','')),
            })
        return output,None
    except Exception as e:
        return [],(did,name,f'download_or_parse:{e}')
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
    futures=[pool.submit(download_parent,item) for item in eligible]
    for index,future in enumerate(concurrent.futures.as_completed(futures),1):
        child_rows,rejected=future.result();rows.extend(child_rows)
        if rejected is not None:rejects.append(rejected)
        if index%10==0 or index==len(futures):
            print('UCI_PARENT_DOWNLOAD_PROGRESS',index,'/',len(futures),
                  'children',len(rows),'rejected',len(rejects),flush=True)
rows.sort(key=lambda r:(r['parent_dataset_id'],r['dataset_id']))
if not rows:raise SystemExit('No UCI parent-child rows survived license and source-data checks')
catalog=a.out/'candidate_catalog.csv'
with catalog.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['dataset_id']);w.writeheader();w.writerows(rows)
with (a.out/'catalog_rejections.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f);w.writerow(['uci_id','dataset_name','reason']);w.writerows(rejects)
parents={r['parent_dataset_id'] for r in rows}
finance={r['parent_dataset_id'] for r in rows if r['source_sector']=='finance'}
summary={'uci_records_seen':len(items),'accepted_parent_count':len(parents),
 'accepted_child_series_count':len(rows),'finance_parent_count':len(finance),
 'other_parent_count':len(parents-finance),'rejected_record_count':len(rejects),
 'catalog_sha256':sha(catalog.read_bytes()),'selector_uses_outcomes':False,
 'license_basis':'CC BY 4.0 declaration on each UCI parent record'}
(a.out/'catalog_manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
print('T3_B3_UCI_CATALOG_PASS',json.dumps(summary,sort_keys=True))
