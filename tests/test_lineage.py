import json

from team import ternary
from training import grow_record, lineage


def test_a_child_of_code_is_still_code():
    assert ternary.leans("t80+g24code2") == "code" and ternary.leans("t80+g24code") == "code"
    assert lineage.organ_of("g24words12") == "words" and lineage.born("g24words12") == 24


def test_a_new_dna_starts_with_one_cell_of_each_organ_and_trials_keep_the_old_way():
    body = {"dna": "t17", "generation": 11, "cells": ["g11code", "g11data"]}
    first = lineage.plan("g30", "t80", body)
    assert [c["name"] for c in first] == ["g30sources", "g30code", "g30data", "g30words"] and not any(c["parent"] for c in first)
    old = lineage.plan("g30", "t17", body, organs=["code", "words"])
    assert [(c["name"], c["parent"]) for c in old] == [("g30code", "g11code"), ("g30words", "")]
    assert old[0]["suffix"] == "code"


def test_the_body_grows_like_fibonaccis_rabbits_until_the_runners_limits():
    body = {"dna": "t80", "generation": 0, "cells": [], "parents": {}}
    sizes = []
    for g in range(1, 9):
        gen = f"g{g}"
        kids = lineage.plan(gen, "t80", body)
        names = [k["name"] for k in kids]
        assert len(set(names)) == len(names) and all(n.startswith(gen) for n in names)
        assert len(kids) <= lineage.MOST_CHILDREN
        parents = dict(body["parents"], **{k["name"]: k["parent"] for k in kids if k["parent"]})
        cells, _ = lineage.grown_body(body["cells"], names, parents)
        body = {"dna": "t80", "generation": g, "cells": cells, "parents": parents}
        sizes.append(len(cells))
    # 4 first cells; then every grown cell has a child, the young wait one generation: 1, 2, 3, 5 an organ ...
    assert sizes[:4] == [4, 8, 12, 20]
    # ... until the body is full, and every organ still has its cells
    assert max(sizes) == lineage.MOST_CELLS and sizes[-1] == lineage.MOST_CELLS
    assert {lineage.organ_of(c) for c in body["cells"]} == set(lineage.ORGANS)


def test_past_the_runners_limit_the_organs_take_turns_and_the_oldest_carried_line_gives_way():
    cells = [f"g{g}{o}" for g in (1, 2, 3) for o in lineage.ORGANS]
    kids = lineage.plan("g5", "t80", {"dna": "t80", "generation": 4, "cells": cells})
    assert len(kids) == lineage.MOST_CHILDREN and [k["organ"] for k in kids[:4]] == list(lineage.ORGANS)
    assert kids[0]["parent"] == "g3sources" and kids[4]["parent"] == "g2sources"  # the newest parents first
    parents = {"g2code": "g1code", "g3code": "g2code"}
    kept, retired = lineage.grown_body(["g1code", "g2code", "g3code", "g1data"], ["g5code"], parents, most=3)
    # g1code and g2code live on in g3code; g1data's line has no one else: it stays
    assert retired == ["g1code", "g2code"] and kept == ["g3code", "g1data", "g5code"]


def test_a_child_does_not_check_its_own_parent(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_MEMBERS", "t80+g1code,t80+g1data,t80+g2code,t80+g3code")
    monkeypatch.delenv("HIVE_SEATING", raising=False)
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"dna": "t80", "cells": [], "parents": {"g2code": "g1code", "g3code": "g2code"}}))
    monkeypatch.setattr(ternary, "BODY", body)
    task = "Write a python function that sums the primes below 100"
    # the newest code cell first; the second seat is from another line (g1data), not its own parent or grandparent
    assert ternary.seating(task, "") == ["t80+g3code", "t80+g1data", "t80+g2code", "t80+g1code"]
    # a body with no lines of descent is seated as before, the newest first
    body.write_text(json.dumps({"dna": "t80", "cells": []}))
    assert ternary.seating(task, "")[:2] == ["t80+g3code", "t80+g2code"]


def _gate(folder, arm, passed, members):
    d = folder / f"gate-{arm}-1"
    d.mkdir(parents=True)
    tasks = [{"kind": "units", "ok": True, "task": "Calculate 3 + 4", "members": members}]
    (d / "x.json").write_text(json.dumps({"summary": {"passed": passed, "tasks": 8, "minutes": 5}, "tasks": tasks}))


def test_every_generations_children_join_the_body_and_whose_they_are_is_kept(tmp_path, monkeypatch):
    folder, got = tmp_path / "gate", tmp_path / "got"
    got.mkdir()
    _gate(folder, "after", 1, [{"who": "t80+g8code", "ok": False}])  # a poor pulse decides nothing
    for c, p in (("g8code", "g7code"), ("g8code2", "g6code"), ("g8words", "g7words")):
        (got / f"t80.{c}.gguf").write_text("x")
        (got / f"t80.{c}.json").write_text(json.dumps({"rows": 3, "seconds": 60, "parent_cell": p}))
    (got / "t80.g88code.gguf").write_text("x")  # another generation's cell, not this one's
    (got / "t80.g88code.json").write_text("{}")
    body, strengths, record = tmp_path / "body.json", tmp_path / "strengths.json", tmp_path / "g.jsonl"
    body.write_text(json.dumps({"dna": "t80", "generation": 7, "cells": ["g6code", "g7code", "g7words"], "parents": {"g7code": "g6code"}}))
    monkeypatch.setattr(grow_record, "BODY", body)
    monkeypatch.setattr(grow_record, "STRENGTHS", strengths)
    monkeypatch.setattr(grow_record, "RECORD", record)
    grow_record.gate([str(folder), str(got), "g8", "--dna", "t80", "--grow"])
    line = json.loads(record.read_text())
    assert line["kept"] and line["cells"] == ["g8code", "g8code2", "g8words"] and "1 of 8" in line["why"]
    b = json.loads(body.read_text())
    assert b["cells"] == ["g6code", "g7code", "g7words", "g8code", "g8code2", "g8words"] and b["generation"] == 8
    assert b["parents"] == {"g7code": "g6code", "g8code": "g7code", "g8code2": "g6code", "g8words": "g7words"}
    assert not strengths.exists()  # nothing is counted
    # the first body of a new DNA: its first cells, whatever the body of another DNA was
    body.write_text(json.dumps({"dna": "t17", "generation": 11, "cells": ["g11code"]}))
    grow_record.gate([str(folder), str(got), "g8", "--dna", "t80", "--grow"])
    assert json.loads(body.read_text())["cells"] == ["g8code", "g8code2", "g8words"]
