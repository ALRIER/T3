#!/usr/bin/env python3
"""Combine independent source catalogs; deduplicate parent identities."""
import argparse,csv,json,hashlib
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('catalogs',nargs='+',type=Path)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--target-parents',type=int,default=642)
p.add_argument('--minimum-finance',type=int,default=200)
p.add_argument('--max-children-per-parent',type=int,default=3)
a=p.parse_args();all_rows=[];parent_group={};seen_children=set();source_totals={};child_counts={}
for path in a.catalogs:
    rows=list(csv.DictReader(path.open(newline='',encoding='utf-8-sig')))
    if not rows:raise SystemExit(f'Empty candidate catalog: {path}')
    if not {'parent_dataset_id','dataset_id','source_group','source_sector'}<=set(rows[0]):
        raise SystemExit(f'Incomplete parent schema: {path}')
    if rows[0]['source_group']=='uci':
        grouped={}
        for row in rows:grouped.setdefault(row['parent_dataset_id'],[]).append(row)
        child_counts.update({pid:len(children) for pid,children in grouped.items()})
        capped=[]
        for pid,children in grouped.items():
            children.sort(key=lambda r:(int(r.get('feature_index') or 0),r['dataset_id']))
            if len(children)>a.max_children_per_parent:
                pick=sorted({0,(len(children)-1)//2,len(children)-1})
                children=[children[i] for i in pick]
            for row in children:
                row['child_selection_rule']='first_middle_last_by_UCI_variable_order_max3'
                capped.append(row)
        rows=capped
    for row in rows:
        pid=row['parent_dataset_id'];group=row['source_group'];child=(pid,row['dataset_id'])
        if pid in parent_group and parent_group[pid]!=group:
            raise SystemExit(f'Parent ID collides across source inventories: {pid}')
        if child in seen_children:raise SystemExit(f'Duplicate parent-child identity: {child}')
        parent_group[pid]=group;seen_children.add(child);all_rows.append(row)
        source_totals[group]=source_totals.get(group,0)+1
parents={}
for row in all_rows:parents.setdefault(row['parent_dataset_id'],row['source_sector'])
finance={k for k,v in parents.items() if v.lower()=='finance'}
other=set(parents)-finance
if len(parents)<a.target_parents or len(finance)<a.minimum_finance or len(other)<a.target_parents-a.minimum_finance:
    raise SystemExit(f'BLOCKED: merged inventory has {len(parents)} parents ({len(finance)} finance, {len(other)} other); '
      f'requires >= {a.target_parents} total, >= {a.minimum_finance} finance, >= {a.target_parents-a.minimum_finance} other')
a.out.parent.mkdir(parents=True,exist_ok=True)
with a.out.open('w',newline='',encoding='utf-8') as f:
    fields=list(dict.fromkeys(k for row in all_rows for k in row))
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(all_rows)
h=hashlib.sha256(a.out.read_bytes()).hexdigest()
summary={'candidate_parent_count':len(parents),'candidate_child_count':len(all_rows),
 'finance_candidate_parent_count':len(finance),'other_candidate_parent_count':len(other),
 'source_child_rows':source_totals,'catalog_sha256':h,
 'uci_children_before_cap':sum(child_counts.values()),
 'uci_children_after_cap':sum(1 for r in all_rows if r['source_group']=='uci'),
 'max_uci_children_per_parent':a.max_children_per_parent,
 'sample_target':a.target_parents,'minimum_finance_parents':a.minimum_finance,
 'sample_selection':'fresh T3 profile and seed freeze after merge; no model outcomes read'}
a.out.with_suffix('.manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
print('T3_B3_REALWORLD_CATALOG_MERGE_PASS',json.dumps(summary,sort_keys=True))
