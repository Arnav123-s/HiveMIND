"""The hive is one body: one ternary model (its DNA) and many cells, each the DNA with a small weight edit of its own.

    practice  ->  rows  ->  every cell regrown from the rows  ->  gate  ->  the body's next generation

practice   Fresh tasks that are never an exam's (seeds from ten million up; the exam's held-out kinds are never
           practised). The body's own cells do them as they do any task (team/solo.py). Each cell's own answer is
           put to the task's own check, computed by code (training/exam.each_member).
rows       From each cell whose own answer the check confirms, agreed with or not: the task -> its final program, the
           program's output -> DONE, and, where it first failed, the failure -> the mended program. Nobody labelled
           anything: the label is that the program ran and its answer was checked.
train      Every cell is grown again from the same DNA (Ternary-Bonsai-1.7B, 0.43 GB packed, the smallest ternary
           model whose full weights are published) on all the rows, as a low-rank weight edit (LoRA) on a CPU. A
           cell leans to one organ (team/ternary.ORGANS): it meets that organ's rows three times as often. So the
           cells are the same size, overlap, and each is strongest somewhere. A cell is a file of a few megabytes
           (cells/members/<dna>+<name>.gguf); the DNA is in memory once for all of them.
gate       The same fresh exam sat by the DNA as published, by the body as it was and by the body as regrown; the
           body changes only when the numbers say so (.github/workflows/grow.yml, training/grow_record.py).

    python training/grow.py practice --seed 10000001 --tasks 16 [--level mixed|hard|basic] [--out runs/grow/rows.jsonl]
    python training/grow.py rows RUN_FOLDER ... [--out rows.jsonl]      rows from sittings already done (checked tasks only)
    python training/grow.py train --rows rows.jsonl --name g3code --lean code [--epochs 2] [--minutes 240] [--ternary] [--foresee]
    python training/grow.py fetch                                        the cells of the body, from the release
"""
import contextlib
import json
import math
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GROW = ROOT / "runs" / "grow"
UNPACKED = {"t17": "prism-ml/Ternary-Bonsai-1.7B-unpacked", "t40": "prism-ml/Ternary-Bonsai-4B-unpacked", "t80": "prism-ml/Ternary-Bonsai-8B-unpacked"}  # members whose full weights are published, so they can be taught
READ_LEN = int(os.environ.get("HIVE_READ_LEN", 256))  # the most pieces of one raw text read in training (train --read)
RELEASE = "hive-grown"  # the GitHub release that holds the rows and the weight edits (never in git: they are big and machine-made)


# ---- rows ------------------------------------------------------------------------------------------------------------
def _home(run):
    """The folder of a task's members' own files (member{n}.json, members.json): run/members, or run itself."""
    return Path(run) / "members" if (Path(run) / "members").is_dir() else Path(run)


def _number(f):
    """The member's number in its file's name: member3.json -> 3."""
    return int(re.sub(r"\D", "", Path(f).stem))


def checked(run, home=None):
    """{member number: ok}: each member's own answer put to the task's own check (exam.json "members", written by
    training/exam.each_member), tied to its member{n}.json by number. None when the task has no such verdicts.
    A verdict written before each was tied to its file (generation 28 and earlier: {"who", "ok"} only) is tied by
    the member's name, and only where exactly one file and one verdict carry that name: never by order, since the
    order the verdicts were written in is not the order of the numbers (member10.json sorts before member2.json)."""
    home = Path(home) if home else _home(run)
    try:
        verdicts = json.loads((Path(run) / "exam.json").read_text()).get("members")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(verdicts, list):
        return None
    files = {}
    for f in home.glob("member[0-9]*.json"):
        try:
            t = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        files[_number(f)] = str(t.get("who") or "")[:80] if isinstance(t, dict) else ""
    named = [v.get("who") for v in verdicts if isinstance(v, dict) and not isinstance(v.get("member"), int)]
    out = {}
    for v in verdicts:
        if not isinstance(v, dict):
            continue
        n = v.get("member")
        if not isinstance(n, int) or isinstance(n, bool):
            who = v.get("who")
            mine = [k for k, w in files.items() if who and w == who]
            n = mine[0] if len(mine) == 1 and named.count(who) == 1 else None
        if n is not None:
            out[n] = out.get(n, False) or v.get("ok") is True
    return out


def taught(run, home=None):
    """The members whose programs become rows. Every member whose own answer the task's check confirms wrote a right
    program, whether or not another agreed with it: agreement is not the check. Generation 28's practice (80 of its
    100 tasks in hand): 3 failed tasks had a member the check confirmed (c10002802_02's first member was right while
    the other two disagreed), 9 right members of passed tasks were left out because two others had agreed, and one
    member taught for agreeing was refused by the check. Without per-member verdicts (a run made before exam.json
    kept them, or a task not sat as an exam: team/engram), the old rule: the members that agreed, on a task the
    check passed."""
    home = Path(home) if home else _home(run)
    said = checked(run, home)
    if said is not None:
        return sorted(n for n, ok in said.items() if ok)
    exam = Path(run) / "exam.json"
    try:
        passed = exam.exists() and json.loads(exam.read_text()).get("ok") is True
    except (OSError, ValueError, AttributeError):
        passed = False
    if exam.exists() and not passed:
        return []
    try:
        return [n for n in json.loads((home / "members.json").read_text()).get("agreeing", []) if isinstance(n, int)]
    except (OSError, ValueError, AttributeError):
        return []


def once(rows):
    """Each row once: two members that wrote the same program for the same task make the same row, and the same row
    twice is the same lesson weighed double."""
    seen, out = set(), []
    for r in rows:
        key = json.dumps([r.get("type"), r.get("messages"), r.get("output"), r.get("rejected")], sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def rows_of(run, task, kind="", seed=None):
    """The training rows of one task: from every member whose own answer the task's check confirmed (taught), whether
    or not the whole task was right. run: the task's folder."""
    from team import solo
    home = _home(run)
    try:
        agreeing = json.loads((home / "members.json").read_text()).get("agreeing", [])
    except (OSError, ValueError, AttributeError):
        agreeing = []
    out = []
    for n in taught(run, home):
        try:
            t = json.loads((home / f"member{n}.json").read_text())
        except (OSError, ValueError):
            continue
        ms, program = t.get("messages") or [], (t.get("program") or "").strip()
        if len(ms) < 3 or not program or len(program) > 6000:
            continue
        # the taught member's short orders (team/solo.SHORT) with the day the work was done, and the task
        day = re.search(r"Today is (\d{4}-\d\d-\d\d \(\w+\))", ms[0]["content"])
        head = [{"role": "system", "content": solo.SHORT.format(today=day.group(1) if day else time.strftime("%Y-%m-%d (%A)"))}, ms[1]]
        fenced = f"```python\n{program}\n```"
        # agreed: whether this member was one of those that agreed (False: a right member the old rule left out)
        base = {"task": task, "kind": kind, "seed": seed, "who": t.get("who", ""), "member": n, "agreed": n in agreeing}
        out.append(base | {"type": "first", "messages": head, "output": fenced})
        out.append(base | {"type": "done", "messages": head + [{"role": "assistant", "content": fenced},
                                                                 {"role": "user", "content": f"OUTPUT:\n{t['answer'][-1800:]}\n\n{solo.MORE}"}], "output": "DONE"})
        # where it failed first: the failing program and what it was told, then the program that was right
        for i in range(2, len(ms) - 2, 2):
            a, fb, nxt = ms[i], ms[i + 1], ms[i + 2]
            if a["role"] == "assistant" and nxt["role"] == "assistant" and solo.extract_code(nxt["content"]).strip() == program \
                    and solo.extract_code(a["content"]).strip() != program and len(a["content"]) < 5000 and len(fb["content"]) < 3000:
                out.append(base | {"type": "fix", "messages": head + [a, fb], "output": fenced})
                break
    return once(out)


def pair_rows(run, task, kind="", seed=None, most=4):
    """Rows that set a right program beside a wrong one written for the same task. The right one is that of a member
    whose own answer the check confirmed (taught); the wrong ones are the first programs of the other members that
    are none of the right programs (sent back with an error, or a different result). A member the check confirmed is
    never the rejected one: what the check passed is not taught as wrong. Trained with --pairs (Iterative Reasoning
    Preference Optimization: DPO with a likelihood term, Pang et al. 2024), the cell learns what makes a program
    wrong as well as what a right one looks like; training only on right answers tends to memorise them (Chu et al.
    2025, "SFT memorizes, RL generalizes"). Used only with --pairs, until a gate has shown it helps."""
    from team import solo
    home = _home(run)
    tries = {}
    for f in sorted(home.glob("member[0-9]*.json")):
        try:
            tries[_number(f)] = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
    right = [n for n in taught(run, home) if n in tries]
    win = next((tries[n] for n in right if (tries[n].get("program") or "").strip()), None)
    if not win or len(win.get("messages") or []) < 3 or len(win["program"]) > 6000:
        return []
    ms, program = win["messages"], win["program"].strip()
    day = re.search(r"Today is (\d{4}-\d\d-\d\d \(\w+\))", ms[0]["content"])
    head = [{"role": "system", "content": solo.SHORT.format(today=day.group(1) if day else time.strftime("%Y-%m-%d (%A)"))}, ms[1]]
    # every program a right member ended with is right: none of them is set down as the wrong one
    out, seen = [], {(tries[n].get("program") or "").strip() for n in right}
    # with the check's own verdict on each member, only members it did not confirm give wrong programs; without it (a
    # run from before the verdicts were kept), as before: any first program that was not the agreed one
    confirmed = set(right) if checked(run, home) is not None else set()
    for n, t in sorted(tries.items()):
        if n in confirmed:
            continue
        tm = t.get("messages") or []
        if len(tm) < 3 or tm[2].get("role") != "assistant":
            continue
        code = solo.extract_code(tm[2]["content"]).strip()
        if not code or code in seen or len(code) > 6000:
            continue
        seen.add(code)
        # whose wrong program it was, and what that member was shown when it ran (its output or its error): a child
        # of that cell learns the correction from exactly there (train: "mend")
        shown = tm[3]["content"].rsplit("\n\n", 1)[0][-900:] if len(tm) > 3 and tm[3].get("role") == "user" else ""
        out.append({"task": task, "kind": kind, "seed": seed, "type": "pair", "member": n, "messages": head,
                    "output": f"```python\n{program}\n```", "rejected": f"```python\n{code}\n```",
                    "rejected_who": t.get("who", ""), "shown": shown})
        if len(out) >= most:
            break
    return out


MEND = "{shown}\n\nThe task's check says that answer is not right. Reply with the whole corrected program."
FORESEE = ("Here is a program that was written for the TASK. Do not write a program: say exactly what this one prints "
           "when it is run (or the last line of its error if it fails).\n```python\n{program}\n```")


def foresee_rows(run, task, kind="", seed=None, most=4):
    """Rows of another kind, from every program any cell ran on a task, right or wrong: the program -> what it
    printed. A cell that can say what a program will print before it runs knows how programs behave; the hive has
    many times more of these rows than of solved tasks, and running the program was the only label needed.
    (The hive's own form of learning by predicting. Used in training only with --foresee, until a gate has shown
    that cells grown with them do better than cells grown without.)"""
    from team import solo
    home = Path(run) / "members" if (Path(run) / "members").exists() else Path(run)
    out, seen = [], set()
    for prog in sorted(home.rglob("member*_*.py")):
        code = prog.read_text(errors="ignore").strip()
        printed = (prog.parent / f".{prog.name}.out")
        err = (prog.parent / f".{prog.name}.err")
        said = printed.read_text(errors="ignore").strip() if printed.exists() else ""
        if not said and err.exists() and err.read_text(errors="ignore").strip():
            said = err.read_text(errors="ignore").strip().splitlines()[-1]
        if not code or not said or len(code) > 3000 or len(said) > 500 or code in seen or re.search(r"look\(|requests|urllib|http|datetime\.(?:now|today)|date\.today|random", code):  # only what the program alone decides
            continue
        seen.add(code)
        out.append({"task": task, "kind": kind, "seed": seed, "type": "foresee", "output": said,
                    "messages": [{"role": "system", "content": solo.SHORT.format(today=time.strftime("%Y-%m-%d (%A)"))},
                                 {"role": "user", "content": f"TASK: {task}\n\n" + FORESEE.format(program=code)}]})
        if len(out) >= most:
            break
    return out


def _dna():
    """The DNA of the body on this machine (cells/body.json), t80 when it says none."""
    from team import ternary
    try:
        return json.loads(ternary.BODY.read_text()).get("dna") or "t80"
    except (OSError, ValueError, AttributeError):
        return "t80"


def edge_weights(dna="t17", last=3, record=None, body=None):
    """{kind: weight} for practice at the edge: the more a kind sits near half passed, the more it is practised.
    A kind always passed is learned; one never passed gives no right program to learn from and no right-against-
    wrong pair yet. p is the body's pass rate on the kind over the last `last` gates of this DNA (with one pass and
    one failure added, so a kind seen twice is not taken as settled), and the weight is p(1 - p), the most at
    one half. As the body gets better, easy kinds drop out of practice and harder ones come in by themselves.

    Where the body's own practice has been counted kind by kind (cells/body.json "kinds", grow_record.practice_kinds),
    the weight is s(1 - f) instead: s how often some member is right on the kind, f how often the body is. It is high
    exactly where practice makes a new right row. p(1 - p) gave a kind passed 2 of 2 and one passed 0 of 2 the same
    weight, so half the practice went to kinds already learned (agent C, 2026-11-16): each kind is passed either always
    or never, and only a never-passed kind that some member gets right sometimes can move."""
    try:
        b = json.loads(Path(body).read_text()) if body else json.loads((ROOT / "cells" / "body.json").read_text())
    except (OSError, ValueError):
        b = {}
    counts = b.get("kinds") if isinstance(b, dict) and b.get("dna") == dna and isinstance(b.get("kinds"), dict) else {}
    if counts:
        out = {}
        for k, c in counts.items():
            if isinstance(c, list) and len(c) == 3 and all(isinstance(x, (int, float)) for x in c):
                tries, right, some = c
                out[k] = ((some + 1) / (tries + 2)) * (1 - (right + 1) / (tries + 2))
        if out:
            return out
    rec = Path(record or ROOT / "training" / "reports" / "generations.jsonl")
    lines = []
    for ln in (rec.read_text().splitlines() if rec.exists() else []):
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("dna", "t17") == dna and d.get("arms", {}).get("after", {}).get("kinds"):
            lines.append(d)
    seen = {}
    for d in lines[-last:]:
        for k, (p, n) in d["arms"]["after"]["kinds"].items():
            a = seen.setdefault(k, [0, 0])
            a[0], a[1] = a[0] + p, a[1] + n
    return {k: ((p + 1) / (n + 2)) * (1 - (p + 1) / (n + 2)) for k, (p, n) in seen.items()}


def practice(seed, n=16, level="mixed", out=None, log=print, minutes=0):
    """Fresh practice tasks done by the hive's members; the rows of those the check confirmed are appended to out.
    minutes: no new task is begun after so long (a runner's job that runs out of time keeps nothing; what is done
    by then is written task by task)."""
    born = time.time()
    from training import exam as E
    from training import exam_hard
    out = Path(out or GROW / "rows.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("AGENT_TEAM_SOLO", "2")
    os.environ.setdefault("AGENT_TEAM_SOLO_ALONE", "1")
    home = E._memory(True)
    made = right = 0
    # where to practise most: the kinds the body's own exams show at its edge (edge and ladder alike; the ladder sets
    # how hard each is). The weights of the body's own DNA: those of another DNA say nothing about this one.
    weights = edge_weights(_dna()) if level in ("edge", "ladder") else None
    if weights:
        log("practice at the edge: " + ", ".join(f"{k} {w:.2f}" for k, w in sorted(weights.items(), key=lambda x: -x[1])), flush=True)
    levels = body_levels() if level == "ladder" else None
    if levels:
        log("how hard the lessons are now: " + ", ".join(f"{k} {v}" for k, v in sorted(levels.items())), flush=True)
    passed = []
    for tid, field, kind, task, check in E.exam(seed, n, (), level, without=exam_hard.HELD_OUT, weights=weights, levels=levels):
        if minutes and time.time() - born > minutes * 60:
            log(f"time is up after {len(passed)} of {n} tasks: practice ends here", flush=True)
            break
        r = E.sit_one(f"practice_{seed}", tid, task, check, home, kind=kind)
        # rows from every member the task's check confirmed, even where the hive's answer was not right (taught)
        new = rows_of(E.RUNS / f"practice_{seed}" / tid, task, kind, seed)
        new += pair_rows(E.RUNS / f"practice_{seed}" / tid, task, kind, seed)
        if os.environ.get("HIVE_FORESEE") == "1":
            new += foresee_rows(E.RUNS / f"practice_{seed}" / tid, task, kind, seed)
        with open(out, "a") as f:
            for row in new:
                f.write(json.dumps(row) + "\n")
        made, right = made + sum(x["type"] not in ("foresee", "pair") for x in new), right + r["ok"]
        if not r["ok"]:
            remember_failure(E.RUNS / f"practice_{seed}" / tid, task, kind, check, r, out.with_name("failures.jsonl"))
        # and, kind by kind, whether the body was right and whether some member was (training/grow_record.practice_kinds):
        # practice is drawn where some member is right and the body is not, the only place it makes a new right row
        some = any(isinstance(m, dict) and m.get("ok") is True for m in r.get("members") or [])
        passed.append({"maker": getattr(check, "maker", ""), "level": getattr(check, "level", 0), "ok": bool(r["ok"]), "kind": kind, "some": some})
        # what was passed at which level, for the record to move the levels by (training/grow_record.levels)
        out.with_name("practice.json").write_text(json.dumps({"seed": seed, "tasks": passed}))
        beyond = sum(x["type"] == "first" and x.get("agreed") is False for x in new)
        log(f"{'RIGHT' if r['ok'] else 'not right'} {tid} [{kind}] {r['seconds']}s, {len(new)} rows"
            + (f", {beyond} of the right members not among those that agreed" if beyond else ""), flush=True)
    return {"practice": seed, "level": level, "tasks": len(passed), "right": right, "rows": made, "file": str(out)}


def body_levels():
    """{maker: level, "compound": parts}: how hard the body's lessons are now (cells/body.json, moved by each
    generation's record)."""
    from team import ternary
    try:
        lv = json.loads(ternary.BODY.read_text()).get("levels") or {}
        return {str(k): int(v) for k, v in lv.items() if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 9}
    except (OSError, ValueError, AttributeError):
        return {}


def _masked(why):
    """What the check said, with its numbers hidden: the hive is to find its mistake, not copy the answer."""
    return re.sub(r"\d+(?:[.,]\d+)*", "#", why or "")[:400]


def remember_failure(run, task, kind, check, result, path):
    """A task the hive got wrong, kept so that it can come back to it (dream): how to make the task again, its own
    last program and what that printed, and what the check said, numbers hidden."""
    if not getattr(check, "maker", None):
        return
    home = Path(run) / "members"
    program, printed, who = "", "", []
    for f in sorted(home.glob("member[0-9]*.json")):
        try:
            t = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        who.append(str(t.get("who", ""))[:80])
        if program:
            continue
        ms = [m for m in t.get("messages") or [] if m.get("role") == "assistant"]
        program = (t.get("program") or (solo_code(ms[-1]["content"]) if ms else "")).strip()
        printed = (t.get("answer") or "")[-600:]
    if not program or len(program) > 5000:
        return
    with open(path, "a") as f:
        f.write(json.dumps({"maker": check.maker, "rseed": check.rseed, "level": getattr(check, "level", 0), "parts": getattr(check, "parts", None),
                            "task": task, "kind": kind, "program": program, "printed": printed, "who": who,
                            "said": _masked(result.get("why")), "when": time.strftime("%Y-%m-%d %H:%M")}) + "\n")


def solo_code(text):
    from team import solo
    return solo.extract_code(text)


DREAM = ("{task}\n\nThis task was done once before, and the answer was wrong. The program written then:\n```python\n{program}\n```\n"
         "It printed: {printed}\nWhat the check said about it (its numbers hidden): {said}\n"
         "Find the mistake in that program, then write the whole corrected program.")


def dream(seed, n=4, failures=None, out=None, log=print, minutes=0, tries=2, weights=None):
    """The hive goes back to tasks it got wrong (failures.jsonl, kept by practice) and corrects itself. Each is made
    again exactly (training/exam.remake), with the old program and what the check said (numbers hidden); where the
    check now passes, the correction is a training row like any other: the old attempt and the verdict lead to the
    right program. Problem solving is the correcting of errors, and the hive's own errors are what it can correct
    (STaR's going back to failed problems, Zelikman et al. 2022; Reflexion, Shinn et al. 2023).
    tries: how many times a task is taken again before it is left for another night, each time with another cell beside
    the trunk (HIVE_ROTATE). Generation 28: one try corrected 5 of 24; a task one cell cannot see through, another may."""
    from training import exam as E
    out = Path(out or GROW / "rows.jsonl")
    src = Path(failures or out.with_name("failures.jsonl"))
    seen = []
    for ln in (src.read_text().splitlines() if src.exists() else []):
        try:
            seen.append(json.loads(ln))
        except ValueError:
            continue
    if not seen:
        return {"dream": seed, "tasks": 0, "right": 0, "rows": 0}
    r = random.Random(f"dream:{seed}")
    recent = seen[-400:]
    # the failures of kinds where some member is right now and then, and the body is not, first (the same weight as
    # practice: edge_weights). Generation 33's dreams took mostly kinds never passed (several parts, modules, facts on
    # the open web) and corrected 0 of 10 in two tries each; lessons start those kinds, dreams finish the ones begun.
    w = weights if weights is not None else edge_weights(_dna())
    pick, pool = [], list(recent)
    while pool and len(pick) < n:
        i = r.choices(range(len(pool)), weights=[max(0.01, w.get(f.get("kind", ""), 0.25)) for f in pool])[0]
        pick.append(pool.pop(i))
    os.environ.setdefault("AGENT_TEAM_SOLO", "2")
    os.environ.setdefault("AGENT_TEAM_SOLO_ALONE", "1")
    home = E._memory(True)
    right = made = 0
    born = time.time()
    for i, f in enumerate(pick):
        if minutes and time.time() - born > minutes * 60:
            log(f"time is up after {i} of {len(pick)} dreams", flush=True)
            break
        again = E.remake(f.get("maker", ""), f.get("rseed", ""), f.get("level", 0), f.get("parts"))
        if not again:
            continue
        field, kind, task, check = again
        text = DREAM.format(task=task, program=f["program"][:5000], printed=(f.get("printed") or "nothing")[:600], said=f.get("said", ""))
        was = os.environ.get("HIVE_ROTATE")
        turn = int(was) if (was or "").isdigit() else 0
        new = []
        for k in range(max(1, int(tries))):
            tid = f"d{seed}_{i:02d}" + (f"_{k}" if k else "")
            if k:  # another cell beside the trunk on each try after the first
                os.environ["HIVE_ROTATE"] = str(turn + k)
            try:
                res = E.sit_one(f"dream_{seed}", tid, text, check, home, kind=kind)
            finally:  # the runner's own turn given back exactly, unset if it was
                if was is None:
                    os.environ.pop("HIVE_ROTATE", None)
                else:
                    os.environ["HIVE_ROTATE"] = was
            # every try's members the check confirmed are rows, the tries that failed as a whole too (taught):
            # generation 28's dreams had 2 failed tries with a member the check confirmed
            new += rows_of(E.RUNS / f"dream_{seed}" / tid, task, kind, seed) + pair_rows(E.RUNS / f"dream_{seed}" / tid, task, kind, seed)
            if res["ok"] or (minutes and time.time() - born > minutes * 60):
                break
        new = once(new)
        for row in new:
            row["dream"] = True
        with open(out, "a") as fo:
            for row in new:
                fo.write(json.dumps(row) + "\n")
        right += res["ok"]
        made += sum(x["type"] != "pair" for x in new)
        log(f"dream {'CORRECTED' if res['ok'] else 'still wrong'} {tid} [{kind}] {res['seconds']}s, try {k + 1}, {len(new)} rows", flush=True)
    return {"dream": seed, "tasks": len(pick), "right": right, "rows": made}


def gather(out, gen, old=(), new=(), log=print):
    """Every checked row so far in one file: those of earlier generations as they are, then this generation's, each
    stamped with the generation it was practised in (training tells new rows from ones the parents already learned).
    The same row is kept once. Returns (rows kept from before, rows added)."""
    from training import grow_record
    lines_old = [ln for f in old for ln in grow_record.lines(f)]
    lines_new = []
    for f in new:
        for ln in grow_record.lines(f):
            try:
                row = json.loads(ln)
            except ValueError:
                continue
            if isinstance(row, dict):
                row.setdefault("gen", gen)
                lines_new.append(json.dumps(row))
    kept = grow_record.union([lines_old, lines_new])
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("".join(ln + "\n" for ln in kept))
    before = len(grow_record.union([lines_old]))
    return before, len(kept) - before


def rows_from(folders, out):
    """Rows from sittings that were already done: every task folder with an exam.json, with rows from the members
    its check confirmed (taught; in a sitting from before the verdicts were kept, only a task that says ok)."""
    made = 0
    with open(out, "a") as f:
        for folder in folders:
            for ex in sorted(Path(folder).rglob("exam.json")):
                try:
                    r = json.loads(ex.read_text())
                except ValueError:
                    continue
                task = (ex.parent / "members" / "TASK.md")
                if isinstance(r, dict) and task.exists():
                    t = task.read_text().strip()
                    for row in rows_of(ex.parent, t) + pair_rows(ex.parent, t):
                        f.write(json.dumps(row) + "\n")
                        made += 1
    return made


# ---- train -----------------------------------------------------------------------------------------------------------
class _Prefix:
    """The layers below the first trained one are frozen, so for a given row they compute the same thing on every
    pass. Their output (the input to the first trained layer) is kept from the first pass of each row, and on later
    passes those layers are skipped and the kept value is used: the same result, without a third to half of the
    forward work from the second pass on (a cell trains the last 14 layers of 28 or 36). Rows are known by their
    tensor. The kept values live in memory up to HIVE_PREFIX_GB (3 by default), or, given a folder, in files there
    up to HIVE_PREFIX_DISK_GB (6): an 8B DNA on a 16 GB runner has no memory to spare for them."""

    def __init__(self, model, first, log=print, folder=None):
        import torch
        layers = model.get_base_model().model.layers if hasattr(model, "get_base_model") else model.model.layers
        self.kept, self.key, self.skip, self.bytes, self.hits, self.misses = {}, None, False, 0, 0, 0
        self.folder = Path(folder) if folder else None
        if self.folder:
            import shutil
            shutil.rmtree(self.folder, ignore_errors=True)
            self.folder.mkdir(parents=True, exist_ok=True)
        self.most = float(os.environ.get("HIVE_PREFIX_DISK_GB", "6") if self.folder else os.environ.get("HIVE_PREFIX_GB", "3")) * 2**30
        for layer in layers[:first]:
            orig = layer.forward

            def passthrough(hidden_states, *a, _orig=orig, **k):
                return hidden_states if self.skip else _orig(hidden_states, *a, **k)
            layer.forward = passthrough

        def pre(module, args, kwargs):
            h = args[0] if args else kwargs["hidden_states"]
            if self.skip:
                h = self._get(self.key)
            elif self.key is not None and self.key not in self.kept and torch.is_grad_enabled() and self.bytes < self.most:
                self._put(self.key, h.detach())
            if args:
                return (h,) + tuple(args[1:]), kwargs
            return args, dict(kwargs, hidden_states=h)
        layers[first].register_forward_pre_hook(pre, with_kwargs=True)

    def _put(self, key, h):
        import torch
        self.bytes += h.numel() * h.element_size()
        if not self.folder:
            self.kept[key] = h
            return
        raw = {2: torch.int16, 4: torch.int32}[h.element_size()]  # the numbers' own bytes, whatever their type
        path = self.folder / f"{len(self.kept)}.bin"
        h.contiguous().view(raw).numpy().tofile(str(path))
        self.kept[key] = (path, tuple(h.shape), h.dtype, raw)

    def _get(self, key):
        import torch
        v = self.kept[key]
        if not isinstance(v, tuple):
            return v
        path, shape, dtype, raw = v
        return torch.from_file(str(path), shared=False, size=math.prod(shape), dtype=raw).view(dtype).view(shape)

    def done(self):
        if self.folder:
            import shutil
            shutil.rmtree(self.folder, ignore_errors=True)

    @contextlib.contextmanager
    def use(self, ids):
        self.key = id(ids)
        self.skip = self.key in self.kept
        self.hits += self.skip
        self.misses += not self.skip
        try:
            yield
        finally:
            self.key, self.skip = None, False


def shorten(messages, keep):
    """The messages with the middle of the longest earlier program cut out (an assistant turn after the task), keeping
    `keep` of its lines: the first ones and the last ones, and a line that says how many were left out. The messages
    themselves when there is no earlier program to cut. Only for context a row shows before its answer."""
    turns = [i for i, m in enumerate(messages) if i >= 2 and m.get("role") == "assistant"]
    if not turns:
        return messages
    i = max(turns, key=lambda j: len(messages[j]["content"]))
    lines = messages[i]["content"].splitlines()
    n = max(6, int(len(lines) * keep))
    if len(lines) <= n + 2:
        return messages
    head, tail = lines[:n * 2 // 3], lines[len(lines) - (n - n * 2 // 3):]
    cut = len(lines) - len(head) - len(tail)
    fence = ["```"] if lines[0].startswith("```") and not tail[-1].startswith("```") else []
    text = "\n".join(head + [f"# ... ({cut} lines of this program left out) ..."] + tail + fence)
    return [dict(m) for m in messages[:i]] + [dict(messages[i], content=text)] + [dict(m) for m in messages[i + 1:]]


KEEP_BACK = int(os.environ.get("HIVE_KEEP_BACK", 2))  # lessons of every kind never trained on, only measured (0: none)


def kept_back(rows, n=None):
    """{kind: [task, ...]}: the `n` lessons of each kind that are never trained on (a lesson is its task; its rows
    share it). The loss of a lesson trained on says only that its rows were met; one never met says whether the kind
    is learned (generation 35's new hard subjects ended at a loss of 0.4 to 1.6 on their own rows, and nothing said
    what that meant for the tasks to come). Chosen by a hash of the task, so every slice of a child keeps back the
    same ones, whatever order the rows come in; and since the rows only grow from one generation to the next, a
    lesson kept back now was kept back in every generation before (the smallest two hashes of a larger set are new
    ones or were already the smallest two)."""
    import zlib
    n = KEEP_BACK if n is None else n
    by = {}
    for r in rows:
        if r.get("who") == "lesson" and r.get("task"):
            by.setdefault(r.get("kind") or "?", set()).add(r["task"])
    return {k: sorted(ts, key=lambda t: (zlib.crc32(t.encode()), t))[:n] for k, ts in sorted(by.items()) if n > 0}


def kept_loss(model, items, dev, cast, beat=None):
    """{kind: [loss of each row]} of the lessons kept back, with the cell's weights as they are now: the same loss
    as training's (the error on the answer's pieces), one row at a time with no gradient, so nothing is held beyond
    one row's logits (an 8B cell trains in 14.7 of 15.6 GB). items: [(kind, (ids, k))] from train's encode."""
    import torch
    was = model.training
    model.eval()  # no dropout: the same rows measured twice give the same number
    out = {}
    with torch.no_grad():
        for j, (kind, (ids, k)) in enumerate(items):
            if beat is not None:
                beat["t"], beat["what"] = time.time(), f"the lessons kept back, row {j + 1} of {len(items)}"
            ids = ids.to(dev)
            with cast():
                lg = model(input_ids=ids, logits_to_keep=k + 1).logits[:, :-1, :]
            out.setdefault(kind, []).append(torch.nn.functional.cross_entropy(lg.float().reshape(-1, lg.size(-1)), ids[:, -k:].reshape(-1)).item())
            del lg
    if was:
        model.train()
    return out


def slice_rows(rows, k, n):
    """Slice k of n of the rows: each row in exactly one slice, chosen by its content (the same row in the same slice on
    every runner, whatever order the rows come in)."""
    import zlib
    if not 0 <= k < n:
        raise ValueError(f"slice {k} of {n}: k must be from 0 to n - 1")
    return [r for r in rows if zlib.crc32(json.dumps([r["messages"][1:], r["output"]], sort_keys=True).encode()) % n == k]


class Study:
    """Which row a cell trains on next. Each kind of task is passed either always or never, and the rows a cell has
    already learned cost passes and teach nothing (g28code's loss went 0.096 -> 0.048 on rows mostly of kinds it
    passed): the passes go where the error is. The rows are sorted into subjects (kind of task, type of row, new this
    generation or not; see subject()). Each pass picks a subject with odds max(its loss, FLOOR), times up to OWN by
    the share of its rows that are the cell's own organ, and trains on that subject's next row (shuffled, cycled). A subject's loss
    is the mean of its last three. A subject not measured yet counts 1.0 and is met before any measured one, so the
    first sweep meets every subject (rehearsing old work too) without waiting on luck. A row is met at most MOST
    times; a subject with none left drops out. Raw text ("read") and judged pairs ("judged") keep a fixed SHARE of
    the passes each instead: their loss does not say what is left to learn."""
    FLOOR, OWN, MOST, SHARE, FIXED = 0.05, 3.0, 4, 0.03, ("read", "judged")  # SHARE was 0.10: g35words gave raw text 30 of 296 passes and its loss went 3.08 -> 2.99

    def __init__(self, subjects, own=(), rng=None, most=None, weight=None):
        """own: {subject: the share of its rows that are the cell's own organ}, or subjects that are wholly its own."""
        self.rng = rng or random.Random(0)
        self.most = self.MOST if most is None else most
        self.weight = self.OWN if weight is None else float(weight)
        self.own = {s: float(v) for s, v in own.items()} if isinstance(own, dict) else {s: 1.0 for s in own}
        self.queue, self.rows, self.passes, self.losses, self.first = {}, {}, {}, {}, {}
        for s, idx in subjects.items():
            if not idx:
                continue
            q = []
            for _ in range(self.most):  # each round of a subject's rows in its own order
                r = list(idx)
                self.rng.shuffle(r)
                q += r
            self.queue[s], self.rows[s], self.passes[s], self.losses[s] = q[::-1], len(idx), 0, []
        self.n = 0

    def loss(self, s):
        h = self.losses[s][-3:]
        return sum(h) / len(h) if h else 1.0

    def odds(self, s):
        return max(self.loss(s), self.FLOOR) * (1.0 + (self.weight - 1.0) * self.own.get(s, 0.0))

    def pick(self):
        """(subject, row index), or None when every row has been met MOST times."""
        alive = [s for s, q in self.queue.items() if q]
        if not alive:
            return None
        rest = [s for s in alive if s not in self.FIXED]
        s = next((f for f in self.FIXED if f in alive and self.passes[f] < self.SHARE * (self.n + 1)), None)
        if s is None:
            fresh = [x for x in rest if not self.losses[x]]
            pool = fresh or rest or alive
            s = self.rng.choices(pool, weights=[self.odds(x) for x in pool])[0]
        self.passes[s] += 1
        self.n += 1
        return s, self.queue[s].pop()

    def learned(self, s, loss):
        if s not in self.first:
            self.first[s] = loss
        self.losses[s].append(float(loss))

    def table(self):
        return [{"subject": s, "rows": self.rows[s], "passes": self.passes[s],
                 "loss_first": round(self.first[s], 4) if s in self.first else None,
                 "loss_last": round(self.loss(s), 4) if self.losses[s] else None}
                for s in sorted(self.rows, key=lambda x: -self.passes[x])]


def lr_share(p):
    """The learning rate's share at `p` of the training done (of its time, or of its passes): a warm-up over the
    first 5%, then a straight fall to 5% at the end."""
    p = min(max(p, 0.0), 1.0)
    return max(0.01, p / 0.05) if p < 0.05 else max(0.05, 1.05 - p)


def subject(row, new=False):
    """The subject a row is studied under (Study): kind of task, type of row, new to the line or not. Rows of type
    "done" (a right program's output -> DONE) are learned at once in every kind (g35code: 40 such subjects, loss about
    0.001, 102 of 444 passes, most of them the first sweep's), so they are one subject, two with the new ones. The
    cell's own organ is not a split (it doubled the subjects) but a weight on a subject by its share of own rows."""
    if row.get("type") == "done":
        return "done" + " · new" * bool(new)
    return " · ".join([row.get("kind") or "?", row.get("type") or "row"] + ["new"] * bool(new))


def train(rows_file, name, base="t17", epochs=2.0, rank=16, lr=2e-4, max_len=1152, layers="all", accum=4, seed=0, limit=0, minutes=0, log=print,
          lean="", weight=3, foresee=False, ternary_edit=False, out_dir=None, checkpoint=True, dtype="bf16", pairs=False, beta=0.1, int8_base=False, read=0, judged=0, parent="", parent_cell="",
          trunk="", pull=0.5, gen="", fresh=2, shard=""):
    """A LoRA weight edit of a ternary member from the hive's rows, on a CPU (or a GPU where there is one, without
    --int8-base: a Colab notebook, training/colab.py); written as a GGUF adapter the
    ternary runtime loads beside the packed base.

    parent: the edit the child starts as. trunk: the body's shared edit (training/merge.py); the child then starts
    as its parent pulled `pull` of the way toward it, so every line of descent stays part of one body.
    parent_cell: the parent's name; what that cell (and the trunk) got wrong in practice, set beside the program
    that was right, is taught to the child as a correction. gen: this generation's name; its rows are new to the
    whole line and are studied as subjects of their own (Study). epochs: the passes over the rows when no `minutes`
    are given; with `minutes` the cell trains until the time is up. weight: how much more the cell's own organ
    weighs in the pick of the next subject. fresh: no longer used (the Study's loss rule replaced the copies).
    shard: "k/n", this runner's slice of the rows (each row in one slice, by its content): a child is grown on n
    runners at once, each from the same start on its own slice, and their edits are averaged into the child
    (training/merge.py join). Generation 28's children got through a third of their rows in their time; n runners
    study n times as many."""
    born = time.time()
    import torch
    from huggingface_hub import snapshot_download
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from team import ternary
    torch.set_num_threads(int(os.environ.get("AGENT_TEAM_THREADS", os.cpu_count() or 4)))
    random.seed(seed)
    torch.manual_seed(seed)
    from team import solo
    rows = [json.loads(x) for x in Path(rows_file).read_text().splitlines() if x.strip()]
    for r in rows:  # rows made before the short orders existed carry the long ones: the taught member is trained under the short
        day = re.search(r"Today is (\d{4}-\d\d-\d\d \(\w+\))", r["messages"][0]["content"])
        r["messages"][0] = {"role": "system", "content": solo.SHORT.format(today=day.group(1) if day else time.strftime("%Y-%m-%d (%A)"))}
    if not foresee:
        rows = [r for r in rows if r.get("type") != "foresee"]
    # what the child's own parent got wrong (and the trunk, the body as one), with the program that was right: the
    # child is taught the correction from where its parent stood (the wrong program, what it was shown, the verdict)
    mend = []
    for r in rows:
        wrong = str(r.get("rejected_who") or "").partition("+")[2]
        if r.get("type") == "pair" and parent_cell and wrong and (wrong == parent_cell or re.fullmatch(r"g\d+trunk", wrong)):
            mend.append({k: v for k, v in r.items() if k not in ("rejected", "rejected_who", "shown")} | {
                "type": "mend", "messages": r["messages"] + [{"role": "assistant", "content": r["rejected"]},
                                                             {"role": "user", "content": MEND.format(shown=r.get("shown") or "It ran.")}]})
    if not pairs:
        rows = [r for r in rows if r.get("type") != "pair"]
    rows += mend
    seen, uniq = set(), []
    for r in rows:  # the same exchange from two sittings teaches nothing twice
        k = json.dumps([r["messages"][1:], r["output"], r.get("rejected")])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    rows = uniq
    # Lessons kept back (kept_back): chosen from all the rows before they are sliced, so every slice keeps back the
    # same ones; no row of their tasks is trained on. Their rows are measured, not their "done" rows (an output ->
    # DONE is learned at once in every kind, about 0.001, and says nothing).
    back = {t: k for k, ts in kept_back(rows).items() for t in ts}
    back_rows = [r for r in rows if r.get("who") == "lesson" and r.get("task") in back and r.get("type") != "done"]
    rows = [r for r in rows if r.get("task") not in back]
    part = ""
    if shard:
        k, n = (int(x) for x in str(shard).split("/"))
        # What is new this generation is studied by every slice; only what the parent already studied is shared out.
        # Generation 35: 3 lessons of a kind fell one to a slice, each slice met its one row 4 times at the most, and
        # the new hard subjects ended at a loss of 0.4 to 1.6. An average of slices keeps what they all learned.
        fresh_rows = [r for r in rows if (gen and r.get("gen") == gen) or r.get("type") == "mend"]
        rows = fresh_rows + slice_rows([r for r in rows if not ((gen and r.get("gen") == gen) or r.get("type") == "mend")], k, n)
        part = f".s{k}"
        log(f"slice {k + 1} of {n}: {len(rows)} rows, {len(fresh_rows)} of them new this generation and studied by every slice "
            f"(the other runners study the rest of the old rows; the slices are averaged into the child)", flush=True)
    src = snapshot_download(UNPACKED[base])
    tok = AutoTokenizer.from_pretrained(src)
    import contextlib
    # bf16 halves the memory and is fast where the CPU has instructions for it (AVX512-BF16); elsewhere 32-bit floats
    # may be the faster way (measured by `speed`)
    half = dtype != "f32"
    if half and int8_base:
        # On a CPU without the 16-bit instructions (about one free runner in four) PyTorch's 16-bit arithmetic is 10 to
        # 16 times slower than its 32-bit, and a cell's first row took hours (three of the first twelve 8B cells were
        # lost that way, with nothing in their logs). There the whole cell is trained in 32-bit: rows have to be
        # about half as long to fit, and it is several times faster than crawling.
        from training import ternary_base
        if not ternary_base.quick16():
            half = False
            log("this CPU has no quick 16-bit arithmetic (no AVX512-BF16, no AMX): the cell is trained in 32-bit numbers", flush=True)
    # a GPU where there is one (a Colab notebook, training/colab.py): the DNA in 16-bit numbers on it, the same LoRA
    # in the same layout as on a CPU, so a cell grown there is a cell like any other
    gpu = torch.cuda.is_available() and not int8_base and os.environ.get("HIVE_GPU", "1") != "0"
    dev = torch.device("cuda" if gpu else "cpu")
    cast = (lambda: torch.autocast(dev.type, dtype=torch.bfloat16)) if half else contextlib.nullcontext
    from transformers import AutoConfig
    nl = AutoConfig.from_pretrained(src).num_hidden_layers
    which = (list(range(nl)) if layers == "all" else list(range(nl // 2, nl)) if layers == "top" else
             list(range(nl - int(layers[4:]), nl)) if layers.startswith("last") else list(range(*map(int, layers.split("-")))))
    cell = None
    if int8_base:
        # the frozen DNA held as what it is, ternary: one byte a weight, so a 4B or 8B DNA trains on a free runner
        # (training/ternary_base.py); the edit is the same LoRA, saved in PEFT's layout
        if ternary_edit:
            raise ValueError("--ternary is not made for --int8-base")
        from training import ternary_base
        model, cell = ternary_base.load(src, rank, 2 * rank, 0.0, which, torch.bfloat16 if half else torch.float32, log=log)
        # How long a row fits beside the DNA on this machine. Measured on the 8B (2026-11-15): 8.1 GB held, and every
        # piece of a row takes about 5 MB more while it is trained on (46 values of the hidden size for each trained
        # layer). A row that does not fit sends the machine into its swap: two of the first eight 8B cells were lost
        # that way, one runner dead, one sitting in its first long row until the job's time was up.
        import psutil
        total = psutil.virtual_memory().total / 2**30
        fits = int((total - ternary_base.held_gb() - 2.5) * 2**30 / (len(which) * model.config.hidden_size * (2 if half else 4) * 46))
        if fits < max_len:
            log(f"this machine has {total:.1f} GB: rows of up to {max(256, fits)} pieces fit beside the DNA (asked for {max_len})", flush=True)
            max_len = max(256, fits)
    else:
        model = AutoModelForCausalLM.from_pretrained(src, dtype=torch.bfloat16 if half else torch.float32).to(dev)
        model = get_peft_model(model, LoraConfig(r=rank, lora_alpha=2 * rank, lora_dropout=0.05, layers_to_transform=which, task_type="CAUSAL_LM",
                                                 target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    if ternary_edit:
        # The cell's own edit in three values as well: each of its matrices is held as ordinary numbers while it is
        # trained, and what the net computes with is their ternary form (-s, 0, +s; s the mean size), the way
        # BitNet b1.58 trains. What is saved is the ternary form, so the whole cell is a BitNet.
        from torch.nn.utils import parametrize

        class Three(torch.nn.Module):
            def forward(self, w):
                s = w.detach().abs().mean().clamp(min=1e-8)
                return w + ((w / s).round().clamp(-1, 1) * s - w).detach()
        edits = [m for n, m in model.named_modules() if n.endswith(("lora_A.default", "lora_B.default"))]
        for m in edits:
            parametrize.register_parametrization(m, "weight", Three())
    model.config.use_cache = False
    start = parent if parent and Path(parent).exists() else ""
    if trunk and Path(trunk).exists():
        # the body's shared edit pulls every line toward it: the child starts as its parent moved `pull` of the way to
        # the trunk (with no parent: as the trunk), cut exactly to the child's rank (training/merge.py)
        from training import merge
        mixed, kept = merge.merge(([merge.load(start)] if start else []) + [merge.load(trunk)], [1 - pull, pull] if start else [1.0], rank)
        GROW.mkdir(parents=True, exist_ok=True)
        start = str(GROW / f"{base}+{name}.start.safetensors")
        merge.save(mixed, start)
        log(f"the child starts as its parent pulled {pull:g} of the way to the trunk ({Path(trunk).name}); at least {kept:.3f} of every matrix is kept at rank {rank}", flush=True)
    if start:
        # the child starts as its parent: every weight of the parent's edit is copied in before training, so what
        # the parent learned (its corrections included) is the child's from the start, and training moves it on
        from safetensors.torch import load_file
        sd = load_file(start)
        got = 0
        if cell:
            for n, m in cell.layers.items():
                a, b = sd.get(f"base_model.model.{n}.lora_A.weight"), sd.get(f"base_model.model.{n}.lora_B.weight")
                if a is not None and b is not None and a.shape == m.lora_A.shape and b.shape == m.lora_B.shape:
                    m.lora_A.data.copy_(a)
                    m.lora_B.data.copy_(b)
                    got += 1
        else:
            for n, p_ in model.named_parameters():
                k = n.replace(".default", "")
                if p_.requires_grad and k in sd and sd[k].shape == p_.shape:
                    p_.data.copy_(sd[k].to(p_.dtype))
                    got += 1
        log(f"the child starts as its parent ({Path(parent).name if parent else Path(trunk).name}): {got} of its matrices inherited", flush=True)
        if not got:
            raise RuntimeError(f"the child was to start from {Path(start).name}, and none of its matrices fit this edit (rank {rank}, layers {which[0]}-{which[-1]})")
    # Each layer's inner values are worked out again on the way back instead of being kept: a third slower, and the
    # memory no longer grows with the length of a row (the first run on a 16 GB runner was killed at step 5).
    if checkpoint:
        model.gradient_checkpointing_enable()
        model.enable_input_require_grads()

    def encode(row):
        p = tok(tok.apply_chat_template(row["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False), add_special_tokens=False)["input_ids"]
        t = tok(row["output"] + "<|im_end|>\n", add_special_tokens=False)["input_ids"]
        if len(p) + len(t) > max_len and not row.get("rejected"):
            # A row that does not fit loses the middle of an earlier program it shows (its context, not what is taught):
            # g28's rows lost 38 of 767 this way, 23 of the 73 rows of modules, almost all "fix" and "done" rows that
            # carry a whole earlier program before the answer. What is taught (the answer) is never cut.
            for keep in (0.6, 0.35, 0.15):
                short = shorten(row["messages"], keep)
                if short is row["messages"]:
                    break
                p = tok(tok.apply_chat_template(short, tokenize=False, add_generation_prompt=True, enable_thinking=False), add_special_tokens=False)["input_ids"]
                if len(p) + len(t) <= max_len:
                    break
        if len(p) + len(t) > max_len:
            return None
        if row.get("rejected"):
            # both are held in memory at once while trained (the right one and the wrong one): together they must fit
            # what one row may take. Counted for one, the first judged pairs on the 8B filled a 16 GB machine (2026-11-15).
            w = tok(row["rejected"] + "<|im_end|>\n", add_special_tokens=False)["input_ids"]
            return None if 2 * len(p) + len(t) + len(w) > max_len else (torch.tensor([p + t]), len(t), torch.tensor([p + w]), len(w))
        return (torch.tensor([p + t]), len(t))
    # Each row once, sorted into its subject (Study): what is trained on next is picked by where the error is, no
    # longer by copies of a row. The cell's own organ weighs `weight` (3) times in that pick: every cell learns all
    # of the hive's checked work (so any two can check each other), each one its own part best. This generation's
    # rows and its parent's corrected mistakes (new to the whole line) are subjects of their own, so the first sweep
    # meets them, and they keep passes for as long as their loss is high. `fresh` is no longer used.
    data, tags, own_rows, mine, new_rows, long = [], [], {}, 0, 0, 0
    for row in rows:
        d = encode(row)
        if d is None:
            long += 1
            continue
        own = bool(lean) and ternary.organ(row["task"]) == lean
        new = (bool(gen) and row.get("gen") == gen) or row.get("type") == "mend"
        data.append(d)
        tags.append(subject(row, new))
        own_rows[tags[-1]] = own_rows.get(tags[-1], 0) + own
        mine += own
        new_rows += new
    if limit:
        data, tags = data[:limit], tags[:limit]
    if lean:
        log(f"this cell leans to {lean}: {mine} of its rows are that organ's, weighed {weight} times in the pick", flush=True)
    if gen or mend:
        log(f"{new_rows} rows are new to this line (generation {gen or '-'}'s own, {len(mend)} of them its parent's mistakes corrected), each a subject of its own", flush=True)
    if long:
        log(f"{long} rows are longer than {max_len} pieces and are left out", flush=True)
    judged_used = 0
    if judged:
        # answers people voted on (training/raw.judged): the best-voted beside the worst-voted for the same question,
        # trained as a right-against-wrong pair, the way the hive's own pairs are
        from training import raw
        for row in raw.judged(judged, name + part, lean, log=log):
            d = encode(row)
            if d is not None:
                data.append(d)
                tags.append("judged")
                judged_used += 1
        log(f"judged: {judged_used} pairs of answers people voted on", flush=True)
    read_used = 0
    if read:
        # raw text and code from the open web (training/raw.py): three times as many drawn as are read, each measured
        # by how well the DNA already predicts it, and the middle band kept: not known yet, but learnable
        from training import raw
        drawn = raw.draw(3 * read, name + part, lean, log=log)
        scored = []
        model.eval()
        for row in drawn:
            # every piece of a raw text carries the loss, not only an answer's: each one keeps the scores of the whole
            # vocabulary (152 thousand words on the 8B) through the step back. 512 pieces filled a 16 GB machine
            # (2026-11-15), so a raw piece is cut to READ_LEN.
            ids = tok(row["text"], add_special_tokens=False)["input_ids"][:READ_LEN]
            if len(ids) < 64:
                continue
            x = torch.tensor([ids])
            with torch.no_grad(), cast():
                lg = model(input_ids=x.to(dev), logits_to_keep=len(ids)).logits[:, :-1, :]
                loss_r = torch.nn.functional.cross_entropy(lg.float().reshape(-1, lg.size(-1)), x[:, 1:].reshape(-1).to(dev)).item()
            scored.append((loss_r, (x, len(ids) - 1)))
        model.train()
        chosen = raw.pick(scored, read)
        data += chosen
        tags += ["read"] * len(chosen)
        read_used = len(chosen)
        if scored:
            ls = sorted(l for l, _ in scored)
            log(f"read: {len(drawn)} raw pieces drawn, {len(scored)} measured (the DNA's error from {ls[0]:.2f} to {ls[-1]:.2f}), "
                f"{read_used} kept from the middle band", flush=True)
    random.seed(f"{seed}:{lean}:{name}")  # two children of one organ in a generation see their rows in their own orders
    torch.manual_seed(abs(hash(lean)) % 10**6 + seed)
    log(f"{len(rows)} rows, {len(data)} within {max_len} pieces (mean {sum(d[0].shape[1] for d in data) // max(1, len(data))}); "
        f"LoRA rank {rank} on layers {which[0]}-{which[-1]} of {UNPACKED[base]}", flush=True)
    params = cell.params if cell else [p for p in model.parameters() if p.requires_grad]
    # What machine this is, and a watch over every row. Three of the first twelve 8B cells never got past their
    # first row (hours, until the job's time was up) and their logs said nothing. Now the log says which CPU this
    # is, a row that takes minutes is reported with the machine's memory, and a row that takes longer than
    # HIVE_ROW_SECONDS (25 minutes) ends the job at once, so the generation goes on with the other children.
    try:
        cpu = next((ln.split(":", 1)[1].strip() for ln in open("/proc/cpuinfo") if ln.startswith("model name")), "?")
    except OSError:
        cpu = "?"
    if int8_base:
        from training import ternary_base
        log(f"this machine: {cpu}, {os.cpu_count()} threads; trained in {'16' if half else '32'}-bit numbers", flush=True)
    elif gpu:
        log(f"this machine: {torch.cuda.get_device_name(0)} ({torch.cuda.get_device_properties(0).total_memory / 2**30:.0f} GB), trained on the GPU", flush=True)
    else:
        log(f"this machine: {cpu}, {os.cpu_count()} threads", flush=True)
    beat = {"t": time.time(), "what": "its first row", "on": True}

    def watch():
        import faulthandler
        import psutil
        most = float(os.environ.get("HIVE_ROW_SECONDS", 1500))
        while beat["on"]:
            time.sleep(60)
            idle = time.time() - beat["t"]
            if beat["on"] and idle > 240:
                vm, sw = psutil.virtual_memory(), psutil.swap_memory()
                log(f"still in {beat['what']} after {idle:.0f} s; memory free {vm.available / 2**30:.1f} GB, swap used {sw.used / 2**30:.1f} GB, load {os.getloadavg()[0]:.1f}", flush=True)
            if beat["on"] and idle > most:
                log(f"one row has taken more than {most:.0f} s: this machine cannot train this cell. The job ends here so that the generation goes on without it.", flush=True)
                faulthandler.dump_traceback(all_threads=True)
                os._exit(3)
    import threading
    threading.Thread(target=watch, daemon=True).start()
    # The passes are not planned ahead from one timed row any more: the loop runs until the time is up, or until
    # every row has been met Study.MOST times, or (with no time given, as in tests) for len(data) x epochs passes;
    # which row comes next is the Study's pick, and the learning rate follows the share of the time used.
    by = {}
    for j, s in enumerate(tags):
        by.setdefault(s, []).append(j)
    own_share = {s: min(1.0, own_rows[s] / len(idx)) for s, idx in by.items() if own_rows.get(s)}
    study = Study(by, own_share, rng=random.Random(f"{seed}:{lean}:{name}{part}"), weight=weight)
    passes = len(data) * study.most if minutes else min(int(len(data) * epochs), len(data) * study.most)
    log(f"{len(data)} rows in {len(study.rows)} subjects; each pass picks a subject by its loss (own organ up to x{weight:g} by its share, read and judged "
        f"{Study.SHARE:.0%} each), a row met at most {study.most} times", flush=True)
    # the lessons kept back, measured where the child starts (its parent pulled toward the trunk) and again at the end;
    # the time the first measure took is kept for the second, out of the cell's own time
    kept_items, kept_long = [], 0
    for r in back_rows:
        d = encode(r)
        if d is None:
            kept_long += 1
        else:
            kept_items.append((back[r["task"]], d[:2]))
    t_kept = time.time()
    kept_before = kept_loss(model, kept_items, dev, cast, beat) if kept_items else {}
    spare = time.time() - t_kept
    if back:
        log(f"lessons kept back: {len(back)}, of {len(set(back.values()))} kinds, never trained on; {len(kept_items)} of their rows measured "
            f"in {spare:.0f} s{f', {kept_long} too long' if kept_long else ''}", flush=True)
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)
    try:
        import ctypes
        trim = ctypes.CDLL("libc.so.6").malloc_trim
    except OSError:
        trim = None
    model.train()
    # not with recomputation (checkpoint): a layer recomputed on the way back would be fed the wrong input
    prefix = (_Prefix(model, which[0], log, folder=GROW / f"{base}+{name}.prefix" if int8_base else None)
              if which[0] > 0 and not checkpoint and not gpu and os.environ.get("HIVE_PREFIX_CACHE", "1") != "0" else None)
    t0, running, step, hist, paired, i, held = time.time(), 0.0, 0, [], 0, 0, 0
    budget = max(1.0, minutes * 60 - (t0 - born) - spare) if minutes else 0

    def done_share():
        return max(i / max(1, passes), (time.time() - t0) / budget if minutes else 0.0)

    def update():
        nonlocal running, step, held
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        p = done_share()
        for g in opt.param_groups:
            g["lr"] = lr * lr_share(p)
        opt.step()
        opt.zero_grad()
        if trim:
            trim(0)
        step += 1
        hist.append(round(running / held, 4))
        running, held = 0.0, 0
        if step % 5 == 0:
            import resource
            on_gpu = f", on the GPU {torch.cuda.max_memory_allocated() / 2**30:.1f} GB" if gpu else ""
            log(f"step {step} ({p:.0%} done, {sum(1 for q in study.queue.values() if q)} subjects left) loss {hist[-1]:.4f} "
                f"{time.time() - t0:.0f}s, most memory {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20:.1f} GB{on_gpu}", flush=True)
    while i < passes:
        if minutes and time.time() - born > minutes * 60 - spare:
            # Two trials were lost on 2026-11-14 because their jobs ran into the time limit with nothing saved: the
            # cell stops here and is kept.
            log(f"time is up after {i} passes: the cell is saved as it is", flush=True)
            break
        got = study.pick()
        if got is None:
            log(f"every row has been met {study.most} times, after {i} passes", flush=True)
            break
        s, idx = got
        ids, k = data[idx][:2]
        ids = ids.to(dev)
        beat["t"], beat["what"] = time.time(), f"pass {i + 1} ({s}, {ids.shape[1]} pieces)"
        with cast(), (prefix.use(ids) if prefix else contextlib.nullcontext()):
            logits = model(input_ids=ids, logits_to_keep=k + 1).logits[:, :-1, :]
        loss = torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.size(-1)), ids[:, -k:].reshape(-1))
        plain = loss.item()  # what the subject is measured by: the error on the right answer (a pair's DPO term starts near 0.69 whatever is known)
        if len(data[idx]) == 4:
            # a right and a wrong program for the same task: DPO, with the plain loss on the right one kept beside it
            # (Iterative RPO). The reference is the cell as it started: the DNA with its edit switched off.
            wid, wk = data[idx][2:]
            wid = wid.to(dev)
            def seq(x, n, lg=None):
                if lg is None:
                    with (prefix.use(x) if prefix else contextlib.nullcontext()):
                        lg = model(input_ids=x, logits_to_keep=n + 1).logits[:, :-1, :]
                return torch.log_softmax(lg.float(), -1).gather(-1, x[:, -n:].unsqueeze(-1)).sum()
            with cast():
                good, bad = seq(ids, k, logits), seq(wid, wk)
                with torch.no_grad(), (cell.off() if cell else model.disable_adapter()):
                    ref_good, ref_bad = seq(ids, k), seq(wid, wk)
            margin = beta * ((good - ref_good) - (bad - ref_bad))
            loss = loss - torch.nn.functional.logsigmoid(margin)
            paired += 1
        (loss / accum).backward()
        running += loss.item()
        held += 1
        study.learned(s, plain)
        i += 1
        if held == accum:
            update()
    if held:
        update()
    subjects = study.table()
    width = max([len(x["subject"]) for x in subjects] + [7])
    log(f"{'subject':<{width}} rows passes  first   last", flush=True)
    for x in subjects:
        f_, l_ = x["loss_first"], x["loss_last"]
        log(f"{x['subject']:<{width}} {x['rows']:>4} {x['passes']:>6} {'-' if f_ is None else f'{f_:.3f}':>6} {'-' if l_ is None else f'{l_:.3f}':>6}", flush=True)
    kept_after = kept_loss(model, kept_items, dev, cast, beat) if kept_items else {}
    mean = lambda v: round(sum(v) / len(v), 4) if v else None  # noqa: E731
    kept = {k: {"lessons": sum(1 for x in back.values() if x == k), "rows": len(kept_before.get(k, [])),
                "before": mean(kept_before.get(k, [])), "after": mean(kept_after.get(k, []))} for k in sorted(set(back.values()))}
    if kept:
        log(f"{'lessons kept back (never trained on), by kind':<{width}} rows before  after", flush=True)
        for k, v in kept.items():
            b_, a_ = v["before"], v["after"]
            log(f"{k:<{width}} {v['rows']:>4} {'-' if b_ is None else f'{b_:.3f}':>6} {'-' if a_ is None else f'{a_:.3f}':>6}", flush=True)
    beat["on"] = False
    work = GROW / f"{base}+{name}"
    work.mkdir(parents=True, exist_ok=True)
    if ternary_edit:
        for m in edits:
            parametrize.remove_parametrizations(m, "weight", leave_parametrized=True)
        levels = max(len(torch.unique(m.weight.detach().float())) for m in edits)
        log(f"the cell's edit is ternary: at most {levels} different values in any of its {len(edits)} matrices", flush=True)
    if cell:
        cell.save(work, src)
    else:
        model.save_pretrained(str(work))
    if prefix:
        log(f"frozen layers skipped on {prefix.hits} of {prefix.hits + prefix.misses} passes (their output kept from the first pass of each row, {prefix.bytes / 2**30:.2f} GB{' on disk' if prefix.folder else ''})", flush=True)
        prefix.done()
    meta = {"member": f"{base}+{name}", "leans": lean, "dtype": dtype, "checkpoint": bool(checkpoint), "seconds_a_row": round((time.time() - t0) / max(1, i), 1), "ternary_edit": bool(ternary_edit), "foresee": bool(foresee), "pairs": paired, "int8_base": bool(int8_base), "read": read_used, "judged": judged_used, "parent": Path(parent).name if parent and Path(parent).exists() else "", "parent_cell": parent_cell, "trunk": Path(trunk).name if trunk and Path(trunk).exists() else "", "mended": len(mend), "new_rows": new_rows, "shard": str(shard or ""), "base": UNPACKED[base], "rows": len(rows), "used": len(data), "passes": i, "epochs": round(i / max(1, len(data)), 2), "rank": rank, "lr": lr,
            "layers": [which[0], which[-1]], "steps": step, "seconds": round(time.time() - t0), "loss_first": hist[0] if hist else None,
            "loss_last": round(sum(hist[-5:]) / max(1, len(hist[-5:])), 4) if hist else None, "when": time.strftime("%Y-%m-%d %H:%M"),
            "memory_gb": round(__import__("resource").getrusage(__import__("resource").RUSAGE_SELF).ru_maxrss / 2**20, 1),
            "gpu": torch.cuda.get_device_name(0) if gpu else "", "subjects": subjects, "kept_back": kept}
    # the adapter as the runtime reads it
    conv = ternary.source() / "convert_lora_to_gguf.py"
    where = Path(out_dir or ternary.ADAPTERS)
    where.mkdir(parents=True, exist_ok=True)
    gguf = where / f"{base}+{name}.gguf"
    done = subprocess.run([sys.executable, str(conv), "--base", src, "--outfile", str(gguf), "--outtype", "f16", str(work)], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError("the edit could not be written as a GGUF adapter: " + done.stderr[-800:])
    meta["file"], meta["megabytes"] = str(gguf), round(gguf.stat().st_size / 2**20, 1)
    (where / f"{base}+{name}.json").write_text(json.dumps(meta, indent=1))
    return meta


def fetch(names=(), log=print):
    """The weight edits the roster names (or those given), downloaded from the release into cells/members/."""
    import urllib.request

    from team import ternary
    repo = os.environ.get("GITHUB_REPOSITORY", "Arnav123-s/HiveMIND")
    got = []
    if not names and not os.environ.get("HIVE_MEMBERS"):
        try:
            body = json.loads(ternary.BODY.read_text())
            names = [f"{body['dna']}+{c}" for c in body.get("cells", [])]
        except (OSError, ValueError, KeyError):
            names = []
    for who in names or ternary.roster():
        if "+" not in who or ternary.adapter(who).exists():
            continue
        ternary.ADAPTERS.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/{repo}/releases/download/{RELEASE}/{who.replace('+', '.')}.gguf"
        try:
            urllib.request.urlretrieve(url, ternary.adapter(who))
            got.append(who)
        except OSError as e:
            log(f"{who}: not fetched from {url}: {e}")
    return got


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    cmd = argv[0] if argv else ""
    if cmd == "dream":
        print(json.dumps(dream(opt("--seed", int(time.time() // 60)), opt("--tasks", 4), opt("--failures", ""), opt("--out", ""), minutes=opt("--minutes", 0), tries=opt("--tries", 2))))
    elif cmd == "practice":
        print(json.dumps(practice(opt("--seed", 10_000_000 + int(time.time() // 60)), opt("--tasks", 16), opt("--level", "mixed"), opt("--out", ""), minutes=opt("--minutes", 0))))
    elif cmd == "gather":
        # python training/grow.py gather --gen g25 --out out/rows.jsonl --old old.jsonl [--old more.jsonl] new1.jsonl new2.jsonl ...
        olds = [argv[i + 1] for i, a in enumerate(argv) if a == "--old" and i + 1 < len(argv)]
        skip = {i + 1 for i, a in enumerate(argv) if a in ("--old", "--gen", "--out")}
        news = [a for i, a in enumerate(argv[1:], 1) if not a.startswith("--") and i not in skip]
        before, added = gather(opt("--out", str(GROW / "rows.jsonl")), opt("--gen", ""), olds, news)
        print(f"rows: {before} from earlier generations, {added} new in generation {opt('--gen', '')}")
    elif cmd == "rows":
        out = opt("--out", str(GROW / "rows.jsonl"))
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        print(rows_from([a for a in argv[1:] if not a.startswith("--") and a != out], out), "rows added to", out)
    elif cmd == "train":
        print(json.dumps(train(opt("--rows", str(GROW / "rows.jsonl")), opt("--name", "gen"), opt("--base", "t17"), opt("--epochs", 2.0), opt("--rank", 16),
                               opt("--lr", 2e-4), opt("--max-len", 1152), opt("--layers", "all"), limit=opt("--limit", 0), minutes=opt("--minutes", 0), lean=opt("--lean", ""), weight=opt("--weight", 3), foresee="--foresee" in argv, pairs="--pairs" in argv, int8_base="--int8-base" in argv, read=opt("--read", 0), judged=opt("--judged", 0), parent=opt("--parent", ""), parent_cell=opt("--parent-cell", ""), trunk=opt("--trunk", ""), pull=opt("--pull", 0.5), gen=opt("--gen", ""), fresh=opt("--fresh", 2), shard=opt("--shard", ""), ternary_edit="--ternary" in argv, checkpoint="--no-checkpoint" not in argv, dtype=opt("--dtype", "bf16")), indent=1))
    elif cmd == "speed":
        # how long one row takes on this machine, each way of training: so that the fastest is used and not guessed
        rows, out = opt("--rows", str(GROW / "rows.jsonl")), []
        for dtype, layers, ck in (("bf16", "all", True), ("bf16", "all", False), ("bf16", "last14", False), ("f32", "all", False), ("f32", "last14", False)):
            p = subprocess.run([sys.executable, __file__, "train", "--rows", rows, "--name", "speed", "--limit", "6", "--epochs", "1", "--dtype", dtype,
                                "--layers", layers, "--base", opt("--base", "t17")] + ([] if ck else ["--no-checkpoint"]), capture_output=True, text=True)
            try:
                m = json.loads(p.stdout[p.stdout.rindex("\n{"):])
                out.append({"dtype": dtype, "layers": layers, "checkpoint": ck, "seconds_a_row": m["seconds_a_row"], "memory_gb": m["memory_gb"], "loss_last": m["loss_last"]})
            except (ValueError, KeyError):
                out.append({"dtype": dtype, "layers": layers, "checkpoint": ck, "failed": (p.stderr or p.stdout)[-200:]})
            print(json.dumps(out[-1]), flush=True)
        for f in (ROOT / "cells" / "members").glob("*+speed.*"):
            f.unlink()
    elif cmd == "fetch":
        print(fetch([a for a in argv[1:] if not a.startswith("--")]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
