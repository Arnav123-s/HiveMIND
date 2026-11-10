"""Where the hive hands a job to a cell instead of a bigger member or a code rule.

A cell takes a job only if it scored at least as well as what it replaces on the same test inputs
(cells/wins.json, written by training/cells_compare.py). AGENT_TEAM_CELLS=0 turns every cell off.
"""
import json
import os

from . import runtime

WINS = runtime.CELLS / "wins.json"
_cache = {}


def wins():
    if WINS.exists():
        m = WINS.stat().st_mtime
        if _cache.get("m") != m:
            _cache.update(m=m, w=json.loads(WINS.read_text()))
        return _cache["w"]
    return {}


def on(skill):
    if os.environ.get("AGENT_TEAM_CELLS", "1") == "0":
        return False
    return bool(wins().get(skill, {}).get("use")) and runtime.available(skill)


def ask(skill, text, board=None):
    out = runtime.run(skill, text)
    if board is not None:
        board.log(f"cell:{skill}", "answer", f"{text[:90]!r} -> {out[:80]!r}")
    return out


def ask_all(skill, texts, board=None):
    """The cell's answer for many inputs at once, spread over the cell pool (team/cells/pool.py)."""
    from . import pool
    texts = list(texts)
    out = pool.map(skill, texts) if texts else []
    if board is not None and texts:
        board.log(f"cell:{skill}", "answer", f"{len(texts)} at once -> " + ", ".join(f"{o}" for o in out[:12])[:160])
    return out


def orders(text, board=None):
    """The order organizer: one yes/no cell per risky kind; the kinds whose cell says yes."""
    got = {k for k in ("spend", "delete", "send", "login", "signup") if ask(f"orders_{k}", text, None) == "yes"}
    if board is not None:
        board.log("cell:orders", "answer", f"{text[:90]!r} -> {sorted(got)}")
    return got


def orders_on():
    return all(on(f"orders_{k}") for k in ("spend", "delete", "send", "login", "signup"))
