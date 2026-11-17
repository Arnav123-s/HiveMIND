"""Every cell has its own engram memory, inherited down its line of descent (team/engram.py)."""
import json

import pytest

from team import engram, ternary

TASK = "add the percent of the apples sold in march to the table of fruit"
LIKE = "add the percent of the pears sold in march to the table of fruit"


@pytest.fixture
def store(tmp_path, monkeypatch):
    home = tmp_path / "engrams"
    home.mkdir()
    monkeypatch.setenv("HIVE_ENGRAMS_HOME", str(home))
    monkeypatch.setattr(ternary, "ENGRAMS", home)
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"dna": "t80", "cells": ["g41code", "g41data"],
                                "parents": {"g41code": "g34code", "g34code": "g27code", "g41data": "g34data"}}))
    monkeypatch.setattr(ternary, "BODY", body)

    def put(*lines, files=True):
        with open(home / "index.jsonl", "a") as f:
            for e in lines:
                e = {"dna": "t80", "task": LIKE, **e}
                f.write(json.dumps(e) + "\n")
                if files:
                    (home / f"{e['dna']}+{e['name']}.gguf").write_bytes(b"")
    return home, put


def test_lineage_walks_the_parents(store):
    assert engram.lineage("g41code") == ["g41code", "g34code", "g27code"]
    assert engram.lineage("t80+g41code") == ["g41code", "g34code", "g27code"]
    assert engram.lineage("g99new") == ["g99new"]  # its line not known: only itself
    assert engram.lineage(None) == [] and engram.lineage("") == []


def test_own_engrams_come_first(store):
    _, put = store
    put({"name": "eother", "cell": "g41data", "task": TASK.replace("apples", "plums")},  # more alike, but another line
        {"name": "eparent", "cell": "g34code", "task": LIKE},
        {"name": "eown", "cell": "g41code", "task": LIKE + " today"})
    assert engram.recall(TASK, "t80", cell="g41code") == ["eown", "eparent"]
    assert engram.recall(TASK, "t80", cell="t80+g41code", most=1) == ["eown"]


def test_a_child_recalls_its_ancestors(store):
    _, put = store
    put({"name": "egrand", "cell": "g27code"}, {"name": "eparent", "cell": "g34code"}, {"name": "eother", "cell": "g41data"})
    assert engram.recall(TASK, "t80", cell="g41code") == ["eparent", "egrand"]
    assert engram.recall(TASK, "t80", cell="g41data") == ["eother"]


def test_others_only_when_nothing_closer(store):
    _, put = store
    put({"name": "eother", "cell": "g41data"}, {"name": "efar", "cell": "g34code", "task": "fetch a page from the web"})
    assert engram.recall(TASK, "t80", cell="g41code") == ["eother"]  # its line's engram is not alike: another's is taken


def test_old_lines_without_a_cell_still_work(store):
    _, put = store
    put({"name": "eold"}, {"name": "eown", "cell": "g41code"}, {"name": "eother", "cell": "g41data"})
    assert engram.recall(TASK, "t80", cell="g41code") == ["eown", "eold"]
    assert engram.recall(TASK, "t80", cell="g41code", most=3) == ["eown", "eold"]  # others' not while anything closer passes
    assert sorted(engram.recall(TASK, "t80", most=3)) == ["eold", "eother", "eown"]  # no cell: as before, any of them


def test_folded_engrams_are_skipped(store):
    home, put = store
    put({"name": "eown", "cell": "g41code"}, {"name": "eparent", "cell": "g34code"})
    assert engram.fold(["eown", "enothere"], 42) == 1
    assert engram.recall(TASK, "t80", cell="g41code") == ["eparent"]
    assert next(json.loads(x) for x in (home / "index.jsonl").read_text().splitlines() if '"eown"' in x)["folded"] == 42
    assert engram.fold(["eown"], 43) == 0  # folded once is enough


def test_the_hive_engram_comes_last_beyond_most(store):
    home, put = store
    put({"name": "eown", "cell": "g41code"}, {"name": "eparent", "cell": "g34code"})
    assert "hive" not in engram.recall(TASK, "t80", cell="g41code")
    (home / "t80+hive.gguf").write_bytes(b"")
    assert engram.recall(TASK, "t80", cell="g41code") == ["eown", "eparent", "hive"]
    assert engram.recall("nothing like it at all", "t80", cell="g41code") == ["hive"]
    assert engram.recall(TASK, "t17", cell="g41code") == []  # another DNA's hive engram is not this one's


def test_missing_files_other_dna_and_the_same_task(store):
    _, put = store
    put({"name": "enofile", "cell": "g41code"}, files=False)
    put({"name": "eotherdna", "cell": "g41code", "dna": "t17"}, {"name": "esame", "cell": "g41code", "task": TASK})
    assert engram.recall(TASK, "t80", cell="g41code") == []


def test_write_records_the_cell(store, monkeypatch, tmp_path):
    home, _ = store
    import training.grow as grow
    monkeypatch.setattr(grow, "rows_of", lambda run, task: [{"messages": []}])
    monkeypatch.setattr(grow, "train", lambda *a, **k: {"megabytes": 1})
    assert engram.write(TASK, tmp_path, base="t80", cell="t80+g41code", log=lambda *a: None)
    assert json.loads((home / "index.jsonl").read_text().splitlines()[-1])["cell"] == "g41code"
    engram.write(LIKE, tmp_path, base="t80", log=lambda *a: None)
    assert json.loads((home / "index.jsonl").read_text().splitlines()[-1])["cell"] is None
