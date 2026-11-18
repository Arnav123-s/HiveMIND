"""School, develop, freeze and examine independently written CPU programs on new tasks."""

import argparse
import contextlib
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from .contracts import EXAM, SCHOOL, TASKS
from .grade import compact, grade
from .guest import Guest
from .native import generate, server


def fingerprint(source):
    return hashlib.sha256(source.encode()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        tmp = Path(stream.name)
        try:
            json.dump(value, stream, allow_nan=False, separators=(",", ":"))
            stream.write("\n")
            stream.close()
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)


def read(path):
    return json.loads(path.read_text())


def shortlist(name, library):
    """Retrieve transferable school programs by overlap in the public task's vocabulary and declared topics."""
    task = TASKS[name]

    def words(text):
        return set(re.findall(r"[a-z]{4,}", text.lower()))

    def score(r):
        other = TASKS[r["task"]]
        tags = set(task.tags) & set(other.tags)
        overlap = words(task.text) & words(other.text)
        return 2 * len(tags) + len(overlap) / max(1, len(words(task.text) | words(other.text)))

    ranked = sorted(library, key=lambda r: (-score(r), r["task"]))
    return [r for r in ranked if score(r) >= 2][:2]


def tool_source(code, skills):
    if not skills:
        return code
    parts = []
    for r in skills:
        label = "skill_" + r["task"]
        parts.extend(
            [
                "_school_scope = {'least_squares': least_squares}",
                f"exec({r['source']!r}, _school_scope)",
                f"{label} = _school_scope['solve']",
            ]
        )
    return "\n".join(parts) + "\n" + code


def invitation(skills):
    if not skills:
        return ""
    out = [
        "\nEarlier cells earned these optional helpers on independent exercises. They are already callable. "
        "You may use, adapt, or ignore them; each has its own exact input and output contract."
    ]
    for r in skills:
        out.append(
            "skill_"
            + r["task"]
            + "(x): "
            + TASKS[r["task"]].text
            + "\nIts learned Python:\n"
            + r["source"][:1800]
        )
    return "\n".join(out)


def fitness(score):
    measures = []
    for row in score["tests"]:
        d = row.get("detail", {})
        if "nrmse" in d or "origin" in d:
            err = d.get("nrmse", d.get("rmse"))
            measures.append(min(1000, float(err)) if err is not None else 1000)
    return score["correct"], -(sum(measures) / len(measures) if measures else 0)


def school(guest, cold, out, names):
    bank = []
    for name in names:
        first = read(cold / (name + ".json"))
        pub = grade(guest, name, first["source"], "public")
        independent = grade(guest, name, first["source"], "promotion") if pub["complete"] else None
        admitted = bool(independent and independent["complete"])
        record = dict(
            task=name,
            source=first["source"],
            digest=fingerprint(first["source"]),
            admitted=admitted,
            public=compact(pub),
            promotion=compact(independent) if independent else None,
        )
        bank.append(record)
        print("school", name, pub["correct"], admitted, flush=True)
    save(out / "school.json", bank)


def develop(guest, cold, out, name, mode, skills, ask, rounds):
    dest = out / mode / (name + ".json")
    if dest.exists():
        return
    selected = shortlist(name, skills) if mode == "grown" else []
    # With an empty bank these two arms have the same user and system messages, seed and budget.
    paired = out / "cold" / (name + ".json")
    if mode == "grown" and not selected and paired.exists():
        other = read(paired)
        if other["attempts"] == rounds or other["public"]["complete"]:
            save(dest, dict(other, replayed_from="cold", additional_tokens=0))
            return
    results = []
    for turn in range(rounds):
        receipt = out / mode / (name + f".turn{turn + 1}.json")
        if receipt.exists():
            results.append(read(receipt))
            if results[-1]["public"]["complete"]:
                break
            continue
        if turn == 0 and mode == "cold":
            row = read(cold / (name + ".json"))
        else:
            earlier = None
            if results:
                prev = max(results, key=lambda r: tuple(r["fitness"]))
                earlier = (
                    prev["source"],
                    f"Public checks passed {prev['public']['correct']} of {prev['public']['total']}. First failure: "
                    + prev["public"]["feedback"],
                )
            row = ask(name, invitation(selected), earlier)
        complete = tool_source(row["source"], selected)
        public = grade(guest, name, complete, "public")
        item = dict(
            source=row["source"],
            program=complete,
            digest=fingerprint(complete),
            turn=turn + 1,
            school=[r["digest"] for r in selected],
            public=compact(public),
            fitness=fitness(public),
            usage=row["usage"],
            seconds=row["seconds"],
            stop=row["stop"],
        )
        save(receipt, item)
        results.append(item)
        print(mode, name, turn + 1, f"{public['correct']}/{public['total']}", flush=True)
        if public["complete"]:
            break
    best = max(results, key=lambda r: tuple(r["fitness"]))
    save(
        dest,
        dict(
            selected=best["digest"],
            program=best["program"],
            turn=best["turn"],
            attempts=len(results),
            school=[r["task"] for r in selected],
            public=best["public"],
            tokens=sum(r["usage"]["completion_tokens"] for r in results),
        ),
    )


def examine(guest, cold, out, names, methods, split):
    for name in names:
        for method in methods:
            dest = out / split / method / (name + ".json")
            if method == "first":
                source = read(cold / (name + ".json"))["source"]
            else:
                draft = read(out / method / (name + ".json"))
                source = draft["program"]
                if fingerprint(source) != draft["selected"]:
                    raise ValueError("frozen program hash changed")
            if dest.exists():
                old = read(dest)
                if old.get("grader_version") == 2 and old.get("digest") == fingerprint(source):
                    continue
            metrics = grade(guest, name, source, split)
            save(
                dest,
                dict(task=name, method=method, grader_version=2, digest=fingerprint(source), **metrics),
            )
            print(split, method, name, f"{metrics['correct']}/{metrics['total']}", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("school", "develop", "examine"))
    for name in ("sdk", "cold", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    for name in ("binary", "weights", "adapter", "library"):
        p.add_argument("--" + name, type=Path)
    p.add_argument("--tasks", nargs="+", choices=TASKS)
    p.add_argument("--modes", nargs="+", choices=("first", "cold", "grown"))
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--budget", type=int, default=1400)
    p.add_argument("--focused", action="store_true")
    p.add_argument("--concise", action="store_true")
    p.add_argument("--split", choices=("exam", "confirmation"), default="exam")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    guest = Guest(args.sdk)
    if args.action == "school":
        school(guest, args.cold, args.out, args.tasks or SCHOOL)
    elif args.action == "examine":
        examine(
            guest,
            args.cold,
            args.out,
            args.tasks or EXAM,
            args.modes or ("first", "cold", "grown"),
            args.split,
        )
    else:
        modes = args.modes or ("cold", "grown")
        if "first" in modes:
            p.error("first is an examination mode")
        lib = read(args.library or args.out / "school.json") if "grown" in modes else []
        with contextlib.ExitStack() as stack:
            url = None

            def ask(name, prefix, prior):
                nonlocal url
                if url is None:
                    url = stack.enter_context(
                        server(
                            args.binary,
                            args.weights,
                            args.out / "development-server.log",
                            args.adapter,
                            args.threads,
                        )
                    )
                return generate(
                    url,
                    TASKS[name],
                    prefix,
                    prior,
                    budget=args.budget,
                    focused=args.focused,
                    concise=args.concise,
                )

            for name in args.tasks or EXAM:
                for mode in modes:
                    develop(
                        guest,
                        args.cold,
                        args.out,
                        name,
                        mode,
                        [r for r in lib if r["admitted"]],
                        ask,
                        args.rounds,
                    )


if __name__ == "__main__":
    main()
