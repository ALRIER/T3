#!/usr/bin/env python3
import csv,json,sys,pathlib
base=pathlib.Path(sys.argv[1])
out=pathlib.Path('artifacts/T2_V3_B3_calibration')
out.mkdir(parents=True,exist_ok=True)
families=('normal','lognormal','weibull','invgauss','exgaussian','exwald')
rows=[]
for fam in families:
 for seed in range(10,15):
  for n in (200,1000,3000):
   p=base/fam/f'seed{seed:02d}_n{n}'/'null_calibration.csv'
   if not p.exists():raise RuntimeError(f'Missing required null audit {p}')
   z=list(csv.DictReader(p.open()))
   if not z:raise RuntimeError(f'Empty null audit {p}')
   groups={}
   for r in z:
    k=(r['training_seed'],r['scenario_id'])
    rate=float(r['joint_familywise_fpr'])
    reps=int(r['null_reps'])
    if not 0<=rate<=1 or reps<30:raise RuntimeError(f'Invalid null calibration {p}')
    if k in groups and groups[k]!=(rate,reps):raise RuntimeError(f'Inconsistent null calibration {p}')
    groups[k]=(rate,reps)
   if len(groups)!=10:raise RuntimeError(f'Missing training seeds: {p}')
   for (train,scenario),(rate,reps) in groups.items():
    rows.append(dict(family=fam,eval_seed=seed,n=n,training_seed=train,scenario=scenario,
                     false_positive_rate=rate,replications=reps))
with (out/'null_panel_T2_V3_B3.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
report={'version':'T2_V3_B3','status':'diagnostic_only','shards':90,'null_panels':len(rows),
        'mean_fwer_diagnostic':sum(r['false_positive_rate'] for r in rows)/len(rows),
        'limitation':'Paired-exchangeability Holm diagnostic only; full-selection and BH-FDR calibration not established'}
(out/'report_T2_V3_B3.json').write_text(json.dumps(report,indent=2))
print('T2_V3_B3_NULL_AUDIT_PASS',report)
