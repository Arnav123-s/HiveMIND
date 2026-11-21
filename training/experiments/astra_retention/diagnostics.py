"""Audit the practice failure ledger and simulate a separate, deny-by-default admission boundary."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile

from training import kinds


def normalized_question(text):
    return " ".join(text.casefold().split())


def bucket(generated_for, maker, seed, parts, task):
    """Route trusted collection metadata before feedback or candidate programs are read."""
    if generated_for != "diagnostic-practice":
        return "ineligible source"
    first, _, _ = str(seed).partition(":")
    if not first.isascii() or not first.isdigit() or not 10_000_000 <= int(first) < 20_000_000:
        return "ineligible seed"
    if maker == "compound":
        if not isinstance(parts, list) or not parts:
            return "unresolved compound"
        names = []
        for part in parts:
            if not isinstance(part, list) or len(part) != 3 or not isinstance(part[0], str):
                return "unresolved compound"
            if str(part[1]).partition(":")[0] != first:
                return "ineligible seed"
            names.append(part[0])
    else:
        names = [maker]
    if any(name not in kinds.BY_NAME for name in names):
        return "unregistered maker"
    if any(name in kinds.HELD_OUT for name in names):
        return "reserved release family"
    if not isinstance(task, str) or not normalized_question(task):
        return "missing question"
    key = sha256(normalized_question(task).encode()).digest()
    return "reserve" if int.from_bytes(key, "big") % 4 == 0 else "diagnostic"


def admit(headers, feedback):
    slot = bucket(**headers)
    if slot != "diagnostic":
        return slot, None
    return slot, feedback()


def controls():
    maker = next(name for name in sorted(kinds.BY_NAME) if name not in kinds.HELD_OUT)
    release = sorted(kinds.HELD_OUT)[0]
    basic = dict(generated_for="diagnostic-practice", maker=maker, seed="10005609:test",
                 parts=None, task="guard fixture")
    tests = {
        "official source even with practice seed": {"generated_for": "release"},
        "official seed even with diagnostic source": {"seed": "held:reserved:0"},
        "official family even with practice seed": {"maker": release},
        "official family inside compound": {"maker": "compound", "parts": [[release, "10005609:part", 0]]},
        "unknown maker": {"maker": "unregistered"},
        "unknown compound parts": {"maker": "compound", "parts": None},
        "foreign compound seed": {"maker": "compound", "parts": [[maker, "held:reserved:1", 0]]},
    }
    tests["reserved diagnostic question"] = next({"task": "fixture " + str(i)} for i in range(100)
        if bucket(**(basic | {"task": "fixture " + str(i)})) == "reserve")
    def forbidden_feedback():
        raise AssertionError("read feedback for a reserved or untrusted source")
    result = {}
    for name, change in tests.items():
        slot, output = admit(basic | change, forbidden_feedback)
        assert output is None
        result[name] = slot
    return result


def audit(path):
    with ZipFile(path) as z:
        raw = z.read("failures.jsonl")
    items = [json.loads(line) for line in raw.splitlines() if line.strip()]
    tags = Counter()
    slots = Counter()
    allowed_flags = Counter()
    seen = {}
    seen_questions = set()
    for row in items:
        tag = {True: "delivered_wrong", False: "not_delivered", None: "unknown"}[row.get("delivered")]
        tags[tag] += 1
        headers = {k: row.get(k) for k in ("maker", "parts", "task")}
        # These are ALREADY PUBLIC practice records. Simulate a separately commissioned diagnostic stream.
        headers.update(generated_for="diagnostic-practice", seed=row.get("rseed"))
        slot, flags = admit(headers, lambda: (bool(row.get("program")), bool(row.get("said")), tag))
        slots[slot] += 1
        q = normalized_question(row["task"])
        if slot in ("diagnostic", "reserve"):
            assert seen.setdefault(q, slot) == slot
        seen_questions.add(q)
        if flags is not None:
            has_program, has_feedback, flag = flags
            if has_program and has_feedback:
                allowed_flags[flag] += 1
    return {
        "failure_ledger_sha256": sha256(raw).hexdigest(),
        "rows": len(items), "distinct_questions": len(seen_questions), "recorded_delivery": dict(tags),
        "retrospective_rows": dict(slots),
        "retrospective_distinct_questions": dict(Counter(seen.values())),
        "eligible_with_program_and_checker_feedback": dict(allowed_flags),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--g55-zip", type=Path, required=True)
    p.add_argument("--g56-zip", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    data = {"g55": audit(a.g55_zip), "g56": audit(a.g56_zip), "controls": controls()}
    a.out.write_text(json.dumps(data, indent=2) + "\n")
