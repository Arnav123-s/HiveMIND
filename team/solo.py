"""The hive as members that each do the whole task, and agree.

    AGENT_TEAM_SOLO=2 python -m team "task" --approve never --run-dir run

Why this exists (2026-11-12). The first three tasks given to the working hive on GitHub, none written to suit it:
"every prime below 200 whose digits add up to 10" (twice) and "the latest httpx on PyPI, its release date, and how
many days ago that was". It got none right: a wrong program passed because it ran; a planner sent a sum to a
researcher; a release date was made up and ticked as done. Each failure was at a hand-over between roles that are
each a small model: the plan, the step's wording, the jury. So here there are no roles. A member is one model that
sees the task as it was given and works on it the only way it can be checked: it writes a program, the program is
run, the member reads what it printed, and writes a better one until it says the output is the answer. The answer
is what that program printed: what the member "knows" never reaches it otherwise.
(Its first form asked for a closing program with a marked last line. On GitHub one member worked the primes out
right in its first program and then failed seven times at the closing form. So there is none: a program, its
output, and the one word DONE.)

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
Reply with ONE complete program in a ```python block and nothing else. It is run and you are shown what it printed.
- Whatever can be computed, compute: arithmetic, primes, dates, counting, sorting, text handling. Do not look those up.
- Only a fact about the world (a version, a release date, a price, a person, a population) is read from a source, by
  the program, never from your memory. APIs are better than pages:
  https://pypi.org/pypi/NAME/json   https://huggingface.co/api/models/OWNER/NAME
  https://en.wikipedia.org/api/rest_v1/page/summary/TITLE   https://hn.algolia.com/api/v1/search?query=WORDS
  Use requests with timeout=30. If you do not know what a source returns, first print a small part of it and look.
- Dates and differences of dates are worked out with datetime. Today is {today}.
- What the program prints is what the user reads: print every result the task asks for, each with a few words saying
  what it is. Print nothing else. A file the task asks for is saved in the current folder under the exact name given.
- Something only you can do (translate, sum up, write): put your text in a string in the program and print it.
- Never log in, delete, send a message or pay.
Every program is complete by itself: it does not use variables of an earlier program."""
MORE = ("If this output, as it stands, is the complete and correct answer to the TASK, reply with the one word DONE. "
        "If not, reply with a better complete program.")
TURNS = int(os.environ.get("AGENT_TEAM_SOLO_TURNS", 6))


def key(answer, task):
    """What two members' answers are compared by: their numbers, without those the task itself names."""
    from .specialists.coder import answer as numbers
    return numbers(answer, task)


def same(a, b, task=""):
    """Do two members' answers agree? The same numbers; or, where neither holds a number (a translation, a name),
    mostly the same words."""
    if not a.strip() or not b.strip():
        return False
    ka, kb = key(a, task), key(b, task)
    if ka or kb:
        return ka == kb
    wa, wb = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    return len(wa & wb) / max(1, len(wa | wb)) >= 0.6


def member(task, n, board, guard, work, temperature):
    """One member's whole try. Returns {"answer", "program", "turns"}: the answer is what its last program that ran
    printed ("" when none ran)."""
    messages = [{"role": "system", "content": MEMBER.format(today=time.strftime("%Y-%m-%d (%A)"))},
                {"role": "user", "content": f"TASK: {task}"}]
    good, last_error, turn = None, None, 0
    for turn in range(1, TURNS + 1):
        stop.check()
        reply = llm.chat("coder", messages, max_new_tokens=700, stop="code", temperature=temperature)
        if "```" not in reply and re.search(r"\bDONE\b", reply):
            if good:
                break
            messages += [{"role": "assistant", "content": reply.strip()[:200]},
                         {"role": "user", "content": "No program of yours has printed an answer yet. Reply with a complete program."}]
            continue
        code = extract_code(reply)
        if not guard.check_code("coder", code):
            board.log(f"member{n}", "stopped", "the program needs Arnav's approval; not run")
            break
        res = run_python(code, work, name=f"member{n}_{turn}.py")
        out, err = res["stdout"].strip(), res["stderr"].strip()
        board.log(f"member{n}", "run", f"turn {turn}: exit {res['returncode']}, printed {len(out)} characters")
        messages.append({"role": "assistant", "content": f"```python\n{code}\n```"})
        if res["returncode"] == 0 and out:
            good, last_error = {"answer": out[-3000:], "program": code}, None
            messages.append({"role": "user", "content": f"OUTPUT:\n{out[-1800:]}\n\n{MORE}"})
            continue
        line = (err.splitlines() or ["it printed nothing"])[-1][:300]
        if line == last_error:  # its fix changed nothing: another turn of the same would cost minutes and give the same
            board.log(f"member{n}", "same-error", line[:150])
            break
        last_error = line
        messages.append({"role": "user", "content": (f"ERROR:\n{err[-900:]}" if err else "It ran but printed nothing.")
                         + "\n\nReply with the whole corrected program."})
    return {"answer": (good or {}).get("answer", ""), "program": (good or {}).get("program", ""), "turns": turn}


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
        tries.append(t)
        board.log(f"member{n}", "answer", t["answer"][:300] or "no answer")
        like = [x for x in tries[:-1] if same(x["answer"], t["answer"], task)]
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
    text = text.strip() + "\n"
    (home / "REPORT.md").write_text(text)
    board.log("hive", "finished", f"report: {home / 'REPORT.md'}")
    return {"dir": str(home), "report": text, "agreed": bool(agreed), "tries": len(tries), "pending_approvals": guard.pending}
