"""Long-term memory shared by the whole team.

- lessons.jsonl : short rules learned from verified failures (written while dreaming)
- runs.jsonl    : one line per finished task (what was asked, how it went, where the report is)
- profile.md    : how Arnav likes things done (he edits it, or tells the chat "remember ...")
- policy.json   : standing approvals for spend / delete / send (ask | allow | deny)

Lives in agent-team/memory/ unless AGENT_TEAM_HOME is set.
"""
import json
import os
import re
import time
from pathlib import Path

from . import config

HOME = Path(os.environ.get("AGENT_TEAM_HOME", config.ROOT / "memory"))
HOME.mkdir(parents=True, exist_ok=True)
LESSONS = HOME / "lessons.jsonl"
RUNS = HOME / "runs.jsonl"
PROFILE = HOME / "profile.md"
POLICY = HOME / "policy.json"
DREAMS = HOME / "dreams.jsonl"

STOP = set("the a an and or of to in on for with from by is are was be it this that what which who how find get "
           "give me my make write tell list show please about into at as".split())


def words(text):
    return {w for w in re.findall(r"[a-z0-9][a-z0-9.\-]{2,}", (text or "").lower()) if w not in STOP}


def _read(path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def _append(path, row):
    with open(path, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------- lessons
def add_lesson(agent, lesson, about, source=""):
    for x in _read(LESSONS):
        if x["lesson"] == lesson:
            return
    _append(LESSONS, {"ts": time.strftime("%F %T"), "agent": agent, "lesson": lesson,
                      "keys": sorted(words(about))[:30], "source": source})


def lessons_for(agent, task, k=3):
    tw = words(task)
    scored = []
    for x in _read(LESSONS):
        if x["agent"] not in (agent, "all"):
            continue
        overlap = len(tw & set(x["keys"]))
        if overlap:
            scored.append((overlap, x["lesson"]))
    scored.sort(reverse=True)
    return [s for _, s in scored[:k]]


# ---------------- runs (episodic memory)
def add_run(goal, run_dir, verdicts, report_head):
    _append(RUNS, {"ts": time.strftime("%F %T"), "goal": goal, "dir": str(run_dir), "verdicts": verdicts,
                   "report": report_head[:600]})


def recall(query, k=3):
    qw = words(query)
    rows = [(len(qw & words(r["goal"] + " " + r["report"])), r) for r in _read(RUNS)]
    return [r for s, r in sorted(rows, key=lambda x: -x[0]) if s][:k]


def runs():
    return _read(RUNS)


# ---------------- profile & policy
def profile():
    return PROFILE.read_text().strip() if PROFILE.exists() else ""


def remember(fact):
    with open(PROFILE, "a") as f:
        f.write(f"- {fact.strip()}\n")


def policy():
    base = {"spend": "ask", "delete": "ask", "send": "ask"}
    if POLICY.exists():
        base.update(json.loads(POLICY.read_text()))
    return base


def log_dream(row):
    _append(DREAMS, {"ts": time.strftime("%F %T"), **row})
