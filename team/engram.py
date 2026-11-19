"""Recall compatible weight edits alongside the active cell.

The original writer trains a small edit on checked work by a cell. Its descendants can recall it by task
similarity and lineage. The domain trainer fits rank-four output edits to bounded label choices on the frozen
8B base. Each verified local topic has a recorded panel of correct answers that a successor must preserve.

    cells/engrams/                shipped weights and their index.jsonl
    runs/engram-learning/native/  private local weights and their index.jsonl
    HIVE_ENGRAMS_HOME             override with a single isolated store

Ordinary chat and work recall compatible edits by default. HIVE_ENGRAMS=0 disables automatic recall.
HIVE_ENGRAM_GATE=1 varies the activation strength with the task match. HIVE_ENGRAM_MATCH=embed selects
cosine similarity of token embeddings, with word overlap as the fallback. Folded entries stay in the
index so their history can be inspected. Recall and answer quality are measured separately.
"""
import hashlib
import json
import os
import re
import stat
import tempfile
import time
from copy import deepcopy
from functools import lru_cache

from . import engram_index, memory, ternary
from .engram_index import catalog as _catalog, rows as _rows


def index():
    rows = []
    for home in ternary.engram_homes():
        try:
            rows.extend(_rows(home / "index.jsonl"))
        except (OSError, ValueError):
            continue
    return rows


@lru_cache(maxsize=256)
def _sha256(path, identity):
    """The caller's file identity changes even when an in-place writer restores size and mtime."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _raw_store(home, shelf):
    return shelf is None and home not in (ternary.LOCAL_ENGRAMS, ternary.BUNDLED_ENGRAMS)


def _weight(home, shelf, base, name):
    if shelf is engram_index.UNREADABLE:
        return None
    row = shelf.records.get(name) if shelf is not None else None
    if row is None:
        if name != "hive" and not _raw_store(home, shelf):
            return None
    elif (row.get("folded") is not None or row.get("archived")
          or (row.get("form") == "label" and row.get("verified") is not True)):
        return None
    path = home / f"{base}+{name}.gguf"
    try:
        info = path.stat()
        if stat.S_ISREG(info.st_mode) and (row is None or "sha256" not in row
                or row["sha256"] == _sha256(path, engram_index.identity(info))):
            return path, row
    except OSError:
        pass
    return None


def bank_entries(base, home):
    """Expose qualified, physically available revisions, including the explicit raw experiment directory."""
    shelf = engram_index.shelf(home, base)
    if _raw_store(home, shelf):
        return {p.stem.split("+", 1)[1]: (p, None) for p in home.glob(f"{base}+*.gguf") if p.is_file()}
    names = dict.fromkeys(shelf.records if shelf is not None else ())
    names.setdefault("hive")
    result = {}
    for name in names:
        item = _weight(home, shelf, base, name)
        if item:
            path, row = item
            result[name] = (path, deepcopy(row))
    return result


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


def _mentions(text, term):
    return isinstance(term, str) and bool(term.strip()) and bool(
        re.search(r"(?<!\w)" + re.escape(" ".join(term.casefold().split())) + r"(?!\w)", text))


def _label_score(task, record, domain, *, framed):
    """A domain alone cannot establish that the edit learned this question or its output form."""
    labels, cues = record.get("labels"), record.get("cues")
    if (record.get("verified") is not True or not isinstance(labels, list) or not 2 <= len(labels) <= 16
            or not all(isinstance(x, str) and x.strip() for x in labels)
            or len({x.casefold() for x in labels}) != len(labels) or not isinstance(cues, list)
            or (domain and domain != record.get("domain"))):
        return 0
    text = " ".join(task.casefold().split())
    count = sum(_mentions(text, c) for c in cues)
    named = bool(record.get("growth_group")) and _mentions(text, record.get("task"))
    if framed:
        # Directly applying these weights requires a request for the same restricted output alphabet.
        if (not all(_mentions(text, x) for x in labels) or not re.search(
                r"\b(?:classify|categorize|pick|choose|select|label|reply|respond|return|output|answer|which)\b", text)):
            return 0
        if not (count or named or (domain and domain == record.get("domain"))):
            return 0
    elif not (count or named) or domain != record.get("domain"):
        return 0
    return min(1.0, 0.8 + 0.05 * count)


def _active(base, *, labels_only=False, words=None, least=0.34, labels=True):
    stores = [(home, engram_index.shelf(home, base)) for home in ternary.engram_homes()]
    names = {}
    for home, shelf in stores:
        if shelf is None:
            continue
        if labels_only:
            names.update(dict.fromkeys(shelf.labels))
        elif words is None:
            names.update(dict.fromkeys(shelf.records))
        else:
            names.update(dict.fromkeys(shelf.matches(words, least)))
            if labels:
                names.update(dict.fromkeys(shelf.labels))
    for name in names:
        if name == "hive" or (ternary.ADAPTERS / f"{base}+{name}.gguf").is_file():
            continue
        # A higher-priority store can own this name even when its own words did not match.
        for home, shelf in stores:
            item = _weight(home, shelf, base, name)
            if item:
                row = item[1]
                if row and isinstance(row.get("task"), str):
                    yield row
                break


def enabled():
    return os.environ.get("HIVE_ENGRAMS", "1").strip().lower() not in {"0", "off", "false", "no"}


def _can_recall(member):
    return enabled() and isinstance(member, str) and member.partition("+")[0] in ternary.MODELS


def is_label_request(task, row, domain=None):
    """Whether this message explicitly requests this verified edit's restricted answer form."""
    return row.get("form") == "label" and bool(_label_score(task, row, domain, framed=True))


def _choose_label(task, candidates):
    """An explicitly named learned topic takes priority. A tie cannot identify the requested convention."""
    text = " ".join(task.casefold().split())
    candidates = [(score, row) for score, row in candidates if score]
    if not candidates:
        return None
    named = []
    for score, row in candidates:
        if row.get("growth_group"):
            topic = " ".join(row["task"].casefold().split())
            if topic:
                for match in re.finditer(r"(?<!\w)" + re.escape(topic) + r"(?!\w)", text):
                    named.append((match.span(), row["name"]))
    if named:
        # "Depot Rule revised" names the longer topic. If "Depot Rule" is also mentioned separately, abstain.
        names = {name for (start, end), name in named if not any(
            left <= start and right >= end and right - left > end - start for (left, right), _ in named)}
        winners = [(score, row) for score, row in candidates if row["name"] in names]
    else:
        best = max(score for score, _ in candidates)
        winners = [(score, row) for score, row in candidates if score == best]
    return winners[0] if len(winners) == 1 else None


_ASK_LABEL = re.compile(
    r"(?:^|[,:;.!?]\s*|\b(?:please|to|can you|could you|will you|would you)\s+)"
    r"(?:classify|categori[sz]e|label|grade)\s+\S|"
    r"\b(?:which|what|return|choose|select|assign|give|output)\s+(?:[\w'-]+\s+){0,3}"
    r"(?:code|label|category|class|grade)\b")


def named_label_for(task, member):
    """Find a verified user-learned convention when a request explicitly names it and asks for a class."""
    if not _can_recall(member):
        return None
    text = " ".join(task.casefold().split())
    if not _ASK_LABEL.search(text) or re.search(r"\b(?:do not|don't|never|how to|how (?:do|would) (?:i|you))\s+"
                                               r"(?:classify|categori[sz]e|label|grade|return|choose|select|assign|give|output)\b", text):
        return None
    matches = []
    for row in _active(ternary.split(member)[0], labels_only=True):
        domain = row.get("domain")
        if (row.get("form") == "label" and isinstance(row.get("growth_group"), str) and row["growth_group"]
                and isinstance(domain, str) and domain and _mentions(text, row["task"])):
            matches.append((_label_score(task, row, domain, framed=False), row))
    match = _choose_label(task, matches)
    return deepcopy(match[1]) if match else None


def label_for(task, member, domain):
    """Find an applicable checked label edit for a *separate* framed inference on this ordinary request."""
    if not _can_recall(member) or not domain:
        return None
    choices = ((_label_score(task, row, domain, framed=False), row)
               for row in _active(ternary.split(member)[0], labels_only=True) if row.get("form") == "label")
    choice = _choose_label(task, choices)
    return deepcopy(choice[1]) if choice else None


def _ranked(task, base, cell=None, most=2, least=0.34, *, domain=None, serving=False, labels=True):
    """[(name, score)] of the engrams recall chooses (see recall), the least that counted as alike, and whether the
    hive's shared engram is there."""
    line = lineage(cell)
    entries, domain_edits = [], []
    words = None if os.environ.get("HIVE_ENGRAM_MATCH") == "embed" else memory.words(task)
    for e in _active(base, words=words, least=least, labels=labels):
        if e.get("form"):
            if labels and e["form"] == "label":
                score = _label_score(task, e, domain, framed=True)
                if score:
                    domain_edits.append((score, e))
        elif (serving or e["task"] != task) and not (domain and e.get("domain") and domain != e["domain"]):
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
    out = []
    choice = _choose_label(task, domain_edits)
    if choice and most > 0:
        score, row = choice
        out.append((row["name"], score))
    out.extend((name, -neg) for _, neg, name in sorted(near or far)[:max(0, most - len(out))])
    shared = any(_weight(home, engram_index.shelf(home, base), base, "hive") for home in ternary.engram_homes())
    return out, least, shared


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


def for_request(task, member, *, domain=None, labels=True):
    """Select actual local weights for this request. An explicit empty selection means no overlays."""
    if not _can_recall(member):
        return ()
    from . import domain_route
    domain = domain_route.current_domain() if domain is None else domain
    base, cell = ternary.split(member)
    # Earlier quoted instructions do not turn the current request into a label-choice task.
    latest = task.partition("\n\n(This continues a conversation. What was said before, for what the task refers to:")[0]
    selected, least, hive = _ranked(latest, base, cell, domain=domain, serving=True, labels=labels)
    if os.environ.get("HIVE_ENGRAM_GATE") == "1":
        return tuple((name, gate(score, least)) for name, score in selected) + (
            (("hive", float(os.environ.get("HIVE_HIVE_SCALE", 0.5))),) if hive else ())
    return tuple(name for name, _ in selected) + (("hive",) if hive else ())


def update_index(transform, *, home=None):
    """Atomically replace current rows with transform(rows), or leave them unchanged when it returns None."""
    import fcntl
    home = ternary.ENGRAMS if home is None else home
    home.mkdir(parents=True, exist_ok=True)
    path = home / "index.jsonl"
    with (home / ".index.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        rows = _rows(path) if path.is_file() else []
        replacement = transform(rows)
        if replacement is None:
            return
        with tempfile.NamedTemporaryFile("w", dir=home, delete=False) as tmp:
            try:
                for row in replacement:
                    tmp.write(json.dumps(row, allow_nan=False) + "\n")
                tmp.flush()
                os.fsync(tmp.fileno())
                os.replace(tmp.name, path)
                directory = os.open(home, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            finally:
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)


def _rewrite(change):
    if not (ternary.ENGRAMS / "index.jsonl").is_file():
        return 0
    changed = 0
    def apply(rows):
        nonlocal changed
        for i, row in enumerate(rows):
            updated = change(row)
            if updated is not None:
                rows[i] = updated
                changed += 1
        return rows if changed else None
    update_index(apply)
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
    try:
        meta = grow.train(f.name, name, base=base, epochs=max(1.0, steps / len(rows)), rank=4, lr=5e-4, layers="last8", accum=1, ternary_edit=True,
                          out_dir=ternary.ENGRAMS, checkpoint=False, log=lambda *a, **k: None)
    finally:
        os.unlink(f.name)
    row = {"name": name, "dna": base, "cell": (lineage(cell) or [None])[0], "task": task[:1500],
           "when": time.strftime("%Y-%m-%d %H:%M"), "rows": len(rows), "seconds": round(time.time() - t0),
           "megabytes": meta.get("megabytes")}
    update_index(lambda records: [r for r in records if (r.get("dna"), r.get("name")) != (base, name)] + [row])
    log(f"engram {name}: {len(rows)} rows, {round(time.time() - t0)} s, {meta.get('megabytes')} MB, loss {meta.get('loss_first')} -> {meta.get('loss_last')}")
    return name
