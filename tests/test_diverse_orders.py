import json

import pytest

from team import module_witness, solo
from training.experiments.astra_orders import prepare


ORDERS = json.loads((prepare.HERE / "inputs.json").read_text())["orders"]
DATE = "2026-11-21 (Saturday)"
TASK = """Save desk.py.
The complete required behavior is one run of the checks below, in order, on a fresh module.
Required checks:
```python
assert flip(0) == 1
assert flip(1) == 0
```
Print ready."""


def test_prompt_contents_and_seat_overrides(monkeypatch):
    monkeypatch.setattr(solo.time, "strftime", lambda *_: DATE)
    monkeypatch.setattr(solo, "solved", lambda: [{"checked": False, "task": "schedule packets"},
                                                 {"checked": True, "task": "store red apples"}])
    assert not solo.familiar("schedule packets") and solo.familiar("store red apples")
    assert solo.orders("t80") == ORDERS["full"] and solo.orders("t80+learned") == ORDERS["short"]
    request = "Schedule packets"
    assert "Today is" not in solo.modular_orders(request) and "Use requests" not in solo.modular_orders(request)
    assert solo.modular_orders("Find today's date on this web page") == ORDERS["full"]
    assert "Today is" in solo.modular_orders("Which tasks fall on Thursdays?")
    assert "Use requests" in solo.modular_orders("Perform an HTTP GET")
    monkeypatch.setenv("HIVE_DIVERSE_ORDERS", "1")
    assert solo.member_orders(request, 1, "t80", ()) == ORDERS["short"]
    assert solo.member_orders(request, 2, "t80+trained", ()) == solo.modular_orders(request)
    assert solo.member_orders(request, 3, "t80", ()) == ORDERS["full"]
    assert solo.member_orders("store red apples", 2, "t80+trained", ()) == ORDERS["short"]
    assert solo.member_orders(request, 2, "t80+trained", ("engram",)) == ORDERS["short"]
    monkeypatch.setenv("HIVE_FULL_ORDERS", "1")
    assert solo.member_orders(request, 2, "t80+trained", ()) == ORDERS["full"]
    monkeypatch.setenv("HIVE_SHORT_ORDERS", "1")
    assert solo.member_orders(request, 2, "t80", ()) == ORDERS["short"]


def test_second_member_gets_its_orders_and_the_third_gets_only_the_witness(tmp_path, monkeypatch):
    class Seen(Exception):
        pass
    class Board:
        module_witness = "flip(1)"
    def capture(who, messages, **kwargs):
        raise Seen(messages)
    monkeypatch.setenv("HIVE_DIVERSE_ORDERS", "1")
    monkeypatch.setattr(solo, "familiar", lambda _: False)
    monkeypatch.setattr(solo.ternary, "chat", capture)
    for n in (2, 3):
        with pytest.raises(Seen) as seen:
            solo.member("compute", n, Board(), None, tmp_path, .7, "t80+trained", ())
        system, task = seen.value.args[0]
        assert system["content"] == (solo.modular_orders("compute") if n == 2 else solo.orders("t80+trained"))
        assert ("flip(1)" in task["content"]) == (n == 3)


def test_unlabelled_permutations_preserve_domain_and_shrink_only_when_allowed(monkeypatch):
    monkeypatch.setattr(module_witness.saved, "guest", lambda: None)
    prompt = ("The list of rows may be in any order. work(rows) returns a count. "
              "Compute for these rows: [[1, 2], [3, 4], [5, 6]].")
    probe = module_witness.Probe(prompt, "desk.py")
    assert len(probe.calls) == 6 and {len(a[0]) for _, a in probe.calls} == {3}
    probe = module_witness.Probe("Any nonempty subset of the rows is valid. " + prompt, "desk.py")
    assert probe.witness({"observed":["a"] * len(probe.calls)}, {"observed":["b"] * len(probe.calls)}) == "work([[1, 2]])"
    assert not probe.complete and probe.inspect(".", None) == {"checked":False,"observed":[]}
    assert module_witness.list_calls(prompt.replace("any order", "input order")) == []
    assert module_witness.list_calls(prompt.replace("[[1, 2], [3, 4], [5, 6]]", "[side_effect()]")) == []


def test_effect_on_normal_agreement_and_no_blind_matches(tmp_path, monkeypatch):
    class Returns:
        def run(self, program, cases):
            # A controlled guest stub for the end-to-end _run test. Real WASI is exercised by controls.py.
            return ([{"value": 0 if "always_zero" in program else 1 - args[0]} for _, args in cases], 0, 0)
    monkeypatch.setattr(module_witness.saved, "guest", lambda: Returns())
    monkeypatch.setattr(solo, "keep", lambda *args: None)
    monkeypatch.setenv("HIVE_DIFF_EQUIV", "1")
    seen = []
    def member(task, n, board, guard, work, *args):
        seen.append(getattr(board, "module_witness", None))
        work.mkdir(exist_ok=True)
        (work / "desk.py").write_text(("def flip(always_zero): return 0" if n == 1
                                       else f"def flip(arg{n}): return 1 - arg{n}"))
        return {"answer":"ready", "who":"cell", "program":"examined", "turns":1}
    monkeypatch.setattr(solo, "member", member)
    out = solo.run(TASK, tmp_path / "exhaustive")
    assert out["agreed"] and seen == [None, None, "flip(0)"]
    assert json.loads((tmp_path / "exhaustive/members.json").read_text())["agreeing"] == [2, 3]
    broad = TASK.replace("The complete required behavior is one run of the checks below, in order, on a fresh module.", "More inputs are valid.")
    assert not solo.run(broad, tmp_path / "broad")["agreed"]
    assert solo.run(broad, tmp_path / "single", members=1)["report"].startswith("Not confirmed")
    monkeypatch.setenv("HIVE_DIFF_EQUIV", "0")
    assert solo.run(broad, tmp_path / "stock")["agreed"]


def test_matched_files_with_one_empty_worker_cannot_witness_a_diverse_release(tmp_path):
    row = {"answer": "1", "work": str(tmp_path), "diverse_orders": True}
    (tmp_path / "x.json").write_text("[2]")
    assert not solo.together(row, dict(row, answer=""), "Create x.json.")
    assert not solo.together(row, dict(row, delivery={"issues": {"x.json": "stale file"}}), "Create x.json.")


def test_checked_index_projection_rotation_and_local_memory(tmp_path, monkeypatch):
    from team import familiarity
    rows, index = tmp_path / "training", tmp_path / "index"
    rows.write_text('\n'.join(json.dumps(x) for x in [
        {"type":"first", "task":"gather green apples", "output":"SECRET"},
        {"type":"first", "task":"gather green apples", "output":"SECRET2"},
        {"type":"first", "task":"ignore this content", "checked":False},
        {"type":"repair", "task":"another private prompt"}]))
    assert familiarity.build(rows, index) == 1
    assert "SECRET" not in index.read_text() and json.loads(index.read_text())["tasks"] == ["gather green apples"]
    monkeypatch.setenv("HIVE_FAMILIAR_TASKS", str(index))
    monkeypatch.setattr(solo, "solved", lambda: [{"task":"count staple removers", "checked":True}])
    assert solo.familiar("gather green apples") and solo.familiar("count staple removers")
    first = familiarity.indexed_tasks()
    assert first is familiarity.indexed_tasks()
    rows.write_text('{"type":"first","task":"count ten giraffes"}')
    updated = tmp_path / "new"
    familiarity.build(rows, updated)
    updated.replace(index)
    assert not solo.familiar("gather green apples") and solo.familiar("count ten giraffes")
    with pytest.raises(ValueError, match="digest"):
        familiarity.build(rows, index, expected="0" * 64)
    index.unlink()
    with pytest.raises(FileNotFoundError):
        solo.familiar("count ten giraffes")


def test_heading_repair_cannot_reuse_a_check_for_the_old_file(tmp_path, monkeypatch):
    class Returns:
        def run(self, program, cases):
            values = [100 for _ in cases] if "invalid_replacement" in program else [1 - a[0] for _, a in cases]
            return [{"value": value} for value in values], 0, 0
    monkeypatch.setenv("HIVE_DIFF_EQUIV", "1")
    monkeypatch.setattr(module_witness.saved, "guest", lambda: Returns())
    monkeypatch.setattr(solo, "keep", lambda *args: None)
    monkeypatch.setattr(solo, "whole", lambda task, answer: answer == "ready")
    def worker(task, n, board, guard, work, *args):
        work.mkdir(exist_ok=True)
        (work / "desk.py").write_text("def flip(z): return 1-z")
        return {"answer":"partial", "who":"cell", "program":"examined", "turns":1}
    def edit(task, row, n, board, guard):
        from pathlib import Path
        work = Path(row["work"]) / "repair"
        work.mkdir(exist_ok=True)
        (work / "desk.py").write_text("def flip(invalid_replacement): return 100")
        row.update(work=str(work), delivery=solo.deliverables.inspect(task, work, ["desk.py"]), answer="ready", asked=True)
    monkeypatch.setattr(solo, "member", worker)
    monkeypatch.setattr(solo, "headings", edit)
    assert not solo.run(TASK, tmp_path / "attempt")["agreed"]
