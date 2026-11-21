"""Build per-gate parent provenance from the run's initial commit and fetched plan/training log extracts."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def collect(repo, sources):
    receipts = json.loads((sources / "child-receipts.json").read_text())
    merges = {r["gen"]:r for r in json.loads((sources / "merge-receipts.json").read_text())}
    result = {"gates": {}, "released_snapshots": {}}
    for gen in range(53, 57):
        run = json.loads((sources / f"g{gen}.json").read_text())
        assert run["plan_complete"] < run["gate_start"]
        plans = json.loads((sources / f"plan{gen}.json").read_text())
        plan = {p["name"]: p["parent"] for p in plans}
        observed = {r["name"]: r for r in receipts if r["gen"] == gen}
        assert all(name in plan and r["parent"] == plan[name] for name, r in observed.items())
        ancestors = git(repo, "log", "--first-parent", "--format=%H", run["head_sha"], "--", "cells/body.json")
        sources_for_gate = []
        for rev in ancestors.decode().splitlines():
            data = git(repo, "show", rev + ":cells/body.json")
            body = json.loads(data)
            if body.get("dna") != "t80" or not body.get("parents"):
                continue
            sources_for_gate.append(rev)
            result["released_snapshots"][rev] = dict(generation=body.get("generation"),trunk=body.get("trunk"),
                body_sha256=hashlib.sha256(data).hexdigest(),parents=body["parents"])
        result["gates"][str(gen)] = {k:run[k] for k in ("run", "head_sha", "plan_job", "plan_complete", "gate_start")}
        merge = merges[gen]
        assert merge["time"] < run["gate_start"] and len(set(merge["trunk_of"])) > 1
        result["gates"][str(gen)].update(released_snapshots=sources_for_gate, plan=plan, training_receipts=observed,
                                         merge_receipt=merge)
    return result


def verify(repo, evidence):
    for rev, recorded in evidence["released_snapshots"].items():
        data = git(repo, "show", rev + ":cells/body.json")
        assert hashlib.sha256(data).hexdigest() == recorded["body_sha256"]
        assert json.loads(data)["parents"] == recorded["parents"]
    for gate in evidence["gates"].values():
        history=git(repo,"log","--first-parent","--format=%H",gate["head_sha"],"--","cells/body.json").decode().splitlines()
        assert all(rev in history for rev in gate["released_snapshots"])
        assert gate["plan_complete"] < gate["gate_start"] and gate["merge_receipt"]["time"] < gate["gate_start"]
        assert set(gate["plan"]) == set(gate["training_receipts"])
        for child, parent in gate["plan"].items():
            receipt=gate["training_receipts"][child]
            assert receipt["name"] == child and receipt["parent"] == parent
            assert receipt["downloaded_parent"] and receipt["mixed_with_trunk"] and receipt["inherited_matrices"] > 0


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",type=Path,default=Path("."))
    p.add_argument("--sources",type=Path,help="rebuild from extracted original plan and training logs")
    p.add_argument("--out",type=Path,default=Path(__file__).resolve().with_name("lineage.json"))
    a=p.parse_args()
    if a.sources:
        evidence=collect(a.repo,a.sources)
        a.out.write_text(json.dumps(evidence,indent=1,sort_keys=True)+"\n")
    else:
        evidence=json.loads(a.out.read_text())
    verify(a.repo,evidence)
