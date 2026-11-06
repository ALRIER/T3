#!/usr/bin/env python3
"""T3/B3 Real-World V2 parent-cluster and cross-scenario post-reduction inference.

Primary: independent parent_dataset_id; no training-seed W pooling.
Secondary: outcome-blind empirical destination families; separate BH family.
Matched-scenario adjacency: descriptive only (overlapping parents/windows).
"""
import argparse,csv,gzip,hashlib,json,math,sqlite3,collections
from pathlib import Path
import numpy as np
from scipy import stats

KEY=['source_family','candidate_id','engine','training_seed','sample_n',
 'transfer_scope','benchmark_role','benchmark']
METRICS=('mse','q95')
def die(s):raise ValueError(s)
def filehash(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for part in iter(lambda:f.read(1<<20),b''):h.update(part)
 return h.hexdigest()
def intervals(values):
 a=np.array(values,dtype=np.float64)
 if len(a)<5:die('Parent count below inferential threshold')
 m=float(a.mean());n=len(a)
 sd=float(a.std(ddof=1))
 if sd<=1e-14*max(abs(m),1.):
  return m,m,m,(2.**(-n) if m<0 else 1.)
 se=sd/math.sqrt(n);crit=float(stats.t.ppf(.975,n-1))
 return m,m-crit*se,m+crit*se,float(stats.t.cdf(m/se,n-1))
def calc(r,kind):
 vals_m=[x[0] for x in r];vals_q=[x[1] for x in r]
 gain_m=[x[2] for x in r];gain_q=[x[3] for x in r]
 m=intervals(vals_m);q=intervals(vals_q);gm=intervals(gain_m);gq=intervals(gain_q)
 return {'inference_scope':kind,'independent_parent_datasets':len(r),
 'mse_difference':m[0],'mse_ci_lower':m[1],'mse_ci_upper':m[2],'mse_p':m[3],
 'q95_difference':q[0],'q95_ci_lower':q[1],'q95_ci_upper':q[2],'q95_p':q[3],
 'mse_gain_pct':gm[0],'mse_gain_pct_ci_lower':gm[1],'mse_gain_pct_ci_upper':gm[2],
 'q95_gain_pct':gq[0],'q95_gain_pct_ci_lower':gq[1],'q95_gain_pct_ci_upper':gq[2],
 'parent_positive_mse_fraction':sum(x<0 for x in vals_m)/len(r),
 'parent_positive_q95_fraction':sum(x<0 for x in vals_q)/len(r)}
def family(a):
 folder=Path(a.input)
 files=sorted(folder.rglob('parent_*.csv.gz'))
 if not files:die('Missing Real-World individual W parent effects')
 out=Path(a.output)
 if out.exists():die('Output exists and cannot be overwritten')
 out.mkdir(parents=True)
 db=sqlite3.connect(str(out/'internal.sqlite'))
 db.execute('PRAGMA journal_mode=OFF');db.execute('PRAGMA synchronous=OFF')
 db.execute('CREATE TABLE d (source TEXT,cid TEXT,engine TEXT,train INTEGER,n INTEGER,seed INTEGER,parent TEXT,scope TEXT,dst TEXT,refrole TEXT,benchmark TEXT,dm REAL,dq REAL,gm REAL,gq REAL,children INTEGER)')
 cols=['source_family','candidate_id','engine','training_seed','sample_n','realworld_seed',
       'parent_dataset_id','transfer_scope','evaluation_family','benchmark_role','benchmark',
       'mse_difference','q95_difference','mse_gain_pct','q95_gain_pct','n_children']
 seen=set();batch=[];nrows=0;source_sha=[]
 for path in files:
  mp=path.with_suffix('.manifest.json')
  if not mp.exists():die('Missing per-source SHA manifest: '+str(path))
  m=json.loads(mp.read_text())
  if m['primary_reduced_sha256']!=filehash(path):die('Reduced data differs from immutable manifest')
  if m['source_family']!=a.family:die('Cross-family archive contamination')
  key=(m['source_family'],m['sample_n'],m['realworld_seed'],m['raw_score_sha256'])
  if key in seen:die('Original raw score shard repeated')
  seen.add(key)
  source_sha.append({'reduced_file':path.name,'raw_sha256':m['raw_score_sha256'],
                     'parent_score_sha256':m['primary_reduced_sha256']})
  with gzip.open(path,'rt',newline='') as f:
   rd=csv.DictReader(f)
   if not set(cols).issubset(rd.fieldnames):die('Missing individual parent effect schema')
   for row in rd:
    if row['source_family']!=a.family:die('Unexpected family in block')
    batch.append(tuple(row[c] for c in cols))
    if len(batch)==10000:
     db.executemany('INSERT INTO d VALUES ('+','.join('?'*16)+')',batch)
     batch=[];nrows+=10000
 if batch:db.executemany('INSERT INTO d VALUES ('+','.join('?'*16)+')',batch);nrows+=len(batch)
 db.commit()
 # Three-stage average prevents children or repeated seeds being used as
 # independent parents: (a) child-weighted profile mean within parent/seed,
 # (b) equal average over ten independent seed summaries within parent,
 # (c) t-inference across *different* parent dataset IDs only.
 db.executescript("""
 CREATE INDEX d_idx ON d(source,cid,n,scope,refrole,parent,seed);
 CREATE TABLE parent_seed AS SELECT source,cid,engine,train,n,parent,scope,refrole,
 seed,SUM(dm*children)/SUM(children) dm,SUM(dq*children)/SUM(children) dq,
 SUM(gm*children)/SUM(children) gm,SUM(gq*children)/SUM(children) gq
 FROM d GROUP BY source,cid,engine,train,n,parent,scope,refrole,seed;
 CREATE TABLE parents AS SELECT source,cid,engine,train,n,parent,scope,refrole,
 COUNT(DISTINCT seed) nseed,AVG(dm) dm,AVG(dq) dq,AVG(gm) gm,AVG(gq) gq
 FROM parent_seed GROUP BY source,cid,engine,train,n,parent,scope,refrole;
 CREATE INDEX parent_idx ON parents(source,cid,n,scope,refrole);
 """)
 q=db.execute('SELECT source,cid,engine,train,n,scope,refrole,parent,nseed,dm,dq,gm,gq FROM parents ORDER BY source,cid,engine,train,n,scope,refrole,parent')
 results=[];key=None;vals=[]
 def flush():
  if not vals:return
  if any(v[0]!=10 for v in vals):die('Missing evaluation seeds 30-39 for independent parent '+str(key))
  if len(vals)>=5:
   stat=calc([v[1:] for v in vals],'independent_parent_generalization')
   results.append(dict(zip(KEY,[*key[:7],'frozen_discovery_scenario_specific' if key[6]=='own' else 'mean']),**stat))
 for row in q:
  k=tuple(row[:7])
  if key is not None and k!=key:flush();vals=[]
  key=k;vals.append(tuple(row[8:]))
 flush()
 # Outcome-blind destinations are secondary hypotheses. A parent is still
 # ONE independent unit even if several children fall in the same destination.
 secondary={}
 cur=db.execute("""SELECT source,cid,engine,train,n,parent,scope,dst,refrole,
  COUNT(DISTINCT seed) nseed,
  SUM(dm*children)/SUM(children) dm,SUM(dq*children)/SUM(children) dq,
  SUM(gm*children)/SUM(children) gm,SUM(gq*children)/SUM(children) gq
  FROM d GROUP BY source,cid,engine,train,n,parent,scope,dst,refrole""")
 # Within each destination, raw rows can include 10 seeds; only parent level
 # is used for inference. Seed-presence is separately validated.
 for row in cur:
  k=(*row[:5],row[6],row[8],row[7]);secondary.setdefault(k,[]).append((row[5],*row[10:]))
 secondary_results=[]
 for k,items in secondary.items():
  if len(items)<5:continue
  if len({v[0] for v in items})!=len(items):die('Repeated independent parent in secondary destination')
  stat=calc([v[1:] for v in items],'empirical_family_subgroup_secondary')
  result=dict(zip(['source_family','candidate_id','engine','training_seed','sample_n',
    'transfer_scope','benchmark_role','evaluation_family'],k))
  result['benchmark']='frozen_discovery_scenario_specific' if result['benchmark_role']=='own' else 'mean'
  secondary_results.append({**result,**stat})
 def write(rows,p):
  if not rows:die('No inferential panels produced')
  with gzip.open(p,'wt',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 write(results,out/'primary_parent_inference_unadjusted.csv.gz')
 write(secondary_results,out/'secondary_family_transfer_unadjusted.csv.gz')
 (out/'family_provenance.json').write_text(json.dumps({'protocol':'T3_B3_RW_V2_PARENT_INDEPENDENCE',
  'source_family':a.family,'original_score_shards':len(files),'input_sha256':source_sha,
  'source_score_rows':nrows,'primary_hypothesis_pairs':len(results),
  'secondary_hypothesis_pairs':len(secondary_results),
  'source_training_seeds':list(range(10)),'evaluation_seeds':list(range(30,40)),
  'primary_unit':'parent_dataset_id','target':'child_depth_full_sample_mean_proxy',
  'single_W_per_training_seed':True},indent=2)+'\n')
 db.close();(out/'internal.sqlite').unlink()
 print('REALWORLD_V2_PARENT_FAMILY_PASS',a.family,len(files),len(results),len(secondary_results),flush=True)
def global_fdr(a):
 folders=sorted(Path(a.input).rglob('family_provenance.json'))
 if len(folders)!=6:die('Exactly six destination/source family analyses are mandatory')
 all_primary=[];all_secondary=[];ids=set()
 for meta in folders:
  m=json.loads(meta.read_text())
  if m['source_family'] in ids:die('Duplicate source family inference')
  ids.add(m['source_family'])
  for filename,arr in [('primary_parent_inference_unadjusted.csv.gz',all_primary),
                       ('secondary_family_transfer_unadjusted.csv.gz',all_secondary)]:
   with gzip.open(meta.parent/filename,'rt',newline='') as f:arr.extend(csv.DictReader(f))
 if ids!={'normal','lognormal','weibull','invgauss','exgaussian','exwald'}:die('Incomplete source family coverage')
 out=Path(a.output)
 if out.exists():die('Refuse to overwrite global inference')
 out.mkdir(parents=True)
 def BH(ps):
  p=np.array(ps,dtype=np.float64)
  order=np.argsort(p,kind='stable');n=len(p);q=np.empty(n)
  q[order]=np.minimum.accumulate((p[order]*n/np.arange(1,n+1))[::-1])[::-1]
  return np.minimum(q,1)
 def finalize(rows,filename):
  q=BH([float(r[m+'_p']) for r in rows for m in METRICS])
  tiers=collections.Counter()
  for i,r in enumerate(rows):
   for j,m in enumerate(METRICS):r[m+'_global_bh_q']=float(q[i*2+j])
   m=float(r['mse_ci_upper'])<0 and r['mse_global_bh_q']<=.05
   q95=float(r['q95_ci_upper'])<0 and r['q95_global_bh_q']<=.05
   mci=float(r['mse_ci_upper'])<0;qci=float(r['q95_ci_upper'])<0
   tier='tier1_joint_mse_q95_bh_fdr' if m and q95 else 'tier2_joint_ci_only' if mci and qci else 'tier3_mse_bh_only' if m else 'tier3_q95_bh_only' if q95 else 'tier4_retained_no_bh_win'
   r.update(tier1_joint_bh_fdr=m and q95,tier2_joint_ci_only=(mci and qci and not(m and q95)),
    tier3_mse_bh_only=m and not(mci and qci),tier3_q95_bh_only=q95 and not(mci and qci),
    highest_tier=tier,secondary_mse_worse=float(r['mse_difference'])>0,
    secondary_q95_worse=float(r['q95_difference'])>0)
   tiers[(r['benchmark_role'],r['transfer_scope'],tier)]+=1
  with gzip.open(out/filename,'wt',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  return tiers
 p1=finalize(all_primary,'primary_parent_BH_taxonomy.csv.gz')
 p2=finalize(all_secondary,'secondary_family_transfer_BH_taxonomy.csv.gz')
 with (out/'tier_counts.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['panel','benchmark_role','transfer_scope','highest_tier','contrasts'])
  for label,coll in [('primary_parent',p1),('secondary_family',p2)]:
   for (b,s,t),v in sorted(coll.items()):w.writerow([label,b,s,t,v])
 (out/'scientific_provenance.json').write_text(json.dumps({
  'protocol':'T3_B3_RW_V2_PRIMARY_PARENT_AND_SECONDARY_FAMILY',
  'alpha':0.05,'bh_scope':'two separate global BH panels: parent primary and destination secondary',
  'primary_hypotheses':2*len(all_primary),'secondary_hypotheses':2*len(all_secondary),
  'original_candidate_count':720,'training_seeds':list(range(10)),
  'realworld_seeds':list(range(30,40)),'parent_independence':True,
  'migration_neighborhood_status':'descriptive only, no overlapping-neighborhood BH claims',
  'realworld_target':'child-depth empirical full-sample mean proxy, not known population truth'},indent=2)+'\n')
 print('REALWORLD_V2_GLOBAL_PARENT_BH_PASS',len(all_primary)*2,len(all_secondary)*2,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 sub=p.add_subparsers(dest='mode',required=True)
 s=sub.add_parser('family');s.add_argument('--input',required=True);s.add_argument('--family',required=True);s.add_argument('--output',required=True)
 s=sub.add_parser('global');s.add_argument('--input',required=True);s.add_argument('--output',required=True)
 args=p.parse_args()
 {'family':family,'global':global_fdr}[args.mode](args)
