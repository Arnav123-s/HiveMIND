"""The hive grows new cells from its own work.

The bigger members decide small things all day: does this quote state this claim (the verifier), does this listed
item meet the task (the juror). Every such decision is logged with its input (memory/decisions/<skill>.jsonl). When a
kind of decision has enough examples, `python -m team grow` trains a new cell on them, with the member as the teacher:
it trains on the oldest 70%, picks the edit on the next 15%, and measures on the newest 15%, decisions the cell never
saw. On dev it also finds the confidence from which the cell agrees with the member at least AGREE of the time. The
cell then answers when it is that sure; the member answers the rest, and those answers keep being logged, so the
next `grow` trains on newer work: that is how the hive adapts to new data.
Bench runs use a throwaway memory (AGENT_TEAM_HOME), so the bench never teaches the hive.
"""
import json
import time

from .. import memory
from .skills import LEARNED  # noqa: F401 - the learned skills' specs

DIR = memory.HOME / "decisions"
AGREE = 0.97  # a learned cell answers only from the confidence at which it agreed this often with the member on dev


def record(skill, text, label):
    """Log one member decision (only labels the cell could learn)."""
    if skill not in LEARNED or label not in LEARNED[skill]["labels"] or not text:
        return
    DIR.mkdir(parents=True, exist_ok=True)
    with open(DIR / f"{skill}.jsonl", "a") as f:
        f.write(json.dumps({"ts": time.time(), "x": text[:1500], "y": label}) + "\n")


def rows(skill):
    p = DIR / f"{skill}.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text().splitlines():
        try:
            d = json.loads(ln)
            out.append((d["ts"], d["x"], d["y"]))
        except (ValueError, KeyError):
            continue
    return [(x, y) for _, x, y in sorted(out)]


def rehearsed(skill):
    """Practice decisions (team/cells/spawn.py rehearse): inputs recombined from the oldest real ones, decided by the
    member. A cell trains on them; it is never judged on them."""
    p = DIR.parent / "rehearsed" / f"{skill}.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text().splitlines():
        try:
            d = json.loads(ln)
            out.append((d["x"], d["y"]))
        except (ValueError, KeyError):
            continue
    return out


def split(skill):
    """Oldest 70% train, next 15% dev, newest 15% test: a cell is judged on decisions newer than any it learned from.
    Practice decisions are added to train only."""
    r = rows(skill)
    a, b = int(len(r) * 0.7), int(len(r) * 0.85)
    real = {x for x, _ in r}
    return r[:a] + [(x, y) for x, y in rehearsed(skill) if x not in real], r[a:b], r[b:]


def register():
    """Kept for callers: the learned skills are in the cell catalogue (team/cells/skills.py LEARNED)."""


def decide(skill, text):
    """The learned cell's answer if it is switched on and sure enough; None means: ask the member (and record)."""
    from . import runtime, use
    w = use.wins().get(skill, {})
    if not (w.get("use") and runtime.available(skill)):
        return None
    register()
    p = runtime.label_probs(skill, text)
    lab, conf = max(p.items(), key=lambda kv: kv[1])
    return lab if conf >= w.get("threshold", 1.01) else None


def decide_all(skill, texts):
    """The learned cell's answers for many inputs at once on the cell pool: a label where it is sure, None where the
    member must decide. None for every input when the cell is not switched on."""
    from . import pool, runtime, use
    w = use.wins().get(skill, {})
    if not (w.get("use") and runtime.available(skill)) or not texts:
        return [None] * len(texts)
    t = w.get("threshold", 1.01)
    out = []
    for p in pool.map(skill, texts, probs=True):
        lab, conf = max(p.items(), key=lambda kv: kv[1])
        out.append(lab if conf >= t else None)
    return out
