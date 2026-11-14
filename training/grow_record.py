"""The gate of a generation: the numbers decide whether the hive's body changes.

    python3 training/grow_record.py gate <folder of the gate's sittings> <folder with the cells' json> <generation>
    python3 training/grow_record.py fetch t17+g3code,t17+g3data     the cells named, from the release into cells/members/

`gate` runs in the one job that may write to the repository, and runs no model and nothing the hive wrote. From the
other jobs it takes only whole numbers within their bounds and names this file builds itself. Needs nothing but
Python.

Three arms sat the same fresh seeds of the exam (.github/workflows/grow.yml), each as members alone:
    dna      the body's ternary model as it was published, with no cell's edit
    before   the body as it was (the cells of the last generation that was kept); absent in the first generation
    after    the body as regrown this time
The regrown body is kept when it passed more tasks than the DNA alone and at least as many as the body before it.
What "after" passes over "dna" is what the hive taught itself; it is also counted apart on the kinds it never
practised. Every generation leaves one line in training/reports/generations.jsonl, whatever the outcome.
"""
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORD = ROOT / "training" / "reports" / "generations.jsonl"
BODY = ROOT / "cells" / "body.json"
MEMBERS = ROOT / "cells" / "members"
ARMS = ("dna", "before", "after")
ORGANS = ("sources", "code", "data", "words")
CELL = r"g\d{1,6}(?:sources|code|data|words)\d{0,2}"
# the kinds the hive never practises on (training/exam_hard.HELD_OUT), by the name the exam gives them
UNPRACTISED = ("walk a site and count into a file", "two facts from two sources, combined", "a file given in the task, edited to a specification",
               "a simulation followed step by step")


def _int(x, most):
    return x if isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= most else None


def arm(folders):
    """What one arm did over its seeds: {"passed", "tasks", "minutes", "unpractised": [passed, tasks], "seeds"}."""
    out = {"passed": 0, "tasks": 0, "minutes": 0, "unpractised": [0, 0], "seeds": 0}
    for folder in folders:
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
    d, b, a = arms["dna"], arms["before"], arms["after"]
    if not a["seeds"] or a["seeds"] != d["seeds"] or a["tasks"] != d["tasks"]:
        return False, "the regrown body and the DNA did not both finish the same seeds"
    if a["passed"] <= d["passed"]:
        return False, f"the regrown body passed no more than the DNA alone ({a['passed']} against {d['passed']})"
    if b["seeds"]:
        if b["seeds"] != a["seeds"] or b["tasks"] != a["tasks"]:
            return False, "the body before did not finish the same seeds"
        if a["passed"] < b["passed"]:
            return False, f"the regrown body passed fewer than the body before ({a['passed']} against {b['passed']})"
        return True, f"the regrown body passed {a['passed']}, the body before {b['passed']}, the DNA alone {d['passed']}"
    return True, f"the first body passed {a['passed']}, the DNA alone {d['passed']}"


def gate(argv):
    folder, got, gen = Path(argv[0]), Path(argv[1]), argv[2]
    if not re.fullmatch(r"g\d{1,6}", gen):
        print("not a generation's name")
        return 1
    arms = {a: arm([p for p in folder.glob(f"gate-{a}-*") if re.fullmatch(rf"gate-{a}-\d", p.name)]) for a in ARMS}
    cells, rows, minutes = [], None, 0
    for o in ORGANS:
        f = got / f"t17.{gen}{o}.json"
        if (got / f"t17.{gen}{o}.gguf").exists() and f.exists():
            cells.append(f"{gen}{o}")
            try:
                meta = json.loads(f.read_text())
                rows, minutes = _int(meta.get("rows"), 10 ** 7), minutes + (_int(meta.get("seconds"), 10 ** 6) or 0) // 60
            except ValueError:
                pass
    body = json.loads(BODY.read_text())
    before = [c for c in body.get("cells", []) if re.fullmatch(CELL, str(c))]
    keep, why = decide(arms) if cells else (False, "no cell was grown")
    line = {"generation": gen, "when": time.strftime("%Y-%m-%d %H:%M"), "rows": rows, "cells": cells, "train_minutes": minutes, "arms": arms,
            "kept": keep, "why": why, "body_before": before, "body_after": cells if keep else before}
    with open(RECORD, "a") as f:
        f.write(json.dumps(line) + "\n")
    if keep:
        body.update({"dna": "t17", "generation": int(gen[1:]), "cells": cells})
        BODY.write_text(json.dumps(body) + "\n")
    print(f"### Generation {gen}\n")
    print(f"- {len(cells)} cells grown from {rows} checked rows ({minutes} minutes of training in all): {', '.join(cells)}")
    print("| who sat | passed | of | minutes | on kinds never practised |\n|---|---|---|---|---|")
    names = {"dna": "the DNA as published", "before": "the body before", "after": "the body regrown"}
    for k in ARMS:
        v = arms[k]
        print(f"| {names[k]} | {v['passed'] if v['seeds'] else '-'} | {v['tasks'] if v['seeds'] else '-'} | {v['minutes'] if v['seeds'] else '-'} | "
              f"{v['unpractised'][0]} of {v['unpractised'][1]} |")
    print(f"\n- the body {'is now ' + ', '.join(cells) if keep else 'stays as it was'}: {why}")
    return 0


def fetch(argv):
    """The cells named, from the release into cells/members/. A cell that is not there is said and passed over."""
    repo = os.environ.get("GITHUB_REPOSITORY", "Arnav123-s/HiveMIND")
    for who in (argv[0] if argv else "").split(","):
        m = re.fullmatch(rf"(t17)\+({CELL}|gen\d{{1,6}})", who.strip())
        if not m:
            continue
        to = MEMBERS / f"{m.group(1)}+{m.group(2)}.gguf"
        if to.exists():
            continue
        MEMBERS.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/{repo}/releases/download/hive-grown/{m.group(1)}.{m.group(2)}.gguf"
        try:
            urllib.request.urlretrieve(url, to)
            print("fetched", who)
        except OSError as e:
            print(f"{who}: not fetched from {url}: {e}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(gate(a[1:]) if a[:1] == ["gate"] and len(a) == 4 else fetch(a[1:]) if a[:1] == ["fetch"] else (print(__doc__) or 1))
