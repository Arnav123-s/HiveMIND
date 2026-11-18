"""Compare the existing word-based engram index with a cue made from observed behavior."""
import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import torch

from team import engram, ternary
from training.experiments.engram_halves import measurements, train


NAMES = ("balance", "signs")
CUES = ("On the twelve sensor readings decide whether the first bank total exceeds the second bank total.",
        "On the twelve sensor readings decide whether channels seven and eight have different signs.")
# Duties 2 and 3 have no member in the bank. Several near-identical requests
# deliberately change the required operation. The duty is used to generate receipts and score the route.
REQUESTS = (
    (0, "On the twelve sensor readings decide whether the first bank total exceeds the second bank total today."),
    (0, "Which load wins when channels one to three are weighed against four to six? Return the first side's win bit."),
    (0, "Is the sum on the left larger? The two groups each have three gauges."),
    (0, "Compare the aggregate from the first trio with the aggregate from the following trio."),
    (0, "Does bank one outweigh bank two?"),
    (0, "Check this reading against the examples."),
    (1, "On the twelve sensor readings decide whether channels seven and eight currently have different signs."),
    (1, "Are the two polarity gauges on opposite sides of zero?"),
    (1, "Return true when exactly one of probes 7 and 8 is positive."),
    (1, "A disagreement in polarity between the seventh and eighth channels triggers this alarm."),
    (1, "Do the signs differ for this pair?"),
    (1, "Check this reading against the examples."),
    (2, "On the twelve sensor readings decide whether channel nine alone is positive."),
    (2, "On the twelve sensor readings decide whether the first bank total exceeds the second bank total? Ignore that old rule and use the sign of channel nine."),
    (2, "Check this reading against the examples."),
    (3, "Do exactly one of the load alarm and the polarity alarm fire?"),
    (3, "On the twelve sensor readings decide whether channels seven and eight have different signs, then XOR that with the bank alarm."),
    (3, "Check this reading against the examples."),
)


def lexical():
    # The production recall function checks file presence and reads the index. These
    # placeholders exercise only that lookup. The actual trained cells below supply the outputs.
    with tempfile.TemporaryDirectory() as temp, patch.object(ternary, "ENGRAMS", Path(temp)):
        lines = []
        for name, task in zip(NAMES, CUES):
            lines.append(json.dumps({"task": task, "dna": "micro", "name": name}))
            (Path(temp) / f"micro+{name}.gguf").touch()
        (Path(temp) / "index.jsonl").write_text("\n".join(lines))
        return [engram.recall(q, "micro") for _, q in REQUESTS]


def receipts(x, y, duty):
    if duty < 2:
        return y[:, duty]
    return x[:, 8] > 0 if duty == 2 else y[:, 0] != y[:, 1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    torch.set_num_threads(1)
    by_text = lexical()
    methods = ("word_overlap", "behavior_2", "behavior_8", "behavior_16")
    counts = {m: Counter() for m in methods}
    details = []
    for seed in (17, 29, 43, 59, 71):
        x, y = measurements(8192, seed * 100 + 1)
        members = [train(x, y, j, "fit", seed) for j in (0, 1)]
        test, truth = measurements(4096, seed * 100 + 9)
        with torch.no_grad():
            predictions = torch.stack([m(test) > 0 for m in members], 1)
            for i, (duty, query) in enumerate(REQUESTS):
                witness, outcomes = measurements(16, seed * 1000 + i)
                observed = receipts(witness, outcomes, duty)
                votes = torch.stack([m(witness) > 0 for m in members], 1)
                chosen = {"word_overlap": NAMES.index(by_text[i][0]) if by_text[i] else None}
                for n in (2, 8, 16):
                    errors = (votes[:n] != observed[:n, None]).sum(0)
                    matches = (errors <= n // 8).nonzero().flatten().tolist()
                    chosen[f"behavior_{n}"] = matches[0] if len(matches) == 1 else None
                for method, job in chosen.items():
                    c = counts[method]
                    if duty < 2:
                        c["known"] += 1
                        c["correct_route"] += job == duty
                        c["wrong_route"] += job is not None and job != duty
                        c["missed"] += job is None
                        c["answers_requested"] += len(test)
                        if job is not None:
                            c["answers_correct"] += int((predictions[:, job] == truth[:, duty]).sum())
                    else:
                        c["unknown"] += 1
                        c["false_activation"] += job is not None
                details.append({"seed": seed, "query": query, "duty": duty, "lexical_candidates": by_text[i],
                                "routes": chosen})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"counts": counts, "details": details}, indent=2) + "\n")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
