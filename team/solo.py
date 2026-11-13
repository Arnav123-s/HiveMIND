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
import json
import os
import re
import time
from pathlib import Path

from . import config, llm, stop, ternary
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
  https://huggingface.co/api/models/OWNER/NAME (["cardData"]["license"]; ["likes"]; ["downloads"]; ["tags"] holds "name:value")
  https://en.wikipedia.org/api/rest_v1/page/summary/TITLE   https://hn.algolia.com/api/v1/search?query=WORDS
  Use requests with timeout=30 and headers={{"User-Agent": "hive/1.0"}} (Wikipedia refuses a request without one).
  If you do not know what a source returns, first print a small part of it and look.
- A page inside a website is reached from the site's first page (https://...), by finding there the link whose text
  matches and following it. An inner address written from memory is usually wrong.
- Dates and differences of dates are worked out with datetime. Today is {today}.
- What the program prints is what the user reads. Where the TASK says how the answer must look (a numbered list,
  labels such as A, B, C, JSON, one word, one sentence, exactly so many items), print exactly that and nothing
  else. Otherwise print every result the task asks for, each on its own line as "name: value". One piece of text
  (a summary, a translation, a word) is printed alone, as it is.
- A value that can be computed is computed by the program, never typed in ('garden'[::-1], not 'nedrag'). A file the task asks for is saved in the current folder under the exact name given.
- Data the TASK gives (a table, a log, a CSV, a list) exists only in the TASK: copy it into the program as a string.
  There is no file unless your program writes it.
- Something only you can do (translate, sum up, write): put your text in a string in the program and print it.
- Never log in, delete, send a message or pay.
Every program is complete by itself: it does not use variables of an earlier program."""
# (For one afternoon this asked more: "... every value asked for, said in words ... if it only shows data you were
# looking at ...". Members then rewrote programs that were already right: 16 tasks took an hour instead of 15 minutes
# and fewer were right. The plain question is back.)
MORE = ("If this output, as it stands, is the complete and correct answer to the TASK, reply with the one word DONE. "
        "If not, reply with a better complete program.")
TURNS = int(os.environ.get("AGENT_TEAM_SOLO_TURNS", 6))
# the most a member may write in one reply. It was 700: on the hard exam a program that writes a module to a file and
# then tests it was cut off in the middle and died of a syntax error (two of three members, first hard practice)
LONG = int(os.environ.get("AGENT_TEAM_SOLO_LONG", 1600))


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
FAILED = re.compile(r"does not exist|not found|could not|couldn't|unable to|failed|\berror\b|no such|is missing|\bunknown\b|not available|\bN/A\b|: None$", re.I | re.M)
LOOK = re.compile(r"KeyError|IndexError|AttributeError|TypeError|JSONDecodeError|does not exist|not found|NoneType|is missing|\bunknown\b|not available|\bN/A\b|: None$", re.I | re.M)


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
    prose = not la and not lb and min(len(a.split()), len(b.split())) >= 5
    if (na or nb) and not prose:
        # "205.0" and "205.03" are one answer given to different places (seed 9005: a conversion went unconfirmed)
        near = lambda x, y: bool(x and y) and (all(any(abs(i - j) < 0.051 for j in y) for i in x)  # noqa: E731
                                               or all(any(abs(i - j) < 0.051 for j in x) for i in y))
        return near(na, nb) and (not (la and lb and wa and wb) or inside(wa, wb))
    if la or lb:
        if inside(wa, wb) and (la and lb or (wa if la else wb) <= (wb if la else wa)):
            return True
    full = [set(re.findall(r"\w+", x.lower())) for x in (a, b)]
    # sentences (a summary, a translation) by two members never match word for word: seed 9005 left both unconfirmed
    return len(full[0] & full[1]) / max(1, len(full[0] | full[1])) >= (0.4 if prose else 0.6)


TYPED = ("That is an answer typed out, not a program. Typed answers are often wrong (a word reversed by hand, a sum "
         "done in the head). Reply with a complete Python program in a ```python block that works out every value "
         "that can be worked out and prints the answer in the form the TASK asks for, like this:\n"
         "```python\nprint('A:', 13 * 5)\nprint('B:', 'garden'[::-1])\nprint('C:', 'Wellington')\n```\n"
         "Text only you can write (a summary, a translation, a name you know) goes in a string and is printed.")
NUMBER = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def form(task, answer):
    """What the TASK says about the shape of the answer that code can count, where the answer does not keep it:
    said in words for the member, or "". Seen on seeds 9005 to 9007: a numbered list printed as "1: Red", a
    one-sentence summary given as the three sentences of the text, the labels A, B, C left out."""
    n = lambda w: int(w) if w.isdigit() else NUMBER.get(w.lower())  # noqa: E731
    lines = [x.strip() for x in answer.splitlines() if x.strip()]
    low = task.lower()
    if "numbered list" in low:
        items = [x for x in lines if re.match(r"\d+[.)]\s+\S", x)]
        m = re.search(r"\bexactly (\d+|[a-z]+)\b", low)
        want = n(m.group(1)) if m else None
        if len(items) != len(lines) or (want and len(items) != want):
            return (f"The TASK asks for a numbered list{f' of exactly {want} items' if want else ''} and nothing else: lines "
                    f"like '1. ...' and '2. ...'. Your output has {len(items)} such line(s) among {len(lines)}.")
    m = re.search(r"\b(\d+|one|two|three|four|five)[- ]sentence\b|\bin (\d+|one|two|three|four|five) sentences?\b", low)
    if m and n(m.group(1) or m.group(2)):
        want, have = n(m.group(1) or m.group(2)), len(re.findall(r"[.!?]+(?=\s|$)", answer.strip())) or 1
        if have != want:
            return f"The TASK asks for {want} sentence(s). Your output has {have}."
    m = re.search(r"\blabel\w* (?:the |your )?(?:answers? |them |results? )?((?:[A-Z](?:, | and |,? and )?){2,})", task)
    if m:
        missing = [c for c in re.findall(r"[A-Z]", m.group(1)) if not any(re.match(rf"{c}\s*[:.)]", x) for x in lines)]
        if missing:
            return (f"The TASK asks for the answers labelled {', '.join(re.findall(r'[A-Z]', m.group(1)))}, each on its own line "
                    f"('A: ...'). Your output has no line for {', '.join(missing)}.")
    # labels the TASK spells out in quotes ("Answer in four lines: 'customer: ', 'spent: ', ..."): seen on the first hard
    # practice, where a member worked all four values out and printed "Sofia: 347.75" four times
    named = re.findall(r"'([A-Za-z][\w ]{0,24}): ?[^']{0,12}'", task)
    if len(named) >= 2:
        missing = [c for c in named if not any(re.match(rf"\W*{re.escape(c)}\s*:", x, re.I) for x in lines)]
        if missing:
            return (f"The TASK asks for lines that begin with {', '.join(repr(c + ':') for c in named)}. Your output has no line "
                    f"that begins with {', '.join(repr(c + ':') for c in missing)}.")
    return ""


FILE = re.compile(r"\b(?:sav\w*|writ\w*|creat\w*|mak\w*|produc\w*|generat\w*|stor\w*|export\w*)\b[^.\n]{0,80}?(?<![\w/.-])([\w-]+\.(?:py|csv|tsv|json|md|txt|html|xml|ya?ml))\b", re.I)


def wanted(task):
    """The files the TASK asks to be saved, by name ("save it as roman.py", "make a new file people.csv")."""
    return list(dict.fromkeys(m.group(1) for m in FILE.finditer(task)))


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
    good, last_error, repeats, turn, typed, looking, shaped, insisted = None, None, 0, 0, 0, False, 0, False
    for turn in range(1, TURNS + 1):
        stop.check()
        who = ternary.seat(n)  # who sits here: the 7B coder, or a ternary model with or without an edit (team/ternary.py)
        if who == "coder":
            reply = llm.chat("coder", messages, max_new_tokens=LONG, stop="code", temperature=temperature)
        else:
            reply = ternary.chat(who, messages, max_new_tokens=LONG, temperature=temperature)
        code = extract_code(reply)
        # Seen once every member's programs were logged (2026-11-12): the word DONE comes back as a program, bare or
        # as print("DONE"). Run, the first died on a NameError and the second replaced a right answer with the four
        # letters DONE; and a member that thought its program final sent the same program again, turn after turn,
        # to the last turn. All three mean the same thing: it is done.
        said = (re.fullmatch(r"(?:print\(\s*)?[\"']?DONE[\"']?\.?\s*\)?", code.strip(), re.I) is not None
                or ("```" not in reply and re.search(r"\bDONE\b", reply) is not None)
                or (good is not None and code.strip() == good["program"].strip()))
        if said:
            if good and form(task, good["answer"]) and not insisted:
                insisted = True  # DONE straight after being told the form is not kept: told once more, then it stands
                messages += [{"role": "assistant", "content": reply.strip()[:200]},
                             {"role": "user", "content": form(task, good["answer"]) + " It is not done. Reply with the complete program that prints it that way."}]
                continue
            if good:
                break
            messages += [{"role": "assistant", "content": reply.strip()[:200]},
                         {"role": "user", "content": "No program of yours has printed an answer yet. Reply with a complete program."}]
            continue
        if typed_out(reply, code):
            # Seen on "multiply 13 by 5; write 'garden' backwards; name the capital": every member typed the three
            # answers out ("B: dnarg"), the text was run as a program, failed the same way twice, and the member stopped.
            # (For a few hours what was typed twice was taken as the answer, for summaries and translations. Those
            # come as programs that print a string anyway; what came typed twice was "B: dnarg", agreed on by two.)
            typed += 1
            if typed > 3:
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
        # Seen on seed 9011 (the members' own work, uploaded): three members each made up the address of an inner
        # page (horror_2, horror_26, horror_37), got a 404, saved a CSV with only its heading, printed "CSV file
        # created", and two of them agreed on that sentence.
        gone = re.search(r"HIVE-HTTP: \w+ (\S+) returned ([45]\d\d)", err)
        if res["returncode"] == 0 and gone:
            res = dict(res, returncode=1)
            err = (f"The address {gone.group(1)} answered {gone.group(2)}: there is no such page. Do not make an address up. "
                   "Fetch the site's first page, print the links on it (their text and href), and follow the one that matches.")
        bare = [f.name for f in (Path(work).iterdir() if Path(work).exists() else []) if f.is_file() and f.suffix in (".csv", ".tsv")
                and len([x for x in f.read_text(errors="ignore").splitlines() if x.strip()]) <= 1]
        if res["returncode"] == 0 and bare:
            res = dict(res, returncode=1)
            err = (f"The file {bare[0]} you saved holds no rows (at most a heading): what the program looked for was not on "
                   "the page. Print what the page really holds and look.")
        lacking = [f for f in wanted(task) if not (Path(work) / f).is_file() or not (Path(work) / f).stat().st_size]
        if res["returncode"] == 0 and lacking:
            # Seen on the first hard sitting (seed 7001): asked to "save it as durations.py", both members wrote the
            # two functions into their own program, printed the values, and agreed. The file was never written.
            res = dict(res, returncode=1)
            err = (f"The TASK asks for the file {lacking[0]} saved in the current folder, and it is not there. Reply with the complete "
                   f"program that writes {lacking[0]} (with open({lacking[0]!r}, 'w')), then uses it, and prints the answer.")
        failed = FAILED.search(out) if res["returncode"] == 0 and out and len(out) < 400 else None
        if failed and failed.group(0).lower() not in task.lower():  # (a task about ERROR lines is answered with the word error)
            # a program that catches its own error and prints it has not answered ("The 'upload_time' key does not
            # exist in the response." was one member's answer to "when was the latest httpx released")
            res = dict(res, returncode=1)
            err = f"The program printed a failure, not an answer: {out[-300:]}"
        if res["returncode"] == 0 and out and looking and re.search(r"\[:\d{3,4}\]", code):
            # it was told to print the data as it is, to see its shape: what that printed is not its answer (two
            # members ended with a dump of JSON, one of them the source's own error message, as their answer)
            looking, last_error = False, None
            messages.append({"role": "user", "content": f"OUTPUT:\n{out[-1800:]}\n\nThat is what is really there. Now reply "
                             "with the complete program that prints the answer to the TASK."})
            continue
        if res["returncode"] == 0 and out:
            good, last_error = {"answer": out[-3000:], "program": code}, None
            shape = form(task, out) if shaped < 2 else ""
            shaped += bool(shape)
            messages.append({"role": "user", "content": f"OUTPUT:\n{out[-1800:]}\n\n" + (
                shape + " Reply with the complete program that prints it that way." if shape else MORE)})
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
            "there, with print(list(data)[:40] if isinstance(data, dict) else type(data)) and print(str(data)[:1500]), so that "
            "you can see its real shape (a license \"Unknown\" or None means the key you read is not there)." if LOOK.search(err or out) else
            "\n\nReply with the whole corrected program.")})
    return {"answer": (good or {}).get("answer", ""), "program": (good or {}).get("program", ""), "turns": turn,
            "who": ternary.seat(n), "messages": messages}


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
        t["work"] = str(work if n == 1 else home / f"member{n}")
        tries.append(t)
        board.log(f"member{n}", "answer", t["answer"][:300] or "no answer")
        # the whole exchange is kept: where the task's check later confirms the answer, it is what the hive's own
        # members are taught from (training/grow.py)
        (home / f"member{n}.json").write_text(json.dumps(t))
        like = [x for x in tries[:-1] if same(x["answer"], t["answer"], task)]
        if like:
            agreed = next((x for x in (like[0], t) if not form(task, x["answer"])), like[0])  # of two that agree, the one that keeps the form asked for
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
    (home / "members.json").write_text(json.dumps({"agreed": bool(agreed), "who": [t["who"] for t in tries],
                                                  "agreeing": [i + 1 for i, t in enumerate(tries) if agreed and same(t["answer"], agreed["answer"], task)]}))
    return {"dir": str(home), "report": text, "agreed": bool(agreed), "tries": len(tries), "pending_approvals": guard.pending,
            "work": agreed["work"] if agreed else str(work)}


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
        for p in Path(out["work"]).iterdir():  # the files of the member whose answer stands (member 1's were taken even when 2 and 3 agreed)
            if p.is_file() and not p.name.startswith(".") and not re.fullmatch(r"member\d+_\d+\.py", p.name):
                shutil.copy2(p, home / "work" / p.name)
    return out
