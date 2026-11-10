"""The hive as an organisation: who manages, which teams there are, who holds each small job.

    python -m team org

Read from what the hive really runs on: the roster (team/config.py), the cell registry and its measured wins
(cells/registry.json, cells/wins.json) and the spawned jobs (cells/spawned.json). Nothing here is decoration: a cell
shown as "working" is one the hive calls; "benched" means a bigger member or a code rule measured better and has the job.
"""
from . import config
from .cells import runtime, spawn, use

TEAMS = [  # team, what it is for, its members, and the first words of the cell jobs that belong to it
    ("Management", "reads the order, plans, routes each step, re-plans after a failure",
     ["coordinator", "plan_reviewer"], ["coordinator", "hive", "the router"]),
    ("Guard", "his rules: nothing risky without his order", ["order_reader"], ["guard"]),
    ("Research", "finds facts in live sources, with exact quotes", ["researcher", "condenser"],
     ["researcher", "research hive", "condenser"]),
    ("Web", "operates websites in a real browser", ["browser"], ["browser"]),
    ("Code", "writes, runs and repairs programs; exact arithmetic", ["coder", "code_reviewer", "calculator"],
     ["coder", "code_reviewer", "calculator", "engine"]),
    ("Quality", "checks every result before anyone relies on it", ["verifier", "juror_brain", "juror_fast", "critic"],
     ["verifier", "juror", "juror_brain", "juror_fast", "critic"]),
    ("Writing", "writes and edits the deliverable; translation", ["writer", "editor"], ["writer", "editor"]),
    ("Growth", "improves the others: diagnoses failures, breeds prompts, retrains weights, spawns cells",
     ["examiner", "prompt_smith", "lesson_writer"], ["examiner", "prompt_smith", "lesson_writer"]),
]
# cells whose record says "use" but which the hive does not call: each failed on real inputs after its synthetic test
NOT_CALLED = {
    "answers_q": "3 of 15 real pairs right; the 4B does this job (training/evals/answers_q_real.jsonl)",
    "de_grammar": "cannot beat the 4B alone on short text (cells/de_grammar_notes.md)",
}
MODELS = {"brain4b": "Qwen3-4B", "brain8b": "Qwen3-8B", "fast": "Qwen3-1.7B", "coder7b": "Qwen2.5-Coder-7B", "coder15": "Qwen2.5-Coder-1.5B"}


def _brain(role):
    b = config.GGUF_ROSTER.get(role, "?")
    base, _, edit = b.partition("+")
    return MODELS.get(base, base) + (" + its own weight edit" if edit else "")


def _cell_line(name, c, w, sp):
    if name in sp:
        st = sp[name].get("status")
        ww = w.get(name, {})
        if st == "on":
            lv = spawn.live(name)
            return (f"working (spawned): answers {ww.get('covers', 0):.0%} of the calls, agreed with its member on "
                    f"{ww.get('agree_when_sure', 0):.0%} of them in test; live: {lv['answered']} answered, "
                    f"{lv['audits']} audited")
        return f"{st} (spawned): {sp[name].get('failed_why') or sp[name].get('retired_why') or 'waiting for training'}"
    if name in NOT_CALLED:
        return "benched: " + NOT_CALLED[name]
    ww = w.get(name, {})
    if not ww:
        return "trained, not compared yet"
    inc = ww.get("incumbent_name") or "nothing"
    score = f"{ww.get('cell')} against {ww.get('incumbent')} for {inc}" if ww.get("incumbent") is not None else f"{ww.get('cell')}"
    return ("working: " if ww.get("use") else "benched: ") + score


def body_lines():
    """The body grown from nothing (training/body.py), from its own record."""
    import json
    f = config.ROOT / "training" / "reports" / "body.json"
    try:
        rep = json.loads(f.read_text())
    except (OSError, ValueError):
        return []
    alive = len(list((config.ROOT / "cells" / "scratch" / "body").glob("cell_*.pt")))
    births, retired = rep.get("births", []), rep.get("retired", [])
    out = ["BODY: cells grown from one stem cell, from nothing, on the CPU (python -m team body)",
           f"  {alive} cells alive; {len(births)} births since the first cells, {sum(b['kept'] for b in births)} kept, "
           f"{len(births) - sum(b['kept'] for b in births)} removed at birth; {len(retired)} retired by the immune check"]
    if rep.get("measured"):
        m = rep["measured"][-1]
        best = min((v, k) for k, v in m["loss"].items() if k.startswith("body"))
        out.append(f"  last measured {m['when']} on {m['passages']} passages no cell trained on (loss, lower is better): "
                   f"stem cell alone {m['loss'].get('stem cell alone')}, one model with the same total training "
                   f"{m['loss'].get('one model, same total training', 'not measured')}, the body at its best {best[0]} ({best[1]})")
    for t in rep.get("trainers", []):
        out.append(f"  trainer {t['id']}: starts from {t['start']}, grows on {t['on']} text, "
                   f"{'moves the three values directly' if t.get('how') == 'flips' else 'reads the ordinary way'}, span {t['span']:g}: "
                   f"{t['births']} births, {t['kept']} kept" + (f" (bred from {t['parent']})" if t.get("parent") else ""))
    if births:
        b = births[-1]
        out.append(f"  last birth {b['when']}: cell {b['cell']} by {b['trainer']}, {'kept' if b['kept'] else 'removed at birth'}: {b['why']}")
    return out + [""]


def chart():
    reg, w, sp = runtime.registry(), use.wins(), spawn.spawned()
    cells = {**{k: v.get("part", "") for k, v in reg.items()}, **{k: v["part"] for k, v in sp.items()}}
    placed, out = set(), ["HiveMIND: one order in, one answer out", ""]
    n_work = 0
    for team, purpose, roles, prefixes in TEAMS:
        out.append(f"{team.upper()}: {purpose}")
        for r in roles:
            if r in config.GGUF_ROSTER:
                out.append(f"  member  {r:<14} {_brain(r)}")
        for name, part in sorted(cells.items()):
            owner = part.split(":")[0].strip().lower()
            if name in placed or not any(owner == p or owner.startswith(p) for p in prefixes):
                continue
            placed.add(name)
            line = _cell_line(name, reg.get(name, {}), w, sp)
            n_work += line.startswith("working")
            out.append(f"    cell  {name:<22} {part.split(':', 1)[-1].strip()[:70]}")
            out.append(f"          {'':<22} {line}")
        out.append("")
    from . import school
    rec = school.record()
    if rec:
        out.append("SCHOOL: small models learning a bigger member's job from that member (python -m team school)")
        for role, v in rec.items():
            line = (f"untouched {v['untouched_agrees']:.0%}, taught {v['taught_agrees']:.0%} agreement with the teacher on "
                    f"{v['test_lessons']} unseen lessons" if "taught_agrees" in v else v.get("why", ""))
            who = (f"{v.get('scheme', 'alone')}: " + ", ".join((v.get("general") or [])[:1 if v.get("scheme", "alone") == "alone" else 9]
                                                             + (v.get("narrow") or []))) if v.get("general") else "no specialist yet"
            status = ("GRADUATED: holds the job" if v.get("graduated") else
                      "in school; ahead of the untouched student, so it holds the job in the small-only hive"
                      if v.get("ahead") else "in school; the teacher keeps the job")
            out.append(f"  {role:<14} {MODELS.get(v['student'], v['student'])} learning from {MODELS.get(v['teacher'], v['teacher'])}: "
                       f"{status}; {v['lessons']} lessons; {line}; its specialists: {who}")
        out.append("")
    from . import recruit
    recs = {k: v for k, v in recruit.record().items() if not k.startswith("_")}
    if recs:
        out.append("RECRUITS: small models of other families the hive found and tried itself (python -m team recruit)")
        for name, v in recs.items():
            tries = "; ".join(f"{role}: {t['alone']:.0%} alone (untouched student {t['untouched_student']:.0%})"
                              + (f", {t.get('student') or t.get('enrolled')}" if t.get("student") or t.get("enrolled") else ", not enrolled")
                              for role, t in (v.get("tryouts") or {}).items()) or "not tried yet"
            out.append(f"  {name:<22} {v['base']} ({v['params'] / 1e9:.2f}B, {v['license']}): {tries}")
        out.append("")
    out += body_lines()
    rest = [n for n in cells if n not in placed]
    if rest:
        out.append("UNPLACED CELLS: " + ", ".join(sorted(rest)))
    out.append(f"{len(config.GGUF_ROSTER)} member roles on {len(set(b.split('+')[0] for b in config.GGUF_ROSTER.values()))} "
               f"models; {len(cells)} cells, {n_work} working; {len(sp)} jobs the hive noticed by itself.")
    return "\n".join(out)


def main():
    print(chart())
    return 0
