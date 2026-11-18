"""Version selection and independent qualification of explicitly specified fieldwork tasks."""
import json
from concurrent.futures import ThreadPoolExecutor

from training.experiments.fieldwork import work as fw


class Guest:
    def __init__(self, functions):
        self.functions = functions
        self.calls = []

    def run(self, source, inputs, fuel):
        self.calls.append((source, list(inputs)))
        # A generated program may have optional library definitions prepended.
        answer = self.functions[source.splitlines()[-1]]
        return [{"value": answer(value)} for value in inputs], 0, 0


def version(bank, name, text, source, passed):
    row = dict(task=name, description=text, source=source, digest=fw.fingerprint(source), public=1,
               validation=passed, parents=[])
    fw.admit(bank, row)
    return row


def order(text, public, private, jobs):
    def examples(rows):
        return [dict(input=x, output=y) for x, y in rows]
    return dict(name="transform", task=text, examples=examples(public), validation=examples(private),
                jobs=[dict(id="job" + str(i), input=x, snapshot_file="answer.json") for i, x in enumerate(jobs)])


def no_generator(*args):
    raise AssertionError("a saved version already solves this order")


def test_exact_versions_survive_helper_limit_and_validation_rejection(tmp_path):
    bank = tmp_path / "bank"
    task = order("Transform each sensor reading", [(0, 0)], [(-3, 3)], [-5])
    first = version(bank, "transform", task["task"], "identity", 20)
    second = version(bank, "transform", task["task"], "absolute", 3)
    for name in ("daily", "monthly", "other"):
        version(bank, name, task["task"], name, 90)
    g = Guest({"identity": lambda x: x, "absolute": abs})
    out = tmp_path / "work"
    receipt = fw.work(task, g, no_generator, out, bank)
    assert [row["reason"] for row in receipt["saved_checks"]] == ["validation_failed", "qualified"]
    assert receipt["saved_checks"][0]["validation_failed"] == 1
    assert receipt["digest"] == second["digest"] and receipt["parents"] == [second["digest"]]
    assert receipt["jobs"] == [{"id": "job0", "value": 5}]
    state = json.loads((out / "work-order.json").read_text())
    assert len(state["parents"]) == 2 and all(row["task"] != "transform" for row in state["parents"])
    assert [row["digest"] for row in state["versions"]] == [first["digest"], second["digest"]]
    calls = len(g.calls)
    assert fw.work(task, g, no_generator, out, bank) == receipt and len(g.calls) == calls


def test_public_counterexample_seeds_repair_and_retains_parent(tmp_path):
    bank, out = tmp_path / "bank", tmp_path / "case"
    task = order("Return an absolute magnitude", [(0, 0), (-4, 4)], [(-98765, 98765)], [-3])
    parent = version(bank, "transform", task["task"], "identity", 2)
    g = Guest({"identity": lambda x: x, "absolute": abs})
    def fix(prompt, prefix, prior):
        assert prior[0] == "identity"
        assert json.loads(prior[1]) == {"input": -4, "expected": 4, "actual": {"value": -4}}
        assert "98765" not in str((prompt, prefix, prior))
        return {"source": "absolute", "usage": {}}
    new = fw.work(task, g, fix, out, bank)
    assert new["validated"] == 1 and new["jobs"][0]["value"] == 3
    assert new["parents"] == [parent["digest"]]
    rows = {r["digest"]: r for r in fw.load_bank(bank)}
    assert rows[parent["digest"]] == parent and rows[new["digest"]]["parents"] == [parent["digest"]]


def test_private_failure_cannot_guide_generated_attempts(tmp_path):
    bank, out = tmp_path / "bank", tmp_path / "case"
    task = order("Return absolute magnitude", [(4, 4)], [(-71, 71)], [-3])
    parent = version(bank, "transform", task["task"], "identity", 2)
    g = Guest({"identity": lambda x: x, "alternate": lambda x: x})
    first = fw.work(task, g, None, out, bank)
    assert first["status"] == "needs_generation" and first["jobs"] == []
    seen = []
    def generate(prompt, prefix, prior):
        seen.append((prompt, prefix, prior))
        assert prior is None and "-71" not in str(seen) and "identity" not in str(seen)
        return {"source": "alternate", "usage": {}}
    r = fw.work(task, g, generate, out, bank, rounds=4)
    assert r["public"] == 1 and r["validated"] == 0 and r["jobs"] == [] and len(seen) == 1
    assert not (out / "job0").exists() and fw.load_bank(bank) == [parent]


def test_overlapping_checks_require_agreement_on_staged_jobs(tmp_path):
    bank = tmp_path / "bank"
    spec = order("Do it", [(1, 1)], [(2, 2)], [3, -3])
    for name in ("identity", "absolute"):
        version(bank, "transform", spec["task"], name, 1)
    g = Guest({"identity": lambda x: x, "absolute": abs})
    withheld = fw.work(spec, g, no_generator, tmp_path / "ambiguous", bank)
    assert withheld["status"] == "ambiguous_saved_versions" and withheld["digest"] is None and withheld["jobs"] == []
    assert "job1" in withheld["reason"] and any(choices in withheld["reason"] for choices in ("(-3 or 3)", "(3 or -3)"))
    assert "new output directory" in withheld["reason"]
    assert not (tmp_path / "ambiguous" / "job0").exists()
    assert not (tmp_path / "ambiguous" / "solver.py").exists()
    g.calls.clear()
    spec["jobs"].pop()
    confirmed = fw.work(spec, g, no_generator, tmp_path / "shared", bank)
    assert confirmed["jobs"] == [{"id": "job0", "value": 3}]
    assert sum(batch == [3] for _, batch in g.calls) == 2  # staged jobs are materialized without rerunning a winner
    assert json.loads((tmp_path / "shared" / "job0" / "answer.json").read_text()) == 3
    assert len(confirmed["versions_compared_on_jobs"]) == 2


def test_digest_is_immutable_and_can_qualify_for_two_contracts_concurrently(tmp_path):
    rows = [dict(task="first", description=name, source="same", digest=fw.fingerprint("same"),
                 public=1, validation=2, parents=[name]) for name in ("contract A", "contract B")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda row: fw.admit(tmp_path, row), rows))
    assert sorted(fw.load_bank(tmp_path), key=lambda row: row["description"]) == rows
    fw.admit(tmp_path, dict(rows[0], parents=["new metadata"]))
    assert sorted(fw.load_bank(tmp_path), key=lambda row: row["description"]) == rows

def test_staged_jobs_follow_their_declared_file_comparators(tmp_path):
    task = order("Write a report file", [(1, "unused")], [(2, "unused")], [])
    task["examples"] = [{"input": 1, "output": {"report.json": '{"x":1}'}}]
    task["validation"] = [{"input": 2, "output": {"report.json": '{"x":2}'}}]
    task["compare"] = {"report.json": "json"}
    bank = tmp_path / "bank"
    for name in ("compact", "spaced"):
        version(bank, "transform", task["task"], name, 2)

    def make_file(x, spaced):
        if x == 0:
            return 3  # An intermediate scalar does not use a file comparator.
        if isinstance(x, dict):
            x = x["number"]
        return {"report.json": json.dumps({"x": x}, indent=2 if spaced else None)}
    g = Guest({"compact": lambda x: make_file(x, False), "spaced": lambda x: make_file(x, True)})
    task["jobs"] = [dict(id="number", input=0, snapshot_file="amount.json"),
                    dict(id="report", input={}, from_job={"number": "number"}, files=["report.json"])]
    result = fw.work(task, g, no_generator, tmp_path / "ok", bank)
    assert len(result["jobs"]) == 2 and json.loads((tmp_path / "ok/report/report.json").read_text()) == {"x": 3}
    task["jobs"][1]["compare"] = {}  # The more specific job requests exact strings.
    assert fw.work(task, g, no_generator, tmp_path / "exact", bank)["status"] == "ambiguous_saved_versions"
    task["jobs"][1]["compare"] = {"report.json": "json"}
    g.functions["spaced"] = lambda x: {"report.json": '{"x":4}'} if isinstance(x, dict) else make_file(x, True)
    conflict = fw.work(task, g, no_generator, tmp_path / "different", bank)
    assert conflict["status"] == "ambiguous_saved_versions" and "report" in conflict["reason"]
    assert "report.json" not in conflict["reason"] and not (tmp_path / "different/number").exists()

def test_legacy_work_order_and_attempt_survive_resume(tmp_path):
    bank, out = tmp_path / "bank", tmp_path / "old-run"
    task = order("Old absolute-value recipe", [(-2, 2)], [(-4, 4)], [-3])
    parent = version(bank, "transform", task["task"], "identity", 1)
    token = fw.fingerprint(json.dumps(task, sort_keys=True, separators=(",", ":")))
    fw.save(out / "work-order.json", {"spec_digest": token, "parents": [parent]})
    fw.save(out / "attempt-1.json", dict(source="absolute", program="absolute", passed=1,
                                          feedback="All examples passed.", usage={}, seconds=0, stop="done"))
    g = Guest({"identity": lambda x: x, "absolute": abs})
    result = fw.work(task, g, no_generator, out, bank, rounds=1)
    assert result["jobs"] == [{"id": "job0", "value": 3}]
    assert result["parents"] == [parent["digest"]] and result["saved_checks"][0]["reason"] == "public_failed"


def test_cli_reports_ambiguous_job_without_a_generator(tmp_path, monkeypatch, capsys):
    bank = tmp_path / "bank"
    task = order("Choose the magnitude", [(2, 2)], [(3, 3)], [-1])
    for name in ("absolute", "identity"):
        version(bank, "transform", task["task"], name, 1)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(task))
    monkeypatch.setattr(fw, "Guest", lambda sdk: Guest({"identity": lambda x: x, "absolute": abs}))
    rc = fw.main(["--sdk", str(tmp_path), "--spec", str(spec), "--out", str(tmp_path / "run"), "--bank", str(bank)])
    output = capsys.readouterr().out
    assert rc != 0 and "0/1 jobs delivered" in output and "job0" in output and "distinguishing example" in output
    assert not (tmp_path / "run/job0").exists()
