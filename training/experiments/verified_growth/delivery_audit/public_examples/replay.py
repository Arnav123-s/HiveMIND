"""Use only pre-verdict archive data to replay the frozen file relay and literal-example controls."""
import argparse
import ast
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import re
import time
from zipfile import ZipFile

from training.experiments.fieldwork.guest import Guest
from training.experiments.verified_growth.file_relay import relay
from training.experiments.verified_growth.file_relay import check as stock_control

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parents[2]
MANIFEST = EXPERIMENTS / "atlas/pulse/artifacts.json"
ORIGINAL_DIGEST = "63a3e2ba9216b5f8d5854c8a628675ed0e81abf98cc92d6d5f5b67aef0658bb1"
WORKER = re.compile(r"(?:work|member\d+)/member(\d+)_(\d+)\.py$")


def digest(x):
    return sha256(x).hexdigest()


class Meter:
    def __init__(self, sdk):
        self.guest = Guest(sdk)
        self.calls = []

    def run(self, source, inputs):
        outputs, fuel, seconds = self.guest.run(source, inputs)
        self.calls.append(dict(inputs=len(inputs), fuel=fuel, seconds=round(seconds, 6)))
        return outputs, fuel, seconds


def literal_calls(prompt):
    """Observer for original duration requests with an explicit final instruction. Never routes a file."""
    head, marker, tail = prompt.partition("Then tell me")
    if not marker:
        raise ValueError("public final instruction absent")
    examples = []
    for match in relay.CALL.finditer(head):
        args = relay.call_args(match)
        relation = relay.RELATION.match(head[match.end():])
        if args and relation:
            value = relay.VALUE.match(head[match.end() + relation.end():])
            if value:
                examples.append((args, ast.literal_eval(value.group())))
    queries = [relay.call_args(m) for m in relay.CALL.finditer(tail)]
    if not examples or not queries or any(q is None for q in queries):
        raise ValueError("no directly executable public examples and queries")
    return examples, queries


def lookup_source(examples):
    by_name = {}
    for (function, args), value in examples:
        by_name.setdefault(function, []).append((args, value))
    parts = []
    for function, pairs in by_name.items():
        body = [f"def {function}(*args):"]
        for args, value in pairs:
            body.extend([f"    if list(args) == {args!r}:", f"        return {value!r}"])
        value = pairs[0][1]
        fallback = type(value)() if value is not None else None
        body.append(f"    return {fallback!r}")
        parts.append("\n".join(body))
    return "\n\n".join(parts) + "\n"


def observe(guest, programs, examples, queries):
    names = sorted({f for (f, _), value in examples})
    dispatch = "\n\ndef solve(x):\n    return {" + ", ".join(f"{n!r}: {n}" for n in names) + "}[x[0]](*x[1])\n"
    sources = {}
    for path, raw in programs:
        module = relay.module_source(raw, set(names))
        if module:
            sources.setdefault(module, []).append(path)
    records = []
    for src, paths in sources.items():
        rows, _, _ = guest.run(src + dispatch, [args for args, v in examples] + queries)
        public = rows[:len(examples)]
        passed = all("value" in r and type(r["value"]) is type(v) and r["value"] == v
                     for r, (_, v) in zip(public, examples, strict=True))
        records.append(dict(sources=paths, module_sha256=digest(src.encode()), passed_public=passed,
                            public_outputs=public, query_outputs=rows[len(examples):]))
    return records


def archives(directory):
    for artifact in json.loads(MANIFEST.read_bytes()):
        archive = directory / f"{artifact['id']}.zip"
        if not archive.exists():
            raise FileNotFoundError(archive)
        assert digest(archive.read_bytes()) == artifact["sha256"]
        with ZipFile(archive) as z:
            names = set(z.namelist())
            for path in sorted(n for n in names if n.endswith("/members/TASK.md")):
                prompt = z.read(path).decode().strip()
                if not prompt.startswith("Write a Python module"):
                    continue
                base = path.removesuffix("TASK.md")
                rp = base + "REPORT.md"
                prior = z.read(rp).decode().strip() if rp in names else None
                filenames = sorted(relay.FILE.findall(prompt))
                assert len(set(filenames)) == 1
                attempts = []
                for name in names:
                    match = WORKER.fullmatch(name.removeprefix(base)) if name.startswith(base) else None
                    if match:
                        attempts.append((int(match[1]), int(match[2]), name.removeprefix(base), z.read(name).decode()))
                programs = [(name, src) for _, _, name, src in sorted(attempts)]
                stdout = {}
                for name, src in programs:
                    out = str(Path(base + name).parent / ("." + Path(name).name + ".out"))
                    if out in names:
                        stdout[name] = z.read(out).decode().strip()
                events = []
                if base + "events.jsonl" in names:
                    events = [e for e in map(json.loads, z.read(base + "events.jsonl").splitlines())
                              if e["kind"] in ("module", "answer", "same-error")]
                row = dict(generation=artifact["generation"], gate=artifact["name"], archive_id=artifact["id"],
                           archive_sha256=artifact["sha256"], task=base.split("/")[1], filename=filenames[0],
                           archived_path=path, prompt_sha256=digest(prompt.encode()), attempts=len(programs))
                yield row, prompt, prior, programs, stdout, events


def compact(result):
    return {k:v for k,v in result.items() if k != "files"} | {"files": {
        name: {"sha256":digest(src.encode()), "source":src} for name,src in result["files"].items()}}


def proposal(proposer, prompt, prior, programs, guest):
    before = len(guest.calls)
    outcome = compact(proposer(prompt, {}, programs, prior, guest=guest))
    return dict(outcome=outcome, guest=guest.calls[before:])


def run(args):
    cpu = time.process_time()
    started = time.monotonic()
    assert digest(Path(relay.__file__).read_bytes()) == ORIGINAL_DIGEST
    guest = Meter(args.sdk)
    if args.alternative:
        provider = importlib.import_module(args.alternative)
        assert digest(Path(provider.__file__).read_bytes()) == args.parser_sha
        parser, proposer = provider.contract, provider.propose
    else:
        parser, proposer = relay.contract, relay.propose
    rows, eligible, evaluated = [], 0, 0
    for row, prompt, prior, programs, stdout, events in archives(args.archives):
        spec = parser(prompt)
        row.update(applies=bool(spec), report_present=prior is not None,
                   prior="missing" if prior is None else "declined" if relay.DECLINE.match(prior) else "answered")
        if prior is not None:
            if spec and row["prior"] == "declined":
                eligible += 1
            if spec and row["prior"] == "declined" and eligible > 20:
                row["not_run"] = "predeclared compute cap"
            else:
                row["proposal"] = proposal(proposer, prompt, prior, programs, guest)
                if spec and row["prior"] == "declined":
                    evaluated += 1
                    synthetic = [("lookup-only",lookup_source(spec[2]))]
                    row["lookup_alone"] = proposal(proposer, prompt, prior, synthetic, guest)
                    row["lookup_with_workers"] = proposal(proposer, prompt, prior, synthetic + programs, guest)
        if row["filename"] == "durations.py" and not args.alternative:
            examples, queries = literal_calls(prompt)
            before = len(guest.calls)
            actual = observe(guest, programs, examples, queries)
            lookup = observe(guest, [("lookup-only",lookup_source(examples))], examples, queries)
            row["diagnostic"] = dict(prompt=prompt, prior=prior, examples=examples, queries=queries,
                                     worker_runs=actual, lookup_runs=lookup, guest=guest.calls[before:],
                                     historical_stdout=stdout, events=[(e["agent"],e["kind"],e["msg"]) for e in events])
        rows.append(row)
    fixture = stock_control.TEXT
    _, _, examples, _ = relay.contract(fixture)
    synthetic = [("lookup-only", lookup_source(examples))]
    control = dict(prompt=fixture,
                   real=proposal(proposer, fixture, "Not confirmed.", [("original-worker",stock_control.WORKER)], guest),
                   lookup=proposal(proposer, fixture, "Not confirmed.", synthetic, guest),
                   both=proposal(proposer, fixture, "Not confirmed.", synthetic+[("original-worker",stock_control.WORKER)], guest))
    return dict(protocol_sha256=digest((HERE/"protocol.md").read_bytes()), original_relay_sha256=ORIGINAL_DIGEST,
                alternative=args.alternative,parser_sha256=args.parser_sha or ORIGINAL_DIGEST,
                phase="decisions only; zero exam.json reads", eligible_declines=eligible, evaluated_declines=evaluated,
                source_sha256=digest(Path(__file__).read_bytes()), rows=rows, control=control,
                meter=dict(calls=len(guest.calls),input_rows=sum(c["inputs"] for c in guest.calls),
                           fuel=sum(c["fuel"] for c in guest.calls),guest_seconds=sum(c["seconds"] for c in guest.calls),
                           total_wall_seconds=time.monotonic()-started,process_cpu_seconds=time.process_time()-cpu))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sdk", type=Path, required=True)
    p.add_argument("--archives", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--alternative")
    p.add_argument("--parser-sha")
    args = p.parse_args()
    os.environ["RAYON_NUM_THREADS"] = "1"
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    doc = run(args)
    args.out.write_text(json.dumps(doc, indent=2) + "\n")
    print(doc["eligible_declines"], doc["meter"], flush=True)


if __name__ == "__main__":
    main()
