"""Coordinator: turns Arnav's one prompt into a plan of assigned steps."""
import re
import time

from .. import config, llm, prompts

AGENTS = {"researcher", "browser", "coder", "calculator", "writer"}


def plan_messages(goal, notes=""):
    user = f"Today is {time.strftime('%Y-%m-%d (%A)')}.\nTask from Arnav:\n{goal}"
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
            from ..cells import use
            if use.on("route_step") and str(s.get("task", "")).strip():  # the routing cell rescues the step
                new = use.ask("route_step", str(s["task"])[:300])
                problems.append(f"unknown agent {agent!r}: route_step cell gave it to {new}")
                agent = new
            else:
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


def instructions(goal, board=None):
    """Arnav's task as a checklist of everything he ordered."""
    from ..cells import use
    if use.on("split_orders"):  # one small cell, trained only to split an order into its instructions
        lines = [ln.strip("-• ").strip() for ln in use.ask("split_orders", goal, board).split("\n")]
        items = []
        for ln in lines:  # the cell may respell names ("Smol LM2"): keep Arnav's own words for each line
            got = _snap(ln, goal) if ln else None
            if got and got not in items and grounded(got, goal):
                items.append(got)
        for sent in re.split(r"(?<=[.!?])\s+", goal.strip()):  # nothing skipped: an uncovered sentence goes in as written
            sent = sent.strip().rstrip(".")
            if sent and not _covered(sent, items):
                items.append(sent)
        if items:
            return items[:15]
    data, _ = llm.chat_json("plan_reviewer", [{"role": "system", "content": prompts.INSTRUCTIONS},
                                              {"role": "user", "content": goal}], max_new_tokens=400)
    items = (data or {}).get("instructions", []) if isinstance(data, dict) else []
    return [str(i)[:200] for i in items if str(i).strip() and grounded(str(i), goal)][:15]


def _snap(line, goal):
    """The span of Arnav's own words closest to a line (compared without spaces or case); None if nothing is close."""
    import difflib
    key = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())  # noqa: E731
    target = key(line)
    if not target:
        return None
    toks = list(re.finditer(r"\S+", goal))
    best, best_r = None, 0.0
    for i in range(len(toks)):
        for j in range(i + 1, min(len(toks), i + len(line.split()) + 4) + 1):
            span = goal[toks[i].start():toks[j - 1].end()]
            r = difflib.SequenceMatcher(None, target, key(span)).ratio()
            if r > best_r:
                best, best_r = span, r
    return best.strip(" ,;.") if best is not None and best_r >= 0.75 else None


_KEEP = set("the and for with from that this then also".split())


def _covered(sent, items):
    """Half of a sentence's words (negations included) already appear in the checklist."""
    words = set(re.findall(r"[a-z0-9]{3,}", sent.lower())) - _KEEP
    have = set(re.findall(r"[a-z0-9]{3,}", " ".join(items).lower()))
    return not words or len(words & have) / len(words) >= 0.5


_STOP = set("the a an and or of to in on for with from by is are was be it this that what which who how find get give "
            "me my make write tell list show please about into at as do not any all each its it's your you i".split())


def grounded(item, goal):
    """An instruction must come from Arnav's own words: most of its content words appear in his task."""
    words = [w for w in re.findall(r"[a-z0-9£$.\-]{3,}", item.lower()) if w not in _STOP]
    if not words:
        return False
    g = goal.lower()
    return sum(w.strip(".") in g for w in words) / len(words) >= 0.5


FILE_ORDER = re.compile(r"\b(csv|spreadsheet|xlsx|excel file|json file|png|histogram|plot|(?:a|bar|line|pie) (?:chart|graph)|"
                        r"(?:chart|graph) of|save (?:it|them|the \w+) (?:to|as|in)|make a file)\b", re.I)


def file_problems(goal, steps):
    """Checked in code: a file or chart Arnav ordered needs a step that can make one (only the coder writes files)."""
    m = FILE_ORDER.search(goal)
    if m and not any(s["agent"] == "coder" for s in steps):
        return [f"Arnav asked for a file or chart ('{m.group(0)}'), and no coder step makes it"]
    return []


def ensure_file_step(goal, steps):
    """The file check, enforced: if Arnav ordered a file and the final plan has no coder, one makes it before the
    writer (a re-plan can drop the coder the first plan had: seen on "save them to a CSV")."""
    probs = file_problems(goal, steps)
    if not probs:
        return steps, []
    ids = {s["id"] for s in steps}
    sid = next(f"s{i}" for i in range(len(steps) + 1, 99) if f"s{i}" not in ids)
    w = steps[-1]
    step = {"id": sid, "agent": "coder", "task": f"Make the file Arnav asked for, from the results so far: {goal[:300]}",
            "needs": [s["id"] for s in steps[:-1]], "for_each": None,
            "done_when": f"the file is saved and holds exactly what he asked for: {goal[:200]}"}
    w = dict(w, needs=list(dict.fromkeys(w["needs"] + [sid])))
    return steps[:-1] + [step, w], [f"added {sid} (coder): {probs[0]}"]


# the triage cell's kinds: one specialist then the writer; "plan" (several kinds, or unsure) goes to the coordinator
TEMPLATES = {
    "write": [],
    "calc": [("calculator", "Compute exactly what Arnav asked: {goal}", "the numbers he asked for are printed")],
    "lookup": [("researcher", "Find, with quotes from sources, what Arnav asked: {goal}", "facts with quotes answer it")],
    "site": [("browser", "{goal}", "the page shows what he asked for")],
    "code": [("coder", "{goal}", "the program ran and did what he asked")],
}
TRIAGE_MIN = 0.9  # below this the cell is unsure, and the coordinator plans


def triage(goal, board):
    """The task_kind cell names the cheapest way through the hive; a template plan for one-kind tasks skips the 4B
    coordinator and plan reviewer. Returns steps, or None (the coordinator plans)."""
    from ..cells import runtime, use
    if not use.on("task_kind"):
        return None
    p = runtime.label_probs("task_kind", goal[:600])
    kind, conf = max(p.items(), key=lambda kv: kv[1])
    board.log("cell:task_kind", "answer", f"{kind} ({conf:.2f})")
    if kind not in TEMPLATES or conf < TRIAGE_MIN:
        return None
    steps = [{"id": f"s{i + 1}", "agent": a, "task": t.format(goal=goal), "needs": [], "for_each": None, "done_when": d}
             for i, (a, t, d) in enumerate(TEMPLATES[kind])]
    steps.append({"id": f"s{len(steps) + 1}", "agent": "writer", "task": f"Write the finished answer for Arnav: {goal}",
                  "needs": [s["id"] for s in steps], "for_each": None, "done_when": "the answer does what he asked"})
    return steps


def reviewed_plan(goal, board, notes="", checklist=()):
    """Plan -> plan reviewer and code checks -> one re-plan if they found problems -> code checks enforced.
    Returns (steps, problems, raw)."""
    steps, problems, raw = plan(goal, board, notes)
    if steps:
        found = review(goal, steps, checklist)
        if found:
            board.log("plan_reviewer", "problems", " | ".join(found))
            notes2 = (notes + "\n" if notes else "") + "A reviewer found these problems in your first plan; fix them:\n" \
                + "\n".join(f"- {r}" for r in found)
            steps2, problems2, raw2 = plan(goal, board, notes2.strip())
            if steps2:
                steps, problems, raw = steps2, problems2, raw2
        else:
            board.log("plan_reviewer", "ok", "plan covers the task")
        steps, added = ensure_file_step(goal, steps)
        problems = problems + added
    return steps, problems, raw


def review(goal, steps, checklist=()):
    """The plan reviewer's problems with a plan ([] if none), plus the checks done in code."""
    import json
    fixed = file_problems(goal, steps)
    plan = json.dumps({"steps": [{k: s[k] for k in ("id", "agent", "task", "needs", "for_each")} for s in steps]})
    todo = "\n".join(f"- {i}" for i in checklist)
    data, _ = llm.chat_json("plan_reviewer", [{"role": "system", "content": prompts.PLAN_REVIEWER},
                                              {"role": "user", "content": f"TASK: {goal}\n\nINSTRUCTIONS:\n{todo}\n\nPLAN: {plan}"}],
                            max_new_tokens=250)
    if not isinstance(data, dict) or data.get("ok", True) is True:
        return fixed
    return fixed + [str(x)[:200] for x in data.get("problems", [])][:5]


def reroute(goal, step, reason):
    """A different specialist for a step that failed every attempt (the hive routes around failure)."""
    data, _ = llm.chat_json("coordinator", [{"role": "system", "content": prompts.REROUTE},
                                            {"role": "user", "content": f"Arnav's task: {goal}\nFailed step ({step['agent']}): "
                                             f"{step['task']}\nWhy it failed: {reason}"}], max_new_tokens=250)
    if not isinstance(data, dict) or data.get("agent") not in AGENTS - {"writer", step["agent"]} or not data.get("task"):
        return None
    return {"id": step["id"] + "r", "agent": data["agent"], "task": str(data["task"]), "needs": step["needs"],
            "for_each": None, "done_when": str(data.get("done_when") or step.get("done_when", ""))}
