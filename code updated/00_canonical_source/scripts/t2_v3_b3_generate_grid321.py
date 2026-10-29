#!/usr/bin/env python3
"""Prospective, outcome-blind B3 321-scenario design manifest.
No edits to historical 121-scenario inputs or frozen Monte Carlo artifacts.
Select an approximately balanced subset of the complete 7*9*8 design.
"""
import csv, itertools, pathlib
from collections import Counter
RATES=(.01,.02,.05,.10,.15,.20,.30)
MAD=(1.5,3,4.5,6,9,12,15,20,30)
MECHANISMS=('upper_tail','lower_tail','symmetric_t','point_mass',
 'clustered_upper','clustered_symmetric','mixture_bimodal_near','mixture_bimodal_far')
space=list(itertools.product(RATES,MAD,MECHANISMS))
selected=[]
counts={'rate':Counter(),'mad':Counter(),'mechanism':Counter()}
# Greedy deterministic, symmetric marginal balance. No response or score input.
for i in range(320):
 def key(z):
  rate,mad,mechanism=z
  return (counts['rate'][rate]/(320/len(RATES))+
          counts['mad'][mad]/(320/len(MAD))+
          counts['mechanism'][mechanism]/(320/len(MECHANISMS)),
          counts['rate'][rate],counts['mad'][mad],counts['mechanism'][mechanism],
          (space.index(z)*37)%len(space))
 chosen=min((z for z in space if z not in selected),key=key)
 selected.append(chosen)
 for name,value in zip(('rate','mad','mechanism'),chosen):counts[name][value]+=1
rows=[dict(scenario_id=0,contamination=0,mad_scale=0,mechanism='clean',band='clean')]
for i,(rate,mad,mechanism) in enumerate(selected,1):
 band='low' if rate<=.05 else 'intermediate' if rate<=.15 else 'high'
 rows.append(dict(scenario_id=i,contamination=rate,mad_scale=mad,
                  mechanism=mechanism,band=band))
assert len(rows)==321 and len(set((z['contamination'],z['mad_scale'],z['mechanism']) for z in rows))==321
assert all(sum(1 for r in rows if r['contamination']==rate)>0 for rate in RATES)
assert all(sum(1 for r in rows if r['mad_scale']==mad)>0 for mad in MAD)
out=pathlib.Path('config/T2_V3_B3_prospective_321_grid.csv')
out.parent.mkdir(parents=True,exist_ok=True)
with out.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
print('B3_PROSPECTIVE_321_GRID_PASS',len(rows))
