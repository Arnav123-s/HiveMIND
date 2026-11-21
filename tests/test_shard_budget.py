import math
import pytest

from training import grow
from training.shard_budget import Plateau, cost_assignment, estimated_work


def row(i, length, reject=None):
    r = {"messages": [{"role":"system","content":"today"}, {"role":"user","content":str(i)}], "output":"x"*length}
    return r if reject is None else {**r,"rejected":reject}


def test_cost_slices_preserve_every_item_and_are_order_independent(monkeypatch):
    rows = [row(i,n) for i,n in enumerate([7300,3050,3050,2700,2100,1250,600,100,80,10,6,3])]
    monkeypatch.setenv("HIVE_SHARD_POLICY","cost")
    slices = [grow.slice_rows(rows,k,3) for k in range(3)]
    assert sorted(id(r) for part in slices for r in part)==sorted(map(id,rows))
    assert all(grow.slice_rows(reversed(rows),k,3)==list(reversed(part)) for k,part in enumerate(slices))
    value = sum(estimated_work(r) for r in rows)
    heaviest = max(sum(map(estimated_work,part)) for part in slices)
    assert heaviest < .36*value
    for r in rows:
        r["messages"][0]["content"]="another runner's date"
    assert [grow.slice_rows(rows,k,3) for k in range(3)]==slices


def test_duplicates_empty_and_preference_cost():
    base=row(0,50)
    duplicate={**base, "kind":"another metadata field"}
    rows=[base,duplicate,row(1,50,"long preference example"*30)]
    who=cost_assignment(rows,4)
    assert who[0]==who[1]
    assert estimated_work(rows[2]) > 2*estimated_work(base)
    assert cost_assignment([],4)==[] and cost_assignment(rows,1)==[0,0,0]
    with pytest.raises(ValueError):
        cost_assignment(rows,0)


def test_hash_default_unchanged_and_bad_policy_raises(monkeypatch):
    rows=[row(i,10) for i in range(30)]
    monkeypatch.delenv("HIVE_SHARD_POLICY",raising=False)
    assert grow.slice_rows(rows,0,3)==grow.slice_rows(rows,0,3,"hash")
    with pytest.raises(ValueError,match="Unknown"):
        grow.slice_rows(rows,0,3,"magic")


def updates(signal, n, loss, coverage=12, offset=0):
    flags=[]
    for i in range(n):
        for j in range(4):
            idx=(i*4+j)%12
            signal.observe(offset+idx,loss(idx))
        flags.append(signal.after_update(coverage))
    return flags


def test_plateau_requires_two_complete_independent_matched_windows():
    s=Plateau("stop",20)
    assert not any(updates(s,30,lambda idx:idx+1))
    assert not any(updates(s,29,lambda idx:idx+1))
    assert updates(s,1,lambda idx:idx+1)==[True]
    assert s.report["would_stop_at_update"]==60
    observer=Plateau("observe",20)
    assert not any(updates(observer,60,lambda idx:idx+1))
    assert observer.report["would_stop_at_update"]==60


def test_coverage_nonmatching_rows_and_changing_loss_cannot_stop():
    for mode in ("coverage","different_rows","improving","worsening","nonfinite"):
        s=Plateau("stop",30 if mode=="coverage" else 20)
        for _ in range(2):
            assert not any(updates(s,15,lambda _:1.0))
            value={"improving":0.9,"worsening":1.1,"nonfinite":math.nan}.get(mode,1.0)
            assert not any(updates(s,15,lambda _:value,offset=50 if mode=="different_rows" else 0))
        assert s.report["would_stop_at_update"] is None

def test_actual_tiny_trainer_enters_cost_and_observation_paths(tmp_path, monkeypatch):
    from test_held_out import _rows, _train

    monkeypatch.setenv("HIVE_SHARD_POLICY", "cost")
    monkeypatch.setenv("HIVE_TRAIN_PLATEAU", "observe")
    meta, _ = _train(tmp_path, monkeypatch, _rows(), "0/2")
    assert meta["shard_policy"] == "cost"
    assert 0 < meta["plateau"]["rows_covered"] <= meta["used"]
    assert meta["plateau"]["full_updates"] == meta["passes"] // 2
    assert meta["plateau"]["would_stop_at_update"] is None


@pytest.mark.parametrize("receipts,expected", [
    ([{"shard_policy":"cost"},{"shard_policy":"cost"}], "cost"),
    ([{},None], "hash"),
    ([None,None], "hash"),
    ([{"shard_policy":"cost"},None], None),
    ([{"shard_policy":"hash"},{"shard_policy":"cost"}], None),
])
def test_join_rejects_mixed_policy_before_writing(tmp_path, monkeypatch, receipts, expected):
    import json
    import numpy as np
    from training import merge

    files=[]
    for i,receipt in enumerate(receipts):
        path=tmp_path/f"slice{i}.safetensors"
        merge.save({"layer.q_proj":(np.ones((1,2)),np.ones((2,1)))},path)
        if receipt is not None:
            path.with_suffix(".json").write_text(json.dumps(receipt))
        files.append(str(path))
    model=tmp_path/"child.gguf"
    def gguf(*args):
        model.write_bytes(b"test")
        return model
    monkeypatch.setattr(merge,"gguf",gguf)
    work=tmp_path/"work"
    cmd=["join",str(work),*files,"--rank","1","--base","t17","--name","g9code"]
    if expected is None:
        with pytest.raises(ValueError,match="incompatible shard policies"):
            merge.main(cmd)
        assert not work.exists()
    else:
        assert merge.main(cmd)==0
        assert json.loads(model.with_suffix(".json").read_text())["shard_policy"]==expected


def test_opposing_large_row_movements_do_not_cancel():
    signal = Plateau("stop", 12)
    for _ in range(2):
        assert not any(updates(signal, 15, lambda _: 1.0))
        assert not any(updates(signal, 15, lambda i: 0.25 if i % 2 else 1.75))
    assert signal.report["would_stop_at_update"] is None
    assert signal.report["last"]["mean_absolute_relative_change"] == pytest.approx(.75)


def test_join_labels_per_shard_measurements():
    from training.merge import slice_observations

    first = {"shard": "0/2", "plateau": {"would_stop_at_update": 60}, "loss_chunk_tokens": 16,
             "memory": {"peak_gb": 8, "row_modes": {"ordinary": 60, "checkpoint": 0}, "training_max_len": 500}}
    second = {"shard": "1/2", "plateau": {"would_stop_at_update": None}, "loss_chunk_tokens": 32,
              "memory": {"peak_gb": 9, "row_modes": {"ordinary": 30, "checkpoint": 50}, "evaluation_max_len": 450}}
    joined = slice_observations([first, second])
    assert "plateau" not in joined and "loss_chunk_tokens" not in joined
    assert joined["memory"] == {"peak_gb": 8}
    observations = joined["slice_observations"]
    assert [row["shard"] for row in observations] == ["0/2", "1/2"]
    assert [row["plateau"]["would_stop_at_update"] for row in observations] == [60, None]
    assert [row["memory"]["row_modes"]["checkpoint"] for row in observations] == [0, 50]
    assert observations[1]["memory"]["evaluation_max_len"] == 450
    assert first["memory"]["training_max_len"] == 500
