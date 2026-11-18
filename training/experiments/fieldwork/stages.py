"""Recover useful phases from unsuccessful programs and recruit a writer for the missing phases."""

import argparse
import ast
import copy
import json
import re
from contextlib import nullcontext
from pathlib import Path

from .campaign import fingerprint, read, save
from .cases import ledger_cases
from .contracts import TASKS, Task
from .grade import compact, grade
from .guest import Guest
from .native import generate, server
from .work import matches


def fragments(source, phase, schema):
    """Try complete entry points and early returns at valid statement boundaries using the observed output keys."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    names = {n.name for n in functions}
    # Top-level examples from earlier submissions may execute I/O unrelated to a phase.
    module = ast.Module(body=imports + functions, type_ignores=[])
    base = ast.unparse(module)
    for name in sorted(names & {"solve", phase}):
        yield f"entry {name}", base + (f"\nsolve = {name}" if name != "solve" else "")
    if not schema or any(not key.isidentifier() for key in schema):
        return
    for fn in functions:
        if fn.name not in {"solve", phase}:
            continue
        assigned = set()
        for i, stmt in enumerate(fn.body):
            assigned.update(
                n.id for n in ast.walk(stmt) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
            )
            if not set(schema) <= assigned or isinstance(stmt, (ast.Return, ast.Raise)):
                continue
            for order in (False, True):
                fields = ", ".join(
                    f"{key!r}: " + (f"sorted({key})" if order and isinstance(schema[key], list) else key)
                    for key in schema
                )
                replacement = copy.copy(fn)
                replacement.name = "solve"
                replacement.body = [*fn.body[: i + 1], ast.parse("return {" + fields + "}").body[0]]
                members = (
                    imports
                    + [other for other in functions if other.name not in {"solve", fn.name}]
                    + [replacement]
                )
                yield (
                    f"return after statement {i + 1}, sorted lists={order}",
                    ast.unparse(ast.Module(body=members, type_ignores=[])),
                )


def assemble(winners):
    entries = []
    for phase, row in winners.items():
        entries += [
            "_scope = {'least_squares': least_squares}",
            f"exec({row['source']!r}, _scope)",
            f"_phases[{phase!r}] = _scope['solve']",
        ]
    return "\n".join(["_phases = {}", *entries, "def solve(x):", "    return _phases[x['phase']](x)"])


def evaluate_phase(guest, source, examples, formats):
    results, _, _ = guest.run(source, [r["input"] for r in examples], fuel=14_000_000_000)
    passed = fields = 0
    feedback = None
    for exemplar, row in zip(examples, results):
        expected, actual = exemplar["output"], row.get("value")
        if "value" in row and matches(actual, expected, formats):
            passed += 1
        elif feedback is None:
            feedback = json.dumps(
                dict(input=exemplar["input"], expected=expected, actual=row), separators=(",", ":")
            )[:1200]
        if isinstance(actual, dict):
            for k, v in expected.items():
                field_format = {k: formats[k]} if formats and k in formats else None
                fields += k in actual and matches({k: actual[k]}, {k: v}, field_format)
    return passed, fields, feedback or "All examples passed."


def phase_prompt(contract, phase, demos):
    segments = re.split(r"\bPhase '([^']+)'", contract)
    instructions = dict(zip(segments[1::2], segments[2::2])).get(phase, contract)
    sample = min(demos, key=lambda r: len(json.dumps(r)))
    rich = max(
        demos, key=lambda r: (sum(str(v).count("\n") for v in r["output"].values()), -len(json.dumps(r)))
    )
    paths = []

    def describe(value, path):
        if isinstance(value, dict):
            for k, v in value.items():
                describe(v, f"{path}[{k!r}]")
        elif isinstance(value, list):
            paths.append(f"{path} is a list; sample item: {value[0]!r}" if value else f"{path} is a list")
        else:
            paths.append(f"{path} is {type(value).__name__}")

    describe(rich["input"], "x")
    return Task(
        f"Write Python solve(x) for phase {phase!r}. This is a standalone function. Requirements: "
        + instructions
        + "\nInput paths from checked examples:\n"
        + "\n".join(paths),
        (),
        "Checked example: "
        + json.dumps(rich, separators=(",", ":"))[:2400]
        + "\nAnother expected result: "
        + json.dumps(sample["output"]),
    )


def learn(name, contract, examples, formats, sources, guest, ask, out, rounds=2):
    selected = {}
    for phase, demos in examples.items():
        dest = out / (phase + ".json")
        if dest.exists():
            selected[phase] = read(dest)
            continue
        best = None
        trace = []
        seen = set()

        def consider(source, origin, edit, usage=None):
            nonlocal best
            key = fingerprint(source)
            if key in seen:
                return
            seen.add(key)
            score, fields, feedback = evaluate_phase(guest, source, demos, formats.get(phase))
            trace.append(
                dict(
                    digest=key,
                    parent=origin,
                    edit=edit,
                    passed=score,
                    fields=fields,
                    usage=usage,
                    source=source if usage else None,
                    feedback=feedback,
                )
            )
            rank = (score, fields, usage is not None)
            if best is None or rank > tuple(best["rank"]):
                best = dict(
                    source=source,
                    digest=key,
                    passed=score,
                    rank=rank,
                    feedback=feedback,
                    origin=origin,
                    edit=edit,
                )

        for origin, source in sources:
            for edit, candidate in fragments(source, phase, demos[0]["output"]):
                consider(candidate, origin, edit)
                if best["passed"] == len(demos):
                    break
            if best and best["passed"] == len(demos):
                break
        for turn in range(rounds):
            if best and best["passed"] == len(demos):
                break
            prompt = phase_prompt(contract, phase, demos)
            prior = (best["source"], best["feedback"]) if turn and best else None
            draft = out / f"{phase}.writer{turn + 1}.json"
            if draft.exists():
                row = read(draft)
            else:
                row = ask(prompt, "", prior)
                save(draft, row)
            consider(row["source"], "local writer", f"phase generation {turn + 1}", row["usage"])
        if best is None:
            raise ValueError("no phase candidates")
        selected[phase] = dict(**best, public=len(demos), search=trace)
        save(dest, selected[phase])
        print(name, phase, best["passed"], len(demos), best["origin"], best["edit"], flush=True)
    return assemble(selected), selected


def examples():
    import csv
    import io

    intake, revise = [], []
    for a, snapshot, request, rows in ledger_cases("public"):
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerows([["zone", "count", "grams"], *rows])
        files = {
            "summary.csv": buf.getvalue(),
            "audit.json": json.dumps(
                {"conflicts": snapshot["conflicts"], "kept_count": len(snapshot["kept"])}
            ),
        }
        intake.append(dict(input=a, output=snapshot))
        revise.append(dict(input=dict(request, snapshot=snapshot), output=files))
    return dict(intake=intake, revise=revise)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("sdk", "out"):
        p.add_argument("--" + k, type=Path, required=True)
    p.add_argument("--sources", type=Path, nargs="+", required=True)
    p.add_argument("--url")
    p.add_argument("--binary", type=Path)
    p.add_argument("--weights", type=Path)
    p.add_argument("--threads", type=int, default=2)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    formats = {"revise": {"summary.csv": "csv", "audit.json": "json"}}
    sources = [(str(p.parent.name) + "/" + p.name, read(p)["source"]) for p in args.sources]
    g = Guest(args.sdk)
    if not args.url and not (args.binary and args.weights):
        p.error("provide either a running local server or its binary and weights")
    with (
        nullcontext(args.url)
        if args.url
        else server(args.binary, args.weights, args.out / "server.log", threads=args.threads)
    ) as url:

        def ask(task, prefix, prior):
            return generate(url, task, prefix, prior, budget=1100, focused=True, concise=True)

        program, parts = learn(
            "ledger", TASKS["ledger"].text, examples(), formats, sources, g, ask, args.out
        )
    result = dict(
        source=program, digest=fingerprint(program), phases={k: v["digest"] for k, v in parts.items()}
    )
    # Public phase selection and program hash are durable before any examination.
    save(args.out / "program.json", result)
    for split in ("public", "exam", "confirmation"):
        scored = grade(g, "ledger", program, split)
        save(args.out / (split + ".json"), scored)
        print(split, compact(scored), flush=True)


if __name__ == "__main__":
    main()
