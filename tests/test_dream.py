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
