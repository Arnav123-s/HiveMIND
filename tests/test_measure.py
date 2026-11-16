"""Agent C's plan, pieces 3 and 4: a pulse that can show learning (hard kinds apart from easy ones, on four seeds),
and practice drawn where some member is right on a kind and the body is not."""
import json
import xml.dom.minidom
from pathlib import Path

from training import grow, grow_record, progress

ROOT = Path(__file__).resolve().parents[1]


def test_the_pulse_counts_hard_easy_and_several_apart(tmp_path):
    (tmp_path / "s1").mkdir()
    (tmp_path / "s1" / "exam.json").write_text(json.dumps({"summary": {"passed": 3, "tasks": 5, "minutes": 9}, "tasks": [
        {"id": "h1_00", "kind": "walk a site over several pages", "ok": False}, {"id": "h1_01", "kind": "a log read and counted into a file", "ok": True},
        {"id": "e1_00", "kind": "a sum in words", "ok": True}, {"id": "e1_01", "kind": "days between two dates", "ok": True},
        {"id": "c1_00", "kind": "several tasks in one", "ok": False}]}))
    a = grow_record.arm([tmp_path / "s1"])
    assert a["hard"] == [1, 2] and a["easy"] == [2, 2] and a["several"] == [0, 1] and a["passed"] == 3


def test_practice_is_counted_kind_by_kind_and_older_generations_weigh_half(tmp_path):
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "practice.json").write_text(json.dumps({"tasks": [
        {"maker": "h_walk", "kind": "walk a site over several pages", "ok": False, "some": True},
        {"maker": "h_walk", "kind": "walk a site over several pages", "ok": False, "some": False},
        {"maker": "m_days", "kind": "days between two dates", "ok": True, "some": True},
        {"maker": "x", "kind": "<script>", "ok": True}]}))  # a name of no known shape is not taken
    got = grow_record.practice_kinds({"days between two dates": [4, 4, 4]}, [tmp_path / "p"])
    assert got == {"days between two dates": [3.0, 3.0, 3.0], "walk a site over several pages": [2, 0, 1]}


def test_practice_goes_where_some_member_is_right_and_the_body_is_not(tmp_path):
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"dna": "t80", "kinds": {
        "learned": [10, 10, 10],          # always right: nothing to gain
        "half": [10, 0, 5],               # some member right half the time, the body never: the most to gain
        "hopeless": [10, 0, 0]}}))        # nobody right: no row to make (lessons start such a kind)
    w = grow.edge_weights("t80", record=tmp_path / "none.jsonl", body=body)
    assert w["half"] > w["hopeless"] and w["half"] > w["learned"]
    assert grow.edge_weights("t17", record=tmp_path / "none.jsonl", body=body) == {}  # another DNA's counts say nothing here


def test_the_parts_graph_is_drawn_and_the_line_sits_four_seeds_with_three_lessons_a_kind(tmp_path):
    gens = [{"generation": "g33", "when": "2026-11-16 10:00", "dna": "t80", "rows": 900,
             "arms": {"after": {"passed": 30, "tasks": 64, "hard": [8, 28], "easy": [18, 20], "several": [4, 16]}}}]
    svg = progress.parts_chart(gens)
    xml.dom.minidom.parseString(svg)
    assert "8 of 28" in svg and "hard kinds" in svg and "tasks of several parts" in svg
    flow = (ROOT / ".github" / "workflows" / "grow.yml").read_text()
    assert "seed: ${{ fromJSON('[1,2,3,4]') }}" in flow and "--per-kind 3" in flow
