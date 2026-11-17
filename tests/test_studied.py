"""Of the cells of one generation, the one that made more training steps sits first and has children first
(cells/studied.json; training/lineage.py, team/ternary.py). g38: three code children, 67, 206 and 375 steps."""
import json

from team import ternary
from training import lineage

STEPS = {"g38code": 67, "g38code2": 206, "g38code3": 375, "g38words": 35, "g38words2": 468, "g34code": 375, "g34code2": 235}
PARENTS = {"g34code": "g27code", "g34code2": "g24code", "g38code": "g28code", "g38code2": "g27code", "g38code3": "g24code",
           "g27code": "g24code", "g28code": "g24code", "g38words": "g28words", "g38words2": "g27words"}
CELLS = ["g24code", "g27code", "g28code", "g34code", "g34code2", "g38code", "g38code2", "g38code3", "g38words", "g38words2"]


def body(tmp_path, monkeypatch, steps=STEPS):
    b = tmp_path / "body.json"
    b.write_text(json.dumps({"dna": "t80", "generation": 38, "cells": CELLS, "parents": PARENTS, "trunk": "g38trunk"}))
    if steps is not None:
        (tmp_path / "studied.json").write_text(json.dumps({"t80": steps}))
    monkeypatch.setattr(ternary, "BODY", b)
    monkeypatch.setenv("HIVE_MEMBERS", ",".join(f"t80+{c}" for c in ["g38trunk"] + CELLS))
    for k in ("HIVE_SEATING", "HIVE_ROTATE", "HIVE_KIND"):
        monkeypatch.delenv(k, raising=False)


def test_the_sibling_that_studied_more_takes_the_seat(tmp_path, monkeypatch):
    body(tmp_path, monkeypatch)
    task = "Write and run a Python program that prints the first ten primes."
    assert ternary.organ(task) == "code"
    seats = ternary.seating(task)
    assert seats[:3] == ["t80+g38trunk", "t80+g38code3", "t80+g38code2"]   # by name it was g38code, then g38code2
    assert seats.index("t80+g38code") < seats.index("t80+g34code")          # still before every older cell


def test_with_no_record_of_steps_the_seats_are_as_they_were(tmp_path, monkeypatch):
    body(tmp_path, monkeypatch, steps=None)
    seats = ternary.seating("Write and run a Python program that prints the first ten primes.")
    assert seats[:3] == ["t80+g38trunk", "t80+g38code", "t80+g38code2"]


def test_the_best_taught_of_a_generation_has_children_first():
    b = {"dna": "t80", "generation": 39, "cells": CELLS, "parents": PARENTS}
    plan = lineage.plan("g40", "t80", b, steps=STEPS)
    code = [c["parent"] for c in plan if c["organ"] == "code"]
    assert code[:3] == ["g38code3", "g38code2", "g38code"]
    assert [c["parent"] for c in plan if c["organ"] == "words"][:2] == ["g38words2", "g38words"]
    assert [c["parent"] for c in lineage.plan("g40", "t80", b, steps={}) if c["organ"] == "code"][:3] == ["g38code", "g38code2", "g38code3"]
    # a trial's one child an organ, and the one cell an organ that answers a single message
    assert lineage.plan("g40", "t80", b, organs=["code"], steps=STEPS)[0]["parent"] == "g38code3"
    assert "g38code3" in lineage.members("t80", b, few=True, steps=STEPS) and "g38code" not in lineage.members("t80", b, few=True, steps=STEPS)
    assert "g38code" in lineage.members("t80", b, few=True, steps={})


def test_steps_are_kept_from_the_cells_own_records(tmp_path):
    got = tmp_path / "got"
    got.mkdir()
    (got / "t80.g39code.json").write_text(json.dumps({"steps": 120, "slices": 3}))
    (got / "t80.g39code2.json").write_text(json.dumps({"steps": 0}))
    (got / "t80.g39trunk.json").write_text(json.dumps({"trunk_of": []}))
    (got / "t17.g39data.json").write_text(json.dumps({"steps": 9}))
    (got / "t80.g39words.json").write_text("not json")
    kept = tmp_path / "studied.json"
    kept.write_text(json.dumps({"t80": {"g38code": 67}, "t17": {"g5code": 4}}))
    assert lineage.keep_studied("t80", got, kept) == {"g39code": 120}
    assert lineage.studied("t80", kept) == {"g38code": 67, "g39code": 120} and lineage.studied("t17", kept) == {"g5code": 4}
    assert lineage.studied("t80", tmp_path / "none.json") == {}
