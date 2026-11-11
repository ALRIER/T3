#!/usr/bin/env python3
"""Audit 84 immutable outcome-blind parent-feature exports before publishing.

Fail closed on ambiguous parent identity; do not reassign/rename parent IDs,
discard parent records, or confuse source block samples with independent parents.
"""
import collections,csv,hashlib,json,pathlib,sys
ROOT=pathlib.Path('incoming/parent_profiles')
OUT=pathlib.Path('artifacts/post_rw_parent_features')
OUT.mkdir(parents=True,exist_ok=True)
paths=sorted(ROOT.rglob('profiles_*.csv'))
blocks=set()
by_key=collections.defaultdict(list)
by_parent=collections.defaultdict(list)
for path in paths:
 with path.open(newline='') as f:
  reader=csv.DictReader(f)
  rows=list(reader)
 if not rows:raise ValueError('Empty frozen source block '+str(path))
 for row in rows:
  block=(row['source_family'],row['original_parent_block_id'])
  blocks.add(block)
  key=(row['parent_dataset_id'],row['sample_n'])
  by_key[key].append((path.name,row))
  by_parent[row['parent_dataset_id']].append((path.name,row))
expected={(family,f'b{b:02d}') for family in
 ('normal','lognormal','weibull','invgauss','exgaussian','exwald') for b in range(1,15)}
if len(paths)!=84 or blocks!=expected:
 raise ValueError('Expected 84 unique immutable frozen source blocks')
diagnostics=[]
for key,items in by_key.items():
 if len(items)<2:continue
 unique={}
 for file,row in items:
  d=tuple(sorted(row.items()))
  unique.setdefault(d,[]).append(file)
 diagnostics.append(dict(parent_dataset_id=key[0],sample_n=key[1],
  occurrences=len(items),distinct_feature_vectors=len(unique),
  families=sorted(set(r['source_family'] for _,r in items)),
  blocks=sorted(set(r['original_parent_block_id'] for _,r in items)),
  files=sorted(set(file for file,_ in items)),
  input_sha256s=sorted(set(r.get('original_parent_block_id','')+'|'+r.get('source_family','') for _,r in items))))
diag=dict(original_export_run=43103963144,total_files=len(paths),
 total_records=sum(len(v) for v in by_key.values()),
 unique_parent_ids=len(by_parent),unique_parent_sample_size_keys=len(by_key),
 distinct_original_blocks=len(blocks),colliding_parent_n_keys=len(diagnostics),
 identical_repeated_keys=sum(x['distinct_feature_vectors']==1 for x in diagnostics),
 conflicting_repeated_keys=sum(x['distinct_feature_vectors']>1 for x in diagnostics),
 collisions=diagnostics[:100],all_source_block_jobs_preserved=True)
(OUT/'original_parent_collision_diagnostic.json').write_text(json.dumps(diag,indent=2)+'\n')
print('FROZEN_PARENT_FEATURE_COLLISION_DIAGNOSTIC',
      json.dumps({k:v for k,v in diag.items() if k!='collisions'}),flush=True)
if diag['conflicting_repeated_keys']>0:
 raise ValueError('Conflicting independent-parent identities; stop and reconcile original catalog provenance')
if diag['unique_parent_ids']!=642 or diag['unique_parent_sample_size_keys']!=1926:
 raise ValueError('Independent 642 parent / 1926 parent-n coverage not demonstrated; do not invent units')
rows=[]
for key,items in sorted(by_key.items()):
 rows.append(items[0][1])
output=OUT/'outcome_blind_parent_features.csv'
with output.open('w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]))
 writer.writeheader();writer.writerows(rows)
(OUT/'frozen_parent_features_provenance.json').write_text(json.dumps(dict(
 frozen_parent_block_run=41514871500,original_feature_export_run=43103963144,
 independent_parents=642,raw_parent_feature_records=diag['total_records'],
 identical_rows_deduplicated=diag['total_records']-len(rows),
 sample_n=[200,1000,3000],original_parent_blocks=84,
 original_parent_features_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
 outcome_blind=True,uses_realworld_estimator_scores=False,
 fit_to_realworld_validation_outcomes=False),indent=2)+'\n')
print('POST_RW_642_FROZEN_INDEPENDENT_PARENT_FEATURES_PASS',len(rows))
