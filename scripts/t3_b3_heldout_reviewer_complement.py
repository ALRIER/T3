#!/usr/bin/env python3
"""T3 Held-out reviewer audit v1. Descriptive robustness only; never new scoring.

Inputs: the immutable 18 seedwise recovery blocks + their completed globally
BH-adjusted inference. Do not use supplementary diagnostics to select new
confirmatory hypotheses. A cell's 10 evaluation seeds are the paired units.
"""
import argparse,collections,csv,gzip,hashlib,itertools,json,math,statistics
from pathlib import Path

FAMILIES=('normal','lognormal','weibull','invgauss','exgaussian','exwald')
SIZES=(200,1000,3000)
EVAL_SEEDS=list(range(10,20))
N_SCENARIOS=241
N_CANDIDATES_PER_BLOCK=240
N_ROWS_PER_BLOCK=N_SCENARIOS*N_CANDIDATES_PER_BLOCK*2
TCRIT9=2.3060041350333704  # two-sided 95%, df=8
PRIMARY_RUN='42045005791'
GROUPS=('candidate_id','evaluation_family','benchmark_role')
CELL_FIELDS=('candidate_id','source_family','evaluation_family','training_seed',
 'sample_n','scenario_id','benchmark_role','benchmark','mechanism','band',
 'contamination','mad_scale','scope','highest_tier',
 'tier1_joint_FDR','tier2_joint_CI','tier3_mse_FDR','tier3_q95_FDR',
 'mse_q_BH','q95_q_BH','mse_gain_pct','mse_gain_ci_lower','mse_gain_ci_upper',
 'q95_gain_pct','q95_gain_ci_lower','q95_gain_ci_upper',
 'mse_fraction_seeds_improved','q95_fraction_seeds_improved',
 'mse_loo_all_means_improved','q95_loo_all_means_improved',
 'mse_loo_worst_ci_upper','q95_loo_worst_ci_upper',
 'mse_min_diff','mse_max_diff','q95_min_diff','q95_max_diff',
 'mse_observed_worsening','q95_observed_worsening',
 'mse_ci95_supported_worsening','q95_ci95_supported_worsening',
 'single_metric_with_secondary_worsening',
 'joint_all_10_seeds_negative','joint_leave_one_out_mean_stable')

def fail(message):
 raise ValueError(message)

def sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def reader(path):
 return csv.DictReader(gzip.open(path,'rt',newline=''))

def finite(x,label):
 try:y=float(x)
 except (ValueError,TypeError):fail('Non-numeric '+label+': '+str(x))
 if not math.isfinite(y):fail('Non-finite '+label+': '+str(x))
 return y

def boolean(x):
 if x in ('True','TRUE','true','1'):return True
 if x in ('False','FALSE','false','0'):return False
 fail('Invalid Boolean: '+str(x))

def series(value,name):
 parts=value.split(';')
 if len(parts)!=10:fail(name+' has '+str(len(parts))+' values, expected ten evaluation seeds')
 return [finite(x,name) for x in parts]

def loo(v):
 """Only sensitivity; deliberately no new hypothesis tests or adjusted p."""
 if len(v)!=10:fail('Expected ten paired evaluation units')
 total=sum(v);ss=sum(x*x for x in v);upper=[];means=[]
 for x in v:
  mu=(total-x)/9
  var=max(0.,(ss-x*x-9*mu*mu)/8)
  means.append(mu)
  upper.append(mu+TCRIT9*math.sqrt(var/9))
 return sum(x<0 for x in v)/10,all(x<0 for x in means),max(upper)

def grid_read(path):
 grid={}
 for r in csv.DictReader(path.open(newline='')):
  i=int(r['scenario_id'])
  if i in grid:fail('Repeated predeclared scenario '+str(i))
  grid[i]=dict(mechanism=r['mechanism'],band=r['band'],
   contamination=finite(r['contamination'],'contamination'),
   mad_scale=finite(r['mad_scale'],'mad_scale'))
 if len(grid)!=321 or set(grid)!=set(range(321)):fail('Expected the original prospectively frozen 321-cell design')
 if sum(r['mechanism'] not in ('mixture_bimodal_near','mixture_bimodal_far') for r in grid.values())!=241:
  fail('Incorrect Held-out scenario partition')
 support={i:r for i,r in grid.items() if r['mechanism'] not in ('mixture_bimodal_near','mixture_bimodal_far')}
 edges={i:set() for i in support}
 for m in sorted({x['mechanism'] for x in support.values()}):
  if m=='clean':continue
  ids=[i for i in support if support[i]['mechanism']==m]
  levels_c=sorted({support[i]['contamination'] for i in ids})
  levels_m=sorted({support[i]['mad_scale'] for i in ids})
  ix_c={x:i for i,x in enumerate(levels_c)}
  ix_m={x:i for i,x in enumerate(levels_m)}
  for i,j in itertools.combinations(ids,2):
   a,b=support[i],support[j]
   c=(a['contamination']==b['contamination'] and abs(ix_m[a['mad_scale']]-ix_m[b['mad_scale']])==1)
   d=(a['mad_scale']==b['mad_scale'] and abs(ix_c[a['contamination']]-ix_c[b['contamination']])==1)
   if c or d:edges[i].add(j);edges[j].add(i)
 if not any(edges.values()):fail('No outcome-blind within-support scenario neighbors')
 return support,edges

def parse_block(path):
 m=path.parent.name
 if m.startswith('t3-heldout-individual-') and '-run' in m:
  m=m.split('-run',1)[0].removeprefix('t3-heldout-individual-')
 if '-n' not in m:fail('Invalid recovered block directory: '+str(path))
 family,n=m.rsplit('-n',1)
 if family not in FAMILIES or not n.isdigit() or int(n) not in SIZES:fail('Unexpected held-out block: '+m)
 return family,int(n)

def matching_key(row):
 return (row['candidate_id'],int(row['scenario_id']),row['benchmark_role'],row['benchmark'])

def audit_block(pair_path,tax_path,infer_path,grid,edges,cell_writer,neigh_writer,counts,provenance):
 family,n=parse_block(pair_path)
 meta_path=pair_path.parent/'manifest.json'
 meta=json.loads(meta_path.read_text())
 if meta.get('family')!=family or meta.get('n')!=n or meta.get('smoke') or meta.get('metric_rows')!=2*N_ROWS_PER_BLOCK or meta.get('eval_seeds')!=EVAL_SEEDS or len(meta.get('original_sources',[]))!=20:
  fail('Original recovery manifest contract failed for '+str(pair_path))
 reg=meta['registry_sha256'];bm=meta['benchmark_map_sha256']
 provenance['registry_sha'].add(reg);provenance['benchmark_sha'].add(bm)
 provenance['block_hashes'].append({'family':family,'sample_n':n,'paired_seed_sha256':sha256(pair_path),
  'taxonomy_sha256':sha256(tax_path),'inference_sha256':sha256(infer_path),
  'manifest_sha256':sha256(meta_path),'original_scoring_shards':len(meta['original_sources'])})
 seen=set();scope_count=collections.Counter();rows=[];local_flags={};benchmarks={}
 with gzip.open(pair_path,'rt',newline='') as p,gzip.open(tax_path,'rt',newline='') as t,gzip.open(infer_path,'rt',newline='') as i:
  pr=csv.DictReader(p);tr=csv.DictReader(t);ir=csv.DictReader(i)
  for pair,tax in itertools.zip_longest(pr,tr):
   if pair is None or tax is None:fail('Pair/taxonomy line-count mismatch '+family)
   key=matching_key(pair)
   if matching_key(tax)!=key:fail('Paired/taxonomy W, scenario, or reference misalignment '+str(key))
   if key in seen:fail('Duplicate individual candidate/scene/reference '+str(key))
   seen.add(key)
   im=next(ir,None);iq=next(ir,None)
   if im is None or iq is None or im['metric']!='mse' or iq['metric']!='q95' or matching_key(im)!=key or matching_key(iq)!=key:
    fail('BH-adjusted metric lines do not align with taxonomy: '+str(key))
   if tax['evaluation_family']!=family or int(tax['sample_n'])!=n:fail('Wrong evaluation family or n')
   cid,sid,role,benchmark=key
   if sid not in grid or role not in ('mean','own'):fail('Out-of-support scenario or benchmark role')
   source=tax['source_family'];scope='within_family_independent_replication' if source==family else 'cross_family_transfer'
   seed=int(tax['training_seed'])
   if source not in FAMILIES or seed not in range(10) or int(cid.split('|')[2][4:])!=seed or cid.split('|')[0]!=source:
    fail('Frozen training seed or source identity inconsistent')
   if pair['eval_seeds']!=';'.join(map(str,EVAL_SEEDS)):fail('Unexpected paired evaluation seeds '+str(key))
   dm=series(pair['differences_mse'],'differences_mse')
   dq=series(pair['differences_q95'],'differences_q95')
   mm=sum(dm)/10;mq=sum(dq)/10
   if abs(mm-finite(im['difference'],'MSE difference'))>1e-9*max(1.,abs(mm)) or abs(mq-finite(iq['difference'],'Q95 difference'))>1e-9*max(1.,abs(mq)):
    fail('Independent raw paired differences disagree with BH inference '+str(key))
   if abs(finite(im['q_value_global'],'BH MSE')-finite(tax['mse_q_BH'],'taxonomy BH MSE'))>1e-12 or abs(finite(iq['q_value_global'],'BH Q95')-finite(tax['q95_q_BH'],'taxonomy BH Q95'))>1e-12:
    fail('Global BH values disagree with winner taxonomy '+str(key))
   wm=finite(im['ci_upper'],'MSE CI upper')<0;wq=finite(iq['ci_upper'],'Q95 CI upper')<0
   fm=wm and finite(im['q_value_global'],'BH MSE')<=.05
   fq=wq and finite(iq['q_value_global'],'BH Q95')<=.05
   joint=fm and fq;ci_joint=wm and wq and not joint
   m_only=fm and not(joint or ci_joint);q_only=fq and not(joint or ci_joint)
   expected='tier1_joint_FDR' if joint else 'tier2_joint_CI' if ci_joint else 'tier3_mse_FDR' if m_only else 'tier3_q95_FDR' if q_only else 'tier4_no_supported_win'
   if tax['highest_tier']!=expected:fail('Stored taxonomy contradicts original global BH inference '+str(key))
   sm,stable_m,loo_m=loo(dm);sq,stable_q,loo_q=loo(dq)
   source_grid=grid[sid]
   harms=(finite(im['ci_lower'],'MSE CI lower')>0,finite(iq['ci_lower'],'Q95 CI lower')>0)
   secondary=(m_only and mq>0) or (q_only and mm>0)
   row=dict(candidate_id=cid,source_family=source,evaluation_family=family,training_seed=seed,
     sample_n=n,scenario_id=sid,benchmark_role=role,benchmark=benchmark,
     mechanism=source_grid['mechanism'],band=source_grid['band'],
     contamination=source_grid['contamination'],mad_scale=source_grid['mad_scale'],
     scope=scope,highest_tier=expected,tier1_joint_FDR=joint,tier2_joint_CI=ci_joint,
     tier3_mse_FDR=m_only,tier3_q95_FDR=q_only,mse_q_BH=tax['mse_q_BH'],
     q95_q_BH=tax['q95_q_BH'],mse_gain_pct=im['gain_pct'],
     mse_gain_ci_lower=im['gain_pct_lower'],mse_gain_ci_upper=im['gain_pct_upper'],
     q95_gain_pct=iq['gain_pct'],q95_gain_ci_lower=iq['gain_pct_lower'],q95_gain_ci_upper=iq['gain_pct_upper'],
     mse_fraction_seeds_improved=sm,q95_fraction_seeds_improved=sq,
     mse_loo_all_means_improved=stable_m,q95_loo_all_means_improved=stable_q,
     mse_loo_worst_ci_upper=loo_m,q95_loo_worst_ci_upper=loo_q,
     mse_min_diff=min(dm),mse_max_diff=max(dm),q95_min_diff=min(dq),q95_max_diff=max(dq),
     mse_observed_worsening=mm>0,q95_observed_worsening=mq>0,
     mse_ci95_supported_worsening=harms[0],q95_ci95_supported_worsening=harms[1],
     single_metric_with_secondary_worsening=secondary,
     joint_all_10_seeds_negative=sm==1 and sq==1,
     joint_leave_one_out_mean_stable=stable_m and stable_q)
   cell_writer.writerow(row);rows.append((cid,sid,role,expected,source,source_grid,secondary,harms,sm,sq,stable_m,stable_q))
   local_flags[(cid,sid,role)]=joint
   benchmarks[(cid,sid)].add(role) if (cid,sid) in benchmarks else benchmarks.setdefault((cid,sid),{role})
   acc=counts[(cid,family,n,role,scope)]
   acc['scenarios']+=1;acc[expected]+=1
   acc['secondary_observed_worse']+=int(secondary)
   acc['secondary_ci_worse']+=int((m_only and harms[1]) or (q_only and harms[0]))
   acc['both_metrics_all_10_seeds_negative']+=int(sm==1 and sq==1)
   acc['both_metrics_loo_mean_stable']+=int(stable_m and stable_q)
   acc['mechanism_'+source_grid['mechanism']+'_tier1']+=int(joint)
   acc['band_'+source_grid['band']+'_tier1']+=int(joint)
   scope_count[scope]+=1
  if next(ir,None) is not None:fail('Unexpected trailing inference metrics in '+family)
 if len(seen)!=N_ROWS_PER_BLOCK or len({(x[0],x[1]) for x in seen})!=N_CANDIDATES_PER_BLOCK*N_SCENARIOS:
  fail('Candidate x 241 scenario x two-reference panel incomplete '+family)
 if any(v!={'own','mean'} for v in benchmarks.values()):fail('Both original benchmark contrasts required')
 if scope_count['within_family_independent_replication']!=40*241*2 or scope_count['cross_family_transfer']!=200*241*2:
  fail('Missing individual within-family or cross-family hypotheses')
 for cid,sid,role,tier,source,sc,secondary,harms,sm,sq,stable_m,stable_q in rows:
  neighbor_ids=edges[sid];p=[local_flags[(cid,ns,role)] for ns in neighbor_ids]
  ratio=sum(p)/len(p) if p else ''
  neigh_writer.writerow({'candidate_id':cid,'evaluation_family':family,'sample_n':n,
    'scenario_id':sid,'benchmark_role':role,'scenario_neighbor_count':len(p),
    'neighbor_tier1_support_fraction':ratio,
    'own_tier1_FDR':local_flags[(cid,sid,role)],
    'neighbor_definition':'same mechanism; next rate at fixed MAD or next MAD at fixed rate; observed support only'})
  if p:
   acc=counts[(cid,family,n,role,'within_family_independent_replication' if source==family else 'cross_family_transfer')]
   acc['with_observed_grid_neighbors']+=1
   acc['tier1_with_any_neighbor_tier1']+=int(local_flags[(cid,sid,role)] and any(p))
   acc['tier1_with_all_neighbor_tier1']+=int(local_flags[(cid,sid,role)] and all(p))
  acc=counts[(cid,family,n,role,'within_family_independent_replication' if source==family else 'cross_family_transfer')]
  acc['tier1_own_and_mean']+=int(local_flags[(cid,sid,'own')] and local_flags[(cid,sid,'mean')])
 return {'family':family,'n':n,'cells':len(seen),'source_sha256':sha256(pair_path),'tax_sha256':sha256(tax_path)}

def write_summary(path,counts):
 fieldnames=['candidate_id','evaluation_family','sample_n','benchmark_role','scope',
  'tested_scenarios','tier1_joint_BH_FDR','tier2_joint_CI_only','tier3_MSE_only_BH','tier3_Q95_only_BH',
  'tier4_no_supported_win','single_metric_secondary_observed_worse',
  'single_metric_secondary_ci95_supported_worse','both_metrics_all_10_seeds_negative',
  'both_metrics_loo_mean_stable','tier1_own_and_mean','observed_grid_neighbor_scenarios',
  'tier1_with_any_local_neighbor_tier1','tier1_with_all_local_neighbors_tier1',
  'tier1_fraction','tier2_fraction','tier3_fraction']
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fieldnames);w.writeheader()
  for (cid,fam,n,role,scope),v in sorted(counts.items()):
   total=v['scenarios']
   if total!=241:fail('Every candidate x evaluation family x reference must have 241 scenarios')
   t1=v['tier1_joint_FDR'];t2=v['tier2_joint_CI'];t3m=v['tier3_mse_FDR'];t3q=v['tier3_q95_FDR'];t4=v['tier4_no_supported_win']
   if t1+t2+t3m+t3q+t4!=total:fail('Taxonomy categories must partition 241 scenarios')
   w.writerow(dict(candidate_id=cid,evaluation_family=fam,sample_n=n,benchmark_role=role,scope=scope,
    tested_scenarios=total,tier1_joint_BH_FDR=t1,tier2_joint_CI_only=t2,tier3_MSE_only_BH=t3m,
    tier3_Q95_only_BH=t3q,tier4_no_supported_win=t4,
    single_metric_secondary_observed_worse=v['secondary_observed_worse'],
    single_metric_secondary_ci95_supported_worse=v['secondary_ci_worse'],
    both_metrics_all_10_seeds_negative=v['both_metrics_all_10_seeds_negative'],
    both_metrics_loo_mean_stable=v['both_metrics_loo_mean_stable'],tier1_own_and_mean=v['tier1_own_and_mean'],
    observed_grid_neighbor_scenarios=v['with_observed_grid_neighbors'],
    tier1_with_any_local_neighbor_tier1=v['tier1_with_any_neighbor_tier1'],
    tier1_with_all_local_neighbors_tier1=v['tier1_with_all_neighbor_tier1'],
    tier1_fraction=t1/total,tier2_fraction=t2/total,tier3_fraction=(t3m+t3q)/total))

def generalize(path,counts):
 aggregated=collections.defaultdict(lambda:collections.Counter())
 for (cid,fam,n,role,scope),v in counts.items():
  a=aggregated[(cid,role,n)]
  a['families_checked']+=1
  a['families_with_joint_BH_win']+=int(v['tier1_joint_FDR']>0)
  a['families_with_joint_BH_win_on_10pct_scenarios']+=int(v['tier1_joint_FDR']>=25)
  a['families_with_any_single_metric_BH_win']+=int(v['tier3_mse_FDR']+v['tier3_q95_FDR']>0)
  a['scenario_comparisons']+=v['scenarios'];a['tier1_scenarios']+=v['tier1_joint_FDR']
  a['tier2_only_scenarios']+=v['tier2_joint_CI'];a['secondary_worsening']+=v['secondary_observed_worse']
  if scope=='within_family_independent_replication':
   a['within_family_joint_wins']+=v['tier1_joint_FDR']
  else:
   a['cross_family_joint_wins']+=v['tier1_joint_FDR']
   a['cross_families_with_joint_win']+=int(v['tier1_joint_FDR']>0)
 with path.open('w',newline='') as f:
  field=['candidate_id','benchmark_role','sample_n','families_evaluated','families_with_any_joint_FDR_win',
   'families_with_joint_win_in_at_least_10pct_scenarios','cross_families_with_any_joint_FDR_win',
   'within_family_joint_win_scenarios','cross_family_joint_win_scenarios',
   'total_joint_FDR_win_scenarios','total_joint_CI_only_scenarios',
   'single_metric_secondary_observed_worsening','total_scenario_contrasts',
   'generalization_label']
  w=csv.DictWriter(f,fieldnames=field);w.writeheader()
  for (cid,role,n),a in sorted(aggregated.items()):
   if a['families_checked']!=6 or a['scenario_comparisons']!=6*241:
    fail('Six-family score support missing for '+cid)
   cross=a['cross_families_with_joint_win']
   label='descriptive_broad_cross_family' if cross>=4 else 'descriptive_some_cross_family' if cross>=1 else 'no_cross_family_joint_BH_win'
   w.writerow(dict(candidate_id=cid,benchmark_role=role,sample_n=n,
    families_evaluated=6,families_with_any_joint_FDR_win=a['families_with_joint_BH_win'],
    families_with_joint_win_in_at_least_10pct_scenarios=a['families_with_joint_BH_win_on_10pct_scenarios'],
    cross_families_with_any_joint_FDR_win=cross,
    within_family_joint_win_scenarios=a['within_family_joint_wins'],
    cross_family_joint_win_scenarios=a['cross_family_joint_wins'],
    total_joint_FDR_win_scenarios=a['tier1_scenarios'],
    total_joint_CI_only_scenarios=a['tier2_only_scenarios'],
    single_metric_secondary_observed_worsening=a['secondary_worsening'],
    total_scenario_contrasts=a['scenario_comparisons'],generalization_label=label))
 if len(aggregated)!=720*2:fail('Expected 720 candidate x 2 reference generalization rows')

def main(a):
 grid,edges=grid_read(Path(a.grid))
 blocks=list(Path(a.blocks).rglob('paired_seed_differences.csv.gz'))
 taxonomy=list(Path(a.final).rglob('individual_winner_taxonomy.csv.gz'))
 inference=list(Path(a.final).rglob('individual_candidate_inference.csv.gz'))
 if len(blocks)!=18 or len(taxonomy)!=18 or len(inference)!=18:
  fail('Expected 18 paired-seed, 18 BH taxonomy, 18 adjusted-inference inputs')
 paired={parse_block(f):f for f in blocks};tax={parse_block(f):f for f in taxonomy};inf={parse_block(f):f for f in inference}
 expected={(f,n) for f in FAMILIES for n in SIZES}
 if set(paired)!=expected or set(tax)!=expected or set(inf)!=expected:fail('18-block family/n coverage mismatch')
 global_manifest=next(iter(Path(a.final).rglob('global_panel_manifest.json')),None)
 if global_manifest is None:fail('Original global-BH manifest missing')
 previous=json.loads(global_manifest.read_text())
 if previous.get('hypotheses_BH')!=4164480 or previous.get('taxonomy_rows')!=2082240 or previous.get('blocks')!=18:
  fail('Incorrect original full-panel multiplicity or taxonomy')
 output=Path(a.output)
 output.mkdir(parents=True,exist_ok=False)
 counts=collections.defaultdict(collections.Counter)
 provenance={'registry_sha':set(),'benchmark_sha':set(),'block_hashes':[]}
 block_report=[]
 with gzip.open(output/'reviewer_full_cell_audit.csv.gz','wt',newline='') as o,gzip.open(output/'observed_local_neighbor_consistency.csv.gz','wt',newline='') as ns:
  writer=csv.DictWriter(o,fieldnames=CELL_FIELDS);writer.writeheader()
  neighbor_fields=['candidate_id','evaluation_family','sample_n','scenario_id','benchmark_role',
   'scenario_neighbor_count','neighbor_tier1_support_fraction','own_tier1_FDR','neighbor_definition']
  nw=csv.DictWriter(ns,fieldnames=neighbor_fields);nw.writeheader()
  for index,(family,n) in enumerate(sorted(expected),1):
   report=audit_block(paired[(family,n)],tax[(family,n)],inf[(family,n)],
    grid,edges,writer,nw,counts,provenance)
   block_report.append(report)
   print('HELDOUT_REVIEWER_BLOCK_PASS',index,'/18',family,n,report['cells'],flush=True)
 if len(provenance['registry_sha'])!=1 or len(provenance['benchmark_sha'])!=1 or next(iter(provenance['registry_sha']))!=previous['registry_sha256'] or next(iter(provenance['benchmark_sha']))!=previous['benchmark_map_sha256']:
  fail('Recovery run and reviewer job use different immutable Discovery or benchmark sources')
 if len(counts)!=720*6*2:fail('Candidate x six evaluation families x two references incomplete')
 write_summary(output/'reviewer_candidate_family_summary.csv',counts)
 generalize(output/'reviewer_candidate_cross_family_generalization.csv',counts)
 with (output/'outcome_blind_scenario_adjacency.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['scenario_id','neighbor_scenario_id','mechanism','contamination','mad_scale'])
  for sid,neighbors in sorted(edges.items()):
   for v in sorted(neighbors):w.writerow([sid,v,grid[sid]['mechanism'],grid[sid]['contamination'],grid[sid]['mad_scale']])
 report={'protocol':'T3_B3_HELDOUT_REVIEWER_COMPLEMENT_V1',
  'source_recovery_run_id':PRIMARY_RUN,'stage':'heldout','source_inference_manifest_sha256':sha256(global_manifest),
  'distinct_W_candidates':720,'evaluation_seeds':EVAL_SEEDS,'source_scoring_reexecuted':False,
  'source_Discovery_training_reexecuted':False,'original_BH_hypotheses':4164480,
  'new_p_values_calculated':False,'new_confirmatory_claims':False,
  'independent_generalization_to_stress_only_mechanisms_claimed':False,
  'supplement_scope':'Post-hoc sensitivity and descriptive generalization within observed Held-out support',
  'neighbors':'Frozen same-mechanism adjacent contamination rate at fixed MAD or adjacent MAD at fixed contamination',
  'neighbor_cells_with_zero_neighbors':sum(len(v)==0 for v in edges.values()),
  'primary_inference':'Global BH-adjusted p-values and t-based CIs from the original 720-W recovery',
  'caution':'A 95-percent CI without BH support is descriptive, not a second confirmatory discovery. '
    'One significant metric does not imply noninferiority of the other. '
    'Adjacent scenario cells are correlated and not independent datasets. '
    'Selection-aware whole-pipeline FPR calibration and external validity are not established by this supplement.',
  'registry_sha256':next(iter(provenance['registry_sha'])),'benchmark_map_sha256':next(iter(provenance['benchmark_sha'])),
  'blocks':block_report}
 (output/'scientific_limitations_and_provenance.json').write_text(json.dumps(report,indent=2)+'\n')
 (output/'README_REVIEWER_SCOPE.txt').write_text(
  'HELD-OUT REVIEWER COMPLEMENT V1\n'
  'Inputs: completed original individual scoring recovery, all six evaluation families, n 200/1000/3000.\n'
  'Primary: global 4,164,480-test BH adjustment is unchanged; winner taxonomy is unchanged.\n'
  'Secondary descriptive checks: per-evaluation-seed signs, leave-one-of-ten evaluation seed sensitivity, '
  '95% gain intervals, deterioration of secondary metric, within-support local neighboring cells, '
  'transfer across evaluated distribution families.\n'
  'Classification: tier1 = both MSE and Q95 improvement with BH q<=.05 and CI upper <0; '
  'tier2 = both CI upper <0 but not tier1; tier3 MSE or Q95 = one BH+CI supported gain '
  'without a joint tier; tier4 = no supported win. All remain subject to original pairing.\n'
  'The ten held-out seeds are evaluation replicates; training seeds identify separate W candidates.\n'
  'NEIGHBORING CELLS: same mechanism, adjacent rate at fixed MAD OR adjacent MAD at fixed rate; '
  'no inference on untouched stress-exclusive mechanisms.\n'
  'All generalization labels are descriptive; no new independent confirmation, equivalence, '
  'familywise error guarantee, or null-selection-calibrated FPR is claimed.\n'
  'No Monte Carlo, Discovery, scoring, or optimizer was executed.\n')
 print('HELDOUT_REVIEWER_COMPLEMENT_PASS',
  'candidates=720','blocks=18','original_BH_hypotheses=4164480',flush=True)

def selftest():
 assert loo([-1.]*10)[0]==1.
 assert loo([-1.]*10)[1]
 assert loo([1.]*10)[0]==0.
 assert not loo([1.]*10)[1]
 assert loo([-1.,-1.,-1.,-1.,-1.,-1.,-1.,-1.,-1.,2.])[1]
 assert boolean('True') is True
 assert boolean('False') is False
 print('HELDOUT_REVIEWER_UNIT_PASS')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--selftest',action='store_true')
 p.add_argument('--blocks')
 p.add_argument('--final')
 p.add_argument('--grid',default='config/T2_V3_B3_prospective_321_grid.csv')
 p.add_argument('--output')
 a=p.parse_args()
 if a.selftest:selftest()
 else:
  if not all((a.blocks,a.final,a.output)):p.error('Required --blocks --final --output')
  main(a)
