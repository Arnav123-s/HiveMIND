import json
import os
from concurrent.futures import ThreadPoolExecutor

from team import engram, ternary
from training.experiments.engram_index_scale import old_recall


def test_recall_preserves_ranking_file_presence_and_legacy_slices(tmp_path, monkeypatch):
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    rows = [{"task": "track sore elbow", "name": name, "dna": "a"} for name in ["z", "b", "z", "missing"]]
    rows += [dict(task="filing another report", name="c", dna="a"), dict(task="track sore elbow", name="q", dna="b"),
             dict(task="", name="empty", dna="a")]
    path = tmp_path / "index.jsonl"
    path.write_text("\n".join(map(json.dumps, rows)))
    for base, name in (("a", "z"), ("a", "b"), ("a", "c"), ("b", "q"), ("a", "empty")):
        (tmp_path / f"{base}+{name}.gguf").touch()
    for query in ("my sore elbow", "", "track sore elbow", "filing", "no shared term"):
        for base in ("a", "b", "other"):
            for most in (0, 1, 2, -1, None):
                for least in (0, -0.5, 0.34, 1):
                    assert engram.recall(query, base, most, least) == old_recall(query, base, most, least)
    assert engram.recall("my sore elbow", "a") == ["z", "z"]
    (tmp_path / "a+z.gguf").unlink()
    assert engram.recall("my sore elbow", "a") == ["b"]
    (tmp_path / "a+missing.gguf").touch()
    assert engram.recall("my sore elbow", "a") == ["missing", "b"]


def test_recall_refreshes_after_atomic_replacement_append_and_partial_line(tmp_path, monkeypatch):
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    path = tmp_path / "index.jsonl"
    def line(name):
        return json.dumps(dict(task="save the new report", name=name, dna="base")) + "\n"
    for name in ("a", "b"):
        (tmp_path / f"base+{name}.gguf").touch()
    query = lambda: engram.recall("new report", "base")
    assert query() == []
    path.write_text(line("a"))
    assert query() == ["a"]
    other = tmp_path / "replacement"
    other.write_text(line("b"))
    os.utime(other, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns))
    other.replace(path)
    assert query() == ["b"]
    with path.open("a") as stream:
        stream.write("{")
    assert query() == []
    with path.open("a") as stream:
        stream.write(line("a")[1:])
    assert query() == ["b", "a"]
    def reader(_):
        return all(query() in (["a"], ["b"], ["b", "a"]) for _ in range(60))
    with ThreadPoolExecutor(max_workers=4) as pool:
        readers = [pool.submit(reader, i) for i in range(3)]
        for name in ("a", "b") * 8:
            other.write_text(line(name))
            other.replace(path)
        assert all(f.result() for f in readers)
    assert query() == ["b"]
    path.unlink()
    assert query() == []
