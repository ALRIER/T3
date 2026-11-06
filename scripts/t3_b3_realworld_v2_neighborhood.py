#!/usr/bin/env python3
"""Real-World V2 outcome-blind matched-scenario neighborhood transfer diagnostics.
No p-values: child series and overlapping neighborhood windows share parents.
Source is frozen empirical matching to the 241 Discovery-supported grid cells.
"""
import argparse,csv,gzip,json,sqlite3,collections,math
from pathlib import Path

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--input',required=True);p.add_argument('--grid',required=True)
 p.add_argument('--family',required=True);p.add_argument('--output',required=True)
 a=p.parse_args()
 rows=list(csv.DictReader(open(a.grid,newline='')))
 support={int(x['scenario_id']):x for x in rows if x['mechanism'] not in ('mixture_bimodal_near','mixture_bimodal_far')}
 if len(support)!=241:raise ValueError('Prospective 241 supported scenario grid changed')
 adjacent=collections.defaultdict(set)
 for sid,x in support.items():
  if sid==0:continue
  for axis,other in [('contamination','mad_scale'),('mad_scale','contamination')]:
   vals=sorted(set(float(z[axis]) for z in support.values()
     if z['mechanism']==x['mechanism'] and float(z[other])==float(x[other]) and int(z['scenario_id'])!=0))
   i=vals.index(float(x[axis]))
   for j in (i-1,i+1):
    if 0<=j<len(vals):
     for tid,y in support.items():
      if tid!=sid and y['mechanism']==x['mechanism'] and float(y[other])==float(x[other]) and float(y[axis])==vals[j]:
       adjacent[sid].add(tid)
 output=Path(a.output)
 if output.exists():raise ValueError('Refusing overwrite neighborhood output')
 output.mkdir(parents=True)
 db=sqlite3.connect(str(output/'scenario.sqlite'))
 db.execute('PRAGMA journal_mode=OFF');db.execute('PRAGMA synchronous=OFF')
 db.execute('CREATE TABLE e (candidate TEXT,n INTEGER,parent TEXT,seed INTEGER,scenario INTEGER,role TEXT,dst TEXT,scope TEXT,dm REAL,dq REAL,gm REAL,gq REAL)')
 files=sorted(Path(a.input).rglob('neighbor_*.csv.gz'))
 if not files:raise ValueError('No preserved Real-World matched-scenario effects')
 total=0;buffer=[]
 for path in files:
  with gzip.open(path,'rt',newline='') as f:
   rd=csv.DictReader(f)
   for r in rd:
    if r['source_family']!=a.family:raise ValueError('Contaminated source family in neighborhood file')
    sid=int(r['matched_scenario_id'])
    if sid not in support:raise ValueError('Matched scenario outside frozen Discovery support')
    buffer.append((r['candidate_id'],int(r['sample_n']),r['parent_dataset_id'],int(r['realworld_seed']),
      sid,r['benchmark_role'],r['evaluation_family'],r['transfer_scope'],
      float(r['mse_difference']),float(r['q95_difference']),float(r['mse_gain_pct']),float(r['q95_gain_pct'])))
    if len(buffer)==10000:
     db.executemany('INSERT INTO e VALUES ('+','.join('?'*12)+')',buffer);total+=len(buffer);buffer=[]
 if buffer:db.executemany('INSERT INTO e VALUES ('+','.join('?'*12)+')',buffer);total+=len(buffer)
 db.commit()
 # Unit of descriptive aggregation is still parent; repeated bootstrap seeds,
 # multiple empirical child variables, and depths cannot increase parent count.
 cur=db.execute('''SELECT candidate,n,parent,scenario,role,dst,scope,AVG(dm),AVG(dq),AVG(gm),AVG(gq)
 FROM e GROUP BY candidate,n,parent,scenario,role,dst,scope''')
 node=collections.defaultdict(list)
 for r in cur:
  k=(r[0],r[1],r[3],r[4],r[5],r[6])
  node[k].append(r[7:])
 records=[]
 for key,values in node.items():
  c,n,sid,role,dst,scope=key
  records.append({'candidate_id':c,'source_family':a.family,'sample_n':n,
   'matched_scenario_id':sid,'matched_mechanism':support[sid]['mechanism'],
   'benchmark_role':role,'evaluation_family':dst,'transfer_scope':scope,
   'independent_parent_coverage':len(values),
   'mse_gain_pct':sum(x[2] for x in values)/len(values),
   'q95_gain_pct':sum(x[3] for x in values)/len(values),
   'parent_joint_direction_fraction':sum(x[0]<0 and x[1]<0 for x in values)/len(values),
   'inference_status':'descriptive_only_not_independent_lookahead_or_BH'})
 nodes={tuple(r[k] for k in ('candidate_id','sample_n','matched_scenario_id','benchmark_role','evaluation_family','transfer_scope')):r for r in records}
 edges=[]
 for (cid,n,sid,role,dst,scope),v in nodes.items():
  for tid in sorted(adjacent[sid]):
   w=nodes.get((cid,n,tid,role,dst,scope))
   if w is None:continue
   if sid>tid:continue
   edges.append({'candidate_id':cid,'source_family':a.family,'sample_n':n,'evaluation_family':dst,
    'transfer_scope':scope,'benchmark_role':role,'scenario_a':sid,'scenario_b':tid,
    'mechanism':support[sid]['mechanism'],'a_independent_parents':v['independent_parent_coverage'],
    'b_independent_parents':w['independent_parent_coverage'],
    'both_scenarios_mean_improve_mse_q95':
      v['mse_gain_pct']>0 and v['q95_gain_pct']>0 and w['mse_gain_pct']>0 and w['q95_gain_pct']>0,
    'mse_gain_shift_pct':w['mse_gain_pct']-v['mse_gain_pct'],
    'q95_gain_shift_pct':w['q95_gain_pct']-v['q95_gain_pct'],
    'inference_status':'overlapping_observational_neighbor_profiles_descriptive_only'})
 def write(path,rows,fields):
  with gzip.open(path,'wt',newline='') as f:
   w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 write(output/'scenario_parent_coverage_descriptive.csv.gz',records,
   list(records[0]) if records else [])
 write(output/'adjacent_observed_scenario_transfer_descriptive.csv.gz',edges,
   list(edges[0]) if edges else [])
 (output/'neighborhood_scope.json').write_text(json.dumps({'protocol':'T3_B3_RW_V2_OUTCOME_BLIND_NEIGHBOR_DIAGNOSTIC',
  'source_family':a.family,'source_score_shards':len(files),'input_neighbor_effect_rows':total,
  'observed_matched_support_scenarios':241,'observed_neighbor_edges':len(edges),
  'matched_labels_not_actual_DGP':True,'parent_is_independent_unit':True,
  'no_neighbor_p_values':True,'no_causal_migration_claims':True},indent=2)+'\n')
 db.close();(output/'scenario.sqlite').unlink()
 print('REALWORLD_V2_NEIGHBOR_DESCRIPTIVE_PASS',a.family,len(files),len(records),len(edges),flush=True)
if __name__=='__main__':main()
