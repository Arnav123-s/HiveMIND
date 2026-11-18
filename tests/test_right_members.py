"""Every member whose own answer the task's check confirms is a right program to learn from, whether or not another
agreed with it (training/grow.taught): generation 28's c10002802_02 had its first member right while the other two
disagreed, and nothing of it was kept."""
import json

from training import exam, grow


def _member(home, n, who, final, answer, first=None):
    first = first or final
    msgs = [{"role": "system", "content": "orders. Today is 2026-11-14 (Friday)."}, {"role": "user", "content": "TASK: add 2 and 3"},
            {"role": "assistant", "content": f"```python\n{first}\n```"}]
    if final != first:
        msgs += [{"role": "user", "content": "OUTPUT:\n23\n\nThat is not it."}, {"role": "assistant", "content": f"```python\n{final}\n```"}]
    (home / f"member{n}.json").write_text(json.dumps({"who": who, "messages": msgs, "program": final, "answer": answer}))


def check(run, report):
    return "5" in report, "wants 5"


def _run(tmp_path, agreeing, ok, members):
    """A fabricated task folder: the members' files, members.json, and exam.json with each member's own verdict made
    by training/exam.each_member (so the verdicts carry the numbers of their files)."""
    run = tmp_path / "run"
    home = run / "members"
    home.mkdir(parents=True)
    for m in members:
        _member(home, *m)
    (home / "members.json").write_text(json.dumps({"agreed": bool(agreeing), "agreeing": agreeing}))
    (run / "exam.json").write_text(json.dumps({"id": "t", "ok": ok, "members": exam.each_member(run, check)}))
    return run


def test_a_right_member_of_a_task_the_members_disagreed_on_is_taught_and_the_refused_are_not(tmp_path):
    run = _run(tmp_path, [], False, [(1, "t80+code", "print(2+3)", "5", "print('2'+'3')"),   # wrong first, then right
                                     (2, "t80+data", "print(6)", "6"),
                                     (3, "t80+words", "print(2*3)", "6")])
    assert grow.taught(run) == [1]
    rows = grow.rows_of(run, "add 2 and 3", "a sum", 7)
    assert sorted(r["type"] for r in rows) == ["done", "first", "fix"]
    assert {r["member"] for r in rows} == {1} and {r["who"] for r in rows} == {"t80+code"}
    assert all(r["output"] in ("```python\nprint(2+3)\n```", "DONE") and r["agreed"] is False for r in rows)
    pairs = grow.pair_rows(run, "add 2 and 3")
    # the right member's own wrong first try is not set down as wrong: only members the check refused are rejected
    assert [(p["member"], p["rejected"]) for p in pairs] == [(2, "```python\nprint(6)\n```"), (3, "```python\nprint(2*3)\n```")]
    assert all(p["output"] == "```python\nprint(2+3)\n```" for p in pairs)


def test_verdicts_are_tied_to_their_files_by_number_not_by_order(tmp_path):
    run = _run(tmp_path, [], False, [(2, "t80+data", "print(6)", "6"), (10, "t80+code", "print(2+3)", "5")])
    said = json.loads((run / "exam.json").read_text())["members"]
    assert [v["member"] for v in said] == [10, 2]  # member10.json sorts first: the order is not the numbers
    assert grow.taught(run) == [10] and {r["member"] for r in grow.rows_of(run, "add")} == {10}
    # a verdict from before the numbers were kept is tied by the member's name, where only one file has it
    (run / "exam.json").write_text(json.dumps({"ok": False, "members": [{"who": "t80+code", "ok": True}, {"who": "t80+data", "ok": False}]}))
    assert grow.taught(run) == [10]
    _member(run / "members", 3, "t80+code", "print(5)", "5")  # now two files carry that name: tied to neither
    assert grow.taught(run) == []


def test_each_right_member_is_taught_once_and_no_right_member_is_ever_rejected(tmp_path):
    # members 1 and 2 agreed and wrote the same program; member 3 was right too, with another program
    run = _run(tmp_path, [1, 2], True, [(1, "t80+code", "print(2+3)", "5"), (2, "t80+data", "print(2+3)", "5"),
                                        (3, "t80+words", "print(3+2)", "5"), (4, "t80+maths", "print(7)", "7")])
    rows = grow.rows_of(run, "add")
    keys = [json.dumps([r["type"], r["messages"], r["output"]]) for r in rows]
    assert len(keys) == len(set(keys)) == 4  # first and done of print(2+3) once, and of print(3+2)
    assert {(r["member"], r["agreed"]) for r in rows} == {(1, True), (3, False)}
    pairs = grow.pair_rows(run, "add")
    assert [p["member"] for p in pairs] == [4]
    assert all(p["rejected"] not in ("```python\nprint(2+3)\n```", "```python\nprint(3+2)\n```") for p in pairs)


def test_a_member_that_agreed_but_the_check_refused_is_not_taught(tmp_path):
    run = _run(tmp_path, [1, 2], True, [(1, "t80+code", "print(2+3)", "5"), (2, "t80+data", "print('five')", "five")])
    assert {r["member"] for r in grow.rows_of(run, "add")} == {1}
    assert [p["member"] for p in grow.pair_rows(run, "add")] == [2]


def test_without_verdicts_the_old_rule_stands(tmp_path):
    run = _run(tmp_path, [1], True, [(1, "t80+code", "print(2+3)", "5"), (2, "t80+data", "print(2+3)", "5")])
    (run / "exam.json").unlink()  # a task not sat as an exam (team/engram): the members that agreed
    assert grow.taught(run) == [1]
    (run / "exam.json").write_text(json.dumps({"ok": False}))  # a failed task from before the verdicts: nothing
    assert grow.taught(run) == [] and grow.rows_of(run, "add") == [] and grow.pair_rows(run, "add") == []


def test_practice_keeps_the_right_member_of_a_task_the_hive_got_wrong(tmp_path, monkeypatch):
    monkeypatch.setattr(exam, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(exam, "_memory", lambda empty: tmp_path)
    monkeypatch.setattr(exam, "exam", lambda *a, **k: iter([("c1_00", "code", "a sum", "add 2 and 3", check)]))

    def sit_one(tag, tid, task, chk, home, kind=""):
        run = exam.RUNS / tag / tid
        home = run / "members"
        home.mkdir(parents=True)
        _member(home, 1, "t80+code", "print(2+3)", "5")
        _member(home, 2, "t80+data", "print(6)", "6")
        _member(home, 3, "t80+words", "print(7)", "7")
        (home / "members.json").write_text(json.dumps({"agreed": False, "agreeing": []}))
        res = {"id": tid, "ok": False, "why": "no answer", "seconds": 1, "members": exam.each_member(run, chk)}
        (run / "exam.json").write_text(json.dumps(res))
        return res
    monkeypatch.setattr(exam, "sit_one", sit_one)
    said = []
    out = tmp_path / "grow" / "rows.jsonl"
    got = grow.practice(5, 1, "mixed", out, log=lambda *a, **k: said.append(a[0]))
    rows = [json.loads(x) for x in out.read_text().splitlines()]
    assert got["right"] == 0 and got["rows"] == 2
    assert {(r["type"], r["member"]) for r in rows} == {("first", 1), ("done", 1), ("pair", 2), ("pair", 3)}
    assert "1 of the right members not among those that agreed" in said[-1]


def test_practice_does_not_promote_an_old_program_for_a_helper_sorted_delivery(tmp_path, monkeypatch):
    from team import memory, solo

    monkeypatch.setattr(exam, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(memory, "HOME", tmp_path / "memory")
    monkeypatch.setenv("AGENT_TEAM_SOLO", "2")
    # Exercise a repaired result and the three forms of ordinary or older receipt.
    receipts = [
        {"file_repairs": [{"name": "out.csv", "column": "value", "direction": "ascending"}]},
        {"file_repairs": []}, {"agreed": True}, None,
    ]
    tasks = [f"Save the observations of sensor {i} in out.csv" for i in range(len(receipts))]
    for task in tasks:
        solo.keep(task, "print('old')", "old")
    monkeypatch.setattr(exam, "exam", lambda *args: [
        (str(i), "data", "table", task, check) for i, task in enumerate(tasks)
    ])
    for i, receipt in enumerate(receipts):
        run = exam.RUNS / "practice_1" / str(i)
        (run / "members").mkdir(parents=True)
        (run / "exam.json").write_text(json.dumps({"id": str(i), "ok": True, "seconds": 0}))
        if receipt is not None:
            (run / "members" / "members.json").write_text(json.dumps(receipt))
    out = exam.practice(1, log=lambda *a, **k: None)
    assert out["right"] == 4 and out["confirmed_in_library"] == 3
    assert {row["task"]: row["checked"] for row in solo.solved()} == {
        task: i != 0 for i, task in enumerate(tasks)
    }
