"""Indexed recall must observe live catalogues, weight changes and source precedence."""
import json
import os

from team import engram, engram_index, ternary


def install(home, name, task):
    home.mkdir(exist_ok=True)
    row = {"name": name, "dna": "t80", "task": task}
    with (home / "index.jsonl").open("a") as output:
        output.write(json.dumps(row) + "\n")
    path = home / f"t80+{name}.gguf"
    path.touch()
    return path


def test_warm_lookup_skips_unrelated_files_and_observes_replaced_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    monkeypatch.delenv("HIVE_ENGRAM_MATCH", raising=False)
    for i in range(40):
        install(tmp_path, f"e{i}", f"ordinary topic {i}")
    matching = install(tmp_path, "target", "special count")
    original, visited = engram._weight, []
    def observe(home, shelf, base, name):
        visited.append(name)
        return original(home, shelf, base, name)
    monkeypatch.setattr(engram, "_weight", observe)
    cold = engram_index.catalog.cache_info().misses
    assert engram.recall("special count now", "t80") == ["target"]
    matching.unlink()
    assert engram.recall("special count now", "t80") == []
    matching.touch()
    assert engram.recall("special count now", "t80") == ["target"]
    assert engram_index.catalog.cache_info().misses == cold + 1
    assert set(visited) == {"target", "hive"}
    path = tmp_path / "index.jsonl"
    stats = path.stat()
    path.write_bytes(path.read_bytes().replace(b"special count", b"generic count"))
    os.utime(path, ns=(stats.st_atime_ns, stats.st_mtime_ns))
    assert engram.recall("special count now", "t80") == []
    assert engram.recall("generic count now", "t80") == ["target"]
    assert engram_index.catalog.cache_info().misses == cold + 2


def test_higher_priority_nonmatching_record_still_shadows_a_hit(tmp_path, monkeypatch):
    shipped, private = tmp_path / "shipped", tmp_path / "private"
    monkeypatch.setattr(ternary, "BUNDLED_ENGRAMS", shipped)
    monkeypatch.setattr(ternary, "LOCAL_ENGRAMS", private)
    monkeypatch.setattr(ternary, "ENGRAMS", private)
    monkeypatch.delenv("HIVE_ENGRAMS_HOME", raising=False)
    monkeypatch.delenv("HIVE_ENGRAM_MATCH", raising=False)
    high = install(shipped, "same", "arrange customer appointment")
    install(private, "same", "circle area")
    assert engram.recall("circle area calculation", "t80") == []
    high.unlink()
    assert engram.recall("circle area calculation", "t80") == ["same"]
    # A public catalogue read exposes copies. Editing one cannot inject a new entry into the warm index.
    engram.bank_entries("t80", private)["same"][1]["task"] = "not the circle"
    assert engram.recall("circle area calculation", "t80") == ["same"]
