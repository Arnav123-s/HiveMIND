"""The normal CLI serves a configured bank on a machine with no loaded models."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from team import bank_admit, cli, saved, sdk, talk, ternary


class Guest:
    """Execute only the fixed, trusted test method."""
    def __init__(self):
        self.calls = 0

    def run(self, program, inputs, fuel=None):
        self.calls += 1
        scope = {}
        exec(program, scope)
        return [{"value": scope["solve"](sample)} for sample in inputs], 0, 0


def setup_local(tmp_path, monkeypatch):
    guest = Guest()
    bank = tmp_path / "bank"
    spec = dict(task="double_integer", description="Double the supplied integer.", function="double",
                arguments=[dict(name="n", min=0, max=5)], outputs=[0,2,4,6,8,10])
    bank_admit.admit("def double(n): return n+n", spec, bank, guest, origin={"test":True})
    guest.calls = 0
    monkeypatch.setenv("HIVE_BANK", str(bank))
    monkeypatch.delenv("HIVE_ROLES", raising=False)
    monkeypatch.setattr(saved, "guest", lambda:guest)
    monkeypatch.setattr(talk, "speaker", lambda:None)
    monkeypatch.setattr(ternary, "chat", lambda *a,**kw:pytest.fail("model on bank path"))
    monkeypatch.setattr(sdk, "Swarm", lambda *a,**kw:pytest.fail("role swarm on bank path"))
    return guest


def test_plain_once_bank_answers_and_remote_or_explicit_roles_take_precedence(monkeypatch,tmp_path,capsys):
    guest = setup_local(tmp_path,monkeypatch)
    prompt = "Calculate double the integer 3."
    monkeypatch.setattr(cli, "service_up", lambda:False)
    assert cli.main(["--once",prompt]) == 0
    assert capsys.readouterr().out.startswith("6\n") and guest.calls == 1
    monkeypatch.setattr(cli, "service_up", lambda:True)
    remote = []
    monkeypatch.setattr(cli, "say_remote", lambda m,h,r:remote.append(m) or "remote")
    cli.main(["--once",prompt])
    assert remote == [prompt] and guest.calls == 1
    monkeypatch.setenv("HIVE_ROLES","1")
    roles = []
    monkeypatch.setattr(sdk, "Swarm", lambda **kw:object())
    monkeypatch.setattr(cli, "say", lambda s,m,h,r:roles.append(m) or "local roles")
    cli.main(["--local","--once",prompt])
    assert roles == [prompt] and guest.calls == 1


def test_interactive_fallback_keeps_context_and_does_not_submit_bank_requests_twice(tmp_path,monkeypatch):
    guest = setup_local(tmp_path,monkeypatch)
    monkeypatch.setattr(cli, "service_up", lambda:pytest.fail("unexpected service probe with --local"))
    monkeypatch.setattr(sys.stdin,"isatty",lambda:True)
    made, fallback = [], []
    monkeypatch.setattr(sdk, "Swarm", lambda **kw:made.append(kw) or object())
    monkeypatch.setattr(cli,"say",lambda s,m,h,r:fallback.append((m,list(h))) or "ordinary answer")
    loop = cli.converse_loop
    followup = iter(["Double the integer from the previous answer", "Calculate double the integer 4 and save it",
                     "Calculate double the integer 4 in result.csv", "Calculate the double integer",
                     "What is an eclipse?", "Calculate double the integer 5.", "quit"])
    monkeypatch.setattr(cli,"converse_loop", lambda first,step,keep_going:loop(
        first,step,inp=lambda _:next(followup),out=lambda *_:None,keep_going=keep_going))
    cli.main(["--local","Calculate double the integer 3."])
    assert len(fallback) == 5 and len(made) == 1 and guest.calls == 2
    assert fallback[0][1][1][1].startswith("6\n")
    assert len(fallback[-1][1]) == 10


def test_real_cli_answers_with_network_and_model_loading_disabled(tmp_path,monkeypatch):
    sdk_path=os.environ.get("HIVE_FIELDWORK_WASI")
    if not sdk_path:
        pytest.skip("set HIVE_FIELDWORK_WASI to run the actual WASI guest")
    setup_local(tmp_path,monkeypatch)
    marker = tmp_path/"network-used"
    (tmp_path/"sitecustomize.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "def guard(event, args):\n"
        "    if event == 'socket.connect':\n"
        f"        Path({str(marker)!r}).touch()\n"
        "        raise RuntimeError('network disabled during bank-only CLI test')\n"
        "sys.addaudithook(guard)\n")
    root=Path(cli.__file__).resolve().parents[1]
    env=dict(os.environ, HIVE_TERNARY_HOME=str(tmp_path/"empty"), HIVE_FIELDWORK_SDK=sdk_path,
             HIVE_PYTHON=sys.executable, HF_HUB_OFFLINE="1", PYTHONPATH=str(tmp_path))
    env.pop("HIVE_MEMBERS",None)
    result=subprocess.run([str(root/"hive"),"--local","--once","Calculate double the integer 3."],cwd=root,
                          capture_output=True,text=True,env=env,check=True,timeout=120)
    assert result.stdout.startswith("6\n") and "saved method double_integer" in result.stdout
    assert not marker.exists() and not (tmp_path/"empty").exists()
