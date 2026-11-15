"""Lessons: right programs for the kinds the hive cannot do yet, put to each task's own check before they are taught.
Offline: the kinds that need no site are run to their check; the website kinds' programs are made and parsed."""
import ast
import json

from training import exam, exam_hard, lessons


def test_no_held_out_kind_is_ever_taught():
    assert not set(lessons.SOLVERS) & exam_hard.HELD_OUT  # they measure what carries over to work never shown


def test_every_module_every_search_the_log_and_the_units_are_right_by_their_own_checks():
    seen = {}
    for i in range(400):  # draw until every module of the exam has come up
        task = exam._made(exam_hard.h_module, f"m{i}", 0)[2]
        name = task.split("save it as ")[1].split(".py")[0]
        seen.setdefault(name, f"m{i}")
        if len(seen) == len(exam_hard.SPECS):
            break
    assert set(seen) == set(exam_hard.SPECS) == set(lessons.MODULES)
    for name, rseed in seen.items():
        les = lessons.lesson("h_module", rseed)
        assert les["ok"], (name, les["why"], les["answer"])  # the hidden tests pass, the values asked for are printed
        assert "inspect.getsource" in les["program"] and "f.write('" not in les["program"]  # the module is never code inside a string
    forms = set()
    for i in range(60):
        task = exam._made(exam_hard.h_search, f"s{i}", 0)[2]
        form = task.split()[0:3]
        if tuple(form) in forms:
            continue
        forms.add(tuple(form))
        for level in (0, 1):
            les = lessons.lesson("h_search", f"s{i}", level)
            assert les["ok"], (task, les["why"], les["answer"])
    assert len(forms) == 4  # the smallest number, palindromes, the nth prime, the coins
    for level in (0, 2):
        les = lessons.lesson("h_log", "log", level)
        assert les["ok"] and 'log = """' in les["program"], les["why"]  # given data copied into the program
    forms = {}
    for i in range(40):  # every form of the unit question: Fahrenheit, Celsius, miles, pounds
        task = exam._made(exam.m_units, f"u{i}", 0)[2]
        forms.setdefault(next(w for w in ("Fahrenheit in", "Celsius in", "miles", "pounds") if w in task), f"u{i}")
    assert len(forms) == 4 and all(lessons.lesson("m_units", rseed)["ok"] for rseed in forms.values())


def test_the_website_programs_follow_links_from_the_first_page_and_never_make_an_address_up():
    for maker, mod in (("m_born", exam), ("m_csv", exam), ("h_walk", exam_hard), ("h_since", exam_hard), ("h_age", exam_hard), ("h_table", exam_hard)):
        task = exam._made(getattr(mod, maker), "web", 0)[2]
        program = lessons.SOLVERS[maker](task)
        assert program, (maker, task)
        ast.parse(program)
        assert "/author/" not in program.replace("a[href*='/author/']", "") and "catalogue/category" not in program  # links are followed
    src = lessons.wikidata("Find the length of the river Loire (France), in kilometres, as Wikidata records it (Wikidata item Q1469). Answer with the number.")
    assert "'Q1469'" in src and "'P2043'" in src and "Q828224" in src
    ast.parse(src)


def test_a_lesson_is_taught_only_when_right_and_a_task_got_wrong_before_comes_back_with_the_wrong_program_first(tmp_path):
    les = lessons.lesson("m_units", "u1")
    wrong = {"program": "print('about 40')", "printed": "about 40"}
    rows = lessons.rows(les, wrong)
    assert [r["type"] for r in rows] == ["first", "done", "fix"]
    first, done, fix = rows
    assert first["messages"][0]["content"].startswith("You solve the TASK by writing Python programs") and first["messages"][1]["content"] == f"TASK: {les['task']}"
    assert first["output"].startswith("```python\n") and done["output"] == "DONE" and les["answer"] in done["messages"][-1]["content"]
    assert "print('about 40')" in fix["messages"][2]["content"] and "about 40" in fix["messages"][3]["content"] and fix["output"] == first["output"]
    assert lessons.rows(dict(les, ok=False)) == []  # never taught when its check said no
    # practice's failures: the taught kinds come back (the newest first, once each); held-out kinds and tasks of several parts never
    failures = tmp_path / "failures.jsonl"
    failures.write_text("\n".join(json.dumps(f) for f in [
        {"maker": "h_sim", "rseed": "a", "level": 0, "program": "x"},
        {"maker": "m_units", "rseed": "u3", "level": 0, "program": "print(1)", "printed": "1"},
        {"maker": "m_units", "rseed": "u3", "level": 0, "program": "print(2)", "printed": "2"},
        {"maker": "h_search", "rseed": "s1", "level": 0, "parts": [["m_units", "x", 0]], "program": "y"}]) + "\nnot json\n")
    import pytest
    monkey = pytest.MonkeyPatch()
    monkey.setattr(lessons, "SOLVERS", {"m_units": lessons.units})  # offline: only the units are drawn fresh
    try:
        out = tmp_path / "rows.jsonl"
        res = lessons.teach("t", 1, failures, out=out, levels={}, log=lambda *a, **k: None)
    finally:
        monkey.undo()
    got = [json.loads(x) for x in out.read_text().splitlines()]
    assert res["lessons"] == 2 and res["right"] == 2 and res["rows"] == 5 and not res["dropped"]
    fixes = [r for r in got if r["type"] == "fix"]
    assert len(fixes) == 1 and "print(2)" in fixes[0]["messages"][2]["content"]  # the newest wrong program of that task
