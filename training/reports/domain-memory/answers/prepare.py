"""Recreate the exact measured runtime in a new Git worktree."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent


def prepare(arm, checkout, weights):
    env = json.loads((HERE / "environment.json").read_text())
    if checkout.exists():
        raise ValueError(f"Choose a new checkout path. {checkout} already exists.")
    if arm in ("bank_v1", "bank_final"):
        bank = env["primary_engram_store"] if arm == "bank_v1" else env["final_system"]["bank"]
        index = HERE / ("index-v1.jsonl" if arm == "bank_v1" else "index-final.jsonl")
        files = {weights / name: digest for name, digest in bank["files"].items()}
        files[index] = bank["index_sha256"]
        for path, expected in files.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Measured weight or index mismatch for {path}")
        checkout.mkdir(parents=True)
        for path in files:
            shutil.copyfile(path, checkout / ("index.jsonl" if path == index else path.name))
        return
    root = subprocess.check_output(["git", "-C", HERE, "rev-parse", "--show-toplevel"], text=True).strip()
    commit = env["final_system"]["source_commit"] if arm == "final_system" else env["baseline_checkout"]
    subprocess.run(["git", "-C", root, "worktree", "add", "--detach", checkout, commit], check=True)
    if arm in ("baseline", "final_system"):
        return
    name = {"signal_only": "signal", "scope_followup": "integrated"}.get(arm, arm)
    hashes = env[name + "_snapshot_changes_from_baseline"]
    for filename in hashes:
        data = subprocess.check_output(["git", "-C", root, "show", env["snapshot_file_source"] + ":" + filename])
        target = checkout / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    patch = gzip.decompress((HERE / (name + ".patch.gz")).read_bytes())
    subprocess.run(["git", "-C", checkout, "apply", "--whitespace=nowarn", "-"], input=patch, check=True)
    for filename, expected in hashes.items():
        if hashlib.sha256((checkout / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Snapshot mismatch for {filename}")
    if arm == "scope_followup":
        for filename, expected in env["scope_followup_files"].items():
            data = subprocess.check_output(["git", "-C", root, "show", env["scope_followup_source"] + ":" + filename])
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f"Follow-up snapshot mismatch for {filename}")
            (checkout / filename).write_bytes(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arm", choices=("baseline", "signal_only", "integrated", "scope_followup", "bank_v1",
                                         "final_system", "bank_final"))
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--weights", type=Path, default=HERE.parents[3] / "cells" / "engrams",
                        help="location of the four original qualified weights when preparing bank_v1")
    args = parser.parse_args()
    prepare(args.arm, args.checkout.resolve(), args.weights)
