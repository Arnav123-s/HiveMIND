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
import ast
import os
import re
import time
from pathlib import Path

from . import bitnet, config, llm, stop
from .board import Board
from .guard import Guard
from .specialists.coder import extract_code
from .tools.sandbox import run_python

MEMBER = """You solve the TASK by writing Python programs. You see the world only through what your programs print.
Reply with ONE complete program in a ```python block and nothing else. It is run and you are shown what it printed.
- Whatever can be computed, compute: arithmetic, primes, dates, counting, sorting, text handling. Do not look those up.
- Only a fact about the world (a version, a release date, a price, a person, a population) is read from a source, by
  the program, never from your memory. APIs are better than pages:
  https://pypi.org/pypi/NAME/json (["info"]["version"]; ["releases"][VERSION][0]["upload_time"])
  https://huggingface.co/api/models/OWNER/NAME
  https://en.wikipedia.org/api/rest_v1/page/summary/TITLE   https://hn.algolia.com/api/v1/search?query=WORDS
  Use requests with timeout=30 and headers={{"User-Agent": "hive/1.0"}} (Wikipedia refuses a request without one).
  If you do not know what a source returns, first print a small part of it and look.
- Dates and differences of dates are worked out with datetime. Today is {today}.
- What the program prints is what the user reads: print every result the task asks for, each on its own line as
  "name: value" (the names the task gives, if it gives any). Print nothing else. One piece of text (a summary, a
  translation, a word) is printed alone, as it is.
- A value that can be computed is computed by the program, never typed in ('garden'[::-1], not 'nedrag'). A file the task asks for is saved in the current folder under the exact name given.
- Something only you can do (translate, sum up, write): put your text in a string in the program and print it.
- Never log in, delete, send a message or pay.
Every program is complete by itself: it does not use variables of an earlier program."""
# (For one afternoon this asked more: "... every value asked for, said in words ... if it only shows data you were
# looking at ...". Members then rewrote programs that were already right: 16 tasks took an hour instead of 15 minutes
# and fewer were right. The plain question is back.)
MORE = ("If this output, as it stands, is the complete and correct answer to the TASK, reply with the one word DONE. "
        "If not, reply with a better complete program.")
TURNS = int(os.environ.get("AGENT_TEAM_SOLO_TURNS", 6))


# ---- what the hive has solved --------------------------------------------------------------------------------------
# A task two members agreed on leaves its program behind (memory/solved.jsonl). The next member that gets a task
# like it starts from that program instead of from nothing. This is how the hive gets better with nobody there: by
# doing tasks. Practice (training/exam.py practice) keeps only programs whose answer the task's own check confirmed.
def library():
    from . import memory
    return memory.HOME / "solved.jsonl"


def solved():
    import json
    try:
        return [json.loads(x) for x in library().read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def keep(task, program, answer):
    import json
    if not program.strip() or len(program) > 6000:
        return
    rows = [r for r in solved() if r.get("task") != task][-499:]
    rows.append({"task": task[:1500], "program": program, "answer": answer[:600], "when": time.strftime("%Y-%m-%d %H:%M"), "checked": False})
    library().parent.mkdir(parents=True, exist_ok=True)
    library().write_text("".join(json.dumps(r) + "\n" for r in rows))


def judge(task, right):
    """Practice only: the task's own check has spoken. A confirmed program is marked; a wrong one leaves the library."""
    import json
    rows = [dict(r, checked=True) if r.get("task") == task[:1500] else r for r in solved() if right or r.get("task") != task[:1500]]
    if library().exists():
        library().write_text("".join(json.dumps(r) + "\n" for r in rows))


def alike(task, most=2, least=0.3):
    """The solved tasks most like this one (shared words over all words), confirmed ones first."""
    from . import memory
    mine, out = memory.words(task), []
    for r in solved():
        theirs = memory.words(r.get("task", ""))
        score = len(mine & theirs) / max(1, len(mine | theirs))
        if score >= least and r.get("task") != task[:1500]:
            out.append((bool(r.get("checked")), score, r))
    return [r for _, _, r in sorted(out, key=lambda x: (x[0], x[1]), reverse=True)[:most]]
FAILED = re.compile(r"does not exist|not found|could not|couldn't|unable to|failed|\berror\b|no such|is missing", re.I)
LOOK = re.compile(r"KeyError|IndexError|AttributeError|TypeError|JSONDecodeError|does not exist|not found|NoneType|is missing", re.I)


def key(answer, task):
    """What two members' answers are compared by: their numbers, without those the task itself names."""
    from .specialists.coder import answer as numbers
    return numbers(answer, task)


def parts(answer, task=""):
    """An answer as what agreement is read from: its numbers (without the task's own), the words of its values
    (of every line's part after the colon where all lines are "name: value", else of the whole), and whether it
    was such lines."""
    lines = [x for x in answer.splitlines() if x.strip()]
    labelled = bool(lines) and all(":" in x for x in lines)
    text = " ".join(x.split(":", 1)[1] if labelled else x for x in lines).lower()
    return {round(x, 2) for x in key(answer, task)}, {w for w in re.findall(r"[^\W\d_]+", text) if len(w) > 1}, labelled


def same(a, b, task=""):
    """Do two members' answers agree? The numbers of one are all among the other's ("935.0" and "$935.00, down from
    1100" agree; seed 9005: seven tasks went unconfirmed because values were compared as written), and where both
    give "name: value" lines the words of one are all among the other's ("B: nedrag" against "B: derang" passed
    while only numbers were compared). With no numbers: the value words likewise, or mostly the same words."""
    if not a.strip() or not b.strip():
        return False
    (na, wa, la), (nb, wb, lb) = parts(a, task), parts(b, task)
    inside = lambda x, y: bool(x and y) and (x <= y or y <= x)  # noqa: E731
    if na or nb:
        return inside(na, nb) and (not (la and lb and wa and wb) or inside(wa, wb))
    if la or lb:
        if inside(wa, wb) and (la and lb or (wa if la else wb) <= (wb if la else wa)):
            return True
    full = [set(re.findall(r"\w+", x.lower())) for x in (a, b)]
    return len(full[0] & full[1]) / max(1, len(full[0] | full[1])) >= 0.6


TYPED = ("That is an answer typed out, not a program. Typed answers are often wrong (a word reversed by hand, a sum "
         "done in the head). Reply with a complete Python program in a ```python block that works out every value "
         "that can be worked out (for example word[::-1], 13 * 5) and prints each result on its own line.")


def typed_out(reply, code):
    """Is the reply an answer typed out and not a program? Text that does not parse and came without a code fence;
    or text that parses but calls nothing ("A: 65" on a line is Python too, an annotation; in a fence or out of
    one, text that calls nothing prints nothing)."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return "```" not in reply
    return not any(isinstance(x, ast.Call) for x in ast.walk(tree))


def member(task, n, board, guard, work, temperature):
    """One member's whole try. Returns {"answer", "program", "turns"}: the answer is what its last program that ran
    printed ("" when none ran)."""
    messages = [{"role": "system", "content": MEMBER.format(today=time.strftime("%Y-%m-%d (%A)"))},
                {"role": "user", "content": f"TASK: {task}"}]
    # Only the first member starts from what the hive solved before; the others start from nothing. Shown to all of
    # them, an old program made them agree by copying it, values and all ("Thursday", "95", "87.8": agreed and
    # wrong, seed 9002). Agreement only checks anything between tries that do not share a source.
    # Off unless HIVE_LIBRARY=1: with the library the members passed 7 of 16 in 89 minutes on seed 9003, with nothing
    # learned 10 of 16 in 56 (same code f705ae1; seed 9002 said the same). It is still kept, to be measured again.
    before = alike(task) if n == 1 and os.environ.get("HIVE_LIBRARY", "0") == "1" else []
    if before:
        board.log(f"member{n}", "library", f"{len(before)} solved task(s) like this one")
        messages[-1]["content"] += ("\n\nPrograms of the hive that solved tasks like this one before. Use what fits; the "
                                    "values are different now.\n" + "\n".join(
                                        f"TASK: {r['task'][:400]}\n```python\n{r['program'][:1800]}\n```" for r in before))
    good, last_error, repeats, turn, typed, looking = None, None, 0, 0, 0, False
    for turn in range(1, TURNS + 1):
        stop.check()
        if bitnet.is_member(n):  # this member is another model: the published 2.4B BitNet (team/bitnet.py)
            reply = bitnet.chat(messages, max_new_tokens=700, temperature=temperature)
        else:
            reply = llm.chat("coder", messages, max_new_tokens=700, stop="code", temperature=temperature)
        code = extract_code(reply)
        # Seen once every member's programs were logged (2026-11-12): the word DONE comes back as a program, bare or
        # as print("DONE"). Run, the first died on a NameError and the second replaced a right answer with the four
        # letters DONE; and a member that thought its program final sent the same program again, turn after turn,
        # to the last turn. All three mean the same thing: it is done.
        said = (re.fullmatch(r"(?:print\(\s*)?[\"']?DONE[\"']?\.?\s*\)?", code.strip(), re.I) is not None
                or ("```" not in reply and re.search(r"\bDONE\b", reply) is not None)
                or (good is not None and code.strip() == good["program"].strip()))
        if said:
            if good:
                break
            messages += [{"role": "assistant", "content": reply.strip()[:200]},
                         {"role": "user", "content": "No program of yours has printed an answer yet. Reply with a complete program."}]
            continue
        if typed_out(reply, code):
            # Seen on "multiply 13 by 5; write 'garden' backwards; name the capital": every member typed the three
            # answers out ("B: dnarg"), the text was run as a program, failed the same way twice, and the member stopped.
            typed += 1
            if typed > 1:  # asked for a program and it typed again: what it typed is its answer (a summary, a translation)
                if good is None:
                    good = {"answer": reply.strip()[-3000:], "program": ""}
                break
            messages += [{"role": "assistant", "content": reply.strip()[:600]}, {"role": "user", "content": TYPED}]
            continue
        if not guard.check_code("coder", code):
            board.log(f"member{n}", "stopped", "the program needs Arnav's approval; not run")
            break
        res = run_python(code, work, name=f"member{n}_{turn}.py")
        out, err = res["stdout"].strip(), res["stderr"].strip()
        board.log(f"member{n}", "run", f"turn {turn}: exit {res['returncode']}, printed {len(out)} characters")
        messages.append({"role": "assistant", "content": f"```python\n{code}\n```"})
        if res["returncode"] == 0 and out and FAILED.search(out) and len(out) < 400:
            # a program that catches its own error and prints it has not answered ("The 'upload_time' key does not
            # exist in the response." was one member's answer to "when was the latest httpx released")
            res = dict(res, returncode=1)
            err = f"The program printed a failure, not an answer: {out[-300:]}"
        if res["returncode"] == 0 and out and looking and "[:800]" in code:
            # it was told to print the data as it is, to see its shape: what that printed is not its answer (two
            # members ended with a dump of JSON, one of them the source's own error message, as their answer)
            looking, last_error = False, None
            messages.append({"role": "user", "content": f"OUTPUT:\n{out[-1800:]}\n\nThat is what is really there. Now reply "
                             "with the complete program that prints the answer to the TASK."})
            continue
        if res["returncode"] == 0 and out:
            good, last_error = {"answer": out[-3000:], "program": code}, None
            messages.append({"role": "user", "content": f"OUTPUT:\n{out[-1800:]}\n\n{MORE}"})
            continue
        line = ((err or out).splitlines() or ["it printed nothing"])[-1][:300]
        repeats = repeats + 1 if line == last_error else 0
        if repeats >= 1:  # the same failure twice running: its fixes change nothing
            board.log(f"member{n}", "same-error", line[:150])
            break
        last_error = line
        shown = "\n".join(x for x in (f"OUTPUT:\n{out[-600:]}" if out else "", f"ERROR:\n{err[-900:]}" if err else "") if x)
        looking = bool(LOOK.search(err or out))
        messages.append({"role": "user", "content": (shown or "It ran but printed nothing.") + (
            "\n\nWhat you expected is not there. Reply with a program that only fetches the data and prints what IS "
            "there, with print(str(data)[:800]), so that you can see its real shape." if LOOK.search(err or out) else
            "\n\nReply with the whole corrected program.")})
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
    for n in range(1, max(1, members) + 2):  # one more than asked: to decide a difference, or in place of one that got nowhere
        if n > members and members < 2:
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
        keep(task, agreed["program"], agreed["answer"])
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


def first(task, run_dir=None, approve="never", members=2):
    """The members' try, kept apart (<run>/members) so that the roles can take the task in <run> if they confirm
    nothing. Where they agree, their answer and the files they saved are the run's."""
    import shutil
    home = Path(run_dir or config.RUNS / time.strftime("%Y%m%d-%H%M%S"))
    out = run(task, home / "members", approve, members)
    out["dir"] = str(home)
    if out["agreed"]:
        (home / "REPORT.md").write_text(out["report"])
        (home / "work").mkdir(parents=True, exist_ok=True)
        for p in (home / "members" / "work").iterdir():
            if p.is_file() and not p.name.startswith(".") and not re.fullmatch(r"member\d+_\d+\.py", p.name):
                shutil.copy2(p, home / "work" / p.name)
    return out
