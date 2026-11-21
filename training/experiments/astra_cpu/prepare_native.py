"""Materialize the three exact original archive rows and verify the two checked parent files."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request

HERE=Path(__file__).resolve().parent
RELEASE="https://github.com/Arnav123-s/HiveMIND/releases/download/hive-grown/"
WEIGHTS={
    "t80.g53sources2.safetensors":"dbd31660e52ba2f45e5a80d087b4e63da735a5ac71b33e0cb9b73a72fad4ef38",
    "t80.g55trunk.safetensors":"6d2b50f593941b73e564286a3889768948bf539fec5517c6b884cd2c390d0ab0",
}


def prepare(folder):
    rows=gzip.decompress((HERE/"input-rows.jsonl.gz").read_bytes()).splitlines(keepends=True)
    specs=sum([json.loads((HERE/name).read_text())["rows"] for name in ("selected.json","overcap.json")],[])
    assert len(rows)==len(specs)==3
    for data,spec in zip(rows,specs,strict=True):
        canonical=json.dumps(json.loads(data),sort_keys=True).encode()
        assert hashlib.sha256(canonical).hexdigest()==spec["row_sha256"]
    for group,lines in (("panel",rows[:2]),("overcap",rows[2:])):
        dest=folder/group
        dest.mkdir(parents=True,exist_ok=True)
        (dest/"rows.jsonl").write_bytes(b"".join(lines))
    for name,sha in WEIGHTS.items():
        path=folder/name
        if not path.exists():
            urllib.request.urlretrieve(RELEASE+name,path)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
            raise ValueError(f"{name} does not match the measured release weights")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder",type=Path)
    prepare(p.parse_args().folder)
