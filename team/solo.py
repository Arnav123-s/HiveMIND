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
import signal
import time
import tempfile
import contextlib
from pathlib import Path

from . import config, deliverables, llm, stop, ternary
from .deliverables import wanted
from .board import Board
from .guard import Guard
from .specialists.coder import extract_code
from .tools.sandbox import give, note, run_python

MEMBER = """You solve the TASK by writing Python programs. You see the world only through what your programs print.
Reply with ONE complete program in a ```python block and nothing else. It is run and you are shown what it printed.
- Whatever can be computed, compute: arithmetic, primes, dates, counting, sorting, text handling. Do not look those up.
- What does not change and you know for certain (a capital city, a chemical symbol, what a word means, a
  translation, a rule of grammar or of science) needs no source: put it in a string in the program and print it.
- Only a fact that changes or must be exact (a version, a release date, a price, a population, a date of birth,
  what a web page says) is read from a source, by the program, never from your memory. APIs are better than pages:
  https://pypi.org/pypi/NAME/json (["info"]["version"]; ["releases"][VERSION][0]["upload_time"])
  https://huggingface.co/api/models/OWNER/NAME (["cardData"]["license"]; ["likes"]; ["downloads"]; ["tags"] holds "name:value")
  https://en.wikipedia.org/api/rest_v1/page/summary/TITLE   https://hn.algolia.com/api/v1/search?query=WORDS
  Use requests with timeout=30 and headers={{"User-Agent": "hive/1.0"}} (Wikipedia refuses a request without one).
  If you do not know what a source returns, look first: look(x) is built in. Given JSON data or a requests
  response it prints the keys, nested; given the text of a web page it prints the page's links and text.
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
# A member the hive has taught (a ternary model with a weight edit of its own, "t17+gen3") was trained on the hive's
# checked work under these few lines: what MEMBER spells out, it has in its weights. Short orders also make its
# training rows short enough for a 16 GB runner, and its turns faster.
SHORT = ("You solve the TASK by writing Python programs. Reply with ONE complete program in a ```python block and nothing "
         "else. It is run and you are shown what it printed. look(x) is built in: it shows what JSON data or a web page "
         "really holds. Today is {today}.")


def orders(who, today=None):
    """The system prompt of the member in a seat: the full orders, or the short ones for a member the hive taught."""
    return (SHORT if "+" in who else MEMBER).format(today=today or time.strftime("%Y-%m-%d (%A)"))


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
# a search that came back empty where the TASK says there is something (seen in a trial of the g27 exam: a log's
# lines split and the level read from the wrong place; "No ERROR lines found.", and max() of nothing)
EMPTY = re.compile(r"\bno\b[^.\n]{0,40}\bfound\b|max\(\) (iterable )?arg\w* is (an )?empty|min\(\) (iterable )?arg\w* is (an )?empty|"
                   r"\bfound nothing\b|\bnothing found\b", re.I)
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


CODE = re.compile(r"(?<![\w.])v?(\d+(?:\.\d+){2,}(?:[.-]?[a-z]+\d*)*)(?![\w]|\.\d)", re.I)


def codes(answer, task=""):
    """The values of an answer that are written with dots and are no number: a version ("1.18.1", "v2.0.0rc1"), an
    address ("10.0.0.7"), without those the task itself names. key() leaves them out, so nothing compared them."""
    named = {x.lower() for x in CODE.findall(task)}
    return {x.lower() for x in CODE.findall(answer)} - named


def same(a, b, task=""):
    """Do two members' answers agree? The numbers of one are all among the other's ("935.0" and "$935.00, down from
    1100" agree; seed 9005: seven tasks went unconfirmed because values were compared as written), and where both
    give "name: value" lines the words of one are all among the other's ("B: nedrag" against "B: derang" passed
    while only numbers were compared). With no numbers: the value words likewise, or mostly the same words."""
    if not a.strip() or not b.strip():
        return False
    from . import parts as several
    pa, pb = several.of_answer(a, merge=True), several.of_answer(b, merge=True)
    if len(pa) > 1 and len(pb) > 1:
        # answers given part by part ('PART A', 'PART B', ...) agree when every part does: compared as a whole, the
        # numbers of one part hid a different word in another
        return set(pa) == set(pb) and all(pa[k].strip() == pb[k].strip() or same(pa[k], pb[k], task) for k in pa)
    (na, wa, la), (nb, wb, lb) = parts(a, task), parts(b, task)
    inside = lambda x, y: bool(x and y) and (x <= y or y <= x)  # noqa: E731
    ca, cb = codes(a, task), codes(b, task)
    if ca and cb:
        # g38's pulse: "1.18.1" and "Current version of scipy on PyPI: 1.18.1" did not agree (a version is no number
        # and the words differ), so two right members gave no answer, twice in 32 easy tasks; and "1.18.1" agreed with
        # "1.18.0" (the digits as words, two of three alike). Where both name such a value it must be the same one;
        # then the numbers decide if both have any, else the value words of lines that are both "name: value".
        if not inside(ca, cb):
            return False
        if not (na and nb):
            return not (la and lb and wa and wb) or inside(wa, wb)
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
    said in words for the member, or "". A task of several parts (team/parts.py) is read part by part: each part's
    answer stands under its own heading and keeps the form that part asks for."""
    from . import parts as several
    asked = several.of_task(task)
    if not asked:
        return _form(task, answer)
    got = several.of_answer(answer)
    missing = [k for k in asked if k not in got]
    if missing:
        # every missing heading is named, and where it goes: in g28's practice the members wrote "# PART A" as a
        # comment, which prints nothing, and one told only of 'PART A' printed that and still left out 'PART B'
        return (f"The TASK asks for each part's answer under its own heading, each heading alone on its line: "
                f"{', '.join(repr('PART ' + k) for k in asked)}. Your output has no line "
                f"{' and no line '.join(repr('PART ' + k) for k in missing)}. A comment such as # PART {missing[0]} prints "
                f"nothing: the program must print('PART {missing[0]}') just before that part's answer.")
    for k, t in asked.items():
        wrong = _form(t, got[k])
        if wrong:
            return f"Under the heading 'PART {k}': " + wrong.replace("The TASK asks", "that part asks").replace("Your output has", "What you printed there has")
    return ""


def whole(task, answer):
    """Does the answer carry the heading of every part the task has (team/parts.py)? Always so for a task of one part.
    The exam reads each part from under its heading: without it the part fails, whatever its values."""
    from . import parts as several
    return set(several.of_task(task)) <= set(several.of_answer(answer))


def _form(task, answer):
    """form() for one task. Seen on seeds 9005 to 9007: a numbered list printed as "1: Red", a one-sentence summary
    given as the three sentences of the text, the labels A, B, C left out."""
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
    # a count asked for, and a list or dict printed: g45's coin task ("in how many different ways ...") got a Counter
    # of every way, 6000 characters, from two members who agreed on it; the count itself was never printed. A list
    # of three items or more alone on a line, or a long run of them (the tail of one cut to 3000 characters)
    if COUNTED.search(task) and (any(LISTED.match(x) and x.count(",") >= 2 for x in lines[-3:])
                                 or len(answer) > 1500 and answer.count(",") > 50):
        return ("The TASK asks how many: its answer is a number, the count. Your output is the items themselves, a list or a "
                "dict. Print the count (len() of what you counted, or the sum), with a few words saying what it counts.")
    return ""


# asked as the question ("tell me how many", "In how many ways ...?"), not a function that "returns how many times"
COUNTED = re.compile(r"(?:\b(?:tell me|say|print|give|report|work out|find out)\s+|(?:^|[.?!:]\s+)(?:in |and )?)how many\b|"
                     r"\bhow many\b[^.?!\n]*\?|\bcount (?:the|how|them|all|every)\b", re.I)
# a printed list, dict, set or Counter, or the tail of one (an answer keeps the last 3000 characters)
LISTED = re.compile(r"(?:\w+\()?[\[{(].*[\]})]\)?$")


def typed_out(reply, code):
    """Is the reply an answer typed out and not a program? Text that does not parse and came without a code fence;
    or text that parses but calls nothing ("A: 65" on a line is Python too, an annotation; in a fence or out of
    one, text that calls nothing prints nothing)."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return "```" not in reply
    # a program that only defines functions calls nothing too, and is a program (a module the TASK asks for)
    return not any(isinstance(x, (ast.Call, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for x in ast.walk(tree))


def module(task, code, work, board=None, n=0):
    """A module the TASK asks for (save it as rle.py), saved from the member's own program when the program did not
    write it: its imports, functions, classes and constants, without the lines that test and print. Seen in the pulse
    of g27: a member's program defined encode and decode right and printed the right values; told rle.py was missing,
    it wrote its own source into a quoted string, broke the quotes, and died of a SyntaxError on every turn after."""
    if Path(work).is_symlink():
        return ""
    lacking = [f for f in wanted(task) if f.endswith(".py") and not (Path(work) / f).exists() and not (Path(work) / f).is_symlink()]
    if not lacking:
        return ""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return ""
    keep = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            keep.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            try:
                ast.literal_eval(node.value)
                keep.append(node)
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                pass
    if not any(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for x in keep):
        return ""
    if any(isinstance(x, ast.ImportFrom) and x.module == lacking[0][:-3] for x in keep):
        return ""  # it imports the module it was to write: its own functions are not that module
    src = "\n\n".join(ast.get_source_segment(code, x) or ast.unparse(x) for x in keep) + "\n"
    (Path(work) / lacking[0]).write_text(src)
    if board is not None:
        board.log(f"member{n}", "module", f"{lacking[0]} saved from the program's functions")
    return lacking[0]


# The help the runtime gave, by name. Every hint that rescues a task makes a row the next cells learn from, so a
# body that learns on its own needs fewer of them generation after generation (scripts/selfreliance.py counts them).
HINTS = [("given", "HIVE-GIVEN:"), ("deeper_key", "it is in the data at:"), ("like_keys", "these look like it:"),
         ("html_json", "is a web page (HTML), not JSON"), ("no_address", "there is no address to fetch"),
         ("no_host", "does not exist (no such host)"), ("memory", "MEMORY: the program used"),
         ("bad_address", "there is no such page. Do not make an address up"), ("same_page", "the loop never moved to"),
         ("empty_file", "holds no rows (at most a heading)"), ("missing_file", "and it is not there. Reply with the complete"),
         ("empty_search", "The program found nothing"), ("printed_failure", "The program printed a failure, not an answer")]


def hints_in(*texts):
    """The names of the runtime's hints that these texts (a program's stderr, what the member was told) carry."""
    t = "\n".join(x or "" for x in texts)
    return [name for name, mark in HINTS if mark in t]


def clashes(code):
    """Names a class gives both to a method (def name) and to a value (self.name = ...): the value hides the method.
    Seen in g45 (h20000451_01): `self.left = []` beside `def left(self, ...)`, and two members stopped on "'list'
    object is not callable"."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []
    out = []
    for c in (x for x in ast.walk(tree) if isinstance(x, ast.ClassDef)):
        methods = {f.name for f in c.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
        values = {t.attr for x in ast.walk(c) if isinstance(x, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                  for t in (x.targets if isinstance(x, ast.Assign) else [x.target])
                  if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self"}
        out += sorted(methods & values)
    return out


def stuck_hint(task, code, err):
    """For a module the TASK asks for (hidden tests call it), what to do about an AssertionError or a TypeError of
    the member's own test: (hint name, words), or None. In g45 17 members' tries ended on the same error twice, most
    of them such tries; told only "print the values", they sent the same program back."""
    if not any(f.endswith(".py") for f in wanted(task)) or not re.search(r"\b(?:AssertionError|TypeError)\b", err or ""):
        return None
    clash = clashes(code)
    if clash:
        return ("name_clash", f"Your class uses the name {clash[0]!r} for a method (def {clash[0]}) and for a value "
                f"(self.{clash[0]} = ...). The value hides the method, so calling it fails. Give the value another name "
                f"(self._{clash[0]}) everywhere it is used, and keep the method's name, which the TASK gives.")
    if "AssertionError" in err:
        return ("assert_values", "One of your own tests failed. Just before each assert, print the actual value and the "
                "expected one (print('got', got, 'want', want)), see which part of the function gives the wrong value, "
                "and fix the function. Keep the test only if the TASK says that value is right.")
    return ("type_values", "A TypeError: the line that failed got a value of another type than it expects. Print type() "
            "and the value of each thing that line works with. Check that no method has the name of a value "
            "(self.name = ...), and that each function takes the arguments the TASK says, in that order.")


def member(task, n, board, guard, work, temperature, who="coder", also=()):
    """One member's whole try. Returns {"answer", "program", "turns"}: the answer is what its last program that ran
    printed ("" when none ran)."""
    # engrams were written under the short orders too, so a member with any engram on gets them. HIVE_SHORT_ORDERS=1
    # gives them with no engram: the control that tells an engram's effect from the short orders' own
    # (training/experiments/memory_stream.py, arm "short")
    short = also or os.environ.get("HIVE_SHORT_ORDERS", "0") == "1"
    # HIVE_FULL_ORDERS=1: the full orders even for a taught member (whose name has "+"), the other arm of practice's
    # split (training/practice_arms.py); never set for the gate or the exams
    full = not short and os.environ.get("HIVE_FULL_ORDERS", "0") == "1"
    messages = [{"role": "system", "content": orders(who.replace("+", "-") if full else who + "+" if short else who)},
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
    if os.environ.get("HIVE_NOTES", "0") == "1":
        # short ways of working the hive wrote down from its own checked work, failures too (team/notes.py): no
        # program and no value in them, so nothing to copy. Put in the orders, which the rows taught from leave out.
        from . import notes
        said = notes.recall(task, os.environ.get("HIVE_KIND") or None)
        if said:
            messages[0]["content"] += notes.block(said)
            board.log(f"member{n}", "notes", f"{len(said)} note(s) from earlier work")
    names = wanted(task)
    messages[-1]["content"] += note(give(task, work, skip=names))
    saved_files = tempfile.TemporaryDirectory() if names else None
    helped = []

    def helps(*names):
        for h in names:
            helped.append(h)
            board.log(f"member{n}", "hint", h)
    good, last_error, repeats, turn, typed, looking, shaped, insisted = None, None, 0, 0, 0, False, 0, False
    for turn in range(1, TURNS + 1):
        stop.check()
        if who == "coder":
            reply = llm.chat("coder", messages, max_new_tokens=LONG, stop="code", temperature=temperature)
        else:
            reply = ternary.chat(who, messages, max_new_tokens=LONG, temperature=temperature, also=also)
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
        again = re.search(r"HIVE-SAME: (\S+) was fetched (\d+) times", err)
        if res["returncode"] == 0 and again:
            res = dict(res, returncode=1)
            err = (f"The program fetched the same page {again.group(1)} {again.group(2)} times: the loop never moved to "
                   "another page. Find the link to the next page on each page (its text is often 'Next') and fetch that, "
                   "or put the page number into the address.")
        bare = []
        if not names and res["returncode"] == 0 and Path(work).exists():
            for f in Path(work).iterdir():
                if f.suffix not in (".csv", ".tsv"):
                    continue
                try:
                    with deliverables.regular(f) as data:
                        lines = (line for line in data if line.strip())
                        if next(lines, None) is None or next(lines, None) is None:
                            bare.append(f.name)
                except (OSError, ValueError):
                    continue
        if res["returncode"] == 0 and bare:
            res = dict(res, returncode=1)
            err = (f"The file {bare[0]} you saved holds no rows (at most a heading): what the program looked for was not on "
                   "the page. Print what the page really holds and look.")
        saved = module(task, code, work, board, n) if res["returncode"] == 0 else ""
        if saved:
            helps("module_saved")
        if saved and not out:
            # Seen in a trial of the g27 exam: the module was saved from two members' programs, which defined the
            # functions and printed nothing; told "it printed nothing" twice, both gave up, and with no two answers
            # alike the module was never counted
            last_error = None
            messages += [{"role": "assistant", "content": f"```python\n{code}\n```"},
                         {"role": "user", "content": f"Your functions are saved as {saved}. Now reply with a short program that "
                          f"imports {saved[:-3]}, calls the functions as the TASK asks, and prints each value it asks for."}]
            continue
        delivery = deliverables.inspect(task, work, names) if names and res["returncode"] == 0 else None
        if res["returncode"] == 0 and out and len(out) < 300 and EMPTY.search(out) and not EMPTY.search(task):
            res = dict(res, returncode=1)
            err = f"The program found nothing: {out.strip()[-200:]}"
        failed = FAILED.search(out) if res["returncode"] == 0 and out and len(out) < 400 else None
        if failed and failed.group(0).lower() not in task.lower():  # (a task about ERROR lines is answered with the word error)
            # a program that catches its own error and prints it has not answered ("The 'upload_time' key does not
            # exist in the response." was one member's answer to "when was the latest httpx released")
            res = dict(res, returncode=1)
            err = f"The program printed a failure, not an answer: {out[-300:]}"
        helps(*hints_in(res["stderr"], err if err != res["stderr"] else ""))
        if res["returncode"] == 0 and out and (looking and re.search(r"\[:\d{3,4}\]", code) or re.search(r"\blook\(", code)
                                                and re.search(r"^PAGE title:|^\s*'\w+': |^\[\d+ items; the first:\]", out, re.M)):
            # it was told to print the data as it is, to see its shape: what that printed is not its answer (two
            # members ended with a dump of JSON, one of them the source's own error message, as their answer)
            looking, last_error = False, None
            messages.append({"role": "user", "content": f"OUTPUT:\n{out[:2600]}\n\nThat is what is really there. Now reply "
                             "with the complete program that prints the answer to the TASK."})
            continue
        if res["returncode"] == 0 and out:
            candidate = {"answer": out[-3000:], "program": code}
            feedback = ""
            if delivery is not None:
                candidate["delivery"] = delivery
                if not delivery["issues"]:
                    try:
                        deliverables.copy_files(work, names, saved_files.name)
                    except (OSError, ValueError) as e:
                        delivery["issues"]["copy"] = str(e)
                if delivery["issues"]:
                    feedback = "; ".join(f"{f}: {why}" for f, why in delivery["issues"].items())
                    feedback += ". Reply with a complete program that fixes the requested file."
            # A later program can overwrite a good file and then fail. Keep the successful
            # output and the matching files together, including through a member's final DONE.
            if good is None or not delivery or not delivery["issues"] or good["delivery"]["issues"]:
                good = candidate
            last_error = None
            shape = form(task, out) if shaped < 2 else ""
            shaped += bool(shape)
            messages.append({"role": "user", "content": f"OUTPUT:\n{out[-1800:]}\n\n" + (
                feedback or (shape + " Reply with the complete program that prints it that way." if shape else MORE))})
            continue
        line = ((err or out).splitlines() or ["it printed nothing"])[-1][:300]
        repeats = repeats + 1 if line == last_error else 0
        # the same failure three times running: its fixes change nothing. It was twice: in g45, 17 members' tries ended
        # so, 12 of them at turn 2 of 6, before a hint could be acted on
        if repeats >= 2:
            board.log(f"member{n}", "same-error", line[:150])
            break
        last_error = line
        shown = "\n".join(x for x in (f"OUTPUT:\n{out[-600:]}" if out else "", f"ERROR:\n{err[-900:]}" if err else "") if x)
        # look() is for data the program read; an error in a calculation of its own is found by printing its own values
        # (seen in g27: a robot simulation's IndexError, and two members went to fetch example.com)
        reads = re.search(r"\brequests\.|urllib|\.json\(|json\.loads?\(|BeautifulSoup|\bopen\(|read_csv|playwright", code) is not None
        stuck = stuck_hint(task, code, err or out)
        if stuck:
            helps(stuck[0])
        looking = not stuck and bool(LOOK.search(err or out)) and (reads or re.search(r"KeyError|NoneType|JSONDecodeError|\bkeys?\b|response|json|\bpage\b|column|field", err or out, re.I) is not None)
        messages.append({"role": "user", "content": (shown or "It ran but printed nothing.") + (
            "\n\n" + stuck[1] + " Reply with the whole corrected program." if stuck else
            "\n\nThe program found nothing where the TASK says there is something, so it reads the data wrongly. Reply "
            "with a short program that prints the first 3 items it looks through and how it splits them (for a line of "
            "text: print(line.split())), so you see their real shape. Then fix the program." if EMPTY.search(err or out) else
            "\n\nWhat you expected is not there. Reply with a short program that only fetches the data and calls look(data) "
            "(look is built in: for JSON it prints the keys, nested; for a web page pass response.text and it prints the links "
            "and the text). Then you see what IS there." if looking else
            "\n\nThe error is in the program's own steps. Print the values it works with just before the line that failed, "
            "see where they go wrong, and reply with the whole corrected program." if LOOK.search(err or out) else
            "\n\nReply with the whole corrected program.")})
    if saved_files is not None:
        if good and not good["delivery"]["issues"]:
            try:
                deliverables.copy_files(saved_files.name, names, work)
            except (OSError, ValueError) as e:
                good["delivery"]["issues"]["copy"] = str(e)
        saved_files.cleanup()
    return {**(good or {"answer": "", "program": ""}), "turns": turn,
            "who": who, "messages": messages, "hints": helped, "temperature": temperature, "also": list(also)}


def headings(task, t, n, board, guard):
    """Ask member n once more, plainly, for the program that prints every part's heading, when its answer to a task of
    several parts agreed with another's without them. Its answer is replaced only by one that carries them all; the
    headings are never put in by guessing which printed line belongs to which part."""
    from . import parts as several
    asked = list(several.of_task(task))
    t["asked"] = True
    stop.check()
    messages = t["messages"]
    if messages and messages[-1]["role"] == "user":  # what it was last told and did not act on: the plain ask takes its place
        messages.pop()
    messages.append({"role": "user", "content": (
        f"OUTPUT:\n{t['answer'][-1800:]}\n\nThat output is not an answer to the TASK yet: it has no headings. The TASK has "
        f"{len(asked)} parts, and the output must show each part's heading printed alone on its own line, with that part's "
        f"answer on the lines below it. A comment such as # PART A prints nothing. Reply with the complete program, with "
        + ", ".join(f"print('PART {k}') just before the lines of part {k}'s answer" for k in asked) + ".")})
    board.log(f"member{n}", "asked", "agreed without the headings of the parts: asked once more for them")
    if t["who"] == "coder":
        reply = llm.chat("coder", messages, max_new_tokens=LONG, stop="code", temperature=t.get("temperature", 0.0))
    else:
        reply = ternary.chat(t["who"], messages, max_new_tokens=LONG, temperature=t.get("temperature", 0.0), also=tuple(t.get("also", ())))
    code = extract_code(reply)
    if typed_out(reply, code) or not code.strip() or not guard.check_code("coder", code):
        return
    work = Path(t["work"])
    names = wanted(task)
    if names:
        work = Path(tempfile.mkdtemp(prefix=f"member{n}-retry-", dir=work.parent))
        give(task, work, skip=names)
        if not t["delivery"]["issues"]:
            try:
                deliverables.copy_files(t["work"], names, work)
            except (ValueError, OSError):
                return
    res = run_python(code, work, name=f"member{n}_{t['turns'] + 1}.py")
    out = res["stdout"].strip()
    messages += [{"role": "assistant", "content": f"```python\n{code}\n```"}, {"role": "user", "content": f"OUTPUT:\n{out[-1800:]}"}]
    board.log(f"member{n}", "run", f"asked again: exit {res['returncode']}, printed {len(out)} characters")
    if res["returncode"] == 0 and whole(task, out):
        if names:
            delivery = deliverables.inspect(task, work, names)
            if delivery["issues"]:
                return
            t.update(work=str(work), delivery=delivery)
        t.update(answer=out[-3000:], program=code, turns=t["turns"] + 1)


def _cell(x):
    """A value of a saved file as it is compared: trimmed, a number written one way ("75", "75.0" and " 75 " alike)."""
    x = str(x).strip()
    try:
        return repr(round(float(x), 6)) if re.fullmatch(r"[-+]?\d[\d_]*(?:\.\d*)?(?:e[-+]?\d+)?", x, re.I) else x
    except ValueError:
        return x


def contents(path):
    """A saved file as what two members' files are compared by: its rows of trimmed cells (a CSV or TSV), its data (a
    JSON file), else its lines trimmed; blank lines left out. None when it is missing, empty or cannot be read."""
    import csv
    p = Path(path)
    try:
        text = p.read_text(errors="ignore") if p.is_file() else ""
    except OSError:
        return None
    if not text.strip():
        return None
    if p.suffix.lower() == ".json":
        try:
            return json.dumps(json.loads(text), sort_keys=True)
        except ValueError:
            pass
    if p.suffix.lower() in (".csv", ".tsv"):
        rows = csv.reader(text.splitlines(), delimiter="\t" if p.suffix.lower() == ".tsv" else ",")
        return [tuple(_cell(c) for c in r) for r in rows if any(c.strip() for c in r)]
    return [" ".join(x.split()) for x in text.splitlines() if x.strip()]


def same_files(x, y, task):
    """Do two members' tries agree on the files the TASK asks to be saved? Each of those files (not a .py module, whose
    code always differs) is in both members' work folders with the same contents(). Seen in g45: on top-rows all
    three members saved the right top.csv and passed the check, but printed "top.csv saved / student: Ines", "Omar /
    Ines" and "Ines : 99", so same() found no two alike and the task was lost; six file tasks were lost that way.
    One of the two must have printed an answer (in g45's pivot task one member saved the right file and then printed
    only a look() at its data)."""
    names = [f for f in wanted(task) if not f.endswith(".py")]
    if not names or not x.get("work") or not y.get("work") or not (x.get("answer") or y.get("answer")):
        return False
    for f in names:
        a, b = contents(Path(x["work"]) / f), contents(Path(y["work"]) / f)
        if a is None or a != b:
            return False
    return True


def together(x, y, task):
    """Do two members' tries agree: their printed answers (same()), or the files the TASK asks for (same_files())."""
    return same(x["answer"], y["answer"], task) or same_files(x, y, task)


def agreeing(tries, task):
    """The pairs of members whose tries agree (together()), the earlier member first."""
    return [(x, y) for i, x in enumerate(tries) for y in tries[i + 1:] if together(x, y, task)]


def _winner(tries, pairs, task):
    """The delivered member needs an agreeing witness, complete headings and all requested files.
    If agreeing witnesses have conflicting structured files, require independent content agreement."""
    candidates = []
    for x in tries:
        peers = [b if a is x else a for a, b in pairs if a is x or b is x]
        if not peers or not whole(task, x["answer"]):
            continue
        delivery = x.get("delivery", {})
        if delivery.get("issues"):
            continue
        comparable = [deliverables.comparison(p["delivery"]) for p in peers if p.get("delivery") and not p["delivery"]["issues"]]
        repair = bool(delivery and deliverables.repairs(delivery))
        if (comparable or repair) and deliverables.comparison(delivery) not in comparable:
            continue
        candidates.append((repair, bool(form(task, x["answer"])), x))
    return min(candidates, key=lambda c: c[:2])[2] if candidates else None


def _home(run_dir):
    if run_dir:
        return Path(run_dir)
    config.RUNS.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=time.strftime("%Y%m%d-%H%M%S-"), dir=config.RUNS))


class Capped(BaseException):
    """The time cap of the task was reached (the exam sends SIGTERM, then SIGKILL after a grace). Not an Exception:
    nothing in a member's work may swallow it."""


_CAP = {"hit": False, "live": False}


def _on_cap(sig, frame):
    _CAP["hit"] = True
    if _CAP["live"]:
        _CAP["live"] = False
        raise Capped()


@contextlib.contextmanager
def capping():
    """SIGTERM is the time cap. In g48's practice 15 of 42 failures were tasks cut off at 600 s, with the answers the
    members had already given thrown away (h10004806_00 had a member's right answer at 427 s). Under this the member in
    hand is given up, and run() goes on to agreement and delivery with the tries that are in."""
    try:
        old = signal.signal(signal.SIGTERM, _on_cap)
    except ValueError:  # not the main thread: no cap to hear
        yield
        return
    _CAP["hit"] = False
    try:
        yield
    finally:
        _CAP["live"] = False
        signal.signal(signal.SIGTERM, old)


def run(task, run_dir=None, approve="never", members=2):
    with capping():
        return _run(task, run_dir, approve, members)


EXTRA_SEATS = 2


def extra_seat(tries, given):
    """May one more member sit after the seats are used up? Seen in g48's gate: 5 of 11 failed hard tasks had one member
    right while the other two crashed (NameError, TypeError) or gave nothing, so no two agreed and nothing was delivered.
    Only where one answer or a disagreement is in and a member got no answer (crashed), and only until two agree: delivery still needs two in agreement, so
    an extra seat never delivers an answer nobody witnessed. At most EXTRA_SEATS more; the time cap still ends the loop.
    Expected cost: one extra member call in the tasks that have a crash and no pair (about 1 in 6 hard tasks)."""
    return given < EXTRA_SEATS and any(t["answer"] for t in tries) and any(not t["answer"] for t in tries) and not _CAP["hit"]


def _run(task, run_dir=None, approve="never", members=2):
    task = task.strip()
    home = _home(run_dir)
    board = Board(home)
    board.goal = task
    (home / "TASK.md").write_text(task + "\n")
    guard = Guard(board, approve, goal=task, use_model=False)
    work = home / "work"
    names = wanted(task)
    tries = []
    agreed = None
    seats = ternary.seating(task)
    board.log("hive", "seats", f"{ternary.organ(task)}: {', '.join(seats[:max(1, members) + 1])}")
    n = 0
    while True:  # one more than asked: to decide a difference, or in place of one that got nowhere
        n += 1
        if n > members and members < 2:
            break
        if n > max(1, members) + 1 and not extra_seat(tries, n - max(1, members) - 2):
            break
        # who sits where for this task: the cells that lean to its kind of work first (team/ternary.seating); the last
        # one named also takes every later seat
        who = seats[n - 1] if n <= len(seats) else seats[-1]
        also = ()
        if os.environ.get("HIVE_ENGRAMS") == "1" and who != "coder":  # the body's fast memory: what it wrote down of tasks like this one
            from . import engram
            base, cell = ternary.split(who)
            if os.environ.get("HIVE_ENGRAM_GATE") == "1":  # each as strong as its task is like this one
                also = tuple(engram.recall_scaled(task, base, cell=cell))
            else:
                also = tuple(engram.recall(task, base, cell=cell))  # its own line's first
            if also and n == 1:
                board.log("hive", "engrams", ", ".join(x if isinstance(x, str) else f"{x[0]} at {x[1]}" for x in also))
        member_work = work if n == 1 else home / f"member{n}"
        if names and (member_work.is_symlink() or member_work.exists() and (not member_work.is_dir() or any(member_work.iterdir()))):
            # A caller may retry the same run directory. Old files cannot witness a new program.
            member_work = Path(tempfile.mkdtemp(prefix=f"member{n}-", dir=home))
        if _CAP["hit"]:
            break
        _CAP["live"] = True
        try:
            t = member(task, n, board, guard, member_work, 0.0 if n == 1 else min(1.0, 0.7 + 0.15 * max(0, n - max(1, members) - 1)), who, also)
        except Capped:
            board.log("hive", "capped", f"time cap reached in member {n}: the {len(tries)} answer(s) in go to agreement")
            break
        finally:
            _CAP["live"] = False
        t["work"] = str(member_work)
        if names:
            checked = deliverables.inspect(task, member_work, names)
            previous = t.get("delivery", {})
            if previous.get("issues"):
                checked["issues"].update(previous["issues"])
            elif previous and previous["byte_hashes"] != checked["byte_hashes"]:
                checked["issues"]["copy"] = "file changed after the program printed its answer"
            t["delivery"] = checked
        tries.append(t)
        board.log(f"member{n}", "answer", t["answer"][:300] or "no answer")
        # the whole exchange is kept: where the task's check later confirms the answer, it is what the hive's own
        # members are taught from (training/grow.py)
        (home / f"member{n}.json").write_text(json.dumps(t))
        pairs = agreeing(tries, task)
        if pairs and not any(whole(task, x["answer"]) for p in pairs for x in p):
            # Seen in g28's practice: two members agreed on the values of a task of several parts, printed with no
            # 'PART A' heading (they wrote "# PART A" as a comment), and the agreed answer failed every part, values
            # right or not. Values that agree are no answer the exam can read until one of them carries every heading:
            # each member that agreed without them is asked once more, plainly, the latest first.
            for i in [i for i in reversed(range(len(tries))) if any(tries[i] is x for p in pairs for x in p) and not tries[i].get("asked")]:
                headings(task, tries[i], i + 1, board, guard)
                (home / f"member{i + 1}.json").write_text(json.dumps(tries[i]))
                if whole(task, tries[i]["answer"]):
                    break
            pairs = agreeing(tries, task)
        pairs = [p for p in pairs if any(whole(task, x["answer"]) for x in p)]
        agreed = _winner(tries, pairs if names else pairs[:1], task)
        if agreed:
            break
    got = [t for t in tries if t["answer"]]
    file_repairs = []
    selected_work = agreed["work"] if agreed else str(work)
    selected_delivery = agreed.get("delivery") if agreed else None
    repair_failure = ""
    if selected_delivery:
        file_repairs = deliverables.repairs(selected_delivery)
    if file_repairs:
        # Two independent cells supplied the same data in the requested sort order
        # after normalization. Preserve their raw artifacts and correct a staging copy.
        staging = Path(tempfile.mkdtemp(prefix="ordered-", dir=home))
        try:
            deliverables.copy_files(selected_work, names, staging)
            if deliverables.inspect(task, staging, names) != selected_delivery:
                raise ValueError("the source file changed before sorting")
            for repair in file_repairs:
                deliverables.apply_order(staging, repair["name"], repair)
            checked = deliverables.inspect(task, staging, names)
            if checked["issues"] or deliverables.repairs(checked) or checked["content"] != deliverables.comparison(selected_delivery):
                raise ValueError("the sorted file did not preserve the checked data")
        except (ValueError, OSError) as e:
            repair_failure = str(e)
            agreed, file_repairs = None, []
        else:
            selected_work, selected_delivery = str(staging), checked
    if agreed:
        if not file_repairs:
            keep(task, agreed["program"], agreed["answer"])
        text = agreed["answer"] + f"\n\n## How it was checked\n- {len(tries)} members worked it out independently; two gave the same values."
        if names:
            matched = any(t is not agreed and same(t["answer"], agreed["answer"], task)
                          and not t["delivery"]["issues"] and t["delivery"]["content"] == agreed["delivery"]["content"]
                          for t in tries)
            text += "\n- Reopened and checked the requested files: " + ", ".join(names) + "."
            if file_repairs:
                for repair in file_repairs:
                    text += f"\n- Two members supplied the same rows. The hive sorted {repair['name']} by {repair['column']} {repair['direction']}."
            elif agreed["delivery"]["content"] and matched:
                text += " Two members produced matching structured data."
    elif names and got and (members >= 2 or got[0]["delivery"]["issues"]):
        reasons = [repair_failure] if repair_failure else []
        for i, t in enumerate(tries, 1):
            issues = t["delivery"]["issues"]
            if issues:
                reasons.append(f"Member {i}: " + "; ".join(f"{name}: {why}" for name, why in issues.items()))
        text = ("Not confirmed: the hive could not select a complete file with an independently supported answer."
                + ("\n\n" + "\n".join(reasons) if reasons else " The members' answers or structured files differ."))
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
    witnesses = [i for i, t in enumerate(tries, 1) if agreed and same(t["answer"], agreed["answer"], task)]
    agreeing_members = [i for i in witnesses if not names or (not tries[i - 1]["delivery"]["issues"]
                        and tries[i - 1]["delivery"]["content"] == agreed["delivery"]["content"])]
    if file_repairs:
        agreeing_members = []  # the user received the helper's sorted copy, not a cell's raw output
    decision = {"agreed": bool(agreed), "who": [t["who"] for t in tries], "agreeing": agreeing_members}
    if names:
        decision.update(requested_files=names, printed_agreeing=witnesses, file_repairs=file_repairs,
                        selected_member=next((i for i, t in enumerate(tries, 1) if t is agreed), None))
    (home / "members.json").write_text(json.dumps(decision))
    result = {"dir": str(home), "report": text, "agreed": bool(agreed), "tries": len(tries), "pending_approvals": guard.pending,
              "work": selected_work if agreed else str(work), "requested_files": names, "file_repairs": file_repairs}
    if names and agreed:
        result["delivery"] = selected_delivery
    return result


def first(task, run_dir=None, approve="never", members=2):
    with capping():
        return _first(task, run_dir, approve, members)


def _first(task, run_dir=None, approve="never", members=2):
    """The members' try, kept apart (<run>/members) so that the roles can take the task in <run> if they confirm
    nothing. Where they agree, their answer and the files they saved are the run's."""
    home = _home(run_dir)
    replaces_report = (home / "members" / "members.json").is_file() and (home / "REPORT.md").is_file()
    out = run(task, home / "members", approve, members)
    out.update(dir=str(home), files=[])
    if out["agreed"]:
        source = Path(out["work"])
        names = out["requested_files"]
        if names:
            # Check the staged bytes that will be published. A disappeared or changed
            # file cannot turn an already-written confirmation into a false delivery.
            try:
                with tempfile.TemporaryDirectory(dir=home) as tmp:
                    deliverables.copy_files(source, names, tmp)
                    if deliverables.inspect(task, tmp, names) != out["delivery"]:
                        raise ValueError("the selected files changed before delivery")
                    deliverables.copy_files(tmp, names, home / "work")
            except (ValueError, OSError) as e:
                out.update(agreed=False, file_repairs=[], report=f"Not confirmed: the requested files could not be delivered. {e}\n")
                # Training reads this decision from disk. An interrupted handoff must
                # not be counted later as a file the user received.
                path = home / "members" / "members.json"
                decision = json.loads(path.read_text())
                decision.update(agreed=False, agreeing=[], delivery_error=str(e))
                path.write_text(json.dumps(decision))
            else:
                out["files"] = list(names)
        else:
            (home / "work").mkdir(parents=True, exist_ok=True)
            for p in source.iterdir():
                if p.is_symlink() or not p.is_file() or p.name.startswith(".") or re.fullmatch(r"member\d+_\d+\.py|task_data(_\d+)?\.txt", p.name):
                    continue
                try:
                    deliverables.copy_files(source, [p.name], home / "work")
                except (ValueError, OSError):
                    continue
                out["files"].append(p.name)
    if out["agreed"] or replaces_report or (out.get("delivery") and not out["agreed"]):
        (home / "REPORT.md").write_text(out["report"])
    return out
