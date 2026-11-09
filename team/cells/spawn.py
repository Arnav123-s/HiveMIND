"""The hive spawns its own cells: nobody declares the job first.

Every model call a member makes inside a run is already logged (runs/<run>/calls.jsonl). A call site is one member
with one instruction (its system prompt). Many sites are small decisions in disguise: the member reads a text and
replies PASS or FAIL, true or false, SUPPORTED or UNSUPPORTED, one name of a few. This module

  notice()   reads the logs, groups the calls by site, and finds the sites whose replies fall into a few fixed values
             (the DECISION). Free text beside the decision is allowed only where it is an explanation (a "reason").
             Each such site becomes a new job: a spawned skill, written to cells/spawned.json with its instruction,
             its labels and the exact reply to give for each label; its logged decisions become its training rows
             (memory/decisions/<skill>.jsonl, oldest first).
  answer()   called by team/llm.py before a member is asked. If a cell holds that site's job (it passed the gate in
             training/cells_spawn.py) and it is sure enough of a label it may answer, its reply is used and the
             member is not run. Otherwise the member answers as before, and that answer is logged for the next
             round of training.
  audit      now and then a call the cell would have answered goes to the member anyway and the two are compared
             (memory/spawn_audit.jsonl). review() retires a cell whose agreement on those real calls falls under
             RETIRE: its job goes back to the member until a retrained cell passes the gate again.

So the loop is: a member does a job by itself -> the hive notices the job is small -> a cell is trained on the
member's own decisions -> it takes the calls it is sure about -> it is checked on live calls -> it is retrained on
newer decisions or retired. `python -m team life` runs one turn of that loop (team/life.py).
AGENT_TEAM_SPAWN=0 turns every spawned cell off.
"""
import hashlib
import json
import os
import random
import re
import threading
import time
from collections import Counter
from pathlib import Path

from .. import config, memory
from . import runtime, skills as S

SPAWNED = S.SPAWNED_FILE
AUDIT = memory.HOME / "spawn_audit.jsonl"
USED = memory.HOME / "spawn_used.jsonl"
EXPLAIN = {"reason", "why", "note", "explanation", "because", "comment"}  # free text that only explains the decision
MAX_LABELS = 6
COVER = 0.97       # the few fixed values must cover this share of a site's replies
MINORITY = 0.05    # and the second most common value at least this share: a site that always says one thing teaches nothing
AUDIT_RATE = float(os.environ.get("AGENT_TEAM_SPAWN_AUDIT", 0.1))
RETIRE = 0.93      # agreement with the member on audited live calls under which a cell is retired
AUDIT_MIN = 30
CLIP_HEAD, CLIP_TAIL = 1000, 450
_local = threading.local()
_cache = {}
_rnd = random.Random()


# ------------------------------------------------------------------ what a call is
def site_id(specialist, system):
    return hashlib.sha1(f"{specialist}|{system[:200]}".encode()).hexdigest()[:8]


def clip(text):
    """What the cell reads of the member's input: a 135M cell holds about 1000 tokens, so a long input keeps its
    head (the question) and its tail."""
    text = text.strip()
    if len(text) <= CLIP_HEAD + CLIP_TAIL + 20:
        return text
    return text[:CLIP_HEAD] + "\n[...]\n" + text[-CLIP_TAIL:]


def _closed(v):
    if isinstance(v, bool) or v is None:
        return True
    if isinstance(v, str):
        return 0 < len(v) <= 24 and len(v.split()) <= 2
    if isinstance(v, list):
        return len(v) <= 4 and all(isinstance(x, str) and 0 < len(x) <= 24 and len(x.split()) <= 2 for x in v)
    return False


def _show(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, list):
        return "+".join(sorted(v)) or "none"
    return v


def decision(output):
    """(label, closed fields or None, free fields) of a member's reply; None when the reply is not a small decision."""
    t = (output or "").strip()
    if t.startswith("{"):
        try:
            d = json.loads(t)
        except ValueError:
            return None
        if not isinstance(d, dict):
            return None
        closed = {k: v for k, v in d.items() if k not in EXPLAIN and _closed(v)}
        if not closed:
            return None
        free = {k: v for k, v in d.items() if k not in closed and v not in ("", [], {}, None)}
        return "/".join(_show(closed[k]) for k in sorted(closed)), closed, free
    if 0 < len(t) <= 24 and "\n" not in t and len(t.split()) <= 2:
        return t, None, {}
    return None


# ------------------------------------------------------------------ notice: read the logs, find the small jobs
def _call_files(dirs=None, bench=False):
    roots = [Path(d) for d in dirs] if dirs else [config.RUNS]
    out = []
    for r in roots:
        if r.exists():
            out += [p for p in r.rglob("calls.jsonl") if bench or dirs or "bench" not in p.relative_to(r).parts]
    return sorted(out, key=lambda p: (p.stat().st_mtime, str(p)))


def calls(dirs=None, bench=False):
    """Every logged member call of two messages (instruction, input), oldest first. Bench runs are left out unless
    asked for: the bench must not teach the hive."""
    for f in _call_files(dirs, bench):
        t = f.stat().st_mtime
        for i, ln in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines()):
            try:
                c = json.loads(ln)
            except ValueError:
                continue
            m = c.get("messages") or []
            if len(m) == 2 and m[0].get("role") == "system" and m[1].get("role") == "user":
                yield {"ts": t + i * 1e-4, "specialist": c["specialist"], "system": m[0]["content"],
                       "user": m[1]["content"], "output": c.get("output", ""), "seconds": c.get("seconds", 0.0),
                       "by_cell": c.get("by_cell")}


def sites(dirs=None, bench=False):
    """Every call site in the logs: its calls, how long the member spent there, and whether it is a small decision."""
    by = {}
    for c in calls(dirs, bench):
        if c["by_cell"]:  # a cell's own answer is not the member's decision: never train on it
            continue
        s = by.setdefault(site_id(c["specialist"], c["system"]),
                          {"specialist": c["specialist"], "system": c["system"], "rows": [], "seconds": 0.0, "calls": 0})
        s["calls"] += 1
        s["seconds"] += c["seconds"] or 0.0
        s["rows"].append((c["ts"], c["user"], decision(c["output"])))
    for sid, s in by.items():
        s["id"] = sid
        s["name"] = f"sp_{re.sub(r'[^a-z0-9]', '', s['specialist'].lower())}_{sid[:6]}"
        s.update(_shape(s["rows"]))
    return by


def _shape(rows):
    """Is this site a small decision? The labels, which of them a cell may answer, and the reply for each."""
    dec = [d for _, _, d in rows if d]
    n = len(rows)
    if not n or len(dec) < n * COVER:
        return {"decision": False, "why": f"{n - len(dec)} of {n} replies are not a small fixed value"}
    count = Counter(d[0] for d in dec)
    top = count.most_common(MAX_LABELS)
    if sum(c for _, c in top) < n * COVER:
        return {"decision": False, "why": f"more than {MAX_LABELS} different replies"}
    labels = [lab for lab, c in top if c >= max(2, n * 0.01)]
    if len(labels) < 2 or top[1][1] < n * MINORITY:
        return {"decision": False, "why": f"almost always the same reply ({top[0][0]!r}, {top[0][1]} of {n})"}
    if len({lab[0].lower() for lab in labels}) < len(labels):  # the cell is read from its label's first token
        return {"decision": False, "why": "two replies start with the same letter"}
    fill, answers = {}, []
    for lab in labels:
        mine = [d for d in dec if d[0] == lab]
        if mine[0][1] is None:  # the whole reply is the label
            fill[lab] = lab
            answers.append(lab)
            continue
        closed = Counter(json.dumps(d[1], sort_keys=True) for d in mine).most_common(1)[0][0]
        free = Counter(k for d in mine for k in d[2])
        needed = [k for k, c in free.items() if c > len(mine) * 0.1]
        if all(k in EXPLAIN for k in needed):  # the rest of the reply only explains: the cell can give the whole reply
            fill[lab] = json.dumps({**json.loads(closed), **{k: "decided by a cell grown from this member's own decisions"
                                                              for k in needed}})
            answers.append(lab)
    return {"decision": True, "labels": labels, "answers": answers, "fill": fill,
            "counts": {lab: count[lab] for lab in labels}}


def _instr(system, labels):
    """The cell's instruction: the head of the member's own, and the labels it must choose from."""
    head = re.split(r"\n\s*Reply with|\nReply ", system.strip())[0]
    head = " ".join(head.split())[:400]
    return f"{head}\nAnswer with one of: {', '.join(labels)}"


def spawned():
    return json.loads(SPAWNED.read_text()) if SPAWNED.exists() else {}


def _save(sp):
    SPAWNED.parent.mkdir(exist_ok=True)
    tmp = SPAWNED.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(sp, indent=1, ensure_ascii=False))
    tmp.replace(SPAWNED)
    S.load_spawned()


def set_status(name, status, **fields):
    sp = spawned()
    sp[name].update(status=status, **fields)
    _save(sp)
    return sp[name]


def rows_of(site):
    """A site's training rows: (time, what the cell reads, label), one per distinct input, oldest first."""
    seen, out = set(), []
    for ts, user, d in site["rows"]:
        x = clip(user)
        if d and d[0] in site["labels"] and x not in seen:
            seen.add(x)
            out.append((ts, x, d[0]))
    return out


def notice(min_rows=150, dirs=None, bench=False, log=print):
    """Find the small jobs in the logs. A decision site with at least min_rows distinct inputs is declared a spawned
    skill (cells/spawned.json) and its decisions written as training rows. Returns every site, for the report."""
    all_sites = sites(dirs, bench)
    sp = spawned()
    from . import learn
    for sid, s in sorted(all_sites.items(), key=lambda kv: -kv[1]["seconds"]):
        s["distinct"] = 0
        if not s["decision"]:
            continue
        rows = rows_of(s)
        s["distinct"] = len(rows)
        if not s["answers"]:
            s["why"] = "every reply carries text a cell cannot write"
            continue
        if len(rows) < min_rows and s["name"] not in sp:
            s["why"] = f"{len(rows)} distinct decisions logged, {min_rows} needed"
            continue
        old = sp.get(s["name"], {})
        sp[s["name"]] = {**old, "site": sid, "member": s["specialist"], "labels": s["labels"], "answers": s["answers"],
                         "fill": s["fill"], "instr": old.get("instr") or _instr(s["system"], s["labels"]),
                         "part": f"{s['specialist']}: spawned from its own calls ({' / '.join(s['labels'])})",
                         "system": s["system"], "status": old.get("status", "candidate"),
                         "born": old.get("born", time.strftime("%Y-%m-%d")), "rows": len(rows),
                         "member_seconds_per_call": round(s["seconds"] / max(1, s["calls"]), 2)}
        learn.DIR.mkdir(parents=True, exist_ok=True)
        with open(learn.DIR / f"{s['name']}.jsonl", "w") as f:
            for ts, x, y in rows:
                f.write(json.dumps({"ts": ts, "x": x, "y": y}, ensure_ascii=False) + "\n")
        s["why"] = f"a job: {len(rows)} decisions ({old.get('status', 'new candidate')})"
        if not old:
            log(f"[spawn] new job noticed: {s['name']} ({s['specialist']}; {' / '.join(s['labels'])}; {len(rows)} decisions)")
    _save(sp)
    return all_sites


# ------------------------------------------------------------------ rehearse: practice cases, decided by the member
_FIELD = re.compile(r"^([A-Z][A-Z _]{1,24}):", re.M)


def fields(text):
    """The labelled parts of a member's input ("CLAIM: ...\nQUOTE: ..."), in order: [(name, text)]."""
    m = list(_FIELD.finditer(text))
    return [(a.group(1), text[a.end():(m[i + 1].start() if i + 1 < len(m) else len(text))].strip())
            for i, a in enumerate(m)]


def _join(fs):
    return "\n".join(f"{k}: {v}" for k, v in fs)


def recombine(a, b, rnd):
    """A new input made of two real ones: input a with one number changed (a near miss), or with one of its parts
    taken from input b (a mismatch). None when the inputs have no labelled parts to work with."""
    fa, fb = fields(a), dict(fields(b))
    if len(fa) < 2:
        return None
    nums = [(i, m) for i, (_, v) in enumerate(fa) for m in re.finditer(r"\d+", v)]
    if nums and rnd.random() < 0.5:
        i, m = rnd.choice(nums)
        old = m.group(0)
        new = str(int(old) + rnd.choice([1, 2, 10, -1])) if len(old) < 9 else old[::-1]
        if new != old and not new.startswith("-"):
            k, v = fa[i]
            fa[i] = (k, v[:m.start()] + new + v[m.end():])
            return _join(fa)
    swap = [i for i, (k, v) in enumerate(fa) if k in fb and fb[k] != v]
    if not swap:
        return None
    i = rnd.choice(swap)
    fa[i] = (fa[i][0], fb[fa[i][0]])
    return _join(fa)


def rehearse(name, n=200, log=print, ask=None):
    """Give a spawned skill practice: recombine the OLDEST 70% of its real inputs (the part it trains on; never the
    newer decisions it is judged on) into up to n new inputs and let its member decide each one, with the member's
    own instruction. Real work is mostly easy yeses; practice is where the cell meets the near misses."""
    from . import learn
    sp = spawned()[name]
    real = learn.rows(name)
    train = [x for x, _ in real[:int(len(real) * 0.7)]]
    path = learn.DIR.parent / "rehearsed" / f"{name}.jsonl"
    have = {x for x, _ in learn.rehearsed(name)} | {x for x, _ in real}
    rnd, made, tries = random.Random(len(have)), 0, 0
    if ask is None:
        from .. import llm
        as_json = sp["fill"][sp["answers"][0]].startswith("{")
        system = sp.get("system")

        def ask(text):
            return llm._chat_member(sp["member"], [{"role": "system", "content": system}, {"role": "user", "content": text}],
                                    160, True, 0.0, "{" if as_json else "", "json" if as_json else None)
        if system is None:
            return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    while made < n and tries < n * 6 and len(train) >= 2:
        tries += 1
        x = recombine(*rnd.sample(train, 2), rnd)
        if not x or clip(x) in have:
            continue
        x = clip(x)
        have.add(x)
        d = decision(re.sub(r"<think>.*?</think>", "", ask(x), flags=re.S).strip())
        if d and d[0] in sp["labels"]:
            with open(path, "a") as f:
                f.write(json.dumps({"ts": time.time(), "x": x, "y": d[0]}, ensure_ascii=False) + "\n")
            made += 1
    log(f"[spawn] {name}: {made} practice decisions by {sp['member']} ({dict(Counter(y for _, y in learn.rehearsed(name)))} in all)")
    return made


# ------------------------------------------------------------------ answer: the cell takes the calls it is sure about
def _by_site():
    m = SPAWNED.stat().st_mtime if SPAWNED.exists() else 0
    if _cache.get("m") != m:
        S.load_spawned()
        _cache.update(m=m, by={v["site"]: (k, v) for k, v in spawned().items()})
    return _cache["by"]


def enabled():
    return os.environ.get("AGENT_TEAM_SPAWN", "1") != "0" and os.environ.get("AGENT_TEAM_CELLS", "1") != "0"


def answer(specialist, messages):
    """The reply of the cell that holds this call's job, or None: the member must answer."""
    _local.pending = None
    if not enabled() or len(messages) != 2 or not SPAWNED.exists():
        return None
    hit = _by_site().get(site_id(specialist, messages[0]["content"]))
    if not hit or hit[1].get("status") != "on":
        return None
    name, sp = hit
    from . import use
    w = use.wins().get(name, {})
    if not (w.get("use") and runtime.available(name)):
        return None
    try:
        p = runtime.label_probs(name, clip(messages[1]["content"]))
    except Exception:  # noqa: BLE001 - a cell that cannot run never stops the member
        return None
    lab, conf = max(p.items(), key=lambda kv: kv[1])
    if lab not in sp["answers"] or conf < w.get("thresholds", {}).get(lab, 1.01):
        return None
    if _rnd.random() < AUDIT_RATE:  # this one goes to the member too: observe() compares the two
        _local.pending = (name, lab, round(conf, 4))
        return None
    _append(USED, {"ts": time.time(), "cell": name, "label": lab, "conf": round(conf, 4)})
    return sp["fill"][lab]


def site_name(specialist, messages):
    hit = _by_site().get(site_id(specialist, messages[0]["content"]))
    return hit[0] if hit else "?"


def observe(specialist, messages, output):
    """After the member answered a call the cell was sure about: log whether they agree."""
    pend, _local.pending = getattr(_local, "pending", None), None
    if not pend:
        return
    d = decision(output)
    _append(AUDIT, {"ts": time.time(), "cell": pend[0], "cell_label": pend[1], "conf": pend[2],
                    "member_label": d[0] if d else None, "agree": bool(d) and d[0] == pend[1]})


def _append(path, row):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass


def _read(path):
    if not path.exists():
        return []
    out = []
    for ln in path.read_text().splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


# ------------------------------------------------------------------ review: live agreement decides who keeps a job
def live(name):
    """How the cell is doing on real calls since it last took its job: calls answered, audits, agreement."""
    since = spawned().get(name, {}).get("on_since", 0)
    aud = [a for a in _read(AUDIT) if a["cell"] == name and a["ts"] >= since][-200:]
    used = sum(1 for u in _read(USED) if u["cell"] == name and u["ts"] >= since)
    agree = sum(a["agree"] for a in aud) / len(aud) if aud else None
    return {"answered": used, "audits": len(aud), "agreement": round(agree, 3) if aud else None}


def review(log=print):
    """Retire every working cell whose agreement with its member on audited live calls fell under RETIRE."""
    out = {}
    for name, sp in spawned().items():
        if sp.get("status") != "on":
            continue
        lv = live(name)
        out[name] = lv
        if lv["audits"] >= AUDIT_MIN and lv["agreement"] < RETIRE:
            set_status(name, "retired", retired=time.strftime("%Y-%m-%d"),
                       retired_why=f"agreed with {sp['member']} on {lv['agreement']:.0%} of {lv['audits']} audited "
                                   f"live calls (needs {RETIRE:.0%})", rows_at_fail=sp.get("rows", 0))
            from . import use
            w = json.loads(use.WINS.read_text()) if use.WINS.exists() else {}
            if name in w:
                w[name]["use"] = False
                use.WINS.write_text(json.dumps(w, indent=1))
            log(f"[spawn] retired {name}: live agreement {lv['agreement']:.0%} over {lv['audits']} audits")
            out[name]["retired"] = True
    return out
