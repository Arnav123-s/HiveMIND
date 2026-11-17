"""Engrams: the body's fast memory. One checked piece of work, kept as one tiny ternary weight edit.

A cell is regrown from everything the hive has checked, once a night: slow memory. An engram is written in about a
minute from ONE task the body has just solved (two cells agreed; in practice the task's check confirmed it), with
nothing else retrained and nothing old touched. When a later task is like it, the engram is switched on beside the
cell that works on the task (the runtime adds any number of edits to the one ternary model in memory). So the body
can learn during the day and forget nothing; the nightly regrowth folds what the engrams hold into the cells.

    cells/engrams/<dna>+e<id>.gguf     the edit (ternary values, rank 4, the last 8 layers: a few megabytes)
    cells/engrams/index.jsonl          one line each: its name, the task it came from, when, and the cell it belongs to
    cells/engrams/<dna>+hive.gguf      the hive's shared engram, when there is one (training/hive_engram.py)

Every cell has an engram memory of its own: an engram belongs to the cell that solved its task (or was corrected on
it), and a child sees its own engrams first, then those of its parent, grandparent and so on (the body's lines of
descent, cells/body.json "parents"), and others' only when nothing closer is like the task. Once the nightly
regrowth has trained a cell on an engram's rows, fold() marks it and it is recalled no more: the cells hold it now.
Old lines with no cell belong to no one: every cell may recall them, after its own line.

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


def lineage(cell):
    """[cell, its parent, its grandparent, ...] by the body's record of whose child each cell is (cells/body.json
    "parents"). A member name ("t80+g41code") counts as its cell. Just [cell] when its line is not known, [] for none."""
    c = (cell or "").partition("+")[2] if "+" in (cell or "") else (cell or "")
    parents = {k: v for k, v in ternary._parents().items() if isinstance(v, str)}
    out = []
    while c and c not in out:
        out.append(c)
        c = parents.get(c, "")
    return out


def recall(task, base, cell=None, most=2, least=0.34):
    """The names of the engrams of this DNA whose tasks are most like this one (shared words over all words), at most
    `most` of them, each at least `least` alike. The cell's own engrams come first, then its ancestors' (nearest first),
    then those of no cell; other cells' only when none of these is alike enough. Folded engrams are skipped. When the
    hive's shared engram is there (<dna>+hive.gguf) "hive" is added last, beyond `most`."""
    line = lineage(cell)
    mine, near, far, seen = memory.words(task), [], [], set()
    for e in index():
        name = e.get("name")
        if not name or name in seen or e.get("dna") != base or e.get("folded") is not None or e.get("task") == task:
            continue
        seen.add(name)
        theirs = memory.words(e.get("task", ""))
        score = len(mine & theirs) / max(1, len(mine | theirs))
        if score < least or not (ternary.ENGRAMS / f"{base}+{name}.gguf").exists():
            continue
        owner = e.get("cell") or ""
        if not line or owner in line:  # no cell asking: every engram is as near as any other
            near.append((line.index(owner) if line else 0, -score, name))
        elif not owner:
            near.append((len(line), -score, name))
        else:
            far.append((0, -score, name))
    out = [name for _, _, name in sorted(near or far)[:most]]
    if (ternary.ENGRAMS / f"{base}+hive.gguf").exists():
        out.append("hive")
    return out


def fold(names, generation):
    """Mark these engrams folded: the cells of this generation were trained on their rows, so they are not recalled
    again. Returns how many lines of the index it marked."""
    names, marked = set(names), 0
    path = ternary.ENGRAMS / "index.jsonl"
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return 0
    out = []
    for x in lines:
        try:
            e = json.loads(x) if x.strip() else None
        except ValueError:
            e = None
        if isinstance(e, dict) and e.get("name") in names and e.get("folded") is None:
            e["folded"] = generation
            x, marked = json.dumps(e), marked + 1
        out.append(x)
    if marked:
        tmp = path.with_suffix(".tmp")
        tmp.write_text("".join(x + "\n" for x in out))
        os.replace(tmp, path)
    return marked


def write(task, run, base="t17", cell=None, steps=12, log=print):
    """Write the engram of a task the body solved: run is the task's folder (with what each cell wrote); cell is the
    cell that solved it or was corrected on it (its engram memory keeps it). Returns its name, or None when there was
    nothing to keep."""
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
        f.write(json.dumps({"name": name, "dna": base, "cell": (lineage(cell) or [None])[0], "task": task[:1500], "when": time.strftime("%Y-%m-%d %H:%M"), "rows": len(rows),
                            "seconds": round(time.time() - t0), "megabytes": meta.get("megabytes")}) + "\n")
    log(f"engram {name}: {len(rows)} rows, {round(time.time() - t0)} s, {meta.get('megabytes')} MB, loss {meta.get('loss_first')} -> {meta.get('loss_last')}")
    return name
