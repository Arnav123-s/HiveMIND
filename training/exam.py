"""A fresh exam for the working hive, made by code and checked by code.

Every sitting has new tasks of the same kinds: sums, dates, units, small tables, programs to write and to mend,
facts read live from a source, a website to operate, a file to make, instructions to follow to the letter, things to
know, sentences to translate, a text to sum up. The tasks are drawn from a seed (by default the day), every answer is
checked in code against a value worked out here or read live from the source, nobody wrote them to suit the hive and
no fix was ever tried on them. So the pass rate of a sitting is an honest number, and sat again and again it shows
whether the hive is getting better, field by field, with nobody there to see.

    python training/exam.py show [--seed N] [--level hard]   the tasks of a sitting, without running them
    python training/exam.py sit [--seed N] [--tasks 16] [--only FIELD ...] [--empty-memory] [--level hard]
                                                       sit it: every task goes through the whole hive
                                                       (python -m team, risky actions never). Writes
                                                       training/reports/exams/<seed>.json and .md and one line
                                                       in training/reports/exams.jsonl
    python training/exam.py held [--seat 1 --seats 8] [--per 3]
                                                       the fixed held-out exam (held_exam): the same tasks every
                                                       generation, 3 of each kind never practised, with no memory;
                                                       a seat sits its share (every 8th task) and writes
                                                       training/reports/exams/held_<seat>.json after every task
    python training/exam.py practice [--tasks 16] [--members 2]
                                                       fresh tasks that are never an exam's, done by the members
                                                       (team/solo.py) with the hive's real memory: a program two
                                                       members agreed on and the task's check confirmed stays in
                                                       the hive's library, for the next task like it
The hive sits the exam with what it has learned (a copy of its memory, so a sitting cannot change it);
--empty-memory: with none.
"""
import datetime
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from training import hive_bench as B  # noqa: E402

OUT = ROOT / "training" / "reports" / "exams"
RECORD = ROOT / "training" / "reports" / "exams.jsonl"
RUNS = ROOT / "runs" / "exam"


# ---- the kinds: each in a file of its own (training/kinds/, docs/KINDS.md), found there by the registry ------------------
# The old names stay here, so what imported them from this module still finds them.
from training import kinds  # noqa: E402
from training.kinds._common import CAPITALS, MONTHS, NAMES, _json_in, _line_says, _nums, every, says  # noqa: E402,F401
from training.kinds.m_born import AUTHORS, m_born  # noqa: E402,F401
from training.kinds.m_code import m_code  # noqa: E402,F401
from training.kinds.m_csv import CATEGORIES, m_csv  # noqa: E402,F401
from training.kinds.m_days import m_days  # noqa: E402,F401
from training.kinds.m_fix import m_fix  # noqa: E402,F401
from training.kinds.m_follow import LISTS, OPPOSITES, m_follow  # noqa: E402,F401
from training.kinds.m_know import ELEMENTS, m_know  # noqa: E402,F401
from training.kinds.m_licence import MODELS, m_licence  # noqa: E402,F401
from training.kinds.m_percent import THINGS, m_percent  # noqa: E402,F401
from training.kinds.m_pypi import PACKAGES, m_pypi  # noqa: E402,F401
from training.kinds.m_steps import m_steps  # noqa: E402,F401
from training.kinds.m_summary import m_summary  # noqa: E402,F401
from training.kinds.m_table import DAYS, m_table  # noqa: E402,F401
from training.kinds.m_translate import TONGUES, m_translate  # noqa: E402,F401
from training.kinds.m_units import m_units  # noqa: E402,F401
from training.kinds.m_weekday import m_weekday  # noqa: E402,F401

# the first exam's makers, in the order its seed shuffles them (a kind with COPIES = 2 twice)
MAKERS = kinds.makers(hard=False)


LEVELED = kinds.LEVELED  # the kinds whose own difficulty can be raised
MOST_LEVEL, MOST_PARTS = 4, 6


def _made(make, rseed, level=0):
    """A task from its maker, the seed it was drawn with and how hard it is to be (0: as the exams make it); the
    check remembers all three, so the task can be made again later exactly (training/grow.dream: the hive goes back
    to what it got wrong)."""
    r = random.Random(rseed)
    r.level = int(level) if make.__name__ in LEVELED else 0
    field, kind, task, check = make(r)
    try:
        check.maker, check.rseed, check.level = make.__name__, rseed, r.level
    except AttributeError:
        pass
    return field, kind, task, check


def _together(made, rseed):
    """Several tasks as one message (team/parts.py). Each part is checked on the answer's piece under its own
    heading, by its own check; the whole is right when every part is."""
    from team import parts
    checks = [c for *_, c in made]

    def check(run, report):
        pieces, res = parts.of_answer(B._body(report)), []
        for i, c in enumerate(checks):
            piece = pieces.get(parts.LETTERS[i])
            if piece is None:
                res.append((False, "no such heading in the answer"))
                continue
            try:
                res.append(c(run, piece))
            except Exception as e:  # noqa: BLE001 - a check that cannot be made is a failed part, with the reason
                res.append((False, f"check failed: {type(e).__name__}: {e}"))
        return all(ok for ok, _ in res), "; ".join(f"PART {parts.LETTERS[i]} {'right' if ok else 'not right'}: {why}" for i, (ok, why) in enumerate(res))
    check.maker, check.rseed, check.level = "compound", rseed, len(made)
    check.parts = [[getattr(c, "maker", ""), getattr(c, "rseed", ""), getattr(c, "level", 0)] for c in checks]
    return "several", "several tasks in one", parts.join([t for _, _, t, _ in made]), check


def compound(rseed, k, makers, levels=None):
    """One task made of k tasks of different kinds: the way the body's lessons grow harder. A program that does
    two or three different things at once cannot be one remembered answer."""
    pool = list(dict.fromkeys(makers))
    r = random.Random(f"{rseed}:parts")
    chosen = r.sample(pool, min(k, len(pool)))
    return _together([_made(m, f"{rseed}:{m.__name__}:{i}", (levels or {}).get(m.__name__, 0)) for i, m in enumerate(chosen)], rseed)


def remake(maker, rseed, level=0, parts=None):
    """The task a maker drew with this seed and level: (field, kind, task, check), or None for a maker this code does
    not have. A task of several parts is made again from its parts."""
    from training import exam_hard
    if maker == "compound":
        made = [remake(*p[:3]) for p in parts or [] if isinstance(p, (list, tuple)) and len(p) >= 2 and p[0] != "compound"]
        return _together(made, rseed) if len(made) >= 2 and all(made) and len(made) == len(parts) else None
    make = next((m for m in MAKERS + exam_hard.MAKERS if m.__name__ == maker), None)
    return _made(make, rseed, level if isinstance(level, int) else 0) if make else None


def exam(seed, n=16, only=(), level="basic", without=(), weights=None, levels=None):
    """The tasks of one sitting: [(id, field, kind, task, check)]. The same seed gives the same exam.
    level "hard": the kinds of several steps (training/exam_hard.py). without: makers left out by name (practice
    leaves out the kinds the hive is never to practise on).
    level "ladder" (for practice, not for exams): half single tasks, each kind as hard as `levels` {maker: level}
    says, and half tasks of several parts, as many parts as levels["compound"] says (2 at first). The record of a
    generation raises a level the body passes mostly and lowers one it mostly fails (training/grow_record.py), so
    the lessons stay at the edge of what the body can do.
    level "edge" (for practice, not for exams): tasks of every kind, drawn by `weights` {kind: weight}, so the hive
    practises most where it is at the edge of what it can do (training/grow.edge_weights)."""
    if level == "mixed":  # half of each: what the hive can mostly do, and what it mostly cannot yet
        return exam(seed, n - n // 2, only, "basic", without) + exam(seed, n // 2, only, "hard", without)
    if level == "ladder":
        from training import exam_hard
        lv = levels or {}
        single = n - n // 2
        if weights:  # the single tasks drawn where the body's exams say it is at its edge (training/progress.py draws why)
            out = exam(seed, single, only, "edge", without, weights=weights, levels=lv)
        else:
            out = exam(seed, single - single // 2, only, "basic", without, levels=lv) + exam(seed, single // 2, only, "hard", without, levels=lv)
        pool = [m for m in MAKERS + exam_hard.MAKERS if m.__name__ not in without]
        k = max(2, min(MOST_PARTS, int(lv.get("compound", 2) or 2)))
        for i in range(n // 2):
            field, kind, task, check = compound(f"{seed}:several:{i}", k, pool, lv)
            out.append((f"c{seed}_{i:02d}", field, kind, task, check))
        return out
    if level == "edge":
        from training import exam_hard
        makers = [(m, "e") for m in MAKERS if m.__name__ not in without] + [(m, "h") for m in exam_hard.MAKERS if m.__name__ not in without]
        r = random.Random(f"{seed}:edge")
        hard = levels or {}  # how hard each kind is to be, as the ladder has it (0 where it has no level)
        tried = [(i, make, lv) + tuple(_made(make, f"{seed}:{make.__name__}:{i}:0", hard.get(make.__name__, 0))) for i, (make, lv) in enumerate(makers)]
        # a kind nobody has measured yet counts as if passed half the time (the most to learn)
        w = [max(1e-3, (weights or {}).get(t[4], 0.25)) for t in tried]
        out, used = [], {}
        for pick in r.choices(range(len(tried)), weights=w, k=n * 3):
            i, make, lv, field, kind, task, check = tried[pick]
            again = used.get(i, 0)
            if again:
                field, kind, task, check = _made(make, f"{seed}:{make.__name__}:{i}:{again}", hard.get(make.__name__, 0))
            used[i] = again + 1
            if task in [t[3] for t in out] or (only and field not in only):
                continue
            out.append((f"{lv}{seed}_{len(out):02d}", field, kind, task, check))
            if len(out) >= n:
                break
        return out
    r = random.Random(seed)
    if level == "hard":
        from training import exam_hard
        makers = [m for m in exam_hard.MAKERS if m.__name__ not in without]
    else:
        makers = [m for m in MAKERS if m.__name__ not in without]
    r.shuffle(makers)
    out = []
    for i, make in enumerate(makers):
        for again in range(8):  # the same task twice in one sitting tells nothing: drawn again
            field, kind, task, check = _made(make, f"{seed}:{make.__name__}:{i}:{again}", (levels or {}).get(make.__name__, 0))
            if task not in [t[3] for t in out]:
                break
        if only and field not in only:
            continue
        out.append((f"{'h' if level == 'hard' else 'e'}{seed}_{len(out):02d}", field, kind, task, check))
        if len(out) >= n:
            break
    return out


# ---- the fixed held-out exam -----------------------------------------------------------------------------------------
# The pulse (a fresh mixed exam each generation) draws only 3 to 9 tasks of the held-out kinds (g43 0 of 6, g44 0 of 3,
# g45 0 of 9), which is noise. This exam is the same every generation, so generations compare: HELD_PER tasks of each
# held-out kind (training/kinds HELD_OUT), each drawn from a seed made of the kind's name and its number alone.
# Its ids begin with x (the pulse's with e, h or c); it is never trained on, as practice leaves these kinds out.
HELD_PER = 3


def held_exam(per=HELD_PER):
    """The fixed held-out exam: [(id, field, kind, task, check)], per tasks of each held-out kind, the kinds in the
    order of their names; the same tasks every time it is made (no seed of the day, the run or the generation)."""
    out = []
    for name in sorted(kinds.HELD_OUT):
        make = kinds.get(name).make
        for i in range(per):
            for again in range(8):  # the same task twice tells nothing: drawn again, still from fixed seeds
                field, kind, task, check = _made(make, f"held:{name}:{i}" + (f":{again}" if again else ""))
                if task not in [t[3] for t in out]:
                    break
            out.append((f"x_{name}_{i}", field, kind, task, check))  # by the kind's name: a kind added later moves no id
    return out


def held_share(tasks, seat=1, seats=1):
    """The tasks one seat of `seats` sits: every seats-th, from its own place (seat 1 to seats)."""
    return list(tasks)[max(0, seat - 1)::max(1, seats)]


def sit_held(seat=1, seats=1, per=HELD_PER, log=print, out=None, seconds=None):
    """A seat's share of the fixed held-out exam, sat as the pulse is (each task through the whole hive, with no
    memory). The json (training/reports/exams/held_<seat>.json) is written after every task, so a seat cut off by its
    time still leaves what it sat; the record compares only the tasks both arms sat."""
    tag, home, rows, t0 = f"exam_held_{seat}", _memory(True), [], time.time()
    path = Path(out or OUT) / f"held_{seat}.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    def save():
        line = {"exam": "held", "seat": seat, "seats": seats, "per": per, "passed": sum(r["ok"] for r in rows), "tasks": len(rows),
                "minutes": round((time.time() - t0) / 60), "memory": "none",
                "members": os.environ.get("HIVE_MEMBERS") or os.environ.get("AGENT_TEAM_SOLO", "")}
        path.write_text(json.dumps({"summary": line, "tasks": rows}, indent=1))
        return line
    line = save()
    for tid, field, kind, task, check in held_share(held_exam(per), seat, seats):
        r = sit_one(tag, tid, task, check, home, timeout=seconds, kind=kind) | {"field": field, "kind": kind, "maker": getattr(check, "maker", ""), "task": task}
        rows.append(r)
        line = save()
        log(f"{'PASS' if r['ok'] else 'FAIL'} {tid} [{r['maker']}: {kind}] {r['seconds']}s - {r['why']} {r['note']}", flush=True)
    return line


# ---- sitting it ------------------------------------------------------------------------------------------------------
def _memory(empty):
    """Where the hive's memory is for a sitting: a copy of what it has learned (lessons, policy, profile), so a
    sitting cannot change it; or nothing."""
    home = Path(tempfile.mkdtemp(prefix="exam-memory-"))
    if not empty:
        from team import memory
        for name in ("lessons.jsonl", "policy.json", "profile.md", "solved.jsonl"):
            if (memory.HOME / name).exists():
                shutil.copyfile(memory.HOME / name, home / name)
    return home


def run_task(cmd, timeout, **kw):
    """(exit code, stderr) of one task run, (None, stderr) when it ran out of time. A task out of time is ended with
    every process it started, the members' servers aside (they serve the next task). Before, only the task itself was
    killed: the program it was running lives in a session of its own (team/tools/sandbox.py), so it lived on, and the
    watch that holds a program to its time and its memory had died with the task. In trial run 32's exam a task ran
    out of time, the member's server stopped answering soon after, and GitHub shut the runner down; generation 28's
    practice runner 4 was shut down after three tasks in a row had run out of time."""
    import psutil
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kw)
    try:
        _, err = p.communicate(timeout=timeout)
        return p.returncode, err
    except subprocess.TimeoutExpired:
        try:
            started = psutil.Process(p.pid).children(recursive=True)  # read before the task ends: then they are no one's
        except psutil.Error:
            started = []
        p.kill()
        for c in started:
            try:
                if "llama-server" not in c.name():
                    c.kill()
            except psutil.Error:
                pass
        _, err = p.communicate()
        return None, err


def sit_one(tag, tid, task, check, memory_home, timeout=None, kind=""):
    timeout = timeout or int(os.environ.get("HIVE_TASK_SECONDS", 2400))  # the most one task may take
    run = RUNS / tag / tid
    if (run / "exam.json").exists():
        return json.loads((run / "exam.json").read_text())
    run.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    code, err = run_task([sys.executable, "-m", "team", task, "--approve", "never", "--run-dir", str(run)], timeout, cwd=ROOT,
                         env=dict(os.environ, AGENT_TEAM_HOME=str(memory_home), HIVE_KIND=kind))
    if code is None:
        note = f"timed out after {timeout} s"
    else:
        note = "" if code == 0 else f"exit {code}: {err.strip().splitlines()[-1][:200] if err.strip() else ''}"
    # a member's server that died or stopped answering and was started again (team/ternary.py) says so here, in the job's log
    note += "".join(f"; {line.strip()[:240]}" for line in err.splitlines() if line.startswith("ternary: the server"))
    report = (run / "REPORT.md").read_text() if (run / "REPORT.md").exists() else ""
    try:
        ok, why = check(run, report)
    except Exception as e:  # noqa: BLE001 - a check that cannot be made is a failed task, with the reason
        ok, why = False, f"check failed: {type(e).__name__}: {e}"
    res = {"id": tid, "ok": bool(ok), "why": why, "seconds": round(time.time() - t0), "note": note, "answer": B._body(report)[:400]}
    res["members"] = each_member(run, check)
    (run / "exam.json").write_text(json.dumps(res, indent=1))
    return res


def each_member(run, check):
    """Every member's own answer put to the task's check: [{"who", "ok", "member"}]. The hive's answer says how the body did;
    this says which cell is right on which kind of task, exactly, so the body can seat a task with the cells whose
    strengths lie nearest to it (team/ternary.seating, cells/strengths.json)."""
    import shutil
    import tempfile
    home = run / "members"
    out = []
    for f in sorted(home.glob("member[0-9]*.json")) if home.exists() else []:
        try:
            t = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(t, dict) or not t.get("who"):
            continue
        ok = False
        if t.get("answer"):
            with tempfile.TemporaryDirectory() as tmp:
                # a member with no work folder has none to copy: Path("") is the current folder (the whole checkout)
                work = Path(t["work"]) if t.get("work") else None
                if work and work.is_dir():
                    shutil.copytree(work, Path(tmp) / "work", ignore=lambda d, names: [n for n in names if (Path(d) / n).is_file() and (Path(d) / n).stat().st_size > 5_000_000])
                try:
                    ok = bool(check(Path(tmp), t["answer"])[0])
                except Exception:  # noqa: BLE001 - a check that cannot be made on one member's answer counts as not right
                    ok = False
        # member: the number of its member{n}.json, so each verdict is tied to the file it was made on (training/grow
        # teaches the members the check confirmed); the order of this list is the files' sorted names, not their numbers
        out.append({"who": str(t["who"])[:80], "ok": ok, "member": int(re.sub(r"\D", "", f.stem))})
    return out


def sit(seed, n=16, only=(), empty_memory=False, log=print, level="basic"):
    name = str(seed) if level == "basic" else f"{seed}_{level}"
    tag, home, rows, t0 = f"exam_{name}", _memory(empty_memory), [], time.time()
    for tid, field, kind, task, check in exam(seed, n, only, level):
        r = sit_one(tag, tid, task, check, home, kind=kind) | {"field": field, "kind": kind, "task": task}
        rows.append(r)
        log(f"{'PASS' if r['ok'] else 'FAIL'} {tid} [{field}: {kind}] {r['seconds']}s - {r['why']} {r['note']}", flush=True)
    by = {}
    for r in rows:
        p, m = by.get(r["field"], (0, 0))
        by[r["field"]] = (p + r["ok"], m + 1)
    try:
        code = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        code = ""
    line = {"seed": seed, "when": time.strftime("%Y-%m-%d %H:%M"), "passed": sum(r["ok"] for r in rows), "tasks": len(rows),
            "by_field": {k: list(v) for k, v in sorted(by.items())}, "minutes": round((time.time() - t0) / 60), "code": code,
            "memory": "none" if empty_memory else "its own", "level": level,
            "members": os.environ.get("HIVE_MEMBERS") or os.environ.get("AGENT_TEAM_SOLO", "")}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps({"summary": line, "tasks": rows}, indent=1))
    md = [f"# The hive's exam {seed}{'' if level == 'basic' else f' ({level})'}", "", f"{line['passed']} of {line['tasks']} tasks passed in {line['minutes']} minutes "
          f"(code {code}, memory: {line['memory']}).", "", "| field | kind | pass | time | the check |", "|---|---|---|---|---|"]
    md += [f"| {r['field']} | {r['kind']} | {'✅' if r['ok'] else '❌'} | {r['seconds']} s | {r['why']} {r['note']} |" for r in rows]
    (OUT / f"{name}.md").write_text("\n".join(md) + "\n")
    with open(RECORD, "a") as f:
        f.write(json.dumps(line) + "\n")
    return line


def practice(seed, n=16, only=(), members=2, log=print):
    """Practice: fresh tasks that are never an exam's (their seeds start at ten million), done by the members with the
    hive's real memory, so what two members agree on stays in its library (team/solo.py); then each task's own check
    says whether that program was right, and a wrong one is taken out again. Nothing is written to the exam's record."""
    from team import memory, solo
    tag, rows = f"practice_{seed}", []
    os.environ["AGENT_TEAM_SOLO"] = str(members)
    had = len(solo.solved())
    for tid, field, kind, task, check in exam(seed, n, only):
        r = sit_one(tag, tid, task, check, memory.HOME)
        # A helper-sorted delivery saved no member program. Its grade belongs
        # to the delivered file, so it cannot judge an older row for this task.
        try:
            receipt = json.loads((RUNS / tag / tid / "members" / "members.json").read_text())
        except FileNotFoundError:
            receipt = {}  # older practice runs may have no receipt
        except (ValueError, OSError):
            receipt = None
        if isinstance(receipt, dict) and not receipt.get("file_repairs"):
            solo.judge(task, r["ok"])
        rows.append(r)
        log(f"{'RIGHT' if r['ok'] else 'not right'} {tid} [{field}: {kind}] {r['seconds']}s", flush=True)
    now = solo.solved()
    return {"practice": seed, "tasks": len(rows), "right": sum(r["ok"] for r in rows), "library_before": had, "library_now": len(now),
            "confirmed_in_library": sum(bool(x.get("checked")) for x in now)}


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    seed = opt("--seed", (datetime.date.today() - datetime.date(2026, 1, 1)).days)
    only = tuple(argv[argv.index("--only") + 1:]) if "--only" in argv else ()
    only = tuple(a for a in only if not a.startswith("--"))
    cmd = argv[0] if argv else ""
    if cmd == "show":
        level = opt("--level", "basic")
        shown = held_exam(opt("--per", HELD_PER)) if level == "held" else exam(seed, opt("--tasks", 16), only, level)
        for tid, field, kind, task, _ in shown:
            print(f"{tid} [{field}: {kind}]\n    {task}\n")
    elif cmd == "practice":
        print(json.dumps(practice(opt("--seed", 10_000_000 + int(time.time() // 3600)), opt("--tasks", 16), only, opt("--members", 2))))
    elif cmd == "held":
        print(json.dumps(sit_held(opt("--seat", 1), opt("--seats", 1), opt("--per", HELD_PER), seconds=opt("--seconds", 0) or None)))
    elif cmd == "sit":
        print(json.dumps(sit(seed, opt("--tasks", 16), only, "--empty-memory" in argv, level=opt("--level", "basic"))))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
