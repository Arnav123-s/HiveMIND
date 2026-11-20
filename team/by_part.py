"""A task of several parts (team/parts.py) worked part by part.

Seen in g53's practice: 28 of the 50 new-kind tasks were two kinds joined into 'PART A ... PART B ...'; 1 of the 28 was
right at the first try, and 15 of the 17 tasks cut off at the 600 s cap were such tasks. Each member spent its turns on
part A and the time ran out before any pair agreed on both parts. Worked as one program, a single slow or wrong part
loses the whole task, and a member can never be 'right with one program' unless one program does everything.

Here each part is sat as a task of its own (team/solo._run): its own members, its own seats (the cells that lean to
that part's kind), agreement on that part alone, and its own share of the time: what is left of the cap divided by the
parts not yet done, so time a quick part does not use goes to the next. The agreed answers are joined under the
headings the task asked for. Nothing is delivered that two members did not agree on, part by part: a part that no pair
agreed on leaves the whole task 'Not confirmed', as before.

The cap is told by the exam (HIVE_CAP_SECONDS, training/exam.sit_one). Without it there are no shares, only the order.
Members' files (member{n}.json, members.json, events.jsonl) are written in the shape the exam and the rows read: member
n's answer is its answers to the parts, joined; a member counts as 'right first try' (scripts/selfreliance.one) when it
ran one program per part and got no hint. HIVE_BY_PART=0 turns it off.
"""
import json
import os
import re
import shutil
import signal
import time
from pathlib import Path

from . import deliverables, parts as several
from .board import Board

MARGIN = 30  # seconds kept at the end of the cap to write the answer


def split(task):
    """{letter: part task} when the task is one of several parts and is to be worked part by part, else {}."""
    if os.environ.get("HIVE_BY_PART", "1") == "0":
        return {}
    p = several.of_task(task)
    return p if len(p) > 1 else {}


def shares(left, parts_left):
    """Seconds the next part may take: the time left divided by the parts left. None: no cap is known."""
    return None if left is None else max(5.0, left / max(1, parts_left))


def _copy_files(src, dst, only=None):
    dst.mkdir(parents=True, exist_ok=True)
    for f in Path(src).iterdir() if Path(src).is_dir() else []:
        if f.is_symlink() or not f.is_file() or f.name.startswith(".") or re.fullmatch(r"member\d+_\d+\.py|task_data(_\d+)?\.txt", f.name):
            continue
        if (only is None or f.name in only) and f.stat().st_size <= 5_000_000:
            shutil.copyfile(f, dst / f.name)


def run(task, home, approve, members, solo):
    """Same result as solo._run, for a task whose parts are split(task)."""
    home = Path(home)
    pieces = split(task)
    board = Board(home)
    board.goal = task
    (home / "TASK.md").write_text(task.strip() + "\n")
    cap = float(os.environ.get("HIVE_CAP_SECONDS") or 0) or None
    t0 = time.time()
    results = {}
    try:
        old_alarm = signal.signal(signal.SIGALRM, solo._on_share)
    except ValueError:  # not the main thread: no shares
        old_alarm = None
    try:
        for i, (letter, part) in enumerate(pieces.items()):
            if solo._CAP["term"]:
                board.log("hive", "capped", f"time cap reached before PART {letter}")
                break
            left = None if cap is None else cap - MARGIN - (time.time() - t0)
            share = shares(left, len(pieces) - i)
            solo._CAP["hit"] = False
            if share is not None and old_alarm is not None:
                signal.setitimer(signal.ITIMER_REAL, share)
            board.log("hive", "part", f"PART {letter}: {share and round(share)} s share")
            try:
                results[letter] = solo._run(part, home / f"part_{letter}", approve, members)
            finally:
                if old_alarm is not None:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                solo._CAP["hit"] = solo._CAP["term"]
    finally:
        if old_alarm is not None:
            signal.signal(signal.SIGALRM, old_alarm)
    letters = list(pieces)
    agreed = {k: r["answer"] for k, r in results.items() if r.get("agreed") and r.get("answer")}
    n_tries = max([r["tries"] for r in results.values()] + [0])
    # member n: its answers to the parts, joined, in the files the exam and the rows read
    answered = {}
    for n in range(1, n_tries + 1):
        mem = {}
        for k, r in results.items():
            f = Path(r["dir"]) / f"member{n}.json"
            if f.exists():
                mem[k] = json.loads(f.read_text())
        if not mem:
            continue
        keep = {k: t for k, t in mem.items() if t.get("answer")}
        answered[n] = keep
        wd = home / f"member{n}"
        for k, t in mem.items():
            if t.get("work"):
                _copy_files(t["work"], wd)
        first = next(iter(mem.values()))
        (home / f"member{n}.json").write_text(json.dumps({
            "who": first.get("who", ""), "work": str(wd), "messages": [],  # no rows from a joined program: the parts' own are in part_*
            "program": "\n\n".join(f"# PART {k}\n{t.get('program', '')}" for k, t in mem.items()),
            "turns": sum(t.get("turns", 0) or 0 for t in mem.values()),
            "answer": "\n\n".join(f"PART {k}\n{t['answer'].strip()}" for k, t in sorted(keep.items()))}))
    ok = len(agreed) == len(letters)
    work, delivery, names = home / "work", None, deliverables.wanted(task)
    if ok:
        work.mkdir(parents=True, exist_ok=True)
        for k, r in results.items():
            _copy_files(r["work"], work, set(r["requested_files"]) or None)
        if names:
            delivery = deliverables.inspect(task, work, names)
            if delivery["issues"]:
                ok = False
    # events in the form scripts/selfreliance.one reads: a member's runs beyond one per part, its hints, its answer
    for n, got in sorted(answered.items()):
        who = f"member{n}"
        extra, hinted = 0, False
        for k, r in results.items():
            ev = Path(r["dir"]) / "events.jsonl"
            mine = [json.loads(x) for x in ev.read_text().splitlines()] if ev.exists() else []
            mine = [e for e in mine if e.get("agent") == who]
            extra += max(0, sum(e["kind"] == "run" for e in mine) - 1)
            hinted = hinted or any(e["kind"] == "hint" for e in mine)
        board.log(who, "run", f"{len(got)} of {len(letters)} parts")
        for _ in range(extra):
            board.log(who, "run", "another program")
        if hinted:
            board.log(who, "hint", "a hint in a part")
        if len(got) == len(letters):
            board.log(who, "answer", got[letters[0]]["answer"][:300])
    if ok:
        text = "\n\n".join(f"PART {k}\n{agreed[k].strip()}" for k in letters)
        answer = text
        text += (f"\n\n## How it was checked\n- Worked part by part: {len(letters)} parts, each worked out by its own members "
                 f"({', '.join(str(r['tries']) for r in results.values())} tries); two gave the same values in every part.")
        if names:
            text += "\n- Reopened and checked the requested files: " + ", ".join(names) + "."
    else:
        answer = ""
        miss = [k for k in letters if k not in agreed]
        got = [f"PART {k}: " + (results[k]["report"].split("\n\n## ")[0].strip()[:300] if k in results else "not reached") for k in miss]
        text = ("Not confirmed: " + ("the hive could not select a complete file with an independently supported answer."
                                    if not miss else f"no two members agreed on PART {', '.join(miss)}.") + "\n\n" + "\n".join(got))
        if not any(r["tries"] for r in results.values()):
            text = "No member got as far as an answer. Their programs and what they printed are in this run's folder."
    text = text.strip() + "\n"
    (home / "REPORT.md").write_text(text)
    board.log("hive", "finished", f"report: {home / 'REPORT.md'}")
    agreeing = [n for n in answered if ok and all(
        k in answered[n] and solo.same(answered[n][k]["answer"], agreed[k], pieces[k]) for k in letters)]
    decision = {"agreed": ok, "who": [json.loads((home / f"member{n}.json").read_text())["who"] for n in sorted(answered)],
                "agreeing": agreeing, "by_part": {k: {"agreed": bool(v["agreed"]), "tries": v["tries"]} for k, v in results.items()}}
    if names:
        decision.update(requested_files=names, printed_agreeing=agreeing, file_repairs=[], selected_member=None)
    (home / "members.json").write_text(json.dumps(decision))
    out = {"dir": str(home), "report": text, "agreed": ok, "tries": n_tries, "pending_approvals": [],
           "work": str(work), "requested_files": names, "file_repairs": [], "answer": answer}
    for r in results.values():
        out["pending_approvals"] += list(r.get("pending_approvals") or [])
    if names and ok:
        out["delivery"] = delivery
    return out
