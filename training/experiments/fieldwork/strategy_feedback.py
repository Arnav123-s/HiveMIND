"""Compare CPU repairs and fresh drafts given ordinary or matched public examples."""

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from . import cases
from .campaign import fingerprint, read, save
from .contracts import TASKS
from .grade import digest, grade
from .guest import Guest
from .native import generate, server
from .strategy_coverage import read_results


def feedback_sets():
    ordinary = [x for x, _ in cases.static_cases("ferry", "public")[:3]]
    route = dict(n=3, src=0, dst=2, start=3, edges=[[0, 1, 4, 5, 14, 2], [1, 2, 7, 6, 19, 3]])
    matched = [dict(route, lay=lay) for lay in ([0, 0, 0], [2, 0, 0], [0, 2, 0])]
    return {"ordinary": ordinary, "matched": matched}


def new_routes():
    """Balance three outcomes on fresh graphs with distinct start and end stops."""
    rng = random.Random(72911)
    data, counts = [], Counter()
    while len(data) < 48:
        n = rng.randint(3, 8)
        src, dst = rng.sample(range(n), 2)
        edges = []
        for _ in range(rng.randint(n - 1, 4 * n)):
            u, v = rng.sample(range(n), 2)
            first, period = rng.randrange(12), rng.randint(1, 8)
            edges.append([u, v, first, period, first + rng.randint(3, 38), rng.randint(1, 8)])
        x = dict(
            n=n, src=src, dst=dst, start=rng.randrange(9),
            lay=[rng.randrange(9) for _ in range(n)], edges=edges,
        )
        answer = cases.ferry_reference(x)
        group = {None: "unreachable", 0: "waiver unnecessary", 1: "waiver essential"}[answer[1]]
        if counts[group] < 16:
            data.append((x, answer, group))
            counts[group] += 1
    return data


def feedback(guest, parent, inputs):
    actual, _, _ = guest.run(parent, inputs)
    examples = [
        {"input": x, "expected": cases.ferry_reference(x), "previous_execution": result}
        for x, result in zip(inputs, actual, strict=True)
    ]
    return "Review these three public executions against the complete original contract.\n" + json.dumps(
        examples, separators=(",", ":")
    )


def score(guest, source, fresh):
    outputs, _, _ = guest.run(source, [x for x, _, _ in fresh])
    by_group = Counter()
    for (_, answer, group), row in zip(fresh, outputs, strict=True):
        by_group[group] += digest(row.get("value")) == digest(answer)
    record = {"source_sha256": fingerprint(source), "fresh": dict(by_group), "fresh_outputs": outputs}
    for split in ("exam", "confirmation"):
        result = grade(guest, "ferry", source, split)
        record[split] = {
            "correct": result["correct"], "total": result["total"], "stress": result["tests"][-1]["ok"],
            "passed_indices": [i for i, test in enumerate(result["tests"]) if test["ok"]],
        }
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    previous = parser.add_mutually_exclusive_group()
    previous.add_argument("--frozen", type=Path, help="Replay the drafts in a saved result without loading weights")
    previous.add_argument("--extend", type=Path, help="Keep both original repairs and generate the two fresh drafts")
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if not args.frozen and not (args.weights and args.binary):
        parser.error("generation requires --binary and --weights")
    results = read_results()
    parent = results["coder7b-cold/ferry.json"]["source"]
    if fingerprint(parent) != results["coder7b/exam/first/ferry.json"]["digest"]:
        raise ValueError("Parent source does not match its archived grades")
    guest = Guest(args.sdk)
    prompts = {arm: feedback(guest, parent, inputs) for arm, inputs in feedback_sets().items()}
    fresh = new_routes()
    design = dict(
        parent_sha256=fingerprint(parent), fresh_sha256=digest(fresh), prompts=prompts, seed=3141, budget=1000,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    drafts = {}
    if args.frozen or args.extend:
        frozen = read(args.frozen or args.extend)
        if frozen["design"] != design:
            raise ValueError("The saved drafts used different inputs or prompts")
        if args.extend and set(frozen["drafts"]) != set(prompts):
            raise ValueError("The follow-up needs exactly the two original repair drafts")
        for name, draft in frozen["drafts"].items():
            if fingerprint(draft["source"]) != frozen["scores"][name]["source_sha256"]:
                raise ValueError(f"Saved source disagrees with its score record for {name}")
        drafts.update(frozen["drafts"])
    if not args.frozen:
        with server(args.binary, args.weights, args.out.with_suffix(".log"), threads=args.threads) as url:
            for show_source in (True, False):
                for name, prompt in prompts.items():
                    arm = name if show_source else "fresh_" + name
                    if arm in drafts:
                        continue
                    prefix = "" if show_source else "\n" + prompt + "\nReturn a complete corrected implementation."
                    drafts[arm] = generate(
                        url, TASKS["ferry"], prefix=prefix, earlier=(parent, prompt) if show_source else None,
                        budget=design["budget"], seed=design["seed"], focused=True, concise=True,
                    )
                    print(arm, drafts[arm]["usage"], flush=True)
    sources = {"parent": parent, **{arm: row["source"] for arm, row in drafts.items()}}
    sources["supplied_family"] = results["algorithm-school-v2/ferry.json"]["source"]
    scores, by_source = {}, {}
    for arm, source in sources.items():
        key = fingerprint(source)
        if key not in by_source:
            by_source[key] = score(guest, source, fresh)
        scores[arm] = by_source[key]
    save(args.out, dict(design=design, drafts=drafts, scores=scores))
    for arm, record in scores.items():
        print(
            arm, record["fresh"], "exam", record["exam"]["correct"],
            "confirmation", record["confirmation"]["correct"],
        )


if __name__ == "__main__":
    main()
