#!/usr/bin/env python3
"""Safely recover one original completed parameter-transfer score checkpoint.

Only results from a named previously verified T3 parameter-transfer Actions run
are accepted. File identities and hashes are checked before reuse. We never
alter an archived frozen estimator or recompute historical p/q values.
"""
from __future__ import annotations
import argparse,csv,hashlib,os,shutil,subprocess,tempfile
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("family")
    p.add_argument("parameter_row",type=int)
    p.add_argument("seed",type=int)
    p.add_argument("n",type=int)
    p.add_argument("run_id",type=int)
    p.add_argument("artifact_name")
    a=p.parse_args()
    assert a.family in {"normal","lognormal","weibull","invgauss","exgaussian","exwald"}
    assert a.parameter_row>=2 and 40<=a.seed<=49 and a.n in (200,1000,3000)
    prefix=f"t3-b3-parametric-score-{a.family}-p{a.parameter_row}-s{a.seed}-n{a.n}-run{a.run_id}-a"
    if not a.artifact_name.startswith(prefix) or not a.artifact_name[len(prefix):].isdigit():
        raise SystemExit("Original score artifact identity does not match requested transfer shard")
    root=Path("artifacts/t3_b3_parametric_transfer")/a.family
    root/=f"parameter_row{a.parameter_row:02d}"/f"seed{a.seed:02d}_n{a.n}"/"b0"
    if root.exists():
        raise SystemExit("Refusing to overwrite existing score output")
    with tempfile.TemporaryDirectory(prefix="q3-recover-") as d:
        tmp=Path(d)
        proc=subprocess.run(["gh","run","download",str(a.run_id),"--repo",os.environ["GITHUB_REPOSITORY"],
            "--name",a.artifact_name,"--dir",str(tmp)],capture_output=True,text=True)
        if proc.returncode:raise SystemExit("Cannot recover original Actions shard: "+proc.stderr[:600])
        candidates=list(tmp.rglob("scores.csv"))
        if len(candidates)!=1:raise SystemExit("Original Actions artifact must contain exactly one scores.csv")
        score=candidates[0];manifest=score.with_name("score_manifest.csv")
        if not manifest.is_file():raise SystemExit("Original score manifest absent")
        with manifest.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
        if len(rows)!=1:raise SystemExit("Original score manifest not singleton")
        m=rows[0]
        for k,want in (("family",a.family),("parameter_row",str(a.parameter_row)),
            ("seed",str(a.seed)),("n",str(a.n)),("protocol","t3_b3_parametric_transfer_score_v3"),
            ("selection","frozen_discovery_W_no_retuning")):
            if str(m.get(k))!=want:raise SystemExit(f"Original artifact identity mismatch {k}: {m.get(k)} != {want}")
        if any(int(m[k])!=v for k,v in (("scenario_block",0),("scenario_block_count",1),
            ("scenario_count",241),("training_seed_count",10))):
            raise SystemExit("Original score lacks full 241-scenario and 10-training-seed contract")
        if digest(score)!=m.get("scores_sha256"):
            raise SystemExit("Original score artifact SHA-256 mismatch")
        if len({int(q) for q in m["scenario_ids"].split(";") if q})!=241:
            raise SystemExit("Original score scenario identity count invalid")
        with score.open(newline="",encoding="utf-8") as f:
            r=csv.DictReader(f)
            must={"family","parameter_row","parametric_seed","sample_n","source_family",
                  "evaluation_family","mse","q95","scenario_id","model"}
            if not must.issubset(set(r.fieldnames or [])):
                raise SystemExit("Original score columns invalid")
            rows_seen=0
            for z in r:
                if z["family"]!=a.family or int(z["parameter_row"])!=a.parameter_row or int(z["parametric_seed"])!=a.seed or int(z["sample_n"])!=a.n:
                    raise SystemExit("Unexpected mixed shard identity in historical score")
                rows_seen+=1
            if rows_seen<241*4:raise SystemExit("Score rows incomplete")
        root.mkdir(parents=True)
        shutil.copy2(score,root/"scores.csv")
        shutil.copy2(manifest,root/"score_manifest.csv")
        print("Q3_ORIGINAL_SHARD_REUSED_VERIFIED",a.artifact_name,rows_seen,digest(root/"scores.csv"))

if __name__=="__main__":main()
