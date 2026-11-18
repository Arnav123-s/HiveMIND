"""An overlapping population and a shared task, using the rule lab's saved notebooks.

Run python -m training.experiments.rule_lab_lifecycle for the population experiment.
For the separate live handoff, pass --binary, --base, --catalog and a fresh --out.
"""
import argparse
import json
import random
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path

from training.experiments import rule_lab as lab
from training.experiments.rule_lab_cpu import serving
from training.experiments.rule_lab_referrals import notebooks, public_answer


METHODS = ("novice", "affine", "interaction")
FOUNDERS = 12
TURNS_PER_TICK = 2
TICKS = 300


@dataclass
class Cell:
    id: int
    born: int
    method: str
    turns: int = 0
    readings: int = 0
    answers: int = 0
    rejected: int = 0
    children: int = 0


def population(seed, episodes, *, disable_answers=False):
    rng = random.Random(seed)
    living = {i: Cell(i, -12, METHODS[i % len(METHODS)]) for i in range(FOUNDERS)}
    turns = deque(living)
    next_id = FOUNDERS
    events = []
    deaths_after_correct_answer = 0
    completed = 0
    completed_after_reader_died = 0
    receipt = None
    for tick in range(TICKS):
        # The clock sees age and available capacity. Work scores never reach it.
        for member, cell in list(living.items()):
            age = tick - cell.born
            if age < 40:
                continue
            hazard = 0.0002 if age < 180 else 0.0006
            if rng.random() < hazard:
                del living[member]
                turns.remove(member)
                deaths_after_correct_answer += cell.answers > 0
                events.append(("death", tick, member))

        adults = [c for c in living.values() if tick - c.born >= 12]
        # At two turns per tick, a target of 40 ticks per rotation allows 80
        # living cells. Filling it slows future births; incumbents keep their lives.
        room = max(0.0, 1 - len(living) / (40 * TURNS_PER_TICK))
        if adults and rng.random() < 0.30 * room:
            parent = rng.choice(adults)
            method = rng.choice(METHODS) if rng.random() < 0.25 else parent.method
            child = Cell(next_id, tick, method)
            living[next_id] = child
            turns.append(next_id)
            parent.children += 1
            events.append(("birth", tick, next_id, parent.id))
            next_id += 1

        for _ in range(min(TURNS_PER_TICK, len(turns))):
            member = turns.popleft()
            turns.append(member)
            cell = living[member]
            cell.turns += 1
            e = episodes[completed % len(episodes)]
            if receipt is None:
                available = {(x, y): z for x, y, z in e["observations"]}
                # The novice requests a point outside the instrument's 0..2 range.
                request = [(3, 3)] if cell.method == "novice" else list(available)
                if all(p in available for p in request):
                    receipt = (member, tuple((x, y, available[x, y]) for x, y in request))
                    cell.readings += 1
                else:
                    cell.rejected += 1
                continue
            reader, observations = receipt
            if member == reader:
                continue
            guess = ([0, 0, 0, 0] if cell.method == "novice" or disable_answers
                     else public_answer(cell.method == "interaction", observations))
            if guess is None or any(lab.instrument(guess, x, y) != z for x, y, z in observations):
                cell.rejected += 1
                continue
            predicted = [lab.instrument(guess, x, y) for x, y in e["score"]["settings"]]
            if predicted != e["score"]["actual"]:
                raise AssertionError("accepted answer failed the private check")
            cell.answers += 1
            completed += 1
            completed_after_reader_died += reader not in living
            receipt = None
    unproductive = [c for c in living.values() if c.born >= 0 and c.rejected and not (c.readings or c.answers)]
    return events, {
        "births": next_id - FOUNDERS, "deaths": sum(e[0] == "death" for e in events),
        "living": len(living), "living_children_with_zero_contributions_and_at_least_one_turn": len(unproductive),
        "of_these_children_that_reproduced": sum(c.children > 0 for c in unproductive),
        "deaths_after_correct_answer": deaths_after_correct_answer, "completed_two_cell_tasks": completed,
        "completed_after_reader_died": completed_after_reader_died,
        "living_newborns_awaiting_first_turn": sum(c.turns == 0 for c in living.values())}


def demographics():
    episodes = notebooks()
    totals = Counter()
    final_sizes = []
    for seed in range(32):
        events, result = population(seed, episodes)
        counterfactual, failed = population(seed, episodes, disable_answers=True)
        if counterfactual != events or failed["completed_two_cell_tasks"]:
            raise AssertionError("changing answer quality affected births or deaths")
        if result["living"] != FOUNDERS + result["births"] - result["deaths"]:
            raise AssertionError("population accounting failed")
        totals.update(result)
        final_sizes.append(result["living"])
    return {"seeds": 32, "ticks_per_seed": TICKS, "founders_per_seed": FOUNDERS,
            "work_turns_per_tick": TURNS_PER_TICK, "identical_demographic_histories": 32,
            "ending_population_range": [min(final_sizes), max(final_sizes)], "totals": dict(totals)}


def live_handoff(args):
    """One scheduled lifespan ends after its receipt. An unsuccessful helper gets another task."""
    if args.out.exists():
        raise ValueError("use a fresh output directory for the live drill")
    args.out.mkdir(parents=True)
    reader, helper, specialist = "t80+g41data", "t80+g41code", "t80+labchild"
    log = []
    retired = set()
    with serving(args.binary, args.base, args.catalog, args.out / "logs", slots=2) as cpu:
        for seed in (331, 332):
            path = args.out / f"affine-{seed}.json"

            class Duty:
                def reply(self, slot, messages):
                    state = json.loads(path.read_text()) if path.exists() else {"turns": [], "observations": []}
                    if seed == 331 and state["observations"] and reader not in retired:
                        # A planned loss in this private drill. The saved measurements survive.
                        retired.add(reader)
                        cpu.close()
                        log.append({"event": "reader lost", "seed": seed, "saved_readings": state["observations"]})
                    if slot == "reader":
                        model = helper if reader in retired else reader
                    else:
                        helper_tried = any(t["cell"] == "interpreter" and t.get("model") == helper for t in state["turns"])
                        model = specialist if seed == 332 or helper_tried else helper
                    if model in retired:
                        raise AssertionError("retired reader was scheduled again")
                    reply = cpu.reply(model, messages)
                    return {**reply, "model": model}

            state = lab.episode(Duty(), path, seed, "affine", "guided", ["reader", "interpreter"])
            log.append({"seed": seed, "score": state["score"],
                        "workers": [{"model": t["model"], "slot": t["cell"], "error": t.get("error"),
                                     "observed": t.get("observed"), "submitted": t.get("submit")}
                                    for t in state["turns"]]})
    lab.save(args.out / "handoff.json", log)
    return log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("binary", "base", "catalog", "out"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if any(vars(args).values()) and not all(vars(args).values()):
        parser.error("the live drill needs --binary, --base, --catalog and --out together")
    result = live_handoff(args) if args.binary else demographics()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
