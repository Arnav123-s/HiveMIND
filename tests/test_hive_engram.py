"""The hive engram (training/hive_engram.py): replay, the cap on kept rows, its index, the fold into the trunk, and
its command line. grow.train is stood in for, so no model is needed."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from training import grow, hive_engram, merge


def row(i):
    return {"messages": [{"role": "system", "content": "s"}, {"role": "user", "content": f"task {i}"}], "output": f"answer {i}"}


def edit(rank, mods=("base_model.model.model.layers.20.self_attn.q_proj", "base_model.model.model.layers.21.mlp.up_proj"), d_in=12, d_out=10, seed=0):
    g = np.random.default_rng(seed)
    return {m: (g.standard_normal((rank, d_in)).astype(np.float32), g.standard_normal((d_out, rank)).astype(np.float32)) for m in mods}


def product(e):
    return {m: b @ a for m, (a, b) in e.items()}


def test_replay_sample_takes_newest_and_some_older():
    old = [row(i) for i in range(100)]
    got = hive_engram.replay_sample(old, 10, seed=1)
    assert len(got) == 10
    assert got[-5:] == old[-5:]                      # half the newest
    assert all(r in old[:95] for r in got[:5])       # half from the rest
    assert len({json.dumps(r) for r in got}) == 10
    assert hive_engram.replay_sample(old, 0) == []
    assert len(hive_engram.replay_sample(old[:3], 10)) == 3


def test_replay_count():
    assert hive_engram.replay_count(10, 100, 0.5) == 10
    assert hive_engram.replay_count(10, 4, 0.5) == 4
    assert hive_engram.replay_count(10, 100, 0) == 0
    assert hive_engram.replay_count(10, 0, 0.5) == 0
    assert hive_engram.replay_count(3, 100, 0.25) == 1
    assert hive_engram.replay_count(5, 7, 1.0) == 7


def test_cap_keeps_newest_and_a_sample_of_older():
    rows = [row(i) for i in range(50)]
    kept = hive_engram.cap_rows(rows, cap=10, seed=2)
    assert len(kept) == 10
    assert kept[-5:] == rows[-5:]
    older = [rows.index(r) for r in kept[:5]]
    assert older == sorted(older) and max(older) < 45
    assert hive_engram.cap_rows(rows[:4], cap=10) == rows[:4]


@pytest.fixture
def fake_train(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(grow, "GROW", tmp_path / "grow")

    def train(rows_file, name, base="t17", rank=16, out_dir=None, parent="", ternary_edit=False, layers="all", checkpoint=True, **k):
        rows = [json.loads(x) for x in Path(rows_file).read_text().splitlines() if x.strip()]
        calls.append({"rows": rows, "name": name, "parent": parent, "rank": rank, "ternary_edit": ternary_edit, "layers": layers,
                      "checkpoint": checkpoint, "out_dir": Path(out_dir)})
        work = grow.GROW / f"{base}+{name}"
        work.mkdir(parents=True, exist_ok=True)
        merge.save(edit(rank, seed=len(calls)), work / "adapter_model.safetensors")
        (Path(out_dir) / f"{base}+{name}.gguf").write_bytes(b"gguf")
        return {"loss_first": 2.0, "loss_last": 0.5, "megabytes": 0.1}
    monkeypatch.setattr(grow, "train", train)
    return calls


def write_rows(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def test_update_continues_replays_and_logs(tmp_path, fake_train):
    home = tmp_path / "engrams"
    first = hive_engram.update(write_rows(tmp_path / "a.jsonl", [row(i) for i in range(6)]), base="t17", home=home, seed=0, log=lambda *a: None)
    assert (home / "t17+hive.gguf").exists() and (home / "t17+hive.safetensors").exists()
    c = fake_train[0]
    assert c["name"] == "hive" and c["parent"] == "" and c["ternary_edit"] and c["layers"] == "last8" and not c["checkpoint"]
    assert c["out_dir"] == home and len(c["rows"]) == 6
    assert first["rows_new"] == 6 and first["rows_replayed"] == 0 and first["loss_last"] == 0.5

    # again, with 4 new rows and 2 already learned: only the new ones are new, and old ones come back
    second = hive_engram.update(write_rows(tmp_path / "b.jsonl", [row(i) for i in range(4, 10)]), base="t17", home=home, seed=0, log=lambda *a: None)
    c = fake_train[1]
    assert c["parent"] == str(home / "t17+hive.safetensors")
    assert second["rows_new"] == 4 and second["rows_replayed"] == 4 and len(c["rows"]) == 8
    assert len(hive_engram.read_rows(home / "hive_rows.jsonl")) == 10
    index = hive_engram.read_rows(home / "hive_index.jsonl")
    assert [x["what"] for x in index] == ["update", "update"]
    assert {"when", "rows_new", "rows_replayed", "seconds", "loss_first", "loss_last"} <= set(index[-1])
    assert not list(home.glob(".*rows.jsonl"))       # the rows handed to training are cleaned up

    # nothing new: nothing trained
    assert hive_engram.update(write_rows(tmp_path / "c.jsonl", [row(1)]), home=home, log=lambda *a: None) is None
    assert len(fake_train) == 2


def test_runtime_file_name_follows_the_engrams_folder(tmp_path):
    from team import ternary
    assert hive_engram.files("t80")["gguf"] == ternary.ENGRAMS / "t80+hive.gguf"
    assert hive_engram.files("t80", tmp_path)["gguf"] == tmp_path / "t80+hive.gguf"


@pytest.mark.parametrize("mode,keep", [("add", 1.0), ("average", 0.75)])
def test_fold_adds_or_averages_at_the_trunks_rank(tmp_path, mode, keep):
    home = tmp_path / "engrams"
    home.mkdir()
    trunk, hive = edit(4, seed=1), edit(2, seed=2)
    for a, _ in trunk.values():
        a[2:] = 0                                         # a trunk of rank 4 holding 2 directions: trunk + hive fits in 4
    hive["base_model.model.model.layers.21.self_attn.v_proj"] = edit(2, mods=("x",), seed=3)["x"]  # a module only the hive trains
    merge.save(trunk, tmp_path / "trunk.safetensors")
    merge.save(hive, home / "t17+hive.safetensors")
    (home / "t17+hive.gguf").write_bytes(b"gguf")
    write_rows(home / "hive_rows.jsonl", [row(1)])
    kw = {} if mode == "add" else {"mode": mode}  # add is the default
    line = hive_engram.fold(tmp_path / "out.safetensors", tmp_path / "trunk.safetensors", base="t17", weight=0.25, gen="g40", home=home,
                            log=lambda *a: None, **kw)
    out = merge.load(tmp_path / "out.safetensors")
    assert line["rank"] == 4 and line["folded"] and line["mode"] == mode
    assert all(a.shape[0] == 4 and b.shape[1] == 4 for a, b in out.values())
    want = {m: keep * product(trunk).get(m, 0) + 0.25 * product(hive).get(m, 0) for m in set(trunk) | set(hive)}  # add: the trunk is not shrunk
    got = product(out)
    assert set(got) == set(want)
    for m, w in want.items():
        assert np.allclose(got[m], w, atol=1e-4)    # the sum has rank 4 at most: the cut keeps all of it
    # the hive engram starts again; its rows stay for replay
    assert not (home / "t17+hive.safetensors").exists() and not (home / "t17+hive.gguf").exists()
    assert (home / "folded" / "t17+hive.g40.safetensors").exists() and (home / "folded" / "t17+hive.g40.gguf").exists()
    assert (home / "hive_rows.jsonl").exists()
    assert hive_engram.read_rows(home / "hive_index.jsonl")[-1]["what"] == "fold"


@pytest.mark.parametrize("mode,keep", [("add", 1.0), ("average", 0.5)])
def test_fold_cuts_to_the_trunks_rank(tmp_path, mode, keep):
    home = tmp_path / "engrams"
    home.mkdir()
    trunk, hive = edit(3, seed=4), edit(3, seed=5)
    merge.save(trunk, tmp_path / "trunk.safetensors")
    merge.save(hive, home / "t17+hive.safetensors")
    hive_engram.fold(tmp_path / "out", tmp_path / "trunk.safetensors", weight=0.5, gen="g1", home=home, mode=mode, log=lambda *a: None)
    out = merge.load(tmp_path / "out" / "adapter_model.safetensors")
    assert json.loads((tmp_path / "out" / "adapter_config.json").read_text())["r"] == 3
    for m, (a, b) in out.items():
        full = keep * product(trunk)[m] + 0.5 * product(hive)[m]
        u, s, vt = np.linalg.svd(full)
        best = (u[:, :3] * s[:3]) @ vt[:3]
        assert a.shape[0] == 3 and np.allclose(b @ a, best, atol=1e-4)


def test_fold_without_a_hive_engram_keeps_the_trunk(tmp_path):
    trunk = edit(4, seed=6)
    merge.save(trunk, tmp_path / "trunk.safetensors")
    line = hive_engram.fold(tmp_path / "out.safetensors", tmp_path / "trunk.safetensors", home=tmp_path / "engrams", log=lambda *a: None)
    assert not line["folded"]
    out = merge.load(tmp_path / "out.safetensors")
    for m in trunk:
        assert np.allclose(product(out)[m], product(trunk)[m])


def test_command_line():
    a = hive_engram.parse(["update", "rows.jsonl", "--base", "t80", "--replay", "0.3", "--rank", "4", "--steps", "10"])
    assert (a.cmd, a.rows, a.base, a.replay, a.rank, a.steps, a.home) == ("update", "rows.jsonl", "t80", 0.3, 4, 10, None)
    a = hive_engram.parse(["fold", "out", "trunk.safetensors", "--weight", "0.1", "--gen", "g41", "--home", "/x"])
    assert (a.cmd, a.trunk_out, a.trunk_edit, a.base, a.weight, a.gen, a.home, a.rank) == ("fold", "out", "trunk.safetensors", "t17", 0.1, "g41", "/x", None)
    assert a.mode == "add"
    assert hive_engram.parse(["fold", "out", "trunk.safetensors", "--mode", "average"]).mode == "average"
    with pytest.raises(SystemExit):
        hive_engram.parse(["fold", "out", "trunk.safetensors", "--mode", "mean"])
    with pytest.raises(SystemExit):
        hive_engram.parse([])


def test_main_runs_fold(tmp_path, capsys):
    merge.save(edit(2, seed=7), tmp_path / "trunk.safetensors")
    assert hive_engram.main(["fold", str(tmp_path / "out.safetensors"), str(tmp_path / "trunk.safetensors"), "--home", str(tmp_path / "e")]) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["what"] == "fold"


def test_saved_key_of_a_ternary_edit():
    """An edit trained as ternary is parametrized; its matrices must still be found in the file it was saved to, or
    the hive engram cannot go on training from itself (its second update failed: none of its matrices fit)."""
    n = "base_model.model.model.layers.20.self_attn.q_proj.lora_A.default.parametrizations.weight.original"
    assert grow.saved_key(n) == "base_model.model.model.layers.20.self_attn.q_proj.lora_A.weight"
    assert grow.saved_key("base_model.model.model.layers.20.mlp.up_proj.lora_B.default.weight") == "base_model.model.model.layers.20.mlp.up_proj.lora_B.weight"


def test_fold_refuses_an_unknown_mode(tmp_path):
    merge.save(edit(2, seed=8), tmp_path / "trunk.safetensors")
    with pytest.raises(ValueError, match="fold mode"):
        hive_engram.fold(tmp_path / "out.safetensors", tmp_path / "trunk.safetensors", home=tmp_path / "e", mode="mean", log=lambda *a: None)


def test_add_keeps_the_trunk_whole_where_the_hive_has_nothing(tmp_path):
    """The dilution the add mode ends: a module only the trunk trains is kept at full strength by add, shrunk by
    average."""
    home = tmp_path / "engrams"
    home.mkdir()
    trunk = edit(4, mods=("t",), seed=9)
    hive = edit(2, mods=("h",), seed=10)
    merge.save(trunk, tmp_path / "trunk.safetensors")
    for mode, keep in (("add", 1.0), ("average", 0.8)):
        merge.save(hive, home / "t17+hive.safetensors")
        hive_engram.fold(tmp_path / f"{mode}.safetensors", tmp_path / "trunk.safetensors", weight=0.2, gen=mode, home=home, mode=mode, log=lambda *a: None)
        got = product(merge.load(tmp_path / f"{mode}.safetensors"))
        assert np.allclose(got["t"], keep * product(trunk)["t"], atol=1e-4)
        assert np.allclose(got["h"], 0.2 * product(hive)["h"], atol=1e-4)


def test_merge_without_normalizing_is_the_weighted_sum():
    a, b = edit(2, mods=("m",), seed=11), edit(2, mods=("m",), seed=12)
    out, _ = merge.merge([a, b], [1.0, 0.5], rank=4, normalize=False)
    assert np.allclose(product(out)["m"], product(a)["m"] + 0.5 * product(b)["m"], atol=1e-4)
    out, _ = merge.merge([a, b], [1.0, 0.5], rank=4)  # as before: the average
    assert np.allclose(product(out)["m"], (product(a)["m"] + 0.5 * product(b)["m"]) / 1.5, atol=1e-4)
