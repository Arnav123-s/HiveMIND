"""Compare lexical and operation-aware memory retrieval on durable local meeting and pickup corrections."""
import argparse
import json
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import patch

from team import engram, ternary
from training.experiments.hive_commitment_cases import cases
from training.experiments.hive_commitments import Journal
from training.experiments.hive_work_order_rules import learn_exchange, learned_exchange


VERBS = ("Trade", "Rotate", "Cycle")
PHRASES = (("{v} the locations between both bookings.", 1), ("Please {v} the weekdays of the two entries.", 0),
           ("{v} both venues. Preserve the dates.", 1), ("{v} the two days. Leave both sites alone.", 0))
TRANSFER = (("Please {v} the dates of both pickups.", 0), ("{v} both sites.", 1),
            ("{v} the days between the two bookings.", 0), ("{v} the two venues.", 1))
NEGATIVE = ("{v} both days if the owner agrees.", "{v} the two sites or the two days.",
            "{v} one meeting with a third booking.", "Do not {v} both venues.")
NOTES = ("Review the dates of the two entries", "Preserve the locations between both bookings",
         "Verify both venues and preserve the dates", "Review both sites in the two bookings")


def teach(verb):
    source = {"Pine": ["Friday", "East"], "Oak": ["Monday", "West"]}
    observed = {"Pine": ["Friday", "West"], "Oak": ["Monday", "East"]}
    demo = f"{verb} the sites between both entries."
    return dict(name=verb.lower(), dna="t17", task=demo, interface="two-record exchange",
                construct=learn_exchange(demo, source, observed))


def exercise(directory, size):
    fixture = list(cases())
    entries = [teach(verb) for verb in VERBS]
    entries += [dict(name=f"note{i}", dna="t17", task=f"{NOTES[i % len(NOTES)]} for ledger{i}.",
                     interface="read-only note") for i in range(size - len(entries))]
    path = directory / "index.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in entries))
    for row in entries:
        (directory / f"t17+{row['name']}.gguf").touch()
    by_name = {row["name"]: row for row in entries}
    def by_verb():
        return {r["construct"]["verb"]: r for r in engram.index() if r.get("interface") == "two-record exchange"}
    db = directory / "orders.sqlite"
    journal = Journal(db)
    logs = []
    def score(phase, verb, tests, method):
        for position, (pattern, field) in enumerate(tests):
            case = fixture[(len(verb) + position * 5) % len(fixture)]
            public = case["public"]
            text = pattern.format(v=verb if pattern.startswith("{") else verb.lower())
            original = public["opening"]
            names = public["names"]
            expected = {name: list(row) for name, row in original.items()}
            if field is not None:
                a, b = names
                expected[a][field], expected[b][field] = original[b][field], original[a][field]
            ident = f"{phase}-{method}-{verb}-{position}"
            journal.create(ident, public)
            if method == "lexical":
                candidate_names = engram.recall(text, "t17")
                candidates = [by_name[name] for name in candidate_names]
            else:
                match = re.match(r"(?:please\s+)?([a-z]+)", text.lower())
                record = typed.get(match[1]) if match else None
                candidates = [record] if record else []
            for row in candidates:
                if row["interface"] == "two-record exchange":
                    changed = learned_exchange(text.lower(), names, original, row["construct"])
                    if changed is not None:
                        journal.apply(ident, "request", 0, changed)
                        journal.apply(ident, "request", 0, changed)
                        break
            logs.append(dict(id=ident, text=text, phase=phase, method=method, expected=expected,
                             field=field, candidates=[r["name"] for r in candidates]))
    with patch.object(ternary, "ENGRAMS", directory):
        typed = by_verb()
        for method in ("lexical", "typed"):
            for verb in VERBS:
                score("known", verb, PHRASES, method)
                score("unsupported", verb, [(p, None) for p in NEGATIVE], method)
            score("new_word", "Shuffle", PHRASES, method)
        # One fresh observed exchange, followed by different wordings and records.
        extra = teach("Shuffle")
        with path.open("a") as stream:
            stream.write(json.dumps(extra) + "\n")
        (directory / "t17+shuffle.gguf").touch()
        by_name["shuffle"] = extra
        typed = by_verb()
        for method in ("lexical", "typed"):
            score("after_teaching", "Shuffle", TRANSFER, method)
            score("after_unsupported", "Shuffle", [(p, None) for p in NEGATIVE], method)
    journal.db.close()
    journal = Journal(db)
    counts = defaultdict(Counter)
    for row in logs:
        _, revision, actual = journal.read(row["id"])
        ok = actual == row["expected"] and revision == int(row["field"] is not None)
        row.update(success=ok, revision=revision)
        stat = counts[f"{row['method']}-{row['phase']}"]
        stat["jobs"] += 1
        stat["correct_outcomes"] += int(ok)
        stat["writes"] += revision
    journal.db.close()
    return dict(counts=counts, examples=logs if size == 4096 else [])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    results = {}
    for n in (8, 32, 128, 4096):
        with tempfile.TemporaryDirectory() as tmp:
            results[n] = exercise(Path(tmp), n)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
