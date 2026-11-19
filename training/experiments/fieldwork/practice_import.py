"""Qualify the interval-merging function of an original local practice submission in CPU WebAssembly."""
import argparse
import ast
import hashlib
import json
import random
import re
import secrets
from pathlib import Path

from team.config import fieldwork_sdk_path, saved_bank_path
from team.skill_inputs import infer_contract
from . import work
from .campaign import fingerprint
from .guest import Guest


PREFIX = "Write a Python module and save it as intervals.py. It has two functions. 1) merge(xs)"
CONTRACT = "Merge integer intervals. Input is an array of [start, end] integer pairs with start <= end. Merge overlapping or touching endpoints and return pairs in ascending start order."
PUBLIC = [([], []), ([[3, 3]], [[3, 3]]), ([[3, 7], [1, 3], [-2, -1]], [[-2, -1], [1, 7]]),
          ([[4, 8], [9, 11], [6, 7], [4, 8]], [[4, 8], [9, 11]])]
ADAPTER = '''

def solve(intervals):
    if type(intervals) is not list or not all(type(row) is list and len(row) == 2
            and all(type(x) is int for x in row) and row[0] <= row[1] for row in intervals):
        raise ValueError("expected a list of [start, end] integer pairs with start <= end")
    return merge(intervals)
'''


def _read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64_000:
        return None
    return path.read_bytes()


def _function(source):
    """Preserve exact source of one plain top-level function. Omit all top-level calls and sibling code."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return None
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "merge"]
    if len(functions) != 1:
        return None
    fn, = functions
    args = fn.args.args + fn.args.posonlyargs
    if (len(args) != 1 or fn.decorator_list or fn.returns or fn.args.defaults or fn.args.vararg or fn.args.kwarg
            or fn.args.kwonlyargs or args[0].annotation):
        return None
    return ast.get_source_segment(source, fn)


def _candidate(directory):
    members = directory / "members"
    sources = []
    for path in members.glob("*/member*_*.py"):
        m = re.fullmatch(r"member([1-9][0-9]*)_([1-9][0-9]*)\.py", path.name)
        if m and path.parent.name in {"work", "member" + m[1]} and not path.parent.is_symlink():
            sources.append((int(m[1]), int(m[2]), path))
    # Select by member and submission order before observing any qualification results.
    for number, _, path in sorted(sources):
        raw = _read(path)
        if raw is None:
            continue
        try:
            fn = _function(raw.decode("utf-8"))
        except UnicodeError:
            continue
        if fn:
            return number, path, raw, fn
    return None


def reference(pairs):
    """Independent contract oracle. Join connected components in the overlap graph."""
    todo = set(range(len(pairs)))
    merged = []
    while todo:
        component = [todo.pop()]
        for index in component:
            lo, hi = pairs[index]
            neighbors = {j for j in todo if lo <= pairs[j][1] and pairs[j][0] <= hi}
            todo.difference_update(neighbors)
            component.extend(neighbors)
        merged.append([min(pairs[j][0] for j in component), max(pairs[j][1] for j in component)])
    return sorted(merged)


def probes(seed):
    rng = random.Random(seed)
    seen = {json.dumps(x) for x, _ in PUBLIC}
    cases = []
    while len(cases) < 72:
        origin = rng.choice([0, 0, 10**17, -(10**17)])
        rows = []
        for _ in range(rng.randint(1, 12)):
            if rows and rng.randrange(6) == 0:
                rows.append(rows[-1].copy())
                continue
            start = rng.randint(-24, 24) + origin
            if rows and rng.randrange(4) == 0:
                start = rows[-1][1] + rng.choice([0, 1])
            rows.append([start, start + rng.randrange(15)])
        rng.shuffle(rows)
        key = json.dumps(rows)
        if key not in seen:
            seen.add(key)
            cases.append({"input": rows, "output": reference(rows)})
    return cases


def import_practice(task_dir, bank, guest, *, seed=None):
    directory = Path(task_dir)
    phase = re.fullmatch(r"practice_([0-9]+)", directory.parent.name)
    if not phase or not re.fullmatch(r"h" + phase[1] + r"_[0-9]+", directory.name):
        return {"status": "skipped", "reason": "requires an original hard task from a practice run"}
    task = _read(directory / "members" / "TASK.md")
    if not task or not task.startswith(PREFIX.encode()):
        return {"status": "skipped", "reason": "requires the intervals.merge practice contract"}
    if (directory / "members").is_symlink():
        return {"status": "skipped", "reason": "requires a local submissions directory"}
    chosen = _candidate(directory)
    if not chosen:
        return {"status": "skipped", "reason": "no submitted standalone merge function"}
    number, path, raw, fn = chosen
    try:
        metadata = json.loads(_read(directory / "exam.json") or "{}")
        who = next((row["who"] for row in metadata.get("members", []) if isinstance(row, dict)
                    and row.get("member") == number and isinstance(row.get("who"), str)), None)
    except (ValueError, AttributeError, TypeError):
        who = None
    source = fn + ADAPTER
    seed = secrets.randbits(64) if seed is None else seed
    origin = dict(contract="intervals.merge", practice=directory.parent.name, task=directory.name,
                  member_path=path.relative_to(directory).as_posix(), member=number, model=who,
                  task_sha256=hashlib.sha256(task).hexdigest(), submission_sha256=hashlib.sha256(raw).hexdigest(),
                  function_sha256=fingerprint(fn))
    public = [{"input": x, "output": y} for x, y in PUBLIC]
    receipt = dict(status="rejected", task="merge_intervals", digest=fingerprint(source), origin=origin,
                   seed=seed, public=0, public_total=len(public), validation=0, validation_total=72)
    receipt["public"], _ = work.check(guest, source, public, explain=False)
    if receipt["public"] != len(public):
        return receipt
    qualified = probes(seed)
    receipt["validation_inputs_sha256"] = fingerprint(json.dumps([r["input"] for r in qualified], separators=(",", ":")))
    receipt["validation"], _ = work.check(guest, source, qualified, explain=False)
    if receipt["validation"] == len(qualified):
        row = dict(task=receipt["task"], digest=receipt["digest"], description=CONTRACT, source=source,
                   public=len(public), validation=len(qualified), parents=[], practice_origin=origin,
                   qualification={"seed": seed, "inputs_sha256": receipt["validation_inputs_sha256"]},
                   input_contract=infer_contract([x for x, _ in PUBLIC]))
        work.admit(Path(bank), row)
        receipt["status"] = "qualified"
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--practice-task-dir", required=True, type=Path)
    parser.add_argument("--contract", choices=["intervals.merge"], default="intervals.merge")
    parser.add_argument("--bank", type=Path, default=saved_bank_path())
    parser.add_argument("--sdk", type=Path, default=fieldwork_sdk_path())
    parser.add_argument("--seed", type=int, help="repeat a qualification draw")
    args = parser.parse_args(argv)
    if args.bank is None:
        parser.error("set --bank to enable a local skill bank")
    try:
        receipt = import_practice(args.practice_task_dir, args.bank, Guest(args.sdk), seed=args.seed)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(1, f"Practice import failed: {exc}\n")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] == "qualified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
