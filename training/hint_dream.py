"""Generate practice-only programs from crossed record formats and stream contracts."""
import ast
import configparser
import csv
import io
import json
import random
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from team.tools.source import extract_code

FORMATS = ("csv", "json", "ini", "queue")
RULES = ("last", "rank", "wrap", "streak")
SYSTEM = "Write a self-contained Python function solve(x). Use the standard library. Return one complete Python code block."
TOKENS = 256


@dataclass(frozen=True)
class Spec:
    seed: str
    form: str
    rule: str
    threshold: int
    modulus: int
    patience: int

    @property
    def kind(self):
        return f"generated stream {self.form} {self.rule}"


def draw(seed, count):
    """Sample format/rule pairs without replacement in balanced, shuffled blocks."""
    rng = random.Random(f"stream-practice-v1:{seed}")
    forms, rules = list(FORMATS), list(RULES)
    rng.shuffle(forms)
    rng.shuffle(rules)
    for i in range(count):
        form_index = i % len(forms)
        form = forms[form_index]
        rule = rules[(form_index + i // len(forms)) % len(rules)]
        modulus = rng.choice((9, 13, 23, 31))
        yield Spec(f"stream-v1/{seed}/{i}", form, rule, rng.randint(2, modulus - 3),
                   modulus, rng.choice((2, 3, 4)))


def encode(form, events):
    if form == "queue":
        return [[label, value] for label, value in events]
    if form == "json":
        return json.dumps([{"label": label, "value": n} for label, n in events])
    if form == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["label", "value"])
        writer.writerows(events)
        return out.getvalue()
    text = configparser.ConfigParser()
    for i, (label, n) in enumerate(events):
        text[f"event{i}"] = {"label": label, "value": str(n)}
    out = io.StringIO()
    text.write(out)
    return out.getvalue()


def expected(spec, events):
    """Judge directly on latent records. Candidate decoders see only the serialization."""
    from itertools import groupby
    labels = list(dict.fromkeys(label for label, _ in events))
    groups = {key: [(i, value) for i, (label, value) in enumerate(events) if key == label] for key in labels}
    if spec.rule == "last":
        return [key for key in labels if groups[key][-1][1] >= spec.threshold]
    if spec.rule == "rank":
        totals = {key: sum(v for _, v in groups[key] if v >= spec.threshold) for key in labels}
        return sorted(labels, key=lambda k: -totals[k])
    if spec.rule == "wrap":
        return {k: sum((v - u) % spec.modulus for (_, u), (_, v) in zip(g, g[1:])) for k, g in groups.items()}
    hits = []
    for key, g in groups.items():
        for above, run in groupby(g, key=lambda iv: iv[1] >= spec.threshold):
            indexes = list(run)
            if above and len(indexes) >= spec.patience:
                hits.append((indexes[spec.patience - 1][0], key))
    return [key for _, key in sorted(hits)]


def examples(spec, split):
    rng = random.Random(f"{spec.seed}/{split}")
    keys = rng.sample(["red", "blue", "lime", "teal", "rose", "oak", "fir", "ash", "elm"], 3)
    a, b, c = keys
    t, m, p = spec.threshold, spec.modulus, spec.patience
    if split == "visible":
        cases = [[(a,t),(b,m-1),(a,1),(c,t),(b,0),(a,t+1)]]
    else:
        cases = [[], [(a,t)], [(b,t),(a,t),(a,t),(b,t)],
                 [(a,m-1),(b,0),(a,0),(a,0),(b,m-1)],
                 [(a,t),(b,t)] * (p+1) + [(a,0)] + [(a,t)] * p]
        for n in (3, 6, 9, 15, 20, 30, 47):
            cases.append([(rng.choice(keys), rng.choice([0,t,t-1,t+1,m-1,rng.randrange(m)])) for _ in range(n)])
    return [(encode(spec.form, case), expected(spec, case)) for case in cases]


def instructions(spec):
    form = {"queue": "x is a list of [label, value] pairs in arrival order.",
            "json": "x is JSON text encoding an array of objects with keys label and value, in arrival order.",
            "csv": "x is CSV text with header label,value and one event per subsequent row, in arrival order.",
            "ini": "x is INI text with one section per event in arrival order, each with keys label and value."}[spec.form]
    t, m, p = spec.threshold, spec.modulus, spec.patience
    rule, hint = {
        "last": (f"Return the labels whose final recorded value is at least {t}. List them in the order they first appeared, even when the final observation order differs.",
                 "Record the last value for every label, including small values; filter only after reading everything."),
        "rank": (f"List every observed label ranked by the sum of its values that are at least {t}, largest sum first. A label with no qualifying values has sum zero. Break ties by first appearance.",
                 "Initialize each label before checking the threshold; preserve first-seen order through a stable descending sort."),
        "wrap": (f"Return a dictionary mapping every label to its total forward change. Each label has its own cyclic meter with values 0 through {m-1}. Its first reading contributes zero. A decrease means one wrap, equality means no change.",
                 f"Keep the previous reading separately for each label; for a later reading add (current - previous) % {m}."),
        "streak": (f"Return a list of alert labels. Emit a label exactly once when its own uninterrupted run of readings at least {t} first reaches length {p}. Only a lower value for that label resets its run. Emit alerts in event order, including later runs.",
                   f"Maintain a count per label; on a low reading reset only that label. Emit only at equality to {p}, not on every later high.")
    }[spec.rule]
    x, y = examples(spec, "visible")[0]
    prompt = (f"{form} Labels are short words and values are whole numbers from 0 to {m-1}. "
              f"{rule} Empty input is valid. Write solve(x), returning the result. "
              f"One example is x = {x!r}, which gives {y!r}.")
    return prompt, hint


def decoding_hint(form):
    """An optional teacher-only reminder of the concrete standard library parser."""
    return {
        "queue": "Iterate directly as `for label, n in x` without sorting the events.",
        "csv": "Iterate csv.DictReader(io.StringIO(x)); it consumes the header. Use r['label'] and int(r['value']).",
        "json": "Iterate json.loads(x), reading each object's r['label'] and r['value'].",
        "ini": "Use cfg=configparser.ConfigParser(); cfg.read_string(x); iterate s in cfg.sections(), reading cfg[s]['label'] and cfg[s].getint('value').",
    }[form]


def messages(prompt, hint=None):
    content = prompt if hint is None else f"{prompt}\n\nImplementation hint: {hint}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]


def grade(reply, spec, guest):
    suites = [examples(spec, split) for split in ("check", "audit")]
    count = sum(map(len, suites))
    program = extract_code(reply)
    try:
        tree = ast.parse(program)
        if not any(isinstance(node, ast.FunctionDef) and node.name == "solve" for node in tree.body):
            raise ValueError("missing solve(x)")
    except (ValueError, SyntaxError) as ex:
        return {"ok": False, "matched": 0, "cases": count, "reason": type(ex).__name__}, None
    matched = 0
    for cases in suites:
        observed, _, _ = guest.run(program, [x for x, _ in cases])
        if len(observed) != len(cases):
            raise RuntimeError("guest returned an incomplete set of grades")
        for row, (_, wanted) in zip(observed, cases, strict=True):
            if "value" in row and json.dumps(row["value"], sort_keys=True) == json.dumps(wanted, sort_keys=True):
                matched += 1
    return {"ok": matched == count, "matched": matched, "cases": count}, program


def trial(spec, member, ask, guest, all_pairs=False, format_hint=False):
    prompt, rule_hint = instructions(spec)
    private = [decoding_hint(spec.form), rule_hint] if format_hint else [rule_hint]
    hint = " ".join(private)
    base = messages(prompt)
    blind = ask(member, base, max_new_tokens=TOKENS, temperature=0.0)
    first, _ = grade(blind, spec, guest)
    audit = {"spec": spec.seed, "kind": spec.kind, "member": member, "blind": first, "hinted": None}
    if first["ok"] and not all_pairs:
        return None, audit
    second, source = grade(ask(member, messages(prompt, hint), max_new_tokens=TOKENS, temperature=0.0), spec, guest)
    audit["hinted"] = second
    if first["ok"] or not second["ok"] or any(part in source for part in private):
        return None, audit
    # The only supervised response is the checked member program paired to the unhinted public task.
    row = {"type": "first", "dream": True, "task": prompt, "kind": spec.kind, "seed": spec.seed,
           "who": member, "hint_regret": True, "messages": base, "output": f"```python\n{source}\n```"}
    return row, audit


def _attempt(seed, output):
    from team import saved, ternary
    guest = saved.guest()
    roster = [member for member in ternary.roster() if member.partition("+")[0] in ternary.MODELS]
    if not guest or not roster:
        output.write_text(json.dumps({"status": "unavailable", "detail": "missing WASI guest or native member"}))
        return
    member = next((m for m in roster if ternary.is_trunk(m)), roster[0])
    spec = next(draw(seed, 1))
    recalled = ()
    if os.environ.get("HIVE_ENGRAMS") == "1":
        from team import engram
        base, cell = ternary.split(member)
        recall = engram.recall_scaled if os.environ.get("HIVE_ENGRAM_GATE") == "1" else engram.recall
        public_prompt, _ = instructions(spec)
        recalled = tuple(recall(public_prompt, base, cell=cell))
    calls = 0

    def ask(*args, **kwargs):
        nonlocal calls
        calls += 1
        return ternary.chat(*args, also=recalled, **kwargs)

    row, audit = trial(spec, member, ask, guest, format_hint=True)
    audit["hint_policy"] = "format-and-rule"
    audit["recalled"] = recalled
    if row:
        row["verified_member"] = True
        row["spec_id"] = spec.seed
        if str(seed).isascii() and str(seed).isdecimal():
            row["seed"] = int(seed)  # preserve the actual grow shard's practice-only seed for self-replay
    output.write_text(json.dumps({"status": "checked", "calls": calls, "audit": audit, "row": row}))


def run_slot(seed, out, receipt, deadline, log=print):
    """Reserve at most one ordinary dream slot, under both the task and job time budgets."""
    cap = float(os.environ.get("HIVE_TASK_SECONDS", 600))
    seconds = min(cap, deadline - time.time()) if deadline else cap
    summary = {"tasks": 0, "right": 0, "rows": 0, "model_calls": 0, "status": "deadline"}
    if seconds <= 0:
        return summary
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=receipt.parent) as tmp:
        path = Path(tmp) / "result.json"
        try:
            subprocess.run([sys.executable, "-m", "training.hint_dream", str(seed), str(path)],
                           timeout=seconds, check=True, cwd=Path(__file__).resolve().parents[1])
            report = json.loads(path.read_text())
        except subprocess.TimeoutExpired:
            report = {"status": "timeout", "calls": None}
        except (subprocess.CalledProcessError, OSError, ValueError) as exc:
            report = {"status": "unavailable", "detail": type(exc).__name__, "calls": None}
        row = report.pop("row", None)
        if row:
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("a") as f:
                f.write(json.dumps(row) + "\n")
        audit = report.get("audit", {})
        solved = any((audit.get(arm) or {}).get("ok") is True for arm in ("blind", "hinted"))
        summary.update(tasks=int(report["status"] != "unavailable"), right=int(solved), rows=int(bool(row)),
                       model_calls=report.get("calls", 0), status=report["status"])
        path.write_text(json.dumps(dict(report, admitted=bool(row)), indent=2) + "\n")
        path.replace(receipt)
    log(f"generated dream {seed}: {summary}", flush=True)
    return summary


if __name__ == "__main__":
    _attempt(sys.argv[1], Path(sys.argv[2]))
