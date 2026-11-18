"""CPU hive experiment. Run with python -m training.experiments.rule_lab --help."""
import argparse
import ast
import hashlib
import itertools
import json
import os
import random
import re
import time
from pathlib import Path

from training.experiments.rule_lab_cpu import serving
from training.experiments.rule_lab_solver import fit

SYSTEM = "You operate an experimental instrument with another lab cell. Reply with exactly one JSON tool call."
PROTOCOL = 3
TERMS = {"affine": "c + a*x + b*y", "interaction": "c + a*x + b*y + d*x*y"}
POINTS = [(-3, -2), (-1, 4), (4, -2), (3, 3), (-2, 0), (0, 4), (5, 1), (1, -3)]


def instrument(coefficients, x, y):
    return sum(c * t for c, t in zip(coefficients, (1, x, y, x * y)))


def secret(seed, family):
    # A permutation per family gives disjoint rules for different seed indices.
    width = 3 if family == "affine" else 4
    rules = list(itertools.product((-4, -3, -2, -1, 1, 2, 3, 4), repeat=width))
    random.Random("hive-rule-lab-v1-" + family).shuffle(rules)
    if not 0 <= seed < len(rules):
        raise ValueError(f"seed must be in [0, {len(rules)})")
    return rules[seed]


def messages(family, mode, state, method=""):
    width = 3 if family == "affine" else 4
    turns = state["turns"]
    obs = state["observations"]
    remaining = width + 1 - len(obs)
    readings = "\n".join(f"r{i}: x={x}, y={y} -> z={z}" for i, (x, y, z) in enumerate(obs)) or "empty"
    notes = [e["note"] for e in turns if e.get("note")]
    words = [
        f"Infer the hidden sensor law z = {TERMS[family]}. Its coefficients are unknown signed integers.",
        f"Submit the {width} coefficients in the order {'c,a,b' if width == 3 else 'c,a,b,d'}. "
        "Your rule must predict readings at unseen settings.",
        f"You may measure integer settings x,y in 0..2. You have {remaining} measurements left.",
        f"Shared instrument notebook:\n{readings}",
    ]
    if remaining:
        words.append('To measure, return {"measure":[[x,y],...],"next":"peer"} or choose "self".')
    words.append('To finish, return {"submit":[...]} with each coefficient as an integer or a quoted arithmetic '
                 'expression using the measured z values r0, r1, ... and +, -, *. A short "note" is optional.')
    if notes:
        words.append("Lab notes: " + " | ".join(notes))
    if mode == "guided":
        words.append("First cell: design and request informative measurements. "
                     "The second cell receives the readings and derives the rule." if not obs else
                     "You received the other cell's work. Infer the coefficients, measuring again only if needed.")
    elif mode == "solo":
        words.append("You are working alone. You keep the readings yourself.")
    if method:
        words.append("A method from an earlier successful calibration: " + method)
    if turns and turns[-1].get("error"):
        words.append("Tool error: " + turns[-1]["error"])
    if not remaining:
        words.append("Calibration is complete. Read the measured values above and submit the coefficients now.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "\n".join(words)}]


def coefficient(value, observations, earlier=None):
    """Small integer calculator for a cell's own expression over public readings."""
    if type(value) is int and abs(value) <= 10000:
        return value
    if not isinstance(value, str) or len(value) > 80:
        raise ValueError("each coefficient needs an integer or a short arithmetic expression")
    readings = {f"r{i}": row[2] for i, row in enumerate(observations)}
    readings.update(earlier or {})

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            result = node.value
        elif isinstance(node, ast.Name) and node.id in readings:
            result = readings[node.id]
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            result = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                result = a + b
            elif isinstance(node.op, ast.Sub):
                result = a - b
            else:
                result = a * b
        else:
            raise ValueError("use measured r indices, integers, +, - or *")
        if abs(result) > 10000:
            raise ValueError("coefficient calculation exceeded 10000")
        return result

    try:
        node = ast.parse(value.strip(), mode="eval").body
    except SyntaxError as exc:
        raise ValueError("invalid arithmetic expression") from exc
    return visit(node)


def checked_action(text, observations, width, accept_probe_envelope=False):
    """Validate tool syntax, bounds and budget. No hidden law is available here."""
    fence = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", text, re.S | re.I)
    call = json.loads(fence[1] if fence else text)
    if not isinstance(call, dict) or ("submit" in call) == ("measure" in call):
        raise ValueError("choose exactly one of measure and submit")
    note = call.get("note", "")
    if not isinstance(note, str) or len(note) > 400:
        raise ValueError("note must be a short string")
    if "submit" in call:
        v = call["submit"]
        if not isinstance(v, list) or len(v) != width:
            raise ValueError(f"submit must contain {width} coefficients")
        return {"submit": [coefficient(c, observations) for c in v], "note": note}
    points = call["measure"]
    unpacked = False
    if (accept_probe_envelope and isinstance(points, list) and len(points) == 2
            and isinstance(points[0], list) and points[0] and isinstance(points[0][0], list)
            and points[1] in (["self"], ["peer"])):
        # Some cell outputs put a routing annotation beside a complete list of
        # coordinates. The explicit top-level next field takes precedence.
        call.setdefault("next", points[1][0])
        points = points[0]
        unpacked = True
    if (isinstance(points, list) and len(points) == 1 and isinstance(points[0], list)
            and points[0] and isinstance(points[0][0], list)):
        points = points[0]
    if not isinstance(points, list) or not 1 <= len(points) <= width + 1 - len(observations):
        raise ValueError("choose new settings within the remaining measurement budget")
    known = {(x, y) for x, y, _ in observations}
    for p in points:
        if not isinstance(p, list) or len(p) != 2 or not all(type(x) is int and 0 <= x <= 2 for x in p):
            raise ValueError("each setting must be two integers in 0..2")
        if tuple(p) in known:
            raise ValueError("that setting is duplicated or already in the notebook")
        known.add(tuple(p))
    if call.get("next", "self") not in ("self", "peer"):
        raise ValueError("next must be self or peer")
    checked = {"measure": points, "next": call.get("next", "self"), "note": note}
    if unpacked:
        checked["unpacked_probe_envelope"] = True
    return checked


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("w") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def episode(cpu, dest, seed, family, mode, cells, method="", accept_probe_envelope=False):
    law = secret(seed, family)
    identity = {"protocol": PROTOCOL, "seed": seed, "family": family, "mode": mode,
                "cells": list(cells), "method": method}
    if accept_probe_envelope:
        identity["accept_probe_envelope"] = True
    state = json.loads(dest.read_text()) if dest.exists() else {
        **identity, "current": 0, "observations": [], "turns": []}
    if any(state.get(k) != v for k, v in identity.items()):
        raise ValueError(f"existing notebook belongs to another experiment: {dest}")
    if "score" in state:
        return state
    while len(state["turns"]) < 6 and not any(t.get("accepted") for t in state["turns"]):
        cell = cells[state["current"]]
        prompt = messages(family, mode, state, method)
        solver_start = time.perf_counter()
        solution = fit(family, state["observations"]) if mode == "solver" else None
        if solution is not None:
            cell = "exact-linear-solver"
            reply = {"text": json.dumps({"submit": solution}), "seconds": time.perf_counter() - solver_start, "usage": {}}
        else:
            reply = cpu.reply(cell, prompt)
        turn = {"cell": cell, "messages": prompt, **reply}
        try:
            call = checked_action(reply["text"], state["observations"], len(law), accept_probe_envelope)
        except (ValueError, TypeError) as e:
            turn["error"] = str(e)
        else:
            turn.update(call)
            if "measure" in call:
                measured = [[x, y, instrument(law, x, y)] for x, y in call["measure"]]
                state["observations"].extend(measured)
                turn["observed"] = measured
                if mode == "guided" or (mode == "open" and call["next"] == "peer"):
                    state["current"] = 1 - state["current"]
            else:
                for x, y, z in state["observations"]:
                    predicted = instrument(call["submit"], x, y)
                    if predicted != z:
                        turn["error"] = (f"Your candidate {call['submit']} predicts {predicted} at x={x}, y={y}. "
                                         f"The instrument measured {z} there. Recalculate using the notebook.")
                        break
                else:
                    turn["accepted"] = True
        state["turns"].append(turn)
        # Restarting after any successful tool call restores its receipt before another turn.
        save(dest, state)
    guess = next((t["submit"] for t in state["turns"] if t.get("accepted")), None)
    predictions = [instrument(guess, x, y) for x, y in POINTS] if guess is not None else []
    actual = [instrument(law, x, y) for x, y in POINTS]
    hits = sum(a == b for a, b in zip(actual, predictions))
    state["score"] = {"correct": hits == len(POINTS), "hits": hits, "out_of": len(POINTS),
                      "settings": POINTS, "actual": actual, "predictions": predictions,
                      "probes": len(state["observations"]), "turns": len(state["turns"]),
                      "used_peer": len({t["cell"] for t in state["turns"]}) > 1}
    save(dest, state)
    return state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path, required=True)
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--catalog", type=Path, required=True, help="directory of named cell GGUF edits")
    p.add_argument("--cells", nargs=2, default=["t80+g41data", "t80+g41code"], metavar=("FIRST", "PEER"))
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--modes", nargs="+", choices=("guided", "open", "solo", "solver"), default=["open"])
    p.add_argument("--families", nargs="+", choices=TERMS, default=["affine"])
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--slots", type=int, default=2)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--method", type=Path, help="optional checked method from a separate teaching run")
    p.add_argument("--accept-probe-envelope", action="store_true",
                   help="also recognize a complete measurement list followed by a nested routing annotation")
    args = p.parse_args()
    method = args.method.read_text().strip() if args.method else ""
    args.out.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    scores = []
    with serving(args.binary, args.base, args.catalog, args.out / "logs", args.slots, args.threads) as cpu:
        for family, seed, mode in itertools.product(args.families, args.seeds, args.modes):
            name = f"{family}-{seed}-{mode}"
            state = episode(cpu, args.out / (name + ".json"), seed, family, mode, args.cells, method,
                            accept_probe_envelope=args.accept_probe_envelope)
            s = state["score"]
            result = {"episode": name, **{k: s[k] for k in ("correct", "hits", "out_of", "probes", "turns", "used_peer")}}
            print(json.dumps(result), flush=True)
            scores.append(result)
    save(args.out / "summary.json", {"scores": scores, "elapsed_seconds": round(time.monotonic() - start, 2),
                                      "server_starts_this_invocation": cpu.starts, "server_peak_kib": cpu.peak_kib,
                                      "cells": args.cells, "threads": args.threads, "slots": args.slots,
                                      "method_sha256": hashlib.sha256(method.encode()).hexdigest() if method else None})


if __name__ == "__main__":
    main()
