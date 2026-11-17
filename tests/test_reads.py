"""The read the record job writes (training/reads.py): docs/reads/gNN.md from a generation's record, gate, train slices
and gather, with the chain by taught hard kind and the next piece chosen by the rules of docs/DECISIONS.md. Small
made-up files, no network."""
import json
import sys
import xml.dom.minidom
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training import grow_record, progress, reads  # noqa: E402

TAUGHT = list(reads.taught_hard().values())
UNTAUGHT = "sum up a text"  # an easy kind with only its kept-back lessons: none trained on


def _gate(home, arm, seed, tasks):
    d = home / f"gate-{arm}-{seed}"
    d.mkdir(parents=True)
    passed = sum(t["ok"] for t in tasks)
    (d / f"{seed}_mixed.json").write_text(json.dumps({"summary": {"seed": seed, "passed": passed, "tasks": len(tasks), "minutes": 30},
                                                      "tasks": tasks}))


def _task(i, kind, ok, who, member_ok, hard=True):
    return {"id": f"{'h' if hard else 'e'}{i:02d}", "ok": ok, "kind": kind, "task": "t",
            "members": [{"who": f"t80+{who}", "ok": member_ok, "member": 1}]}


def _arm(tasks):
    kinds = {}
    for t in tasks:
        k = kinds.setdefault(t["kind"], [0, 0])
        k[0] += t["ok"]
        k[1] += 1
    hard = [t for t in tasks if t["id"][0] == "h"]
    easy = [t for t in tasks if t["id"][0] == "e"]
    return {"passed": sum(t["ok"] for t in tasks), "tasks": len(tasks), "seeds": 1, "kinds": kinds,
            "hard": [sum(t["ok"] for t in hard), len(hard)], "easy": [sum(t["ok"] for t in easy), len(easy)], "unpractised": [0, 0]}


def build(tmp_path, lessons_right=12, used=(9, 9), fall_taught=0.5, fall_untaught=0.1, child_ok=True, parent_ok=False,
          body_ok=False, prev_taught_ok=False):
    """Every file of one generation, g40, made up; returns the read's text and its next-piece line."""
    gate = tmp_path / "gate"
    after = [_task(i, k, body_ok, "g40code", child_ok) for i, k in enumerate(TAUGHT)] + [_task(50, "a sum in words", True, "g40code", True, hard=False)]
    before = [_task(i, k, False, "g34code", parent_ok) for i, k in enumerate(TAUGHT)] + [_task(50, "a sum in words", True, "g34code", True, hard=False)]
    _gate(gate, "after", 1, after)
    _gate(gate, "before", 1, before)
    prev_tasks = [_task(i, k, prev_taught_ok, "g34code", prev_taught_ok) for i, k in enumerate(TAUGHT)] * 2
    record = tmp_path / "generations.jsonl"
    lines = [{"generation": "g39", "when": "2026-11-17 10:00", "arms": {"after": _arm(prev_tasks)}, "hours": 6.5, "started_by": "line"},
             {"generation": "g40", "when": "2026-11-17 16:00", "verdict": "kept", "kept": True, "why": "the body grows: after 9 of 10",
              "cells": ["g40code"], "parents": {"g40code": "g34code"}, "arms": {"after": _arm(after * 2 if body_ok else after), "before": _arm(before)}}]
    record.write_text("".join(json.dumps(x) + "\n" for x in lines))
    rows = [{"who": "lesson", "kind": k, "task": f"{k} lesson {i}", "gen": "g40", "type": "first", "seed": f"lesson:g40:{i}",
             "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": f"{k} {i}"}], "output": "x"}
            for k in TAUGHT for i in range(6)]
    rows += [{"who": "lesson", "kind": UNTAUGHT, "task": f"u{i}", "gen": "g30", "type": "first",
              "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": f"u{i}"}], "output": "y"} for i in range(2)]
    rows_file = tmp_path / "rows.jsonl"
    rows_file.write_text("".join(json.dumps(r) + "\n" for r in rows))
    kept = {k: {"lessons": 2, "rows": 2, "before": 1.0, "after": 1.0 - fall_taught} for k in TAUGHT}
    kept[UNTAUGHT] = {"lessons": 2, "rows": 2, "before": 1.0, "after": 1.0 - fall_untaught}
    slices = [{"job": f"train (g40code, {n})", "conclusion": "success", "long": 3, "max_len": 1152,
               "record": {"member": "t80+g40code", "shard": f"{n}/2", "kept_back": kept,
                          "subjects": [{"subject": f"{k} · first · new", "rows": u, "passes": 3} for k in TAUGHT]}}
              for n, u in enumerate(used)]
    jobs = [{"name": "practice (1)", "started_at": "2026-11-17T10:00:00Z", "completed_at": "2026-11-17T12:00:00Z", "conclusion": "success"},
            {"name": "dream (1)", "started_at": "2026-11-17T10:00:00Z", "completed_at": "2026-11-17T10:50:00Z", "conclusion": "success"},
            {"name": "train (g40code, 0)", "started_at": "2026-11-17T12:10:00Z", "completed_at": "2026-11-17T15:00:00Z", "conclusion": "success"},
            {"name": "train (g40code, 1)", "started_at": "2026-11-17T12:10:00Z", "completed_at": "2026-11-17T13:00:00Z", "conclusion": "failure"},
            {"name": "gate (after, 1)", "started_at": "2026-11-17T15:05:00Z", "completed_at": "2026-11-17T15:55:00Z", "conclusion": "success"},
            {"name": "bench", "started_at": "2026-11-17T12:00:00Z", "completed_at": "2026-11-17T12:00:00Z", "conclusion": "skipped"},
            {"name": "record", "started_at": "2026-11-17T15:56:00Z", "completed_at": "2026-11-17T16:00:00Z", "conclusion": "success"}]
    minutes, hours = reads.hours_of(jobs)
    facts = {"run": "1", "repo": "o/r", "jobs": jobs, "minutes_by_step": minutes, "hours": hours, "lost_slices": reads.lost_slices(jobs),
             "dead_seats": 0, "slices": slices, "started_by": "line", "first_try": [3, 10]}
    lessons = tmp_path / "lessons.json"
    lessons.write_text(json.dumps({"lessons": 120, "by_kind": {k: [lessons_right, 12] for k in TAUGHT}}) + "\n")
    out = tmp_path / "reads"
    said = reads.write("g40", facts, gate, rows_file, lessons, record, out, tmp_path / "chain.svg")
    text = (out / "g40.md").read_text()
    assert (out / "latest.md").read_text() == text
    return text, said


def test_the_read_has_every_section(tmp_path):
    text, said = build(tmp_path)
    assert text.startswith("# The read of g40")
    for words in ("## The numbers", "| Easy kinds passed | 1 of 1 | - | 1 of 1 |", "Hard kinds that have lessons",
                  "Hard kinds never practised (held out)", "| Right at the first try (practice) | 0.30 (3 of 10) | - | - |",
                  "| Hours for one generation | 6.0 | 6.5 | - |", "| Generations recorded with nobody's hand | 2 | 1 | - |",
                  "## The chain, by taught hard kind", "## Hours", "| practice | 120 |", "| dream | 50 |", "| train | 170 |",
                  "| gate | 50 |", "Train slices lost: 1 of 2", "Pulse seats whose server died: 0", "## Next piece",
                  "![The chain by kind](../progress/chain.svg)"):
        assert words in text, words
    # one row a taught hard kind: lessons, rows, kept-back loss and its gap, the child and its parent alone, the body
    assert len(TAUGHT) == 9
    for k in TAUGHT:
        assert f"| {k} | 12 of 12 | 0 of 18 | 1.000 -> 0.500 | +40 | 1 of 1 | 0 of 1 | 0 of 1 | 0 of 1 |" in text, k
    assert f"mean fall of the kinds none of whose lessons were trained on ({UNTAUGHT}: 10 points)" in text
    assert text.count("next piece:") == 1 and said in text
    xml.dom.minidom.parseString((tmp_path / "chain.svg").read_text())
    assert "child alone right" in (tmp_path / "chain.svg").read_text()


@pytest.mark.parametrize("kw, rule, piece", [
    (dict(lessons_right=5), 1, "lessons: mend"),
    (dict(used=(9, 2)), 2, "T4: shorter lessons"),
    (dict(fall_taught=0.2), 3, "dose:"),
    (dict(child_ok=True, parent_ok=False, body_ok=False), 4, "R1: a right member is not lost"),
    (dict(child_ok=False), 5, "T3:"),
    (dict(child_ok=True, parent_ok=True, body_ok=True, prev_taught_ok=True), 6, "K1:"),
    (dict(child_ok=True, parent_ok=True, body_ok=True), 7, "none"),
])
def test_the_next_piece_is_the_first_rule_that_holds_for_the_most_kinds(tmp_path, kw, rule, piece):
    text, said = build(tmp_path, **kw)
    assert said.startswith("next piece: " + piece), said
    assert f"(rule {rule}" in said


def test_a_rule_that_holds_for_more_kinds_wins_over_an_earlier_one_and_ties_go_to_the_earlier():
    row = lambda k, **v: dict({"kind": k, "lessons": [12, 12], "left": [0, 10], "gap": 40.0, "child": [1, 1], "parent": [0, 1],  # noqa: E731
                               "body": [0, 1], "before": [0, 1]}, **v)
    line = {"arms": {"after": {"kinds": {}}}}
    rows = [row("a", lessons=[2, 12]), row("b", gap=5.0), row("c", gap=5.0)]
    assert reads.next_piece(rows, line)[:3] == (3, reads.RULES[2][2], ["b", "c"])
    rows = [row("a", lessons=[2, 12]), row("b", gap=5.0)]
    assert reads.next_piece(rows, line)[0] == 1
    # an unmeasured link holds no rule
    assert reads.next_piece([row("a", lessons=None, left=None, gap=None, child=None)], line)[:2] == (7, "none")


def test_g38_without_by_kind_counts_lessons_from_rows_and_the_dropped_list():
    rows = [{"who": "lesson", "gen": "g38", "kind": "walk a site over several pages", "seed": f"lesson:g38:h_walk:{i}"} for i in range(5)]
    got, how = reads.lessons_by_kind({"lessons": 300, "right": 5, "dropped": ["h_walk: the site refused", "out of time"]}, rows, "g38")
    assert how == "rows" and got == {"walk a site over several pages": [5, 6]}
    got, how = reads.lessons_by_kind({"by_kind": {"x": [3, 12]}}, rows, "g38")
    assert how == "gather" and got == {"x": [3, 12]}


def test_the_log_parsers_and_the_hours():
    log = "2026-11-17T01:00:00.1Z 26 rows are longer than 1044 pieces and are left out\n2026-11-17T01:00:01.1Z {\n \"member\": \"t80+g\",\n \"rows\": 3\n}\n"
    text = reads.strip_log(log)
    assert reads.long_in_log(text) == (26, 1044) and reads.record_in_log(text) == {"member": "t80+g", "rows": 3}
    assert reads.lessons_in_log('x\n{"lessons": 3, "by_kind": {}}\n') == {"lessons": 3, "by_kind": {}}
    assert reads.stage_of("train (g40code, code, 1)") == "train" and reads.stage_of("fresh") is None
    m, h = reads.hours_of([{"name": "practice (1)", "started_at": "2026-11-17T10:00:00Z", "completed_at": "2026-11-17T11:30:00Z"},
                           {"name": "record", "started_at": "2026-11-17T11:30:00Z", "completed_at": None}], now=reads._when("2026-11-17T12:00:00Z"))
    assert m == {"practice": 90, "record": 30} and h == 2.0


def test_the_record_line_takes_only_known_numbers_from_the_facts(tmp_path):
    got = reads.record_fields({"minutes_by_step": {"practice": 120, "evil": 3, "train": "x"}, "hours": 6.0, "dead_seats": 1,
                               "lost_slices": [7, 24], "first_try": [3, 10], "started_by": "line", "junk": 1})
    assert got == {"minutes_by_step": {"practice": 120}, "hours": 6.0, "dead_seats": 1, "lost_slices": [7, 24], "first_try": [3, 10], "started_by": "line"}
    assert reads.record_fields({"hours": "6", "lost_slices": [1], "started_by": "me"}) == {}
    # what progress.py draws from it: the hours by step, the lost slices and dead seats
    g = {"generation": "g40", "minutes_by_step": got["minutes_by_step"], "hours": 6.0, "dead_seats": 1, "lost_slices": [7, 24]}
    assert progress._hours(g) == {"practice": 120.0} and progress._losses(g) == "1 pulse seat dead, 7 of 24 train slices lost"
    assert progress._hours({"minutes_by_step": {"pulse": 60, "dreams": 5}}) == {"gate": 60.0, "dream": 5.0}  # the older names


def test_the_gate_writes_the_facts_into_the_record_line(tmp_path, monkeypatch):
    rec, body = tmp_path / "generations.jsonl", tmp_path / "body.json"
    body.write_text(json.dumps({"dna": "t80", "cells": [], "parents": {}}))
    monkeypatch.setattr(grow_record, "RECORD", rec)
    monkeypatch.setattr(grow_record, "BODY", body)
    got = tmp_path / "got"
    got.mkdir()
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps({"minutes_by_step": {"train": 170}, "hours": 5.5, "dead_seats": 0, "lost_slices": [1, 20], "started_by": "line"}))
    assert grow_record.gate([str(tmp_path / "gate"), str(got), "g40", "--dna", "t80", "--facts", str(facts)]) == 0
    line = json.loads(rec.read_text().splitlines()[-1])
    assert line["minutes_by_step"] == {"train": 170} and line["hours"] == 5.5 and line["lost_slices"] == [1, 20] and line["started_by"] == "line"


def test_the_record_job_writes_the_read_and_redraws_and_commits_it():
    import yaml
    steps = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())["jobs"]["record"]["steps"]
    text = "\n".join(s.get("run", "") for s in steps)
    assert "training/reads.py facts" in text and "--facts facts.json" in text
    assert "training/reads.py write \"$GEN\"" in text and "training/progress.py" in text and "scripts/knowledge.py" in text
    assert "docs/reads" in text.split("git add", 1)[1] and "docs/KNOWLEDGE.md" in text.split("git add", 1)[1]
    assert any(s.get("with", {}).get("name") == "lessons" for s in steps)
