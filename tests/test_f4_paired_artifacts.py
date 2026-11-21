import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from training import exam
from training.experiments.astra_orders.worker_contracts import f4_paired as scorer
from training.experiments.astra_orders.worker_contracts.paired import INDEX

CHILD_SHA = "b" * 40
REGISTRATION = {"source_ref": "d" * 40, "file": "t80-hint-dream.gguf", "sha256": "a" * 64,
                "parent_sha256": scorer.PARENT, "stock_workflow_sha": scorer.STOCK_SHA}


def fixture(folder):
    stock = Path(scorer.__file__).with_name("g55-contemporaneous.sha256").read_bytes()
    roster = ",".join(Path(line.split()[1]).stem for line in stock.decode().splitlines())
    fixed = exam.held_exam()
    for arm, prefix, run, sha in (("stock", "f3", "101", scorer.STOCK_SHA), ("child", "f4", "202", CHILD_SHA)):
        manifest = stock if arm == "stock" else stock.replace(scorer.PARENT.encode(), REGISTRATION["sha256"].encode())
        successes = {r[0] for r in (fixed[:3] if arm == "stock" else fixed[3:6])}
        for seat in range(1, 9):
            rows = [{"id": tid, "task": task, "maker": tid[2:].rsplit("_", 1)[0], "ok": tid in successes}
                    for tid, _, _, task, _ in exam.held_share(fixed, seat, 8)]
            summary = {"exam": "held", "seat": seat, "seats": 8, "per": 3, "memory": "none", "members": roster,
                       "passed": sum(row["ok"] for row in rows), "tasks": len(rows)}
            assignment = {"GITHUB_RUN_ID": run, "GITHUB_SHA": sha, "ARM": arm, "SHARD": str(seat), "HIVE_MEMBERS": roster,
                          "AGENT_TEAM_SOLO": "2", "HIVE_ASSERT_FIRST": "0", "HIVE_PAGE_CHECKS": "0",
                          "HIVE_HTTP_CACHE": "0", "machine": "x86_64"}
            grade = json.dumps({"summary": summary, "tasks": rows}).encode()
            evidence = {"adapters.sha256": manifest, "roster.sha256": scorer.ROSTER_HASHES,
                        "familiar-index.sha256": f"{INDEX}  /tmp/checked.json\n".encode(),
                        "assignment.json": json.dumps(assignment).encode(), f"held_{seat}.json": grade}
            stem = folder / f"{prefix}-{arm}-{seat}-attempt-1"
            if arm == "stock":
                with ZipFile(stem.with_suffix(".zip"), "w") as z:
                    for name, data in evidence.items():
                        z.writestr(name, data)
            else:
                stem.mkdir()
                evidence["f4-adapter.json"] = json.dumps(REGISTRATION).encode()
                evidence["held.sha256"] = f"{hashlib.sha256(grade).hexdigest()}  held_{seat}.json\n".encode()
                for name, data in evidence.items():
                    (stem / name).write_bytes(data)


@pytest.fixture
def artifacts(tmp_path, monkeypatch):
    fixture(tmp_path)

    def registered(sha):
        assert sha == CHILD_SHA
        return REGISTRATION

    monkeypatch.setattr(scorer, "load_registration", registered)
    return tmp_path


def score(folder):
    return scorer.collect(folder, 1, "101", "202", CHILD_SHA)


def test_pairs_across_registered_runs_but_withholds_incomplete_kind_result(artifacts):
    result = score(artifacts)
    assert result["complete"] and result["paired"] == 30 and result["net"] == 0
    assert result["right_on_paired"] == {"stock": 3, "child": 3}
    assert result["kinds_passing_of_ten"] == {"stock": 1, "child": 1}
    assert result["net_kinds"] == 0 and not result["child_at_least_two_kinds"]
    assert len(result["gained"]) == len(result["lost"]) == 3
    assert len(result["gained_kinds"]) == len(result["lost_kinds"]) == 1
    (artifacts / "f4-child-1-attempt-1" / "held_1.json").unlink()
    partial = score(artifacts)
    assert not partial["complete"] and partial["paired"] == 26
    assert partial["kinds_passing_of_ten"] == {"stock": None, "child": None}
    assert partial["gained_kinds"] is partial["lost_kinds"] is partial["child_at_least_two_kinds"] is None
    assert partial["shards"][8]["status"] == "incomplete artifact"
    (artifacts / "f3-stock-1-attempt-1.zip").unlink()
    assert score(artifacts)["shards"][0]["status"] == "artifact missing"


@pytest.mark.parametrize(("file", "cooked", "error"), [
    ("adapters.sha256", lambda s: s.replace(REGISTRATION["sha256"], scorer.PARENT), "adapter manifest"),
    ("adapters.sha256", lambda s: s.splitlines()[0] + "\n" + s[s.index("\n") + 10:], "adapter manifest"),
    ("f4-adapter.json", lambda s: s.replace(REGISTRATION["source_ref"], "0" * 40), "registered F4 adapter"),
    ("roster.sha256", lambda s: s[:-2], "frozen G55 roster"),
    ("assignment.json", lambda s: s.replace('"202"', '"999"'), "wrong hosted run"),
    ("assignment.json", lambda s: s.replace(CHILD_SHA, "e" * 40), "wrong hosted run"),
    ("assignment.json", lambda s: s.replace('"HIVE_ASSERT_FIRST": "0"', '"HIVE_ASSERT_FIRST": "1"'), "wrong arm"),
    ("held_1.json", lambda s: s + " ", "grade checksum")])
def test_rejects_unmatched_child_artifacts(artifacts, file, cooked, error):
    path = artifacts / "f4-child-1-attempt-1" / file
    path.write_text(cooked(path.read_text()))
    with pytest.raises(ValueError, match=error):
        score(artifacts)


def test_rejects_unregistered_control(artifacts):
    with pytest.raises(ValueError, match="wrong hosted run"):
        scorer.collect(artifacts, 1, "303", "202", CHILD_SHA)
    with pytest.raises(ValueError, match="distinct stock and child run IDs"):
        scorer.collect(artifacts, 1, "202", "202", CHILD_SHA)


def test_rejects_parent_as_candidate():
    with pytest.raises(ValueError, match="fitted child"):
        scorer.child_manifest(b"", REGISTRATION | {"sha256": scorer.PARENT})
    with pytest.raises(ValueError, match="immutable adapter source"):
        scorer.child_manifest(b"", REGISTRATION | {"source_ref": "moving-branch"})
    with pytest.raises(ValueError, match="separately dispatched"):
        scorer.load_registration(scorer.STOCK_SHA)


def test_rejects_unequal_official_budget():
    from copy import deepcopy

    job = {"steps": [{"name": "Run this shard of the normal fixed held-out exam",
                      "run": "python training/exam.py held --seats 8 --per 3 --seconds 900", "timeout-minutes": 70}],
           "env": {"ARM": "stock", "AGENT_TEAM_SOLO": "2"}, "strategy": {"matrix": {"mode": ["stock", "f3"], "shard": list(range(1, 9))}}}
    stock = {"jobs": {"exam": job}}
    child = deepcopy(stock)
    child_job = child["jobs"]["exam"]
    child_job["env"].update(ARM="child", HIVE_ASSERT_FIRST="0", HIVE_PAGE_CHECKS="0", HIVE_HTTP_CACHE="0")
    del child_job["strategy"]["matrix"]["mode"]
    scorer.check_workflows(stock, child)
    child_job["steps"][0]["timeout-minutes"] = 60
    with pytest.raises(ValueError, match="official exam command"):
        scorer.check_workflows(stock, child)
