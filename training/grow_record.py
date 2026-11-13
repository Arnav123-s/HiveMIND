"""The gate of a generation: the numbers decide whether the hive's roster changes.

    python3 training/grow_record.py <folder of the gate's sittings> <folder with the member's json> <name>

Runs in the one job that may write to the repository, and runs no model and nothing the hive wrote. From the other
jobs it takes only whole numbers within their bounds and names this file builds itself. Needs nothing but Python.

Four arms sat the same fresh seeds of the hard exam (.github/workflows/grow.yml):
    as-published        the 1.7B ternary member as it was published, alone
    taught              the same member with the weight edit trained this night, alone
    hive                the hive as its roster stands
    hive-with-taught    the hive with the new member in the first seat
What "taught" passes over "as-published" is what the hive taught itself (also counted apart on the kinds it never
practised). The roster changes only when the hive with the new member passed at least as many tasks as the hive
without, and either passed more or took at most 85% of the time. Every generation leaves one line in
training/reports/generations.jsonl, whatever the outcome.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORD = ROOT / "training" / "reports" / "generations.jsonl"
ROSTER = ROOT / "cells" / "roster.json"
ARMS = ("as-published", "taught", "hive", "hive-with-taught")
SEAT = r"(?:coder|bitnet|t\d{1,2}(?:\+gen\d{1,6})?)"
# the kinds the hive never practises on (training/exam_hard.HELD_OUT), by the name the exam gives them
UNPRACTISED = ("walk a site and count into a file", "two facts from two sources, combined", "a file given in the task, edited to a specification",
               "a simulation followed step by step")


def _int(x, most):
    return x if isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= most else None


def arm(folder):
    """What one arm did over its seeds: {"passed", "tasks", "minutes", "unpractised": [passed, tasks], "seeds"}."""
    out = {"passed": 0, "tasks": 0, "minutes": 0, "unpractised": [0, 0], "seeds": 0}
    for f in sorted(Path(folder).rglob("*.json")):
        if f.stat().st_size > 2_000_000:
            continue
        try:
            d = json.loads(f.read_text())
        except ValueError:
            continue
        s = d.get("summary") if isinstance(d, dict) else None
        if not isinstance(s, dict):
            continue
        passed, tasks, minutes = _int(s.get("passed"), 64), _int(s.get("tasks"), 64), _int(s.get("minutes"), 600)
        if None in (passed, tasks, minutes) or passed > tasks:
            continue
        out["passed"], out["tasks"], out["minutes"], out["seeds"] = out["passed"] + passed, out["tasks"] + tasks, out["minutes"] + minutes, out["seeds"] + 1
        for t in d.get("tasks") or []:
            if isinstance(t, dict) and t.get("kind") in UNPRACTISED:
                out["unpractised"][0] += t.get("ok") is True
                out["unpractised"][1] += 1
    return out


def decide(arms):
    h, w = arms.get("hive"), arms.get("hive-with-taught")
    if not h or not w or not h["seeds"] or h["seeds"] != w["seeds"] or h["tasks"] != w["tasks"]:
        return False, "the two hive arms did not both finish the same seeds"
    if w["passed"] < h["passed"]:
        return False, f"with the new member the hive passed fewer ({w['passed']} against {h['passed']})"
    if w["passed"] > h["passed"]:
        return True, f"with the new member the hive passed more ({w['passed']} against {h['passed']})"
    if w["minutes"] <= 0.85 * h["minutes"]:
        return True, f"with the new member the hive passed as many ({w['passed']}) in less time ({w['minutes']} against {h['minutes']} minutes)"
    return False, f"with the new member the hive passed as many ({w['passed']}) and was not faster ({w['minutes']} against {h['minutes']} minutes)"


def main(argv):
    gate, got, name = Path(argv[0]), Path(argv[1]), argv[2]
    if not re.fullmatch(r"gen\d{1,6}", name):
        print("not a generation's name")
        return 1
    arms = {}
    for a in ARMS:
        folders = [p for p in gate.glob(f"gate-{a}-*") if re.fullmatch(rf"gate-{re.escape(a)}-\d", p.name)]
        tot = {"passed": 0, "tasks": 0, "minutes": 0, "unpractised": [0, 0], "seeds": 0}
        for p in folders:
            one = arm(p)
            for k in ("passed", "tasks", "minutes", "seeds"):
                tot[k] += one[k]
            tot["unpractised"] = [tot["unpractised"][0] + one["unpractised"][0], tot["unpractised"][1] + one["unpractised"][1]]
        arms[a] = tot
    try:
        meta = json.loads((got / f"t17.{name}.json").read_text())
    except (OSError, ValueError):
        meta = {}
    roster = json.loads(ROSTER.read_text())
    before = roster.get("members", "")
    promote, why = decide(arms)
    after = before
    if promote:
        rest = [s for s in before.split(",") if s and not s.startswith("t17+")]
        after = ",".join([f"t17+{name}"] + rest)
        if not re.fullmatch(rf"{SEAT}(?:,{SEAT})*", after):
            promote, why, after = False, "the new roster is not one this file can write", before
    line = {"generation": name, "when": __import__("time").strftime("%Y-%m-%d %H:%M"),
            "rows": _int(meta.get("rows"), 10 ** 7), "used": _int(meta.get("used"), 10 ** 7), "steps": _int(meta.get("steps"), 10 ** 6),
            "train_minutes": (_int(meta.get("seconds"), 10 ** 6) or 0) // 60, "arms": arms, "promoted": promote, "why": why,
            "roster_before": before if re.fullmatch(rf"{SEAT}(?:,{SEAT})*", before) else "", "roster_after": after}
    with open(RECORD, "a") as f:
        f.write(json.dumps(line) + "\n")
    if promote:
        roster.update({"members": after, "generation": int(name[3:])})
        ROSTER.write_text(json.dumps(roster) + "\n")
    a, t = arms["as-published"], arms["taught"]
    print(f"### Generation {name}\n")
    print(f"- trained on {line['rows']} checked rows in {line['train_minutes']} minutes")
    print("| who sat | passed | of | minutes | on kinds never practised |\n|---|---|---|---|---|")
    for k in ARMS:
        v = arms[k]
        print(f"| {k} | {v['passed']} | {v['tasks']} | {v['minutes']} | {v['unpractised'][0]} of {v['unpractised'][1]} |")
    print(f"\n- what the hive taught its small member: {a['passed']} -> {t['passed']} of {t['tasks']}")
    print(f"- roster: {'changed to ' + after if promote else 'stays ' + before}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
