"""The brain the hive grew from nothing, at work: it answers a cell job where it measured at least as well as the
cell that had the job.

One model of about 2.6 million weights (training/scratch.py: a stem cell that read the hive's own harvest, then one
shared trunk and a small head per job, trained on all the jobs together). It needs no outside weights and answers in
a few milliseconds on the CPU. Which jobs it holds is decided by measurement only, when it is trained
(cells/scratch/holds.json): the same test of unseen words as today's cells, and it takes a job only where its score
is at least the score of whoever does that job now. AGENT_TEAM_TINY=0 turns it off.
"""
import json
import os
import sys
import threading

from .. import config

HOME = config.ROOT / "cells" / "scratch"
_lock = threading.Lock()
_state = {}


def holds():
    """{job: {"test": its score, "was": the score it had to reach}} for the jobs the brain holds."""
    if os.environ.get("AGENT_TEAM_TINY", "1") == "0":
        return {}
    f = HOME / "holds.json"
    try:
        m = f.stat().st_mtime
        if _state.get("holds_m") != m:
            _state.update(holds_m=m, holds=json.loads(f.read_text()))
        return _state["holds"] if (HOME / "brain.pt").exists() else {}
    except (OSError, ValueError):
        return {}


def _brain():
    f = HOME / "brain.pt"
    m = f.stat().st_mtime
    if _state.get("m") != m:
        import torch
        if str(config.ROOT) not in sys.path:
            sys.path.insert(0, str(config.ROOT))
        from training import scratch as T
        meta = json.loads((HOME / "brain.json").read_text())
        model = T.Brain({k: len(v) for k, v in meta["jobs"].items()}, meta.get("talk", False))
        model.load_state_dict(torch.load(f))
        _state.update(m=m, model=model.eval(), meta=meta, tok=T.tokenizer(), T=T, torch=torch)
    return _state


def answer(skill, texts):
    """The brain's label for each text of one job."""
    with _lock:
        st = _brain()
        T, torch = st["T"], st["torch"]
        labels, out = st["meta"]["jobs"][skill], []
        with torch.no_grad():
            for i in range(0, len(texts), 64):
                ids, last = T._batch(st["tok"], texts[i:i + 64])
                out += [labels[j] for j in st["model"](skill, ids, last)[0].argmax(-1).tolist()]
    return out


def decide_holds(tests, wins, margin=0.0):
    """Which jobs the brain takes, from its test scores and the present holders' scores on the same test (wins.json:
    "cell" is today's cell, "incumbent" the member or rule; "use" says which of the two has the job now)."""
    out = {}
    for skill, score in tests.items():
        w = wins.get(skill) or {}
        was = w.get("cell") if w.get("use") else w.get("incumbent")
        if was is not None and score >= was + margin:
            out[skill] = {"test": round(score, 4), "was": was, "from": "today's cell" if w.get("use") else "the member or rule"}
    return out
