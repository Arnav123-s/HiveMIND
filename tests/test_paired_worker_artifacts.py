import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from training import exam
from training.experiments.astra_orders.worker_contracts import paired


def write_shards(root):
    fixed = exam.held_exam()
    for arm in paired.ARMS:
        flag = "1" if arm == "f3" else "0"
        for seat in range(1, 9):
            rows = [{"id": tid, "maker": tid[2:].rsplit("_", 1)[0], "task": task,
                     "ok": arm == "f3" and tid in {r[0] for r in fixed[:4]}}
                    for tid, _, _, task, _ in exam.held_share(fixed, seat, 8)]
            stuff = {
                "assignment.json": json.dumps({"ARM": arm, "SHARD": str(seat), "AGENT_TEAM_SOLO": "2",
                                               "HIVE_ASSERT_FIRST": flag, "HIVE_PAGE_CHECKS": flag,
                                               "HIVE_HTTP_CACHE": flag, "GITHUB_RUN_ID": "fixture",
                                               "GITHUB_SHA": "local-control", "HIVE_MEMBERS": "same"}),
                "adapters.sha256": Path(paired.__file__).with_name("g55-contemporaneous.sha256").read_bytes(),
                "roster.sha256": "same bytes",
                "familiar-index.sha256": paired.INDEX + "  /tmp/checked-tasks.json",
                f"held_{seat}.json": json.dumps({"summary": {"exam": "held", "seat": seat}, "tasks": rows})}
            stem = root / f"f3-{arm}-{seat}-attempt-1"
            if arm == "stock":
                with ZipFile(stem.with_suffix(".zip"), "w") as z:
                    for name, data in stuff.items():
                        z.writestr(name, data)
            else:
                stem.mkdir()
                for name, data in stuff.items():
                    (stem / name).write_bytes(data if isinstance(data, bytes) else data.encode())


def test_pairs_only_matching_official_tasks_and_handles_missing_shard(tmp_path):
    write_shards(tmp_path)
    result = paired.collect(tmp_path, 1)
    assert result["complete"] and result["paired"] == 30 and result["at_least_four_more"]
    assert result["right_on_paired"] == {"stock": 0, "f3": 4}
    assert result["kinds_passing_of_ten"] == {"stock": 0, "f3": 1}
    (tmp_path / "f3-stock-1-attempt-1.zip").unlink()
    partial = paired.collect(tmp_path, 1)
    assert not partial["complete"] and partial["paired"] == 26
    assert partial["at_least_four_more"] is None
    assert len(partial["missing"]["stock"]) == 4 and not partial["missing"]["f3"]


def test_rejects_cross_run_artifacts(tmp_path):
    write_shards(tmp_path)
    assignment = tmp_path / "f3-f3-1-attempt-1" / "assignment.json"
    data = json.loads(assignment.read_bytes())
    data["GITHUB_RUN_ID"] = "another-run"
    assignment.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="workflow run"):
        paired.collect(tmp_path, 1)
