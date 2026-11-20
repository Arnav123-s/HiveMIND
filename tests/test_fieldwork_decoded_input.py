"""Contract and provenance of the one-candidate decoded-input adapter."""

import os
from pathlib import Path

import pytest

from training.experiments.fieldwork import decoded_input_repair, repair_learning, work
from training.experiments.fieldwork.guest import Guest


@pytest.mark.parametrize("source", [
    "import json\ndef solve(x):\n    data = json.loads(x)\n    return data",
    "import json as codec\ndef solve(data):\n    data = codec.loads(data)\n    return data",
    "def solve(req):\n    from json import loads as read\n    return read(req)['weight']",
    "from json import loads\ndef solve(x):\n    return loads(x).get('list', [])[0]",
])
def test_exactly_one_guard_for_a_bound_original_entry_argument(source):
    candidate, = decoded_input_repair.variants(source)
    assert candidate["method"] == "decoded_input"
    assert candidate["before"] in source and " is dict " in candidate["after"] and " is list " in candidate["after"]
    assert not list(decoded_input_repair.variants(candidate["source"]))


@pytest.mark.parametrize("source", [
    "import json\ndef solve(x): return json.loads(x['nested'])",
    "import json\ndef solve(x): return json.loads(x, parse_int=str)",
    "import json\ndef solve(x):\n    x = '123'\n    return json.loads(x)",
    "from other import loads\ndef solve(x): return loads(x)",
    "from .json import loads\ndef solve(x): return loads(x)",
    "import json\ndef solve(x):\n    data = json.loads(x)\n    json.loads = str\n    return data",
    "import json\ndef solve(x):\n    data = json.loads(x)\n    type = int\n    return data",
    "from json import loads\ndef solve(x):\n    y = loads(x)\n    loads = str\n    return y",
    "import json\ndef solve(x):\n    if isinstance(x, str): return json.loads(x)\n    return x",
    "import json\ndef solve(x): return [json.loads(x) for x in x]",
])
def test_ambiguous_bindings_decline_without_a_candidate(source):
    assert not list(decoded_input_repair.variants(source))


def test_decoded_input_spends_one_public_evaluation_in_the_shared_limit():
    source = "import json\ndef solve(x): return json.loads(x).get('days', [])"
    seen = []

    def score(candidate, examples):
        seen.append(candidate)
        return len(examples)

    examples = [{"input": {"days": [3]}, "output": [3]}]
    assert repair_learning.select(source, examples, score, limit=0, original_passed=0) is None
    assert not seen
    receipt = repair_learning.select(source, examples, score, limit=1, original_passed=0)
    assert len(seen) == receipt["tried"] == 1 and receipt["method"] == "decoded_input"


@pytest.fixture(scope="module")
def wasi():
    sdk = os.environ.get("HIVE_FIELDWORK_WASI")
    if not sdk:
        pytest.skip("set HIVE_FIELDWORK_WASI to run the real WebAssembly guest")
    pytest.importorskip("wasmtime")
    return Guest(Path(sdk))


def test_real_wasi_guard_accepts_only_decoded_containers_and_keeps_string_parsing(wasi):
    original = "import json\ndef solve(x):\n    y = json.loads(x)\n    return y"
    candidate, = decoded_input_repair.variants(original)
    values = [{"n": 4}, [7], '{"n":4}', '[7]', 'invalid', 23, None]
    baseline, _, _ = wasi.run(original, values, fuel=5_000_000_000)
    fixed, _, _ = wasi.run(candidate["source"], values, fuel=5_000_000_000)
    assert all("error" in item for item in baseline[:2])
    assert fixed[:2] == [{"value": {"n": 4}}, {"value": [7]}]
    assert fixed[2:] == baseline[2:] and all("error" in item for item in fixed[4:])


@pytest.mark.parametrize(("learn", "expected"), [(True, 4), (False, 4), (True, 88)])
def test_real_work_distinguishes_handwritten_repair_and_requires_independent_success(tmp_path, wasi, learn, expected):
    source = "import json\ndef solve(x): return json.loads(x)['n']"
    spec = dict(name="measurement", task="Read n from the measured object",
                examples=[dict(input={"n": 2}, output=2)], validation=[dict(input={"n": 4}, output=expected)],
                jobs=[dict(id="fresh", input={"n": 8})])
    bank = tmp_path / "bank"
    def writer(*args):
        return {"source": source, "usage": {}}
    receipt = work.work(spec, wasi, writer, tmp_path / "run", bank, rounds=1, repair_budget=1, learn_repairs=learn)
    assert receipt["repair_search"]["candidates_checked"] == receipt["decoded_input_repair"]["tried"] == 1
    assert not any(key in receipt for key in ("learned_repair", "arithmetic_repair", "repair_experience"))
    if expected == 4:
        row, = work.load_bank(bank)
        assert row["decoded_input_repair"] == receipt["decoded_input_repair"]
        assert receipt["jobs"] == [{"id": "fresh", "value": 8}]
    else:
        assert not receipt["jobs"] and not work.load_bank(bank)
