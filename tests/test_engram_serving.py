"""Check that the ordinary paths actually select, apply and isolate a neural memory."""

import json
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
import socket
import threading
import time

import pytest

from team import engram, engram_index, solo, talk, ternary


def put(home, name, task, **meta):
    home.mkdir(exist_ok=True)
    (home / f"t80+{name}.gguf").write_bytes(b"fixture")
    row = dict(dna="t80", name=name, task=task, **meta)
    engram.update_index(lambda rows: rows + [row], home=home)
    return row


def test_explicit_classifier_has_a_narrow_form_and_internal_advice_requires_its_topic(tmp_path, monkeypatch):
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    monkeypatch.delenv("HIVE_ENGRAMS", raising=False)
    row = put(tmp_path, "e_memory", "Choose a memory tier", domain="computer_engineering", verified=True,
              skill_id="tiers", form="label", labels=["cache", "dram"], cues=["cache locality"])
    domain = row["domain"]
    task = "Cache locality changes the performance. Choose cache or DRAM."
    assert engram.for_request(task, "t80", domain=domain) == ("e_memory",)
    assert engram.for_request(task, "t80", domain=domain, labels=False) == ()
    plain = "Explain what cache locality means."
    assert engram.for_request(plain, "t80", domain=domain) == ()
    assert engram.label_for(plain, "t80", domain) == row
    assert engram.label_for("Should I replace the power supply?", "t80", domain) is None
    assert engram.label_for(plain, "t80", "math") is None
    assert engram.label_for(plain, "t17", domain) is None
    monkeypatch.setenv("HIVE_ENGRAMS", "off")
    assert engram.for_request(task, "t80", domain=domain) == ()
    assert engram.label_for(plain, "t80", domain) is None


def test_private_overlay_shares_reads_and_never_replaces_shipped_records(tmp_path, monkeypatch):
    shipped, local = tmp_path / "shipped", tmp_path / "private"
    monkeypatch.delenv("HIVE_ENGRAMS_HOME", raising=False)
    monkeypatch.setattr(ternary, "BUNDLED_ENGRAMS", shipped)
    monkeypatch.setattr(ternary, "LOCAL_ENGRAMS", local)
    monkeypatch.setattr(ternary, "ENGRAMS", local)
    public = put(shipped, "published", "Model speed")
    original = (shipped / "index.jsonl").read_bytes()
    put(local, "personal", "Private local task")
    put(local, "published", "Unrelated task with same name")
    assert ternary.edits_here("t80")["published"].parent == shipped
    assert list(engram._active("t80")) == [public, {"name":"personal", "task":"Private local task", "dna":"t80"}]
    assert engram.fold(["published", "personal"], 2) == 2  # only local records mutated
    assert list(engram._active("t80")) == [public]
    assert (shipped / "index.jsonl").read_bytes() == original
    monkeypatch.setenv("HIVE_ENGRAMS_HOME", str(local))
    assert list(engram._active("t80")) == []
    assert "published" not in ternary.edits_here("t80")


def test_two_learned_conventions_need_the_named_topic_or_unique_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    monkeypatch.delenv("HIVE_ENGRAMS", raising=False)
    meta = dict(domain="math", form="label", verified=True, labels=["low", "high"], cues=["parcel", "stamp"],
                validation_version=engram_index.GROWTH_VALIDATION)
    old = put(tmp_path, "z_old", "Copper Chart", growth_group="first", **meta)
    new = put(tmp_path, "a_new", "Amber Chart", growth_group="second", **meta)
    query = "Choose low or high for this parcel stamp."
    for topic, expected in [("COPPER  chart", old), ("Amber Chart", new)]:
        message = f"Use {topic}. {query}"
        assert engram.for_request(message, "t80", domain="math") == (expected["name"],)
        assert engram.label_for(message, "t80", "math") == expected
    for prefix in ["", "Copper Chartreuse. ", "Consult both Copper Chart and Amber Chart. "]:
        assert engram.for_request(prefix + query, "t80", domain="math") == ()
        assert engram.label_for(prefix + query, "t80", "math") is None
    # Explicit conventions still work when a paraphrase shares none of the recorded keywords.
    assert engram.for_request("Under Copper Chart choose low or high for a crate weighing 80 grams.", "t80", domain=None) == ("z_old",)
    assert engram.named_label_for("Which audit code applies under Copper Chart for an 80 g parcel?", "t80") == old
    assert engram.named_label_for("What label applies with Amber Chart for a fragile parcel?", "t80") == new
    assert engram.named_label_for("Describe the origin of Copper Chart.", "t80") is None
    assert engram.named_label_for("Do not classify; describe Copper Chart.", "t80") is None
    assert engram.named_label_for("Which label applies under both Copper Chart and Amber Chart?", "t80") is None
    revised = put(tmp_path, "revised", "Amber Chart revised", growth_group="third", **meta)
    assert engram.named_label_for("Under Amber Chart revised, classify this parcel.", "t80") == revised
    assert engram.named_label_for("Return category for Amber Chart and Amber Chart revised.", "t80") is None


def test_concurrent_updates_keep_the_other_publishers_rows(tmp_path):
    def publish(i):
        engram.update_index(lambda rows: [*rows, {"i": i}], home=tmp_path)
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(publish, range(12)))
    assert sorted(row["i"] for row in engram._rows(tmp_path / "index.jsonl")) == list(range(12))


def test_unregraded_local_label_is_withheld_without_losing_history(tmp_path, monkeypatch):
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    meta = dict(domain="math", form="label", verified=True, labels=["low", "high"], cues=["stamp"])
    put(tmp_path, "old", "North stamps", growth_group="local", **meta)
    put(tmp_path, "new", "South stamps", growth_group="local2", validation_version=engram_index.GROWTH_VALIDATION, **meta)
    put(tmp_path, "shipped", "Registered stamp", **meta)
    put(tmp_path, "episode", "Previous checked stamp question")
    assert set(ternary.edits_here("t80")) >= {"new", "shipped", "episode"}
    assert "old" not in ternary.edits_here("t80")
    assert set(r["name"] for r in engram.index()) == {"old", "new", "shipped", "episode"}
    assert engram.named_label_for("Which code for North stamps?", "t80") is None


def test_unavailable_catalogues_and_external_bases_abstain_on_each_request(tmp_path, monkeypatch):
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    monkeypatch.delenv("HIVE_ENGRAMS", raising=False)
    message = "Which audit code applies under Copper Chart? Its seal is torn."
    put(tmp_path, "e1", "Copper Chart", domain="math", form="label", labels=["L", "H"],
        verified=True, cues=["audit"], growth_group="example", validation_version=engram_index.GROWTH_VALIDATION)
    assert engram.named_label_for(message, "t80")["name"] == "e1"
    assert engram.named_label_for(message, "dna") is None
    assert engram.label_for(message, "dna", "math") is None
    assert engram.for_request(message, "non-native+writer", domain="math") == ()
    index = tmp_path / "index.jsonl"
    for content in (b"invalid json\n", b"\xff", None):
        if content is None:
            index.unlink()
        else:
            index.write_bytes(content)
        for _ in range(2):
            assert engram.named_label_for(message, "t80") is None
            assert engram.for_request(message, "t80", domain="math") == ()


def test_native_has_to_hold_each_requested_edit(monkeypatch):
    monkeypatch.setattr(ternary, "_loaded", lambda at: {"e_other": 2})
    with pytest.raises(ternary.Silent, match="missing"):
        ternary._on("at", "t80", ("", (("e_missing", 1.0),)))


def test_direct_chat_applies_exact_episode_by_default_and_ablation_keeps_the_prompt(tmp_path, monkeypatch):
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    monkeypatch.delenv("HIVE_ENGRAMS", raising=False)
    monkeypatch.setenv("HIVE_SIGNALS", "0")
    monkeypatch.setenv("HIVE_BANK", "off")
    message = "Describe the calculus of orbital velocity"
    put(tmp_path, "e_orbit", message)
    calls = []
    monkeypatch.setattr(talk, "route", lambda base, message, history: ("talk", [{"role": "user", "content": message}]))
    def chat(member, messages, **options):
        calls.append((member, messages, options))
        return "A short explanation."
    monkeypatch.setattr(ternary, "chat", chat)
    result = talk.reply(message, base="t80")
    assert calls[-1][2]["also"] == ("e_orbit",)
    assert result["engrams"] == [{"stage": "answer", "member": "t80", "edits": ["e_orbit"]}]
    monkeypatch.setenv("HIVE_ENGRAMS", "0")
    assert "engrams" not in talk.reply(message, base="t80")
    assert "also" not in calls[-1][2] and calls[0][1] == calls[-1][1]


def test_member_work_records_real_selection_and_skips_folded_or_missing_rows(tmp_path, monkeypatch):
    bank = tmp_path / "engrams"
    monkeypatch.setattr(ternary, "ENGRAMS", bank)
    monkeypatch.setenv("HIVE_SIGNALS", "0")
    monkeypatch.delenv("HIVE_ENGRAMS", raising=False)
    task = "Compute orbital velocities using Keplerian periods"
    put(bank, "e_orbit", task)
    put(bank, "e_old", task, folded=2)
    put(bank, "e_gone", task)
    (bank / "t80+e_gone.gguf").unlink()
    monkeypatch.setattr(ternary, "seating", lambda *args, **kwargs: ["t80+code", "t80+data"])
    monkeypatch.setattr(solo, "keep", lambda *args: None)
    seen = []
    def member(task, n, board, guard, work, temperature, who, also):
        seen.append((who, also))
        return {"answer": "123", "program": "print(123)", "who": who, "turns": 1, "also": list(also)}
    monkeypatch.setattr(solo, "member", member)
    run = tmp_path / "run"
    result = solo.run(task, run, members=2)
    assert seen == [("t80+code", ("e_orbit",)), ("t80+data", ("e_orbit",))]
    assert result["engrams"] == json.loads((run / "members.json").read_text())["engrams"]
    assert [seat["edits"] for seat in result["engrams"]] == [["e_orbit"], ["e_orbit"]]


def test_replaced_adapter_forces_reload_even_under_same_file_name(tmp_path, monkeypatch):
    bank = tmp_path / "edits"
    put(bank, "example", "alpha")
    monkeypatch.setattr(ternary, "ENGRAMS", bank)
    monkeypatch.setattr(ternary, "ADAPTERS", tmp_path / "members")
    monkeypatch.setattr(ternary, "HOME", tmp_path)
    edit = bank / "t80+example.gguf"
    manifest = tmp_path / "t80.loaded-edits.json"
    identity = ternary._edit_files({"example": edit})
    manifest.write_text(json.dumps(identity))
    monkeypatch.setattr(ternary, "_loaded", lambda at, paths=False: {"example": str(edit.resolve())})
    assert not ternary._same_edits("at", "t80")  # pre-fix servers could reuse a graph built with different weights
    monkeypatch.setattr(ternary, "_serves", lambda pid, n, graph_safe: pid == 42 and graph_safe)
    manifest.write_text(json.dumps({"pid": 42, "graph_reuse": False, "edits": identity}))
    assert ternary._same_edits("at", "t80")
    replacement = bank / "new"
    replacement.write_bytes(b"fixture")
    os.replace(replacement, edit)
    assert not ternary._same_edits("at", "t80")


def _chat(changes):
    return ternary.chat("t80", [{"role": "user", "content": "same"}], also=changes)


def test_overlapping_and_cross_process_requests_cannot_inherit_another_edit(tmp_path, monkeypatch):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    at = f"http://127.0.0.1:{port}"
    active = tmp_path / "server-scales"
    monkeypatch.setattr(ternary, "port", lambda member: port)
    monkeypatch.setattr(ternary, "up", lambda member: at)
    monkeypatch.setattr(ternary, "_ON", {})
    monkeypatch.setattr(ternary, "_loaded", lambda at, scales=False: {"e_test": float(active.read_text()) if scales else 0})
    monkeypatch.setattr(ternary, "_switch", lambda at, values: active.write_text(str(values[0]["scale"])))
    first_started = threading.Event()
    def complete(url, body, timeout):
        first_started.set()
        time.sleep(0.06)
        return {"choices": [{"message": {"content": active.read_text()}}]}
    monkeypatch.setattr(ternary, "_post", complete)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(_chat, ("e_test",))
        assert first_started.wait(5)
        second = pool.submit(_chat, ())
        assert first.result() == "1.0" and second.result() == "0.0"
    assert _chat(("e_test",)) == "1.0"
    with multiprocessing.get_context("fork").Pool(1) as child:
        assert child.apply(_chat, ((),)) == "0.0"
    # The parent used the very same selection last time; its local cache is stale.
    assert _chat(("e_test",)) == "1.0"
    # A separate HTTP client changed scales between calls without touching the Hive endpoint lock.
    active.write_text("0.0")
    assert _chat(("e_test",)) == "1.0"
