"""The causes of g45's lost hard tasks, each made small: members that saved the same right file agree; one line of data
is offered as a file; a count printed as a list is told to print the count; a name clash in a module is named."""
from team import solo
from team.tools.sandbox import give, given, run_python

TOP = ("Here is the file results.csv:\nclass,student,marks\nA2,Omar,75\nB2,Ines,99\n\n"
       "Save a file top.csv with the columns class,rank,student,marks. Then tell me which student has the highest marks of all.")


def _try(tmp_path, name, answer, rows):
    work = tmp_path / name
    work.mkdir()
    if rows is not None:
        (work / "top.csv").write_text(rows)
    return {"answer": answer, "work": str(work)}


def test_members_that_saved_the_same_file_agree(tmp_path):
    # g45 h20000458_02: three right top.csv files, three different sentences, and no two agreed
    rows = "class,rank,student,marks\nA2,1,Omar,75\nB2,1,Ines,99\n"
    a = _try(tmp_path, "a", "top.csv saved\nstudent: Ines", rows)
    b = _try(tmp_path, "b", "Omar\nInes", "class , rank,student,marks\r\nA2,1,Omar,75.0\n\nB2,1,Ines,99\n")
    c = _try(tmp_path, "c", "Ines : 99", rows.replace("99", "98"))
    d = _try(tmp_path, "d", "", rows)
    e = _try(tmp_path, "e", "", rows)
    assert not solo.same(a["answer"], b["answer"], TOP)
    assert solo.same_files(a, b, TOP) and solo.agreeing([a, b], TOP) == [(a, b)]
    assert not solo.same_files(a, c, TOP)  # another value in the file
    assert solo.same_files(a, d, TOP)  # one of the two printed an answer
    assert not solo.same_files(d, e, TOP)  # neither did
    assert not solo.same_files(a, _try(tmp_path, "f", "Ines", None), TOP)  # no file saved
    assert not solo.same_files(a, b, "What is 2 + 2?")  # no file asked for: the printed answers decide


def test_a_module_file_is_never_compared(tmp_path):
    task = "Write a Python module and save it as rle.py. Then print encode('aab')."
    a, b = (tmp_path / "a", tmp_path / "b")
    for w in (a, b):
        w.mkdir()
        (w / "rle.py").write_text("def encode(s):\n    return s\n")
    assert not solo.same_files({"answer": "a2b1", "work": str(a)}, {"answer": "x", "work": str(b)}, task)


def test_one_line_of_data_is_given(tmp_path):
    # g45 h20000454_02: the text was one line, and all three members opened a file they made up
    text = "Mira wrote: 4752-3907 6309-6133, then left. Pavel gave the number 5151-5975-8354."
    task = (f"Here is a text:\n{text}\nA card number is exactly four groups of four digits. Save the whole text so changed "
            "in redacted.txt and tell me how many card numbers you masked.")
    assert given(task) == [{"text": text, "name": ""}]
    assert given(f"Here is the file notes.txt:\n{text}\nCount the words in it and tell me the number of them.") == [{"text": text, "name": "notes.txt"}]
    give(task, tmp_path, skip=solo.wanted(task))
    r = run_python("print(open('input.txt').read().strip())", tmp_path, name="m.py")
    assert r["returncode"] == 0 and r["stdout"].strip() == text


def test_ordinary_sentences_are_not_data():
    for task in ("Do this:\nAdd 2 and 3, and tell me the sum of them all.", "Answer in this form:\nA: the sum",
                 "Note the following:\nThe meeting is on Monday at the main hall of the school.",
                 "Here is what to do:\nSave a file a.txt with the word hi in it.", "What is 2 + 2?",
                 "Use these steps:\nFirst read the file, then count the lines."):
        assert given(task) == [], task


def test_a_count_printed_as_a_list_is_told():
    # g45 h20000454_01: a Counter of every way, 6000 characters, where the number of ways was asked
    task = "In how many different ways can 261 cents be paid with coins of 1, 10, 20, 25 cents?"
    tail = "): 1, " + ", ".join(f"({i}, 0, 3, 8): 1" for i in range(300)) + "})"
    assert "how many" in solo.form(task, tail)
    assert "how many" in solo.form("Tell me how many there are.", "['a', 'b', 'c']")
    assert solo.form(task, "ways: 113") == "" and solo.form("Tell me how many there are.", "3") == ""
    # a function that "returns how many times" is no count asked for; a list answer to "which keys" is no count
    assert solo.form("visits(events, state) returns how many times the machine is in that state. Then tell me "
                     "the value of run(['a', 'b'])", "run(['tick', 'fail', 'resume']) = running") == ""
    assert solo.form("Then tell me the value of keys().", "['b', 'f', 'a', 'c']") == ""


def test_a_name_clash_is_named_for_a_module_task():
    # g45 h20000451_01: self.left = [] beside def left(...), and "'list' object is not callable" twice
    task = "Write a Python module and save it as desk.py for one desk. Test it yourself."
    code = ("class Desk:\n    def __init__(self):\n        self.left = []\n    def left(self, c):\n        return self.left\n"
            "d = Desk()\nprint(d.left([]))\n")
    assert solo.clashes(code) == ["left"]
    name, words = solo.stuck_hint(task, code, "TypeError: 'list' object is not callable")
    assert name == "name_clash" and "self._left" in words
    assert solo.stuck_hint(task, "assert f(1) == 2", "AssertionError")[0] == "assert_values"
    assert solo.stuck_hint(task, "x = 1\nx()", "TypeError: 'int' object is not callable")[0] == "type_values"
    assert solo.stuck_hint("What is 2 + 2?", code, "TypeError: x") is None  # not a module task
    assert solo.stuck_hint(task, code, "NameError: name 'q' is not defined") is None


def test_a_member_is_told_of_the_clash_and_stops_only_on_a_third_same_error(tmp_path, monkeypatch):
    task = "Write a Python module and save it as desk.py with a class Desk. Test it yourself."
    code = ("class Desk:\n    def __init__(self):\n        self.left = []\n    def left(self, c):\n        return self.left\n"
            "print(Desk().left([]))\n")
    told, left = [], [code] * 3

    def chat(who, msgs, **k):
        told.append(msgs[-1]["content"])
        return f"```python\n{left.pop(0)}\n```"
    monkeypatch.setattr(solo.llm, "chat", chat)
    t = solo.member(task, 1, solo.Board(tmp_path), solo.Guard(solo.Board(tmp_path), "never", goal=task, use_model=False),
                    tmp_path / "work", 0.0)
    assert t["turns"] == 3 and not left  # two same errors running no longer stop it
    assert "self._left" in told[1] and "name_clash" in t["hints"]
