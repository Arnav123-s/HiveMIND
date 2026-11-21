"""Generate practice-only programs from crossed record formats and stream contracts."""
import ast
import configparser
import csv
import hashlib
import io
import json
import random
from dataclasses import dataclass
from pathlib import Path

from team.specialists.coder import extract_code

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
        form, rule = forms[i % 4], rules[(i + i // 4) % 4]
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


def messages(prompt, hint=None):
    content = prompt if hint is None else f"{prompt}\n\nImplementation hint: {hint}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]


def grade(reply, spec, guest):
    program = extract_code(reply)
    try:
        tree = ast.parse(program)
        if not any(isinstance(node, ast.FunctionDef) and node.name == "solve" for node in tree.body):
            raise ValueError("missing solve(x)")
    except (ValueError, SyntaxError) as ex:
        return {"ok": False, "matched": 0, "cases": 24, "reason": type(ex).__name__}, None
    matched = 0
    for split in ("check", "audit"):
        cases = examples(spec, split)
        observed, _, _ = guest.run(program, [x for x, _ in cases])
        if len(observed) != len(cases):
            raise RuntimeError("guest returned an incomplete set of grades")
        for row, (_, wanted) in zip(observed, cases, strict=True):
            if "value" in row and json.dumps(row["value"], sort_keys=True) == json.dumps(wanted, sort_keys=True):
                matched += 1
    return {"ok": matched == 24, "matched": matched, "cases": 24}, program


def trial(spec, member, ask, guest, all_pairs=False):
    prompt, hint = instructions(spec)
    base = messages(prompt)
    blind = ask(member, base, max_new_tokens=TOKENS, temperature=0.0)
    first, _ = grade(blind, spec, guest)
    audit = {"spec": spec.seed, "kind": spec.kind, "member": member, "blind": first, "hinted": None}
    if first["ok"] and not all_pairs:
        return None, audit
    second, source = grade(ask(member, messages(prompt, hint), max_new_tokens=TOKENS, temperature=0.0), spec, guest)
    audit["hinted"] = second
    if first["ok"] or not second["ok"] or hint in source:
        return None, audit
    # The only supervised response is the checked member program paired to the unhinted public task.
    row = {"type": "first", "dream": True, "task": prompt, "kind": spec.kind, "seed": spec.seed,
           "who": member, "hint_regret": True, "messages": base, "output": f"```python\n{source}\n```"}
    return row, audit
