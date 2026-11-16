"""A member's server that dies or stops answering is started again, the cell put back on, and the request asked once
more; a bounded number of times in one process. Tested against a fake llama-server: a tiny HTTP server that answers
the same requests, and dies or hangs on a chat request when told to."""
import json
import os
import socket
import stat
import sys
import time

import pytest

from team import ternary
from training import exam

FAKE = '''#!{python}
import json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
args = sys.argv[1:]
port = int(args[args.index("--port") + 1])
loras = [args[i + 1] for i, a in enumerate(args) if a == "--lora"]
scale = [0.0] * len(loras)  # started with --lora-init-without-apply: every cell loaded, none on
d = os.environ["FAKE_DIR"]
open(os.path.join(d, "starts"), "a").write("%d\\n" % os.getpid())

def mode():
    p = os.path.join(d, "mode")
    m = open(p).read().strip() if os.path.exists(p) else ""
    if m.endswith("_once"):
        os.remove(p)
    return m

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        if self.path == "/health":
            return self.send({{"status": "ok"}})
        if self.path == "/lora-adapters":
            return self.send([{{"id": i, "path": p, "scale": scale[i]}} for i, p in enumerate(loras)])
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/lora-adapters":
            for s in body:
                scale[s["id"]] = s["scale"]
            open(os.path.join(d, "switches"), "a").write(json.dumps({{"pid": os.getpid(), "scales": body}}) + "\\n")
            return self.send(body)
        m = mode()
        if m.startswith("die"):
            os._exit(1)
        if m.startswith("hang"):
            time.sleep(3600)
        on = [os.path.basename(p).split("+")[1][:-5] for i, p in enumerate(loras) if scale[i] == 1.0]
        self.send({{"choices": [{{"message": {{"content": "on: " + ",".join(on)}}}}]}})

ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
'''


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def fake(tmp_path, monkeypatch):
    bin_dir, cells, state = tmp_path / "bin", tmp_path / "cells", tmp_path / "state"
    for d in (bin_dir, cells, state):
        d.mkdir()
    server = bin_dir / "llama-server"
    server.write_text(FAKE.format(python=sys.executable))
    server.chmod(server.stat().st_mode | stat.S_IEXEC)
    for c in ("c1", "c2"):
        (cells / f"t2+{c}.gguf").write_bytes(b"")
    n = _free_port()
    monkeypatch.setenv("HIVE_TERNARY_BIN", str(server))
    monkeypatch.setenv("FAKE_DIR", str(state))
    monkeypatch.setattr(ternary, "HOME", tmp_path / "home")
    monkeypatch.setattr(ternary, "ADAPTERS", cells)
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path / "no-engrams")
    monkeypatch.setattr(ternary, "weights", lambda base: "fake.gguf")
    monkeypatch.setattr(ternary, "port", lambda member: n)
    monkeypatch.setattr(ternary, "_ON", {})
    monkeypatch.setattr(ternary, "_PROC", {})
    monkeypatch.setattr(ternary, "_RESTARTED", [0])
    monkeypatch.setattr(ternary, "RESTARTS", 3)
    yield state
    ternary._kill(n)


def _starts(state):
    return (state / "starts").read_text().split()


def _switches(state):
    return [json.loads(x) for x in (state / "switches").read_text().splitlines()]


def _ask(member="t2+c1"):
    return ternary.chat(member, [{"role": "system", "content": "s"}, {"role": "user", "content": "task"}])


def test_dead_server_is_started_again_and_the_cell_put_back_on(fake, capsys):
    assert _ask() == "on: c1"
    (fake / "mode").write_text("die_once")  # it dies in the middle of the next request
    assert _ask() == "on: c1"  # answered by a new server, with the cell on again
    first, second = _starts(fake)
    assert first != second
    last = _switches(fake)[-1]  # the cell was switched on in the new server, not left off
    assert last["pid"] == int(second) and {"id": 0, "scale": 1.0} in last["scales"] and {"id": 1, "scale": 0.0} in last["scales"]
    err = capsys.readouterr().err
    assert err.count("ternary: the server of t2") == 1 and "memory free" in err
    # the process that died is gone, its port taken by the new one
    assert not ternary._running(int(first))


def _zombie(pid):
    try:
        return open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[0] == "Z"
    except OSError:
        return False


def test_a_hung_request_times_out_and_recovers(fake, capsys, monkeypatch):
    monkeypatch.setattr(ternary, "_patience", lambda n: 2)
    assert _ask() == "on: c1"
    (fake / "mode").write_text("hang_once")
    t0 = time.time()
    assert _ask("t2+c2") == "on: c2"  # also the switch to the other cell survives the restart
    assert time.time() - t0 < 30
    assert len(_starts(fake)) == 2
    assert "did not answer in 2 s" in capsys.readouterr().err


def test_the_restarts_are_bounded(fake, monkeypatch):
    monkeypatch.setattr(ternary, "RESTARTS", 1)
    (fake / "mode").write_text("die")  # dies on every chat request
    with pytest.raises(ternary.Silent, match="also after it was started again"):
        _ask()
    assert len(_starts(fake)) == 2  # the first and one more
    with pytest.raises(ternary.Silent, match="not again"):
        _ask()
    assert len(_starts(fake)) == 2  # no third


def test_a_server_that_does_not_answer_the_switch_is_started_again(fake, monkeypatch):
    # what trial run 32's exam met: "the server does not answer when told which cell is on"
    real, calls = ternary._switch, []

    def switch(at, scales):
        calls.append(scales)
        if len(calls) == 1:
            raise ternary.Silent("the server does not answer when told which cell is on")
        return real(at, scales)
    monkeypatch.setattr(ternary, "_switch", switch)
    assert _ask() == "on: c1"
    assert len(_starts(fake)) == 2 and len(calls) == 2


def test_a_task_out_of_time_takes_what_it_started_with_it(tmp_path):
    # the task starts a program in a session of its own (as team/tools/sandbox.py does) and then hangs
    pidfile = tmp_path / "pid"
    task = ("import subprocess, sys, time\n"
            f"p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)'], start_new_session=True)\n"
            f"open({str(pidfile)!r}, 'w').write(str(p.pid))\n"
            "print('ternary: the server of t2 did not answer in 2 s; ended and started again', file=sys.stderr, flush=True)\n"
            "time.sleep(600)\n")
    code, err = exam.run_task([sys.executable, "-c", task], 3)
    assert code is None and "ternary: the server of t2" in err
    pid = int(pidfile.read_text())
    t0 = time.time()
    while time.time() - t0 < 10:
        try:
            os.kill(pid, 0)
        except OSError:
            break
        if _zombie(pid):
            break
        time.sleep(0.1)
    else:
        os.kill(pid, 9)
        pytest.fail("the program the task started outlived it")


def test_the_runtime_source_fetch_is_tried_again_when_the_network_drops(tmp_path, monkeypatch):
    """g35: a slice was lost because one fetch of the runtime source failed (exit 128)."""
    import subprocess
    from team import ternary
    monkeypatch.setattr(ternary, "HOME", tmp_path)
    (tmp_path / "ik_llama.cpp" / ".git").mkdir(parents=True)
    fetches = []

    def run(cmd, check=False, **k):
        if "fetch" in cmd:
            fetches.append(1)
            return subprocess.CompletedProcess(cmd, 128 if len(fetches) < 3 else 0)
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(ternary.subprocess, "run", run)
    monkeypatch.setattr(ternary.time, "sleep", lambda s: None)
    ternary.source()
    assert len(fetches) == 3
    fetches.clear()
    monkeypatch.setattr(ternary.subprocess, "run", lambda cmd, check=False, **k: fetches.append(1) or subprocess.CompletedProcess(cmd, 128 if "fetch" in cmd else 0))
    import pytest
    with pytest.raises(RuntimeError):
        ternary.source()
    assert len(fetches) == 4


def test_a_server_that_ends_at_once_says_how_and_why(fake, tmp_path, monkeypatch):
    """g35, seed 4: every start of the server ended at once and was reported as 'did not come up in 600 s'; its own
    words were in a log no artifact kept. Now the exit code and its last lines are in the error."""
    dead = tmp_path / "bin" / "dead-server"
    dead.write_text(f"#!{sys.executable}\nimport sys\nprint('loading model ...')\nsys.stderr.write('error: failed to open fake.gguf: unexpected end of file\\n')\nsys.exit(3)\n")
    dead.chmod(dead.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("HIVE_TERNARY_BIN", str(dead))
    (ternary.HOME).mkdir(parents=True, exist_ok=True)
    (ternary.HOME / "t2.log").write_text("an older start's words, not this one's\n")
    t0 = time.time()
    with pytest.raises(RuntimeError) as e:
        ternary._start("t2", wait=60)
    said = str(e.value)
    assert time.time() - t0 < 30  # no waiting out the minute for a server that has ended
    assert "ended" in said and "exit code 3" in said and "unexpected end of file" in said
    assert "older start" not in said  # only this start's own lines
