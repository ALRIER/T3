#!/usr/bin/env python3
"""Freeze deterministic, parent-intact blocks for bounded Real-world scoring."""
import argparse, csv, json, math, hashlib
from collections import defaultdict
from pathlib import Path

FAMILIES=('normal','lognormal','weibull','invgauss','exgaussian','exwald')
p=argparse.ArgumentParser()
p.add_argument('manifest',type=Path);p.add_argument('--out',type=Path,required=True)
p.add_argument('--target-child-rows',type=int,default=55)
a=p.parse_args()
rows=list(csv.DictReader(a.manifest.open(newline='',encoding='utf-8-sig')))
required={'parent_dataset_id','dataset_id','training_family','processed_path','processed_sha256'}
if not rows or required-set(rows[0]): raise SystemExit('Frozen manifest schema is incomplete')
by_family=defaultdict(lambda:defaultdict(list))
for r in rows:
    if r['training_family'] not in FAMILIES: raise SystemExit('Unknown source family in manifest')
    by_family[r['training_family']][r['parent_dataset_id']].append(r)
if set(by_family)!=set(FAMILIES): raise SystemExit('Frozen manifest does not include all six families')
block_rows=[];index=[]
for family in FAMILIES:
    parents=by_family[family]
    if len(parents)!=642: raise SystemExit(f'{family}: expected 642 parent IDs, got {len(parents)}')
    child_total=sum(map(len,parents.values()))
    nblocks=math.ceil(child_total/a.target_child_rows)
    bins=[[] for _ in range(nblocks)];loads=[0]*nblocks
    # Greedy longest-parent-first scheduling balances child profiles while
    # keeping every child of a parent inside one checkpoint.
    ordered=sorted(parents.items(),key=lambda kv:(-len(kv[1]),kv[0]))
    for pid,children in ordered:
        j=min(range(nblocks),key=lambda k:(loads[k],k))
        bins[j].append(pid);loads[j]+=len(children)
    if max(loads)>a.target_child_rows*1.25:
        raise SystemExit(f'{family}: parent clustering makes blocks too imbalanced: {max(loads)} rows')
    for j,pids in enumerate(bins,1):
        bid=f'b{j:02d}'
        chunk=[]
        for pid in sorted(pids):
            for r in parents[pid]:
                q=dict(r);q['parent_block_id']=bid;chunk.append(q)
        block_rows.extend(chunk)
        index.append({'training_family':family,'parent_block_id':bid,
          'parent_count':len(pids),'child_count':len(chunk),
          'parent_ids_semicolon':';'.join(sorted(pids))})
    if sum(loads)!=child_total: raise SystemExit('Block planner lost child rows')
a.out.parent.mkdir(parents=True,exist_ok=True)
with a.out.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(block_rows[0]));w.writeheader();w.writerows(block_rows)
idx=a.out.with_name('realworld_parent_block_index.csv')
with idx.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(index[0]));w.writeheader();w.writerows(index)
if len({(r['training_family'],r['parent_dataset_id']) for r in block_rows})!=6*642:
    raise SystemExit('Each family-parent must occur in exactly one block')
payload={'protocol':'T3_B3_realworld_parent_blocks_v1','target_child_rows':a.target_child_rows,
 'family_count':6,'parents_per_family':642,'children_per_family':{f:sum(map(len,by_family[f].values())) for f in FAMILIES},
 'blocks_per_family':{f:sum(x['training_family']==f for x in index) for f in FAMILIES},
 'total_blocks':len(index),'parent_cluster_unit':'parent_dataset_id',
 'manifest_rows':len(block_rows),'plan_sha256':hashlib.sha256(a.out.read_bytes()).hexdigest()}
a.out.with_name('realworld_parent_block_plan.json').write_text(json.dumps(payload,indent=2)+'\n')
print('T3_REALWORLD_PARENT_BLOCK_PLAN_PASS',json.dumps(payload,sort_keys=True))
