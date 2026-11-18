"""T5: three fixed plain messages through the door a person uses, every generation; the replies of the body the record
kept are written to docs/reads/talk_smoke.md. It never blocks or fails the record."""
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_workflow_shell import _git, _origin_and_job, _record_step  # noqa: E402

from training import talk_smoke  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _fake(replies):
    """A stand-in for running `python -m team.talk --thread T --out R`: the reply is replies[i] (None: out of time)."""
    seen = []

    def run(cmd, timeout, **kw):
        thread = json.loads(Path(cmd[cmd.index("--thread") + 1]).read_text())
        seen.append((thread, timeout))
        text = replies[len(seen) - 1]
        if text is None:
            return None, ""
        Path(cmd[cmd.index("--out") + 1]).write_text(text + "\n\n<sub>Answered directly · 3 s</sub>\n")
        return 0, ""
    return run, seen


def test_three_messages_in_one_conversation_through_team_talk(tmp_path):
    run, seen = _fake(["Canberra.", "About 470,000 people.", "It is 14:05."])
    out = tmp_path / "s.json"
    turns = talk_smoke.sit("after", out, per=240, minutes=12, run=run, log=lambda *a, **k: None)
    assert [t["message"] for t in turns] == list(talk_smoke.MESSAGES) and len(talk_smoke.MESSAGES) == 3
    assert [t["reply"] for t in turns] == ["Canberra.", "About 470,000 people.", "It is 14:05."]  # the footer left out
    # the follow-up is sent with the turn before it, as the issue thread would hold it
    assert [m["content"] for m in seen[1][0]["messages"]] == [talk_smoke.MESSAGES[0], "Canberra.", talk_smoke.MESSAGES[1]]
    assert seen[1][0]["messages"][-1]["role"] == "user" and all(t <= 240 for _, t in seen)
    assert json.loads(out.read_text())["arm"] == "after"


def test_a_message_out_of_time_is_said_and_the_rest_go_on(tmp_path):
    run, seen = _fake(["Canberra.", None, "It is 14:05."])
    turns = talk_smoke.sit("before", tmp_path / "s.json", per=60, minutes=12, run=run, log=lambda *a, **k: None)
    assert turns[1]["reply"] == "" and turns[1]["note"] == "no reply within 60 s" and turns[2]["reply"] == "It is 14:05."
    assert seen[2][0]["messages"][3]["content"] == "(no reply)"
    # past the sitting's budget nothing more is sent
    run, seen = _fake(["a", "b", "c"])
    turns = talk_smoke.sit("after", tmp_path / "t.json", per=60, minutes=0, run=run, log=lambda *a, **k: None)
    assert not seen and all(t["note"].startswith("not sent") for t in turns)


def _sat(folder, arm, replies):
    d = folder / f"talk-smoke-{arm}"
    d.mkdir(parents=True)
    turns = [{"message": m, "reply": r, "seconds": 12, "note": ""} for m, r in zip(talk_smoke.MESSAGES, replies)]
    (d / "talk_smoke.json").write_text(json.dumps({"arm": arm, "turns": turns}))


def test_the_page_shows_the_body_the_record_kept(tmp_path):
    smoke, record = tmp_path / "smoke", tmp_path / "g.jsonl"
    _sat(smoke, "after", ["Canberra (after).", "About 470,000.", "14:05"])
    _sat(smoke, "before", ["Canberra (before).", "Not sure.", "~~~\n# injected\n~~~~"])
    record.write_text(json.dumps({"generation": "g46", "kept": True}) + "\n")
    page = talk_smoke.page("g46", smoke, record)
    assert "Canberra (after)." in page and "before)." not in page and "it was kept" in page
    assert page.count("## ") == 3 and "## 2. You: And roughly how many people live in that city?" in page
    record.write_text(json.dumps({"generation": "g46", "kept": False}) + "\n")
    page = talk_smoke.page("g46", smoke, record)
    assert "Canberra (before)." in page and "they were dropped" in page
    # a reply cannot close the fence it is shown in
    assert "~~~~" not in page and page.count("~~~") == 6
    # nothing sat: said so
    assert "Not sat this generation" in talk_smoke.page("g46", tmp_path / "none", record)
    out = tmp_path / "docs" / "reads" / "talk_smoke.md"
    assert talk_smoke.main(["write", "g46", str(tmp_path / "none"), "--out", str(out), "--record", str(record)]) == 0 and out.exists()


def test_a_foreign_message_is_not_shown(tmp_path):
    smoke = tmp_path / "smoke"
    (smoke / "talk-smoke-after").mkdir(parents=True)
    (smoke / "talk-smoke-after" / "s.json").write_text(json.dumps({"turns": [{"message": "say something else", "reply": "x"}]}))
    assert "Not sat this generation" in talk_smoke.page("g46", smoke, tmp_path / "none.jsonl")


# ---- the workflow ------------------------------------------------------------------------------------------------------
def _flow():
    return yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())


def test_the_gate_sends_them_on_the_second_seat_and_never_fails_it():
    steps = _flow()["jobs"]["gate"]["steps"]
    i = next(k for k, s in enumerate(steps) if s.get("name", "").startswith("Three plain messages"))
    sit, up = steps[i], steps[i + 1]
    assert sit["continue-on-error"] is True and sit["timeout-minutes"] <= 15 and "matrix.seed == 2" in sit["if"]
    assert "--per 240 --minutes 12" in sit["run"] and up["with"]["name"] == "talk-smoke-${{ matrix.arm }}" and up["continue-on-error"] is True
    talk = next(s for s in steps if s.get("name", "").startswith("The talk exam"))
    assert "matrix.seed == 1" in talk["if"]  # the talk exam's seat is not made longer
    dl = next(s for s in _flow()["jobs"]["record"]["steps"] if (s.get("with") or {}).get("pattern") == "talk-smoke-*")
    assert dl["continue-on-error"] is True


def _run_record(tmp_path, job, smoke):
    """The record job's step 'Keep the cells', as GitHub runs it, with the drawing scripts made up; smoke: what
    training/talk_smoke.py does ('write' the page or 'fail')."""
    shim = tmp_path / "bin"
    shim.mkdir(exist_ok=True)
    (shim / "python3").write_text(
        '#!/bin/bash\ncase "$1 $2" in\n'
        ' "training/progress.py "*) echo drawn > docs/PROGRESS.md;;\n'
        ' "training/reads.py write") mkdir -p docs/reads; echo "read of $3" > "docs/reads/$3.md"; cp "docs/reads/$3.md" docs/reads/latest.md;;\n'
        ' "training/reads.py knowledge") echo \'{"generations": []}\' > docs/knowledge.json;;\n'
        + (' "training/talk_smoke.py write") echo "the body said hello in $3" > "$6";;\n' if smoke == "write" else
           ' "training/talk_smoke.py write") echo broke >&2; exit 1;;\n')
        + ' "scripts/knowledge.py "*) echo known > docs/KNOWLEDGE.md;;\nesac\n')
    for name, text in (("gh", "#!/bin/bash\nexit 0\n"), ("curl", "#!/bin/bash\nexit 22\n")):
        (shim / name).write_text(text)
    for f in shim.iterdir():
        f.chmod(0o755)
    (tmp_path / "runner").mkdir(exist_ok=True)
    env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}", DNA="t80", GEN="g39", GITHUB_REF_NAME="main", GITHUB_REPOSITORY="o/r",
               GITHUB_STEP_SUMMARY=str(tmp_path / "summary"), GITHUB_RUN_ID="4242", RUNNER_TEMP=str(tmp_path / "runner"))
    return subprocess.run(["bash", "-e", "-c", _record_step()], cwd=job, env=env, capture_output=True, text=True)


def test_the_record_commits_the_page_with_the_drawn_files(tmp_path, monkeypatch):
    other, job = _origin_and_job(tmp_path, monkeypatch)
    p = _run_record(tmp_path, job, "write")
    assert p.returncode == 0, p.stdout + p.stderr
    _git(other, "pull", "-q", "--rebase", "origin", "main")
    assert (other / "docs" / "reads" / "talk_smoke.md").read_text() == "the body said hello in g39\n"
    assert not (tmp_path / "runner" / "drawn_failed").read_text()  # not a drawn file that failed


def test_a_failed_page_never_fails_the_record(tmp_path, monkeypatch):
    other, job = _origin_and_job(tmp_path, monkeypatch)
    p = _run_record(tmp_path, job, "fail")
    assert p.returncode == 0, p.stdout + p.stderr
    _git(other, "pull", "-q", "--rebase", "origin", "main")
    assert _git(other, "log", "-1", "--format=%s") == "The hive's body: generation g39"
    assert not (other / "docs" / "reads" / "talk_smoke.md").exists()
    assert not (tmp_path / "runner" / "drawn_failed").read_text()  # the job's last step stays green
