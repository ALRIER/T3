#!/usr/bin/env python3
"""Read-only inspection of existing T3 archived sources for unfinished RQ1 checks.

Stage must run only after all new crossed-seed R1 reviewer analyses pass.
No fitting, sampling, scoring or use of unverified new observations.
"""
import argparse
import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

FAMILIES=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
SOURCE="44310024979"

def ensure(p,message):
    if not p: raise ValueError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def manifests(root,stage):
    base=root/stage/"actions"
    ensure(base.is_dir(),"Missing local archive metadata stage "+stage)
    found=[]
    for path in sorted(base.glob("*/manifest.json")):
        z=json.loads(path.read_text())
        if z.get("complete") is not True:
            continue
        source=z.get("source",{})
        if not isinstance(source,dict):source={}
        found.append({
          "path":str(path.parent),
          "name":path.parent.name,
          "archive_sha256":z.get("sha256"),
          "bytes":z.get("size_bytes"),
          "source_run":source.get("run_id"),
          "source_artifact_name":source.get("name"),
          "parts":len(z.get("parts",[])),
          "state":"complete_manifest_only_no_part_hash_reverification"})
    return found

def read_archive(directory,max_bytes=75000000):
    meta=json.loads((directory/"manifest.json").read_text())
    total=int(meta["size_bytes"])
    ensure(total<=max_bytes,"Oversize sample; refusing archive recovery: "+str(directory))
    parts=[]
    for part in meta["parts"]:
        p=directory/part["name"]
        raw=p.read_bytes()
        ensure(len(raw)==part["bytes"] and sha(raw)==part["sha256"],
          "Unhydrated or corrupted sample LFS chunk: "+str(p))
        parts.append(raw)
    blob=b"".join(parts)
    ensure(len(blob)==total and sha(blob)==meta["sha256"],
      "Sample archive failed immutable checksum")
    return blob,meta

def inspect_heldout_controls(root,out):
    directory=root/"heldout"/"actions"
    records=[]
    for family in FAMILIES:
        files=sorted(directory.glob("actions-*_t3-b3-heldout-"+family+"-s10-n200-run41208513291.zip"))
        ensure(len(files)==1,"Expected one original independent Held Out control probe for "+family)
        blob,meta=read_archive(files[0])
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            csvs=[name for name in z.namelist()
              if name.endswith("scores.csv") and not name.endswith("control_scores.csv")]
            ensure(len(csvs)==1,"Expected one original scores.csv per sampled shard")
            with z.open(csvs[0]) as binary:
                stream=io.TextIOWrapper(binary,encoding="utf-8",newline="")
                reader=csv.DictReader(stream)
                ensure("model" in reader.fieldnames,"Archive original score lacks model identity")
                names=collections.Counter()
                for row in reader:names[row["model"]]+=1
            models=sorted(names)
            control=[m for m in models if any(token in m.lower() for token in (
                 "convex_mse","local_deterministic","projected","coordinate","quadratic","slsqp"))]
            records.append(dict(family=family,sample_n=200,eval_seed=10,
                archived_shard=files[0].name,archive_sha256=meta["sha256"],
                candidates_or_models=len(models),scored_rows=int(sum(names.values())),
                independent_deterministic_candidate_identifiers=control,
                actual_scoring_present_for_controls=bool(control),
                sample_scope="one original independent heldout shard per family"))
    out.mkdir(parents=True,exist_ok=True)
    (out/"sampled_original_heldout_model_inventory.json").write_text(json.dumps(records,indent=2)+"\n")
    (out/"ASSESSMENT.md").write_text(
      "# Independent deterministic control availability\n\n"
      "Six original Held Out score archives were recovered from Git LFS using the "
      "complete archived SHA256 manifest and inspected without calculating new scores. "
      "Each covers seed 10 and n=200 for one destination family. This is a **sampling "
      "probe**, not complete independent confirmation across all 18 blocks or ten seeds.\n\n"
      "Independent deterministic control identifiers found in sampled shards: "+
      str(sum(bool(r["independent_deterministic_candidate_identifiers"]) for r in records))+"/6.\n\n"
      "The already-recovered Discovery deterministic panel is training-only. "
      "Before any independent deterministic comparison, validate each control's exact "
      "candidate identity, original training provenance, all 10 evaluation seeds, "
      "and matched 241 support scenarios. If absent, another frozen-weight scoring "
      "job would be necessary and is **not authorized by this inspection**.\n")
    print("R1_ARCHIVE_DETERMINISTIC_SAMPLE_PASS",len(records),flush=True)

def inspect_quantile_data(root,out):
    mc=manifests(root,"montecarlo")
    heldout=manifests(root,"heldout")
    candidates=[r for r in mc if any(s in r["name"].lower()
      for s in ("heldout","mc","montecarlo","matrix"))]
    source_code=Path("scripts/t3_b3_heldout_seedwise.py")
    ensure(source_code.is_file(),"Absent original recovery program")
    # Only structural metadata; a .zip name is NOT proof of replicate-level losses.
    out.mkdir(parents=True,exist_ok=True)
    data=dict(total_complete_montecarlo_action_archives=len(mc),
      total_complete_heldout_action_archives=len(heldout),
      candidate_montecarlo_archives=len(candidates),
      sample_candidate_archive_names=[r["name"] for r in candidates[:60]],
      original_MC_code_sha256=sha(source_code.read_bytes()),
      replicate_level_loss_availability="NOT_YET_VERIFIED",
      next_validation="Recover one relevant 500-replicate component matrix, confirm known target and candidate W, compute scenario-level Q95 uncertainty only after provenance validation",
      no_new_replicates_generated=True)
    (out/"montecarlo_replication_source_index.json").write_text(json.dumps(data,indent=2)+"\n")
    (out/"ASSESSMENT.md").write_text(
      "# Q95 Monte Carlo uncertainty: archived input feasibility\n\n"
      "Complete archive manifest names and expected sizes were inventoried without "
      "downloading ~21 GB of archived Monte Carlo source datasets or rerunning a simulator. "
      "The existing R1 Q95 panel has evaluation-seed variation but cannot supply "
      "the 500 within-scenario replicate losses needed for a direct quantile Monte Carlo SE.\n\n"
      "Next: select and checksum an actual Monte Carlo replicate matrix, verify the "
      "clean target and frozen W mapping, then estimate Q95 uncertainty separately "
      "from across-seed bootstrap uncertainty. This remains an **input inspection "
      "candidate**, not a completed Q95 Monte Carlo SE.\n")
    print("R1_ARCHIVE_Q95_INDEX_PASS",len(mc),len(heldout),flush=True)

def inspect_cost(root,out):
    d=manifests(root,"discovery")
    prov=manifests(root,"provenance")
    names=[r for r in d+prov if any(term in r["name"].lower() for term in (
      "hpo","budget","nested","runtime","timing","registry","optimization"))]
    costs=[]
    for n in (200,1000,3000):
        p=Path("R1/runs/"+SOURCE+"/discovery/n"+str(n)+"/training_optimizer_costs.csv")
        ensure(p.exists(),"Missing already analyzed R1 optimizer costs")
        with p.open(newline="") as f:
            records=list(csv.DictReader(f))
        ensure(len(records)==240,"Expected 240 original frozen optimizer cost records per n")
        costs.extend(records)
    ensure(len(costs)==720,"Original optimizer evaluations registry incomplete")
    # This is a preflight only; evaluation counts and wall-clock timestamps differ.
    out.mkdir(parents=True,exist_ok=True)
    (out/"optimizer_cost_provenance_index.json").write_text(json.dumps({
      "original_frozen_optimizer_evaluation_records":len(costs),
      "discovery_archive_manifest_count":len(d),
      "provenance_action_archive_manifest_count":len(prov),
      "hpo_runtime_possible_metadata_source_names":[r["name"] for r in names],
      "tuning_wall_time_verified":False,
      "optimizer_wall_time_verified":False,
      "actual_evaluations_verified_from_prior_r1":True,
      "new_optimizer_executions":0,
      "needed_for_total_cost":"Locate immutable HPO trial logs and workflow timestamps, match by family, n, training seed, and method; then compare total compute under one policy"},
      indent=2)+"\n")
    (out/"ASSESSMENT.md").write_text(
      "# Full cost accounting: archived input feasibility\n\n"
      "All 720 frozen optimizer evaluation counts are already present in R1. "
      "They are **not** equivalent to total cost: Dirichlet and evolutionary "
      "methods may differ in actual evaluations, and hyperparameter tuning overhead "
      "must be accounted for separately. Possible original HPO metadata archives "
      "have been indexed by name only; their runtime records are not yet verified.\n\n"
      "Next: identify original run/job duration metadata and nested-HPO costs, "
      "preserve provenance for every comparison, and avoid treating nominal budgets "
      "as measured compute expense. No optimizer rerun is required for this inventory.\n")
    print("R1_ARCHIVE_COST_INDEX_PASS",len(costs),len(names),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",required=True,choices=("deterministic","q95","cost"))
    p.add_argument("--archive-root",type=Path,default=Path("data-archive"))
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    status=json.loads((a.archive_root/"catalog"/"status.json").read_text())
    ensure(status.get("complete") is True and status.get("pending_sources")==0,
      "Archive catalog not declared complete")
    if a.mode=="deterministic":inspect_heldout_controls(a.archive_root,a.output)
    elif a.mode=="q95":inspect_quantile_data(a.archive_root,a.output)
    else:inspect_cost(a.archive_root,a.output)
    (a.output/"PROBE_META.json").write_text(json.dumps(dict(
      mode=a.mode,only_read_existing_sources=True,
      no_new_mc_generation=True,no_optimizer_fitting=True,
      archive_inventory_scope=status["scope"],
      original_backup_status_verified=True,
      note="Feasibility audit only; presence of filenames does not certify usable raw data"),indent=2)+"\n")

if __name__=="__main__":main()
