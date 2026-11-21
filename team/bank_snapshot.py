"""Promote individually checked practice targets into a cumulative, verified method bank."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import textwrap

from . import bank_admit
from .tools.source import extract_code
from training.experiments.fieldwork import work


def digest(rows):
    return hashlib.sha256(bank_admit.canonical(rows).encode()).hexdigest()


def read(path):
    """Verify the whole snapshot before exposing any version. Omitting a contrary version changes the answer."""
    data = json.loads(path.read_bytes())
    if (not isinstance(data, dict) or set(data) != {"version", "sha256", "methods"} or data["version"] != 1
            or not isinstance(data["methods"], list) or digest(data["methods"]) != data["sha256"]):
        raise ValueError("invalid method snapshot")
    seen = set()
    for row in data["methods"]:
        try:
            valid = (isinstance(row["source"], str) and row["source"].startswith(work.FINITE_PREFIX)
                     and row["digest"] == work.fingerprint(row["source"]) and work.valid_scope(row)
                     and re.fullmatch("[a-z][a-z0-9_]{0,60}", row["task"]) and isinstance(row["description"], str)
                     and type(row["validation"]) is int and row["validation"] > 0 and row["digest"] not in seen)
        except (TypeError, KeyError, AttributeError) as exc:
            raise ValueError("invalid bounded method record") from exc
        if not valid:
            raise ValueError("invalid bounded method record")
        seen.add(row["digest"])
    return data["methods"]


def restore(row, specs, stage, runner):
    """Recover just the function; rebuild its guard from the trusted contract and re-execute every input."""
    spec = specs.get(row["contract_sha256"])
    if not spec:
        raise ValueError("previously admitted method needs its original independent contract " + row["contract_sha256"])
    tree = ast.parse(row["source"])
    wrapper = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_invoke"), None)
    if wrapper is None or not wrapper.body or not isinstance(wrapper.body[0], ast.FunctionDef):
        raise ValueError("invalid stored function")
    # ast.get_source_segment for a nested node leaves continuation lines indented by four extra spaces.
    original = textwrap.dedent(ast.get_source_segment(row["source"], wrapper.body[0], padded=True))
    if bank_admit.guarded(original, spec) != row["source"]:
        raise ValueError("stored guard or implementation does not match the trusted contract")
    bank_admit.admit(original, spec, stage, runner, origin=row.get("origin", {}))


def promote(previous, output, practice, contracts, runner):
    specs = {}
    for path in sorted(contracts.glob("*.json")):
        spec = json.loads(path.read_bytes())
        bank_admit.validate_contract(spec)
        specs[digest(spec)] = spec
    if not specs:
        raise ValueError("supply independently maintained contract files")
    prior = read(previous) if previous is not None else []
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        for row in prior:
            restore(row, specs, stage, runner)
        old = {row["digest"]:row for row in prior}
        considered = rejected = 0
        seen = set()
        for shard in sorted(practice.glob("rows-*/rows.jsonl")):
            if not re.fullmatch(r"rows-[0-9]+", shard.parent.name):
                continue
            with shard.open() as stream:
                for line in stream:
                    row = json.loads(line)
                    if (row.get("type") != "first" or row.get("verified_member") is not True
                            or type(row.get("member")) is not int or type(row.get("seed")) is not int
                            or not isinstance(row.get("output"), str) or len(row["output"]) > 8192):
                        continue
                    program = extract_code(row["output"])
                    code_id = work.fingerprint(program)
                    if code_id in seen:
                        continue
                    seen.add(code_id)
                    try:
                        names = {n.name for n in ast.parse(program).body if isinstance(n, ast.FunctionDef)}
                    except (ValueError, SyntaxError):
                        continue
                    for spec in specs.values():
                        if spec["function"] not in names:
                            continue
                        considered += 1
                        try:
                            bank_admit.admit(program, spec, stage, runner, origin={
                                "shard":shard.parent.name, "seed":row["seed"], "member":row["member"], "who":str(row.get("who", ""))[:80]})
                        except ValueError:
                            rejected += 1
        # Retain original provenance for unchanged methods after their independent re-check.
        methods = [old.get(row["digest"], row) for row in work.load_bank(stage)]
        methods.sort(key=lambda row: row["digest"])
        if not set(old) <= {row["digest"] for row in methods}:
            raise ValueError("a previously qualified version was lost")
        payload = bank_admit.canonical({"version":1, "sha256":digest(methods), "methods":methods}) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
        tmpfile = Path(stream.name)
    try:
        tmpfile.write_bytes(payload.encode())
        try:
            os.link(tmpfile, output)
        except FileExistsError:
            if output.read_bytes() != payload.encode():
                raise ValueError("snapshot destination already holds a different version")
    finally:
        tmpfile.unlink(missing_ok=True)
    return {"previous":len(prior), "tested":considered, "rejected":rejected, "methods":len(methods), "sha256":digest(methods)}


def main(argv=None):
    from . import config
    parser = argparse.ArgumentParser(prog="hive bank-promote", description=__doc__)
    parser.add_argument("--previous", type=Path, help="previous cumulative snapshot")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--practice", type=Path, required=True, help="directory of rows-N/rows.jsonl checked practice artifacts")
    parser.add_argument("--contracts", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, default=os.environ.get("HIVE_FIELDWORK_SDK", config.ROOT / "runs/fieldwork-assets/wasi"))
    args = parser.parse_args(argv)
    try:
        result = promote(args.previous, args.output, args.practice, args.contracts, bank_admit.runtime(args.sdk))
    except (ImportError, OSError, SyntaxError, TypeError, ValueError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
