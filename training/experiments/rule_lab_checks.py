"""Replay the checked procedure, establish an arithmetic control and exercise live CPU recovery."""
import argparse
import hashlib
import itertools
import json
import re
import time
from pathlib import Path

from team import ternary
from training.experiments import rule_lab as lab
from training.experiments.rule_lab_cpu import serving
from training.experiments.rule_lab_recipe import calibrate, execute
from training.experiments.rule_lab_solver import fit


def fixed_controls(recipe):
    scores = []
    corners = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for family in lab.TERMS:
        for seed in range(101, 105):
            law = lab.secret(seed, family)

            def observe(x, y):
                return lab.instrument(law, x, y)

            workers = {"fixed_corners_solver": lambda: fit(family, [(x, y, observe(x, y)) for x, y in corners])}
            if family == "affine":
                workers["stored_procedure"] = lambda: execute(recipe, observe)
            for name, run in workers.items():
                start = time.perf_counter()
                result = run()
                elapsed = time.perf_counter() - start
                hits = sum(lab.instrument(result, x, y) == observe(x, y) for x, y in lab.POINTS)
                scores.append({"worker": name, "family": family, "seed": seed, "hits": hits, "out_of": len(lab.POINTS),
                               "probes": len(recipe["points"]) if name == "stored_procedure" else len(corners),
                               "elapsed_seconds": elapsed})
    return scores


def drift_check(recipe):
    """A fresh sensor changes silently. Only this simulated instrument knows the current law."""
    results = []
    for seed in range(201, 205):
        coefficients = lab.secret(seed, "interaction")
        for phase in ("affine", "interaction", "quadratic", "aliased"):
            def observe(x, y):
                value = lab.instrument(coefficients[:3] if phase in ("affine", "aliased") else coefficients, x, y)
                if phase == "quadratic":
                    return value + x * x
                if phase == "aliased":
                    # All allowed x values are roots. Every calibration probe agrees with an affine world.
                    return value + x * (x - 1) * (x - 2)
                return value

            receipt = calibrate(recipe, observe)
            guess = receipt["coefficients"]
            hits = sum(lab.instrument(guess, x, y) == observe(x, y) for x, y in lab.POINTS) if guess else None
            results.append({"seed": seed, "phase": phase, "selected": receipt["worker"],
                            "probes": len(receipt["observations"]), "hits": hits})
    return results


def exhaustive_checks(recipe):
    """Exercise only the executable workers across the full finite coefficient grid."""
    outcomes = {}
    for family, width in (("affine", 3), ("interaction", 4)):
        wins = 0
        total = 0
        for law in itertools.product((-4, -3, -2, -1, 1, 2, 3, 4), repeat=width):
            def observe(x, y):
                return lab.instrument(law, x, y)

            if family == "affine":
                guess = execute(recipe, observe)
            else:
                corners = [(0, 0), (0, 1), (1, 0), (1, 1)]
                guess = fit(family, [(x, y, observe(x, y)) for x, y in corners])
            wins += guess is not None and all(lab.instrument(guess, x, y) == observe(x, y) for x, y in lab.POINTS)
            total += 1
        outcomes[family] = {"worker": "stored procedure" if family == "affine" else "fixed corners and exact solver",
                            "correct": wins, "worlds": total}
    return outcomes


class WorkerLost(Exception):
    pass


def retention_scores(text, expected):
    try:
        value = json.loads(text)
        return value == expected, value == expected
    except ValueError:
        fence = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", text, re.S | re.I)
        if fence:
            try:
                return False, json.loads(fence[1]) == expected
            except ValueError:
                pass
        return False, False


def retention(cpu, cell):
    items = [
        ("changed plan", [
            {"role": "user", "content": "Book club meets Tuesday in Cedar room. Remember that for this chat."},
            {"role": "assistant", "content": "I have Tuesday in Cedar room."},
            {"role": "user", "content": 'Change the day to Friday. Return the current plan as JSON with keys day and room. Use just the room name.'}],
         {"day": "Friday", "room": "Cedar"}),
        ("inventory", [{"role": "user", "content": "I start with 7 red and 4 green boxes. I ship 2 red and receive 3 green. "
                                     "Return the final integer counts as JSON with keys red and green."}], {"red": 5, "green": 7}),
        ("ordering", [{"role": "user", "content": 'Three jobs fill three slots. Paint follows Sand. Dry follows Paint. '
                                    'Return {"order":[...]} using those exact three job names.'}], {"order": ["Sand", "Paint", "Dry"]}),
        ("missing detail", [{"role": "user", "content": "To book a table we require date, time and party_size. "
                                         'I requested Friday at 7 pm. Return {"missing":[...]} using only the field names still needed.'}],
         {"missing": ["party_size"]}),
    ]
    rows = []
    for item, exchange, expected in items:
        reply = cpu.reply(cell, exchange)
        correct, content = retention_scores(reply["text"], expected)
        rows.append({"item": item, "messages": exchange, "expected": expected, "correct": correct,
                     "content_after_stripping_markdown": content, **reply})
    return rows


def checks(args):
    args.out.mkdir(parents=True, exist_ok=True)
    recipe = json.loads(args.recipe.read_text())["recipe"]
    lab.save(args.out / "fixed.json", fixed_controls(recipe))
    lab.save(args.out / "drift.json", drift_check(recipe))
    lab.save(args.out / "exhaustive.json", exhaustive_checks(recipe))
    notebook = args.out / "recovery-98.json"
    if notebook.exists():
        raise ValueError("choose a fresh output directory for a live interruption")
    cells = ["t80+g41data", "t80+labchild"]
    params = args.binary, args.base, args.catalog, args.out / "logs"
    with serving(*params) as cpu:
        class InterruptAfterReceipt:
            def reply(self, cell, messages):
                if notebook.exists() and json.loads(notebook.read_text())["observations"]:
                    cpu.proc.kill()
                    cpu.proc.wait(timeout=10)
                    raise WorkerLost()
                return cpu.reply(cell, messages)

        try:
            lab.episode(InterruptAfterReceipt(), notebook, 98, "affine", "open", cells)
        except WorkerLost:
            old_pid = cpu.proc.pid
        else:
            raise RuntimeError("no checkpointed measurement was made before the experiment ended")
    before = json.loads(notebook.read_text())
    with serving(*params) as fresh:
        recovered = lab.episode(fresh, notebook, 98, "affine", "open", cells)
        new_pid = fresh.proc.pid
        fresh.proc.kill()
        fresh.proc.wait(timeout=10)
        answer = fresh.reply(cells[1], [{"role": "user", "content": 'Reply with {"ready":1}'}])
        restarted_pid = fresh.proc.pid
        auto_repairs = fresh.repairs
    n = len(before["turns"])
    if before["turns"] != recovered["turns"][:n] or before["observations"] != recovered["observations"][:len(before["observations"])]:
        raise RuntimeError("recovery changed the saved receipt")
    lab.save(args.out / "recovery.json", {
        "killed_pid": old_pid, "new_pid": new_pid, "saved_turns": n, "saved_observations": before["observations"],
        "saved_owner": before["current"], "resuming_cell": recovered["turns"][n]["cell"],
        "receipt_sha256": hashlib.sha256(json.dumps(before["turns"], sort_keys=True).encode()).hexdigest(),
        "score": recovered["score"], "automatic_restarts_after_second_kill": auto_repairs,
        "automatic_replacement_pid": restarted_pid, "automatic_replacement_answer": answer["text"]})
    switches = []
    with serving(*params) as cpu:
        for cell in ("t80+g41data", "t80+g41code", "t80+g41data", "t80+labchild", "t80+g41data", "t80+g41code"):
            starts = cpu.starts
            reply = cpu.reply(cell, [{"role": "user", "content": 'Reply with {"ready":1}'}])
            scales = {Path(a["path"]).stem: a["scale"] for a in ternary._get(cpu.url + "/lora-adapters")}
            if len(scales) > cpu.slots or {k for k, v in scales.items() if v} != {cell}:
                raise RuntimeError("resident adapter set or active weights differ from the request")
            switches.append({"cell": cell, "resident": reply["resident"], "restarted": cpu.starts > starts,
                             "seconds": reply["seconds"], "answer": reply["text"], "scales": scales})
        lab.save(args.out / "cache.json", {"catalog_entries": len(list(args.catalog.glob("*.gguf"))),
                                          "slots": cpu.slots, "peak_kib": cpu.peak_kib, "switches": switches})
    with serving(*params) as cpu:
        lab.save(args.out / "retention.json", {name: retention(cpu, name) for name in ("t80+g41data", "t80+labchild")})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("binary", "base", "catalog", "recipe", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    checks(p.parse_args())


if __name__ == "__main__":
    main()
