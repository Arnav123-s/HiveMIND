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

HIVE_ENGRAMS=1 turns recall on in team/solo.py. Two more, both off unless asked:
    HIVE_ENGRAM_GATE=1       an engram is switched on as strongly as its task matches (recall_scaled: from 0.25 for
                             one just alike enough to 1.0, HIVE_ENGRAM_GAIN 2; the hive's own at HIVE_HIVE_SCALE 0.5),
                             not at full strength whatever the match, as side-memory editing gates its memories
    HIVE_ENGRAM_MATCH=embed  alike by the cosine of the tasks' mean token embeddings (the runtime's /embedding; at
                             least HIVE_ENGRAM_EMBED_LEAST 0.8), not shared words; words again on any error Whether engrams help is measured, not assumed
(training/experiments/engram_stream.py): a memory of one solution can also make a cell copy old values, which is
what the library of solved programs did.
"""
import hashlib
import json
import os
import tempfile
import time

from . import memory, ternary


def _rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def index():
    try:
        return _rows(ternary.ENGRAMS / "index.jsonl")
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


def _scores(task, base, entries):
    """{name: how alike its task is to this one, 0 to 1}, and the `least` that counts as alike for that measure.
    HIVE_ENGRAM_MATCH=embed: the cosine of the mean token embeddings of the two tasks, from the runtime's /embedding
    endpoint (vectors of the engrams' tasks kept in the index as "vec"); on any error, silently, shared words over all
    words, as by default."""
    if os.environ.get("HIVE_ENGRAM_MATCH", "words") == "embed":
        try:
            got = _embed_scores(task, base, entries)
            if got is not None:
                return got, float(os.environ.get("HIVE_ENGRAM_EMBED_LEAST", 0.8))
        except Exception:  # noqa: BLE001 - any trouble with the server or the cache: words, as by default
            pass
    mine = memory.words(task)
    out = {}
    for e in entries:
        theirs = memory.words(e.get("task", ""))
        out[e["name"]] = len(mine & theirs) / max(1, len(mine | theirs))
    return out, None


def embed_url(base):
    """Where the mean token embedding of a text is asked: HIVE_ENGRAM_EMBED_URL, else the base's own server. The
    runtime answers /embedding only when started with --embeddings (which also stops it writing), so the base's server
    usually refuses, and the words decide."""
    return os.environ.get("HIVE_ENGRAM_EMBED_URL") or f"http://127.0.0.1:{ternary.port(base)}/embedding"


def embed(text, base, timeout=20):
    """The mean of the token embeddings of a text, as the runtime gives them (a list of floats). Raises on any
    trouble. The runtime answers [{"index": 0, "embedding": [[...], ...]}] (one row a token, or one pooled row), or
    older ones {"embedding": [...]}."""
    got = ternary._post(embed_url(base), {"content": text}, timeout=timeout)
    if isinstance(got, list):
        got = got[0]
    rows = got["embedding"]
    if rows and not isinstance(rows[0], list):
        rows = [rows]
    if not rows or not rows[0]:
        raise ValueError("no embedding")
    n = len(rows[0])
    return [sum(r[i] for r in rows) / len(rows) for i in range(n)]


def cosine(a, b):
    num = sum(x * y for x, y in zip(a, b))
    den = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
    return num / den if den else 0.0


def _embed_scores(task, base, entries):
    """{name: cosine} of each engram's task to this one, its vector taken from the index or asked once and kept there.
    None when the server gives nothing."""
    mine = embed(task, base)
    out, fresh = {}, {}
    for e in entries:
        vec = e.get("vec")
        if not (isinstance(vec, list) and len(vec) == len(mine)):
            vec = embed(e.get("task", ""), base)
            fresh[e["name"]] = [round(x, 5) for x in vec]
        out[e["name"]] = cosine(mine, vec)
    if fresh:
        _keep_vectors(fresh)
    return out


def _keep_vectors(vecs):
    """Write the vectors of these engrams' tasks into their lines of the index ("vec"), so each is asked once."""
    _rewrite(lambda e: {**e, "vec": vecs[e["name"]]} if e.get("name") in vecs else None)


def _ranked(task, base, cell=None, most=2, least=0.34):
    """[(name, score)] of the engrams recall chooses (see recall), the least that counted as alike, and whether the
    hive's shared engram is there."""
    line = lineage(cell)
    entries, seen = [], set()
    for e in index():
        name = e.get("name")
        if not name or name in seen or e.get("dna") != base or e.get("folded") is not None or e.get("task") == task:
            continue
        seen.add(name)
        if (ternary.ENGRAMS / f"{base}+{name}.gguf").exists():
            entries.append(e)
    scores, other_least = _scores(task, base, entries) if entries else ({}, None)
    least = least if other_least is None else other_least
    near, far = [], []
    for e in entries:
        name, score = e["name"], scores.get(e["name"], 0.0)
        if score < least:
            continue
        owner = e.get("cell") or ""
        if not line or owner in line:  # no cell asking: every engram is as near as any other
            near.append((line.index(owner) if line else 0, -score, name))
        elif not owner:
            near.append((len(line), -score, name))
        else:
            far.append((0, -score, name))
    out = [(name, -neg) for _, neg, name in sorted(near or far)[:most]]
    return out, least, (ternary.ENGRAMS / f"{base}+hive.gguf").exists()


def recall(task, base, cell=None, most=2, least=0.34):
    """The names of the engrams of this DNA whose tasks are most like this one (shared words over all words), at most
    `most` of them, each at least `least` alike. The cell's own engrams come first, then its ancestors' (nearest first),
    then those of no cell; other cells' only when none of these is alike enough. Folded engrams are skipped. When the
    hive's shared engram is there (<dna>+hive.gguf) "hive" is added last, beyond `most`."""
    out, _, hive = _ranked(task, base, cell, most, least)
    return [name for name, _ in out] + (["hive"] if hive else [])


def gate(score, least, gain=None, floor=0.25):
    """How strongly an engram is switched on, from how alike its task is: an engram just alike enough at `floor`,
    rising with the likeness (`gain` times its share of the way from `least` to a perfect match) to full strength."""
    gain = float(os.environ.get("HIVE_ENGRAM_GAIN", 2.0)) if gain is None else gain
    share = (score - least) / max(1e-9, 1 - least)
    return round(min(1.0, max(floor, share * gain)), 3)


def recall_scaled(task, base, cell=None, most=2, least=0.34):
    """recall(), each engram with the strength it is switched on with: [(name, scale)]. The scale follows how well its
    task matches (gate()); the hive's shared engram, which matches every task a little, at HIVE_HIVE_SCALE (0.5)."""
    out, least, hive = _ranked(task, base, cell, most, least)
    got = [(name, gate(score, least)) for name, score in out]
    if hive:
        got.append(("hive", float(os.environ.get("HIVE_HIVE_SCALE", 0.5))))
    return got


def _rewrite(change):
    """Rewrite the index, each line through change(entry) (a new entry, or None to keep it as it is). Returns how many
    lines changed."""
    path = ternary.ENGRAMS / "index.jsonl"
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return 0
    out, changed = [], 0
    for x in lines:
        try:
            e = json.loads(x) if x.strip() else None
        except ValueError:
            e = None
        new = change(e) if isinstance(e, dict) else None
        if new is not None:
            x, changed = json.dumps(new), changed + 1
        out.append(x)
    if changed:
        tmp = path.with_suffix(".tmp")
        tmp.write_text("".join(x + "\n" for x in out))
        os.replace(tmp, path)
    return changed


def fold(names, generation):
    """Mark these engrams folded: the cells of this generation were trained on their rows, so they are not recalled
    again. Returns how many lines of the index it marked."""
    names = set(names)
    return _rewrite(lambda e: {**e, "folded": generation} if e.get("name") in names and e.get("folded") is None else None)


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
