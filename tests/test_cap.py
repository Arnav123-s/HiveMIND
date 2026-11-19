"""The time cap (SIGTERM, then SIGKILL, from training/exam.run_task) does not throw away the answers already in: g48's
practice lost 15 of 42 tasks to the 600 s cap, with a member's right answer (h10004806_00 at 427 s) never delivered."""
import os
import signal
import subprocess
import sys
import time

from team import solo

TASK = "Add 2 and 3 and tell me the sum."


def _hive(monkeypatch, replies):
    left = list(replies)

    def chat(*a, **k):
        r = left.pop(0)
        if r == "CAP":
            os.kill(os.getpid(), signal.SIGTERM)  # the cap arrives while this member is working
            time.sleep(5)
            raise AssertionError("the cap did not interrupt the member")
        return r if r == "DONE" else f"```python\n{r}\n```"
    monkeypatch.setattr(solo.llm, "chat", chat)
    return left


def test_the_answers_in_when_the_cap_hits_still_go_through_agreement(tmp_path, monkeypatch):
    _hive(monkeypatch, ["print('sum: 5')", "DONE", "CAP"])
    old = signal.getsignal(signal.SIGTERM)
    out = solo.run(TASK, tmp_path / "a", "never", members=2)
    assert signal.getsignal(signal.SIGTERM) is old  # the handler is put back
    assert (tmp_path / "a" / "REPORT.md").read_text() == out["report"]  # the run delivers instead of leaving nothing
    assert out["tries"] == 1 and "sum: 5" in out["report"]


def test_a_cap_after_one_member_with_no_partner_delivers_it_unconfirmed_not_nothing(tmp_path, monkeypatch):
    _hive(monkeypatch, ["print('sum: 5')", "DONE", "CAP"])
    out = solo.run(TASK, tmp_path / "b", "never", members=2)
    assert not out["agreed"] and out["report"].startswith("Not confirmed") and "Member 1: sum: 5" in out["report"]


def test_a_cap_with_no_answer_says_so(tmp_path, monkeypatch):
    _hive(monkeypatch, ["CAP"])
    out = solo.run(TASK, tmp_path / "c", "never", members=2)
    assert "No member got as far" in out["report"] and out["tries"] == 0


def test_two_members_in_before_the_cap_agree_and_are_delivered(tmp_path, monkeypatch):
    _hive(monkeypatch, ["print('sum: 5')", "DONE", "print('The sum is 5')", "DONE"])
    out = solo.run(TASK, tmp_path / "d", "never", members=2)
    assert out["agreed"] and out["tries"] == 2


def test_run_task_gives_a_grace_after_sigterm(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_CAP_GRACE", "2")
    from training import exam
    script = ("import signal, sys, time\n"
              "signal.signal(signal.SIGTERM, lambda *a: (open(sys.argv[1], 'w').write('delivered'), sys.exit(0)))\n"
              "time.sleep(60)\n")
    mark = tmp_path / "mark"
    code, _ = exam.run_task([sys.executable, "-c", script, str(mark)], 1)
    assert code is None and mark.read_text() == "delivered"
    t0 = time.time()
    code, _ = exam.run_task([sys.executable, "-c", "import signal,time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)"], 1)
    assert code is None and time.time() - t0 < 60  # one that ignores SIGTERM is killed after the grace
