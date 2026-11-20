"""g53: a block of task data saved as task_data.txt is named by its real format, and the member is helped when it reads the
file as JSON or sends the same SyntaxError twice; a program that overwrote a value gets its repair turn after DONE."""
from team import solo
from team.tools.sandbox import describe, give, note

INI = "# c\n[LOGGING]\nhost = 1\n; x = 2\n[MAIL]\nuser = a"


def test_describe_names_the_format():
    assert describe('{"a": [1, 2]}').startswith("JSON")
    assert describe("| a | b |\n|---|---|\n| 1 | 2 |").startswith("a markdown table")
    assert describe("a,b\n1,2\n3,4").startswith("CSV")
    assert describe("a\tb\n1\t2\n3\t4").startswith("TSV")
    assert describe(INI).startswith("INI-style")
    assert describe("one\ntwo words\nthree").startswith("plain text")


def test_note_names_it(tmp_path):
    said = note(give("Here is a config file:\n" + INI + "\nWhat is user in mail?", tmp_path))
    assert "task_data.txt (6 lines, INI-style text" in said and "not JSON" in said


def test_hint_for_json_load_of_the_data_file():
    err = "json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)"
    assert "not JSON" in solo.data_file_hint("import json\ndata = json.load(open('task_data.txt'))", err)
    assert solo.data_file_hint("import json\njson.loads(requests.get(u).text)", err) == ""
    assert solo.data_file_hint("open('task_data.txt')", "ValueError: x") == ""


def test_syntax_hint_shows_the_line():
    code = "rows = []\nblank = sum(1 for r in rows if not r[0]))\n"
    err = '  File "m.py", line 2\n    blank = x))\n SyntaxError: unmatched \')\'\n'
    words = solo.syntax_hint(code, err)
    assert "line 2" in words and "blank = sum(1 for r in rows if not r[0]))" in words and "closing" in words
    assert solo.syntax_hint(code, "ValueError: x") == ""


def test_overwrite_names_are_found_for_the_repair_turn():
    code = "def f(p):\n    return 1, 2\nversion, released = f('a')\nversion, released = f('b')\nprint(version)\n"
    assert solo.overwritten(code) == ["released", "version"]
    assert solo.overwrite_hint(code)
    assert solo.overwrite_hint("a = 1\nprint(a)\n") == ""


def test_done_after_an_overwriting_program_gets_one_repair_turn(tmp_path, monkeypatch):
    bad = "def f(p):\n    return 1, 2\na, b = f('x')\na, b = f('y')\nprint('later:', a)\nprint('days:', b)"
    good = "def f(p):\n    return 1, 2\na, b = f('x')\nc, d = f('y')\nprint('later:', c)\nprint('days:', d)"
    left = ["```python\n" + bad + "\n```", "DONE", "```python\n" + good + "\n```", "DONE"]
    seen = []

    def chat(who, messages, **k):
        seen.append(messages[-1]["content"])
        return left.pop(0)
    monkeypatch.setattr(solo.llm, "chat", chat)
    from team.board import Board
    out = solo.member("Compare x and y. Answer in two lines.", 1, solo.Board(tmp_path), solo.Guard(solo.Board(tmp_path), "never", goal="t", use_model=False),
                      tmp_path / "w", 0.0)
    assert not left and out["program"].strip() == good and "It is not done" in "\n".join(seen)
