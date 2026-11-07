"""Coordinator: turns Arnav's one prompt into a plan of assigned steps."""
import re

from .. import config, llm, prompts

AGENTS = {"researcher", "browser", "coder", "writer"}


def plan_messages(goal, notes=""):
    user = f"Task from Arnav:\n{goal}"
    if notes:
        user += f"\n\nLessons from earlier runs:\n{notes}"
    return [{"role": "system", "content": prompts.COORDINATOR}, {"role": "user", "content": user}]


def normalize(plan, goal):
    """Make a model plan safe to execute. Returns (steps, problems)."""
    problems = []
    steps = (plan or {}).get("steps") if isinstance(plan, dict) else plan if isinstance(plan, list) else None
    if not isinstance(steps, list) or not steps:
        return None, ["no steps"]
    out, seen = [], set()
    for i, s in enumerate(steps[:config.MAX_STEPS]):
        if not isinstance(s, dict):
            problems.append(f"step {i} not an object")
            continue
        agent = str(s.get("agent", "")).lower().strip()
        if agent == "verifier":
            problems.append("dropped planned verifier step (verification is automatic)")
            continue
        if agent not in AGENTS:
            problems.append(f"unknown agent {agent!r}")
            continue
        sid = str(s.get("id") or f"s{i + 1}")
        if sid in seen or not re.fullmatch(r"[A-Za-z0-9_]+", sid):
            sid = f"s{i + 1}"
        needs = [n for n in (s.get("needs") or []) if n in seen] if isinstance(s.get("needs"), list) else []
        fe = s.get("for_each")
        if fe not in seen:
            if fe:
                problems.append(f"for_each {fe!r} is not an earlier step")
            fe = None
        task_text = str(s.get("task") or "")
        if (fe is None and agent == "browser" and needs and
                re.search(r"\b(for each|each of|every one of|each model|each item|each result)\b", task_text, re.I)):
            fe = needs[0]
            problems.append(f"{sid}: fanned out over {fe} (task says 'each')")
        task = str(s.get("task") or "").strip()
        if not task:
            problems.append(f"{sid} has no task")
            continue
        if fe and "{item}" not in task:
            task += " Item: {item}"
        if fe and fe not in needs:
            needs.append(fe)
        out.append({"id": sid, "agent": agent, "task": task, "needs": needs, "for_each": fe,
                    "done_when": str(s.get("done_when") or "").strip()})
        seen.add(sid)
    if not out:
        return None, problems or ["no usable steps"]
    if out[-1]["agent"] != "writer":
        problems.append("added final writer step")
        out.append({"id": f"s{len(out) + 1}", "agent": "writer",
                    "task": f"Write the finished answer for Arnav: {goal[:300]}",
                    "needs": [s["id"] for s in out], "for_each": None,
                    "done_when": "the report answers the task with sources"})
    return out, problems


def plan(goal, board, notes=""):
    data, raw = llm.chat_json("coordinator", plan_messages(goal, notes), max_new_tokens=900)
    steps, problems = normalize(data, goal)
    if steps is None:
        board.log("coordinator", "replan", f"plan unusable ({problems}); asking again")
        data, raw = llm.chat_json("coordinator", plan_messages(goal, notes) + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "That plan cannot run: " + "; ".join(problems) +
             ". Reply with the JSON plan only."}], max_new_tokens=900)
        steps, problems = normalize(data, goal)
    return steps, problems, raw
