#!/usr/bin/env python3
"""R1 Stage 5A/5B and 12A: original-only, checksum-verifiable analysis.

Does not fit optimizers, simulate observations, estimate nominal coverage from
the observed point estimates, or edit existing R1 evidence.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import time
import urllib.error
import urllib.request
import zipfile

FAMILIES = ("normal", "lognormal", "weibull", "invgauss", "exgaussian", "exwald")
SIZES = (200, 1000, 3000)
METHODS = ("ga", "nsga2", "de", "dirichlet")
PATTERN = re.compile(r"^actions-(\d+)_t3-nested-(" + "|".join(FAMILIES) +
                     r")-seed(\d+)-n(200|1000|3000)-fold([1-5])[.]zip$")
FIELDS = ("family", "seed", "outer_fold", "sample_n", "engine", "trial",
          "inner_fold", "score", "objective_evaluations",
          "maximum_objective_evaluations", "training_scenarios",
          "scenario_evaluations", "elapsed_seconds", "early_stop_saved",
          "budget_policy")

def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

def save_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def inventory():
    result = {}
    for stage in ("misc", "discovery"):
        root = Path("data-archive") / stage / "actions"
        for manifest in root.glob("actions-*_t3-nested-*.zip/manifest.json"):
            m = PATTERN.fullmatch(manifest.parent.name)
            if not m:
                raise ValueError("Invalid original HPO archive label: " + str(manifest))
            aid, family, seed, n, fold = m.groups()
            key = (family, int(seed), int(n), int(fold))
            assert key not in result, ("Duplicate original nested fold", key)
            meta = json.loads(manifest.read_text())
            assert meta["complete"] is True and meta["schema_version"] == 1
            assert meta["source"]["artifact_id"] == int(aid)
            assert meta["source"]["name"] == f"t3-nested-{family}-seed{seed}-n{n}-fold{fold}.zip"
            assert len(meta["sha256"]) == 64 and int(meta["size_bytes"]) > 0
            assert meta["parts"] and all(len(x["sha256"]) == 64 for x in meta["parts"])
            result[key] = (manifest.parent, meta)
    expected = {(f, s, n, fold) for f in FAMILIES for s in range(10)
                for n in SIZES for fold in range(1, 6)}
    missing = expected - result.keys()
    extra = result.keys() - expected
    assert not missing and not extra and len(result) == 900, (
        "The exact 900 original nested HPO sources are required",
        len(result), sorted(missing)[:10], sorted(extra)[:10])
    return result

def restore_verified(directory, meta):
    h = hashlib.sha256()
    binary = io.BytesIO()
    total = 0
    for part in meta["parts"]:
        p = directory / part["name"]
        b = p.read_bytes()
        assert len(b) == int(part["bytes"]) and hashlib.sha256(b).hexdigest() == part["sha256"], (
            "Missing, unhydrated, or damaged LFS archive part", str(p))
        h.update(b)
        total += len(b)
        binary.write(b)
    assert total == meta["size_bytes"] and h.hexdigest() == meta["sha256"], (
        "Original artifact digest does not match the recovery manifest", str(directory))
    binary.seek(0)
    return binary

def preflight(args):
    items = inventory()
    runs = sorted({int(m["source"]["run_id"]) for _, m in items.values()})
    save(args.output, dict(status="manifest_inventory_only", expected=900,
          observed=len(items), expected_inner_fold_trials=900 * 4 * 8 * 3,
          source_runs=runs, archive_stages=["misc", "discovery"],
          integrity_scope="Manifest source identity and presence only; worker verifies restored bytes",
          new_training=False, new_simulations=False))
    print("R1_HPO_ORIGINAL_900_MANIFEST_PREFLIGHT_PASS", len(items), runs, flush=True)

def hpo(args):
    items = inventory()
    family, n = args.family, args.n
    records, provenance = [], []
    for seed in range(10):
        for fold in range(1, 6):
            archive, meta = items[(family, seed, n, fold)]
            raw = restore_verified(archive, meta)
            with zipfile.ZipFile(raw) as z:
                bad = z.testzip()
                assert bad is None, ("Corrupt ZIP entry", bad)
                members = [x for x in z.namelist()
                           if x.split("/")[-1] == "all_inner_fold_costs.csv"]
                assert len(members) == 1, ("Missing/duplicate original HPO ledger", str(archive), members)
                with z.open(members[0]) as stream:
                    lines = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
                    reader = csv.DictReader(lines)
                    assert set(FIELDS).issubset(reader.fieldnames or []), ("Missing original HPO fields", str(archive))
                    rows = list(reader)
            seen = set()
            for row in rows:
                engine = row["engine"]
                trial = int(row["trial"])
                inner = int(row["inner_fold"])
                key = (engine, trial, inner)
                assert engine in METHODS and 0 <= trial < 8 and inner in (1, 2, 3)
                assert key not in seen, ("Repeated HPO trial", archive, key)
                seen.add(key)
                assert (row["family"] == family and int(row["sample_n"]) == n
                        and int(row["seed"]) == seed and int(row["outer_fold"]) == fold), (
                            "Source archive and HPO trial provenance disagree", str(archive))
                used = int(row["objective_evaluations"])
                maximum = int(row["maximum_objective_evaluations"])
                scenario_count = int(row["training_scenarios"])
                scenario_evals = int(row["scenario_evaluations"])
                elapsed = float(row["elapsed_seconds"])
                assert 0 < used <= maximum and scenario_count > 0
                assert scenario_evals == used * scenario_count
                assert int(row["early_stop_saved"]) == maximum - used
                assert 0 <= elapsed < 1e9 and elapsed == elapsed
                assert row["budget_policy"] == "B3_EQUAL_MAX_BUDGET_ADAPTIVE_V2"
                row["original_source_run"] = meta["source"]["run_id"]
                row["archive_sha256"] = meta["sha256"]
                row["artifact_id"] = meta["source"]["artifact_id"]
                records.append(row)
            assert seen == {(e, t, i) for e in METHODS for t in range(8)
                            for i in (1, 2, 3)}, (
                                "An original nested HPO archive lacks its 96 trials", str(archive), len(seen))
            provenance.append(dict(family=family, n=n, seed=seed, outer_fold=fold,
                                   source_run=meta["source"]["run_id"],
                                   artifact_id=meta["source"]["artifact_id"],
                                   archive_sha256=meta["sha256"],
                                   archive_bytes=meta["size_bytes"], trial_rows=len(rows)))
    assert len(records) == 4800 and len(provenance) == 50
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    save_csv(out / "verified_inner_fold_costs.csv", records,
             list(FIELDS) + ["original_source_run", "archive_sha256", "artifact_id"])
    save_csv(out / "verified_original_archive_lineage.csv", provenance, list(provenance[0]))
    summaries = []
    for method in METHODS:
        records_m = [x for x in records if x["engine"] == method]
        assert len(records_m) == 1200
        summaries.append(dict(family=family, sample_n=n, engine=method,
           nested_outer_fold_archives=50, original_inner_fold_trials=len(records_m),
           objective_evaluations=sum(int(x["objective_evaluations"]) for x in records_m),
           maximum_objective_evaluations=sum(int(x["maximum_objective_evaluations"]) for x in records_m),
           early_stop_saved=sum(int(x["early_stop_saved"]) for x in records_m),
           scenario_evaluations=sum(int(x["scenario_evaluations"]) for x in records_m),
           observed_trial_elapsed_seconds=sum(float(x["elapsed_seconds"]) for x in records_m),
           measurement="sum of original per-inner-fold elapsed_seconds; not whole-job time"))
    save_csv(out / "hpo_cost_by_optimizer.csv", summaries, list(summaries[0]))
    save(out / "CHECK.json", dict(status="PASS", stage="5A", family=family, sample_n=n,
        restored_sha256_verified_sources=50, individual_trial_costs=len(records),
        methods=4, new_optimizer_fits=0, source_run_ids=sorted(set(x["source_run"] for x in provenance))))
    print("R1_STAGE5A_HPO_VERIFIED", family, n, len(provenance), len(records), flush=True)

def github_api(path, token):
    url = "https://api.github.com/" + path.lstrip("/")
    for attempt in range(5):
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "t3-r1-runtimes"})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.load(resp)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, http.client.IncompleteRead, ConnectionError, OSError, json.JSONDecodeError):
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)

def seconds(a, b):
    if not a or not b:
        return None
    x = dt.datetime.fromisoformat(a.replace("Z", "+00:00"))
    y = dt.datetime.fromisoformat(b.replace("Z", "+00:00"))
    return max(0., (y - x).total_seconds())

def timing(args):
    items = inventory()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "ALRIER/T3")
    assert token, "GitHub Actions read-only API token required"
    archive_runs = {int(m["source"]["run_id"]) for _, m in items.values()}
    run_ids = sorted(archive_runs | {41113724413, 41487091262})
    jobs, steps, missing = [], [], []
    for run_id in run_ids:
        try:
            run = github_api(f"repos/{repo}/actions/runs/{run_id}", token)
            workflow = run.get("name", "")
            page = 1
            while True:
                data = github_api(f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=30&page={page}&filter=all", token)
                batch = data.get("jobs", [])
                for job in batch:
                    item = dict(source_run=run_id, source_workflow=workflow,
                          job_id=job["id"], job_name=job.get("name"),
                          conclusion=job.get("conclusion"),
                          started_at=job.get("started_at"),
                          completed_at=job.get("completed_at"),
                          job_elapsed_seconds=seconds(job.get("started_at"),job.get("completed_at")),
                          scope="full GitHub Actions job, includes preparation, HPO, refit and upload")
                    jobs.append(item)
                    for step in job.get("steps", []):
                        steps.append(dict(source_run=run_id, job_id=job["id"],
                           job_name=job.get("name"), step_name=step.get("name"),
                           conclusion=step.get("conclusion"),
                           step_elapsed_seconds=seconds(step.get("started_at"),step.get("completed_at"))))
                if len(batch) < 30:
                    break
                page += 1
                assert page < 25, "Unbounded Actions history pagination"
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            missing.append(dict(source_run=run_id, reason=str(exc)))
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    save_csv(out/"original_actions_job_times.csv", jobs,
        ["source_run","source_workflow","job_id","job_name","conclusion",
         "started_at","completed_at","job_elapsed_seconds","scope"])
    save_csv(out/"original_actions_step_times.csv", steps,
        ["source_run","job_id","job_name","step_name","conclusion","step_elapsed_seconds"])
    save(out/"RUNTIME_SCOPE.json", dict(stage="5B",
        source_hpo_runs=sorted(archive_runs), additional_discovery_runs=[41113724413,41487091262],
        source_runs_consulted=run_ids, captured_job_rows=len(jobs),
        captured_step_rows=len(steps), unreachable_runs=missing,
        status="COMPLETE_API_HISTORY" if not missing else "PARTIAL_API_HISTORY",
        valid_inference="Job-stage wall-clock duration is not a per-engine final-fit timing measurement",
        per_engine_final_discovery_fit_elapsed_verified=False,
        no_optimizer_reexecution=True))
    print("R1_STAGE5B_ACTIONS_TIMING_AUDIT", len(jobs),len(steps),len(missing),flush=True)

def calibration(args):
    base = Path("R1/runs/44307352615/all_pairwise_global_holm.csv")
    with base.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 216
    counts = collections.Counter((r["family"],int(r["sample_n"]),r["metric"]) for r in rows)
    assert counts == {(f,n,metric):6 for f in FAMILIES for n in SIZES
                      for metric in ("mse","q95")}
    assert {int(r["independent_seeds"]) for r in rows} == {10}
    assert {r["method_a"] for r in rows} | {r["method_b"] for r in rows} == set(METHODS)
    scope = Path("R1/runs/44324757704/synthesis/table_RQ1_inferential_evidence_and_scope.csv")
    with scope.open(newline="") as inp:
        evidence = list(csv.DictReader(inp))
    assert len(evidence) >= 6
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    save_csv(out/"source_inferential_scope.csv", evidence, list(evidence[0]))
    save(out/"STAGE12A_FEASIBILITY.json", dict(stage="12A", status="FEASIBILITY_COMPLETE_COVERAGE_NOT_ESTABLISHED",
        checked_original_optimizer_contrasts=216,
        blocks=18, independent_evaluation_seeds_per_block=10,
        original_q95_mc_reps_per_scenario=500,
        known_generating_reference_effects_for_optimizer_comparison=False,
        independent_complete_resampling_of_selection_pipeline=False,
        original_selection_replayed_under_valid_null=False,
        global_fwer_control_validated=False,
        fdr_calibration_validated=False,
        selection_aware_nominal_95_percent_ci_coverage_verified=False,
        existing_sensitivity_evidence=[x["metric"] for x in evidence],
        source_t2_null_diagnostic_is_not_r1_calibration=True,
        stage12b_required_for_empirical_coverage_claims=True,
        next_stage="predeclare independent known-truth null/alternative experiments; replay selection and evaluation; assess empirical CI coverage, FWER/FDR and multiplicity under dependence",
        replay_requirements=[
          "freeze reference effects and null data-generating processes before simulation",
          "repeat selection including nested HPO and final fitting when those affect inference",
          "independently score held-out samples using known truth",
          "include training/evaluation-seed and scenario dependence in uncertainty calculation",
          "measure nominal 95% interval coverage and uncertainty in the coverage estimate",
          "measure familywise and false discovery error across the intended 216 hypotheses",
          "retain failure cases and preregister exclusion and stopping criteria"],
        no_new_simulations=True))
    (out/"INTERPRETATION.md").write_text(
      "# Stage 12A — Original-only calibration feasibility audit\n\n"
      "The 216 original method comparisons have 10 independent evaluation seeds in "
      "18 family/sample-size blocks, and the source reports 500 MC draws for conditional Q95. "
      "These are valid sources for existing point estimates and sensitivity checks. "
      "**They do not generate independent known-truth replays of the complete "
      "selection-and-inference pipeline.** The T2 null diagnostic has a different "
      "experimental scope and is not substituted for RQ1 calibration.\n\n"
      "No empirical nominal coverage, full-pipeline FWER, or FDR may be claimed from "
      "this audit. Stage 12B remains conditional and must be separately implemented "
      "and completed before making those claims.\n")
    print("R1_STAGE12A_ORIGINAL_ONLY_FEASIBILITY_PASS_WITH_COVERAGE_GAP", flush=True)

def finalize(args):
    root = Path(args.root)
    checks = sorted(root.glob("stage5a/*/n*/CHECK.json"))
    assert len(checks) == 18, ("Missing HPO source partitions", len(checks))
    audit = [json.loads(p.read_text()) for p in checks]
    assert all(x["status"] == "PASS" for x in audit)
    assert sum(x["restored_sha256_verified_sources"] for x in audit) == 900
    assert sum(x["individual_trial_costs"] for x in audit) == 86400
    totals = collections.defaultdict(lambda: collections.Counter())
    source_rows = []
    for p in sorted(root.glob("stage5a/*/n*/hpo_cost_by_optimizer.csv")):
        with p.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 4
        source_rows.extend(rows)
        for r in rows:
            t = totals[r["engine"]]
            for key in ("nested_outer_fold_archives","original_inner_fold_trials",
                        "objective_evaluations","maximum_objective_evaluations",
                        "early_stop_saved","scenario_evaluations"):
                t[key] += int(r[key])
            t["observed_trial_elapsed_seconds"] += float(r["observed_trial_elapsed_seconds"])
    summary = [dict(engine=method, **dict(totals[method])) for method in METHODS]
    assert len(source_rows) == 72
    assert all(x["nested_outer_fold_archives"] == 900 for x in summary)
    assert all(x["original_inner_fold_trials"] == 21600 for x in summary)
    save_csv(root/"stage5_cost_by_family_n_engine.csv", source_rows, list(source_rows[0]))
    save_csv(root/"stage5_hpo_cost_global_by_engine.csv", summary, list(summary[0]))
    stage5b = root/"stage5b/RUNTIME_SCOPE.json"
    stage12a = root/"stage12a/STAGE12A_FEASIBILITY.json"
    assert stage5b.is_file() and stage12a.is_file(), "Must retain historic timing and calibration feasibility reports"
    runtime = json.loads(stage5b.read_text())
    cal = json.loads(stage12a.read_text())
    digest = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "R1_STAGE5_12A_SHA256_MANIFEST.json":
            digest.append(dict(path=p.relative_to(root).as_posix(),
                               bytes=p.stat().st_size,
                               sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    save(root/"R1_STAGE5_12A_SHA256_MANIFEST.json", dict(stage="Q1 stages 5A 5B 12A",
         status="PASS_WITH_EXPLICIT_SCIENTIFIC_LIMITATIONS",
         verified_original_HPO_archives=900,
         verified_original_HPO_inner_trial_rows=86400,
         stage5B_scope=runtime["status"],
         stage12A_coverage_status=cal["status"],
         per_optimizer_final_fit_elapsed_validated=False,
         nominal_CI_coverage_validated=False,
         new_fits_or_simulations=False,
         files=digest))
    print("R1_STAGE5_12A_REPOSITORY_RECOVERY_PACKAGE_PASS",len(digest),flush=True)

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("preflight")
    a.add_argument("--output", required=True)
    a = sub.add_parser("hpo")
    a.add_argument("--family", choices=FAMILIES, required=True)
    a.add_argument("--n", type=int, choices=SIZES, required=True)
    a.add_argument("--output", required=True)
    a = sub.add_parser("timing")
    a.add_argument("--output", required=True)
    a = sub.add_parser("calibration")
    a.add_argument("--output", required=True)
    a = sub.add_parser("finalize")
    a.add_argument("--root", required=True)
    args = p.parse_args()
    {"preflight":preflight, "hpo":hpo, "timing":timing,
     "calibration":calibration, "finalize":finalize}[args.command](args)

if __name__ == "__main__":
    main()
