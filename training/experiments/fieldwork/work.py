"""Run a new, user-defined programming work order on CPU with public examples and a persistent skill directory."""

import argparse
import csv
import contextlib
import fcntl
import io
import json
import os
import re
import tempfile
from pathlib import Path

from .campaign import fingerprint, save, tool_source
from .contracts import Task
from .guest import Guest
from .native import generate, server


def words(text):
    return set(re.findall(r"[a-z]{4,}", text.lower())) - {
        "return",
        "input",
        "output",
        "write",
        "python",
        "list",
        "function",
        "solve",
        "with",
        "each",
    }


def retrieve(text, bank):
    mine = words(text)

    def score(row):
        other = words(row["description"])
        return len(mine & other) / max(1, len(mine | other))

    ranked = sorted(
        (r for r in bank if score(r) > 0), key=lambda r: (-score(r), -r["validation"], r["digest"])
    )
    selected = {}
    for r in ranked:
        selected.setdefault(r["task"], r)
    return list(selected.values())[:2]


def matches(actual, expected, formats=None):
    if formats:
        if not isinstance(actual, dict) or set(expected) != set(actual):
            return False
        actual, expected = actual.copy(), expected.copy()
        for key, fmt in formats.items():
            if not isinstance(actual.get(key), str) or not isinstance(expected.get(key), str):
                return False
            try:
                if fmt == "json":
                    actual[key], expected[key] = json.loads(actual[key]), json.loads(expected[key])
                elif fmt == "csv":
                    if expected[key].endswith("\n") and not actual[key].endswith("\n"):
                        return False
                    actual[key] = list(csv.reader(io.StringIO(actual[key])))
                    expected[key] = list(csv.reader(io.StringIO(expected[key])))
                else:
                    raise ValueError("unknown file comparison")
            except (ValueError, csv.Error):
                return False
    return json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)


def check(guest, program, examples, formats=None):
    results, _, _ = guest.run(program, [r["input"] for r in examples], fuel=14_000_000_000)
    ok = [
        ("value" in v and matches(v["value"], r["output"], r.get("compare", formats)))
        for v, r in zip(results, examples)
    ]
    failed = next((i for i, b in enumerate(ok) if not b), None)
    feedback = "All examples passed."
    if failed is not None:
        feedback = json.dumps(
            {
                "input": examples[failed]["input"],
                "expected": examples[failed]["output"],
                "actual": results[failed],
            },
            separators=(",", ":"),
        )[:650]
    return sum(ok), feedback


def load_bank(directory):
    if directory is None or not directory.is_dir():
        return []
    old = []
    for p in sorted(directory.glob("*.json")):
        try:
            row = json.loads(p.read_text())
            if (
                re.fullmatch("[a-z][a-z0-9_]{0,60}", row["task"])
                and fingerprint(row["source"]) == row["digest"] == p.stem
                and isinstance(row["description"], str)
                and type(row["validation"]) is int
                and row["validation"] > 0
            ):
                old.append(row)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            continue
    return old


def finish_files(root, ident, value, names):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", ident):
        raise ValueError("job ID must be a single name")
    if (
        len(set(names)) != len(names)
        or not names
        or any(Path(n).name != n or n in (".", "..", "") for n in names)
        or not isinstance(value, dict)
        or set(value) != set(names)
        or not all(isinstance(v, str) for v in value.values())
    ):
        raise ValueError("returned files differ from the requested file contract")
    destination = root / ident
    if destination.is_symlink():
        raise FileExistsError(destination)
    if destination.exists():
        if not destination.is_dir():
            raise FileExistsError(destination)
        present = {p.name for p in destination.iterdir()}
        if not present <= set(names) or any(
            (destination / n).is_symlink()
            or not (destination / n).is_file()
            or (destination / n).read_bytes() != value[n].encode()
            for n in present
        ):
            raise FileExistsError(destination)
        for n in set(names) - present:
            with tempfile.NamedTemporaryFile(dir=root) as stream:
                stream.write(value[n].encode())
                stream.flush()
                os.link(stream.name, destination / n)
        return
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        stage = Path(tmp) / "files"
        stage.mkdir()
        for n in names:
            (stage / n).write_bytes(value[n].encode())
        os.replace(stage, destination)


def commit_output(root, job, value):
    if "snapshot_file" in job:
        name = job["snapshot_file"]
        if "files" in job:
            raise ValueError("a job must choose a JSON snapshot or named file outputs")
        body = json.dumps(value, sort_keys=True, allow_nan=False) + "\n"
        finish_files(root, job["id"], {name: body}, [name])
        return root / job["id"] / name
    if "files" in job:
        finish_files(root, job["id"], value, job["files"])


def saved_receipt(out, spec):
    result = json.loads((out / "receipt.json").read_text())
    by_id = {j["id"]: j for j in spec.get("jobs", [])}
    valid = set()
    for i, row in enumerate(result["jobs"]):
        if "value" in row:
            try:
                job = by_id[row["id"]]
                if not set(job.get("from_job", {}).values()) <= valid:
                    raise ValueError("a stored snapshot could not be verified")
                commit_output(out, job, row["value"])
                valid.add(row["id"])
            except (ValueError, TypeError, OSError) as exc:
                result["jobs"][i] = {"id": row["id"], "error": str(exc)}
    return result


def deliver(guest, program, jobs, root):
    ids = [j["id"] for j in jobs]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", i) for i in ids):
        raise ValueError("each job needs a unique short ID")
    linked = any(j.get("from_job") for j in jobs)
    results = [] if linked else guest.run(program, [j["input"] for j in jobs], fuel=30_000_000_000)[0]
    receipts = []
    snapshots = {}
    for i, job in enumerate(jobs):
        try:
            if linked:
                value = job["input"]
                if job.get("from_job"):
                    value = dict(value)
                    for field, prior in job["from_job"].items():
                        if prior not in snapshots or field in value:
                            raise ValueError("snapshot dependency unavailable or input field already set")
                        value[field] = json.loads(snapshots[prior].read_bytes())
                row = guest.run(program, [value], fuel=30_000_000_000)[0][0]
            else:
                row = results[i]
            if "value" in row:
                snapshot = commit_output(root, job, row["value"])
                if snapshot is not None:
                    snapshots[job["id"]] = snapshot
        except (OSError, ValueError, TypeError) as exc:
            row = {"error": str(exc)}
        receipts.append({"id": job["id"], **row})
    return receipts


def work(spec, guest, ask, out, bank_path=None, rounds=3, memory_view="contract"):
    out.mkdir(parents=True, exist_ok=True)
    with (out / ".work.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _work(spec, guest, ask, out, bank_path, rounds, memory_view)


def _work(spec, guest, ask, out, bank_path, rounds, memory_view):
    name = spec["name"]
    if not re.fullmatch("[a-z][a-z0-9_]{0,60}", name) or not spec["examples"] or rounds < 1:
        raise ValueError("provide a short program name and at least one checked example")
    if memory_view not in ("contract", "source"):
        raise ValueError("unknown memory view")
    token = fingerprint(json.dumps(spec, sort_keys=True, separators=(",", ":")))
    manifest = out / "work-order.json"
    if manifest.exists():
        state = json.loads(manifest.read_text())
        if state["spec_digest"] != token:
            raise ValueError("this output belongs to a different work order")
        old = state["parents"]
        memory_view = state.get("memory_view", "source")
        if (out / "receipt.json").exists():
            return saved_receipt(out, spec)
    else:
        if any(p.name != ".work.lock" for p in out.iterdir()):
            raise FileExistsError("use a fresh or matching work-order directory")
        old = retrieve(spec["task"], load_bank(bank_path))
        save(manifest, dict(spec_digest=token, parents=old, memory_view=memory_view))
    prompt = Task(
        spec["task"], (), "Public examples: " + json.dumps(spec["examples"], separators=(",", ":"))[:1900]
    )
    prefix = ""
    if old and memory_view == "contract":
        helpers = []
        for item in old:
            label = "skill_" + item["task"]
            description = item["description"].replace("Write solve(x)", label + "(x) is available")
            helpers.append(f"{label}(x) — {description}")
        prompt = Task(
            "Optional library, already implemented:\n"
            + "\n".join(helpers)
            + "\n\nCurrent assignment:\n"
            + prompt.text,
            (),
            prompt.example,
        )
    elif old:
        prefix = "\nVerified optional functions from previous work:\n" + "\n".join(
            f"skill_{r['task']}(x): {r['description']}\n{r['source'][:1300]}" for r in old
        )
    best, trace = None, []
    # A new batch of jobs can use a previously qualified worker for exactly this contract.
    # Test its current public examples before spending an inference call.
    for member in old:
        if member["task"] == name and member["description"] == spec["task"]:
            passed, feedback = check(guest, member["source"], spec["examples"], spec.get("compare"))
            if passed == len(spec["examples"]):
                best = dict(
                    program=member["source"],
                    source=member["source"],
                    passed=passed,
                    feedback=feedback,
                    usage={"completion_tokens": 0},
                    stop="verified_reuse",
                    seconds=0,
                )
                trace.append(best)
                break
    for attempt in range(rounds):
        if best is not None and best["passed"] == len(spec["examples"]):
            break
        trial = out / f"attempt-{attempt + 1}.json"
        if trial.exists():
            new = json.loads(trial.read_text())
        else:
            prior = (best["source"], best["feedback"]) if best else None
            row = ask(prompt, prefix, prior)
            program = tool_source(row["source"], old)
            passed, feedback = check(guest, program, spec["examples"], spec.get("compare"))
            new = dict(
                program=program,
                source=row["source"],
                passed=passed,
                feedback=feedback,
                usage=row["usage"],
                seconds=row.get("seconds"),
                stop=row.get("stop"),
            )
            save(trial, new)
        trace.append(new)
        if best is None or new["passed"] > best["passed"]:
            best = new
        if new["passed"] == len(spec["examples"]):
            break
    (out / "solver.py").write_text(best["program"] + "\n")
    promotion = spec.get("validation", [])
    checked = 0
    if promotion and best["passed"] == len(spec["examples"]):
        checked, _ = check(guest, best["program"], promotion, spec.get("compare"))
    key = fingerprint(best["program"])
    result = dict(
        digest=key,
        public=best["passed"],
        examples=len(spec["examples"]),
        validated=checked,
        validation_total=len(promotion),
        parents=[r["digest"] for r in old],
        attempts=trace,
        jobs=[],
    )
    jobs = spec.get("jobs", [])
    if best["passed"] == len(spec["examples"]) and (not promotion or checked == len(promotion)):
        result["jobs"] = deliver(guest, best["program"], jobs, out)
    if (
        bank_path
        and promotion
        and checked == len(promotion)
        and best["passed"] == len(spec["examples"])
        and all("value" in j for j in result["jobs"])
        and key not in result["parents"]
    ):
        save(
            bank_path / (key + ".json"),
            dict(
                task=name,
                description=spec["task"],
                source=best["program"],
                digest=key,
                public=best["passed"],
                validation=checked,
                parents=result["parents"],
            ),
        )
    save(out / "receipt.json", result)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("spec", "out", "sdk"):
        p.add_argument("--" + k, type=Path, required=True)
    for k in ("binary", "weights"):
        p.add_argument("--" + k, type=Path, help="needed when generating a new worker")
    p.add_argument("--adapter", type=Path)
    p.add_argument("--bank", type=Path)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--budget", type=int, default=1400, help="maximum generated tokens per attempt")
    p.add_argument("--concise", action="store_true", help="request code without inline explanations")
    p.add_argument("--memory-view", choices=("contract", "source"), default="contract")
    args = p.parse_args(argv)
    if min(args.rounds, args.threads, args.budget) < 1:
        p.error("rounds, threads and budget must be positive")
    spec = json.loads(args.spec.read_text())
    g = Guest(args.sdk)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
        url = None

        def ask(task, prefix, prior):
            nonlocal url
            if url is None:
                if args.binary is None or args.weights is None:
                    p.error(
                        "no verified worker satisfied these examples; supply --binary and --weights to generate one"
                    )
                url = stack.enter_context(
                    server(args.binary, args.weights, Path(tmp) / "server.log", args.adapter, args.threads)
                )
            return generate(
                url, task, prefix, prior, focused=True, concise=args.concise, budget=args.budget
            )

        score = work(spec, g, ask, args.out, args.bank, args.rounds, args.memory_view)
    jobs = spec.get("jobs", [])
    delivered = sum("value" in row for row in score["jobs"])
    print(
        f"{score['public']}/{score['examples']} examples, {score['validated']}/{score['validation_total']} independent checks, "
        f"{delivered}/{len(jobs)} jobs delivered"
    )
    return int(
        score["public"] != score["examples"]
        or score["validated"] != score["validation_total"]
        or delivered != len(jobs)
    )


if __name__ == "__main__":
    raise SystemExit(main())
