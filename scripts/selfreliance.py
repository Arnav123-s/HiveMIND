"""How much the hive needed the runtime's help, from the members' own work: is it learning on its own?

Every hint the runtime gives (team/solo.HINTS: data given as a file, a key that is elsewhere, a page read as JSON,
one page fetched again and again ...) can rescue a task, and a rescued task becomes a training row whose answer is
the final, right program. A body that learns from those rows writes that program at once the next time. So,
generation after generation, `right_first_try` should rise and `hints_per_task` should fall.

    python scripts/selfreliance.py LABEL FOLDER [FOLDER ...]     one CSV row on stdout (FOLDER: unzipped work artifacts)
    python scripts/selfreliance.py LABEL FOLDER ... --add docs/selfreliance.csv   the row added to the file

A task is right first try when a member whose answer stands ran one program, with no hint, and the task's check
passed. Older work (before hints were logged by name) is read from what the programs printed to stderr.
"""
import collections
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _hints():
    """team.solo.HINTS, read from its source: team.solo needs the model's packages, and the record job has none."""
    import ast
    src = ast.parse((Path(__file__).resolve().parent.parent / "team" / "solo.py").read_text())
    node = next(n for n in src.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "HINTS")
    return ast.literal_eval(node.value)


def hints_in(*texts):
    """The names of the runtime's hints that these texts carry (team.solo.hints_in)."""
    t = "\n".join(x or "" for x in texts)
    return [name for name, mark in _hints() if mark in t]

FIELDS = ["label", "tasks", "right", "right_first_try", "first_try_share", "hints", "hints_per_task", "top_hints"]


def task_dirs(folders):
    for f in folders:
        for e in Path(f).rglob("exam.json"):
            yield e.parent


def one(task):
    """(right, right_first_try, [hint names]) of one task's folder."""
    try:
        ok = bool(json.loads((task / "exam.json").read_text()).get("ok"))
    except (OSError, ValueError):
        return None
    m = task / "members" if (task / "members").is_dir() else task
    events = []
    if (m / "events.jsonl").exists():
        for line in (m / "events.jsonl").read_text(errors="ignore").splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    logged = [e["msg"] for e in events if e.get("kind") == "hint"]
    if logged:
        hints = logged
    else:  # work from before the hints were logged: what the programs themselves were told on stderr
        hints = [h for f in sorted(m.rglob(".member*_*.py.err")) for h in hints_in(f.read_text(errors="ignore"))]
    runs, helped, first = collections.Counter(), set(), False
    for e in events:
        who = e.get("agent", "")
        if e.get("kind") == "run":
            runs[who] += 1
        elif e.get("kind") == "hint":
            helped.add(who)
        elif e.get("kind") == "answer" and e.get("msg") not in ("", "no answer") and runs[who] == 1 and who not in helped:
            first = True
    if not events:  # no log (practice before 2026-11-15 22:40): member 1 right with one program and no hint
        progs = sorted((m / "work").glob("member1_*.py")) if (m / "work").is_dir() else []
        first = len(progs) == 1 and not hints
    return ok, ok and first, hints


def row(label, folders):
    n = right = first = 0
    names = collections.Counter()
    for t in task_dirs(folders):
        got = one(t)
        if got is None:
            continue
        n += 1
        right += got[0]
        first += got[1]
        names.update(got[2])
    total = sum(names.values())
    return {"label": label, "tasks": n, "right": right, "right_first_try": first,
            "first_try_share": round(first / n, 3) if n else 0, "hints": total,
            "hints_per_task": round(total / n, 2) if n else 0,
            "top_hints": " ".join(f"{k}:{v}" for k, v in names.most_common(5))}


def main(argv):
    add = None
    if "--add" in argv:
        i = argv.index("--add")
        add, argv = Path(argv[i + 1]), argv[:i] + argv[i + 2:]
    if len(argv) < 2:
        print(__doc__)
        return 2
    r = row(argv[0], argv[1:])
    buf = io.StringIO()
    w = csv.DictWriter(buf, FIELDS)
    if add is None or not add.exists():
        w.writeheader()
    w.writerow(r)
    if add is None:
        print(buf.getvalue(), end="")
    else:
        with add.open("a") as f:
            f.write(buf.getvalue())
        print(f"added to {add}: {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
