"""Engrams: the body's fast memory. One checked piece of work, kept as one tiny ternary weight edit.

A cell is regrown from everything the hive has checked, once a night: slow memory. An engram is written in about a
minute from ONE task the body has just solved (two cells agreed; in practice the task's check confirmed it), with
nothing else retrained and nothing old touched. When a later task is like it, the engram is switched on beside the
cell that works on the task (the runtime adds any number of edits to the one ternary model in memory). So the body
can learn during the day and forget nothing; the nightly regrowth folds what the engrams hold into the cells.

    cells/engrams/<dna>+e<id>.gguf     the edit (ternary values, rank 4, the last 8 layers: a few megabytes)
    cells/engrams/index.jsonl          one line each: its name, the task it came from, when

HIVE_ENGRAMS=1 turns recall on in team/solo.py. Whether engrams help is measured, not assumed
(training/experiments/engram_stream.py): a memory of one solution can also make a cell copy old values, which is
what the library of solved programs did.
"""
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from . import memory, ternary


def index():
    try:
        return [json.loads(x) for x in (ternary.ENGRAMS / "index.jsonl").read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def recall(task, base, most=2, least=0.34):
    """The names of the engrams of this DNA whose tasks are most like this one (shared words over all words)."""
    mine, out = memory.words(task), []
    for e in index():
        theirs = memory.words(e.get("task", ""))
        score = len(mine & theirs) / max(1, len(mine | theirs))
        if e.get("dna") == base and score >= least and e.get("task") != task and (ternary.ENGRAMS / f"{base}+{e['name']}.gguf").exists():
            out.append((score, e["name"]))
    return [name for _, name in sorted(out, reverse=True)[:most]]


def write(task, run, base="t17", steps=12, log=print):
    """Write the engram of a task the body solved: run is the task's folder (with what each cell wrote). Returns its
    name, or None when there was nothing to keep."""
    from training import grow
    rows = grow.rows_of(run, task)
    if not rows:
        return None
    name = "e" + hashlib.sha1(task.encode()).hexdigest()[:8]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))
    t0 = time.time()
    meta = grow.train(f.name, name, base=base, epochs=max(1.0, steps / len(rows)), rank=4, lr=5e-4, layers="last8", accum=1, ternary_edit=True,
                      out_dir=ternary.ENGRAMS, checkpoint=False, log=lambda *a, **k: None)
    os.unlink(f.name)
    with open(ternary.ENGRAMS / "index.jsonl", "a") as f:
        f.write(json.dumps({"name": name, "dna": base, "task": task[:1500], "when": time.strftime("%Y-%m-%d %H:%M"), "rows": len(rows),
                            "seconds": round(time.time() - t0), "megabytes": meta.get("megabytes")}) + "\n")
    log(f"engram {name}: {len(rows)} rows, {round(time.time() - t0)} s, {meta.get('megabytes')} MB, loss {meta.get('loss_first')} -> {meta.get('loss_last')}")
    return name
