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
        assert "shutil.copy(__file__, " in les["program"] and "f.write(" not in les["program"]  # the module is never code inside a string
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
        assert les["ok"] and 'open("log.txt")' in les["program"] and "ERROR" not in les["program"].replace('"ERROR"', ""), les["why"]  # the file the runtime saves, not a copy
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
        res = lessons.teach("t", 1, failures, out=out, levels={}, log=lambda *a, **k: None, several=0)
    finally:
        monkey.undo()
    got = [json.loads(x) for x in out.read_text().splitlines()]
    assert res["lessons"] == 2 and res["right"] == 2 and res["rows"] == 5 and not res["dropped"]
    fixes = [r for r in got if r["type"] == "fix"]
    assert len(fixes) == 1 and "print(2)" in fixes[0]["messages"][2]["content"]  # the newest wrong program of that task


def test_what_is_known_is_printed_from_the_program_and_never_fetched():
    forms = {}
    for i in range(80):
        task = exam._made(exam.m_know, f"k{i}", 0)[2]
        forms.setdefault(next(w for w in ("capital", "chemical symbol", "prime number", "greatest common divisor", "rectangle") if w in task), f"k{i}")
    assert len(forms) == 5  # capital, element, prime, divisor, rectangle
    for rseed in forms.values():
        les = lessons.lesson("m_know", rseed)
        assert les["ok"] and "requests" not in les["program"], (les["task"], les["why"])


def test_a_task_of_several_parts_is_taught_as_its_parts_programs_each_under_its_heading():
    from team import parts
    pool = [exam.m_units, exam.m_know, exam_hard.h_module, exam_hard.h_log, exam_hard.h_search]  # parts that need no site
    for i, k in ((0, 2), (1, 3), (2, 2)):
        made = exam.compound(f"several{i}", k, pool, {})
        les = lessons.lesson("compound", f"several{i}", k, made[3].parts)
        assert les["ok"], les["why"]
        assert les["program"].count("print('PART ") == k and set(parts.of_answer(les["answer"])) == set(parts.LETTERS[:k])
    # a part with no lesson (a held-out kind): no lesson for the whole
    made = exam.compound("held", 2, [exam.m_units, exam_hard.h_sim], {})
    assert lessons.lesson("compound", "held", 2, made[3].parts)["why"] == "no program for this form of the task"


def test_the_everyday_kinds_are_computed_never_typed():
    """Generation 28: 'pocket' backwards typed as 'etok', 'lantern' in capitals as 'LANCERN', 680 less 15% as 528."""
    for maker in ("m_percent", "m_days", "m_weekday", "m_table", "m_code", "m_fix", "m_follow", "m_steps", "h_join"):
        for i in range(6):
            for level in ((0, 1) if maker in ("m_percent", "m_table", "h_join") else (0,)):
                les = lessons.lesson(maker, f"every{i}", level)
                assert les["ok"], (maker, level, les["task"], les["why"], les["answer"])
    steps = lessons.SOLVERS["m_steps"]("Do these three things and label the answers A, B and C, each on its own line: first multiply 44 by 4; then write the word 'pocket' backwards; then name the capital of Finland.")
    assert "'pocket'[::-1]" in steps and "44 * 4" in steps
    assert "'lantern'.upper()" in lessons.SOLVERS["m_follow"]("Write the word 'lantern' in capital letters and nothing else.")
    assert "price * (1 - 15 / 100)" in lessons.SOLVERS["m_percent"]("A printer costs 680 dollars and the price falls by 15%. What is the new price?")


def test_teach_says_right_of_made_for_every_kind_and_why_the_others_failed(tmp_path, monkeypatch, capsys):
    """Decision 1, order 1c: g38 printed 126 right of 300 and nobody could say for which kinds, or that most were never made."""
    units, percent, days = (exam.remake(m, "x", 0, None)[1] for m in ("m_units", "m_percent", "m_days"))
    monkeypatch.setattr(lessons, "SOLVERS", {"m_units": lessons.units, "m_percent": lambda task: "print('about 40')",
                                             "m_days": lessons.days})
    real = lessons.lesson

    def lesson(maker, rseed, level=0, parts=None):
        if maker == "m_days" and rseed.endswith(":0"):
            return {"maker": maker, "kind": "", "ok": False, "why": "the program failed: requests.exceptions.ReadTimeout: read timed out"}
        return real(maker, rseed, level, parts, timeout=60)
    monkeypatch.setattr(lessons, "lesson", lesson)
    printed = []
    res = lessons.teach("t", 2, out=tmp_path / "rows.jsonl", levels={}, log=lambda *a, **k: printed.append(a[0]), several=0,
                        own={days: lessons.OWN}, pulse={days: [0, 4]})  # its own programs, but the body still fails it
    assert res["by_kind"] == {units: [2, 2], percent: [0, 2], "m_days": [0, 1], days: [1, 1]}
    assert res["failed_by_kind"] == {percent: {"check failed": 2}, "m_days": {"timed out": 1}}
    assert res["lessons"] == 6 and res["made"] == 6 and res["right"] == 3
    assert printed[-1] == f"lessons by kind: {percent} 0/2 (check failed), m_days 0/1 (timed out), {units} 2/2, {days} 1/1"  # worst first
    # a kind left to the hive is not made, and is not counted as made
    res = lessons.teach("t", 1, out=None, levels={}, log=lambda *a, **k: printed.append(a[0]), several=0, own={units: lessons.OWN})
    assert units not in res["by_kind"] and res["lessons"] == 3 and res["made"] == 2 and res["left_to_the_hive"] == [units]
    assert lessons.reason("site said: 429 Client Error: Too Many Requests") == "site refused"
    assert lessons.reason("the program failed: ConnectionError: Max retries exceeded") == "site refused"
    assert lessons.reason("the program failed: JSONDecodeError: the reply from https://x.org/a.json is a web page (HTML), not JSON") == "site refused"
    assert lessons.reason("check failed: JSONDecodeError: Expecting value: line 1 column 1 (char 0)") == "site refused"
    assert lessons.reason("the answer was 41, not 40") == "check failed"
    # the command line: the by-kind line just before the summary, which carries the same counts (grow.yml keeps the last 2)
    monkeypatch.setattr(lessons, "teach", lambda *a, **k: (print("lessons by kind: x 1/2 (timed out)"), {"lessons": 2, "by_kind": {"x": [1, 2]}})[1])
    lessons.main(["--seed", "t", "--out", str(tmp_path / "r.jsonl")])
    last = capsys.readouterr().out.strip().splitlines()[-2:]
    assert last[0].startswith("lessons by kind: ") and json.loads(last[1])["by_kind"] == {"x": [1, 2]}


def _longest(les, wrong=None):
    return max(lessons.row_pieces(r) for r in lessons.rows(les, wrong, today="2026-11-17 (Tuesday)"))


def test_t4_the_log_lesson_reads_the_file_and_its_rows_fit_a_32_bit_runner():
    """T4: the log lesson copied the log into its program (about 1300 pieces): 237 of 238 rows left out in g38."""
    for level in (0, 1, 2):
        for i in range(3):
            les = lessons.lesson("h_log", f"t4log{i}", level)
            assert les["ok"], les["why"]
            first = lessons.rows(les)[0]["messages"][1]["content"]
            assert "more lines like these" in first and sum(ln[:4].isdigit() for ln in first.splitlines()) == 5  # the log cut in the prompt
            wrong = {"program": les["program"].replace("ERROR", "WARN"), "printed": les["answer"]}
            assert _longest(les, wrong) <= lessons.LIMIT, (level, i)
    # in a task of several parts whose first block of data is another part's, log.txt would hold that: copied there
    task = exam._made(exam_hard.h_log, "t4", 0)[2]
    assert 'open("log.txt")' in lessons.log(task) and 'log = """' in lessons.log(task, copy=True)
    assert lessons.lean(task, lessons.log(task, copy=True)) == task  # a log the program copies stays whole in the prompt


def test_t4_module_and_search_lessons_fit_508_pieces_and_are_drawn_again_when_their_values_do_not():
    for i in range(12):
        les = lessons.fitting("h_module", f"t4mod{i}")
        assert les["ok"], les["why"]
        assert _longest(les) <= lessons.LIMIT, les["task"]
        wrong = {"program": les["program"] + "\nprint('checked')\n", "printed": les["answer"]}
        fix = lessons.rows(les, wrong)[-1]
        assert fix["type"] == "fix" and lessons.row_pieces(fix) <= lessons.LIMIT and fix["output"].endswith(les["program"].strip() + "\n```")
        les = lessons.fitting("h_search", f"t4s{i}")
        assert les["ok"] and _longest(les) <= lessons.LIMIT
    # a module asked of two 4 by 4 matrices does not fit: a fresh lesson draws its task again, a task the hive got wrong never
    long = next(f"w{i}" for i in range(400) if "spiral" in exam._made(exam_hard.h_module, f"w{i}", 0)[2]
                and _longest(lessons.lesson("h_module", f"w{i}")) > lessons.LIMIT)
    assert lessons.fitting("h_module", long)["rseed"].startswith(long + ":")
    assert lessons.fitting("h_module", long, fresh=False)["rseed"] == long


def test_t4_the_website_and_fact_lessons_fit_without_a_site():
    """Their programs made from tasks drawn offline, with an answer as long as the longest these lessons printed."""
    for maker in ("h_walk", "h_age", "h_table", "h_since", "h_web"):
        for i in range(4):
            made = exam._made(getattr(exam_hard, maker), f"t4w{i}", 0)
            program = lessons.SOLVERS[maker](made[2])
            assert program, (maker, made[2])
            les = {"ok": True, "task": made[2], "kind": made[1], "rseed": "x", "maker": maker, "program": program,
                   "answer": "versions.md saved\nreleased most recently: requests 2026-11-02\nbooks: 20\ndays: 12345"}
            assert _longest(les) <= lessons.LIMIT, maker


def test_t4_join_copies_the_tables_as_the_task_writes_them():
    """The join's tables are in the task's own sentence (no block the runtime saves): copied as written, not as lists of
    tuples (300 pieces). Its first row stays over 508: the tables are there twice, in the task and in the program."""
    les = lessons.lesson("h_join", "t4j", 0)
    assert les["ok"] and '.split("; ")' in les["program"] and "('" not in les["program"]
    assert lessons.row_pieces(lessons.rows(les)[0]) < 650


def test_t4_pieces_are_counted_like_the_tokenizer_or_by_a_rule_near_it(monkeypatch):
    text = lessons.lesson("h_module", "t4p")["program"]
    by_tok = lessons.pieces(text)
    monkeypatch.setattr(lessons, "_TOK", [None])
    assert abs(lessons.pieces(text) - by_tok) <= by_tok / 3 and lessons.pieces("12345") == 5
