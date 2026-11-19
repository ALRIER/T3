#!/usr/bin/env python3
"""Q2/F3: source-audited robust effect reconstruction from original Q2 paired seeds.
No original training, scenario simulation, or selection is repeated.
"""
import argparse,csv,gzip,hashlib,json,math
from pathlib import Path
from collections import defaultdict
import numpy as np

METHODS=("ga","nsga2","de","dirichlet")
ROLES=("own","mean")
METRICS=("mse","q95")
MECHS=("upper_tail","lower_tail","symmetric_t","point_mass","clustered_upper","clustered_symmetric")
BASE=Path("Q2/runs/44599590079/blocks")

def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):h.update(block)
    return h.hexdigest()
def must(ok,msg):
    if not ok:raise RuntimeError("Q2_F3_BLOCK_GATE: "+str(msg))
def write(path,fields,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,"w",newline="",encoding="utf8") as h:
        w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
def selftest():
    c=np.array([1.,2.,3.]);r=np.array([2.,4.,6.])
    must(abs(100*(1-c.mean()/r.mean())-50)<1e-12,"ratio of means")
    must(abs(np.median(c/r)-.5)<1e-12,"paired ratio")
    print("Q2_F3_BLOCK_SELFTEST_PASS")

def block(family,n,output):
    source=BASE/(family+"-n"+str(n))
    manifest=json.loads((source/"Q2_BLOCK_MANIFEST.json").read_text())
    must(manifest["family"]==family and manifest["sample_n"]==n,"source block identity")
    must(manifest["paired_benchmark_metric_records"]==192800 and manifest["scenario_rows"]==1928,"source design counts")
    must(len(manifest["original_archive_lineage"])==10,"ten original input archives")
    for k,info in manifest["outputs"].items():
        f=source/k
        must(f.is_file() and f.stat().st_size==info["bytes"] and digest(f)==info["sha256"],"input hash "+k)
    with (source/"scenario_effects.csv").open(newline="") as f:
        orig=list(csv.DictReader(f))
    must(len(orig)==1928,"source scenario summary rows")
    scenarios={int(r["scenario_id"]):r for r in orig}
    ids=sorted({int(r["scenario_id"]) for r in orig})
    must(len(ids)==241,"241 original support scenario identities")
    idx={k:i for i,k in enumerate(ids)}
    must(len({(r["scenario_id"],r["method"],r["benchmark_role"]) for r in orig})==1928,"unique summaries")
    for sid in ids:
        must(len({(r["method"],r["benchmark_role"]) for r in orig if int(r["scenario_id"])==sid})==8,"source coverage")
    # scenario × method × reference × 10 training × 10 independent evaluation × loss × {candidate,reference}
    cell=np.full((241,4,2,10,10,2,2),np.nan,dtype=np.float64)
    seen=np.zeros((241,4,2,10,10),dtype=np.bool_)
    rows=0
    with gzip.open(source/"paired_seed_cells.csv.gz","rt",newline="") as f:
        for r in csv.DictReader(f):
            sid=int(r["scenario_id"]);i=idx[sid];m=METHODS.index(r["method"]);role=ROLES.index(r["benchmark_role"])
            tr=int(r["training_seed"]);ev=int(r["evaluation_seed"])-10
            must(0<=tr<10 and 0<=ev<10 and not seen[i,m,role,tr,ev],"duplicate/corrupt original cell")
            must(r["family"]==family and int(r["sample_n"])==n,"family mismatch")
            seen[i,m,role,tr,ev]=True
            for k,metric in enumerate(METRICS):
                a=float(r[metric+"_candidate"]);b=float(r[metric+"_reference"])
                must(math.isfinite(a) and math.isfinite(b) and a>=0 and b>=0,"invalid loss")
                cell[i,m,role,tr,ev,k,0]=a;cell[i,m,role,tr,ev,k,1]=b
            rows+=1
    must(rows==192800 and seen.all() and np.isfinite(cell).all(),"all original cells are required")
    robust=[];original={(int(x["scenario_id"]),x["method"],x["benchmark_role"]):x for x in orig}
    for sid in ids:
        i=idx[sid];meta=scenarios[sid]
        for mi,method in enumerate(METHODS):
            for ri,role in enumerate(ROLES):
                z=cell[i,mi,ri];a=z[:,:,:,0];b=z[:,:,:,1]
                record={"family":family,"sample_n":n,"scenario_id":sid,"mechanism":meta["mechanism"],
                        "contamination":meta["contamination"],"mad_scale":meta["mad_scale"],
                        "method":method,"benchmark_role":role,"training_seeds":10,"evaluation_seeds":10}
                source_original=original[sid,method,role]
                for k,metric in enumerate(METRICS):
                    c=a[:,:,k];ref=b[:,:,k]; denom=np.maximum(ref,1e-14)
                    gain=100*(ref-c)/denom
                    must(abs(float(gain.mean())-float(source_original[metric+"_gain_pct"]))<1e-5,
                         "independent reconstruction differs from original Q2 "+str((sid,method,role,metric)))
                    mc=float(c.mean());mr=float(ref.mean())
                    ratio=mc/max(mr,1e-14)
                    record.update({metric+"_candidate_mean":mc,metric+"_reference_mean":mr,
                                   metric+"_absolute_diff_mean":float((c-ref).mean()),
                                   metric+"_absolute_diff_median":float(np.median(c-ref)),
                                   metric+"_mean_ratio":ratio,
                                   metric+"_ratio_of_means_gain_pct":100*(1-ratio),
                                   metric+"_median_paired_ratio":float(np.median(c/denom)),
                                   metric+"_paired_seed_win_fraction":float(np.mean(c<ref)),
                                   metric+"_original_mean_pct_gain":float(gain.mean())})
                record["joint_scenario_ratio_positive"]=int(record["mse_mean_ratio"]<1 and record["q95_mean_ratio"]<1)
                record["joint_seed_pair_win_fraction"]=float(np.mean((a[:,:,0]<b[:,:,0])&(a[:,:,1]<b[:,:,1])))
                robust.append(record)
    must(len(robust)==1928,"complete robust summary")
    # Mechanism × 4 methods × 2 benchmarks: compare raw losses before taking ratios.
    aggregate=[]
    for method in METHODS:
      for role in ROLES:
        for mech in ("clean",)+MECHS:
            chosen=[x for x in robust if x["method"]==method and x["benchmark_role"]==role and x["mechanism"]==mech]
            must(len(chosen)==(1 if mech=="clean" else 40),"mechanism support coverage")
            row=dict(family=family,sample_n=n,method=method,benchmark_role=role,mechanism=mech,
                     scenarios=len(chosen),joint_ratio_wins=sum(x["joint_scenario_ratio_positive"] for x in chosen))
            for metric in METRICS:
                ratios=np.array([x[metric+"_mean_ratio"] for x in chosen])
                candidate=sum(x[metric+"_candidate_mean"] for x in chosen)
                ref=sum(x[metric+"_reference_mean"] for x in chosen)
                row.update({metric+"_pooled_loss_ratio":candidate/max(ref,1e-14),
                    metric+"_median_scenario_ratio":float(np.median(ratios)),
                    metric+"_scenario_ratio_q10":float(np.quantile(ratios,.1)),
                    metric+"_scenario_ratio_q90":float(np.quantile(ratios,.9)),
                    metric+"_mean_absolute_diff":float(np.mean([x[metric+"_absolute_diff_mean"] for x in chosen])),
                    metric+"_scenario_win_count":int(np.sum(ratios<1))})
            aggregate.append(row)
    # Observed original neighborhood edges. Do not fabricate missing factorial cells.
    map_scenario={(r["method"],r["benchmark_role"],int(r["scenario_id"])):r for r in robust}
    local=[]
    with (source/"local_neighbors.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            a=map_scenario[r["method"],r["benchmark_role"],int(r["scenario_low"])]
            b=map_scenario[r["method"],r["benchmark_role"],int(r["scenario_high"])]
            row=dict(family=family,sample_n=n,mechanism=r["mechanism"],axis=r["axis"],
                     scenario_low=r["scenario_low"],scenario_high=r["scenario_high"],
                     method=r["method"],benchmark_role=r["benchmark_role"])
            for metric in METRICS:
                row[metric+"_log_ratio_change"]=float(math.log(max(b[metric+"_mean_ratio"],1e-14))-
                                                       math.log(max(a[metric+"_mean_ratio"],1e-14)))
                row[metric+"_absolute_diff_change"]=float(b[metric+"_absolute_diff_mean"]-
                                                        a[metric+"_absolute_diff_mean"])
            local.append(row)
    # Fixed-scenario crossed 10x10 raw loss differences for fitted additive null surrogate.
    source_mechs={sid:scenarios[sid]["mechanism"] for sid in ids}
    matrices=[];labels=[]
    for mech in MECHS:
        selected=[idx[sid] for sid in ids if source_mechs[sid]==mech]
        must(len(selected)==40,"fixed 40 scenarios in mechanism")
        for k,metric in enumerate(METRICS):
            z=cell[selected,2,0,:,: ,k,:]  # DE vs Discovery-selected classical reference
            matrices.append((z[...,0]-z[...,1]).mean(axis=0))
            labels.append(mech+"|"+metric)
    matrices=np.array(matrices,dtype=float)
    must(matrices.shape==(12,10,10) and np.isfinite(matrices).all(),"crossed contrast matrix")
    output.mkdir(parents=True,exist_ok=False)
    write(output/"ROBUST_SCENARIO_EFFECTS.csv",list(robust[0]),robust)
    write(output/"ROBUST_MECHANISM_SUMMARY.csv",list(aggregate[0]),aggregate)
    write(output/"ROBUST_OBSERVED_NEIGHBORS.csv",list(local[0]),local)
    np.savez_compressed(output/"DE_OWN_12_CONTRASTS_CROSSED.npz",difference=matrices,labels=np.array(labels))
    files={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in output.iterdir() if p.is_file()}
    receipt={"status":"PASS_F3_ROBUST_RECONSTRUCTION","original_q2_run":44599590079,
             "family":family,"sample_n":n,"original_paired_cells":rows,
             "scenario_summaries":len(robust),"mechanism_summaries":len(aggregate),"observed_local_edges":len(local),
             "crossed_training_seeds":10,"crossed_heldout_seeds":10,
             "primary_contrast_matrices":len(labels),"full_factorial":False,
             "reconstructed_from_original_q2_shards":True,
             "source_manifest_git_path":str(source/"Q2_BLOCK_MANIFEST.json"),
             "source_manifest_sha256":digest(source/"Q2_BLOCK_MANIFEST.json"),
             "files":files}
    (output/"F3_BLOCK_MANIFEST.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("Q2_F3_BLOCK_PASS",family,n,"input",rows,"robust",len(robust),"neighbors",len(local),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("mode",choices=["block","selftest"])
    p.add_argument("--family");p.add_argument("--n",type=int);p.add_argument("--output")
    args=p.parse_args()
    if args.mode=="selftest":selftest()
    else:
      must(args.family in ("normal","lognormal","weibull","invgauss","exgaussian","exwald") and args.n in (200,1000,3000),"matrix")
      must(args.output,"output path");block(args.family,args.n,Path(args.output))
