"""Let a real cell write a small repeatable procedure from its hive's calibration receipts."""
import argparse
import itertools
import json
import re
from pathlib import Path

from training.experiments import rule_lab as lab
from training.experiments.rule_lab_cpu import serving
from training.experiments.rule_lab_solver import fit


def execute(recipe, observe):
    """The procedure can only request sensor readings and evaluate bounded integer expressions."""
    points = lab.checked_action(json.dumps({"measure": recipe["points"]}), [], 3)["measure"]
    observations = [[x, y, observe(x, y)] for x, y in points]
    expressions = recipe["expressions"]
    if not isinstance(expressions, list) or len(expressions) != 3:
        raise ValueError("supply one expression for each of c, a and b")
    earlier = {}
    for name, expr in zip(("c", "a", "b"), expressions):
        if isinstance(expr, str):
            expr = re.sub(rf"^\s*{name}\s*=\s*", "", expr)
        earlier[name] = lab.coefficient(expr, observations, earlier)
    return list(earlier.values())


def calibrate(recipe, observe):
    """Calibrate a callable integer sensor with the stored procedure and a change check.

    Returns the candidate and its public evidence. A null candidate means neither
    supported family accounts for the measurements. Callers can persist the receipt.
    """
    table = {}

    def measure(x, y):
        if (x, y) not in table:
            table[x, y] = observe(x, y)
        return table[x, y]

    guess = execute(recipe, measure)
    measure(2, 1)
    evidence = [[x, y, z] for (x, y), z in table.items()]
    selected = "stored affine"
    if any(lab.instrument(guess, x, y) != z for x, y, z in evidence):
        guess = fit("interaction", evidence)
        selected = "interaction solver" if guess else "abstain"
    return {"worker": selected, "coefficients": guess, "observations": evidence}


def public_error(recipe, worlds):
    for readings in worlds:
        table = {(x, y): z for x, y, z in readings}
        try:
            guess = execute(recipe, lambda x, y: table[x, y])
        except KeyError:
            return "Choose measurement points present in the example notebook."
        for (x, y), z in table.items():
            predicted = lab.instrument(guess, x, y)
            if predicted != z:
                return f"On public notebook {readings} your coefficients {guess} give {predicted} at {x},{y}; it measured {z}."
    return ""


def synthesize(worlds):
    """Induce short signed sums of sensor readings from checked public data in several worlds."""
    if len(worlds) < 3:
        raise ValueError("need independent public notebooks for expression search")
    tables = [{(x, y): z for x, y, z in world} for world in worlds]
    points = sorted(set.intersection(*(set(t) for t in tables)))
    if not 3 <= len(points) <= 4:
        raise ValueError("need three or four shared measurement settings")
    targets = [fit("affine", world) for world in worlds]
    if any(target is None for target in targets):
        raise ValueError("public data do not identify a unique calibration")
    weights = sorted(itertools.product((0, 1, -1), repeat=len(points)), key=lambda w: sum(map(abs, w)))
    expressions = []
    for j in range(3):
        for w in weights:
            if all(sum(v * t[p] for v, p in zip(w, points)) == goal[j] for t, goal in zip(tables, targets)):
                expr = "".join(("+" if v > 0 else "-") + f"r{i}" for i, v in enumerate(w) if v)
                expressions.append(expr.lstrip("+") or "0")
                break
        else:
            raise ValueError("no signed sum fits these teaching examples")
    return {"points": [list(p) for p in points], "expressions": expressions}


def portable(recipe):
    names = {}
    for name, expression in zip(("c", "a", "b"), recipe["expressions"]):
        expr = re.sub(rf"^\s*{name}\s*=\s*", "", str(expression))
        for previous, value in names.items():
            expr = re.sub(rf"\b{previous}\b", f"({value})", expr)
        names[name] = expr
    return {"points": recipe["points"], "expressions": list(names.values())}


def learn(cpu, cell, sources, out):
    episodes = [json.loads(p.read_text()) for p in sorted(sources)]
    if any(e["family"] != "affine" or not 10 <= e["seed"] <= 15 for e in episodes):
        raise ValueError("use affine teaching receipts 10 through 15")
    successes = [e for e in episodes if e.get("score", {}).get("correct")]
    if not successes:
        raise ValueError("need a checked demonstration")
    example = min(successes, key=lambda e: (len(e["turns"]), e["seed"]))
    worlds = [e["observations"] for e in episodes if len(e["observations"]) >= 3]
    base = (f"From this successful calibration derive a general procedure for ANY affine sensor z=c+a*x+b*y. "
            f"The example notebook is {example['observations']} (each entry is [x,y,z]); "
            f"the checked answer [c,a,b] is {example['turns'][-1]['submit']}. "
            'Return {"points":[...],"expressions":[...]} only. Pick 3 or 4 distinct [x,y] measurements '
            'from the example. In that exact order, their z readings are r0, r1, etc. '
            'Write three bare, quoted arithmetic expressions for c,a,b using r names and + or -. '
            'The numbers will change on the next sensor. Derive the expressions symbolically.')
    traces = []
    prompt = base
    for _ in range(5):
        reply = cpu.reply(cell, [{"role": "system", "content": "You write short reusable instrument procedures in JSON."},
                                 {"role": "user", "content": prompt}])
        try:
            text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", reply["text"], flags=re.I)
            candidate = json.loads(text)
            if not isinstance(candidate, dict) or not {"points", "expressions"} <= candidate.keys():
                raise ValueError("provide both points and expressions")
            error = public_error(candidate, worlds)
        except (ValueError, KeyError, TypeError) as exc:
            error = str(exc)
        traces.append({"prompt": prompt, **reply, "feedback": error})
        result = {"author": cell, "demonstration_seed": example["seed"], "public_worlds": len(worlds),
                  "attempts": traces, "recipe": portable(candidate) if not error else None}
        lab.save(out, result)
        if not error:
            return result
        prompt = f"{base}\nYour previous response was {reply['text']}. The public check returned: {error}"
    candidate = synthesize(worlds)
    if public_error(candidate, worlds):
        raise ValueError("synthesized procedure failed its teaching evidence")
    result.update(author="bounded expression search", recipe=candidate)
    lab.save(out, result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path, required=True)
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    with serving(args.binary, args.base, args.catalog, args.out / "logs") as cpu:
        result = learn(cpu, "t80+g41code", args.source.glob("affine-*-guided.json"), args.out / "learner.json")
    if not result["recipe"]:
        raise SystemExit("no procedure passed the teaching notebooks")
    recipe = result["recipe"]
    method = (f"For an affine sensor, request points {recipe['points']} in this order, then submit "
              f"{json.dumps(recipe['expressions'])}. The r names refer to readings in that order.")
    (args.out / "method.txt").write_text(method + "\n")
    print(method)


if __name__ == "__main__":
    main()
