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
sys.path.insert(0, str(ROOT))  # team.ternary names organs and leanings; it needs nothing but Python
from training import lineage  # noqa: E402
RECORD = ROOT / "training" / "reports" / "generations.jsonl"
BODY = ROOT / "cells" / "body.json"
STRENGTHS = ROOT / "cells" / "strengths.json"
MEMBERS = ROOT / "cells" / "members"
ARMS = ("dna", "before", "after", "versus")  # versus: a second kind of cell from the same rows, in a trial (grow.yml input `versus`)
FLAGS = r"(--(pairs|foresee|ternary|no-checkpoint|lr|rank|epochs|layers|weight|max-len|read|judged)( [a-z0-9.]+)?[ ]?)*"
ORGANS = ("sources", "code", "data", "words")
DNAS = ("t17", "t40", "t80")
CELL = r"g\d{1,6}(?:sources|code|data|words)\d{0,2}"
# the kinds the hive never practises on (training/exam_hard.HELD_OUT), by the name the exam gives them
UNPRACTISED = ("walk a site and count into a file", "two facts from two sources, combined", "a file given in the task, edited to a specification",
               "a simulation followed step by step")


def _int(x, most):
    return x if isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= most else None


def arm(folders):
    """What one arm did over its seeds: {"passed", "tasks", "minutes", "unpractised": [passed, tasks], "seeds"}."""
    out = {"passed": 0, "tasks": 0, "minutes": 0, "unpractised": [0, 0], "seeds": 0, "kinds": {}, "by_lean": {}}
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
                # passed and sat, kind by kind: what practice weighs to stay at the edge (training/grow.edge_weights).
                # Only kinds of a known shape are kept: the name is text from another job.
                k = t.get("kind") if isinstance(t, dict) else None
                if isinstance(k, str) and re.fullmatch(r"[\w ,.:'()-]{1,80}", k) and len(out["kinds"]) < 64:
                    got = out["kinds"].setdefault(k, [0, 0])
                    got[0] += t.get("ok") is True
                    got[1] += 1
                # each member's own answer, put to the task's check (training/exam.each_member): which cell is right
                # on what, by the organ it leans to; team/ternary.seating seats tasks by it
                if isinstance(k, str) and isinstance(t.get("task"), str) and isinstance(t.get("members"), list):
                    from team import ternary
                    o = ternary.organ(t["task"][:3000])
                    for m in t["members"][:5]:
                        who = m.get("who") if isinstance(m, dict) else None
                        if not (isinstance(who, str) and re.fullmatch(r"[\w.+-]{1,80}", who)):
                            continue
                        lean = ternary.leans(who) or "dna"
                        rec = out["by_lean"].setdefault(lean, {"kind": {}, "organ": {}})
                        for table, key in ((rec["kind"], k), (rec["organ"], o)):
                            if key in table or len(table) < 64:
                                c = table.setdefault(key, [0, 0])
                                c[0] += m.get("ok") is True
                                c[1] += 1
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
    trial = "--trial" in argv
    dna = argv[argv.index("--dna") + 1] if "--dna" in argv else "t17"
    if dna not in DNAS:
        print("not a DNA this file knows")
        return 1
    grow = "--grow" in argv
    cells, rows, minutes, ternary, foresee, pairs, parent_of = [], None, 0, [], [], 0, {}
    names = sorted({p.name[len(dna) + 1:-5] for p in got.glob(f"{dna}.{gen}*.gguf")}, key=lambda c: (lineage.ORGANS.index(lineage.organ_of(c)) if lineage.organ_of(c) else 9, len(c), c))
    for c in names:
        f = got / f"{dna}.{c}.json"
        if re.fullmatch(CELL, c) and c.startswith(gen) and not c[len(gen)].isdigit() and f.exists():
            cells.append(c)
            try:
                meta = json.loads(f.read_text())
                if isinstance(meta.get("parent_cell"), str) and re.fullmatch(CELL, meta["parent_cell"]):
                    parent_of[c] = meta["parent_cell"]
                rows, minutes = _int(meta.get("rows"), 10 ** 7), minutes + (_int(meta.get("seconds"), 10 ** 6) or 0) // 60
                ternary.append(meta.get("ternary_edit") is True)
                foresee.append(meta.get("foresee") is True)
                pairs += _int(meta.get("pairs"), 10 ** 7) or 0
            except ValueError:
                pass
    body = json.loads(BODY.read_text())
    before = [c for c in body.get("cells", []) if re.fullmatch(CELL, str(c))] if body.get("dna") == dna else []
    # a new DNA (Arnav, 2026-11-14: bigger, whether or not it scores higher at first): its first body is judged
    # against its own DNA alone; the old body's score is recorded beside it, for information
    same_dna = body.get("dna") == dna
    judged = arms if same_dna else dict(arms, before={"passed": 0, "tasks": 0, "minutes": 0, "unpractised": [0, 0], "seeds": 0})
    keep, why = decide(judged) if cells else (False, "no cell was grown")
    if grow and cells and not trial:
        # the body multiplies (Arnav, 2026-11-14): no gate decides it; the children always join. The sitting of the
        # body with its children is its pulse, kept to trace a problem back from, and decides nothing
        a = arms["after"]
        keep, why = True, (f"the body grows; its pulse: {a['passed']} of {a['tasks']} with its children" if a["seeds"] else "the body grows (no pulse was taken)")
    if cells and not same_dna:
        why += f" (a new DNA, {dna}: the body of {body.get('dna')} before it is not the bar)"
    if trial and keep:
        keep, why = False, "a trial beside the line of generations (the body is not changed by it); by the numbers it would be kept: " + why
    after, retired = cells, []
    old_parents = {c: p for c, p in (body.get("parents") or {}).items() if isinstance(p, str)} if same_dna else {}
    if keep and grow:
        # the body multiplies: the cells before stay and their children join them (training/lineage.py)
        after, retired = lineage.grown_body(before, cells, dict(old_parents, **parent_of))
    elif not keep:
        after = before
    line = {"generation": gen, "when": time.strftime("%Y-%m-%d %H:%M"), "rows": rows, "cells": cells, "train_minutes": minutes, "arms": arms,
            "kept": keep, "why": why, "body_before": before, "body_after": after, "trial": trial, "grow": grow,
            "parents": {c: parent_of[c] for c in cells if c in parent_of}, "retired": retired,
            "versus": (os.environ.get("VERSUS_FLAGS", "").strip() if re.fullmatch(FLAGS, os.environ.get("VERSUS_FLAGS", "")) else "?") if arms["versus"]["seeds"] else "",
            "ternary_cells": bool(ternary) and all(ternary), "foresee": bool(foresee) and all(foresee), "pair_steps": pairs, "dna": dna}
    with open(RECORD, "a") as f:
        f.write(json.dumps(line) + "\n")
    if keep:
        parents = {c: p for c, p in dict(old_parents, **parent_of).items() if c in after}
        body.update({"dna": dna, "generation": int(gen[1:]), "cells": after, "parents": parents})
        BODY.write_text(json.dumps(body) + "\n")
    # who in the body is strong on what, by organ, for trials of seating by it (HIVE_SEATING=strength); a body that
    # multiplies is not seated by it
    src = arms["after"] if keep else arms["before"]
    if not trial and not grow and src.get("by_lean"):
        STRENGTHS.write_text(json.dumps({"from": gen, "dna": dna, "by_lean": src["by_lean"]}) + "\n")
    print(f"### Generation {gen}\n")
    print(f"- {len(cells)} cells grown from {rows} checked rows ({minutes} minutes of training in all): {', '.join(cells)}"
          f"{'; their own edits ternary' if line['ternary_cells'] else ''}{'; trained to foresee as well' if line['foresee'] else ''}{f'; {pairs} steps on right-against-wrong pairs' if pairs else ''}")
    print("| who sat | passed | of | minutes | on kinds never practised |\n|---|---|---|---|---|")
    names = {"dna": "the DNA as published", "before": "the body before", "after": "the body regrown",
             "versus": f"the body regrown with {line['versus']}"}
    for k in ARMS:
        v = arms[k]
        if not v["seeds"] and (k == "versus" or grow):
            continue
        print(f"| {names[k]} | {v['passed'] if v['seeds'] else '-'} | {v['tasks'] if v['seeds'] else '-'} | {v['minutes'] if v['seeds'] else '-'} | "
              f"{v['unpractised'][0]} of {v['unpractised'][1]} |")
    if keep and grow:
        born = ", ".join(f"{c} (child of {parent_of[c]})" if c in parent_of else c for c in cells)
        print(f"\n- the body multiplies: {born} join it; it has {len(after)} cells now{'; gave up their place, best of the body at nothing: ' + ', '.join(retired) if retired else ''}")
    print(f"\n- the body {'is now ' + ', '.join(after) if keep else 'stays as it was'}: {why}")
    return 0


def fetch(argv):
    """The cells named, from the release into cells/members/. A cell that is not there is said and passed over."""
    repo = os.environ.get("GITHUB_REPOSITORY", "Arnav123-s/HiveMIND")
    for who in (argv[0] if argv else "").split(","):
        m = re.fullmatch(rf"(t17|t40|t80)\+({CELL}|gen\d{{1,6}})", who.strip())
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
    sys.exit(gate(a[1:]) if a[:1] == ["gate"] and len(a) >= 4 else fetch(a[1:]) if a[:1] == ["fetch"] else (print(__doc__) or 1))
