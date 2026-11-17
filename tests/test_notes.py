"""Notes (team/notes.py): short ways of working written by rules from checked work, with no digit, kept once, read
back by kind and words, and put in a member's orders only when HIVE_NOTES=1."""
import json
import re

from team import notes


def _try(ok, program, *told, hints=()):
    ms = [{"role": "system", "content": "orders"}, {"role": "user", "content": "TASK: x"}]
    for m in told:
        ms += [{"role": "assistant", "content": f"```python\n{program}\n```"}, {"role": "user", "content": m}]
    return {"ok": ok, "program": program if ok else "", "answer": "", "messages": ms, "hints": list(hints)}


FAILED_JSON = _try(False, "import requests\nprint(requests.get('https://example.org/item/42').json()['price'])",
                   "ERROR:\nTraceback (most recent call last):\n  File \"m.py\", line 2\n"
                   "requests.exceptions.JSONDecodeError: Expecting value: line 1 column 1 (char 0)")
FAILED_KEY = _try(False, "d = {}\nprint(d['total_2024'])", "ERROR:\nKeyError: 'total_2024'")
RIGHT_PAGES = _try(True, "import requests\nfrom urllib.parse import urljoin\nurl = 'https://books.toscrape.com/'\n"
                         "while url:\n    nxt = p.select_one('li.next a')\n    url = urljoin(url, nxt['href']) if nxt else None\n"
                         "print('cheapest:', 12.5)")


def test_a_failure_and_a_success_give_one_note_each():
    made = notes.distill([FAILED_JSON, RIGHT_PAGES], "web_walk")
    assert len(made) == 2
    assert [n["from"] for n in made] == ["failure", "success"]
    assert "JSON" in made[0]["note"] and "BeautifulSoup" in made[0]["note"]
    assert "next link" in made[1]["note"]
    for n in made:
        assert n["note"].startswith("When ") and len(n["note"]) <= notes.LONGEST and n["kind"] == "web_walk"


def test_no_digit_is_ever_kept():
    made = notes.distill([FAILED_JSON, FAILED_KEY, RIGHT_PAGES], "data")
    assert made and not any(re.search(r"\d", n["note"]) for n in made)
    assert notes.plain("When the year 2024 had 3 items, use 7.5") == "When the year had items, use ."


def test_the_runtime_s_own_hints_and_a_timeout_make_notes():
    html = _try(False, "x", "ERROR:\nhttps://site/api is a web page (HTML), not JSON: read it with BeautifulSoup")
    assert any("HTML instead of data" in n["note"] for n in notes.distill([html]))
    shape = _try(False, "x", "OUTPUT:\na\n\nThe TASK asks for a numbered list of exactly 5 items and nothing else")
    assert any("numbered list" in n["note"] for n in notes.distill([shape]))
    slow = _try(False, "x", "ERROR:\nTIMEOUT after 120s")
    assert any("ran out of time" in n["note"] for n in notes.distill([slow]))


def test_a_remembered_failure_record_is_read_too():
    rec = {"task": "t", "kind": "k", "program": "x", "printed": "", "said": "ValueError: could not convert string to float"}
    made = notes.distill([rec], "k")
    assert made and made[0]["from"] == "failure" and "strip units" in made[0]["note"]


def test_nothing_known_gives_no_note():
    assert notes.distill([_try(False, "x", "OUTPUT:\nsomething")]) == []
    assert notes.distill([]) == []


def test_the_same_note_is_kept_once_and_counted(tmp_path):
    f = tmp_path / "notes.jsonl"
    for _ in range(3):
        notes.keep(notes.distill([FAILED_KEY], "data"), "read the total from 2024 data", path=f)
    rows = notes.read(f)
    assert len(rows) == 1 and rows[0]["seen"] == 3 and rows[0]["helped"] == 0
    assert set(rows[0]) >= {"kind", "note", "from", "seen", "helped", "when"}
    assert not any(re.search(r"\d", w) for w in rows[0]["words"])
    # a note that differs only in digits, case or stops is the same note
    notes.keep([{"kind": "data", "note": rows[0]["note"].upper() + " 42", "from": "failure"}], path=f)
    assert len(notes.read(f)) == 1 and notes.read(f)[0]["seen"] == 4


def test_recall_by_kind_first_then_by_words(tmp_path):
    f = tmp_path / "notes.jsonl"
    notes.keep([{"kind": "web", "note": "When a web source returned HTML, read it with BeautifulSoup.", "from": "failure"}], path=f)
    notes.keep([{"kind": "code", "note": "When a list had fewer items, check how many there are.", "from": "failure"}], path=f)
    notes.keep([{"kind": "data", "note": "When a csv file had headings, print the headings first.", "from": "success"}], path=f)
    got = notes.recall("read the csv file of prices", kind="web", path=f)
    assert got[0].startswith("When a web source") and "csv" in got[1] and len(got) == 2
    assert notes.recall("open the csv file", path=f) == ["When a csv file had headings, print the headings first."]
    assert notes.recall("nothing alike here", kind="other", path=f) == []
    assert len(notes.recall("csv file web list", kind="web", most=1, path=f)) == 1


def _run_folder(tmp_path, ok_first):
    run = tmp_path / "practice" / "t1"
    (run / "members").mkdir(parents=True)
    (run / "TASK.md").write_text("Walk the category over all its pages and print the cheapest price.\n")
    (run / "members" / "member1.json").write_text(json.dumps(RIGHT_PAGES if ok_first else FAILED_JSON))
    (run / "members" / "member2.json").write_text(json.dumps(FAILED_JSON))
    (run / "exam.json").write_text(json.dumps({"ok": ok_first, "why": "", "note": "",
                                               "members": [{"who": "a", "ok": ok_first, "member": 1}, {"who": "b", "ok": False, "member": 2}]}))
    return run


def test_distill_and_learn_read_a_task_folder(tmp_path):
    run = _run_folder(tmp_path, True)
    made = notes.distill(run, "web_walk")
    assert {n["from"] for n in made} == {"failure", "success"}
    f = tmp_path / "notes.jsonl"
    # a confirmed member that was shown a note: that note helped
    shown = json.loads((run / "members" / "member1.json").read_text())
    shown["messages"][0]["content"] += notes.block([made[1]["note"]])
    (run / "members" / "member1.json").write_text(json.dumps(shown))
    notes.learn(run, "web_walk", path=f)
    helped = {r["note"]: r["helped"] for r in notes.read(f)}
    assert helped[made[1]["note"]] == 1 and helped[made[0]["note"]] == 0


def test_the_command_line(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(notes, "FILE", tmp_path / "n" / "notes.jsonl")
    _run_folder(tmp_path, False)
    assert notes.main(["distill", str(tmp_path / "practice"), "--kind", "web"]) == 0
    assert "[failure] web: When" in capsys.readouterr().out
    assert notes.main(["show"]) == 0
    assert "1 seen" in capsys.readouterr().out


def _member(monkeypatch, tmp_path, store):
    from team import solo
    from team.board import Board
    from team.guard import Guard
    seen = []
    monkeypatch.setattr(notes, "FILE", store)
    monkeypatch.setattr(solo.ternary, "chat", lambda who, messages, **k: seen.append(messages[0]["content"]) or "```python\nprint('hello')\n```" if not seen else "DONE")
    task = "Print the word hello from a csv file"
    board = Board(tmp_path / "run")
    solo.member(task, 1, board, Guard(board, "never", goal=task, use_model=False), tmp_path / "run" / "w", 0.0, "t80+x")
    return seen[0]


def test_notes_are_in_the_orders_only_with_hive_notes(tmp_path, monkeypatch):
    store = tmp_path / "notes.jsonl"
    notes.keep([{"kind": "data", "note": "When a csv file had headings, print the headings first.", "from": "success"}], path=store)
    monkeypatch.delenv("HIVE_NOTES", raising=False)
    assert notes.HEAD not in _member(monkeypatch, tmp_path / "a", store)
    monkeypatch.setenv("HIVE_NOTES", "1")
    monkeypatch.setenv("HIVE_KIND", "data")
    orders = _member(monkeypatch, tmp_path / "b", store)
    assert notes.HEAD in orders and "- When a csv file had headings, print the headings first." in orders
