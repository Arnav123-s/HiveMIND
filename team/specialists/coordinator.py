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
    data, raw = None, ""
    if config.SMALL:  # the planner's small specialists, taught by the 4B, plan together (team/school.py)
        from .. import school
        raw = school.answer("coordinator", plan_messages(goal, notes), goal) or ""
        data = llm.parse_json(raw) if raw else None
    if data is None:
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
    """Arnav's task as a checklist of everything he ordered. Material he hands over (after "Summarise this:", a quoted
    sentence, code) is what an instruction works on, not instructions of its own."""
    from ..cells import use
    from ..guard import split_material
    order, material = split_material(goal)
    items = _split(order, board) if use.on("split_orders") else []
    if items:
        if material:
            items[0] = f"{items[0]}: {material}" if len(material) <= 150 else f"{items[0]} (the text he gave)"
        return items[:15]
    goal = order if material else goal
    data, _ = llm.chat_json("plan_reviewer", [{"role": "system", "content": prompts.INSTRUCTIONS},
                                              {"role": "user", "content": goal}], max_new_tokens=400)
    items = (data or {}).get("instructions", []) if isinstance(data, dict) else []
    return [str(i)[:200] for i in items if str(i).strip() and grounded(str(i), goal)][:15]


def _split(goal, board=None):
    from ..cells import use
    lines = [ln.strip("-• ").strip() for ln in use.ask("split_orders", goal, board).split("\n")]
    items = []
    for ln in lines:  # the cell may respell names ("Smol LM2"): keep Arnav's own words for each line
        got = _snap(ln, goal) if ln else None
        if got and items and len(got.split()) == 1:
            # a name alone is no instruction of its own: "Plot the counts of A and B as a bar chart" was cut into
            # "Plot the counts of A" and "B", and the critic then had nothing to check "B" against. It joins the
            # instruction before it, in Arnav's own words.
            items[-1] = _join(items[-1], got, goal)
            continue
        if got and grounded(got, goal) and not any(got.lower() in i.lower() for i in items):
            # a part of a line already listed is no instruction of its own ("List the three newest", from a
            # line the cell cut short)
            items = [i for i in items if i.lower() not in got.lower()] + [got]
    for sent in re.split(r"(?<=[.!?])\s+", goal.strip()):  # nothing skipped: an uncovered sentence goes in as written
        sent = sent.strip().rstrip(".")
        if sent and not _covered(sent, items):
            items.append(sent)
            continue
        # and an uncovered clause: half of "List the three newest papers ..., with their titles and dates" was
        # covered, so "with their titles and dates" was lost
        for clause in re.split(r",\s*|;\s*", sent)[1:]:
            clause = clause.strip()
            if len(re.findall(r"[a-z0-9]{3,}", clause.lower())) >= 2 and not _covered(clause, items):
                items.append(clause)
    return items


def _join(item, frag, goal):
    """An instruction and a fragment cut from it, as one span of Arnav's words (else both with "and")."""
    a = goal.find(item)
    b = goal.find(frag, a + len(item)) if a >= 0 else -1
    if a >= 0 and b >= 0 and b - (a + len(item)) <= 40:
        return goal[a:b + len(frag)].strip(" ,;.")
    return f"{item} and {frag}"


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


def ensure_data_steps(goal, steps):
    """Data he hands over is computed on, not researched: a researcher step in a task that gives its own numbers
    ("Monthly sales: Jan 120, Feb 95, ...") becomes a calculator step. (A plan sent two researchers to search the web
    for 'average sales per month calculation method'; the writer then guessed 115.5 for an average of 117.)"""
    from ..guard import DATA_RUN, split_material
    order, material = split_material(goal)
    if not (material and DATA_RUN.match(material)) or any(s["agent"] == "browser" for s in steps):
        return steps, []
    makes = bool(FILE_ORDER.search(goal) or MAKE_ORDER.search(goal))  # a file or program he ordered keeps its coder
    fixed, notes = [], []
    for st in steps:
        if st["agent"] == "researcher" or (st["agent"] == "coder" and not makes):
            notes.append(f"{st['id']}: {st['agent']} -> calculator (the data is in his task)")
            st = dict(st, agent="calculator", task=f"Compute from the data Arnav gave ({material[:300]}): {st['task']}")
        fixed.append(st)
    return fixed, notes


# the triage cell's kinds: one specialist then the writer; "plan" (several kinds, or unsure) goes to the coordinator
TEMPLATES = {
    "write": [],
    "calc": [("calculator", "Compute exactly what Arnav asked: {goal}", "the numbers he asked for are printed")],
    "lookup": [("researcher", "Find, with quotes from sources, what Arnav asked: {goal}", "facts with quotes answer it")],
    "site": [("browser", "{goal}", "the page shows what he asked for")],
    "code": [("coder", "{goal}", "the program ran and did what he asked")],
}
TRIAGE_MIN = 0.9  # below this the cell is unsure, and the coordinator plans
SECOND_MIN = 0.6  # each cell alone needs 0.9; two that agree need 0.5 and 0.6: they rarely err the same way
SECOND = {"code": "coder", "lookup": "researcher", "site": "browser"}  # the specialist that confirms a task kind


def triage(goal, board):
    """The task_kind cell names the cheapest way through the hive; a template plan for one-kind tasks skips the 4B
    coordinator and plan reviewer. Returns steps, or None (the coordinator plans)."""
    from ..cells import runtime, use
    from ..guard import DATA_RUN, split_material
    from .research_hive import broad
    _, material = split_material(goal)
    if material and DATA_RUN.match(material) and not (FILE_ORDER.search(goal) or MAKE_ORDER.search(goal)):
        # data he hands over is computed on: the cell was unsure ("plan" 0.62) for "Monthly rainfall in mm: Jan 80,
        # ...", and the coordinator sent researchers to search the web for it and a coder to an invented URL
        board.log("coordinator", "triage", "his own data with a question: the calculator computes it")
        return _template("calc", goal)
    if broad(goal):
        # a research question goes to the research hive, which splits it into sub-questions and runs experiments
        # with the coder when one needs it; planned by the coordinator, the battery question got a browser, a coder
        # and a calculator step each "if needed", padding with nothing to do
        if FILE_ORDER.search(goal) or MAKE_ORDER.search(goal):
            board.log("coordinator", "triage", "a research question that also orders a file or a program: "
                                               "the coordinator plans")
            return None
        board.log("coordinator", "triage", "a research question: the research hive takes it")
        return _template("lookup", goal)
    if not use.on("task_kind"):
        return None
    p = runtime.label_probs("task_kind", goal[:600])
    kind, conf = max(p.items(), key=lambda kv: kv[1])
    board.log("cell:task_kind", "answer", f"{kind} ({conf:.2f})")
    # per kind, chosen on dev by training/cells_triage_threshold.py (a wrong 'write' skips research and calculation)
    need = use.wins().get("task_kind", {}).get("thresholds", {}).get(kind, TRIAGE_MIN)
    if kind not in TEMPLATES:
        return None
    if conf < max(TRIAGE_MIN, need):
        # an unsure cell asks a second one: the routing cell reads the same task and names a specialist. Two cells
        # trained on different data that agree are taken at their word; alone, neither is. (With the 1.7B as
        # coordinator, "write a function ... and tell me fib(30)" (code, 0.58) was planned as research.)
        second = SECOND.get(kind)
        if not (second and conf >= 0.5 and use.on("route_step")):
            return None
        q = runtime.label_probs("route_step", goal[:300])
        who, sure = max(q.items(), key=lambda kv: kv[1])
        board.log("cell:route_step", "answer", f"second opinion on the whole task: {who} ({sure:.2f})")
        if who != second or sure < SECOND_MIN:
            return None
        board.log("coordinator", "triage", f"task_kind ({kind}) and route_step ({who}) agree")
    return _template(kind, goal)


def _template(kind, goal):
    steps = [{"id": f"s{i + 1}", "agent": a, "task": t.format(goal=goal), "needs": [], "for_each": None, "done_when": d}
             for i, (a, t, d) in enumerate(TEMPLATES[kind])]
    steps.append({"id": f"s{len(steps) + 1}", "agent": "writer", "task": f"Write the finished answer for Arnav: {goal}",
                  "needs": [s["id"] for s in steps], "for_each": None, "done_when": "the answer does what he asked"})
    return steps


# (the cell said "code" (0.92) for "Research how lithium-ion batteries degrade over time ...": a research question is
# decided in code before the cell is asked)
MAKE_ORDER = re.compile(r"\b(?:write|build|make|create|give me) (?:me )?(?:a |an )?(?:python |small |simple )?"
                        r"(?:program|script|function|app|tool|class|module|chart|plot|graph|spreadsheet|table file)\b|"
                        r"\b(?:chart|charts|plot|plots|graph|graphs|visuali[sz]e|diagram|histogram)\b", re.I)
PADDING = re.compile(r"\b(?:if (?:needed|necessary|required|applicable|relevant)|as needed|where needed)\b", re.I)


def drop_padding(steps):
    """Steps the coordinator adds "if needed" are not his orders: dropped (with their ids taken out of later needs),
    as long as another step still does the work."""
    pad = {s["id"] for s in steps if s["agent"] != "writer" and PADDING.search(s.get("task", ""))}
    if not pad or all(s["id"] in pad or s["agent"] == "writer" for s in steps):
        return steps, []
    kept = [dict(s, needs=[n for n in s.get("needs", []) if n not in pad]) for s in steps if s["id"] not in pad]
    return kept, [f"dropped {sorted(pad)}: steps added 'if needed' are not his orders"]


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
        steps, padded = drop_padding(steps)
        if padded:
            board.log("plan_reviewer", "drop", padded[0])
        steps, added = ensure_file_step(goal, steps)
        steps, swapped = ensure_data_steps(goal, steps)
        problems = problems + padded + added + swapped
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


PROSE = re.compile(r"\b(explain\w*|describ\w*|summari[sz]\w*|defin\w*|tell\w*|what (?:is|are)|write about)\b", re.I)
COMPUTE = re.compile(r"\b(program|code|script|function|python|compute|calculat\w*|measur\w*|benchmark\w*|simulat\w*|"
                     r"experiment\w*|plot|chart|graph|csv|json|file|api|download|scrape|average|sum|percent\w*|\d)\b", re.I)


def reroute(goal, step, reason):
    """A different specialist for a step that failed every attempt (the hive routes around failure)."""
    data, _ = llm.chat_json("coordinator", [{"role": "system", "content": prompts.REROUTE},
                                            {"role": "user", "content": f"Arnav's task: {goal}\nFailed step ({step['agent']}): "
                                             f"{step['task']}\nWhy it failed: {reason}"}], max_new_tokens=250)
    if not isinstance(data, dict) or data.get("agent") not in AGENTS - {"writer", step["agent"]} or not data.get("task"):
        return None
    if data["agent"] in ("coder", "calculator") and PROSE.search(str(data["task"])) and not COMPUTE.search(goal):
        # a program cannot explain: "Write a Python program that explains what a hash table is" made invalid Python
        return None
    return {"id": step["id"] + "r", "agent": data["agent"], "task": str(data["task"]), "needs": step["needs"],
            "for_each": None, "done_when": str(data.get("done_when") or step.get("done_when", ""))}
