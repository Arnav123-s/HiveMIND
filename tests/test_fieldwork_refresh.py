"""Exercise failure recovery through the ordinary work-order and artifact publication paths."""
import errno
import json
import multiprocessing
import os

import pytest

from test_fieldwork_versions import Guest, no_generator, order, version
from training.experiments.fieldwork import repair_learning, work as fw


def test_new_exact_version_refreshes_challenge_with_the_same_bank_snapshot(tmp_path):
    source = "def solve(amounts): return len(amounts)"
    task = order("Count amounts", [([1], 1)], [([1, 1], 2)], [[2, 3]])
    out, bank = tmp_path / "old", tmp_path / "bank"
    class CountGuest:
        def run(self, program, inputs, fuel):
            op = sum if "sum(amounts)" in program else len
            return [{"value": op(xs)} for xs in inputs], 0, 0
    g = CountGuest()
    assert fw.work(task, g, None, out, bank, challenge_budget=1)["status"] == "needs_generation"
    version(bank, task["name"], task["task"], source, 2)
    for name in ["orders", "events"]:
        before = f"def solve({name}): return len({name})"
        after = before.replace("len(", "sum(")
        rule = repair_learning.discover(before, after)
        fw.admit(bank, dict(task=name, description="Sum the " + name, source=after, digest=fw.fingerprint(after),
                            validation=4, repair_experience=[dict(parent=fw.fingerprint(before), rule=rule,
                                                                  validation_set=fw.fingerprint(name))]))
    for where in [out, tmp_path / "new"]:
        r = fw.work(task, g, no_generator, where, bank, challenge_budget=1)
        assert r["status"] == "challenge_ambiguous" and r["challenge"]["witness"]["answers"] == [2, 5]
        assert not r["jobs"] and not (where / "job0").exists()


def test_new_exact_version_replaces_failed_draft_with_history_and_no_new_writer(tmp_path):
    task = order("Double the amount", [(2, 4)], [(3, 6)], [5])
    out, bank = tmp_path / "run", tmp_path / "bank"
    g = Guest({"wrong": lambda x: 0, "double": lambda x: 2 * x})
    failed = fw.work(task, g, lambda *args: dict(source="wrong", usage={"tokens": 3}), out, bank,
                     rounds=1, repair_budget=0, learn_repairs=False)
    assert failed["status"] == "public_failed"
    version(bank, "transform", "Other policy", "double", 2)
    assert fw.work(task, g, no_generator, out, bank) == failed
    exact = version(bank, "transform", task["task"], "double", 2)
    r = fw.work(task, g, no_generator, out, bank)
    assert r["parents"] == [exact["digest"]] and r["jobs"] == [{"id": "job0", "value": 10}]
    assert r["attempts"][:-1] == failed["attempts"] and r["attempts"][-1]["stop"] == "verified_reuse"
    assert r["prior_searches"] == [failed["repair_search"]]
    calls = len(g.calls)
    assert fw.work(task, g, no_generator, out, bank) == r and len(g.calls) == calls


@pytest.mark.parametrize("legacy", [False, True])
def test_publication_retries_only_unfinished_work_and_never_overwrites_foreign_files(tmp_path, monkeypatch, legacy):
    task = order("Add the carried subtotal", [({"n": 1}, 1)], [({"n": 2}, 2)], [])
    task["jobs"] = [dict(id="first", input={"n": 5}, snapshot_file="answer.json"),
                    dict(id="second", input={"n": 7}, from_job={"subtotal": "first"}, snapshot_file="answer.json")]
    out, bank = tmp_path / "work", tmp_path / "bank"
    g = Guest({"total": lambda x: sum(x.values())})
    with monkeypatch.context() as m:
        def disk_full(*args):
            raise OSError(errno.ENOSPC, "No space left on device")
        m.setattr(fw, "commit_output", disk_full)
        r = fw.work(task, g, lambda *args: dict(source="total", usage={}), out, bank)
    assert r["status"] == "delivery_failed" and not fw.load_bank(bank)
    assert r["jobs"][0]["pending_value"] == 5 and r["jobs"][1]["retry_delivery"]
    if legacy:
        r["jobs"][0].pop("pending_value")
        r["jobs"][1] = {"id": "second", "error": "snapshot dependency unavailable or input field already set"}
        (out / "receipt.json").write_text(json.dumps(r))
    (out / "first").mkdir()
    foreign = out / "first/answer.json"
    foreign.write_text("user-owned contents")
    conflict = fw.work(task, g, no_generator, out, bank)
    assert conflict["status"] == "delivery_failed" and foreign.read_text() == "user-owned contents"
    assert not (out / "second").exists() and not fw.load_bank(bank)
    foreign.unlink()
    fixed = fw.work(task, g, no_generator, out, bank)
    assert fixed["jobs"] == [{"id": "first", "value": 5}, {"id": "second", "value": 12}]
    assert "status" not in fixed and fixed["attempts"] == r["attempts"]
    assert json.loads((out / "second/answer.json").read_text()) == 12 and len(fw.load_bank(bank)) == 1
    assert sum(inputs == [{"n": 5}] for _, inputs in g.calls) == (2 if legacy else 1)
    assert sum(inputs == [{"n": 7, "subtotal": 5}] for _, inputs in g.calls) == 1
    calls = len(g.calls)
    assert fw.work(task, g, no_generator, out, bank) == fixed and len(g.calls) == calls


def test_guest_failure_is_permanent_and_does_not_spend_any_budget_on_resume(tmp_path):
    task = order("Double", [(1, 2)], [(2, 4)], [-12])
    class BrokenGuest:
        calls = 0
        def run(self, program, inputs, fuel):
            self.calls += 1
            return [{"error": "OSError: [Errno 28] guest failure"} if x < 0 else {"value": 2*x} for x in inputs], 0, 0
    g, out = BrokenGuest(), tmp_path / "out"
    r = fw.work(task, g, lambda *args: dict(source="double", usage={}), out)
    assert r["status"] == "delivery_failed"
    calls = g.calls
    assert fw.work(task, g, no_generator, out) == r and g.calls == calls


def abandon_manifest(directory, task):
    def die_before_publish(*args):
        os._exit(75)
    os.replace = die_before_publish
    fw.work(task, None, None, directory)


def test_interrupted_first_manifest_recovers_only_the_owned_staging_file(tmp_path):
    task = order("Double", [(1, 2)], [(2, 4)], [4])
    out = tmp_path / "interrupted"
    child = multiprocessing.get_context("spawn").Process(target=abandon_manifest, args=(out, task))
    child.start()
    child.join(15)
    assert child.exitcode == 75
    pending, = out.glob(".work-order-*.pending")
    assert not (out / "work-order.json").exists()
    other = out / "tmp-user"
    other.write_text("keep")
    with pytest.raises(FileExistsError, match="fresh"):
        fw.work(task, None, None, out)
    assert other.read_text() == "keep" and pending.exists()
    other.unlink()
    fresh = tmp_path / "foreign"
    fresh.mkdir()
    (fresh / pending.name).write_text("user content")
    with pytest.raises(FileExistsError, match="occupied"):
        fw.work(task, None, None, fresh)
    assert (fresh / pending.name).read_text() == "user content"
    r = fw.work(task, None, None, out)
    assert r["status"] == "needs_generation" and (out / "work-order.json").is_file() and not pending.exists()


def test_batch_rechecks_new_exact_version_even_when_old_job_had_no_repair_search(tmp_path):
    first = order("Double the amount", [(2, 4)], [], [5])
    second = order("Double the amount", [(3, 6)], [(4, 8)], [6])
    drafts = iter(["wrong", "double"])
    g = Guest({"wrong": lambda x: 0, "double": lambda x: 2*x})
    results = fw.run_orders([first, second], g, lambda *args: dict(source=next(drafts), usage={}),
                            tmp_path / "orders", tmp_path / "bank", rounds=1, repair_budget=0)
    assert "prior_searches" not in results[0]
    assert results[0]["attempts"][0]["source"] == "wrong" and results[0]["attempts"][-1]["stop"] == "verified_reuse"
    assert [r["jobs"][0]["value"] for r in results] == [10, 12]
