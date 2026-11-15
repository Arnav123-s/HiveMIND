"""The world a member's program runs in: data the TASK gave is a file, a module asked for is saved, a missing JSON key
says where it is, and an address without its site is joined to the page fetched last. Each case is a failure seen in
the members' own work in the pulse of generation 27."""
import http.server
import threading

from team.solo import module, wanted
from team.tools.sandbox import give, given, run_python

CSV_TASK = ("Here is a CSV file:\nname,age,city\nLena,52,Lima\nTomas,20,Oslo\nOmar,45,Kyoto\n"
            "Make a new file people.csv from it: keep only the people aged 44 or more. Then tell me how many there are.")
LOG_TASK = ("Here is a log:\n2026-01-11 08:01:58 ERROR auth: disk full\n2026-01-11 09:13:03 WARN search: disk full\n"
            "Save a file errors.json: one JSON object that maps each service to its ERROR lines.")


def test_given_finds_the_data_and_stops_at_the_instruction():
    b = given(CSV_TASK)
    assert len(b) == 1 and b[0]["text"].splitlines() == ["name,age,city", "Lena,52,Lima", "Tomas,20,Oslo", "Omar,45,Kyoto"]
    assert given(LOG_TASK)[0]["text"].count("\n") == 1
    assert given("What is 2 + 2?") == []
    assert given("Here is the file data.json:\n```\n{\"a\": 1}\n```\nRead it.")[0]["text"] == '{"a": 1}'
    assert given("Here is the file scores.csv:\na,b\n1,2\nSum the column b.")[0]["name"] == "scores.csv"


def test_a_program_opens_the_given_data_by_any_name(tmp_path):
    give(CSV_TASK, tmp_path, skip=wanted(CSV_TASK))
    assert not (tmp_path / "people.csv").exists()  # the file asked for is not made for it
    code = ("import csv\nrows = list(csv.DictReader(open('input.csv')))\nimport pandas\n"
            "print(len(rows), len(pandas.read_csv('people.csv')))")
    r = run_python(code, tmp_path, name="m.py")
    assert r["returncode"] == 0 and r["stdout"].split() == ["3", "3"]
    r = run_python("open('out.txt', 'w').write('x')\nopen('nothere/a.csv')", tmp_path, name="w.py")
    assert r["returncode"] == 1 and "FileNotFoundError" in r["stderr"]  # writing and other folders are as always


def test_no_data_no_change(tmp_path):
    give("What is 2 + 2?", tmp_path)
    r = run_python("open('input.csv')", tmp_path, name="m.py")
    assert r["returncode"] == 1 and "FileNotFoundError" in r["stderr"]


def test_a_module_asked_for_is_saved_from_the_program(tmp_path):
    task = "Write a Python module and save it as rle.py. It has two functions, encode and decode. Then print encode('aab')."
    code = ("import re\nLIMIT = 9\n\ndef encode(s):\n    return ''.join(m.group(0)[0] + str(len(m.group(0))) "
            "for m in re.finditer(r'(.)\\1*', s))\n\ndef decode(s):\n    return ''.join(c * int(n) for c, n in "
            "re.findall(r'(\\D)(\\d+)', s))\n\nprint(encode('aab'))\nassert decode(encode('aab')) == 'aab'\n")
    assert module(task, code, tmp_path) == "rle.py"
    r = run_python("import rle\nprint(rle.encode('aaab'), rle.decode('e11f4'), rle.LIMIT)", tmp_path, name="t.py")
    assert r["stdout"].split() == ["a3b1", "eeeeeeeeeeeffff", "9"]  # and nothing printed on import
    assert module(task, code, tmp_path) == ""  # it is there now
    assert module("Save it as x.py.", "print(1)", tmp_path) == ""  # no functions, nothing saved


def test_a_missing_key_says_where_it_is(tmp_path):
    code = ("import json\nd = json.loads('{\"info\": {\"version\": \"1.2\"}, \"urls\": [{\"upload_time\": \"2026-11-13\"}]}')\n"
            "print(d['info']['upload_time'])")
    r = run_python(code, tmp_path, name="k.py")
    assert "data['urls'][0]['upload_time'] = '2026-11-13'" in r["stderr"]


def test_an_address_without_its_site_is_joined(tmp_path, monkeypatch):
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text('<a href="/author/x.html">X</a>')
    (tmp_path / "site" / "author").mkdir()
    (tmp_path / "site" / "author" / "x.html").write_text("born March 14")

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(tmp_path / "site"), **k)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    for k in ("NO_PROXY", "no_proxy"):
        monkeypatch.setenv(k, "127.0.0.1,localhost")
    try:
        code = (f"import requests\nr = requests.get('http://127.0.0.1:{srv.server_address[1]}/', timeout=10)\n"
                "print(requests.get('/author/x.html', timeout=10).text)")
        r = run_python(code, tmp_path / "w", name="j.py")
    finally:
        srv.shutdown()
    assert r["returncode"] == 0 and r["stdout"].strip() == "born March 14", r["stderr"]


def test_a_loop_on_one_page_is_seen(tmp_path, monkeypatch):
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text("<p>page</p>")

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(tmp_path / "site"), **k)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    for k in ("NO_PROXY", "no_proxy"):
        monkeypatch.setenv(k, "127.0.0.1,localhost")
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}/"
        once = run_python(f"import requests\nrequests.get({url!r})\nrequests.get({url!r} + 'index.html')", tmp_path, name="a.py")
        loop = run_python(f"import requests\nfor p in range(1, 6):\n    requests.get({url!r})", tmp_path, name="b.py")
    finally:
        srv.shutdown()
    assert "HIVE-SAME" not in once["stderr"]
    assert f"HIVE-SAME: {url} was fetched 5 times" in loop["stderr"]


def test_the_program_hook_parses():
    import ast

    from team.tools.sandbox import _HOOK_SRC
    ast.parse(_HOOK_SRC)  # a stray escape once broke it for every program


def test_a_program_that_fills_memory_is_stopped(tmp_path, monkeypatch):
    import team.tools.sandbox as sb
    monkeypatch.setattr(sb, "MEMORY_MB", 200)
    r = run_python("x = bytearray(600 * 2**20)\nx[::4096] = b'1' * len(x[::4096])\nimport time\ntime.sleep(5)\nprint('done')",
                   tmp_path, name="big.py", timeout=30)
    assert r["returncode"] != 0 and "MEMORY" in r["stderr"] and "done" not in r["stdout"]


def _scripted(monkeypatch, tmp_path, task, replies):
    """The member loop driven by a model that says the given replies in turn; returns the try and what it was told."""
    from team import solo
    from team.board import Board
    from team.guard import Guard
    said = iter(replies)
    monkeypatch.setattr(solo.ternary, "chat", lambda who, messages, **k: next(said))
    board = Board(tmp_path / "run")
    t = solo.member(task, 2, board, Guard(board, "never", goal=task, use_model=False), tmp_path / "run" / "w", 0.0, "t80+x")
    return t, [m["content"] for m in t["messages"] if m["role"] == "user"]


def test_after_its_module_is_saved_a_member_is_told_to_use_it(tmp_path, monkeypatch):
    task = "Write a Python module and save it as twice.py with a function double(x). Then print double(21)."
    t, told = _scripted(monkeypatch, tmp_path, task, [
        "```python\ndef double(x):\n    return 2 * x\n```",
        "```python\nimport twice\nprint(twice.double(21))\n```",
        "DONE"])
    assert any("saved as twice.py" in m for m in told)
    assert t["answer"].strip() == "42" and (tmp_path / "run" / "w" / "twice.py").is_file()


def test_a_search_that_found_nothing_is_told_to_look_at_the_data(tmp_path, monkeypatch):
    task = ("Here is a log:\n2026-01-11 08:01:58 ERROR auth: disk full\n2026-01-11 09:13:03 WARN search: disk full\n"
            "Tell me how many ERROR lines there are.")
    t, told = _scripted(monkeypatch, tmp_path, task, [
        "```python\nprint('No ERROR lines found.')\n```",
        "```python\nprint('1')\n```",
        "DONE"])
    assert any("prints the first 3 items" in m for m in told)
    assert t["answer"].strip() == "1"
