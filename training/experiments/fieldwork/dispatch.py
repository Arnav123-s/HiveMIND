"""Choose a field worker using public evidence and evaluate the frozen choice separately."""

import argparse
import inspect
from pathlib import Path

from . import discovery
from .campaign import fingerprint, fitness, read, save
from .contracts import EXAM
from .grade import compact, grade
from .guest import Guest
from .numeric_guest import NumericGuest


def scientist(name, adaptive):
    if name == "climate":
        functions = (discovery.seasonal, discovery.atmosphere)
        entry = f"def solve(x):\n    return atmosphere(x, choose={adaptive})"
    else:
        functions = (
            discovery.drive,
            discovery.raw_lags,
            discovery.dictionary,
            discovery.columns,
            discovery.forecast,
            discovery.paths,
            discovery.identify,
        )
        entry = (
            "def solve(x):\n    if x['phase'] == 'design':\n        return drive(x['budget'])\n"
            f"    return identify(x['u'], x['y'], x['future'], grow={adaptive})[0]"
        )
    return "\n\n".join(["import numpy as np", *(inspect.getsource(fn) for fn in functions), entry])


def registry(root, name):
    candidates = []

    def read_member(path, label, field, origin):
        if path.is_file():
            source = read(path)[field]
            candidates.append((label, source, "wasi", origin))

    for model in ("g41", "recruit", "4b", "q35", "coder7b"):
        read_member(root / (model + "-cold") / (name + ".json"), model + "/first", "source", "model")
        for treatment in ("cold", "grown", "coached"):
            read_member(
                root / model / treatment / (name + ".json"),
                model + "/" + treatment,
                "program",
                "model with reference notes" if treatment == "coached" else "model",
            )
    if name in ("roster", "ferry"):
        read_member(
            root / "algorithm-school-v2" / (name + ".json"),
            "algorithm school",
            "source",
            "supplied algorithm family",
        )
    elif name == "ledger":
        for arm in ("standard", "csv"):
            read_member(
                root / "phase-repair" / arm / "program.json",
                "repaired phases/" + arm,
                "source",
                "model-derived phases",
            )
        read_member(
            root / "report-school" / "program.json",
            "recovered intake and learned report",
            "source",
            "supplied reporting family and model fragment",
        )
        read_member(root / "stages" / "program.json", "phase workers", "source", "model-derived phases")
        read_member(
            root / "stages-typed" / "program.json",
            "phase workers with input paths",
            "source",
            "model-derived phases",
        )
    elif name in ("thermal", "climate"):
        for path in sorted((root / "numeric-trial" / name).glob("*.json")):
            trial = read(path)
            origin = "model" if trial["digest"] == trial["parent"] else "model with interface repair"
            candidates.append((path.stem + "/numpy", trial["source"], "numpy", origin))
        for adaptive in (False, True):
            label = "adaptive" if adaptive else "fixed"
            candidates.append(
                (label, scientist(name, adaptive), "numpy", "supplied scientific model family")
            )
    return candidates


def select(root, name, candidates, guests):
    ranking = []
    for label, source, runtime, origin in candidates:
        key = fingerprint(source)
        path = root / "public" / name / (runtime + "-" + key + ".json")
        if path.exists():
            row = read(path)
        else:
            public = grade(guests[runtime], name, source, "public")
            if name == "ledger":
                from .phase_repair import FORMATS, comma_example
                from .work import check

                extra, feedback = check(guests[runtime], source, [comma_example()], FORMATS)
                public["correct"] += extra
                public["total"] += 1
                public["complete"] = public["correct"] == public["total"]
                if not extra:
                    public["feedback"] = feedback
            row = dict(digest=key, public=compact(public), fitness=fitness(public))
            save(path, row)
        ranking.append(dict(label=label, program=source, runtime=runtime, origin=origin, **row))
    if not ranking:
        raise ValueError("no candidates for " + name)
    # On an exact public tie, prefer a model-written worker, then the shorter program.
    ranking.sort(
        key=lambda r: (
            -r["fitness"][0],
            -r["fitness"][1],
            r["origin"].startswith("supplied"),
            r["origin"] == "model with reference notes",
            len(r["program"]),
            r["label"],
        )
    )
    winner = ranking[0]
    return dict(
        task=name,
        qualified=winner["public"]["complete"],
        winner=winner["label"],
        digest=winner["digest"],
        runtime=winner["runtime"],
        origin=winner["origin"],
        program=winner["program"],
        candidates=[{k: v for k, v in r.items() if k != "program"} for r in ranking],
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("sdk", "root", "out"):
        p.add_argument("--" + k, type=Path, required=True)
    p.add_argument("--tasks", nargs="+", choices=EXAM, default=EXAM)
    args = p.parse_args()
    guests = {"wasi": Guest(args.sdk), "numpy": NumericGuest()}
    for name in args.tasks:
        dest = args.out / name
        row = select(args.out, name, registry(args.root, name), guests)
        save(dest / "selected.json", row)
        if row["qualified"]:
            for split in ("exam", "confirmation"):
                trial = grade(guests[row["runtime"]], name, row["program"], split)
                save(dest / (split + ".json"), dict(digest=row["digest"], **trial))
                print(name, row["winner"], split, trial["correct"], trial["total"], flush=True)
        else:
            print(name, "no worker qualified", flush=True)


if __name__ == "__main__":
    main()
