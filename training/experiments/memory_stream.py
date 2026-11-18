"""Does each of the hive's memories help? One stream of tasks, done by the body's DNA with each memory on alone and all
together, before any of them is switched on for real.

    python training/experiments/memory_stream.py [--seed 32000] [--rounds 4] [--who t17] [--arms off,notes,cell,hive,all]
                                                 [--seen 6] [--unseen 4] [--task-seconds 600]

The stream: in every round one fresh task of each SEEN kind (new values every round, the order shuffled), and from
round 3 on, tasks of UNSEEN kinds: each such kind comes once, so nothing in memory was ever of its kind. Same-kind tasks
ask whether a memory helps; unseen-kind tasks ask whether it hurts (a memory of other work pulling an answer off,
values copied from it).

The arms, each with its own memory folders (tmp dirs) and the same tasks in the same order:
    off     no memory
    notes   team/notes.py (HIVE_NOTES=1): after every task, notes.learn() on its folder (failures too)
    cell    team/engram.py (HIVE_ENGRAMS=1): after every task the check confirms, an engram is written for the member
            the check confirmed (cell=its name); later tasks recall the engrams of tasks like them
    hive    training/hive_engram.py: after every round, update() with that round's checked rows; recalled last
    all     notes, cell engrams and the hive engram together
    short   no memory, but the short orders (HIVE_SHORT_ORDERS=1) that a member gets whenever an engram is on: the
            control that tells what an engram does from what the shorter orders do

Recorded per task: right or not, seconds, what was recalled, and for a wrong answer whether it repeats a value of a
recalled task (its text or its answer) that the task itself does not hold: copying. The same test against every
earlier confirmed task, in every arm, is the baseline of values that repeat by chance.
Result: training/experiments/memory_stream_<seed>.json.
"""
import json
import os
import random
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from training import exam as E  # noqa: E402
from training import exam_hard as H  # noqa: E402

SEEN = ["m_percent", "m_days", "m_units", "m_table", "m_code", "m_fix", "m_weekday", "m_steps"]
UNSEEN = ["m_know", "h_join", "m_follow", "h_log", "m_weekday", "m_steps"]  # all made offline; the first not in SEEN are used
ARMS = ("off", "notes", "cell", "hive", "all", "short")
DAYS = r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"


def maker(name):
    return next(m for m in E.MAKERS + H.MAKERS if m.__name__ == name)


def stream(seed, rounds, seen, unseen):
    """[(round, id, maker, kind, task, check, "seen"|"unseen")]: the same for every arm. Unseen kinds come from round 3
    on (round 2 too when there are more of them than later rounds can hold two each)."""
    later = list(range(3, rounds + 1)) or [rounds]
    spots = {r: [] for r in range(1, rounds + 1)}
    for i, name in enumerate(unseen):
        spots[later[i % len(later)]].append(name)
    out = []
    for r in range(1, rounds + 1):
        todo = [(n, "seen") for n in seen] + [(n, "unseen") for n in spots[r]]
        random.Random(f"{seed}:{r}:order").shuffle(todo)
        for i, (name, which) in enumerate(todo):
            field, kind, task, check = E._made(maker(name), f"{seed}:{r}:{name}")
            out.append((r, f"r{r}_{i:02d}_{name}", name, kind, task, check, which))
    return out


def values(text):
    """The values an answer or a task holds: numbers (commas out, trailing zeros of decimals out) and weekday names."""
    text = (text or "").lower()
    out = set()
    for m in re.findall(r"-?\d[\d,]*(?:\.\d+)?", text):
        v = m.replace(",", "")
        if "." in v:
            v = v.rstrip("0").rstrip(".")
        out.add(v)
    return out | set(re.findall(DAYS, text))


def distinctive(v):
    """A value that repeats by chance rarely: not a one-digit number."""
    return not re.fullmatch(r"-?\d", v)


def copied(answer, task, sources):
    """The values of a wrong answer that come from these earlier tasks (their texts or answers) and not from this task."""
    mine, here = values(answer), values(task)
    theirs = set().union(*[values(s["task"]) | values(s["answer"]) for s in sources]) if sources else set()
    return sorted(v for v in mine & theirs if v not in here and distinctive(v))


def recalled_of(run):
    """The engrams the first member recalled (the hive's log of the task), [] for none."""
    for ev in (run / "members" / "events.jsonl", run / "events.jsonl"):
        if ev.exists():
            for x in ev.read_text().splitlines():
                try:
                    e = json.loads(x)
                except ValueError:
                    continue
                if e.get("kind") == "engrams":
                    return [n.split(" at ")[0].strip() for n in e.get("msg", "").split(",") if n.strip()]  # "e1a2b at 0.6": gated recall
    return []


def notes_shown(run):
    for ev in (run / "members" / "events.jsonl", run / "events.jsonl"):
        if ev.exists() and '"notes"' in ev.read_text():
            return True
    return False


def run_arm(arm, tasks, seed, who, log=print):
    from team import engram, notes, ternary
    from training import grow, hive_engram
    base = who.split(",")[0].split("+")[0]
    tag = f"memory_{seed}_{arm}"
    shutil.rmtree(E.RUNS / tag, ignore_errors=True)
    store = Path(tempfile.mkdtemp(prefix=f"engrams-{arm}-"))
    notes_file = Path(tempfile.mkdtemp(prefix=f"notes-{arm}-")) / "notes.jsonl"
    use_notes, use_cell, use_hive = arm in ("notes", "all"), arm in ("cell", "all"), arm in ("hive", "all")
    os.environ.update({"HIVE_ENGRAMS_HOME": str(store), "HIVE_NOTES_FILE": str(notes_file),
                       "HIVE_ENGRAMS": "1" if (use_cell or use_hive) else "0", "HIVE_NOTES": "1" if use_notes else "0",
                       "HIVE_SHORT_ORDERS": "1" if arm == "short" else "0"})
    ternary.ENGRAMS = store
    ternary.stop()
    home = E._memory(True)
    rows, t0, wrote = [], time.time(), {"engrams": 0, "notes": 0, "hive_updates": 0, "seconds": 0}
    by_name = {}  # engram name -> the confirmed task it was written from
    confirmed = []  # every earlier task the check confirmed, with its answer: {"task", "answer", "round"}
    in_hive = []  # the confirmed tasks whose rows the hive engram holds
    round_rows, round_tasks = [], []
    for i, (rnd, tid, name, kind, task, check, which) in enumerate(tasks):
        res = E.sit_one(tag, tid, task, check, home, kind=kind)
        run = E.RUNS / tag / tid
        recalled = recalled_of(run)
        sources = [by_name[n] for n in recalled if n in by_name] + (in_hive if "hive" in recalled else [])
        ok = bool(res["ok"])
        answer = res.get("answer", "")
        row = {"round": rnd, "id": tid, "maker": name, "kind": kind, "which": which, "ok": ok, "seconds": res["seconds"],
               "recalled": recalled, "notes_shown": notes_shown(run), "note": res.get("note", ""),
               "copied": [] if ok else copied(answer, task, sources),
               "chance": [] if ok else copied(answer, task, confirmed)}
        w0 = time.time()
        if use_notes:
            wrote["notes"] += len(notes.learn(run, kind, path=notes_file))
        right = [m for m in res.get("members", []) if m.get("ok")]
        if right:  # a member the check confirmed: its work is memory (the hive's answer may still be wrong)
            confirmed.append({"task": task, "answer": answer if ok else "", "round": rnd, "id": tid})
            if use_cell:
                e = engram.write(task, run, base=base, cell=right[0]["who"], log=lambda *a, **k: None)
                if e:
                    by_name[e] = confirmed[-1]
                    wrote["engrams"] += 1
            if use_hive:
                new = grow.rows_of(run, task, kind)
                if new:
                    round_rows += new
                    round_tasks.append(confirmed[-1])
        row["write_seconds"] = round(time.time() - w0)
        rows.append(row)
        last_of_round = i + 1 == len(tasks) or tasks[i + 1][0] != rnd
        if use_hive and last_of_round and rnd < tasks[-1][0] and round_rows:
            w0 = time.time()
            path = store / f".round{rnd}.jsonl"
            hive_engram.write_rows(path, round_rows)
            line = hive_engram.update(path, base=base, home=store, seed=seed + rnd, log=lambda *a, **k: None)
            path.unlink(missing_ok=True)
            if line:
                wrote["hive_updates"] += 1
                in_hive.extend(round_tasks)
            round_rows, round_tasks = [], []
            ternary.stop()  # the hive engram keeps its name, so a running server would go on with the old one
            rows[-1]["write_seconds"] += round(time.time() - w0)
        wrote["seconds"] += rows[-1]["write_seconds"]
        log(f"{arm} r{rnd} {'PASS' if ok else 'FAIL'} [{which} {name}] {res['seconds']}s +{rows[-1]['write_seconds']}s"
            f"{' recalled ' + ','.join(recalled) if recalled else ''}{' notes' if row['notes_shown'] else ''}"
            f"{' COPIED ' + ','.join(row['copied']) if row['copied'] else ''}")
    ternary.stop()
    shutil.rmtree(store, ignore_errors=True)
    shutil.rmtree(notes_file.parent, ignore_errors=True)
    return summary(rows, wrote, time.time() - t0)


def summary(rows, wrote, seconds):
    rounds = sorted({r["round"] for r in rows})
    later = [r for r in rows if r["round"] > 1]
    pick = lambda xs: [sum(x["ok"] for x in xs), len(xs)]  # noqa: E731
    return {"by_round": {k: pick([r for r in rows if r["round"] == k and r["which"] == "seen"]) for k in rounds},
            "later_seen": pick([r for r in later if r["which"] == "seen"]),
            "unseen": pick([r for r in rows if r["which"] == "unseen"]),
            "first_round": pick([r for r in rows if r["round"] == 1]),
            "copying": sum(bool(r["copied"]) for r in rows), "chance_repeats": sum(bool(r["chance"]) for r in rows),
            "recalled_tasks": sum(bool(r["recalled"]) for r in rows), "notes_shown": sum(r["notes_shown"] for r in rows),
            "task_seconds": sum(r["seconds"] for r in rows), "write_seconds": wrote["seconds"], "seconds": round(seconds),
            "written": wrote, "rows": rows}


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    seed, rounds, who = opt("--seed", 32000), opt("--rounds", 4), opt("--who", "t17")
    arms = [a for a in opt("--arms", ",".join(ARMS)).split(",") if a]
    seen = SEEN[:opt("--seen", 6)]
    unseen = [k for k in UNSEEN if k not in seen][:opt("--unseen", 4)]
    tasks = stream(seed, rounds, seen, unseen)
    os.environ.update({"HIVE_MEMBERS": who, "AGENT_TEAM_SOLO": "2", "AGENT_TEAM_SOLO_ALONE": "1",
                       "HIVE_TASK_SECONDS": str(opt("--task-seconds", 600))})
    path = ROOT / "training" / "experiments" / f"memory_stream_{seed}.json"
    out = json.loads(path.read_text()) if path.exists() and "--fresh" not in argv else {}
    out.update({"seed": seed, "who": who, "rounds": rounds, "seen": seen, "unseen": unseen, "tasks": len(tasks)})
    out.setdefault("arms", {})
    for arm in arms:
        out["arms"][arm] = run_arm(arm, tasks, seed, who)
        path.write_text(json.dumps(out, indent=1))  # after every arm: a run cut short keeps what it measured
        a = out["arms"][arm]
        print(json.dumps({arm: {k: a[k] for k in ("later_seen", "unseen", "copying", "chance_repeats", "seconds", "write_seconds")}}), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
