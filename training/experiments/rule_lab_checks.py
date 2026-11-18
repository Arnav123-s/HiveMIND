"""Replay the checked procedure, establish an arithmetic control and exercise live CPU recovery."""
import argparse
import hashlib
import json
import time
from pathlib import Path

from team import ternary
from training.experiments import rule_lab as lab
from training.experiments.rule_lab_cpu import serving
from training.experiments.rule_lab_recipe import execute
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
        for phase in ("affine", "interaction", "quadratic"):
            def observe(x, y):
                value = lab.instrument(coefficients[:3] if phase == "affine" else coefficients, x, y)
                return value + (x * x if phase == "quadratic" else 0)

            table = {}

            def measure(x, y):
                table[x, y] = observe(x, y)
                return table[x, y]

            guess = execute(recipe, measure)
            measure(2, 1)  # preselected confirmation outside the recipe's unit square
            evidence = [(x, y, z) for (x, y), z in table.items()]
            selected = "stored affine"
            if any(lab.instrument(guess, x, y) != z for x, y, z in evidence):
                guess = fit("interaction", evidence)
                selected = "interaction solver" if guess else "abstain"
            hits = sum(lab.instrument(guess, x, y) == observe(x, y) for x, y in lab.POINTS) if guess else None
            results.append({"seed": seed, "phase": phase, "selected": selected, "probes": len(table), "hits": hits})
    return results


class WorkerLost(Exception):
    pass


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
        try:
            value = json.loads(reply["text"])
            correct = value == expected
        except ValueError:
            correct = False
        rows.append({"item": item, "messages": exchange, "expected": expected, "correct": correct, **reply})
    return rows


def checks(args):
    args.out.mkdir(parents=True, exist_ok=True)
    recipe = json.loads(args.recipe.read_text())["recipe"]
    lab.save(args.out / "fixed.json", fixed_controls(recipe))
    lab.save(args.out / "drift.json", drift_check(recipe))
    notebook = args.out / "recovery-98.json"
    if notebook.exists():
        raise ValueError("choose a fresh output directory for a live interruption")
    cells = ["t80+g41data", "t80+g41code"]
    params = args.binary, args.base, args.catalog, args.out / "logs"
    method = args.recipe.with_name("method.txt").read_text().strip()
    with serving(*params) as cpu:
        class InterruptAfterReceipt:
            def reply(self, cell, messages):
                if notebook.exists() and json.loads(notebook.read_text())["observations"]:
                    cpu.proc.kill()
                    cpu.proc.wait(timeout=10)
                    raise WorkerLost()
                return cpu.reply(cell, messages)

        try:
            lab.episode(InterruptAfterReceipt(), notebook, 98, "affine", "guided", cells, method)
        except WorkerLost:
            old_pid = cpu.proc.pid
        else:
            raise RuntimeError("no checkpointed measurement was made before the experiment ended")
    before = json.loads(notebook.read_text())
    with serving(*params) as fresh:
        recovered = lab.episode(fresh, notebook, 98, "affine", "guided", cells, method)
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
