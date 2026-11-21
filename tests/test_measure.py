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


def test_every_hard_family_counts_in_its_declared_group(tmp_path):
    from training import kinds, reads

    tasks = []
    for i, mod in enumerate(kinds.HARD_KINDS):
        _, label, _, _ = kinds.sample(mod.KIND)
        tasks.append({"id": f"h{i}", "kind": label, "ok": i % 2 == 0})
    total = sum(t["ok"] for t in tasks)
    (tmp_path / "exam.json").write_text(json.dumps({"summary": {"tasks": len(tasks), "passed": total, "minutes": 1},
                                                     "tasks": tasks}))
    arm = grow_record.arm([tmp_path])
    for key, subset in (("taught", [t for m, t in zip(kinds.HARD_KINDS, tasks) if m.lesson and not m.HELD_OUT]),
                        ("unpractised", [t for m, t in zip(kinds.HARD_KINDS, tasks) if m.HELD_OUT])):
        assert arm[key] == [sum(t["ok"] for t in subset), len(subset)]
    assert arm["taught"][1] + arm["unpractised"][1] == arm["hard"][1]
    # Models may gain or lose families in future. The recording-time groups stay authoritative.
    assert kinds.hard_scores(dict(arm, kinds={})) == (arm["taught"], arm["unpractised"])
    # The previous schema counted just the first four held-out families. Recover from the complete roll.
    old = {k: v for k, v in arm.items() if k != "taught"}
    old["unpractised"] = [0, 1]
    line = {"generation": "g-test", "arms": {"after": old}}
    assert reads.generation_entry(line)["hard"] == arm["taught"]
    assert reads.generation_entry(line)["held_out"] == progress._held_out(line) == arm["unpractised"]
    assert kinds.hard_scores({"unpractised": [0, 9]}) == ([0, 0], [0, 9])
    assert kinds.hard_scores({}) == ([0, 0], [0, 0])


def test_member_success_and_delivery_are_compared_on_covered_cases(tmp_path):
    from training import reads

    tasks = [
        {"id": "h1", "ok": False, "members": [{"ok": True}, {"ok": False}]},
        {"id": "h2", "ok": True, "members": [{"ok": True}]},
        {"id": "h3", "ok": True, "members": [{"ok": False}]},
        {"id": "e1", "ok": False, "members": [{"ok": False}]},
        {"id": "h4", "ok": False, "members": [], "agreed": True},
        {"id": "h5", "ok": False, "members": [{"ok": False}, {}]},
        {"id": "e2", "ok": False, "members": [{}, {"ok": True}]},
        {"id": "e3", "members": [{"ok": True}]},
    ]
    (tmp_path / "grades.json").write_text(json.dumps({"summary": {"tasks": len(tasks), "passed": 2, "minutes": 1},
                                                     "tasks": tasks}))
    arm = grow_record.arm([tmp_path])
    assert arm["member_delivery"]["all"] == dict(both=1, member_only=2, delivery_only=1, neither=1)
    assert arm["member_delivery"]["hard"] == dict(both=1, member_only=1, delivery_only=1, neither=0)
    old = {k: v for k, v in arm.items() if k != "member_delivery"}
    table = reads.member_delivery_table({"arms": {"before": old, "after": arm}})
    assert "| before | hard | unrecorded | – | – | – | – |" in table
    assert "| after | hard | 3 of 5 | 2 | 2 | 1 | 1 |" in table
    assert "| after | all | 5 of 8 | 3 | 2 | 2 | 1 |" in table


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


def test_the_parts_graph_is_drawn_and_the_default_gate_keeps_all_seeds_and_lessons(tmp_path):
    gens = [{"generation": "g33", "when": "2026-11-16 10:00", "dna": "t80", "rows": 900,
             "arms": {"after": {"passed": 30, "tasks": 64, "hard": [8, 28], "easy": [18, 20], "several": [4, 16]}}}]
    svg = progress.parts_chart(gens)
    xml.dom.minidom.parseString(svg)
    assert "8 of 28" in svg and "hard kinds" in svg and "tasks of several parts" in svg
    flow = (ROOT / ".github" / "workflows" / "grow.yml").read_text()
    seed_line, = (line for line in flow.splitlines() if "seed: ${{ fromJSON" in line)
    assert "vars.HIVE_GATE_SPRT == '1' && '[1,2,3,4]' || '[1,2,3,4,5,6,7,8]'" in seed_line
    assert '--per-kind "$LESSONS"' in flow and "vars.HIVE_LESSONS || '12'" in flow
