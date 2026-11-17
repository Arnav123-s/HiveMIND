"""Notes: short ways of working the hive wrote down from its own checked work, read again on tasks like it.

    python team/notes.py distill RUN_FOLDER [--kind KIND]     notes from one task's folder (or every task under it)
    python team/notes.py show [--kind KIND]                   the notes kept, most seen first

Why: a library of whole solved programs was tried on 12 Nov and lost: the members copied the old programs, values and
all, and agreed on them wrong (team/solo.alike, off). A note is not a program and holds no value. It is one line,
"When <what happened>, <what to do or not do>", written by rules from what the task's check and the runtime said:
the error a program died of, a timeout, an answer in the wrong form, a web source that sent a page (HTML) where JSON
was expected. Notes come from failures as well as from successes, and every digit is taken out, so a note can never
be copied as an answer.

Kept in cells/notes/notes.jsonl, one note per line: {kind, note, from (success|failure), seen, helped, when, words}.
The same note written again is counted (seen), not kept twice. A note shown to a member whose answer the check then
confirmed counts as having helped.

Read by team/solo.member only when HIVE_NOTES=1: up to three notes, by kind first, then by the words they share with
the task, as a short block "Notes from earlier work:" at the end of the member's orders.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

if __package__ in (None, ""):  # run as a file: python team/notes.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "team"

from .memory import words  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FILE = Path(os.environ.get("HIVE_NOTES_FILE", ROOT / "cells" / "notes" / "notes.jsonl"))
LONGEST = 200  # the most characters of one note
MOST = 2  # the most notes one task gives
HEAD = "Notes from earlier work:"

# The error a program died of -> (what happened, what to do). Only the error's name is read, never its message: the
# message can carry the task's values.
ERRORS = [
    ("JSONDecodeError", "a source's reply would not read as JSON", "print the start of response.text first; a web page is HTML, read it with BeautifulSoup"),
    ("KeyError", "a key was not in the data", "print the keys the data really has (look(data)) before reading one"),
    ("IndexError", "a list had fewer items than the program took", "check how many items there are before taking one by its place"),
    ("AttributeError", "an element or value was None", "check that find or select_one found something before using it"),
    ("TypeError", "a value had another type than expected", "print the value and its type just before the line that failed"),
    ("ValueError", "text would not turn into a number or date", "print the text first and strip units, commas and spaces before converting"),
    ("ZeroDivisionError", "a division by zero stopped the program", "check the count is not zero before dividing"),
    ("NameError", "a name was used that was never defined", "write one whole program that defines every name it uses"),
    ("SyntaxError", "the program would not even parse", "reply with one complete program in one code block and no prose inside it"),
    ("IndentationError", "the program would not even parse", "reply with one complete program in one code block and no prose inside it"),
    ("ModuleNotFoundError", "a module was not installed", "use the standard library, requests and bs4 only"),
    ("FileNotFoundError", "a file was read that was not there", "write the file the task names in the current folder before reading it"),
    ("UnicodeDecodeError", "a file or page would not decode", "read it with errors='ignore' or use response.text"),
    ("RecursionError", "the program recursed too deep", "use a loop in place of recursion"),
    ("ConnectionError", "a source could not be reached", "fetch the site's first page and follow its links; do not make an address up"),
    ("HTTPError", "a source answered with an error", "fetch the site's first page and follow its links; do not make an address up"),
]

# What the runtime told the member (team/solo.HINTS and its other messages) -> (what happened, what to do)
TOLD = [
    ("is a web page (HTML), not JSON", "a web source returned HTML instead of data", "read it with BeautifulSoup, not .json()"),
    ("there is no such page. Do not make an address up", "an address was made up and not found", "avoid guessing addresses; fetch the first page and follow its links"),
    ("the loop never moved to", "a list runs over several pages", "follow each page's next link until there is none"),
    ("holds no rows (at most a heading)", "a saved file held only its heading", "print what the page really holds before writing rows"),
    ("and it is not there. Reply with the complete", "the task names a file to save", "write it with open(name, 'w') in the current folder, then use it"),
    ("The program found nothing", "the program found nothing where the task says there is something", "print the first items it looks through to see their real shape"),
    ("The program printed a failure, not an answer", "a program caught its own error and printed it", "avoid printing caught errors as the answer; fix the step that failed"),
    ("MEMORY: the program used", "a program used too much memory", "read in pieces and avoid building huge lists"),
    ("TIMEOUT after", "a program ran out of time", "avoid long loops and sleeps; fetch only the pages needed and give every request a timeout"),
    ("does not exist (no such host)", "a host did not exist", "use only addresses the task gives or links found on its pages"),
    ("it has no headings", "a task has several parts", "print each part's heading alone on its own line before its answer"),
    ("The TASK asks for a numbered list", "the task asks for a numbered list", "print only the numbered lines, nothing else"),
    ("sentence(s). Your output has", "the task asks for a number of sentences", "print exactly as many sentences as asked"),
    ("The TASK asks for the answers labelled", "the task labels its answers", "print each answer on its own line after its label"),
    ("The TASK asks for lines that begin with", "the task names how lines begin", "begin each line the way the task says"),
]

# What a right program did that fits a kind of work -> (what the task was like, what worked). Read from the code.
WORKED = [
    (r"li\.next|['\"]next['\"]", r"urljoin", "a list runs over several pages", "follow each page's next link with urljoin until there is none"),
    (r"open\([^)]*\.py['\"],\s*['\"]w", r"^import |^from ", "the task asks for a module", "write the module file first, then import it and print each value"),
    (r"print\(\s*['\"]PART ", r"", "a task has several parts", "print each part's heading alone on its own line before its answer"),
    (r"csv\.writer|to_csv\(", r"", "the task asks for a CSV file", "write the heading and the rows with csv.writer, then print how many rows"),
    (r"BeautifulSoup", r"\.select|\.find", "the answer is on a web page", "fetch the page and select the elements by their CSS class with BeautifulSoup"),
    (r"datetime|date\(", r"strptime|timedelta|\.days", "the task counts days between dates", "parse the dates with datetime and subtract them"),
]


def plain(text):
    """A note with no digit in it and no doubled spaces, at most LONGEST characters."""
    text = re.sub(r"\s+", " ", re.sub(r"\d", "", text or "")).strip()
    return text[:LONGEST].rstrip()


def key(text):
    """What two notes that say the same thing have in common: their words, small letters, no digits."""
    return " ".join(re.findall(r"[a-z]+", plain(text).lower()))


def say(situation, advice):
    return plain(f"When {situation}, {advice}.")


# ---- what one task's work says ---------------------------------------------------------------------------------------
def _tries(source):
    """The members' tries of one task and what is known of it: (tries, ok, note, task). source: a task's folder, or a
    list of tries (dicts as member{n}.json holds them, each with "ok" where the check's verdict is known; a record of
    failures.jsonl, with "program", "printed" and "said", counts as one failed try)."""
    if not isinstance(source, (str, Path)):
        tries = [dict(t) for t in source or [] if isinstance(t, dict)]
        for t in tries:
            if "said" in t and "ok" not in t:  # a remembered failure (training/grow.remember_failure)
                t.update(ok=False, answer=t.get("printed", ""))
        task = next((t.get("task") for t in tries if t.get("task")), "")
        return tries, any(t.get("ok") for t in tries), "", task
    from training import grow
    run = Path(source)
    home = grow._home(run)
    try:
        exam = json.loads((run / "exam.json").read_text())
    except (OSError, ValueError):
        exam = {}
    exam = exam if isinstance(exam, dict) else {}
    right = set(grow.taught(run, home))
    tries = []
    for f in sorted(home.glob("member[0-9]*.json"), key=grow._number):
        try:
            t = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(t, dict):
            tries.append(t | {"ok": grow._number(f) in right})
    task = (run / "TASK.md").read_text().strip() if (run / "TASK.md").exists() else exam.get("task", "")
    return tries, bool(exam.get("ok")) or any(t["ok"] for t in tries), " ".join(str(exam.get(k) or "") for k in ("note", "why")), task


def _told(t):
    """Everything the member was told back (outputs, errors, the runtime's hints) as one text."""
    said = [m.get("content", "") for m in (t.get("messages") or [])[2:] if isinstance(m, dict) and m.get("role") == "user"]
    return "\n".join(said + [str(t.get("printed") or ""), str(t.get("said") or "")])


def _errors(text):
    """The names of the errors in a text, as ERRORS knows them, the first seen first."""
    seen = []
    for m in re.finditer(r"\b([A-Z]\w*(?:Error|Exception))\b", text):
        name = m.group(1)
        if name.endswith("JSONDecodeError"):
            name = "JSONDecodeError"
        if any(name == e for e, _, _ in ERRORS) and name not in seen:
            seen.append(name)
    return seen


def failure_notes(t, note=""):
    """Notes from what went wrong in one try: the runtime's own messages first (they say most), then errors."""
    text = _told(t) + "\n" + (note or "")
    out = [say(s, a) for mark, s, a in TOLD if mark in text]
    if re.search(r"timed out after", note or ""):
        out.append(say("a task ran out of time", "write one short program early and fetch only the pages needed"))
    out += [say(s, a) for e, s, a in ERRORS if e in _errors(text)]
    return out


def success_notes(t):
    """Notes from a right try: what the right program did that fits its kind of work, and what it got past."""
    code = t.get("program") or ""
    out = [say(s, a) for first, then, s, a in WORKED if re.search(first, code) and re.search(then, code, re.M)]
    got_past = failure_notes(t)
    return got_past[:1] + out


def distill(source, kind=""):
    """At most MOST short notes from the checked work of one task (its folder, or its tries): one from what failed,
    one from what worked. Written by rules, not by a model; no digit in any of them."""
    tries, ok, note, _ = _tries(source)
    failed, right = [], []
    for t in tries:
        if t.get("ok"):
            right += [(x, "success") for x in success_notes(t)]
        else:
            failed += [(x, "failure") for x in failure_notes(t, note)]
    if not tries and note:
        failed += [(x, "failure") for x in failure_notes({}, note)]
    # the most common failure first: what went wrong for most members is what the next members most need to hear
    counts = {}
    for x, _ in failed:
        counts[x] = counts.get(x, 0) + 1
    failed.sort(key=lambda p: -counts[p[0]])
    out, keys = [], set()
    for x, src in failed[:1] + right[:1] + failed[1:] + right[1:]:
        if x and key(x) not in keys and len(out) < MOST:
            keys.add(key(x))
            out.append({"kind": kind or "", "note": x, "from": src})
    return out


# ---- the store -------------------------------------------------------------------------------------------------------
def read(path=None):
    path = Path(path or FILE)
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            x = json.loads(line)
        except ValueError:
            continue
        if isinstance(x, dict) and x.get("note"):
            out.append(x)
    return out


def _write(rows, path=None):
    path = Path(path or FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def keep(notes, task="", path=None):
    """Add notes to the store. A note already there (same kind, same words) is counted again (seen), not added."""
    rows = read(path)
    at = {(r.get("kind", ""), key(r["note"])): r for r in rows}
    near = sorted(w for w in words(plain(task)) if not re.search(r"\d", w))[:30]
    for n in notes:
        k = (n.get("kind", ""), key(n["note"]))
        if k in at:
            r = at[k]
            r["seen"] = r.get("seen", 1) + 1
            r["when"] = time.strftime("%Y-%m-%d %H:%M")
            r["words"] = sorted(set(r.get("words", [])) | set(near))[:60]
            if n.get("from") == "success":
                r["from"] = "success" if r.get("from") == "success" else r.get("from", "failure")
        else:
            r = {"kind": n.get("kind", ""), "note": plain(n["note"]), "from": n.get("from", "failure"), "seen": 1,
                 "helped": 0, "when": time.strftime("%Y-%m-%d %H:%M"), "words": near}
            rows.append(r)
            at[k] = r
    _write(rows, path)
    return rows


def shown(tries):
    """The notes that were in the orders of these tries: the lines under HEAD in their first message."""
    out = []
    for t in tries:
        ms = t.get("messages") or []
        first = ms[0].get("content", "") if ms and isinstance(ms[0], dict) else ""
        if HEAD in first:
            out.append((t, [x[2:].strip() for x in first.split(HEAD, 1)[1].splitlines() if x.startswith("- ")]))
    return out


def learn(source, kind="", path=None):
    """distill, keep, and count as having helped every note a confirmed member was shown. Returns the new notes."""
    tries, _, _, task = _tries(source)
    made = distill(source, kind)
    rows = keep(made, task, path)
    helped = {key(x) for t, xs in shown(tries) if t.get("ok") for x in xs}
    if helped:
        for r in rows:
            if key(r["note"]) in helped:
                r["helped"] = r.get("helped", 0) + 1
        _write(rows, path)
    return made


def recall(task, kind=None, most=3, path=None):
    """Up to `most` notes for a task: those of its kind first, then by how many words they share with it (the note's
    own words and those of the tasks it came from), then by how often they were seen and helped."""
    tw = words(task)
    scored = []
    for r in read(path):
        same = bool(kind) and r.get("kind") == kind
        overlap = len(tw & (words(r["note"]) | set(r.get("words", []))))
        if not same and not overlap:
            continue
        scored.append((same, overlap, r.get("helped", 0), r.get("seen", 1), r["note"]))
    scored.sort(key=lambda s: s[:4], reverse=True)
    out = []
    for s in scored:
        if s[4] not in out:
            out.append(s[4])
    return out[:most]


def block(notes):
    """The notes as they are put in a member's orders."""
    return f"\n\n{HEAD}\n" + "\n".join(f"- {plain(x)}" for x in notes) if notes else ""


# ---- by hand ---------------------------------------------------------------------------------------------------------
def _folders(run):
    """The task folders under a folder: itself when it holds members' files, else every folder with an exam.json."""
    run = Path(run)
    if list(run.glob("member[0-9]*.json")) or (run / "members").is_dir():
        return [run]
    return sorted({p.parent for p in run.rglob("exam.json")})


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="the hive's notes from its own checked work")
    sub = p.add_subparsers(dest="what", required=True)
    d = sub.add_parser("distill", help="notes from a task's folder, or every task folder under it")
    d.add_argument("run")
    d.add_argument("--kind", default="")
    s = sub.add_parser("show", help="the notes kept")
    s.add_argument("--kind", default="")
    a = p.parse_args(argv)
    if a.what == "distill":
        for f in _folders(a.run):
            kind = a.kind
            if not kind:
                try:
                    kind = json.loads((f / "exam.json").read_text()).get("kind", "")
                except (OSError, ValueError, AttributeError):
                    kind = ""
            for n in learn(f, kind):
                print(f"[{n['from']}] {n['kind'] or '-'}: {n['note']}")
        return 0
    rows = [r for r in read() if not a.kind or r.get("kind") == a.kind]
    for r in sorted(rows, key=lambda r: (-r.get("seen", 1), -r.get("helped", 0))):
        print(f"{r.get('seen', 1):>3} seen {r.get('helped', 0):>3} helped  [{r.get('from')}] {r.get('kind') or '-'}: {r['note']}")
    if not rows:
        print("no notes yet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
