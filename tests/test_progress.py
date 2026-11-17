"""The hive's progress graphs, and the loop they close: practice drawn where the exams show the body weakest."""
import json
import xml.dom.minidom

from training import exam, grow, progress


def _record(tmp_path):
    rows = [
        {"generation": "g9", "when": "2026-11-14 10:00", "rows": 200, "dna": "t17", "trial": True,
         "arms": {"dna": {"passed": 7, "tasks": 64}, "after": {"passed": 13, "tasks": 64, "unpractised": [0, 9]}}},
        {"generation": "g24", "when": "2026-11-15 02:00", "rows": 414, "dna": "t80",
         "arms": {"after": {"passed": 11, "tasks": 32, "unpractised": [1, 5],
                            "kinds": {"days between two dates": [1, 1], "operate a website": [0, 2], "write and run a program": [1, 1]}}}},
        {"generation": "g27", "when": "2026-11-15 17:00", "rows": 657, "dna": "t80",
         "arms": {"after": {"passed": 15, "tasks": 32, "unpractised": [0, 7],
                            "kinds": {"days between two dates": [1, 1], "operate a website": [0, 1], "a unit conversion": [0, 1]}}}},
        {"generation": "g28", "when": "2026-11-15 18:00", "rows": 0, "arms": {"after": {"passed": 0, "tasks": 0}}},  # no pulse: not drawn
    ]
    rec = tmp_path / "generations.jsonl"
    rec.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"dna": "t80", "levels": {"h_web": 1}}))
    return rec, body


def test_the_record_is_drawn_as_graphs_and_a_page_that_says_where_the_body_stands(tmp_path):
    rec, body = _record(tmp_path)
    out = progress.draw(rec, tmp_path / "docs" / "progress", body)
    assert out["generations"] == 3 and out["dna"] == "t80"
    for name in ("score", "carry", "kinds", "rows"):
        svg = (tmp_path / "docs" / "progress" / f"{name}.svg").read_text()
        xml.dom.minidom.parseString(svg)  # every graph is a well-formed SVG
        assert "prefers-color-scheme: dark" in svg  # and has its own dark steps
    score = (tmp_path / "docs" / "progress" / "score.svg").read_text()
    assert "15 of 32" in score and "1.7B body" in score and "8B body" in score and "DNA alone" in score
    assert "g9 (1.7B, a trial): 13 of 64" in score  # every point says its numbers on hover
    page = (tmp_path / "docs" / "PROGRESS.md").read_text()
    assert "**The goal:**" in page and "g27 of the 8B body passed 15 of 32" in page and "progress/kinds.svg" in page
    assert "h_web 1" in page and "## Where it practises most next" in page


def test_kinds_are_shown_weakest_first_and_only_for_the_bodys_dna(tmp_path):
    rec, _ = _record(tmp_path)
    table, names = progress.kinds(progress.load(rec), "t80")
    assert names == ["g24", "g27"]
    assert list(table)[0] == "operate a website"  # 0 of 3: the weakest
    assert table["a unit conversion"] == [None, (0, 1)]  # not in g24's exam: an empty cell
    assert progress.kinds(progress.load(rec), "t40") == ({}, [])


def _maker(kind):
    def make(r):
        return "f", kind, f"{kind} task {r.random()} at level {getattr(r, 'level', 0)}", lambda ans: True
    make.__name__ = "m_" + kind.replace(" ", "_")
    return make


def test_ladder_practice_is_drawn_where_the_exams_show_the_body_at_its_edge(tmp_path, monkeypatch):
    rec, _ = _record(tmp_path)
    w = grow.edge_weights("t80", record=rec)
    assert set(w) == {"days between two dates", "operate a website", "write and run a program", "a unit conversion"}
    assert grow.edge_weights("t17", record=rec) == {}  # the 1.7B's record has no kinds: nothing to say about the 8B
    from training import exam_hard
    monkeypatch.setattr(exam, "MAKERS", [_maker("days between two dates"), _maker("a unit conversion")])
    monkeypatch.setattr(exam_hard, "MAKERS", [_maker("operate a website"), _maker("write and run a program")])
    monkeypatch.setattr(exam, "LEVELED", set(exam.LEVELED) | {"m_operate_a_website"})
    lean = {k: 0.001 for k in w}
    lean["days between two dates"] = 50.0
    tasks = exam.exam(7, 16, level="ladder", weights=lean, levels={"compound": 2, "m_operate_a_website": 2})
    single = [t for t in tasks if not t[0].startswith("c")]
    assert len(single) == 8 and len(tasks) == 16  # half single, half of several parts, as before
    assert sum(t[2] == "days between two dates" for t in single) >= 6  # drawn by the weights
    plain = [t for t in exam.exam(7, 16, level="ladder", levels={"compound": 2}) if not t[0].startswith("c")]
    assert len(plain) == 4 and sum(t[2] == "days between two dates" for t in plain) == 1  # without weights: each kind once, as before
    # the ladder's levels still set how hard each kind is when it is drawn by the weights
    web = [t for t in exam.exam(7, 8, level="ladder", weights={"operate a website": 1.0}, levels={"m_operate_a_website": 2}) if t[2] == "operate a website"]
    assert web and all("at level 2" in t[3] for t in web)
    # practice uses the weights of the body's own DNA
    monkeypatch.setattr(grow, "_dna", lambda: "t80")
    seen = {}
    monkeypatch.setattr(grow, "edge_weights", lambda dna="t17", **k: seen.setdefault("dna", dna) and {})
    monkeypatch.setattr(exam, "exam", lambda *a, **k: seen.setdefault("weights", k.get("weights")) and [] or [])
    grow.practice(1, 2, level="ladder", out=tmp_path / "rows.jsonl", log=lambda *a, **k: None)
    assert seen["dna"] == "t80"


def test_hard_easy_and_held_out_are_drawn_and_a_generation_that_lost_seats_or_slices_is_marked():
    gens = [
        {"generation": "g34", "when": "1", "dna": "t80", "arms": {"after": {"passed": 37, "tasks": 64, "hard": [6, 32], "easy": [31, 32], "unpractised": [1, 9]}}},
        {"generation": "g38", "when": "2", "dna": "t80", "dead_seats": 1, "lost_slices": [7, 24],
         "arms": {"after": {"passed": 30, "tasks": 48, "hard": [8, 24], "easy": [22, 24], "unpractised": [1, 7]}}},
    ]
    svg = progress.split_chart(gens)
    xml.dom.minidom.parseString(svg)
    for words in ("g34, hard kinds: 6 of 32", "g34, easy kinds: 31 of 32", "g34, held-out kinds (never practised): 1 of 9",
                  "g38: 1 pulse seat dead, 7 of 24 train slices lost", "seats or slices lost"):
        assert words in svg
    assert svg.count('class="lost"') == 2  # one mark for g38, one in the legend
    assert progress._losses(gens[0]) == "" and progress._losses({"lost_slices": 3}) == "3 train slices lost"


def test_hours_are_drawn_by_step_when_the_record_says_them_and_named_missing_when_not(tmp_path):
    gens = [{"generation": "g39", "when": "1", "dna": "t80", "minutes_by_step": {"practice": 63, "train": 175, "pulse": 60, "record": 2},
             "arms": {"after": {"passed": 1, "tasks": 2}}},
            {"generation": "g40", "when": "2", "dna": "t80", "hours": 4.5, "arms": {"after": {"passed": 1, "tasks": 2}}},
            {"generation": "g41", "when": "3", "dna": "t80", "arms": {"after": {"passed": 1, "tasks": 2}}}]
    svg = progress.hours_chart(gens)
    xml.dom.minidom.parseString(svg)
    assert "g39, train: 175 min" in svg and "5.0 h" in svg and "4.5 h" in svg and "g41" not in svg
    assert "stroke-dasharray" in svg  # the bar of 5 hours
    empty = progress.hours_chart(gens[2:])
    assert "says its hours yet" in empty and "minutes_by_step" in empty
    rec = tmp_path / "generations.jsonl"
    rec.write_text("\n".join(json.dumps(g) for g in gens[2:]))
    progress.draw(rec, tmp_path / "docs" / "progress", tmp_path / "none.json")
    for name in ("split", "hours"):
        xml.dom.minidom.parseString((tmp_path / "docs" / "progress" / f"{name}.svg").read_text())
    page = (tmp_path / "docs" / "PROGRESS.md").read_text()
    assert "progress/split.svg" in page and "progress/hours.svg" in page and "the record job is to write `minutes_by_step`" in page
