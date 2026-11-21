"""Split and rejoin the original fixed seat using the normal task generators and callbacks."""
import json
from pathlib import Path

import pytest

from training import exam
from training.experiments.astra_cpu.gate_timing import halves, replay


def test_halves_match_original_callbacks_order_fields_and_grades(tmp_path, monkeypatch):
    source = exam.held_exam(3)
    monkeypatch.setattr(exam, "held_exam", lambda per: source)
    homes, calls = [], []
    def memory(empty):
        assert empty is True
        dest = tmp_path / f"memory{len(homes)}"
        dest.mkdir()
        homes.append(dest)
        return dest
    def sit(tag, tid, task, check, home, timeout, kind):
        assert home == homes[-1] and timeout == 900
        calls.append((tid, task, check, kind))
        return dict(id=tid, ok=tid.endswith("_0"), members=[], seconds=1, why="", note="", answer="")
    monkeypatch.setattr(exam, "_memory", memory)
    monkeypatch.setattr(exam, "sit_one", sit)
    monkeypatch.setenv("HIVE_MEMBERS", "t80+one,t80+two")
    partdir, joined = tmp_path / "parts", tmp_path / "joined"
    opts = dict(out=partdir, seconds=900, log=lambda *a,**kw:None)
    exam.sit_held(3,8,3,**opts)
    original_calls = calls.copy()
    calls.clear()
    for half in (1,2):
        exam.sit_held(3,8,3,half=half,group="run-after",**opts)
    assert calls == original_calls and len(set(homes)) == 3
    halves.join(partdir, joined, 3,8,3,"run-after")
    assert json.loads((joined/"held_3.json").read_text()) == json.loads((partdir/"held_3.json").read_text())
    halves.join(partdir, joined, 3,8,3,"run-after")
    other = tmp_path / "other"
    file = partdir/"part-2-seat-3.json"
    raw = file.read_text()
    for alter in ("partial","duplicated","workers","run","grade"):
        d=json.loads(raw)
        if alter=="partial":
            d["tasks"].pop()
        elif alter=="duplicated":
            d["tasks"][1]=d["tasks"][0]
        elif alter=="workers":
            d["summary"]["members"]="some other workers"
        elif alter=="run":
            d["summary"]["group"]="other-run"
        else:
            d["summary"]["passed"]+=1
        file.write_text(json.dumps(d))
        with pytest.raises(ValueError):
            halves.join(partdir,other,3,8,3,"run-after")
        assert not (other/"held_3.json").exists()
    file.unlink()
    with pytest.raises(FileNotFoundError):
        halves.join(partdir,other,3,8,3,"run-after")
    monkeypatch.setenv("HIVE_LIBRARY","1")
    with pytest.raises(ValueError,match="carry work"):
        exam.sit_held(3,8,3,half=1,group="run-after",**opts)


def test_trace_replay_covers_every_record_and_never_overbooks():
    folder=Path(replay.__file__).parent
    traces=json.loads((folder/"traces.json").read_text())
    observed=replay.report(traces)
    assert observed==json.loads((folder/"result.json").read_text())
    assert "exclusion" in observed["g54"]
    assert observed["g56"]["completed_fixed"]==60
    assert all(s["peak"]<=20 for r in observed.values() for s in r.values() if isinstance(s,dict))
