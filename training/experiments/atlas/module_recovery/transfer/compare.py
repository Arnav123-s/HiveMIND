"""Replay versioned duration programs in WASI and score deliveries after selection."""
import argparse
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import random
import sys
import zipfile

HERE = Path(__file__).resolve().parent
RECOVERY = HERE.parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))

from training.experiments.atlas.module_recovery import holdout, recover
from training.experiments.fieldwork.guest import Guest
from training.kinds.h_module import h_module


A, B = "h20000523_03", "h20000527_03"
G50 = "h20000502_00"
G50_ARCHIVE = 14527107867
VERSIONS = {A: "83af6f54adb6aef8b4c56bd1738c394e7db591d2f8ac5eb567cb58d7c815b425",
            B: "ee6373e9af74950603cf5c4b9a2520d3c02a55758f5fa06196eba16e5ec21a53"}
PANEL_HASH = "6e291b80905ade19abe555cbc873af5cae7e6b392b7f69564850f37e304c6e77"
KEY_HASH = "9c66e47e415b9d4b3931e777399090a778f51e0ec3ad6083e6186440fc4e4715"
ARMS = {"empty": (), "version_A": (A,), "version_B": (B,), "both_agree": (A, B), "handwritten": ("reference",)}
REFERENCE = """def to_seconds(text):
    quantity = total = 0
    for c in text:
        if c.isdecimal():
            quantity = 10 * quantity + int(c)
        else:
            total += quantity * {'h': 3600, 'm': 60, 's': 1}[c]
            quantity = 0
    return total

def to_text(n):
    values = (n // 3600, n // 60 % 60, n % 60)
    return ''.join(str(v) + suffix for v, suffix in zip(values, 'hms') if v) or '0s'
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def loaded(path, required=None):
    data = path.read_bytes()
    if required and digest(data) != required:
        raise ValueError(f"Digest mismatch in {path.name}")
    return json.loads(data)


def extract_g50(path):
    manifest = loaded(RECOVERY.parent / "pulse/artifacts.json")
    manifest_row = next(i for i in manifest if i["id"] == G50_ARCHIVE)
    if digest(path.read_bytes()) != manifest_row["sha256"]:
        raise ValueError("Unexpected G50 archive bytes")
    base = "exam_20000502_mixed/" + G50
    with zipfile.ZipFile(path) as z:
        files = {k: z.read(base + "/" + k) for k in ("exam.json", "REPORT.md", "members/TASK.md")}
        durations = [n for n in z.namelist() if n.startswith(base + "/") and n.endswith("/durations.py")]
    return {"artifact_id": G50_ARCHIVE, "artifact_sha256": manifest_row["sha256"],
            "entry_sha256": {k: digest(b) for k, b in files.items()}, "duration_files": durations,
            "verdict": json.loads(files["exam.json"]), "report": files["REPORT.md"].decode(),
            "prompt": files["members/TASK.md"].decode().strip()}


def versions():
    history = loaded(RECOVERY / "results.json")["rows"]
    sources = {"reference": REFERENCE}
    for name, sha in VERSIONS.items():
        row = next(r for r in history if r["id"] == name and r["generation"] == "g52")
        src = (RECOVERY / "g52" / name / "durations.py").read_bytes()
        if digest(src) != sha or row["receipt"]["sha256"] != sha or not row["recovered"]:
            raise ValueError(f"Unrecognized retained version {name}")
        sources[name] = src.decode()
    return sources


def calls(prompt):
    match = recover.REQUEST.fullmatch(prompt)
    if match and recover.INPUT.fullmatch(match[1]):
        return [("to_seconds", match[1]), ("to_text", int(match[2]))]
    return []


def official_tests(task_id, prompt):
    # Same prompt and pseudorandom method used by the public original h_module grader.
    event, ordinal = task_id[1:].split("_")
    for attempt in range(8):
        _, _, task, check = h_module(random.Random(f"{event}:h_module:{int(ordinal)}:{attempt}"))
        if task == prompt:
            break
    else:
        raise ValueError("Could not regenerate original prompt")
    info = inspect.getclosurevars(check).nonlocals
    rng = random.Random(f"hidden:{info['seed']}")
    rows = [(name, a[0], ref(*a)) for name, _, ref, draw in info["fns"]
            for a in (draw(rng) for _ in range(25))]
    return rows, info["want"]


def generate(requests, sdk, out):
    sources = versions()
    runner = Guest(sdk)
    requested = {r["id"]: calls(r["request"]) for r in requests}
    issued, receipts = {}, {}
    for arm, eligible in ARMS.items():
        batch = [op for pair in requested.values() for op in pair]
        observed = {}
        for version in eligible:
            answers, fuel, _ = recover.execute(runner, sources[version], batch)
            if len(answers) != len(batch):
                raise ValueError("Guest produced wrong number of outputs")
            observed[version] = answers
            receipts[f"{arm}/{version}"] = {"operations": len(batch), "fuel": fuel,
                                             "source_sha256": digest(sources[version].encode())}
        offset = 0
        outcomes = {}
        for ident, ops in requested.items():
            if not ops or not eligible:
                outcomes[ident] = {"status": "deferred"}
                continue
            outputs = [observed[v][offset:offset + len(ops)] for v in eligible]
            offset += len(ops)
            if any(len(a) != 2 or type(a[0]) is not int or type(a[1]) is not str for a in outputs):
                outcomes[ident] = {"status": "invalid_output"}
                continue
            if any(a != outputs[0] for a in outputs[1:]):
                outcomes[ident] = {"status": "disputed"}
                continue
            chosen = eligible[0]
            folder = out / arm / ident
            folder.mkdir(parents=True)
            (folder / "durations.py").write_text(sources[chosen])
            (folder / "REPORT.md").write_text("\n".join(map(str, outputs[0])) + "\n")
            outcomes[ident] = {"status": "delivered", "version": chosen, "answers": outputs[0],
                               "source_sha256": digest((folder / "durations.py").read_bytes())}
        issued[arm] = outcomes
    result = {"outcomes": issued, "calls": receipts}
    (out / "ungraded.json").write_text(json.dumps(result, indent=2) + "\n")
    return result, runner


def measure(out, sdk):
    requests = loaded(HERE / "requests.json", PANEL_HASH)
    archived = loaded(HERE / "g50-original.json")
    history = loaded(RECOVERY / "archive.json")
    matched = {r["id"]: r["prompt"] for r in history if "prompt" in r}
    assert matched[G50] == archived["prompt"]
    assert not {r["request"] for r in requests}.intersection(matched.values())
    orders = [*requests, {"id": G50, "request": matched[G50]}]
    issued, runner = generate(orders, sdk, out)

    keys = loaded(HERE / "keys.json", KEY_HASH)
    old_checks, expected = official_tests(G50, matched[G50])
    positive = {q["id"] for q in requests if keys[q["id"]]["scope"] == "deliver"}
    fresh_count, historical = {}, {}
    for arm, results in issued["outcomes"].items():
        score = Counter()
        for ident, key in keys.items():
            row = results[ident]
            if ident in positive:
                if row["status"] == "delivered" and row["answers"] == key["answers"]:
                    score["correct_complete"] += 1
                elif row["status"] == "delivered":
                    score["wrong_release"] += 1
                else:
                    score["missed"] += 1
            else:
                score["outside_withheld" if row["status"] == "deferred" else "outside_activation"] += 1
        fresh_count[arm] = dict(score)
        delivery = results[G50]
        historical[arm] = {"status": delivery["status"]}
        if delivery["status"] == "delivered":
            folder = out / arm / G50
            source = (folder / "durations.py").read_text()
            answers, fuel, _ = recover.execute(runner, source, [(n, v) for n, v, _ in old_checks])
            official = sum(type(answer) is type(row[2]) and answer == row[2]
                           for answer, row in zip(answers, old_checks, strict=True))
            report = (folder / "REPORT.md").read_text()
            historical[arm].update(passed=official, total=len(old_checks), fuel=fuel,
                                   report=report, report_matches=(report == "\n".join(map(str, expected)) + "\n"))
    new_inputs = {op for q in requests if q["id"] in positive for op in calls(q["request"])}
    study_sets = {"admission": recover.contract_cases(), "previous_sixty": holdout.cases()}
    for ident, prompt in matched.items():
        study_sets[ident] = official_tests(ident, prompt)[0]
    repeated = {k: sorted(new_inputs.intersection((fn, value) for fn, value, _ in rows))
                for k, rows in study_sets.items()}
    return {"fresh_case_counts": fresh_count, "g50_replay": historical, "g50_original": archived["verdict"],
            "fresh_positive_operations": len(new_inputs), "overlap_with_previous_checks": repeated,
            "native_model_calls": 0, "wasm_sha256": digest((sdk / "python.wasm").read_bytes()),
            "ungraded_sha256": digest((out / "ungraded.json").read_bytes()), "source_sha256": digest(Path(__file__).read_bytes()),
            "requests_sha256": PANEL_HASH, "keys_sha256": KEY_HASH, **issued}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="a new output directory")
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--extract-original", type=Path, help="only extract the digest-pinned G50 ZIP to this output")
    args = parser.parse_args()
    if args.extract_original:
        args.out.write_text(json.dumps(extract_g50(args.extract_original), indent=2) + "\n")
    elif args.sdk:
        args.out.mkdir(parents=True, exist_ok=False)
        result = measure(args.out, args.sdk)
        (args.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    else:
        parser.error("--sdk or --extract-original is required")
