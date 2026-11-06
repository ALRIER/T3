#!/usr/bin/env python3
"""Non-destructive, complete T3/B3 Real World two-policy scientific consolidation.
Preserve predeclared source-policy results and supplementary destination-policy panels.
Never concatenate their p-values or recompute BH across policies.
"""
import argparse,csv,gzip,hashlib,json,math,collections,pathlib
FAMILIES=('normal','lognormal','weibull','invgauss','exgaussian','exwald')
SCOPES=('within_regime','within_family_neighborhood','cross_family_transfer')
PANELS=('primary','secondary')
FILES={'primary':'primary_parent_BH_taxonomy.csv.gz','secondary':'secondary_family_transfer_BH_taxonomy.csv.gz'}
KEY=('source_family','candidate_id','engine','training_seed','sample_n','transfer_scope','benchmark_role')
def check(x,msg):
 if not x:raise ValueError(msg)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()
def rows(p):
 with gzip.open(p,'rt',newline='') as f:yield from csv.DictReader(f)
def dump(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def csvout(p,data):
 check(data,'Cannot export an empty comparison')
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def num(row,col):
 x=float(row[col]);check(math.isfinite(x),'Invalid finite value '+col);return x
def key(r,panel):
 k=tuple(r[f] for f in KEY)
 return k+(r['evaluation_family'],) if panel=='secondary' else k
def read_policy(directory,label):
 directory=pathlib.Path(directory)
 prov=json.loads((directory/'scientific_provenance.json').read_text())
 check(prov['original_candidate_count']==720,'Missing 720 W')
 check(prov['realworld_seeds']==list(range(30,40)),'Incorrect reserved evaluation seeds')
 check(prov['primary_hypotheses']==8160 and prov['secondary_hypotheses']==29760,'Incomplete BH hypothesis panels')
 if label=='destination':check(prov.get('own_benchmark_family_policy')=='destination','Destination policy mismatch')
 else:check(prov.get('own_benchmark_family_policy','source')=='source','Source policy mismatch')
 data={}
 for panel in PANELS:
  p=directory/FILES[panel];d={};candidates=set();counts=collections.Counter()
  for r in rows(p):
   k=key(r,panel)
   check(k not in d,'Duplicate hypothesis row '+str(k))
   check(r['source_family'] in FAMILIES and r['transfer_scope'] in SCOPES,'Unexpected family/scope')
   check(r['benchmark_role'] in ('own','mean'),'Unexpected classical comparator policy')
   check(int(r['independent_parent_datasets'])>=5,'Insufficient independent parent datasets')
   if panel=='secondary':check(r['evaluation_family'] in FAMILIES,'Unknown destination')
   for metric in ('mse','q95'):
    q=num(r,metric+'_global_bh_q');check(0<=q<=1,'Invalid BH q')
    num(r,metric+'_difference');num(r,metric+'_ci_upper');num(r,metric+'_p')
   expected=(num(r,'mse_global_bh_q')<=.05 and num(r,'q95_global_bh_q')<=.05
             and num(r,'mse_ci_upper')<0 and num(r,'q95_ci_upper')<0)
   check((r['highest_tier']=='tier1_joint_mse_q95_bh_fdr')==expected,'Tier 1 not reproducible')
   d[k]=r;candidates.add(r['candidate_id']);counts[(r['source_family'],r['benchmark_role'])]+=1
  check(len(candidates)==720,'Candidate set incomplete in '+label+'/'+panel)
  expected_rows=4080 if panel=='primary' else 14880
  check(len(d)==expected_rows,'Hypothesis count mismatch in '+label+'/'+panel)
  data[panel]=d
 return prov,data
def main():
 a=argparse.ArgumentParser()
 a.add_argument('--source',required=True);a.add_argument('--destination',required=True)
 a.add_argument('--source-review',required=True);a.add_argument('--destination-review',required=True)
 a.add_argument('--ledger',required=True);a.add_argument('--output',required=True)
 args=a.parse_args();out=pathlib.Path(args.output)
 check(not out.exists(),'Refusing to overwrite completed scientific consolidation')
 out.mkdir(parents=True)
 src,sp=read_policy(args.source,'source')
 dst,dp=read_policy(args.destination,'destination')
 ledger=json.loads(pathlib.Path(args.ledger).read_text())
 check(ledger['source_shards']==856 and ledger['reduction_jobs']==216,'Original scoring source lineage incomplete')
 ids={x['artifact_id'] for x in ledger['all_artifacts']}
 check(len(ids)==856,'Original score source artifact ID duplicate')
 for label,p in (('source',args.source_review),('destination',args.destination_review)):
  review=json.loads(pathlib.Path(p,'reviewer_scientific_scope.json').read_text())
  check(review['original_frozen_W']==720 and review['primary_parent_contrasts']==4080
        and review['secondary_destination_contrasts']==14880,'Reviewer did not cover complete '+label+' panels')
 compare=[];changes=collections.Counter();retained=collections.Counter();tier=collections.Counter()
 mean_raw_checked=0
 for panel in PANELS:
  arows=sp[panel];brows=dp[panel]
  check(set(arows)==set(brows),'The two policies have mismatched inferential panel identities: '+panel)
  for k in sorted(arows):
   x=arows[k];y=brows[k];role=x['benchmark_role'];f=x['source_family']
   same_raw=all(math.isclose(num(x,m),num(y,m),rel_tol=1e-11,abs_tol=1e-11)
                for m in ('mse_difference','q95_difference','mse_ci_lower','mse_ci_upper',
                          'q95_ci_lower','q95_ci_upper','mse_p','q95_p'))
   if role=='mean':
    check(same_raw,'Original mean-benchmark measured effects changed under destination-policy reanalysis')
    mean_raw_checked+=1
   tiers=(x['highest_tier'],y['highest_tier'])
   changed=tiers[0]!=tiers[1]
   row={field:x[field] for field in KEY}
   row['panel']=panel;row['evaluation_family']=x['evaluation_family'] if panel=='secondary' else ''
   row.update(source_tier=tiers[0],destination_tier=tiers[1],tier_changed=changed,
              original_mean_effect_invariant=(same_raw if role=='mean' else ''),
              source_mse_gain_pct=num(x,'mse_gain_pct'),destination_mse_gain_pct=num(y,'mse_gain_pct'),
              source_q95_gain_pct=num(x,'q95_gain_pct'),destination_q95_gain_pct=num(y,'q95_gain_pct'),
              source_mse_global_q=num(x,'mse_global_bh_q'),destination_mse_global_q=num(y,'mse_global_bh_q'),
              source_q95_global_q=num(x,'q95_global_bh_q'),destination_q95_global_q=num(y,'q95_global_bh_q'),
              source_independent_parents=int(x['independent_parent_datasets']),
              destination_independent_parents=int(y['independent_parent_datasets']))
   compare.append(row)
   changes[(panel,role,f)]+=int(changed)
   retained[(panel,role,f)]+=1
   tier[(panel,role,tiers[0],tiers[1])]+=1
 csvout(out/'complete_720W_both_policies_paired_comparisons.csv',compare)
 distribution=[dict(panel=p,benchmark_role=role,source_family=family,
                    total=retained[p,role,family],tier_changed=changes[p,role,family])
               for p in PANELS for role in ('own','mean') for family in FAMILIES]
 csvout(out/'policy_comparison_by_family.csv',distribution)
 csvout(out/'tier_transition_matrix.csv',
        [dict(panel=p,benchmark_role=r,source_tier=s,destination_tier=d,contrasts=n)
         for (p,r,s,d),n in sorted(tier.items())])
 # Candidate-level results are observational external evaluation results, not new training metrics.
 candidate=collections.defaultdict(lambda:collections.Counter())
 for row in compare:
  id_=row['candidate_id'];c=candidate[id_]
  c['n_panels']+=1
  if row['source_tier']=='tier1_joint_mse_q95_bh_fdr':c['source_tier1']+=1
  if row['destination_tier']=='tier1_joint_mse_q95_bh_fdr':c['destination_tier1']+=1
  if row['source_tier']==row['destination_tier']=='tier1_joint_mse_q95_bh_fdr':c['both_tier1']+=1
  if row['benchmark_role']=='mean':
   c['mean_rows']+=1
 candidate_rows=[dict(candidate_id=k,**v) for k,v in sorted(candidate.items())]
 check(len(candidate_rows)==720,'Lost individual W identity in complete comparison')
 csvout(out/'all_720_individual_W_cross_policy_summary.csv',candidate_rows)
 provenance={'protocol':'T3_B3_REALWORLD_COMPLETE_EXISTING_FROZEN_EVIDENCE_INTEGRATION',
  'scope':'642 independent empirical parents, 743 frozen child profiles, 856 original raw scoring artifacts, 720 frozen W',
  'source_policy_primary_run':42251598557,'destination_policy_sensitivity_run':42282378329,
  'original_raw_score_shards':856,'distinct_original_individual_W':720,
  'training_seeds':list(range(10)),'evaluation_seeds':list(range(30,40)),
  'primary_parent_hypotheses_per_policy':8160,'secondary_destination_hypotheses_per_policy':29760,
  'primary_contrasts_per_policy':4080,'secondary_contrasts_per_policy':14880,
  'paired_contrasts_across_two_policies':len(compare),
  'mean_reference_measurement_invariance_checked':mean_raw_checked,
  'source_original_ledger_sha256':sha(pathlib.Path(args.ledger)),
  'source_taxonomy_sha256':{p:sha(pathlib.Path(args.source)/FILES[p]) for p in PANELS},
  'destination_taxonomy_sha256':{p:sha(pathlib.Path(args.destination)/FILES[p]) for p in PANELS},
  'global_BH_panels_stay_separate_between_source_and_destination':True,
  'destination_family_estimated_not_true_DGP':True,
  'neighborhood_diagnostics_descriptive_not_causal':True,
  'non_evolutionary_control_scores_not_in_856_raw_source_artifacts':True,
  'independent_unit':'parent_dataset_id','new_simulation_or_optimizers_run':False,
  'publication_rule':'predeclared source benchmark primary; destination policy supplementary; do not select after external outcomes'}
 dump(out/'final_complete_provenance.json',provenance)
 (out/'scientific_scope_and_limits.md').write_text(
 '# T3 B3 Real World — Complete frozen 720-W scientific consolidation\n\n'
 'Covers both completed benchmark policies, both independent-parent/empirical-destination BH panels, '
 'six source and six empirical families, all three sample sizes, ten Discovery fits, ten evaluation seeds, '
 'and the frozen 856-shard external-score provenance. This is **final inference synthesis**, not fresh scoring.\n\n'
 'Original primary policy: Discovery-frozen classical comparator for the training source family. '
 'Supplementary policy: Discovery-frozen classical comparator for the outcome-blind estimated empirical destination family. '
 'The sample mean comparator is unchanged in measured effects, although its global BH q-values can differ because '
 'the complete hypothesis family also contains classical-comparator comparisons. '
 'Results and q-values from distinct policies are never pooled.\n\n'
 'No true population mean or true empirical generating family is known; inference uses parent clusters. '
 'Adjacent empirical scenario transitions are descriptive only, not causal. '
 'Both non-evolutionary controls mentioned in older code are not among the scored 720 frozen evolutionary W '
 'and cannot be represented as evaluated here. They require separately approved, auditable scoring. '
 'The archived 26 classic benchmark scores were used for the frozen own classical comparator and mean; '
 'the present primary inference does not claim paired wins over every individual classic.\n\n'
 'Post hoc ranking of candidate W by external results is exploratory and is not independent held-out confirmation.\n')
 print('REALWORLD_COMPLETE_SCIENTIFIC_720W_PAIRED_POLICIES_PASS',len(compare),'paired hypotheses,',mean_raw_checked,'unchanged mean reference comparisons',flush=True)
if __name__=='__main__':main()
