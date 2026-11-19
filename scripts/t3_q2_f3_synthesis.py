#!/usr/bin/env python3
"""Q2/F3: independently verify 18 robust shards; Q1/Q2 benchmark crosswalk and
conditional crossed-seed null surrogate with independent validation.
This is NOT full original optimizer-selection or experimental rerun calibration.
"""
import argparse,csv,hashlib,json,math
from pathlib import Path
from collections import defaultdict
import numpy as np
FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
SIZES=(200,1000,3000)
METHODS=("ga","nsga2","de","dirichlet")
MECHS=("upper_tail","lower_tail","symmetric_t","point_mass","clustered_upper","clustered_symmetric")
METRICS=("mse","q95")
Q1=Path("R1/runs/44324757704/synthesis/table_RQ1_72_method_family_sample_integrated.csv")
N_CAL=4096
N_VAL=4096

def must(x,msg):
    if not x:raise RuntimeError("Q2_F3_SYNTHESIS_GATE: "+str(msg))
def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for x in iter(lambda:f.read(1<<20),b""):h.update(x)
    return h.hexdigest()
def read_csv(path):
    with path.open(newline="",encoding="utf8") as f:return list(csv.DictReader(f))
def write(path,rows,fields=None):
    must(rows,"cannot write empty table "+str(path))
    with path.open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=fields or list(rows[0]))
        writer.writeheader();writer.writerows(rows)

def t_crossed(z):
    """Conservative clipped two-way cluster variance, with overlap correction.
    z: simulated replicates x 12 contrasts x 10 training x 10 eval.
    """
    m=z.mean(axis=(2,3))
    r=z.mean(axis=3);c=z.mean(axis=2)
    resid=z-r[:,:,:,None]-c[:,:,None,:]+m[:,:,None,None]
    se2=r.var(axis=2,ddof=1)/10+c.var(axis=2,ddof=1)/10-resid.var(axis=(2,3),ddof=1)/100
    se=np.sqrt(np.maximum(se2,1e-24))
    return m,se,m/se

def sample_crossed_null(original,rng,count):
    """Empirical additive row/column/cell null surrogate, contrasts share resampled
    seed axes; source scenario set fixed. Null mean centered at exact known zero.
    """
    mu=original.mean(axis=(1,2))
    rows=original.mean(axis=2)-mu[:,None]
    cols=original.mean(axis=1)-mu[:,None]
    resid=original-mu[:,None,None]-rows[:,:,None]-cols[:,None,:]
    resid=resid.reshape(12,100)
    out=np.empty((count,12),dtype=np.float64)
    for start in range(0,count,256):
        batch=min(256,count-start)
        ri=rng.integers(0,10,(batch,10));ci=rng.integers(0,10,(batch,10))
        ei=rng.integers(0,100,(batch,10,10))
        R=rows[:,ri].transpose(1,0,2)[:,:,:,None]
        C=cols[:,ci].transpose(1,0,2)[:,:,None,:]
        E=resid[:,ei].transpose(1,0,2,3)
        z=R+C+E
        must(z.shape==(batch,12,10,10),"surrogate dimensionality")
        out[start:start+batch]=t_crossed(z)[2]
    must(np.isfinite(out).all(),"finite null studentized contrasts")
    return out

def synthesize(root):
    blocks=root/"blocks";out=root/"synthesis"
    must(blocks.is_dir() and not out.exists(),"18 blocks must be preserved and synthesis must be new")
    out.mkdir(parents=True)
    original_q1=read_csv(Q1)
    must(len(original_q1)==72,"Q1 72 family-size-method rows")
    q1map={(r["family"],int(r["sample_n"]),r["method"]):r for r in original_q1}
    must(len(q1map)==72,"Q1 matched row uniqueness")
    block_records=[];all_robust=[];all_mech=[];all_local=[]
    matrices=[];keys=[]
    for family in FAMILIES:
      for n in SIZES:
        base=blocks/(family+"-n"+str(n))
        must(base.is_dir(),"missing Q2 F3 block "+str(base))
        v=json.loads((base/"F3_BLOCK_MANIFEST.json").read_text())
        must(v["status"]=="PASS_F3_ROBUST_RECONSTRUCTION" and v["family"]==family and v["sample_n"]==n,"F3 gate")
        must(v["original_paired_cells"]==192800 and v["scenario_summaries"]==1928,"original scientific size")
        for file,expect in v["files"].items():
            p=base/file
            must(p.is_file() and p.stat().st_size==expect["bytes"] and digest(p)==expect["sha256"],
                 "corrupt/missing F3 output "+str(p))
        records=read_csv(base/"ROBUST_SCENARIO_EFFECTS.csv")
        mechanisms=read_csv(base/"ROBUST_MECHANISM_SUMMARY.csv")
        local=read_csv(base/"ROBUST_OBSERVED_NEIGHBORS.csv")
        must(len(records)==1928 and len(mechanisms)==56,"complete F3 per-block tables")
        must(all(r["family"]==family and int(r["sample_n"])==n for r in records),"family/sample data corruption")
        must(len({(r["scenario_id"],r["method"],r["benchmark_role"]) for r in records})==1928,"unique scenario keys")
        must(len({(r["method"],r["benchmark_role"],r["mechanism"]) for r in mechanisms})==56,"mechanism table uniqueness")
        with np.load(base/"DE_OWN_12_CONTRASTS_CROSSED.npz",allow_pickle=False) as matrix:
            a=matrix["difference"];labels=list(matrix["labels"])
        must(a.shape==(12,10,10) and labels==[mech+"|"+metric for mech in MECHS for metric in METRICS],
             "calibration contrast / mechanism alignment")
        must(np.isfinite(a).all(),"nonfinite source contrast")
        matrices.append(a);keys.append((family,n))
        block_records.append(dict(family=family,sample_n=n,robust_scenarios=len(records),
                                  mechanisms=len(mechanisms),neighbor_edges=len(local),
                                  source_manifest_sha=v["source_manifest_sha256"]))
        all_robust.extend(records);all_mech.extend(mechanisms);all_local.extend(local)
    must(len(all_robust)==34704 and len(all_mech)==1008 and len(matrices)==18,"complete original 18 blocks")
    must(len({(r["family"],r["sample_n"],r["scenario_id"],r["method"],r["benchmark_role"])
              for r in all_robust})==34704,"cross-block de-duplication")

    # Independent Q1 block-level controls and Q2 matched per-scenario comparisons
    # are included together but NOT declared numerically paired or identical estimands.
    crosswalk=[]
    for family in FAMILIES:
      for n in SIZES:
        for method in METHODS:
          q1=q1map[family,n,method]
          for role in ("own","mean"):
            x=[r for r in all_robust if r["family"]==family and int(r["sample_n"])==n and
               r["method"]==method and r["benchmark_role"]==role and r["mechanism"]!="clean"]
            must(len(x)==240,"expected 240 original nonclean scenario rows in crosswalk")
            row=dict(family=family,sample_n=n,method=method,q2_reference_role=role,
                 q2_source_scenarios=240,q1_aggregation="original R1 family-size-control summaries",
                 q2_aggregation="original Q2 240 matched scenario x 100 paired-seed cells",
                 note="SIDE_BY_SIDE_ONLY_NOT_EXACT_PAIRED_CROSS_POLICY_CONTRAST")
            for metric in METRICS:
                a=sum(float(z[metric+"_candidate_mean"]) for z in x)
                b=sum(float(z[metric+"_reference_mean"]) for z in x)
                ratios=np.array([float(z[metric+"_mean_ratio"]) for z in x])
                row[metric+"_q2_pooled_ratio"]=a/max(b,1e-14)
                row[metric+"_q2_median_ratio"]=float(np.median(ratios))
                row[metric+"_q2_scenario_win_count"]=int(np.sum(ratios<1))
                row[metric+"_q1_convex_mse_gain_pct"]=q1["convex_mse_"+metric+"_relative_gain_pct"]
                row[metric+"_q1_local_deterministic_gain_pct"]=q1["local_deterministic_"+metric+"_relative_gain_pct"]
            row["q2_joint_ratio_scenario_wins"]=sum(int(z["joint_scenario_ratio_positive"]) for z in x)
            crosswalk.append(row)
    must(len(crosswalk)==144,"four methods x 18 blocks x 2 Q2 references")
    write(out/"Q2_F3_Q1_Q2_BENCHMARK_CROSSWALK.csv",crosswalk)
    write(out/"Q2_F3_ROBUST_ALL_SCENARIOS.csv",all_robust)
    write(out/"Q2_F3_ROBUST_MECHANISM_BLOCKS.csv",all_mech)
    write(out/"Q2_F3_LOCAL_NEIGHBOR_SENSITIVITY.csv",all_local)

    # Primary frozen DE-own 216 contrasts; both metrics, 6 mechanisms x 18 blocks.
    # Fit effect covariance to the original 10x10 seed matrix. Draw independent
    # calibration and validation surrogates (new synthetic data, not original MC).
    calibration=np.empty((N_CAL,216))
    validation=np.empty((N_VAL,216))
    original=np.empty((216,))
    effect=np.empty((216,));std_err=np.empty((216,))
    primary=[];block_null=[]
    for ib,(key,z) in enumerate(zip(keys,matrices)):
        rng=np.random.default_rng(720001+ib*1009)
        simcal=sample_crossed_null(z,rng,N_CAL)
        simval=sample_crossed_null(z,rng,N_VAL)
        obsmean,obsse,obsstat=t_crossed(z[None,...])
        start=12*ib
        calibration[:,start:start+12]=simcal
        validation[:,start:start+12]=simval
        original[start:start+12]=obsstat[0]
        effect[start:start+12]=obsmean[0]
        std_err[start:start+12]=obsse[0]
        nullcrit=float(np.quantile(np.max(np.abs(simcal),axis=1),.95,method="higher"))
        block_null.append(dict(family=key[0],sample_n=key[1],comparisons=12,
            calibrated_5pct_maxT_critical=nullcrit,
            independent_validation_FWER_12=float(np.mean(np.max(np.abs(simval),axis=1)>nullcrit)),
            surrogate_calibration_replicates=N_CAL,surrogate_validation_replicates=N_VAL))
        for j,mech in enumerate(MECHS):
            for k,metric in enumerate(METRICS):
                i=start+2*j+k
                primary.append(dict(family=key[0],sample_n=key[1],method="de",
                   reference="own",mechanism=mech,metric=metric,
                   raw_candidate_minus_reference=effect[i],two_way_seed_se=std_err[i],
                   observed_two_way_studentized=original[i],
                   null_surrogate="centered empirical additive crossed-seed generator",
                   original_scenario_resampling=False,
                   original_optimizer_reselection=False))
    must(len(primary)==216 and np.isfinite(calibration).all() and np.isfinite(validation).all(),"216 complete primary")
    globalcal=np.max(np.abs(calibration),axis=1)
    globalval=np.max(np.abs(validation),axis=1)
    cutoff=float(np.quantile(globalcal,.95,method="higher"))
    global_fwer=float(np.mean(globalval>cutoff))
    nominal_fwer=float(np.mean(globalval>2.2621571627409915))
    for i,row in enumerate(primary):
        row["synthetic_global216_maxT_cutoff"]=cutoff
        row["synthetic_global216_maxT_support"]=bool(abs(original[i])>cutoff)
        row["synthetic_global216_maxT_p"]=(1+int(np.sum(globalcal>=abs(original[i]))))/(N_CAL+1)
        row["synthetic_global216_95CI_lower"]=float(effect[i]-cutoff*std_err[i])
        row["synthetic_global216_95CI_upper"]=float(effect[i]+cutoff*std_err[i])
        row["synthetic_independent_validation_FWER"]=global_fwer
        row["inferential_status"]="EXPLORATORY_FIXED_CANDIDATE_SURROGATE_NOT_FULL_PIPELINE_CALIBRATED"
    write(out/"Q2_F3_PRIMARY_216_CROSSED_SURROGATE_SENSITIVITY.csv",primary)
    write(out/"Q2_F3_18_BLOCK_NULL_VALIDATION.csv",block_null)
    write(out/"Q2_F3_BLOCK_INTEGRITY_AND_LINEAGE.csv",block_records)
    de_own=[r for r in all_robust if r["method"]=="de" and r["benchmark_role"]=="own" and r["mechanism"]!="clean"]
    de_mean=[r for r in all_robust if r["method"]=="de" and r["benchmark_role"]=="mean" and r["mechanism"]!="clean"]
    must(len(de_own)==len(de_mean)==4320,"DE comparator denominators")
    summary={}
    for name,x in (("own",de_own),("mean",de_mean)):
        summary[name]=dict(scenarios=len(x),
          joint_scenario_ratio_wins=sum(int(r["joint_scenario_ratio_positive"]) for r in x),
          mse_median_ratio=float(np.median([float(r["mse_mean_ratio"]) for r in x])),
          q95_median_ratio=float(np.median([float(r["q95_mean_ratio"]) for r in x])),
          mse_ratio_of_pooled_losses=sum(float(z["mse_candidate_mean"]) for z in x)/
                          max(sum(float(z["mse_reference_mean"]) for z in x),1e-14),
          q95_ratio_of_pooled_losses=sum(float(z["q95_candidate_mean"]) for z in x)/
                          max(sum(float(z["q95_reference_mean"]) for z in x),1e-14))
    audit={"status":"PASS_Q2_F3_POINTS_1_AND_2_CONDITIONAL",
      "source_run":44599590079,"source_blocks":18,"original_source_archives":180,
      "original_paired_seed_metric_records":18*192800,
      "scenario_summary_rows":len(all_robust),
      "method_reference_mechanism_block_rows":len(all_mech),
      "local_neighbor_rows":len(all_local),
      "q1_comparator_crosswalk_rows":len(crosswalk),
      "primary_de_own_effect_contrasts":216,
      "original_scenario_or_optimizer_rerun":False,
      "conditional_null_calibration_synthetic_replicates":N_CAL,
      "independent_null_validation_synthetic_replicates":N_VAL,
      "null_5pct_global216_maxT_threshold":cutoff,
      "independent_global216_null_fwer_surrogate":global_fwer,
      "independent_global216_null_fwer_original_t9_cutoff_surrogate":nominal_fwer,
      "global216_calibration_model_requires_independence_of_18_blocks":True,
      "uncertainty_limited_to_original_10x10_training_evaluation_seed_axes":True,
      "original_optimizer_reselection_calibrated":False,
      "original_HPO_calibrated":False,
      "full_joint_dependency_and_selection_coverage_guarantee":False,
      "factorial_design_complete":False,
      "benchmarks_are_comparable_only_within_original_matched_policy":True,
      "de_summary":summary,
      "note":"Synthetic fitted crossed-seed null diagnostic; validates only this surrogate's fixed-candidate, fixed-scenario assumptions. The independent seeded validation cannot establish actual full-pipeline familywise error."}
    manifest={}
    for p in sorted(out.iterdir()):
        if p.is_file():manifest[p.name]=dict(sha256=digest(p),bytes=p.stat().st_size)
    audit["synthesis_source_checksums"]=manifest
    (out/"Q2_F3_SCIENTIFIC_AUDIT.json").write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n")
    story=f"""# Q2 F3 — Scientific reconstruction and conditional inference

## Scope
Original 18 Q2 blocks: {18*192800:,} paired candidate/reference observations,
{len(all_robust):,} scenario–method–reference summaries, 180 original source ZIPs.
No original data simulation, original optimizer re-training, HPO or candidate reselection.
The 241 supported scenarios include one clean and 240 contaminated observations per block.
All inputs checked against original permanent Q2 per-block SHA-256 manifests.

## Primary comparator policy
DE versus Discovery-selected classical reference ('own') is the original Q2 policy.
It yields {summary['own']['joint_scenario_ratio_wins']}/{summary['own']['scenarios']} favorable
two-loss scenarios when comparing the ratios of mean original candidate/reference losses.
Against the sample mean: {summary['mean']['joint_scenario_ratio_wins']}/{summary['mean']['scenarios']}.
These are descriptive source-scenario classifications, not independent hypothesis tests.

## Q1 reconciliation
The 144-row crosswalk displays original Q1 convex-MSE and local deterministic
family/size contrasts side by side with Q2's original own/mean regime-specific
ratios. **This crosswalk is NOT an exact seed/scenario-matched head-to-head
test between convex-MSE and Q2's own reference.** Do not subtract the
reported percentages or relabel one as another. Deriving a matched
convex-MSE per-scenario reference requires original classical score-level data.

## Conditional Q2-specific null diagnostic
The original 216 DE-vs-own raw-loss effects are re-expressed using a two-way
10 training x 10 evaluation seed variance approximation.
For each block, a centered additive row/column/cell empirical model creates
{N_CAL:,} synthetic calibration draws and a disjoint {N_VAL:,} validation draws.
The global 216-statistic maxT cutoff is {cutoff:.5g}.
Its held-out synthetic global-null rejection rate is {100*global_fwer:.3f}%;
using the uncalibrated t9 cutoff, {100*nominal_fwer:.3f}%.
The global model independently generates the 18 blocks and shares both
two-loss and six-mechanism correlation within each block. Original seed reuse
across blocks, source-scenario randomness, weight selection and nested HPO
are not captured. **Synthetic conditional calibration cannot be advertised
as genuine selection-aware nominal error control on original Q2 data.**

## Scientific interpretation
Compare absolute losses and pooled/median ratios together with the
unfavorable tails; the mean of per-pair percent changes explodes when the
classical reference loss is near zero. Fraction and MAD severity results
use only observed original neighbor edges; the six mechanisms do not
form complete 7 x 9 factor grids.

## Permanently retained evidence
Every F3 block contains ROBUST_SCENARIO_EFFECTS.csv,
ROBUST_MECHANISM_SUMMARY.csv, ROBUST_OBSERVED_NEIGHBORS.csv,
DE_OWN_12_CONTRASTS_CROSSED.npz and F3_BLOCK_MANIFEST.json.
The synthesis contains the complete pooled summaries, Q1/Q2 policy
crosswalk, null-surrogate validation, 216 conditional effects, and source hashes.
All are new immutable records under Q2/F3/runs/; original Q2 is untouched.
"""
    (out/"Q2_F3_RESULTS_AND_LIMITATIONS.md").write_text(story)
    # Manifest is written after every output it covers, excluding itself.
    manifest={p.name:dict(sha256=digest(p),bytes=p.stat().st_size) for p in sorted(out.iterdir()) if p.is_file()}
    (out/"Q2_F3_SHA256_MANIFEST.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print("Q2_F3_FULL_SYNTHESIS_PASS",len(all_robust),"scenarios",len(all_local),"neighbors",len(primary),"contrasts",
          "synthetic_null_FWER",global_fwer,flush=True)

def selftest():
    a=np.arange(1200,dtype=float).reshape(12,10,10)
    rng=np.random.default_rng(111)
    sim=sample_crossed_null(a,rng,128)
    must(sim.shape==(128,12) and np.isfinite(sim).all(),"selftest shape")
    print("Q2_F3_SYNTHESIS_SELFTEST_PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("mode",choices=["run","selftest"]);p.add_argument("--root")
    args=p.parse_args()
    if args.mode=="selftest":selftest()
    else:must(args.root,"required root");synthesize(Path(args.root))
