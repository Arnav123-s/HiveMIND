import json
import random

import pytest

from team import ternary
from training import body_archive as archive, grow, self_replay
from training import kinds


def test_gather_preserves_individual_proof_and_excludes_false_confirmations(tmp_path):
    run = tmp_path / "run"
    home = run / "members"
    home.mkdir(parents=True)
    who = "t80+g51data"
    msgs = [{"role": "system", "content": "work"}, {"role": "user", "content": "solve"},
            {"role": "assistant", "content": "program"}]
    (home / "member1.json").write_text(json.dumps(dict(who=who, messages=msgs, program="print(5)", answer="5")))
    (home / "members.json").write_text(json.dumps({"agreeing": [1]}))
    def grade(verdicts):
        (run / "exam.json").write_text(json.dumps({"members": verdicts, "ok": True}))
        return grow.rows_of(run, "question", "a sum", 10005001)[0]
    right = {"member": 1, "who": who, "ok": True}
    assert not grade([right | {"who": "other"}])["verified_member"]
    assert not grade([right, right | {"ok": False}])["verified_member"]
    (run / "exam.json").write_text('{"ok":true}')
    assert not grow.rows_of(run, "question", "a sum", 10005001)[0]["verified_member"]
    source, dest = tmp_path / "new", tmp_path / "all"
    source.write_text(json.dumps(grade([right])) + "\n")
    grow.gather(dest, "g52", new=[source])
    row = json.loads(dest.read_text())
    body = {"dna": "t80", "generation": 55, "cells": ["g51data"]}
    bad = [row | change for change in ({"who": "t80+g5data"}, {"gen": "g56"}, {"seed": 20005550},
           {"verified_member": False, "agreed": False}, {"kind": kinds.written(next(iter(kinds.HELD_OUT)))[0]},
           {"task": "Kept   BACK"}, {"output": "DONE"})]
    eligible = row | {"task": "more"}
    legacy = {k: v for k, v in (row | {"agreed": False}).items() if k != "verified_member"}
    mixed = [*bad, eligible, legacy]
    assert self_replay.select(mixed, body, "t80", "g56", {"kept back"}) == {len(bad), len(bad) + 1}
    assert not self_replay.select(mixed, body, "t40", "g56", ())
    assert not self_replay.select(mixed, body, "t80", "g55", ())
    def selected(rows):
        return {rows[i]["task"] for i in self_replay.select(rows, body, "t80", "g56", {"kept back"}, limit=1)}
    assert selected(mixed) == selected(list(reversed(mixed)))


@pytest.mark.parametrize("ratio", [2, 3, 4])
def test_study_exposes_requested_dose_and_falls_back_without_reusing_exhausted_rows(ratio):
    # A successful pass advances the dose; an OOM skip returns its row to its subject.
    tags = ["new"] * 20 + ["old"] * 4 + ["other"]
    by = {t: [i for i, x in enumerate(tags) if x == t] for t in tags}
    study = grow.Study(by, rng=random.Random(7), most=1)
    schedule = self_replay.Schedule(ratio, tags, {"old"}, {"new"})
    for _ in range(2 * (ratio + 1)):
        s, i = schedule.pick(study)
        study.learned(s, 1)
        schedule.learned(s, i, 10)
    assert schedule.passes == {"fresh": 2 * ratio, "replay": 2, "other": 0}
    while got := schedule.pick(study):
        s, i = got
        study.learned(s, 1)
        schedule.learned(s, i, 10)
    assert schedule.report()["unique_rows"] == schedule.passes == {"fresh": 20, "replay": 4, "other": 1}
    a, b = [grow.Study(by, rng=random.Random(2)) for _ in (0, 1)]
    empty = self_replay.Schedule(ratio, tags, set(), {"new"})
    assert empty.pick(a) == b.pick()


def test_retains_distinct_verified_complements_and_routes_available_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_ARCHIVE_K", "3")
    def body(gen, wins):
        actor = f"t80+g{gen}trunk"
        f = tmp_path / (actor + ".gguf")
        f.write_text(actor)
        return dict(actor=actor, dna="t80", generation=gen, protocol="test", sha256=archive.digest(f),
                    asset=archive.asset(actor), results={q: {"ok": q in wins, "organ": organ}
                    for q, organ in zip("abcd", ("code", "words", "data", "code"))})
    a, b, c, d = (body(i, win) for i, win in enumerate(("a", "b", "c", "d"), 51))
    old = {"bodies": [b, a, d | {"protocol": "different"}]}
    kept = archive.retain(old, c)
    assert len(kept["bodies"]) == 3 and kept["incumbent_solved"] == 1 and kept["joint_solved"] == 3
    path = tmp_path / "body.json"
    path.write_text(json.dumps({"dna": "t80", "cells": ["g53code"], "trunk": "g53trunk"}))
    (tmp_path / "body_archive.json").write_text(json.dumps(kept))
    monkeypatch.setattr(ternary, "BODY", path)
    monkeypatch.setattr(ternary, "ADAPTERS", tmp_path)
    order = [c["actor"], "t80+g53code"]
    monkeypatch.setenv("HIVE_MEMBERS", ",".join(order))
    assert ternary.seating("write a poem") == [c["actor"], b["actor"], "t80+g53code"]
    assert ternary.seating("return a CSV table") == order
    (tmp_path / (b["actor"] + ".gguf")).write_text("changed digest")
    assert ternary.seating("write a poem") == order
    monkeypatch.setenv("HIVE_MEMBERS", c["actor"])
    assert ternary.seating("calculate 5+4") == [c["actor"]]
    assert archive.retain(kept, None) == kept


def test_collect_requires_matching_complete_pre_gate_coverage(tmp_path):
    body = {"generation": 53, "dna": "t80", "trunk": "g53trunk", "cells": ["g53code"]}
    for slot in range(1, 5):
        task, _, organ = archive.panel(slot)
        f = tmp_path / f"archive-before-{slot}" / "profile.json"
        f.parent.mkdir()
        r = {"actor": "t80+g53trunk", "slot": slot, "protocol": archive.protocol(), "question": archive.sha256(task.encode()).hexdigest(),
             "organ": organ, "sha256": "a" * 64, "ok": slot == 4}
        f.write_text(json.dumps(r))
    result = archive.collect(tmp_path, "before", body, "g54")
    assert result["asset"] == "t80.g53trunk.gguf" and len(archive.solved(result)) == 1
    f.write_text(json.dumps(r | {"sha256": "b" * 64}))
    assert archive.collect(tmp_path, "before", body, "g54") is None


def test_real_tiny_training_reports_only_completed_exposures(tmp_path, monkeypatch):
    from test_held_out import _lesson, _train

    body = tmp_path / "body.json"
    body.write_text(json.dumps({"generation": 2, "dna": "t17", "cells": ["g2code"]}))
    monkeypatch.setattr(ternary, "BODY", body)
    monkeypatch.setenv("HIVE_SELF_REPLAY", "1")
    rows = [_lesson("old", i, "t17+g2code")[0] | {"gen": "g2", "verified_member": True, "seed": 10000201}
            for i in range(4)]
    rows += [_lesson("new", i, "t17+g2code")[0] | {"gen": "g3"} for i in range(8)]
    meta, _ = _train(tmp_path, monkeypatch, rows, "", gen="g3")
    counts = meta["self_replay"]
    assert counts["passes"] == {"fresh": 16, "replay": 8, "other": 0}
    assert counts["status"] == "active" and counts["unique_rows"]["replay"] == 4
    assert sum(counts["passes"].values()) == meta["passes"] and min(counts["answer_tokens"][s] for s in ("fresh", "replay")) > 0


def test_both_gate_arms_route_only_after_complete_development_receipts(tmp_path):
    directory = tmp_path / "weights"
    directory.mkdir()
    old = {"dna": "t80", "generation": 51, "trunk": "g51trunk", "cells": ["g51code"]}
    for arm, actor, win in (("before", "t80+g51trunk", 2), ("after", "t80+g52trunk", 3)):
        weights = directory / (actor + ".gguf")
        weights.write_text(actor)
        for slot in range(1, 5):
            task, _, organ = archive.panel(slot)
            path = tmp_path / f"archive-{arm}-{slot}" / "profile.json"
            path.parent.mkdir()
            path.write_text(json.dumps({"actor": actor, "slot": slot, "protocol": archive.protocol(),
                "sha256": archive.digest(weights), "organ": organ, "question": archive.sha256(task.encode()).hexdigest(), "ok": slot == win}))
    roster = ["t80+g52trunk", "t80+g52code", "t80+g51code"]
    immutable = {}
    trial = archive.freeze(tmp_path, old, roster, directory, "g52", immutable)
    assert [r["actor"] for r in trial["bodies"]] == [roster[0], "t80+g51trunk"]
    assert trial["joint_solved"] == 2 and immutable == {}
    assert archive.route(roster, "data", trial, directory)[:2] == ["t80+g52trunk", "t80+g51trunk"]
    path.unlink()
    assert archive.freeze(tmp_path, old, roster, directory, "g52", immutable) == {}
    assert archive.freeze(tmp_path, old, ["t80+g51trunk", "t80+g51code"], directory, "g52", immutable) == {}
