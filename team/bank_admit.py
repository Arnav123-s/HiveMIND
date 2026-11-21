"""Admit a worker function after exhaustive comparison with a separately supplied finite contract."""
import argparse
import ast
import itertools
import json
import keyword
import math
import os
import re
import textwrap
from functools import lru_cache
from pathlib import Path

from . import saved
from .helper_source import signature
from training.experiments.fieldwork import work
from training.experiments.fieldwork.guest import Guest


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fields(arguments):
    """Ordered Cartesian axes. Integer intervals and typed, explicit JSON values both have exact membership."""
    if not isinstance(arguments, list):
        raise ValueError("arguments must be an ordered list")
    axes = {}
    for arg in arguments:
        name = arg.get("name") if isinstance(arg, dict) else None
        if not isinstance(name, str) or not name.isidentifier() or keyword.iskeyword(name) or name in axes:
            raise ValueError("expected unique Python argument names")
        if set(arg) == {"name", "min", "max"} and type(arg["min"]) is type(arg["max"]) is int:
            if not 1 <= arg["max"] - arg["min"] + 1 <= 65536:
                raise ValueError("integer range must cover 1 to 65,536 values")
            values = range(arg["min"], arg["max"] + 1)
        elif set(arg) == {"name", "values"} and isinstance(arg["values"], list):
            values = arg["values"]
            if not values or len({canonical(v) for v in values}) != len(values):
                raise ValueError("expected distinct JSON values in a nonempty enumeration")
        else:
            raise ValueError("specify either integer min/max or a list of values")
        axes[name] = values
    if not axes or math.prod(map(len, axes.values())) > 65536:
        raise ValueError("contract must cover 1 to 65,536 complete inputs")
    return axes


def validate_contract(spec):
    if not isinstance(spec, dict) or set(spec) != {"task", "description", "function", "arguments", "outputs"}:
        raise ValueError("expected task, description, function, arguments and independent outputs")
    if not isinstance(spec["task"], str) or not re.fullmatch("[a-z][a-z0-9_]{0,60}", spec["task"]):
        raise ValueError("invalid task name")
    if not isinstance(spec["description"], str) or not spec["description"].strip():
        raise ValueError("task description required")
    name = spec["function"]
    if not isinstance(name, str) or not name.isidentifier() or name.startswith("_") or keyword.iskeyword(name):
        raise ValueError("public function name required")
    axes = fields(spec["arguments"])
    if not isinstance(spec["outputs"], list) or len(spec["outputs"]) != math.prod(map(len, axes.values())):
        raise ValueError("one trusted expected output is required for every input")
    canonical(spec)  # Reject non-finite numbers before considering any worker.


def applies(arguments, value):
    try:
        axes = fields(arguments)
        if type(value) is not dict or value.keys() != axes.keys():
            return False
        for name, axis in axes.items():
            item = value[name]
            if isinstance(axis, range):
                if type(item) is not int or item not in axis:
                    return False
            elif canonical(item) not in {canonical(v) for v in axis}:
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def guarded(program, spec):
    """Extract only the named standalone definition. Top-level statements never enter the guest."""
    found = [n for n in ast.parse(program).body if isinstance(n, ast.FunctionDef) and n.name == spec["function"]]
    if len(found) != 1 or signature(found[0]) is None:
        raise ValueError("one standalone definition matching the contract is required")
    fn = found[0]
    positional = [a.arg for a in fn.args.posonlyargs + fn.args.args]
    named = [a.arg for a in fn.args.kwonlyargs]
    axes = fields(spec["arguments"])
    if set(positional + named) != axes.keys():
        raise ValueError("function arguments differ from contract")
    source = ast.get_source_segment(program, fn)
    # A nested scope preserves recursion and keeps worker-chosen names separate from guard builtins.
    call = [f"__row[{k!r}]" for k in positional] + [f"{k}=__row[{k!r}]" for k in named]
    stamp = work.finite_stamp(dict(spec, validation=len(spec["outputs"]), contract_sha256=work.fingerprint(canonical(spec))))
    lines = [stamp, "from __future__ import annotations",
             "def _invoke(__row):", textwrap.indent(source, "    "), f"    return {fn.name}({', '.join(call)})",
             "", "def solve(x):", "    import json", f"    if type(x) is not dict or set(x) != set({list(axes)!r}):",
             "        raise ValueError('wrong input fields')"]
    for k, axis in axes.items():
        expr = f"x[{k!r}]"
        if isinstance(axis, range):
            bad = f"type({expr}) is not int or not {axis.start} <= {expr} <= {axis.stop - 1}"
        else:
            allowed = tuple(canonical(v) for v in axis)
            bad = f"json.dumps({expr}, sort_keys=True, separators=(',', ':'), allow_nan=False) not in {allowed!r}"
        lines.extend([f"    if {bad}:", f"        raise ValueError('outside verified domain for {k}')"])
    lines.append("    return _invoke(x)")
    return "\n".join(lines) + "\n"


def admit(program, spec, bank, guest, *, origin):
    validate_contract(spec)
    source = guarded(program, spec)
    axes = fields(spec["arguments"])
    row = dict(task=spec["task"], description=spec["description"], source=source,
               digest=work.fingerprint(source), validation=len(spec["outputs"]), arguments=spec["arguments"],
               contract_sha256=work.fingerprint(canonical(spec)), program_sha256=work.fingerprint(program), origin=origin)

    def published():
        return any(all(old.get(k) == row[k] for k in
                       ("task", "description", "digest", "validation", "arguments", "contract_sha256"))
                   for old in work.load_bank(bank))

    if not published():
        inputs = (dict(zip(axes, vals)) for vals in itertools.product(*axes.values()))
        for offset in range(0, row["validation"], 512):
            batch = list(itertools.islice(inputs, 512))
            outputs, _, _ = guest.run(source, batch)
            expected = spec["outputs"][offset:offset + len(batch)]
            if len(outputs) != len(batch):
                raise ValueError("incomplete guest response")
            for idx, (observed, wanted) in enumerate(zip(outputs, expected)):
                if "value" not in observed or canonical(observed["value"]) != canonical(wanted):
                    raise ValueError(f"function failed independent check {offset + idx + 1}")
        work.admit(bank, row)
        if not published():
            raise ValueError("stored method failed integrity check")
    return {k: row[k] for k in ("task", "digest", "validation", "contract_sha256", "program_sha256")}


@lru_cache(maxsize=1)
def runtime(sdk):
    return Guest(sdk)


def practice(run, verdicts, contracts_dir, bank, sdk):
    """Use only individually confirmed member programs. The caller supplies independently maintained contracts."""
    if not contracts_dir.is_dir():
        raise ValueError(f"missing contract directory {contracts_dir}")
    observed, specs = [], []
    for path in sorted(contracts_dir.glob("*.json")):
        try:
            spec = json.loads(path.read_text())
            validate_contract(spec)
        except (ValueError, OSError) as exc:
            observed.append({"contract": path.name, "unavailable": str(exc)})
            continue
        specs.append(spec)
    for member in verdicts:
        if member.get("ok") is not True or type(member.get("member")) is not int:
            continue
        number = member["member"]
        receipt = run / "members" / f"member{number}.json"
        data = json.loads(receipt.read_text()) if receipt.is_file() else {}
        program = data.get("program")
        if not isinstance(program, str) or str(data.get("who", ""))[:80] != member.get("who"):
            continue
        try:
            names = {node.name for node in ast.parse(program).body if isinstance(node, ast.FunctionDef)}
        except (ValueError, SyntaxError):
            continue
        for spec in specs:
            if spec["function"] not in names:
                continue
            origin = {"practice": run.parent.name, "job": run.name, "member": number, "who": member["who"]}
            try:
                observation = admit(program, spec, bank, runtime(sdk), origin=origin)
            except ValueError as exc:
                observation = {"task": spec["task"], "rejected": str(exc)}
            observed.append(observation)
    return observed


def main(argv=None):
    from team.config import ROOT
    p = argparse.ArgumentParser(prog="hive bank-admit", description=__doc__)
    p.add_argument("program", type=Path, help="worker program containing the named standalone function")
    p.add_argument("contract", type=Path, help="independently supplied JSON domain and expected outputs")
    p.add_argument("--bank", type=Path, default=saved.bank_path(), help="destination directory, default HIVE_BANK")
    p.add_argument("--sdk", type=Path, default=os.environ.get("HIVE_FIELDWORK_SDK", ROOT / "runs/fieldwork-assets/wasi"))
    args = p.parse_args(argv)
    if args.bank is None:
        p.error("set HIVE_BANK or give --bank")
    try:
        receipt = admit(args.program.read_text(), json.loads(args.contract.read_text()), args.bank,
                        runtime(args.sdk), origin={"file": args.program.name})
    except (ImportError, OSError, TypeError, ValueError, SyntaxError) as exc:
        p.exit(1, f"{p.prog}: {exc}\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0
