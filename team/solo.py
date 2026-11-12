"""The hive as members that each do the whole task, and agree.

    AGENT_TEAM_SOLO=2 python -m team "task" --approve never --run-dir run

Why this exists (2026-11-12). The first three tasks given to the working hive on GitHub, none written to suit it:
"every prime below 200 whose digits add up to 10" (twice) and "the latest httpx on PyPI, its release date, and how
many days ago that was". It got none right: a wrong program passed because it ran; a planner sent a sum to a
researcher; a release date was made up and ticked as done. Each failure was at a hand-over between roles that are
each a small model: the plan, the step's wording, the jury. So here there are no roles. A member is one model that
sees the task as it was given and works on it the only way it can be checked: it writes a program, the program is
run, the member reads what it printed, and goes on until a program does the whole task and prints the answer. What
the member "knows" never reaches the answer unless a program printed it.

One member can still be wrong. So the task is done again by another member, independently (it sees nothing of the
first), and code compares the two answers' values. The same twice: that is the answer. Different: a third member
decides. No two agree: the answer is given as not confirmed, with what each member found. That is what "many,
acting as one" means here: not many roles, many whole tries.

Whether this is better than the roles is not claimed here. It is measured on the same fresh exam
(training/exam.py, AGENT_TEAM_SOLO set or not); the number decides.
"""
import os
import re
import time
from pathlib import Path

from . import config, llm, stop
from .board import Board
from .guard import Guard
from .specialists.coder import extract_code
from .tools.sandbox import run_python

MEMBER = """You solve the TASK by writing Python programs. You see the world only through what your programs print.
Each turn reply with ONE ```python block and nothing else. It is run, and you are shown what it printed.
- Take small steps. First look: fetch the page or API and print the part that matters. Then compute from what you saw.
- A fact about the world (a version, a date, a price, a person, a count) must come from a source a program of yours read
  in this conversation, never from memory. APIs are better than pages:
  https://pypi.org/pypi/NAME/json   https://huggingface.co/api/models/OWNER/NAME
  https://en.wikipedia.org/api/rest_v1/page/summary/TITLE   https://hn.algolia.com/api/v1/search?query=WORDS
- requests and BeautifulSoup are installed. Use timeout=30. Print a few hundred characters, never a whole page.
- Dates, counts and sums are worked out by the program (datetime, len, sum), never in your head. Today is {today}.
- A file the task asks for is saved in the current folder under the exact name given.
- Something only you can do (translate, sum up, write): put your text in a string in the program and print it.
- Never log in, delete, send a message or pay.
When a program of yours has shown everything the task asks for, write the LAST program: it does the whole task again
from the start, by itself, and prints a line FINAL ANSWER, then the answer for the user in plain words (every value
from a variable, none typed in), then one last line starting with KEY: that holds only the bare values asked for,
separated by commas."""

TURNS = int(os.environ.get("AGENT_TEAM_SOLO_TURNS", 8))


def key(answer, task):
    """What two answers are compared by: the KEY line's values, lower-cased, numbers as numbers; without one, the
    answer's numbers that the task does not itself name."""
    m = re.search(r"(?im)^\s*KEY:\s*(.+)$", answer)
    if m:
        parts = [p.strip().lower().strip(".'\"") for p in re.split(r"[,;]", m.group(1)) if p.strip()]
        out = []
        for p in parts:
            try:
                out.append(str(round(float(p.replace(" ", "")), 4)))
            except ValueError:
                out.append(re.sub(r"\s+", " ", p))
        return tuple(sorted(out))
    from .specialists.coder import answer as numbers
    return tuple(str(x) for x in numbers(answer, task))


def same(a, b):
    """Do two answers' values agree? Equal; or, where they are words and no numbers (a translation, a name with or
    without its article), mostly the same words."""
    if not a or not b:
        return False
    if a == b:
        return True
    ta, tb = " ".join(a), " ".join(b)
    if re.search(r"\d", ta + tb):
        return False
    wa, wb = set(re.findall(r"\w+", ta)), set(re.findall(r"\w+", tb))
    return len(wa & wb) / max(1, len(wa | wb)) >= 0.6


def member(task, n, board, guard, work, temperature):
    """One member's whole try. Returns {"answer", "program", "turns"} (answer "" when it never got there)."""
    messages = [{"role": "system", "content": MEMBER.format(today=time.strftime("%Y-%m-%d (%A)"))},
                {"role": "user", "content": f"TASK: {task}"}]
    seen = set()
    for turn in range(1, TURNS + 1):
        stop.check()
        code = extract_code(llm.chat("coder", messages, max_new_tokens=900, stop="code", temperature=temperature))
        if code.strip() in seen:  # the same program again: asked once more with chance in the choice of words
            code = extract_code(llm.chat("coder", messages, max_new_tokens=900, stop="code", temperature=0.8))
        seen.add(code.strip())
        if not guard.check_code("coder", code):
            board.log(f"member{n}", "stopped", "the program needs Arnav's approval; not run")
            return {"answer": "", "program": code, "turns": turn, "stopped": True}
        res = run_python(code, work, name=f"member{n}_{turn}.py")
        out, err = res["stdout"].strip(), res["stderr"].strip()
        board.log(f"member{n}", "run", f"turn {turn}: exit {res['returncode']}, printed {len(out)} characters")
        if res["returncode"] == 0 and "FINAL ANSWER" in out:
            return {"answer": out.split("FINAL ANSWER", 1)[1].lstrip(" :\n").strip(), "program": code, "turns": turn}
        shown = (out[-1800:] or "(nothing printed)") + (f"\nERROR:\n{err[-900:]}" if res["returncode"] != 0 else "")
        last = turn >= TURNS - 1
        messages += [{"role": "assistant", "content": f"```python\n{code}\n```"},
                     {"role": "user", "content": f"OUTPUT:\n{shown}\n\n" + (
                         "Write the LAST program now: the whole task from the start, FINAL ANSWER, the answer, the KEY: line."
                         if last else "Go on. If this shows everything the task asks for, write the LAST program.")}]
    return {"answer": "", "program": "", "turns": TURNS}


def run(task, run_dir=None, approve="never", members=2):
    task = task.strip()
    home = Path(run_dir or config.RUNS / time.strftime("%Y%m%d-%H%M%S"))
    board = Board(home)
    board.goal = task
    (home / "TASK.md").write_text(task + "\n")
    guard = Guard(board, approve, goal=task, use_model=False)
    work = home / "work"
    tries = []
    agreed = None
    for n in range(1, max(1, members) + 2):  # one more than asked, only to decide a difference
        if n > members and (members < 2 or len([t for t in tries if t["answer"]]) < 2):
            break
        t = member(task, n, board, guard, work if n == 1 else home / f"member{n}", 0.0 if n == 1 else 0.7)
        t["key"] = key(t["answer"], task) if t["answer"] else None
        tries.append(t)
        board.log(f"member{n}", "answer", (t["answer"][:200] or "no answer") + f" | key {t['key']}")
        like = [x for x in tries[:-1] if same(x["key"], t["key"])]
        if like:
            agreed = like[0]
            break
    got = [t for t in tries if t["answer"]]
    if agreed:
        text = agreed["answer"] + f"\n\n## How it was checked\n- {len(tries)} members worked it out independently; two gave the same values."
    elif members < 2 and got:
        text = got[0]["answer"] + "\n\n## How it was checked\n- One member worked it out; nobody checked it."
    elif got:
        text = ("Not confirmed: the members that worked this out independently did not agree, so no answer is given."
                "\n\n## What each member found (not confirmed)\n"
                + "\n\n".join(f"Member {i + 1}: {t['answer'][:700]}" for i, t in enumerate(got))
                + "\n\n## How it was checked\n- No two members gave the same values.")
    else:
        text = "No member got as far as an answer. Their programs and what they printed are in this run's folder."
    text = re.sub(r"(?im)^\s*KEY:.*$\n?", "", text).strip() + "\n"
    (home / "REPORT.md").write_text(text)
    board.log("hive", "finished", f"report: {home / 'REPORT.md'}")
    return {"dir": str(home), "report": text, "agreed": bool(agreed), "tries": len(tries), "pending_approvals": guard.pending}
