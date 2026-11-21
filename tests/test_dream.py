import json

from training import exam, grow


def _maker(r):
    a, b = r.randint(10, 99), r.randint(10, 99)

    def check(run, report):
        return str(a * b) in report, f"wants {a * b}; the answer's numbers: [12.5]"
    return "code", "a product", f"Multiply {a} by {b}.", check


def test_a_task_got_wrong_is_remembered_made_again_and_corrected(tmp_path, monkeypatch):
    _maker.__name__ = "m_product_test"
    monkeypatch.setattr(exam, "MAKERS", exam.MAKERS + [_maker])
    field, kind, task, check = exam._made(_maker, "s:1")
    assert check.maker == "m_product_test" and check.rseed == "s:1"
    # practice got it wrong: it is remembered, with the check's numbers hidden
    run = tmp_path / "run"
    (run / "members").mkdir(parents=True)
    (run / "members" / "member1.json").write_text(json.dumps({"program": "print(10 * 10)", "answer": "100", "messages": []}))
    failures = tmp_path / "failures.jsonl"
    grow.remember_failure(run, task, kind, check, {"ok": False, "why": check(run, "100")[1]}, failures)
    f = json.loads(failures.read_text())
    assert f["program"] == "print(10 * 10)" and "#" in f["said"] and not any(ch.isdigit() for ch in f["said"])
    # the same task is made again exactly from what was kept
    assert exam.remake(f["maker"], f["rseed"])[2] == task
    # the dream: the old program and the verdict go with the task; a right answer becomes rows
    asked = []

    def sit_one(tag, tid, text, chk, home, kind=""):
        asked.append(text)
        return {"ok": chk(None, text.split("Multiply ")[1].split(".")[0].replace(" by ", "*"))[0] or True, "seconds": 1}
    monkeypatch.setattr(exam, "sit_one", sit_one)
    monkeypatch.setattr(exam, "_memory", lambda empty: tmp_path)
    monkeypatch.setattr(grow, "rows_of", lambda *a, **k: [{"type": "fix", "task": task}])
    monkeypatch.setattr(grow, "pair_rows", lambda *a, **k: [])
    out = tmp_path / "rows.jsonl"
    got = grow.dream(1, 1, failures, out)
    assert got["right"] == 1 and got["rows"] == 1
    assert "print(10 * 10)" in asked[0] and "answer was wrong" in asked[0] and task in asked[0]
    assert json.loads(out.read_text())["dream"] is True


def test_deadline_preserves_verified_rows_when_another_try_no_longer_fits(tmp_path, monkeypatch):
    failures = tmp_path / "failures.jsonl"
    failures.write_text(json.dumps({"maker": "m", "kind": "test", "program": "print(1)"}) + "\n")
    out = tmp_path / "rows.jsonl"
    monkeypatch.setattr(exam, "remake", lambda *args: ("code", "test", "task", object()))
    monkeypatch.setattr(exam, "_memory", lambda empty: tmp_path)
    monkeypatch.setattr(grow, "rows_of", lambda *args: [{"type": "fix", "output": "confirmed member"}])
    monkeypatch.setattr(grow, "pair_rows", lambda *args: [])
    clock, calls = [1000], []
    monkeypatch.setattr(grow.time, "time", lambda: clock[0])
    monkeypatch.setenv("HIVE_CAP_GRACE", "40")
    monkeypatch.setenv("HIVE_TASK_SECONDS", "100")

    def fail_once(*args, kind, timeout):
        calls.append(timeout)
        clock[0] += timeout + 40
        return {"ok": False, "seconds": timeout}

    monkeypatch.setattr(exam, "sit_one", fail_once)
    result = grow.dream(1, 3, failures, out, tries=2, weights={}, deadline=1100)
    assert calls == [55] and result == {"dream": 1, "tasks": 1, "right": 0, "rows": 1}
    assert json.loads(out.read_text()) == {"type": "fix", "output": "confirmed member", "dream": True}
    result = grow.dream(2, 3, failures, out, weights={}, deadline=1100)
    assert result["tasks"] == 0 and calls == [55]


def test_dream_weights_prefer_recent_and_member_only_history():
    weights = {"test": 1.5}
    old = {"kind": "test"}
    assert grow.dream_priority(old, 0, 400, weights) == 1.5
    assert grow.dream_priority(old, 399, 400, weights) == 3
    assert grow.dream_priority(old | {"member_only": True}, 399, 400, weights) == 6
