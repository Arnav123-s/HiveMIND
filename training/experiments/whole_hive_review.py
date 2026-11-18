"""Recount the current generation ledger or exercise the ordinary local talk path."""

import argparse
import ast
import csv
import itertools
import json
import math
import random
import socket
import subprocess
from fractions import Fraction
from pathlib import Path

from training import kinds


ROOT = Path(__file__).resolve().parents[2]
FILE_TASK = (
    "A rain gauge recorded 7 mm on Monday, 11 mm on Tuesday, and 3 mm on Wednesday. "
    "Create a CSV file named rainfall.csv with columns day,mm and rows in the order Wednesday, Monday, Tuesday. "
    "Tell me the total rainfall in millimetres."
)
EXPECTED_CSV = [["day", "mm"], ["Wednesday", "3"], ["Monday", "7"], ["Tuesday", "11"]]
CONVERSATION = (
    "My field notebook is called Copper. Please acknowledge in one short sentence.",
    "I renamed it Juniper. Please acknowledge in one short sentence.",
    "What is my field notebook called now? Reply with just its name.",
)
CODE_TASK = (
    "Write and save a Python module gauge.py with a function exposure(points, ceiling, max_gap). "
    "Points are [minute, reading] pairs in strictly increasing time order. Readings are numbers or None. "
    "Between adjacent readings the signal changes linearly. Skip a segment if either reading is None or "
    "if its duration exceeds max_gap. Return a two-item list: total minutes strictly above ceiling "
    "(fractional minutes count), and the number of eligible segments that start at or below ceiling and "
    "end above it. A missing observation or a long gap cannot bridge two segments. Use the standard library."
)
EVIDENCE = ROOT / "training/reports/whole-hive-g47/observations.json"
REVISION_CASE = ([[0, 6], [4, 7]], 3, 4)


def recount():
    registry = {}
    for module in kinds.HARD_KINDS:
        label = kinds.sample(module.KIND)[1]
        if label in registry or not (module.HELD_OUT or module.KIND in kinds.SOLVERS):
            raise ValueError(f"Ambiguous or unclassified hard label: {label}")
        registry[label] = module.HELD_OUT
    records = (ROOT / "training/reports/generations.jsonl").read_text().splitlines()
    results = {}
    for line in records:
        record = json.loads(line)
        if record["generation"] not in ("g44", "g45", "g47"):
            continue
        arms = {}
        for name in ("before", "after"):
            arm = record["arms"][name]
            counts = {}
            for group, held in (("taught", False), ("held_out", True)):
                rows = [v for label, v in arm["kinds"].items() if registry.get(label) is held]
                counts[group] = dict(
                    correct=sum(v[0] for v in rows), cases=sum(v[1] for v in rows),
                    families_sampled=len(rows), families_with_any_pass=sum(v[0] > 0 for v in rows),
                )
            hard = arm["hard"]
            if [sum(g[k] for g in counts.values()) for k in ("correct", "cases")] != hard:
                raise ValueError(f"Subgroups do not account for the hard score: {record['generation']} {name}")
            arms[name] = counts
        results[record["generation"]] = arms
    if set(results) != {"g44", "g45", "g47"}:
        raise ValueError("This audit requires the recorded g44, g45 and g47 generations")
    missing = [m.KIND for m in kinds.HARD_KINDS if not kinds.written(m.KIND)]
    return dict(hard_families=len(registry), omitted_by_written=missing, generations=results)


def file_evidence(job):
    files = {}
    for path in sorted(job.rglob("rainfall.csv")):
        with path.open(newline="") as stream:
            files[str(path.relative_to(job))] = list(csv.reader(stream))
    return files


def schema_eligible(files):
    """Only use the requested columns, without seeing the expected rain values."""
    return [
        name for name, rows in files.items()
        if name.startswith("members/") and rows and rows[0] == ["day", "mm"]
        and len(rows) > 1 and all(len(row) == 2 for row in rows[1:])
    ]


def gauge_cases():
    inputs = [
        ([], 3, 8), ([[5, 9]], 3, 8), ([[0, 3], [8, 3]], 3, 8),
        ([[0, 3], [9, 12]], 3, 9), ([[0, 7], [8, -1]], 3, 8),
        ([[0, 0], [4, None], [8, 9]], 3, 8), ([[0, 4], [11, 5]], 3, 10),
        ([[0, 2], [3, 4], [7, 3], [10, 3], [12, 9]], 3, 4),
    ]
    rng = random.Random(55417)
    for _ in range(32):
        minute, points = 0, []
        for _ in range(rng.randint(4, 15)):
            minute += rng.randint(1, 8)
            points.append([minute, rng.choice([None, -4, -1, 0, 2, 3, 6, 9])])
        inputs.append((points, rng.randint(-2, 4), rng.randint(2, 9)))
    return inputs


def reference(points, ceiling, max_gap):
    minutes, count = Fraction(0), 0
    ceiling = Fraction(ceiling)
    for (start, a), (end, b) in zip(points, points[1:]):
        if a is None or b is None or end - start > max_gap:
            continue
        a, b = Fraction(a), Fraction(b)
        count += a <= ceiling < b
        cuts = [Fraction(0), Fraction(1)]
        if min(a, b) < ceiling < max(a, b):
            cuts.insert(1, (ceiling - a) / (b - a))
        for left, right in zip(cuts, cuts[1:]):
            if a + (b - a) * (left + right) / 2 > ceiling:
                minutes += (Fraction(end) - Fraction(start)) * (right - left)
    return [float(minutes), count]


def confirmation_cases():
    """Separate correlated readings, including plateaus and negative timestamps."""
    rng = random.Random(928703)
    inputs = []
    for _ in range(96):
        minute, reading = rng.randint(-30, 0), rng.randint(-8, 8)
        ceiling, gap = rng.randint(-5, 5), rng.randint(2, 16)
        points = []
        for _ in range(rng.randint(2, 22)):
            minute += rng.randint(1, 12)
            reading += rng.choice([-6, -2, 0, 0, 1, 4])
            points.append([minute, None if rng.randrange(8) == 0 else reading])
        inputs.append((points, ceiling, gap))
    return inputs


def fractional_cases():
    """Two segments with every combination of missing, below, equal and above."""
    inputs = []
    for first, second in ((0.75, 2.25), (3.75, 1.5)):
        for gap in (1.5, 4.5):
            for a, b, c in itertools.product((None, -2.5, 0.5, 4.5), repeat=3):
                inputs.append(([[0, a], [first, b], [first + second, c]], 0.5, gap))
    return inputs


def coding_suites():
    return dict(original=gauge_cases(), confirmation=confirmation_cases(), fractional=fractional_cases())


def grade_module(source, guest, inputs=None):
    if inputs is None:
        inputs = gauge_cases()
    observed, _, _ = guest.run(source + "\ndef solve(x): return exposure(*x)\n", inputs)
    passes = []
    for row, sample in zip(observed, inputs, strict=True):
        answer = reference(*sample)
        value = row.get("value")
        passes.append(
            isinstance(value, list) and len(value) == 2 and type(value[0]) in (int, float)
            and math.isclose(value[0], answer[0], rel_tol=1e-8, abs_tol=1e-8)
            and type(value[1]) is int and value[1] == answer[1]
        )
    return passes


def revision_trial(evidence, out, sdk):
    """Ask the author of the best draft twice, independently, with one example in the second prompt."""
    from team import ternary
    from team.tools.source import extract_code
    from training.experiments.fieldwork.guest import Guest

    out.mkdir(parents=True, exist_ok=False)
    frozen = json.loads(evidence.read_text())["live_coding"]
    draft_path = "members/member3/gauge.py"
    source = frozen["result"]["files"][draft_path]["source"]
    author = frozen["seats"][2]
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "exposure")
    function = ast.get_source_segment(source, node)
    prompt = CODE_TASK + "\nHere is your previous function:\n\n" + function
    prompt += "\n\nReview your draft against the request. Return the complete corrected module in one Python block."
    guest = Guest(sdk)
    got, _, _ = guest.run(source + "\ndef solve(x): return exposure(*x)\n", [REVISION_CASE])
    expected = reference(*REVISION_CASE)
    feedback = f"\nOne check: exposure{REVISION_CASE!r} returned {got[0].get('value')!r} and should return {expected!r}."
    result = dict(author=author, draft_path=draft_path, prompt=prompt, feedback=feedback, arms={})
    candidates = {"original": source}
    try:
        for name, extra in (("retry", ""), ("counterexample", feedback)):
            message = [{"role": "user", "content": prompt + extra}]
            reply = ternary.chat(author, message, max_new_tokens=700, temperature=0.0)
            candidates[name] = extract_code(reply)
            result["arms"][name] = dict(reply=reply, source=candidates[name])
            (out / "revision.json").write_text(json.dumps(result, indent=2) + "\n")
    finally:
        stop_owned_servers()
    result["scores"] = {
        name: dict(original=grade_module(program, guest), confirmation=grade_module(program, guest, confirmation_cases()))
        for name, program in candidates.items()
    }
    (out / "revision.json").write_text(json.dumps(result, indent=2) + "\n")
    print({name: {k: sum(v) for k, v in sets.items()} for name, sets in result["scores"].items()})


def stop_owned_servers():
    from team import ternary

    for process in list(ternary._PROC.values()):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def grid_trial(evidence, out, sdk):
    """Collect mistakes on nine two-point examples and ask the same cell for an importable function."""
    from team import ternary
    from team.tools.source import extract_code
    from training.experiments.fieldwork.guest import Guest

    out.mkdir(parents=True, exist_ok=False)
    recorded = json.loads(evidence.read_text())
    previous = recorded["revision_trial"]
    original = recorded["live_coding"]["result"]["files"][previous["draft_path"]]["source"]
    guest = Guest(sdk)
    probes = [([[0, a], [4, b]], 3, 4) for a, b in itertools.product((1, 3, 5), repeat=2)]
    observed, _, _ = guest.run(original + "\ndef solve(x): return exposure(*x)\n", probes)
    failed = []
    for sample, row in zip(probes, observed, strict=True):
        expected = reference(*sample)
        if row.get("value") != expected:
            failed.append(dict(inputs=sample, received=row.get("value"), required=expected))
    instruction = (
        "\nA separate caller handles saving. Return only the corrected importable exposure function. "
        "It must have no top-level file operations. The following checks of your previous function failed. "
        "Review all of them and account for other inputs allowed by the original request.\n"
    )
    prompt = previous["prompt"] + instruction + json.dumps(failed)
    try:
        reply = ternary.chat(previous["author"], [{"role": "user", "content": prompt}], max_new_tokens=700, temperature=0.0)
    finally:
        stop_owned_servers()
    program = extract_code(reply)
    trial = dict(author=previous["author"], prompt=prompt, probes=len(probes), failed=failed, reply=reply, source=program)
    trial["scores"] = {name: grade_module(program, guest, cases) for name, cases in coding_suites().items()}
    (out / "grid.json").write_text(json.dumps(trial, indent=2) + "\n")
    print({name: (sum(results), len(results)) for name, results in trial["scores"].items()})


def score_code(out, sdk):
    from team import talk
    from training.experiments.fieldwork.guest import Guest

    job = out / "code-job"
    reply = talk.reply(CODE_TASK, [], name="Reviewer", run_dir=job)
    guest = Guest(sdk)
    files = {}
    for path in sorted(job.rglob("gauge.py")):
        source = path.read_text()
        passes = grade_module(source, guest)
        files[str(path.relative_to(job))] = dict(source=source, correct=sum(passes), passed=passes)
    return dict(
        task=CODE_TASK, reply={k: reply[k] for k in ("text", "worked", "agreed", "seconds")},
        n_checks=len(gauge_cases()), delivered="work/gauge.py" in files, files=files,
    )


def smoke(out, sdk=None):
    from team import talk, ternary

    if out.exists():
        raise FileExistsError(f"Choose a new directory for the live run: {out}")
    out.mkdir(parents=True)
    base = talk.speaker()
    if not base:
        raise RuntimeError("Install the CPU runtime and fetch the active workflow members before the smoke test")
    with socket.socket() as conn:
        if conn.connect_ex(("127.0.0.1", ternary.port(base))) == 0:
            raise RuntimeError("Use an idle local runtime for this cold-process measurement")
    roster = ternary.roster()
    if not all(ternary.adapter(member) and ternary.adapter(member).is_file() for member in roster):
        raise RuntimeError("The workflow's selected adapters must be present")

    record = dict(
        revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        members=roster, conversation=[], file_task=FILE_TASK, expected_csv=EXPECTED_CSV,
    )
    trace = out / "smoke.json"
    history = []
    try:
        if sdk is not None:
            coding = dict(revision=record["revision"], members=roster, result=score_code(out, sdk))
            (out / "code.json").write_text(json.dumps(coding, indent=2) + "\n")
            print({p: row["correct"] for p, row in coding["result"]["files"].items()})
            return
        for i, message in enumerate(CONVERSATION):
            reply = talk.reply(message, history, name="Reviewer", run_dir=out / f"turn-{i + 1}")
            record["conversation"].append(dict(
                user=message, reply=reply["text"], worked=reply["worked"], seconds=reply["seconds"],
            ))
            history.extend(({"role": "user", "content": message}, {"role": "assistant", "content": reply["text"]}))
            trace.write_text(json.dumps(record, indent=2) + "\n")
            print(f"Conversation turn {i + 1}: {reply['text']}", flush=True)
        record["recalled_latest_name"] = history[-1]["content"].strip().rstrip(".").casefold() == "juniper"
        job = out / "file-job"
        reply = talk.reply(FILE_TASK, [], name="Reviewer", run_dir=job)
        record["file_reply"] = {k: reply[k] for k in ("text", "worked", "agreed", "seconds")}
        record["reopened_files"] = file_evidence(job)
        record["candidate_files_matching_schema"] = schema_eligible(record["reopened_files"])
        record["csv_exact"] = record["reopened_files"].get("work/rainfall.csv") == EXPECTED_CSV
        trace.write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record["file_reply"]), "CSV matches:", record["csv_exact"])
    finally:
        stop_owned_servers()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--smoke", type=Path, help="Run the live conversation and file job in this new directory")
    action.add_argument("--replay", type=Path, help="Verify stored observations and regrade frozen module sources")
    action.add_argument("--revise", type=Path, help="Retry the best frozen gauge function with and without one example")
    action.add_argument("--grid", type=Path, help="Retry the same function with all failures on a nine-input grid")
    parser.add_argument("--coding-sdk", type=Path, help="Use this WASI SDK to score the scientific coding brief")
    args = parser.parse_args()
    if args.replay:
        if not args.coding_sdk:
            parser.error("--replay requires --coding-sdk")
        from training.experiments.fieldwork.guest import Guest

        evidence = json.loads(args.replay.read_text())
        if evidence["generation_recount"] != recount():
            raise ValueError("The raw generation ledger disagrees with the published recount")
        rain = evidence["live_conversation_and_file"]
        if schema_eligible(rain["reopened_files"]) != rain["candidate_files_matching_schema"]:
            raise ValueError("The stored CSVs give a different selection with the required schema")
        if (rain["reopened_files"].get("work/rainfall.csv") == EXPECTED_CSV) != rain["csv_exact"]:
            raise ValueError("The delivered CSV and its recorded exact grade disagree")
        guest = Guest(args.coding_sdk)
        code = evidence["live_coding"]["result"]
        if ("work/gauge.py" in code["files"]) != code["delivered"] or code["n_checks"] != len(gauge_cases()):
            raise ValueError("The recorded module delivery or case count disagrees with the evidence")
        for path, item in code["files"].items():
            passes = grade_module(item["source"], guest)
            if passes != item["passed"] or sum(passes) != item["correct"]:
                raise ValueError(f"The replay disagrees on {path}")
            print(f"{path}: {sum(passes)}/{len(passes)}")
        trial = evidence["revision_trial"]
        programs = {name: item["source"] for name, item in trial["arms"].items()}
        programs["original"] = code["files"][trial["draft_path"]]["source"]
        for name, program in programs.items():
            for group, inputs in (("original", gauge_cases()), ("confirmation", confirmation_cases())):
                passes = grade_module(program, guest, inputs)
                if passes != trial["scores"][name][group]:
                    raise ValueError(f"The revision replay disagrees on {name}/{group}")
                print(f"{name}/{group}: {sum(passes)}/{len(passes)}")
        grid, supplied = evidence["grid_trial"], evidence["supplied_repair"]
        for group, cases in coding_suites().items():
            passes = grade_module(grid["source"], guest, cases)
            if passes != grid["scores"][group]:
                raise ValueError(f"The structured retry disagrees on {group}")
            print(f"grid/{group}: {sum(passes)}/{len(passes)}")
            repaired = grade_module(supplied["source"], guest, cases)
            if not all(repaired) or sum(repaired) != supplied["scores"][group]:
                raise ValueError(f"The supplied repair disagrees on {group}")
        print("Generation recount, CSV selection, module scores and revision grades agree.")
    elif args.smoke:
        smoke(args.smoke, args.coding_sdk)
    elif args.revise:
        if not args.coding_sdk:
            parser.error("--revise requires --coding-sdk")
        revision_trial(EVIDENCE, args.revise, args.coding_sdk)
    elif args.grid:
        if not args.coding_sdk:
            parser.error("--grid requires --coding-sdk")
        grid_trial(EVIDENCE, args.grid, args.coding_sdk)
    elif args.coding_sdk:
        parser.error("--coding-sdk requires --smoke, --replay, --revise or --grid")
    else:
        print(json.dumps(recount(), indent=2))
