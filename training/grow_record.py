"""The gate of a generation: the numbers decide whether the hive's body changes.

    python3 training/grow_record.py gate <folder of the gate's sittings> <folder with the cells' json> <generation>
    python3 training/grow_record.py fetch t17+g3code,t17+g3data     the cells named, from the release into cells/members/
    python3 training/grow_record.py rows OUT FILE ...               every row of the files once, in order, into OUT
    python3 training/grow_record.py failures OUT FILE ...           the same for the tasks got wrong
    python3 training/grow_record.py restart [RECORD]                exit 1 (saying why) after three generations dropped running

`gate` runs in the one job that may write to the repository, and runs no model and nothing the hive wrote. From the
other jobs it takes only whole numbers within their bounds and names this file builds itself. Needs nothing but
Python.

Three arms sat the same fresh seeds of the exam (.github/workflows/grow.yml), each as members alone:
    dna      the body's ternary model as it was published, with no cell's edit
    before   the body as it was (the cells of the last generation that was kept); absent in the first generation
    after    the body as regrown this time
The regrown body is kept when it passed more tasks than the DNA alone and at least as many as the body before it.
A body that multiplies sits only before and after, on the same seeds (the paired gate): its children are kept
unless after is more than 2 tasks under before in all or on easy; a dropped generation's rows are still kept in
the release and the body stays as it was. Three generations dropped running stop the line (`restart`).
What "after" passes over "dna" is what the hive taught itself; it is also counted apart on the kinds it never
practised. Every generation leaves one line in training/reports/generations.jsonl, whatever the outcome.
"""
import hashlib
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
MOST_ROWS, MOST_FAILURES = 20000, 3000  # what the release keeps: the newest
# the kinds the hive never practises on (training/exam_hard.HELD_OUT), by the name the exam gives them
UNPRACTISED = ("walk a site and count into a file", "two facts from two sources, combined", "a file given in the task, edited to a specification",
               "a simulation followed step by step")


def _int(x, most):
    return x if isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= most else None


# ---- the rows: what the release holds is added to, never replaced by an older copy ------------------------------------
def lines(path):
    try:
        return [ln for ln in Path(path).read_text().splitlines() if ln.strip()]
    except OSError:
        return []


def _row(ln):
    """What makes two rows the same row: the exchange and its answer, not when or by whom it was practised."""
    try:
        r = json.loads(ln)
        return hashlib.sha1(json.dumps([r.get("type"), r["messages"][1:], r.get("output"), r.get("rejected")], sort_keys=True).encode()).hexdigest()
    except (ValueError, KeyError, TypeError, IndexError):
        return None


def _failure(ln):
    try:
        r = json.loads(ln)
        return hashlib.sha1(json.dumps([r["maker"], r["rseed"], r.get("level", 0), r.get("program")], sort_keys=True).encode()).hexdigest()
    except (ValueError, KeyError, TypeError):
        return None


def union(groups, key=_row, most=MOST_ROWS):
    """Every line of every group once, in order (a line that is no row is dropped), the newest `most` of them.
    On 2026-11-14 a trial that had read the release hours before wrote its older, smaller copy back over it, and
    the 170 rows generation 11 had practised were gone from the release: so nothing is uploaded now that was not
    first joined with what the release holds at that moment."""
    seen, out = set(), []
    for group in groups:
        for ln in group:
            k = key(ln)
            if k and k not in seen:
                seen.add(k)
                out.append(ln)
    return out[-most:]


# ---- how hard the lessons are: moved by what practice passed ----------------------------------------------------------
def levels(now, folders):
    """The body's levels after this generation's practice: ({maker: level, "compound": parts}, what was seen).
    A kind (or the number of parts of a task of several) the body passed at least 7 times in 10 at its level goes
    up one; one it passed at most 3 times in 20 comes down one; at least four tries are needed to move it. Only
    whole numbers within their bounds and names this repository knows are taken from the practice jobs."""
    from training import exam
    known = set(exam.LEVELED) | {"compound"}
    seen = {}
    for folder in folders:
        for f in sorted(Path(folder).rglob("practice.json")):
            if f.stat().st_size > 500_000:
                continue
            try:
                d = json.loads(f.read_text())
            except ValueError:
                continue
            for t in (d.get("tasks") if isinstance(d, dict) else None) or []:
                m, lv = (t.get("maker"), _int(t.get("level"), 9)) if isinstance(t, dict) else (None, None)
                if m in known and lv is not None:
                    c = seen.setdefault(m, {}).setdefault(lv, [0, 0])
                    c[0] += t.get("ok") is True
                    c[1] += 1
    out = {k: v for k, v in (now or {}).items() if k in known and _int(v, 9) is not None}
    for m, by in seen.items():
        low, high = (2, exam.MOST_PARTS) if m == "compound" else (0, exam.MOST_LEVEL)
        cur = max(low, min(high, out.get(m, low)))
        right, tried = by.get(cur, [0, 0])
        out[m] = min(high, cur + 1) if tried >= 4 and right >= 0.7 * tried else max(low, cur - 1) if tried >= 4 and right <= 0.15 * tried else cur
    return out, {m: {str(k): v for k, v in sorted(by.items())} for m, by in sorted(seen.items())}


def practice_kinds(old, folders, keep=0.5):
    """{kind: [tries, body right, some member right]} over the generations' practice: this generation's practice.json
    files added to the counts kept so far, those weighed by `keep` (each generation counts half as much as the one
    after it). training/grow.edge_weights draws practice by it. Only kinds of a known shape, at most 64."""
    out = {}
    for k, c in (old or {}).items():
        if isinstance(k, str) and re.fullmatch(r"[\w ,.:'()-]{1,80}", k) and isinstance(c, list) and len(c) == 3 and all(isinstance(x, (int, float)) for x in c):
            out[k] = [round(x * keep, 3) for x in c]
    for folder in folders:
        for f in sorted(Path(folder).rglob("practice.json")):
            if f.stat().st_size > 500_000:
                continue
            try:
                d = json.loads(f.read_text())
            except ValueError:
                continue
            for t in (d.get("tasks") if isinstance(d, dict) else None) or []:
                k = t.get("kind") if isinstance(t, dict) else None
                if not (isinstance(k, str) and re.fullmatch(r"[\w ,.:'()-]{1,80}", k)) or (k not in out and len(out) >= 64):
                    continue
                c = out.setdefault(k, [0, 0, 0])
                c[0] += 1
                c[1] += t.get("ok") is True
                c[2] += t.get("some") is True or t.get("ok") is True
    return {k: [round(x, 3) for x in c] for k, c in sorted(out.items())}


def arm(folders):
    """What one arm did over its seeds: {"passed", "tasks", "minutes", "unpractised": [passed, tasks], "seeds"}."""
    out = {"passed": 0, "tasks": 0, "minutes": 0, "unpractised": [0, 0], "seeds": 0, "kinds": {}, "by_lean": {},
           "hard": [0, 0], "easy": [0, 0], "several": [0, 0]}
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
                # the hard kinds apart from the easy ones and the tasks of several parts (an exam task's id begins with
                # h, e or c): the score moves only when a never-passed kind is learned, and those are mostly hard
                tid = t.get("id") if isinstance(t, dict) else None
                part = {"h": "hard", "e": "easy", "c": "several"}.get(tid[:1]) if isinstance(tid, str) and tid else None
                if part:
                    out[part][0] += t.get("ok") is True
                    out[part][1] += 1
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
                        lean = ternary.leans(who) or ("trunk" if ternary.is_trunk(who) else "dna")
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


MOST_UNDER = 2  # the paired gate: after may be at most this many tasks under before, in all and on easy
DROPS_TO_STOP = 3  # the line does not start again after this many generations dropped running


def _seated(folder):
    """True when a gate folder holds one sitting with a summary of whole numbers in bounds (what arm() counts)."""
    return arm([folder])["seeds"] > 0


def paired(folder, names=("before", "after")):
    """The arms of the paired gate, on the seeds both finished only: {arm: arm(...)} and the seeds compared."""
    by = {a: {p.name.rsplit("-", 1)[1]: p for p in folder.glob(f"gate-{a}-*") if re.fullmatch(rf"gate-{a}-\d", p.name) and _seated(p)} for a in names}
    both = sorted(set.intersection(*(set(v) for v in by.values())))
    return {a: arm([by[a][s] for s in both]) for a in names}, both


def decide(arms, grow=False):
    """Whether the regrown body is kept: (keep, why).
    grow (the paired gate): the body with its children (after) and as it was (before) sat the same seeds; the
    children are kept unless after passed more than 2 tasks fewer than before in all, or more than 2 fewer on the
    easy tasks (ids starting with e). A body that sat nothing before is not judged and kept; one whose after sat
    nothing while before did is dropped."""
    if grow:
        b, a = arms["before"], arms["after"]
        if not b["seeds"]:
            return (True, "the body grows; before did not sit, so it was not judged" + (f" (after: {a['passed']} of {a['tasks']})" if a["seeds"] else ""))
        if not a["seeds"]:
            return False, f"the body with its children finished no seed that the body before finished ({b['passed']} of {b['tasks']} before)"
        if b["seeds"] != a["seeds"] or b["tasks"] != a["tasks"]:
            return False, "before and after did not sit the same seeds"
        said = (f"after {a['passed']} of {a['tasks']} (easy {a['easy'][0]} of {a['easy'][1]}, hard {a['hard'][0]} of {a['hard'][1]}), "
                f"before {b['passed']} of {b['tasks']} (easy {b['easy'][0]} of {b['easy'][1]}, hard {b['hard'][0]} of {b['hard'][1]}) on {a['seeds']} seeds")
        if b["passed"] - a["passed"] > MOST_UNDER:
            return False, f"the children did harm: after is {b['passed'] - a['passed']} tasks under before in all; " + said
        if b["easy"][0] - a["easy"][0] > MOST_UNDER:
            return False, f"the children did harm: after is {b['easy'][0] - a['easy'][0]} tasks under before on easy; " + said
        return True, "the body grows: " + said
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
    # the trunk of this generation: the average of the body's newest cells (training/merge.py), made by the merge job
    trunk = f"{gen}trunk" if (got / f"{dna}.{gen}trunk.gguf").exists() else ""
    before = [c for c in body.get("cells", []) if re.fullmatch(CELL, str(c))] if body.get("dna") == dna else []
    # a new DNA (Arnav, 2026-11-14: bigger, whether or not it scores higher at first): its first body is judged
    # against its own DNA alone; the old body's score is recorded beside it, for information
    same_dna = body.get("dna") == dna
    judged = arms if same_dna else dict(arms, before={"passed": 0, "tasks": 0, "minutes": 0, "unpractised": [0, 0], "seeds": 0})
    keep, why = decide(judged) if cells else (False, "no cell was grown")
    seeds = []
    if grow and cells and not trial:
        # the body multiplies: the paired gate decides it. Before and after sat the same seeds; only the seeds both
        # finished are compared (a seat that died on one side does not count against the other)
        pair, seeds = paired(folder)
        if arms["before"]["seeds"]:
            arms = dict(arms, **pair)
        keep, why = decide(arms, grow=True)
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
    # how hard the lessons are from here on, by what this generation's practice passed (a trial moves nothing)
    practised = [argv[i + 1] for i, a in enumerate(argv) if a == "--practice" and i + 1 < len(argv)]
    lv_now = body.get("levels") if same_dna and isinstance(body.get("levels"), dict) else {}
    lv_next, lv_seen = levels(lv_now, practised) if practised else (lv_now, {})
    kinds_now = body.get("kinds") if same_dna and isinstance(body.get("kinds"), dict) else {}
    kinds_next = practice_kinds(kinds_now, practised) if practised else kinds_now
    both = {k: {"passed": arms[k]["passed"], "tasks": arms[k]["tasks"], "hard": arms[k]["hard"], "easy": arms[k]["easy"], "seeds": arms[k]["seeds"]}
            for k in ("before", "after")}
    line = {"generation": gen, "when": time.strftime("%Y-%m-%d %H:%M"), "rows": rows, "cells": cells, "train_minutes": minutes, "arms": arms,
            "kept": keep, "verdict": "kept" if keep else "dropped", "paired": dict(both, seeds=seeds) if grow else both, "why": why, "body_before": before, "body_after": after, "trial": trial, "grow": grow,
            "trunk": trunk if keep and grow else "", "levels": lv_next if keep and grow else lv_now, "practice": lv_seen, "practice_kinds": kinds_next,
            "parents": {c: parent_of[c] for c in cells if c in parent_of}, "retired": retired,
            "versus": (os.environ.get("VERSUS_FLAGS", "").strip() if re.fullmatch(FLAGS, os.environ.get("VERSUS_FLAGS", "")) else "?") if arms["versus"]["seeds"] else "",
            "ternary_cells": bool(ternary) and all(ternary), "foresee": bool(foresee) and all(foresee), "pair_steps": pairs, "dna": dna}
    with open(RECORD, "a") as f:
        f.write(json.dumps(line) + "\n")
    if keep:
        parents = {c: p for c, p in dict(old_parents, **parent_of).items() if c in after}
        body.update({"dna": dna, "generation": int(gen[1:]), "cells": after, "parents": parents})
        if grow:
            # a generation whose merge failed keeps the trunk it had (of the same DNA); the levels move with practice
            body["trunk"] = trunk or (body.get("trunk", "") if same_dna else "")
            body["levels"] = lv_next
            body["kinds"] = kinds_next
        elif not same_dna:
            body.pop("trunk", None)
            body.pop("levels", None)
            body.pop("kinds", None)
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
        print(f"\n- the body multiplies: {born} join it; it has {len(after)} cells now{'; gave up their place (their lines go on in their children): ' + ', '.join(retired) if retired else ''}")
        print(f"- the trunk (the body's newest cells averaged into one edit, which answers first): {trunk or 'none was made this generation'}")
        if lv_seen:
            print("- how hard the lessons are now: " + ", ".join(f"{k} {v}" + (f" (was {lv_now.get(k)})" if k in lv_now and lv_now.get(k) != v else "") for k, v in sorted(lv_next.items()))
                  + "; practice passed " + ", ".join(f"{m} at level {k}: {r} of {n}" for m, by in lv_seen.items() for k, (r, n) in by.items()))
    if grow and not keep and cells and not trial:
        print(f"\n- **dropped**: {', '.join(cells)} do not join the body; their rows are kept in the release")
    print(f"\n- the body {'is now ' + ', '.join(after) if keep else 'stays as it was'}: {why}")
    return 0


def restart(argv):
    """Whether the line may start its next generation: exit 1, saying why, when the last DROPS_TO_STOP generations
    of the line (trials left out) were all dropped by the paired gate."""
    record = Path(argv[0]) if argv else RECORD
    line = []
    for ln in lines(record):
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if isinstance(r, dict) and not r.get("trial"):
            line.append(r)
    last = line[-DROPS_TO_STOP:]
    if len(last) == DROPS_TO_STOP and all(r.get("verdict") == "dropped" for r in last):
        print(f"the line stops: the paired gate dropped {DROPS_TO_STOP} generations running ("
              + "; ".join(f"{r.get('generation')}: {r.get('why', '')}" for r in last) + "). The body stays as it was; read them before starting again")
        return 1
    print("the next generation may start" + (f" ({sum(1 for r in last if r.get('verdict') == 'dropped')} of the last {len(last)} dropped)" if last else ""))
    return 0


def fetch(argv):
    """The cells named, from the release into cells/members/. A cell that is not there is said and passed over."""
    repo = os.environ.get("GITHUB_REPOSITORY", "Arnav123-s/HiveMIND")
    for who in (argv[0] if argv else "").split(","):
        m = re.fullmatch(rf"(t17|t40|t80)\+({CELL}|{lineage.TRUNK}|gen\d{{1,6}})", who.strip())
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


def join(argv, key, most):
    """OUT FILE ...: every line of the files once, in order, written to OUT (which may be one of the files)."""
    kept = union([lines(f) for f in argv[1:]], key, most)
    Path(argv[0]).write_text("".join(ln + "\n" for ln in kept))
    print(f"{argv[0]}: {len(kept)} lines from {', '.join(f'{f} ({len(lines(f))})' for f in argv[1:])}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(gate(a[1:]) if a[:1] == ["gate"] and len(a) >= 4 else fetch(a[1:]) if a[:1] == ["fetch"] else
             join(a[1:], _row, MOST_ROWS) if a[:1] == ["rows"] and len(a) >= 3 else
             join(a[1:], _failure, MOST_FAILURES) if a[:1] == ["failures"] and len(a) >= 3 else
             restart(a[1:]) if a[:1] == ["restart"] else (print(__doc__) or 1))
