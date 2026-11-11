#!/usr/bin/env python3
"""Audited one-world full-pipeline-null execution contract.

Never treat fixed-W score permutation as the complete selection-adjusted
null. The experiment-native runner MUST generate its null-world data, repeat
Discovery tuning/training/selection, freeze all individual W, and independently
evaluate on disjoint null data. This adapter accepts only a pinned, explicitly
approved command; it never substitutes a shortcut.
"""
import argparse,hashlib,json,os,pathlib,subprocess
def check(ok,msg):
 if not ok:raise ValueError(msg)
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--protocol',required=True)
 p.add_argument('--world-id',type=int,required=True)
 p.add_argument('--output',required=True)
 args=p.parse_args()
 cfg=json.loads(pathlib.Path(args.protocol).read_text())
 fields=('protocol_version','training_pipeline_revision','null_generator_revision',
         'null_hypothesis','executable_argv','expected_null_worlds','max_seconds_per_world')
 check(set(fields)<=set(cfg),'Incomplete native full-pipeline null contract')
 check(cfg['protocol_version']=='T3_B3_FULL_PIPELINE_NULL_V1','Unsupported null protocol')
 check(cfg['training_pipeline_revision']==os.environ.get('GITHUB_SHA',cfg['training_pipeline_revision']),
       'Training code revision is not frozen against this execution')
 check(cfg['null_hypothesis'] and cfg['null_generator_revision'],'Null design undocumented')
 check(int(cfg['expected_null_worlds'])>=100,'Need at least 100 independent null worlds')
 check(0<=args.world_id<int(cfg['expected_null_worlds']),'Invalid null world identity')
 timeout=int(cfg['max_seconds_per_world']);check(60<=timeout<=19800,'Bounded per-world budget required')
 argv=cfg['executable_argv']
 check(isinstance(argv,list) and 2<=len(argv)<=16 and all(isinstance(z,str) and z for z in argv),
       'Only explicit argument-array native runner accepted, never a shell command')
 exe=pathlib.Path(argv[0])
 check(exe.name in ('Rscript','python3','python'),'Unexpected native training runner')
 check(any('full_pipeline_null' in z for z in argv[1:]),
       'Runner must explicitly implement full-pipeline-null training and confirmation')
 # A unique output per world eliminates accidental reuse of fitted models,
 # seeds, selection normalizers, or training data.
 out=pathlib.Path(args.output);out.mkdir(parents=True,exist_ok=False)
 seed=int.from_bytes(hashlib.sha256(
  ('T3_B3_END_TO_END_NULL_WORLD_V1|'+str(args.world_id)).encode()).digest()[:8],'big')%2147483647
 env=os.environ.copy();env['T3_NULL_WORLD_INDEX']=str(args.world_id)
 env['T3_NULL_WORLD_SEED']=str(seed)
 env['T3_NULL_WORLD_OUTPUT']=str(out.resolve())
 p=subprocess.run(argv,check=False,env=env,timeout=timeout,capture_output=True,text=True)
 (out/'native_stdout.txt').write_text(p.stdout[-200000:])
 (out/'native_stderr.txt').write_text(p.stderr[-200000:])
 check(p.returncode==0,'Native full-pipeline null runner failed; see log')
 respath=out/'full_pipeline_null_result.json'
 check(respath.is_file(),'Native runner did not produce complete null scientific proof')
 x=json.loads(respath.read_text())
 gates={'null_world_index':args.world_id,'null_world_seed':seed,'train_and_test_disjoint':True,
  'all_training_hyperparameters_retuned':True,'all_720_individual_W_frozen':True,
  'all_26_baselines_scored':True,'independent_confirmation_scored':True,
  'full_selection_and_multiplicity_replayed':True}
 for k,v in gates.items():check(x.get(k)==v,'Native runner failed scientific null gate: '+k)
 check(isinstance(x.get('joint_fdr_supported_contrasts'),int)
       and 0<=x['joint_fdr_supported_contrasts']<=720,'Invalid false discovery tally')
 (out/'adapter_audit.json').write_text(json.dumps(dict(protocol=cfg['protocol_version'],
  native_runner_revision=cfg['training_pipeline_revision'],world=args.world_id,seed=seed,
  null_hypothesis=cfg['null_hypothesis'],gates_passed=list(gates)),indent=2)+'\n')
 print('T3_B3_NATIVE_FULL_PIPELINE_NULL_WORLD_PASS',args.world_id)
if __name__=='__main__':main()
