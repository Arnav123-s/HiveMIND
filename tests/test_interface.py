"""The SDK and the API, with a stand-in hive (no models): jobs, follow-up rounds, every endpoint over real HTTP."""
import json
from pathlib import Path
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

import pytest


class FakeHive:
    """Writes events and a report like the hive. The first round leaves one instruction undone."""
    calls = []

    def __init__(self, goal, run_dir=None, approve="ask", allow_login=(), context="", triage=True):
        self.goal, self.dir, self.context, self.triage = goal, run_dir, context, triage
        FakeHive.calls.append(self)

    def run(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / "events.jsonl", "a") as f:
            for i in range(3):
                f.write(json.dumps({"ts": time.time(), "agent": "researcher", "kind": "step", "msg": f"working {i}"}) + "\n")
                f.flush()
                time.sleep(0.05)
        first = len(FakeHive.calls) % 2 == 1
        rep = "Answer: 42.\n\n## Your instructions\n- ✅ find it\n" + ("- ❌ give two lines - one line only\n" if first else "- ✅ give two lines\n")
        (self.dir / "REPORT.md").write_text(rep)
        (self.dir / "work").mkdir(exist_ok=True)
        (self.dir / "work" / "out.csv").write_text("a,b\n1,2\n")
        return {"dir": str(self.dir), "report": rep, "pending_approvals": []}


@pytest.fixture
def swarm(tmp_path, monkeypatch):
    from team import hive, sdk
    monkeypatch.setattr(hive, "Hive", FakeHive)
    FakeHive.calls = []
    return sdk.Swarm(root=tmp_path / "runs")


def test_a_job_runs_unattended_and_rounds_until_nothing_is_left(swarm):
    job = swarm.submit("Find it and give two lines. Buy nothing.", until_done=2).wait(10)
    assert job.status == "done" and len(job.rounds) == 2 and job.unmet == []
    assert job.rounds[0]["unmet"] == ["give two lines - one line only"]
    first, second = FakeHive.calls
    assert first.goal == second.goal == "Find it and give two lines. Buy nothing."  # the order never changes
    assert "Still not done" in second.context and "Answer: 42." in second.context and second.triage is False
    assert job.report.startswith("Answer: 42.") and job.files[0].endswith("out.csv")
    assert [e["msg"] for e in job.events()][:3] == ["working 0", "working 1", "working 2"]
    again = swarm.get(job.id)
    assert again.status == "done" and again.rounds == job.rounds  # kept on disk


def test_without_until_done_one_round_and_what_is_undone_is_reported(swarm):
    job = swarm.run("Find it and give two lines.")
    assert len(job.rounds) == 1 and job.unmet == ["give two lines - one line only"]


def _server(swarm, monkeypatch):
    from team import api
    monkeypatch.setattr(api, "SWARM", swarm)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), api.H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _post(url, body, headers=None):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read().decode()


def test_openai_and_anthropic_shapes_and_jobs_over_http(swarm, monkeypatch):
    srv, base = _server(swarm, monkeypatch)
    try:
        models = json.loads(urllib.request.urlopen(base + "/v1/models", timeout=10).read())
        assert models["data"][0]["id"] == "hivemind"
        msgs = [{"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Buy the cheapest one."}, {"role": "assistant", "content": "Done."},
                {"role": "user", "content": [{"type": "text", "text": "Now find it and give two lines."}]}]
        code, out = _post(base + "/v1/chat/completions", {"model": "hivemind", "messages": msgs})
        r = json.loads(out)
        assert code == 200 and r["choices"][0]["message"]["content"].startswith("Answer: 42.")
        call = FakeHive.calls[-1]
        assert call.goal == "Now find it and give two lines."  # an old message is context, never the order
        assert "Arnav: Buy the cheapest one." in call.context and "helpful assistant" not in call.context
        code, out = _post(base + "/v1/chat/completions", {"model": "hivemind", "stream": True, "messages": msgs})
        chunks = [json.loads(ln[6:]) for ln in out.splitlines() if ln.startswith("data: {")]
        assert any("reasoning_content" in c["choices"][0]["delta"] for c in chunks)  # progress while it works
        assert "".join(c["choices"][0]["delta"].get("content", "") for c in chunks).startswith("Answer: 42.")
        assert out.rstrip().endswith("data: [DONE]")
        code, out = _post(base + "/v1/messages", {"model": "hivemind", "max_tokens": 100, "messages": msgs})
        m = json.loads(out)
        assert m["type"] == "message" and m["content"][0]["text"].startswith("Answer: 42.")
        code, out = _post(base + "/v1/messages", {"model": "hivemind", "max_tokens": 100, "stream": True, "messages": msgs})
        assert "event: message_start" in out and "event: message_stop" in out and "Answer: 42." in out
        code, out = _post(base + "/v1/jobs", {"task": "Find it.", "until_done": 1})
        jid = json.loads(out)["id"]
        assert code == 202
        events = urllib.request.urlopen(f"{base}/v1/jobs/{jid}/events", timeout=20).read().decode()
        assert "working 0" in events and "event: done" in events
        job = json.loads(urllib.request.urlopen(f"{base}/v1/jobs/{jid}", timeout=10).read())
        assert job["status"] == "done" and job["unmet"] == [] and len(job["rounds"]) == 2
    finally:
        srv.shutdown()


def test_an_api_key_is_required_when_set(swarm, monkeypatch):
    monkeypatch.setenv("AGENT_TEAM_API_KEY", "s3cret")
    srv, base = _server(swarm, monkeypatch)
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + "/v1/models", timeout=10)
        assert e.value.code == 401
        req = urllib.request.Request(base + "/v1/models", headers={"Authorization": "Bearer s3cret"})
        assert urllib.request.urlopen(req, timeout=10).status == 200
    finally:
        srv.shutdown()


def test_the_chat_page_uses_the_same_queue(swarm, monkeypatch):
    srv, base = _server(swarm, monkeypatch)
    try:
        assert b"<textarea" in urllib.request.urlopen(base + "/", timeout=10).read()
        code, out = _post(base + "/api/task", {"task": "Find it."})
        jid = json.loads(out)["queued"]
        swarm.get(jid).wait(10)
        runs = json.loads(urllib.request.urlopen(base + "/api/runs", timeout=10).read())
        assert runs[0]["goal"] == "Find it." and runs[0]["report"].startswith("Answer: 42.") and runs[0]["events"]
    finally:
        srv.shutdown()


def test_two_workers_run_two_jobs_at_once_each_with_its_own_records(tmp_path, monkeypatch):
    from team import hive, llm, sdk
    seen = {}

    class SlowHive(FakeHive):
        def run(self):
            llm.set_recorder(lambda *a, **k: seen.setdefault(str(self.dir), []).append(a[0]))
            time.sleep(0.4)  # waiting on a page: the other job runs meanwhile
            llm._recorder()(f"member-of-{self.dir.parent.name}", [], "")
            out = super().run()
            llm.set_recorder(None)
            return out
    monkeypatch.setattr(hive, "Hive", SlowHive)
    swarm = sdk.Swarm(root=tmp_path / "runs", workers=2)
    t = time.time()
    a, b = swarm.submit("Find A."), swarm.submit("Find B.")
    a.wait(10), b.wait(10)
    assert a.status == b.status == "done" and time.time() - t < 1.5  # at once, not one after the other (2 x 0.55 s+)
    assert sorted(seen) == sorted([str(a.dir / "r1"), str(b.dir / "r1")])
    assert all(v == [f"member-of-{Path(k).parent.name}"] for k, v in seen.items())  # nobody recorded the other's calls


def test_the_kill_switch_stops_every_running_job(tmp_path, monkeypatch):
    from team import stop
    monkeypatch.setattr(stop, "FLAG", tmp_path / "STOP")
    monkeypatch.setattr(stop, "INBOX_FLAG", tmp_path / "inbox" / "STOP")
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    stop.enter(tmp_path / "a"), stop.enter(tmp_path / "b")
    stop.request("test")
    stop.archive(tmp_path / "a")
    stop.leave(tmp_path / "a")
    assert stop.requested()  # b has not stopped yet: the flag stays
    stop.archive(tmp_path / "b")
    stop.leave(tmp_path / "b")
    assert not stop.requested() and (tmp_path / "a" / "STOP.flag").exists() and (tmp_path / "b" / "STOP.flag").exists()


def test_hive_takes_a_prompt_shows_the_work_and_keeps_a_session(swarm, monkeypatch):
    """`hive "prompt"`: progress, then the answer, files and run folder; in a session, earlier turns are context."""
    from team import cli
    said = []
    job = cli.run_prompt(swarm, "Find it and give two lines.", rounds=1, out=said.append)
    text = "\n".join(said)
    assert job.status == "done" and "Answer: 42." in text and "out.csv" in text and "run folder" in text
    said.clear()
    prompts = iter(["Find it.", "Now make it one line.", "/exit"])
    cli.session(swarm, 0, inp=lambda p: next(prompts), out=said.append)
    last = FakeHive.calls[-1]
    assert last.goal == "Now make it one line." and "Arnav: Find it." in last.context and "Answer: 42." in last.context
