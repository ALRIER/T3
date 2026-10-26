#!/usr/bin/env python3
"""Fail-closed provenance and redistribution gate for a frozen external catalog."""
import argparse, csv, re, hashlib
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

SHA256=re.compile(r'^[0-9a-f]{64}$',re.I)
REQUIRED={'dataset_id','parent_dataset_id','source_url','source_path','source_sha256',
          'processed_path','processed_sha256','profile_sha256','license_name',
          'license_url','license_review_status','catalog_commit'}
p=argparse.ArgumentParser()
p.add_argument('manifest')
p.add_argument('--minimum-parents',type=int,default=1)
a=p.parse_args()
with open(a.manifest,newline='',encoding='utf-8') as f:
 rows=list(csv.DictReader(f))
if not rows:raise SystemExit('BLOCKED: external dataset manifest is empty')
missing=REQUIRED-set(rows[0])
if missing:raise SystemExit('BLOCKED: missing manifest columns: '+', '.join(sorted(missing)))
seen=set();parents=defaultdict(set)
for line,row in enumerate(rows,2):
 if not row.get('dataset_id','').strip() or row['dataset_id'] in seen:
  raise SystemExit(f'BLOCKED: blank/duplicate dataset_id at line {line}')
 seen.add(row['dataset_id'])
 if not row.get('parent_dataset_id','').strip():raise SystemExit(f'BLOCKED: no parent_dataset_id at line {line}')
 for field in ('source_sha256','processed_sha256','profile_sha256'):
  if not SHA256.fullmatch(row.get(field,'').strip()):raise SystemExit(f'BLOCKED: invalid {field} at line {line}')
 for path_field,hash_field in (('source_path','source_sha256'),('processed_path','processed_sha256')):
  target=Path(row[path_field])
  if not target.is_file():raise SystemExit(f'BLOCKED: missing {path_field} at line {line}')
  h=hashlib.sha256()
  with target.open('rb') as stream:
   for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
  digest=h.hexdigest()
  if digest.lower()!=row[hash_field].lower():raise SystemExit(f'BLOCKED: checksum mismatch for {path_field} at line {line}')
 for field in ('source_url','license_url'):
  u=urlparse(row.get(field,'').strip())
  if u.scheme!='https' or not u.netloc:raise SystemExit(f'BLOCKED: non-HTTPS/missing {field} at line {line}')
 if row.get('license_review_status','').strip().lower()!='verified' or not row.get('license_name','').strip():
  raise SystemExit(f'BLOCKED: license is not individually verified at line {line}')
 if not row.get('catalog_commit','').strip():raise SystemExit(f'BLOCKED: catalog commit missing at line {line}')
 parents[row['parent_dataset_id']].add(row['source_sha256'].lower())
if any(len(hashes)!=1 for hashes in parents.values()):
 raise SystemExit('BLOCKED: one parent_dataset_id maps to multiple raw source hashes')
if len(parents)<a.minimum_parents:
 raise SystemExit(f'BLOCKED: {len(parents)} independent parents; minimum is {a.minimum_parents}')
print(f'T3_REALWORLD_MANIFEST_PASS rows={len(rows)} parents={len(parents)} licenses=verified')
