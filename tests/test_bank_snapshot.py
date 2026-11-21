import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from team import api, bank_snapshot, saved, talk
from test_bank_admit import Guest
from training import exam, grow

TASK = "Double the integer"
SPEC = {"task":"double_integer", "description":"Double the supplied integer.", "function":"double",
        "arguments":[{"name":"n","min":0,"max":3}], "outputs":[0,2,4,6]}
SRC = "def double(n):\n    return n+n"


def proposal(shard, program, checked=True):
    shard.mkdir(parents=True, exist_ok=True)
    with (shard / "rows.jsonl").open("a") as out:
        print(json.dumps({"member":1, "who":"cell", "seed":101, "verified_member":checked, "output":"```python\n"+program+"\n```", "type":"first"}), file=out)


def setup(tmp_path):
    contracts = tmp_path / "contracts"
    contracts.mkdir()
    (contracts / "double.json").write_text(json.dumps(SPEC))
    practice = tmp_path / "artifacts"
    proposal(practice / "rows-1", SRC)
    proposal(practice / "rows-1", "def double(n): return 5")  # independently disproved
    proposal(practice / "rows-dream-1", "def double(n): return n*2")  # separate untrusted stream
    proposal(practice / "rows-1", "def double(n): return n*2", checked=False)
    return practice, contracts


def test_snapshot_restore_rechecks_scope_keeps_versions_and_rejects_corruption(tmp_path, monkeypatch):
    source, contracts = setup(tmp_path)
    one, two = tmp_path / "one.json", tmp_path / "two.json"
    guest = Guest()
    result = bank_snapshot.promote(None, one, source, contracts, guest)
    assert result["methods"] == 1 and result["tested"] == 2 and result["rejected"] == 1
    assert bank_snapshot.promote(None, one, source, contracts, guest) == result
    altered = dict(SPEC, description="Double every input integer in the new convention.", outputs=[1,3,5,7])
    (contracts / "v2.json").write_text(json.dumps(altered))
    proposal(source / "rows-2", "def double(n): return 2*n+1")
    result = bank_snapshot.promote(one, two, source, contracts, guest)
    assert result["methods"] == 2
    first = saved.answer(TASK + " 2", bank=one, runner=guest)
    second = saved.answer(TASK + " 2", bank=two, runner=guest)
    assert first["value"] == 4 and second["status"] == "ambiguous"
    with pytest.raises(ValueError, match="different version"):
        bank_snapshot.promote(one, one, source, contracts, guest)
    forged = json.loads(one.read_text())
    record = forged["methods"][0]
    record["source"] = record["source"].replace("return n+n", "return 0")
    record["digest"] = bank_snapshot.work.fingerprint(record["source"])
    forged["sha256"] = bank_snapshot.digest(forged["methods"])
    broken = tmp_path / "forged.json"
    broken.write_text(json.dumps(forged))
    with pytest.raises(ValueError):
        bank_snapshot.promote(broken, tmp_path / "restored.json", source, contracts, guest)
    assert not (tmp_path / "restored.json").exists()
    (contracts / "double.json").unlink()
    with pytest.raises(ValueError, match="original independent contract"):
        bank_snapshot.promote(two, tmp_path / "third.json", source, contracts, guest)
    package = json.loads(two.read_text())
    package["methods"].pop()
    two.write_text(json.dumps(package))
    assert saved.answer(TASK + " 2", bank=two, runner=guest) is None


def test_ordinary_model_and_api_paths_use_independent_bank_requests_only(tmp_path, monkeypatch):
    source, contracts = setup(tmp_path)
    snap = tmp_path / "bank.json"
    guest = Guest()
    bank_snapshot.promote(None, snap, source, contracts, guest)
    monkeypatch.setenv("HIVE_BANK", str(snap))
    monkeypatch.setattr(saved, "guest", lambda:guest)
    monkeypatch.setattr(talk, "speaker", lambda:pytest.fail("unnecessary body lookup"))
    monkeypatch.setattr(talk, "route", lambda *a:pytest.fail("unnecessary classification"))
    assert talk.reply(TASK+" 3")["saved"]["value"] == 6
    assert api.H._submit_chat(None, {"messages":[{"role":"user","content":TASK+" 2"}]}).report.startswith("4\n")
    assert saved.direct("Double that integer again.", [("user",TASK+" 2")]) is None
    assert saved.direct(TASK+" 2", [{"role":"user","content":"From now on use binary notation."}]) is None
    assert saved.direct(TASK+' {"n":2} plus 9') is None
    assert saved.direct(TASK+" 2", [("user", "Write your numbers in binary.")]) is None
    assert saved.direct(TASK+" 2", [("user", TASK+" 3")])["value"] == 4
    assert saved.direct(TASK+" 2", [("user", "What is an eclipse?")])["value"] == 4
    assert saved.direct(TASK+" 2", [("user", "Create a poem in result.txt.")])["value"] == 4
    assert saved.direct(TASK+" 2", [("user", "Can you always format answers as binary?")]) is None
    assert saved.direct(TASK+" 2", [("user", "My convention is to round after doubling.")]) is None
    from http.server import ThreadingHTTPServer
    import threading
    import urllib.request
    monkeypatch.delenv("AGENT_TEAM_API_KEY", raising=False)
    with ThreadingHTTPServer(("127.0.0.1", 0), api.H) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        def post(path, body):
            req = urllib.request.Request(url + path, data=json.dumps(body).encode(),
                                         headers={"Content-Type":"application/json"})
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.load(response)
        try:
            assert post("/api/task", {"task":TASK+" 2"})["answer"].startswith("4\n")
            choices = post("/v1/chat/completions", {"messages":[{"role":"user","content":TASK+" 2"}]})["choices"]
            assert choices[0]["message"]["content"].startswith("4\n")
        finally:
            server.shutdown()
            thread.join()



def test_equally_matching_method_names_do_not_win_by_description_length():
    methods = [{"task":"double_integer", "description":"Double the supplied integer."},
               {"task":"double_integer_item","description":"Double each supplied integer for the older item convention."}]
    assert saved.fit("Double the integer 2", methods) is None


def test_ordinary_training_rows_match_individual_seat_and_worker(tmp_path):
    (tmp_path / "members").mkdir()
    meta = tmp_path / "members"
    (meta / "members.json").write_text(json.dumps({"agreeing":[1]}))
    (meta / "member1.json").write_text(json.dumps({"who":"worker","answer":"4","program":SRC,
        "messages":[{"role":"system","content":"python"},{"role":"user","content":TASK},{"role":"assistant","content":SRC}]}))
    for who, expected in (("worker",True), ("different",False)):
        (tmp_path / "exam.json").write_text(json.dumps({"ok":True, "members":[{"member":1,"who":who,"ok":True}]}))
        rows = grow.rows_of(tmp_path, TASK, "arithmetic", 101)
        assert rows and all(r["verified_member"] is expected for r in rows)


def test_real_offline_snapshot_then_ordinary_worker_cli(tmp_path, monkeypatch):
    sdk = os.environ.get("HIVE_FIELDWORK_WASI")
    if not sdk:
        pytest.skip("set HIVE_FIELDWORK_WASI for the real guest")
    source, contracts = setup(tmp_path)
    run_dir = tmp_path / "practice" / "task"
    members = run_dir / "members"
    members.mkdir(parents=True)
    worker = {"who":"t80+demo", "answer":"4", "program":SRC,
              "messages":[{"role":"system","content":"Python"},{"role":"user","content":TASK},
                          {"role":"assistant","content":SRC}]}
    (members / "member1.json").write_text(json.dumps(worker))
    (members / "members.json").write_text(json.dumps({"agreeing":[1]}))
    grades = exam.each_member(run_dir, lambda folder, answer: (answer == "4", "independent practice verdict"))
    assert grades == [{"who":"t80+demo","ok":True,"member":1}]
    (run_dir / "exam.json").write_text(json.dumps({"ok":True, "members":grades}))
    rows = grow.rows_of(run_dir, TASK, "arithmetic", 101)
    assert [r["verified_member"] for r in rows if r["type"] == "first"] == [True]
    (source / "rows-1" / "rows.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    snapshot = tmp_path / "bank.json"
    root = Path(talk.__file__).resolve().parents[1]
    env = dict(os.environ, HIVE_FIELDWORK_SDK=sdk, HIVE_BANK=str(snapshot), HIVE_MEMBERS="t80+unloaded",
               HIVE_PYTHON=sys.executable, HF_HUB_OFFLINE="1", RAYON_NUM_THREADS="1")
    code = ("import sys\ndef offline(event, args):\n"
            "    if event == 'socket.connect': raise RuntimeError('network forbidden')\n"
            "sys.addaudithook(offline)\n")
    (tmp_path / "sitecustomize.py").write_text(code)
    env["PYTHONPATH"] = str(tmp_path)
    def run(*args):
        return subprocess.run([str(root / "hive"),*args], env=env, cwd=root, text=True, capture_output=True, timeout=100,check=True)
    run("bank-promote","--contracts",str(contracts),"--practice",str(source),"--output",str(snapshot))
    assert run("--local","--once",TASK+" 3").stdout.splitlines()[-3] == "6"
    thread, reply = tmp_path / "thread.json", tmp_path / "reply.md"
    thread.write_text(json.dumps({"messages":[{"role":"user","content":TASK+" 1"}]}))
    cmd = [sys.executable, "-m", "team.talk", "--bank-only", "--thread", str(thread), "--out", str(reply)]
    subprocess.run(cmd, env=env, cwd=root, check=True, timeout=100)
    assert reply.read_text().startswith("2") and "two workers" not in reply.read_text().lower()
    thread.write_text(json.dumps({"messages":[{"role":"user","content":"Use words for every number."},
                                              {"role":"user","content":TASK+" 1"}]}))
    assert subprocess.run(cmd, env=env, cwd=root, timeout=100).returncode == 3
