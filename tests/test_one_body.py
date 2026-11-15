"""The body as one: the trunk (the cells averaged into one edit), lessons that grow harder, rows that are never lost."""
import json

import numpy as np

from team import parts, solo, ternary
from training import exam, exam_hard, grow, grow_record, lineage, merge

Q = "base_model.model.model.layers.3.self_attn.q_proj"
U = "base_model.model.model.layers.3.mlp.up_proj"


def _edit(seed, r=4, din=24, dout=12):
    g = np.random.default_rng(seed)
    return {Q: (g.normal(size=(r, din)).astype("f4"), g.normal(size=(dout, r)).astype("f4")),
            U: (g.normal(size=(r, din)).astype("f4"), g.normal(size=(2 * dout, r)).astype("f4"))}


def _full(e, k):
    return e[k][1] @ e[k][0]


# ---- the trunk -------------------------------------------------------------------------------------------------------
def test_the_trunk_is_exactly_the_average_of_the_cells_and_the_best_edit_of_its_rank():
    cells = [_edit(i) for i in range(3)]
    want = sum(_full(e, Q) for e in cells) / 3
    whole, kept = merge.merge(cells, rank=12)  # three edits of rank 4: nothing is lost at rank 12
    assert np.abs(_full(whole, Q) - want).max() < 1e-5 and kept > 0.9999
    cut, kept = merge.merge(cells, rank=4)
    u, s, vt = np.linalg.svd(want)
    assert np.abs(_full(cut, Q) - (u[:, :4] * s[:4]) @ vt[:4]).max() < 1e-5  # no edit of rank 4 is nearer
    assert 0.5 < kept < 1 and cut[Q][0].shape == (4, 24) and cut[U][1].shape == (24, 4)


def test_a_child_starts_as_its_parent_pulled_toward_the_trunk(tmp_path):
    parent, trunk = _edit(1), _edit(2, r=8)  # the trunk may have a higher rank than a cell
    merge.save(parent, tmp_path / "p.safetensors")
    merge.save(trunk, tmp_path / "t.safetensors")
    assert merge.main(["mix", str(tmp_path / "c.safetensors"), str(tmp_path / "p.safetensors"), str(tmp_path / "t.safetensors"), "--pull", "0.25", "--rank", "12"]) == 0
    child = merge.load(tmp_path / "c.safetensors")
    assert np.abs(_full(child, U) - (0.75 * _full(parent, U) + 0.25 * _full(trunk, U))).max() < 1e-5
    # an edit merged with itself is itself, and an edit of lower rank is padded, not broken
    same, kept = merge.merge([parent, parent], rank=6)
    assert np.abs(_full(same, Q) - _full(parent, Q)).max() < 1e-5 and same[Q][0].shape[0] == 6 and kept > 0.9999


def test_the_trunk_is_made_of_the_newest_cell_of_every_line():
    body = {"dna": "t80", "generation": 25, "cells": ["g24sources", "g24code", "g24data", "g24words", "g25sources", "g25code", "g25data", "g25words"],
            "parents": {f"g25{o}": f"g24{o}" for o in lineage.ORGANS}}
    kids = [c["name"] for c in lineage.plan("g26", "t80", body)]
    assert kids == ["g26sources", "g26code", "g26data", "g26words"]  # second children of the grown cells; the g25 are young
    got = lineage.trunk_of("g26", "t80", kids[:3], body)  # the words child did not grow
    # every g24 cell lives on in a child; the young g25 cells and the children that grew are the newest of their lines
    assert got["name"] == "g26trunk" and got["of"] == ["g25sources", "g25code", "g25data", "g25words", "g26sources", "g26code", "g26data"]
    assert got["older"] == ["g25sources", "g25code", "g25data", "g25words"]
    assert lineage.members("t80", dict(body, trunk="g25trunk"))[:2] == ["g25trunk", "g24sources"]
    assert lineage.members("t17", body) == [] and lineage.members("t80", {"dna": "t80", "cells": [], "trunk": "g1trunk"}) == []


def test_the_trunk_sits_first_and_in_practice_every_cell_takes_its_turn_beside_it(tmp_path, monkeypatch):
    who = "t80+g2code,t80+g1data,t80+g2trunk,t80+g1code,t80+g1trunk,t80+g2words"
    monkeypatch.setenv("HIVE_MEMBERS", who)
    monkeypatch.delenv("HIVE_SEATING", raising=False)
    monkeypatch.delenv("HIVE_ROTATE", raising=False)
    body = tmp_path / "body.json"
    body.write_text(json.dumps({"dna": "t80", "cells": [], "parents": {"g2code": "g1code"}}))
    monkeypatch.setattr(ternary, "BODY", body)
    task = "Write a python function that sums the primes below 100"
    seats = ternary.seating(task, "")
    # the newest trunk, then the newest cell of the task's organ, then a cell of another line; an older trunk never sits
    assert seats[:3] == ["t80+g2trunk", "t80+g2code", "t80+g2words"] and "t80+g1trunk" not in seats
    firsts = set()
    for turn in range(8):
        monkeypatch.setenv("HIVE_ROTATE", str(turn))
        s = ternary.seating(task, "")
        assert s[0] == "t80+g2trunk" and sorted(s) == sorted(seats)
        firsts.add(s[1])
    assert firsts == {"t80+g2code", "t80+g1data", "t80+g1code", "t80+g2words"}
    assert ternary.is_trunk("t80+g12trunk") and not ternary.is_trunk("t80+g12code") and ternary.leans("t80+g12trunk") == ""


# ---- lessons that grow harder ----------------------------------------------------------------------------------------
def test_several_tasks_in_one_are_checked_part_by_part():
    makers = [exam.m_percent, exam.m_days, exam.m_weekday]
    field, kind, task, check = exam.compound("s:1", 2, makers)
    asked = parts.of_task(task)
    assert kind == "several tasks in one" and list(asked) == ["A", "B"] and check.maker == "compound" and check.level == 2
    assert all(len(p) == 3 for p in check.parts)
    # the same task is made again exactly from what a failure keeps of it
    again = exam.remake("compound", check.rseed, check.level, json.loads(json.dumps(check.parts)))
    assert again[2] == task
    # each part's own check reads only the piece under its heading
    singles = [exam.remake(*p) for p in check.parts]
    answers = []
    for f, k, t, c in singles:
        import re
        nums = re.findall(r"wants (-?[\d.]+)", c(None, "nothing")[1])
        answers.append(nums[0] if nums else c(None, "nothing")[1])
    if all(re.fullmatch(r"-?[\d.]+", a) for a in answers):
        right = f"PART A\n{answers[0]}\nPART B: {answers[1]}\n"
        assert check(None, right)[0]
        assert not check(None, f"PART A\n{answers[1]}\nPART B\n{answers[0]}\n")[0] or answers[0] == answers[1]
        assert not check(None, f"{answers[0]}\n{answers[1]}")[0]  # no headings: not an answer to this task
    assert "no such heading" in check(None, "PART A\n1")[1]


def test_the_form_is_asked_for_part_by_part():
    task = parts.join(["Give me exactly 3 colours as a numbered list and nothing else.", "What is 2 + 2?"])
    assert "PART B" in solo.form(task, "PART A\n1. red\n2. blue\n3. green")
    assert "PART A" in solo.form(task, "PART A\nred, blue\nPART B\n4") and "numbered list" in solo.form(task, "PART A\nred, blue\nPART B\n4")
    assert solo.form(task, "PART A\n1. red\n2. blue\n3. green\nPART B\n4") == ""
    assert solo.form("What is 2 + 2?", "4") == ""
    # answers given part by part agree only when every part does
    a, b = "PART A\n112\nPART B\nRabat", "PART A\n112\nPART B\nMarrakech"
    assert not solo.same(a, b) and solo.same(a, a.replace("PART B\n", "PART B: "))


def test_a_harder_level_makes_a_harder_task_and_level_0_is_the_exams_own():
    import random
    for make in (exam.m_percent, exam.m_table, exam_hard.h_join, exam_hard.h_log, exam_hard.h_search):
        assert make.__name__ in exam.LEVELED
        base, hard = exam._made(make, "s:7", 0), exam._made(make, "s:7", 2)
        assert base[2] == make(random.Random("s:7"))[2]  # level 0: as the exam has always made it
        assert hard[2] != base[2] and hard[3].level == 2 and base[3].level == 0
        assert exam.remake(make.__name__, "s:7", 2)[2] == hard[2]
    assert exam._made(exam.m_days, "s:7", 3)[3].level == 0  # a kind with no harder form stays as it is
    ladder = exam.exam(10000001, 8, (), "ladder", without=exam_hard.HELD_OUT | {"h_web"}, levels={"compound": 3, "m_percent": 1})
    assert len(ladder) == 8 and sum(t[2] == "several tasks in one" for t in ladder) == 4
    assert all(len(parts.of_task(t[3])) == 3 for t in ladder if t[2] == "several tasks in one")
    assert not any(p[0] in exam_hard.HELD_OUT for t in ladder if t[2] == "several tasks in one" for p in t[4].parts)


def test_the_levels_move_with_what_practice_passed(tmp_path):
    (tmp_path / "rows-1").mkdir()
    tasks = ([{"maker": "compound", "level": 2, "ok": True}] * 5 + [{"maker": "compound", "level": 2, "ok": False}]
             + [{"maker": "h_join", "level": 1, "ok": False}] * 5 + [{"maker": "m_percent", "level": 0, "ok": True}] * 3
             + [{"maker": "m_days", "level": 0, "ok": True}] * 9 + [{"maker": "h_log", "level": 7, "ok": True}] * 9 + [{"maker": "evil", "level": 0, "ok": True}] * 9)
    (tmp_path / "rows-1" / "practice.json").write_text(json.dumps({"seed": 1, "tasks": tasks}))
    now, seen = grow_record.levels({"compound": 2, "h_join": 1, "h_search": 2, "x": 5}, [tmp_path])
    # passed mostly: one up; failed mostly: one down; three tries move nothing; unknown names and kinds without levels are not taken
    assert now == {"compound": 3, "h_join": 0, "h_search": 2, "m_percent": 0, "h_log": 0}
    assert seen["compound"] == {"2": [5, 6]} and "evil" not in seen and "m_days" not in seen


# ---- rows are added to, never replaced -------------------------------------------------------------------------------
def _row(task, out, **more):
    return json.dumps({"type": "first", "task": task, "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": f"TASK: {task}"}], "output": out} | more)


def test_rows_are_joined_with_what_the_release_holds_and_stamped_with_their_generation(tmp_path):
    release = tmp_path / "release.jsonl"
    release.write_text("\n".join([_row("a", "1"), _row("b", "2"), "not a row", _row("a", "1", who="another member")]) + "\n")
    mine = tmp_path / "mine.jsonl"
    mine.write_text("\n".join([_row("a", "1"), _row("c", "3")]) + "\n")
    out = tmp_path / "out.jsonl"
    assert grow.gather(out, "g25", [release], [mine]) == (2, 1)
    rows = [json.loads(x) for x in out.read_text().splitlines()]
    assert [r["task"] for r in rows] == ["a", "b", "c"] and [r.get("gen") for r in rows] == [None, None, "g25"]
    # the record: what the release holds now comes first, this run's rows are added, an older copy removes nothing
    older = tmp_path / "older.jsonl"
    older.write_text(_row("a", "1") + "\n")
    assert grow_record.join([str(older), str(out), str(older)], grow_record._row, 100) == 0
    assert [json.loads(x)["task"] for x in older.read_text().splitlines()] == ["a", "b", "c"]
    assert len(grow_record.union([[_row(str(i), "x") for i in range(30)]], most=10)) == 10


def test_a_child_is_taught_its_parents_mistakes(tmp_path):
    home = tmp_path / "members"
    home.mkdir()

    def member(n, who, first, final, answer):
        msgs = [{"role": "system", "content": "orders. Today is 2026-11-14 (Friday)."}, {"role": "user", "content": "TASK: add"},
                {"role": "assistant", "content": f"```python\n{first}\n```"}, {"role": "user", "content": f"OUTPUT:\n{answer}\n\nIf this output..."}]
        (home / f"member{n}.json").write_text(json.dumps({"messages": msgs, "program": final, "answer": answer, "who": who}))
    member(1, "t80+g2trunk", "print(2+3)", "print(2+3)", "5")
    member(2, "t80+g1code", "print(6)", "print(6)", "6")  # the cell that was wrong
    member(3, "t80+g1data", "print(2+3)", "print(2+3)", "5")
    (home / "members.json").write_text(json.dumps({"agreed": True, "agreeing": [1, 3]}))
    rows = grow.pair_rows(tmp_path, "add")
    assert len(rows) == 1 and rows[0]["rejected_who"] == "t80+g1code" and rows[0]["shown"] == "OUTPUT:\n6"
    assert "not right" in grow.MEND.format(shown=rows[0]["shown"])
