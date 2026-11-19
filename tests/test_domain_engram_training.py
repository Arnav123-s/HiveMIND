import numpy as np
import pytest

from training import domain_engram


def test_low_rank_residual_learns_two_independent_labels():
    x = np.array([[1.0, 2.0], [1.1, 1.9], [2.0, -1.0], [1.8, -1.1]])
    ids, a, b, result = domain_engram.fit(x, [5, 5, 2, 2])
    predicted = ids[np.argmax(x @ a.T @ b.T, axis=1)]
    assert list(predicted) == [5, 5, 2, 2]
    assert result["target_mse_after"] < result["target_mse_before"]
    assert a.shape == (domain_engram.RANK, 2) and b.shape == (2, domain_engram.RANK)


def test_insufficient_support_and_nonfinite_states_are_rejected():
    with pytest.raises(ValueError):
        domain_engram.fit(np.eye(3), [4, 4, 6])
    with pytest.raises(ValueError):
        domain_engram.fit(np.array([[np.nan], [1], [2], [3]]), [3, 3, 5, 5])


def test_non_disjoint_and_conflicting_prompts_are_rejected_before_loading(tmp_path):
    a = {"prompt": "Label this record.", "answer": "A"}
    args = {"model": None, "runtime": None, "threads": 1}
    with pytest.raises(ValueError, match="disjoint"):
        domain_engram.train([a], tmp_path / "x", validation=[a], **args)
    with pytest.raises(ValueError, match="conflicting"):
        domain_engram.train([a, dict(a, answer="B")], tmp_path / "x", **args)



def test_another_base_cannot_publish_a_t80_adapter(tmp_path):
    foreign = tmp_path / "unrelated.gguf"
    foreign.write_bytes(b"another model")
    with pytest.raises(ValueError, match="Ternary-Bonsai-8B"):
        domain_engram.train([{"prompt": "A?", "answer": "X"}], tmp_path / "candidate.gguf",
                            model=foreign, runtime=None)


def test_starter_index_ships_the_measured_bytes_for_qualifying_edits():
    import hashlib
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    bank = root / "cells/engrams"
    report = root / "training/reports/domain-engrams"
    proof = json.loads((report / "results.json").read_text())
    catalog = json.loads((report / "catalog.json").read_text())
    assert set(proof["domain"]) == set(catalog) and len(catalog) == 6
    assert proof["corpus_sha256"] == hashlib.sha256((report / "exercises.json").read_bytes()).hexdigest()
    assert proof["train_states_sha256"] == hashlib.sha256((report / "training-states.npz").read_bytes()).hexdigest()
    primary_names = {"e_domain_" + meta["domain"] for meta in catalog.values()}
    installed = {row["name"]: row for line in (bank / "index.jsonl").read_text().splitlines()
                 if (row := json.loads(line))["name"] in primary_names}
    qualified = set()
    for key, observation in proof["domain"].items():
        score = observation["validation"]
        assert observation["qualified"] == (score["after"] == score["count"] == 3 and score["regressions"] == 0)
        name = "e_domain_" + catalog[key]["domain"]
        weight = bank / ("t80+" + name + ".gguf")
        if observation["qualified"]:
            qualified.add(name)
            row = installed[name]
            assert row["domain"] == catalog[key]["domain"] and row["skill_id"] == catalog[key]["skill_id"]
            assert row["verified"] and row["form"] == "label"
            assert row["sha256"] == score["fit"]["sha256"] == hashlib.sha256(weight.read_bytes()).hexdigest()
        else:
            assert not weight.exists()
    assert qualified == set(installed)


def test_native_feature_helper_runs_after_tokenizer_releases_the_model(monkeypatch, tmp_path):
    import contextlib
    import io
    from pathlib import Path
    from types import SimpleNamespace

    state = {"resident": False}

    @contextlib.contextmanager
    def server(*args, **kwargs):
        assert not kwargs["features"]
        state["resident"] = True
        try:
            yield "native"
        finally:
            state["resident"] = False

    def run_helper(command, **kwargs):
        assert not state["resident"]
        assert len(Path(command[2]).read_text().splitlines()) == 4
        np.zeros((4, 4096), dtype=np.float32).tofile(command[3])
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(domain_engram, "_feature_helper", lambda runtime, path: path / "helper")
    monkeypatch.setattr(domain_engram, "_server", server)
    monkeypatch.setattr(domain_engram, "_render", lambda url, row: row["prompt"])
    monkeypatch.setattr(domain_engram.urllib.request, "urlopen", lambda url: io.BytesIO(
        b'{"data":[{"meta":{"n_embd":4096,"n_vocab":151669}}]}'))
    monkeypatch.setattr(domain_engram, "_post", lambda url, route, body: {"tokens": [2 if body["content"] == "A" else 3]})
    monkeypatch.setattr(domain_engram.subprocess, "run", run_helper)
    rows = [{"prompt": str(i), "answer": label} for i, label in enumerate(["A", "B", "A", "B"])]
    accepted, features = domain_engram._feature_rows(rows, [], tmp_path / "model", "runtime", 1)
    assert len(accepted) == 4 and features.shape == (4, 4096)


def test_corrective_weights_need_independent_native_and_serving_confirmation():
    import hashlib
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    report = root / "training/reports/domain-engrams"
    bank = root / "cells/engrams"
    installed = {r["sha256"]: r for row in (bank / "index.jsonl").read_text().splitlines()
                 if (r := json.loads(row)).get("sha256")}
    for name in ("water-v2", "timing-v2"):
        study = report / name
        native = json.loads((study / "qualification.json").read_text())
        decision = json.loads((study / "release.json").read_text())
        fit = json.loads((study / "fit.json").read_text())
        assert fit["sha256"] == decision["sha256"] == native["v2_sha256"]
        assert native["original_tokens_reproduced"] and native["v1_reactivation_reproduced"]
        assert native["qualified"] == all(r["v2"]["correct"] for r in native["cases"])
        served = study / "serving-qualification.json"
        confirmed = False
        if served.is_file():
            http = json.loads(served.read_text())
            assert http["sha256"] == fit["sha256"]
            assert [r["id"] for r in http["cases"]] == [r["id"] for r in native["cases"]]
            confirmed = all(r["correct"] and r["same_rendered_prompt"] for r in http["cases"])
        assert decision["released"] == (native["qualified"] and confirmed)
        if decision["released"]:
            row = installed[fit["sha256"]]
            weight = bank / (row["dna"] + "+" + row["name"] + ".gguf")
            assert row["verified"] and hashlib.sha256(weight.read_bytes()).hexdigest() == fit["sha256"]
        else:
            assert fit["sha256"] not in installed
