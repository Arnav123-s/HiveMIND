from collections import Counter
from http.server import HTTPServer
from threading import Thread

import pytest

from team import solo
from team.familiarity import familiar
from team.public_examples import module_examples, required_gets
from team.tools.sandbox import member_http, run_python
from training.experiments.astra_orders.http_cache.study import Controls


class Log:
    def __init__(self):
        self.events = []

    def log(self, *fields):
        self.events.append(fields)


def worker(task, programs, work, monkeypatch):
    # Only generation is scripted. Normal guard, CPython runs, repair turns and file restoration are used.
    replies = iter([f"```python\n{code}\n```" for code in programs] + ["DONE"])
    monkeypatch.setattr(solo.llm, "chat", lambda *a, **k: next(replies))
    board = Log()
    result = solo.member(task, 1, board, solo.Guard(board, approve="never", goal=task),
                         work, 0, who="coder")
    return result, board


@pytest.fixture
def origin(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    server = HTTPServer(("127.0.0.1", 0), Controls)
    server.visits = Counter()
    server.seen = []
    server.public_feed = True
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize("reuse", [False, True])
def test_same_address_can_hold_five_cursor_pages_across_worker_turns(origin, tmp_path, monkeypatch, reuse):
    base, server = origin
    monkeypatch.setenv("HIVE_HTTP_CACHE", str(int(reuse)))
    monkeypatch.setenv("HIVE_PAGE_CHECKS", "1")
    task = "Use the first 5 pages of the feed to count its authors. Print their counts."
    prog = ("import requests\nfrom collections import Counter\ncounts = Counter()\nfor i in range(1,6):\n"
            f"    page = requests.get({base + '/feed'!r}, headers={{'X-Cursor':str(i)}})\n"
            "    counts.update(page.json()['authors'])\nprint(dict(sorted(counts.items())))")
    for idx in range(2):
        result, board = worker(task, [prog, prog + "\n# second traversal"], tmp_path / str(idx), monkeypatch)
        assert result["answer"] == "{'Ada': 2, 'Lin': 4, 'Mei': 1, 'Ros': 2}"
        assert [e[-1] for e in board.events if e[1] == "http"] == [
            "HIVE-URLS: 1 hits=0 covered=", f"HIVE-URLS: 1 hits={5 if reuse else 0} covered="]
        assert server.visits["/feed"] == (5 if reuse else 10) * (idx + 1)


def test_worker_observes_only_a_literal_required_list(origin, tmp_path, monkeypatch):
    base, _ = origin
    a, b = base + "/a", base + "/b"
    task = f"Using requests, fetch each of these URLs:\n{a}\n{b}\n\nPrint done."
    monkeypatch.setenv("HIVE_PAGE_CHECKS", "1")
    first = f"import requests\nrequests.get({a!r})\nprint('one checked')"
    second = f"import requests\nrequests.get({b!r})\nprint('both checked')"
    result, board = worker(task, [first, second], tmp_path, monkeypatch)
    assert result["answer"] == "both checked"
    assert any(f"Still missing: {b}" in m["content"] for m in result["messages"] if m["role"] == "user")
    assert [e[-1] for e in board.events if e[1] == "http"] == [
        "HIVE-URLS: 1 hits=0 covered=0", "HIVE-URLS: 1 hits=0 covered=1"]
    assert required_gets("Visit the first 5 pages at " + a) == ()


def test_sensitive_uncacheable_and_encoded_requests_go_to_origin(origin, tmp_path, monkeypatch):
    base, server = origin
    monkeypatch.setenv("HIVE_HTTP_CACHE", "1")
    with member_http("Read the feed"):
        for _ in range(2):
            program = f"""import requests
base = {base!r}
for path in ('/private','/gzip','/too-old','/set-cookie','/lookup?x=1','/ambiguous','/no-offer'):
    requests.get(base + path).raise_for_status()
requests.get(base + '/auth', headers={{'Authorization':'Bearer fixture'}})
print('ok')"""
            assert run_python(program, tmp_path)["returncode"] == 0
    assert set(server.visits.values()) == {2}
    assert len(server.visits) == 8


EXAMPLES = """Write answers.py containing a function count(xs) returning a count.
Acceptance tests:
```python
assert count([]) == 0
assert count([4]) == 1
```
Print ready after saving it."""


def test_explicit_examples_are_data_not_code():
    assert module_examples(EXAMPLES, ["answers.py"]) == (("count", [[]], 0), ("count", [[4]], 1))
    for bad in ("helper()", "assert count([]) == side_effect()", "assert count((4,)) == 1"):
        assert not module_examples(EXAMPLES.replace("assert count([]) == 0", bad), ["answers.py"])
    assert not module_examples(EXAMPLES, ["a.py", "b.py"])
    assert not module_examples(EXAMPLES.replace("Acceptance tests:", "A bad example:"), ["answers.py"])


def test_inspect_prompt_only_for_unfamiliar(tmp_path, monkeypatch):
    from team.public_examples import INSPECT
    task = "Please print the number of squares in this checkerboard."
    monkeypatch.setenv("HIVE_ASSERT_FIRST", "1")
    for checked in (False, True):
        monkeypatch.setattr(solo, "solved", lambda: [{"task": task, "checked": checked}])
        assert familiar(task) is checked
        result, _ = worker(task, ["print(64)"], tmp_path, monkeypatch)
        assert (INSPECT in result["messages"][1]["content"]) is (not checked)


def test_wasi_counterexample_reaches_the_next_worker_turn(tmp_path, monkeypatch):
    from team import saved
    if saved.guest() is None:
        pytest.skip("requires HIVE_FIELDWORK_SDK")
    monkeypatch.setenv("HIVE_ASSERT_FIRST", "1")
    def save(source):
        return f"open('answers.py', 'w').write({source!r})\nprint('ready')"
    programs = [save("def count(xs): return xs[0]"), save("def count(xs): return len(xs)")]
    result, _ = worker(EXAMPLES, programs, tmp_path, monkeypatch)
    assert result["hints"] == ["supplied_test"]
    assert any("expected 0" in m["content"] and "raised IndexError" in m["content"] for m in result["messages"])
    assert not result["delivery"]["issues"]
    assert result["answer"] == "ready"
    assert (tmp_path / "answers.py").read_text() == "def count(xs): return len(xs)"


def test_disproved_peer_cannot_confirm_a_single_survivor():
    bad = {"answer": "ready", "supplied_test_failed": True}
    plausible = {"answer": "ready"}
    assert solo.agreeing([bad, plausible], EXAMPLES) == []


def test_reread_directive_forgets_the_previous_representation(origin, tmp_path, monkeypatch):
    base, server = origin
    monkeypatch.setenv("HIVE_HTTP_CACHE", "1")
    prefix = f"import requests\nu = {base + '/reread'!r}\n"
    with member_http("Read twice"):
        for code, expected in (("print(requests.get(u).text)", "1"),
                               ("print(requests.get(u).text)", "1"),
                               ("print(requests.get(u, headers={'Cache-Control':'no-cache'}).text)", "2"),
                               ("print(requests.get(u).text)", "3")):
            assert run_python(prefix + code, tmp_path)["stdout"].strip() == expected
    assert server.visits["/reread"] == 3


def test_missing_freshness_on_new_variant_invalidates_prior_public_variant(origin, tmp_path, monkeypatch):
    base, server = origin
    monkeypatch.setenv("HIVE_HTTP_CACHE", "1")
    with member_http("Read cursor pages"):
        for cursor, public in ((1, True), (2, False), (1, False)):
            server.public_feed = public
            program = f"import requests\nprint(requests.get({base + '/feed'!r}, headers={{'X-Cursor': {str(cursor)!r}}}).text)"
            result = run_python(program, tmp_path)
            assert result["returncode"] == 0 and "authors" in result["stdout"]
    assert server.visits["/feed"] == 3


def test_prepared_sends_preserve_transport_and_bytes_headers(tmp_path, monkeypatch):
    from email.utils import formatdate
    from io import BytesIO
    from pathlib import Path

    import requests
    from requests.adapters import HTTPAdapter
    from urllib3._collections import HTTPHeaderDict
    from urllib3.response import HTTPResponse

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "team/tools/program_hooks"))
    from page_cache import install

    calls = []
    def transport(adapter, request, **settings):
        route = "proxy" if settings["proxies"] else "verified" if settings["verify"] else "unverified"
        calls.append(route)
        raw = HTTPResponse(body=BytesIO(route.encode()), status=200, reason="OK", preload_content=False,
                           headers=HTTPHeaderDict({"Date": formatdate(usegmt=True), "Cache-Control": "public, max-age=60"}))
        return adapter.build_response(request, raw)

    monkeypatch.setattr(HTTPAdapter, "send", transport)
    monkeypatch.setattr(requests.Session, "send", requests.Session.send)  # Restore the installed hook after the test.
    install(str(tmp_path / "pages.sqlite"))
    with requests.Session() as session:
        session.trust_env = False
        first = "https://origin.invalid/first"
        prepared = session.prepare_request(requests.Request("GET", first))
        assert session.get(first).text == session.get(first).text == "verified"
        assert calls == ["verified"]

        session.proxies = {"https": "http://proxy.invalid"}
        assert session.send(prepared).text == "proxy"
        session.proxies.clear()
        session.stream = True
        streamed = session.send(prepared)
        assert streamed.raw.read() == b"verified"
        session.stream = False

        second = "https://origin.invalid/second"
        prepared = session.prepare_request(requests.Request("GET", second))
        session.verify = False
        assert session.send(prepared).text == "unverified"
        session.verify = True
        assert session.get(second).text == "verified"

        for _ in range(2):
            assert session.get(first, headers={"Accept": b"application/json"}).text == "verified"
        assert calls == ["verified", "proxy", "verified", "unverified", "verified", "verified", "verified"]
