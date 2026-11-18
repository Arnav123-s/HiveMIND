"""Practice split in two, for measuring, and practice counted by how old its kinds are. No model is needed here.

Orders (piece O1). Every member of the t80 body is named "t80+<cell>", and team/solo.orders gives a name with "+"
the short orders (team/solo.SHORT): practice and the gate both run on them now. The bare DNA's full orders
(team/solo.MEMBER) are what the small DNA's stream measured against (docs/RESEARCH.md section 8: short 16 of 18 on
later rounds, full 6 of 18). So a generation's practice is split by runner: even runners keep the short orders
(HIVE_SHORT_ORDERS=1, as now), odd runners are given the full ones (HIVE_FULL_ORDERS=1). The repository variable
HIVE_SHORT_ORDERS_AB (on unless "0") switches the split off. Only practice is split: the gate, the dreams and the
answers at the exams are untouched, and every training row is written under the short orders whichever arm made it
(training/grow.rows_of), the same orders the exam's members have.

    python3 training/practice_arms.py arm SHARD [ON]      the arm of a practice runner: short, full, or "" (ON is "0")

Kinds (piece F2). The 24 kinds K2 added at g44 (h_tab_*, h_txt_*, h_prog_*: hard kinds with ORDER 300 and above,
training/kinds) are "new"; every other kind is "old". A task of several parts is new when any part is.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ARMS = ("short", "full")
NEW_ORDER = 300  # the first ORDER of the K2 kinds (h_tab_group)


def arm(shard, on="1"):
    """The orders a practice runner is given: "short" for an even runner, "full" for an odd one, "" with the split
    off (on is "0", "off" or empty) or a runner number that is not a whole number."""
    if str(on).strip().lower() in ("0", "off", "no", "false", ""):
        return ""
    try:
        n = int(str(shard).strip())
    except ValueError:
        return ""
    return "short" if n % 2 == 0 else "full"


def env_for(which):
    """The variables team/solo.member reads for this arm."""
    return {"short": {"HIVE_SHORT_ORDERS": "1"}, "full": {"HIVE_FULL_ORDERS": "1"}}.get(which, {})


def age(maker, parts=()):
    """ "new" for a K2 kind (or a task of several parts with one among them), "old" for any other kind this repository
    knows, "" for a name it does not."""
    from training import kinds
    if maker == "compound":
        got = [age(p[0] if isinstance(p, (list, tuple)) and p else p) for p in parts or ()]
        return "new" if "new" in got else "old" if got and all(got) else ""
    m = kinds.BY_NAME.get(maker)
    if m is None:
        return ""
    return "new" if m.HARD and m.ORDER >= NEW_ORDER else "old"


def first_try(task_folder):
    """Whether a practice task was right at the first try (scripts/selfreliance.one), None when it cannot be told."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import selfreliance
    got = selfreliance.one(Path(task_folder))
    return None if got is None else bool(got[1])


def _files(folders):
    for folder in folders:
        for f in sorted(Path(folder).rglob("practice.json")):
            if f.stat().st_size > 500_000:
                continue
            try:
                d = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            if isinstance(d, dict) and isinstance(d.get("tasks"), list):
                yield d


def summary(folders):
    """{"orders_ab": {arm: {...}}, "first_try_by_age": {"old": [right, of], "new": [right, of]}} over the practice.json
    of every practice runner in the folders. An arm: runners, first_try [right, of], right [right, of], seconds (the mean
    a task took) and timeouts. Only tasks that say whether they were right at the first try count there (practice from
    before this was written says nothing, and is left out of both)."""
    arms, ages = {}, {}
    for d in _files(folders):
        a = d.get("arm") if d.get("arm") in ARMS else ""
        tasks = [t for t in d["tasks"] if isinstance(t, dict)]
        if a:
            s = arms.setdefault(a, {"runners": 0, "first_try": [0, 0], "right": [0, 0], "seconds": 0, "timeouts": 0, "_secs": []})
            s["runners"] += 1
        for t in tasks:
            first = t.get("first")
            if a:
                s["right"][0] += t.get("ok") is True
                s["right"][1] += 1
                if isinstance(first, bool):
                    s["first_try"][0] += first
                    s["first_try"][1] += 1
                if isinstance(t.get("seconds"), (int, float)) and not isinstance(t.get("seconds"), bool):
                    s["_secs"].append(t["seconds"])
                s["timeouts"] += t.get("timeout") is True
            k = t.get("age") if t.get("age") in ("old", "new") else ""
            if k and isinstance(first, bool):
                c = ages.setdefault(k, [0, 0])
                c[0] += first
                c[1] += 1
    for s in arms.values():
        secs = s.pop("_secs")
        s["seconds"] = round(sum(secs) / len(secs)) if secs else None
    out = {}
    if arms:
        out["orders_ab"] = {a: arms[a] for a in ARMS if a in arms}
    if ages:
        out["first_try_by_age"] = {k: ages[k] for k in ("old", "new") if k in ages}
    return out


def _share(c):
    return f"{c[0] / c[1]:.2f} ({c[0]} of {c[1]})" if isinstance(c, list) and len(c) == 2 and c[1] else "-"


def ab_text(ab):
    """One cell of the read: each arm's first try, tasks right, mean seconds and timeouts."""
    if not isinstance(ab, dict) or not ab:
        return "not split"
    parts = []
    for a in ARMS:
        s = ab.get(a)
        if not isinstance(s, dict):
            continue
        secs = s.get("seconds")
        parts.append(f"{a}: first try {_share(s.get('first_try'))}, right {_share(s.get('right'))}, "
                     f"{secs if secs is not None else '-'} s a task, {s.get('timeouts', 0)} timed out, {s.get('runners', 0)} runners")
    return "; ".join(parts) or "not split"


def age_text(by):
    """One cell of the read: the first try on the old kinds and on K2's new ones."""
    if not isinstance(by, dict) or not by:
        return "not measured"
    return f"old kinds {_share(by.get('old'))}; new kinds (K2) {_share(by.get('new'))}"


def main(argv):
    if argv[:1] == ["arm"] and len(argv) >= 2:
        print(arm(argv[1], argv[2] if len(argv) > 2 else "1"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
