#!/usr/bin/env python3
"""Rebuild original Actions or Zenodo archive and check SHA-256 + ZIP integrity."""
import argparse,hashlib,json,pathlib,zipfile
p=argparse.ArgumentParser()
p.add_argument("artifact_dir",type=pathlib.Path)
p.add_argument("--output",required=True,type=pathlib.Path)
a=p.parse_args()
m=json.loads((a.artifact_dir/"manifest.json").read_text())
a.output.parent.mkdir(parents=True,exist_ok=True)
h=hashlib.sha256();n=0
with a.output.open("wb") as out:
    for part in m["parts"]:
        path=a.artifact_dir/part["name"]
        check=hashlib.sha256();count=0
        with path.open("rb") as f:
            for data in iter(lambda:f.read(4*1024*1024),b""):
                out.write(data);h.update(data);check.update(data)
                n+=len(data);count+=len(data)
        if check.hexdigest()!=part["sha256"] or count!=part["bytes"]:
            raise ValueError(f"Missing/corrupt LFS part {path}")
if n!=m["size_bytes"] or h.hexdigest()!=m["sha256"]:
    raise ValueError("Original archive checksum mismatch")
if a.output.suffix==".zip":
    with zipfile.ZipFile(a.output) as z:
        broken=z.testzip()
        if broken:raise ValueError("Corrupt ZIP member: "+broken)
print("VERIFIED",a.output,n,h.hexdigest())
