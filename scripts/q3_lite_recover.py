#!/usr/bin/env python3
"""Recover a complete prespecified 49-scenario score subset from an original full
241-scenario checkpoint, or copy an already-complete Q3 compact score.

The original source is never overwritten or modified. Training/evaluation seed
identity, frozen candidate weights, benchmark selection, and original Monte
Carlo loss values remain unchanged. Original source hashes are retained.
"""
from __future__ import annotations
import argparse,csv,hashlib,os,shutil,subprocess,tempfile
from pathlib import Path
from q3_lite_plan import grid

def digest(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("family")
    ap.add_argument("parameter_row",type=int)
    ap.add_argument("seed",type=int)
    ap.add_argument("n",type=int)
    ap.add_argument("run_id",type=int)
    ap.add_argument("artifact_name")
    ap.add_argument("reuse_kind",choices=("original","group","lite"))
    a=ap.parse_args()
    scenarios,_=grid();support=set(scenarios)
    allowed={"normal","lognormal","weibull","invgauss","exgaussian","exwald"}
    if a.family not in allowed or a.n not in (200,1000,3000) or not 40<=a.seed<=49:
        raise SystemExit("Invalid original compact recovery identity")
    if a.reuse_kind=="group":
        if not (a.artifact_name.startswith("q3-parametric-group-") and
                a.artifact_name.endswith(f"-run{a.run_id}")):
            raise SystemExit("Invalid complete-group original checkpoint name")
    else:
        prefix=(f"q3-lite-score-" if a.reuse_kind=="lite" else "t3-b3-parametric-score-")
        required=f"{prefix}{a.family}-p{a.parameter_row}-s{a.seed}-n{a.n}-run{a.run_id}-a"
        if not a.artifact_name.startswith(required) or not a.artifact_name[len(required):].isdigit():
            raise SystemExit("Original score artifact does not match identity")
    target=Path("artifacts/t3_b3_parametric_transfer")/a.family
    target=target/f"parameter_row{a.parameter_row:02d}"/f"seed{a.seed:02d}_n{a.n}"/"b0"
    if target.exists():raise SystemExit("Never overwrite an existing recovered score target")
    with tempfile.TemporaryDirectory(prefix="q3-compact-recover-") as path:
        root=Path(path)
        proc=subprocess.run(["gh","run","download",str(a.run_id),"--repo",
              os.environ["GITHUB_REPOSITORY"],"--name",a.artifact_name,"--dir",str(root)],
              text=True,capture_output=True)
        if proc.returncode:raise SystemExit("Original scored artifact retrieval failure: "+proc.stderr[:300])
        match=[]
        for p in root.rglob("score_manifest.csv"):
            with p.open(newline="") as f:rows=list(csv.DictReader(f))
            if len(rows)!=1:continue
            m=rows[0]
            if all(str(m.get(k))==want for k,want in (
                ("family",a.family),("parameter_row",str(a.parameter_row)),
                ("seed",str(a.seed)),("n",str(a.n)))):
                match.append((p,m))
        if len(match)!=1:raise SystemExit("Original artifact lacks exactly one matching score identity")
        original_manifest,m=match[0];score=original_manifest.with_name("scores.csv")
        if not score.exists() or digest(score)!=m.get("scores_sha256"):
            raise SystemExit("Original immutable score SHA-256 mismatch")
        if int(m.get("scenario_block",-1))!=0 or int(m.get("scenario_block_count",-1))!=1 or int(m.get("training_seed_count",-1))!=10:
            raise SystemExit("Original score frozen candidate/evaluation seed contract mismatch")
        source_protocol=m.get("protocol")
        if source_protocol not in ("t3_b3_parametric_transfer_score_v3","t3_q3_compact_parametric_score_v1"):
            raise SystemExit("Unrecognized scoring protocol")
        original_ids={int(x) for x in m["scenario_ids"].split(";") if x}
        if source_protocol=="t3_b3_parametric_transfer_score_v3" and (int(m["scenario_count"])!=241 or not support.issubset(original_ids)):
            raise SystemExit("Full original 241-scenario checkpoint lacks selected support")
        if source_protocol=="t3_q3_compact_parametric_score_v1" and (int(m["scenario_count"])!=49 or original_ids!=support):
            raise SystemExit("Already-reduced Q3 artifact violates exactly selected 49 scenario identities")
        with score.open(newline="") as f:
            reader=csv.DictReader(f);fields=reader.fieldnames or []
            if not {"scenario_id","family","source_family","evaluation_family",
              "parametric_seed","sample_n","parameter_row","training_seed_count",
              "model","mse","q95"}.issubset(fields):
                raise SystemExit("Original output science schema changed")
            raw=list(reader)
        filtered=[row for row in raw if int(row["scenario_id"]) in support]
        got={int(r["scenario_id"]) for r in filtered}
        if got!=support or len(filtered)!=49*6:
            raise SystemExit("Recovered original score subset is not the complete 49×6 model grid")
        for row in filtered:
            if (row["family"]!=a.family or row["source_family"]!=a.family or
                row["evaluation_family"]!=a.family or int(row["sample_n"])!=a.n or
                int(row["parameter_row"])!=a.parameter_row or int(row["parametric_seed"])!=a.seed or
                int(row["training_seed_count"])!=10):
                raise SystemExit("Mixed frozen candidate/evaluation identity in source rows")
        target.mkdir(parents=True)
        output=target/"scores.csv"
        with output.open("w",newline="") as f:
            wr=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
            wr.writeheader();wr.writerows(filtered)
        new=dict(m)
        new["protocol"]="t3_q3_compact_parametric_score_v1"
        new["scenario_count"]="49"
        new["scenario_ids"]=";".join(map(str,scenarios))
        new["score_rows"]=str(len(filtered))
        new["scores_sha256"]=digest(output)
        new["recovery"]="verified_original_score_subsample_prespecified_outcome_blind"
        new["source_artifact_name"]=a.artifact_name
        new["source_actions_run_id"]=str(a.run_id)
        new["source_score_sha256"]=digest(score)
        new["source_score_manifest_sha256"]=digest(original_manifest)
        new["original_source_scenario_count"]=m["scenario_count"]
        with (target/"score_manifest.csv").open("w",newline="") as f:
            wr=csv.DictWriter(f,fieldnames=list(new),lineterminator="\n")
            wr.writeheader();wr.writerow(new)
        print("Q3_COMPACT_VERIFIED_ORIGINAL_RECOVERY_PASS",a.family,a.parameter_row,a.seed,a.n,
              "original_scenarios",m["scenario_count"],"retained",len(filtered),"score_sha256",digest(output))

if __name__=="__main__":main()
