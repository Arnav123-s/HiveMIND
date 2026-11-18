"""Compare rebuilt adapters on fresh, identical notebooks and four ordinary requests."""
import argparse
from pathlib import Path

from training.experiments import rule_lab as lab
from training.experiments.rule_lab_checks import retention
from training.experiments.rule_lab_cpu import serving


def one_reply(cpu, name, seed, family):
    law = lab.secret(seed, family)
    corners = [(0, 0), (0, 1), (1, 0), (1, 1)]
    points = corners if family == "affine" else corners + [(2, 2)]
    readings = [[x, y, lab.instrument(law, x, y)] for x, y in points]
    messages = lab.messages(family, "open", {"observations": readings, "turns": []})
    reply = cpu.reply(name, messages)
    try:
        guess = lab.checked_action(reply["text"], readings, len(law)).get("submit")
    except (ValueError, TypeError):
        guess = None
    correct = guess is not None and all(lab.instrument(guess, x, y) == lab.instrument(law, x, y)
                                        for x, y in lab.POINTS)
    return {"seed": seed, "family": family, "readings": readings, "answer": reply["text"],
            "guess": guess, "law": law, "correct": correct}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("binary", "base", "catalog", "rebuilt", "out"):
        p.add_argument(f"--{k}", required=True, type=Path)
    args = p.parse_args()
    for name in ("exact", "fit", "absmean", "groupfit", "t80+g41data"):
        dest = args.out / f"{name}.json"
        catalog = args.catalog if name == "t80+g41data" else args.rebuilt
        with serving(args.binary, args.base, catalog, args.out / "logs", slots=1) as cpu:
            rows = [one_reply(cpu, name, seed, family) for family, count in (("affine", 8), ("interaction", 4))
                    for seed in range(421, 421 + count)]
            ordinary = retention(cpu, name)
            lab.save(dest, {"cell": name, "worlds": rows, "ordinary": ordinary, "peak_kib": cpu.peak_kib})
            print(name, [(fam, sum(r["correct"] for r in rows if r["family"] == fam))
                         for fam in ("affine", "interaction")], sum(r["correct"] for r in ordinary), flush=True)


if __name__ == "__main__":
    main()
