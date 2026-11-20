"""Engrams switched on as strongly as they match (team/engram.py recall_scaled), matched by embeddings when asked
(HIVE_ENGRAM_MATCH=embed, falling back to words), and the strengths carried to the runtime (team/ternary.py). No model
and no server: the runtime's answers are stood in for."""
import json

import pytest

from team import engram, ternary

TASK = "add the percent of the apples sold in march to the table of fruit"
LIKE = "add the percent of the pears sold in march to the table of fruit"
HALF = "add the percent of the pears sold in june to the table of nuts"


@pytest.fixture
def store(tmp_path, monkeypatch):
    home = tmp_path / "engrams"
    home.mkdir()
    monkeypatch.setattr(ternary, "ENGRAMS", home)
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"dna": "t80", "cells": ["g41code"], "parents": {"g41code": "g34code"}}))
    monkeypatch.setattr(ternary, "BODY", body)
    for k in ("HIVE_ENGRAM_MATCH", "HIVE_ENGRAM_GAIN", "HIVE_HIVE_SCALE", "HIVE_ENGRAM_EMBED_LEAST", "HIVE_ENGRAM_EMBED_URL"):
        monkeypatch.delenv(k, raising=False)

    def put(*lines):
        with open(home / "index.jsonl", "a") as f:
            for e in lines:
                e = {"dna": "t80", "cell": "g41code", **e}
                f.write(json.dumps(e) + "\n")
                (home / f"t80+{e['name']}.gguf").write_bytes(b"")
    return home, put


def test_gate_follows_the_match():
    assert engram.gate(0.34, 0.34) == 0.25           # just alike enough: the floor
    assert engram.gate(1.0, 0.34) == 1.0             # the same task: full strength
    assert engram.gate(0.5, 0.34, gain=2.0) == round((0.5 - 0.34) / 0.66 * 2, 3)
    assert engram.gate(0.9, 0.34, gain=2.0) == 1.0   # capped
    assert engram.gate(0.4, 0.34, gain=1.0) == 0.25  # never below the floor


def test_recall_scaled_gives_each_its_strength_and_the_hive_a_modest_one(store, monkeypatch):
    home, put = store
    put({"name": "elike", "task": LIKE}, {"name": "ehalf", "task": HALF})
    assert engram.recall(TASK, "t80", cell="g41code") == ["elike", "ehalf"]  # the old answer, unchanged: names only
    got = dict(engram.recall_scaled(TASK, "t80", cell="g41code"))
    assert list(got) == ["elike", "ehalf"]
    assert got["elike"] > got["ehalf"] >= 0.25 and got["elike"] <= 1.0
    (home / "t80+hive.gguf").write_bytes(b"")
    assert engram.recall_scaled(TASK, "t80", cell="g41code")[-1] == ("hive", 0.5)
    monkeypatch.setenv("HIVE_HIVE_SCALE", "0.3")
    assert engram.recall_scaled("nothing like it", "t80", cell="g41code") == [("hive", 0.3)]
    monkeypatch.setenv("HIVE_ENGRAM_GAIN", "100")
    assert all(s == 1.0 for n, s in engram.recall_scaled(TASK, "t80", cell="g41code") if n != "hive")


def fake_post(vectors, calls):
    """The runtime's /embedding: one row a token, as the runtime gives them with no pooling."""
    def post(url, body, timeout=0):
        calls.append((url, body["content"]))
        v = vectors[body["content"]]
        return [{"index": 0, "embedding": [v, v]}]
    return post


def test_embed_match_uses_cosine_and_keeps_the_vectors(store, monkeypatch):
    home, put = store
    # by words LIKE is the nearer; by meaning (the vectors) FAR is
    far = "count the fruit in the basket"
    put({"name": "elike", "task": LIKE}, {"name": "efar", "task": far})
    vectors = {TASK: [1.0, 0.0, 0.0], LIKE: [0.0, 1.0, 0.0], far: [0.95, 0.05, 0.0]}
    calls = []
    monkeypatch.setattr(ternary, "_post", fake_post(vectors, calls))
    monkeypatch.setenv("HIVE_ENGRAM_MATCH", "embed")
    assert engram.recall(TASK, "t80", cell="g41code") == ["efar"]  # LIKE's cosine is 0: below 0.8
    assert calls[0][0] == f"http://127.0.0.1:{ternary.port('t80')}/embedding"
    kept = {e["name"]: e.get("vec") for e in engram.index()}
    assert kept == {"elike": [0.0, 1.0, 0.0], "efar": [0.95, 0.05, 0.0]}
    calls.clear()
    got = engram.recall_scaled(TASK, "t80", cell="g41code")
    assert [x for _, x in calls] == [TASK]  # the engrams' vectors come from the index now
    assert got[0][0] == "efar" and 0.25 <= got[0][1] <= 1.0
    monkeypatch.setenv("HIVE_ENGRAM_EMBED_URL", "http://elsewhere:1/embedding")
    engram.recall(TASK, "t80", cell="g41code")
    assert calls[-1][0] == "http://elsewhere:1/embedding"


def test_embed_falls_back_to_words_on_any_error(store, monkeypatch):
    _, put = store
    put({"name": "elike", "task": LIKE})
    monkeypatch.setenv("HIVE_ENGRAM_MATCH", "embed")

    def refuse(url, body, timeout=0):
        raise OSError("This server does not support embeddings")
    monkeypatch.setattr(ternary, "_post", refuse)
    assert engram.recall(TASK, "t80", cell="g41code") == ["elike"]
    monkeypatch.setattr(ternary, "_post", lambda *a, **k: {"nothing": 1})
    assert engram.recall(TASK, "t80", cell="g41code") == ["elike"]
    assert "vec" not in engram.index()[0]


def test_embed_reads_both_shapes(monkeypatch):
    monkeypatch.setattr(ternary, "_post", lambda *a, **k: {"embedding": [1.0, 3.0]})  # older runtimes: one pooled vector
    assert engram.embed("x", "t80") == [1.0, 3.0]
    monkeypatch.setattr(ternary, "_post", lambda *a, **k: [{"index": 0, "embedding": [[1.0, 2.0], [3.0, 4.0]]}])
    assert engram.embed("x", "t80") == [2.0, 3.0]
    assert engram.cosine([1, 0], [0, 1]) == 0 and engram.cosine([1, 1], [2, 2]) == pytest.approx(1.0)


def test_fold_still_marks_and_keeps_other_fields(store):
    home, put = store
    put({"name": "ea", "task": LIKE, "vec": [1.0]}, {"name": "eb", "task": LIKE})
    assert engram.fold(["ea"], 7) == 1
    e = engram.index()[0]
    assert e["folded"] == 7 and e["vec"] == [1.0]


def test_gated_reads_names_and_pairs():
    assert ternary._gated(()) == ()
    assert ternary._gated(("e1", "hive")) == (("e1", 1.0), ("hive", 1.0))           # names alone: full strength, as before
    assert ternary._gated((("hive", 0.5), ("e1", 0.7))) == (("e1", 0.7), ("hive", 0.5))
    assert ternary._gated([["e1", 0.7]]) == (("e1", 0.7),)                           # as a task's record keeps them (JSON)


@pytest.fixture
def server(monkeypatch):
    sent = []
    monkeypatch.setattr(ternary, "_ON", {})
    ids = {"g41code": 0, "e1": 1, "e2": 2, "hive": 3}
    monkeypatch.setattr(ternary, "_loaded", lambda at, scales=False: {
        name: sent[-1][i] for name, i in ids.items()} if scales and sent else ids)
    monkeypatch.setattr(ternary, "edits_here", lambda base: {"g41code": "x"})
    monkeypatch.setattr(ternary, "_switch", lambda at, scales: sent.append({s["id"]: s["scale"] for s in scales}))
    return sent


def test_the_runtime_gets_each_engrams_strength(server):
    at = "http://127.0.0.1:1"
    assert ternary._on(at, "t80", ("g41code", ternary._gated((("e1", 0.6), ("hive", 0.5)))))
    assert server[-1] == {0: 1.0, 1: 0.6, 2: 0.0, 3: 0.5}
    assert not ternary._on(at, "t80", ("g41code", ternary._gated((("e1", 0.6), ("hive", 0.5)))))  # already on
    assert ternary._on(at, "t80", ("g41code", ternary._gated(("e1", "hive"))))  # names alone: all at 1.0, as before
    assert server[-1] == {0: 1.0, 1: 1.0, 2: 0.0, 3: 1.0}
    assert ternary._on(at, "t80", ("", ()))  # the base alone: all off
    assert server[-1] == {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}


def test_chat_passes_the_strengths_through(server, monkeypatch):
    monkeypatch.setattr(ternary, "up", lambda member: "http://127.0.0.1:1")
    monkeypatch.setattr(ternary, "_post", lambda url, body, timeout=0: {"choices": [{"message": {"content": "ok"}}]})
    assert ternary.chat("t80+g41code", [{"role": "user", "content": "q"}], also=(("e2", 0.25), "hive")) == "ok"
    assert server[-1] == {0: 1.0, 1: 0.0, 2: 0.25, 3: 1.0}
