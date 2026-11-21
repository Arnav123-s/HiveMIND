"""Answer a work request in chat from a saved, verified method, with no model call.

The fieldwork command (`./hive fieldwork --bank ...`) keeps programs that passed independent checks in a bank folder.
When HIVE_BANK points at such a folder, team.talk asks this module first for every message routed to work:

  answered   one saved task fits the message, its inputs can be read from it, and every saved version of that task
             gives the same result (fieldwork's own shared_results check). The reply is the result and names the method.
  ambiguous  the saved versions give different results on these inputs: nothing is released, the bill is named.
  missing    a saved task fits, but the message does not carry inputs it can run on: it says what is missing.
  None       nothing fits (or no bank, or no WebAssembly runtime): the hive's members do the work as before.

The runtime is the CPython WebAssembly guest the fieldwork command uses (HIVE_FIELDWORK_SDK, by default
runs/fieldwork-assets/wasi; see training/reports/rule_lab/fieldwork/reproduce.md).
"""
import json
import os
import re
from pathlib import Path

from . import config

SKIP = {"what", "much", "many", "does", "cost", "costs", "please", "tell", "give", "need", "want", "this", "that"}


def bank_path():
    path = os.environ.get("HIVE_BANK", "").strip()
    return Path(path) if path else None


def guest():
    """The fieldwork guest, or None when the runtime is not on this machine."""
    from training.experiments.fieldwork.guest import Guest
    sdk = Path(os.environ.get("HIVE_FIELDWORK_SDK") or config.ROOT / "runs" / "fieldwork-assets" / "wasi")
    try:
        import wasmtime  # noqa: F401
        return Guest(sdk) if (sdk / "python.wasm").is_file() else None
    except (ImportError, OSError):
        return None


def _stems(words):
    return {w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w for w in words}


def fit(message, bank):
    """The saved task that fits the message best: (task, description, versions), or None.
    Fieldwork's own word match (work.words) over the description, plus at least one word of the task's name."""
    from training.experiments.fieldwork.work import words
    said = _stems(words(message)) - SKIP
    said_short = _stems(re.findall(r"[a-z]{3,}", message.lower()))
    groups = {}
    for row in bank:
        groups.setdefault((row["task"], row["description"]), []).append(row)
    best = None
    for (task, text), rows in groups.items():
        name = _stems(re.findall(r"[a-z]{3,}", task.replace("_", " "))) - SKIP
        shared = said & _stems(words(text))
        if not (name & said_short) or len(shared) < 2:
            continue
        key = (len(name & said_short), len(shared), -len(text))
        if best is None or key > best[0]:
            rows = sorted({r["digest"]: r for r in rows}.values(), key=lambda r: (-r["validation"], r["digest"]))
            best = (key, task, text, rows)
    return best[1:] if best else None


def input_keys(versions, description):
    """The fields of x the saved programs read."""
    keys = []
    for text in [description] + [r["source"] for r in versions]:
        for k in re.findall(r"""x\[['"](\w+)['"]\]|x\.get\(['"](\w+)['"]|\bx has an? (\w+)\b""", text):
            k = next(p for p in k if p)
            if k not in keys:
                keys.append(k)
    return keys


def read_inputs(message, keys):
    """(input, None) or (None, what is missing)."""
    if not keys:
        return None, "the saved method does not say which inputs it takes"
    for found in re.findall(r"\{.*\}", message, re.S):
        try:
            value = json.loads(found)
        except ValueError:
            continue
        if isinstance(value, dict) and set(keys) <= set(value):
            return value, None
    if len(keys) > 1:
        return None, "the inputs " + ", ".join(keys) + ", given as JSON, e.g. {" + ", ".join(f'"{k}": ...' for k in keys) + "}"
    numbers = re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.]*\d)", message)
    if not numbers:
        return None, f"the {keys[0]} (a list of whole numbers)"
    if any("." in n or n.startswith("-") for n in numbers):
        return None, f"the {keys[0]} as whole, non-negative numbers (I read {', '.join(numbers)})"
    return {keys[0]: [int(n) for n in numbers]}, None


def bounded_inputs(message, versions):
    obj = re.search(r"\{.*\}", message, re.S)
    if obj:
        try:
            return json.loads(obj.group())
        except ValueError:
            return None
    # Only a single integer field can be filled from prose without guessing the field or coercing its type.
    axes = [r["arguments"] for r in versions]
    if not all(len(axis) == 1 and "min" in axis[0] for axis in axes):
        return None
    keys = {axis[0]["name"] for axis in axes}
    numbers = re.findall(r"[+-]?(?:\d+(?:[.,]\d+)*|\.\d+)(?:[eE][+-]?\d+)?", message)
    if len(keys) == len(numbers) == 1 and re.fullmatch(r"[+-]?[0-9]+", numbers[0]):
        try:
            return {keys.pop(): int(numbers[0])}
        except ValueError:
            pass
    return None


def answer(message, bank=None, runner=None, log=None):
    """A saved method's answer to the message (see the module's notes), or None to go on as before."""
    from training.experiments.fieldwork.work import load_bank, shared_results
    say = log or (lambda *a: None)
    bank = bank or bank_path()
    if bank is None:
        return None
    found = fit(message, load_bank(bank))
    if found is None:
        return None
    task, description, versions = found
    plain = re.sub(r"^Write solve\(x\) to\s+", "", description)
    bounded = [r for r in versions if "arguments" in r]
    if bounded:
        from .bank_admit import applies
        value = bounded_inputs(message, bounded)
        legacy = [r for r in versions if "arguments" not in r]
        eligible = [r for r in bounded if applies(r["arguments"], value)]
        if value is None and legacy:
            value, missing = read_inputs(message, input_keys(legacy, description))
        else:
            missing = None if isinstance(value, dict) and (eligible or legacy) else (
                "a JSON object within a saved method's verified domain")
        if not missing:
            versions = eligible + legacy
    else:
        value, missing = read_inputs(message, input_keys(versions, description))
    method = f"{task} ({', '.join(r['digest'][:12] for r in versions)})"
    if missing:
        return dict(status="missing", task=task, methods=[r["digest"] for r in versions],
                    text=f"I have a saved, checked method for this, {method}, but I cannot run it on your message: "
                         f"it needs {missing}. It is made to {plain}")
    runner = runner or guest()
    if runner is None:
        say(f"a saved method fits ({method}), but the WebAssembly runtime is not here; the members do the work")
        return None
    rows, conflict = shared_results(versions, runner, [dict(id="request", input=value)])
    shown = json.dumps(value, separators=(", ", ": "))
    if conflict and "different answers" in conflict:
        amounts = re.search(r"\((.*)\)\.$", conflict)
        return dict(status="ambiguous", task=task, methods=[r["digest"] for r in versions], input=value,
                    text=f"My {len(versions)} saved methods for {task} disagree on this bill, {shown}"
                         + (f": they give {amounts.group(1)}" if amounts else "")
                         + ". Both passed their own checks, so I am not giving an answer. Tell me which convention "
                           "applies, or give a bill with its correct amount that tells them apart.")
    if conflict:
        return dict(status="missing", task=task, methods=[r["digest"] for r in versions], input=value,
                    text=f"I have a saved, checked method for this, {method}, but it does not run on what I read from "
                         f"your message ({shown}). It is made to {plain}")
    result = rows[0]["value"]
    who = (f"the saved method {task} ({versions[0]['digest'][:12]}, passed {versions[0]['validation']} independent checks)"
           if len(versions) == 1 else f"{len(versions)} saved methods for {task}, which agree ({method})")
    return dict(status="answered", task=task, methods=[r["digest"] for r in versions], input=value, value=result,
                text=f"{json.dumps(result) if not isinstance(result, str) else result}\n\n"
                     f"Worked out by {who}, on {shown}, with no model call.")
