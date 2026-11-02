#!/usr/bin/env python3
"""Package one immutable parent block with verified inputs and labels."""
import argparse,csv,hashlib,json,shutil
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('catalog_root',type=Path);p.add_argument('block_manifest',type=Path)
p.add_argument('family_classifier',type=Path);p.add_argument('--family',required=True)
p.add_argument('--block-id',required=True);p.add_argument('--out-dir',type=Path,required=True)
a=p.parse_args();root=a.catalog_root.resolve();out=a.out_dir
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(path):return list(csv.DictReader(path.open(newline='',encoding='utf-8-sig')))
rows=read(a.block_manifest);classes=read(a.family_classifier)
lookup={r['dataset_id']:r for r in classes}
if len(lookup)!=len(classes):raise SystemExit('Duplicate dataset in empirical family classifier')
rows=[r for r in rows if r.get('training_family')==a.family and r.get('parent_block_id')==a.block_id]
if not rows:raise SystemExit('Requested family/block has no children')
need={'parent_dataset_id','dataset_id','processed_path','processed_sha256','source_path','source_sha256',
 'license_evidence_path','license_evidence_sha256','profile_sha256','training_family','transfer_scope'}
if need-set(rows[0]):raise SystemExit('Parent block manifest lacks provenance fields')
out.mkdir(parents=True,exist_ok=False)
for sub in ('processed','sources','license_evidence'): (out/sub).mkdir()
def resolve(p):
 x=Path(p)
 return x.resolve() if x.is_absolute() else (root/x).resolve()
def copy_verified(row,path_col,hash_col,sub,suffix):
 src=resolve(row[path_col]);expected=row[hash_col].strip().lower()
 if not src.is_file() or sha(src)!=expected:raise SystemExit(f'{path_col} SHA mismatch for {row["dataset_id"]}')
 name=f'{expected}.{suffix or src.suffix.lstrip(".") or "bin"}'
 dst=out/sub/name
 if not dst.exists():shutil.copy2(src,dst)
 if sha(dst)!=expected:raise SystemExit(f'Copied {path_col} SHA mismatch')
 return f'{sub}/{name}'
packed=[]
for row in rows:
 c=lookup.get(row['dataset_id'])
 if c is None or c['parent_dataset_id']!=row['parent_dataset_id']:
  raise SystemExit(f'Missing or mismatched family label for {row["dataset_id"]}')
 q=dict(row)
 q['source_path']=copy_verified(row,'source_path','source_sha256','sources','')
 q['processed_path']=copy_verified(row,'processed_path','processed_sha256','processed','rds')
 q['license_evidence_path']=copy_verified(row,'license_evidence_path','license_evidence_sha256','license_evidence','')
 for k,v in c.items():
  if k not in {'dataset_id','parent_dataset_id'}:q[k]=v
 q['empirical_family_relation']='same_family' if c['empirical_family_assignment']==a.family else 'other_family'
 q['family_assignment_scope']='proximity_diagnostic_not_true_dgp'
 packed.append(q)
manifest=out/'parent_block_manifest.csv'
with manifest.open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=list(packed[0]));w.writeheader();w.writerows(packed)
parent_ids=sorted({r['parent_dataset_id'] for r in packed})
payload={'protocol':'T3_B3_realworld_parent_block_bundle_v1','training_family':a.family,
 'parent_block_id':a.block_id,'parent_count':len(parent_ids),'child_count':len(packed),
 'parent_ids':parent_ids,'manifest_sha256':sha(manifest),
 'family_classifier_method':packed[0]['family_assignment_method'],
 'family_classifier_rows':len({r['dataset_id'] for r in packed}),
 'all_source_and_processed_hashes_verified':True,
 'source_hashes':[r['source_sha256'] for r in packed],
 'processed_hashes':[r['processed_sha256'] for r in packed],
 'license_evidence_hashes':[r['license_evidence_sha256'] for r in packed]}
(out/'block_provenance.json').write_text(json.dumps(payload,indent=2)+'\n')
print('T3_REALWORLD_BLOCK_BUNDLE_PASS',json.dumps({k:v for k,v in payload.items() if k not in {'parent_ids','source_hashes','processed_hashes','license_evidence_hashes'}},sort_keys=True))
