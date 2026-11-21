"""Run the frozen three-transition preference study. Inputs are the four original all-rows JSONL files."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import pickle
import random
import re
import tempfile
from types import ModuleType
from zipfile import ZipFile

from training import grow, self_replay
from training.body_archive import ROOT

SEEDS = (17, 42, 91)
ARMS = ("fresh", "live-2", "live-4", "stream-row-2", "stream-row-4", "stream-byte-2", "stream-byte-4")
BUDGET = 30_000


def measure(path):
    source = path.read_bytes()
    if sha256(source).hexdigest() != "86f3d33c55f3f8d7aee78934596a6cb0c8dd7b58c1a17e6a9250bb54ecf4fc33":
        raise ValueError("wrong PR 132 measuring code")
    m = ModuleType("pr132_measure")
    m.__file__ = str(ROOT / "training/experiments/replay_archive/pr132_measure.py")
    exec(compile(source, str(path), "exec"), m.__dict__)
    return m


def key(m, row):
    return m.fingerprint(m.question(row)) + m.fingerprint(m.code(row["output"]))


def partition(m, row):
    return int(m.fingerprint(m.question(row)), 16) % 4 == 1


def pairs(m, rows):
    """One immutable pair per request. The choice among pairs is blind to which program won."""
    selected = {}
    for r in rows:
        if r.get("type") != "pair" or not partition(m, r):
            continue
        q = m.question(r)
        a, b = (m.code(r.get(k, "")) for k in ("output", "rejected"))
        if not a or not b or a == b:
            continue
        h = m.fingerprint(json.dumps(sorted((a, b)), ensure_ascii=False))
        if q not in selected or h < selected[q][0]:
            selected[q] = (h, (q, a, b))
    return [item for _, item in sorted(selected.values())]


def prior_body(records, gen):
    i = max(n for n, row in records.items() if n < gen and row["kept"])
    row = records[i]
    return {"dna": "t80", "generation": i, "cells": row["body_after"], "trunk": row["trunk"]}


def sources(m, gen, history, current, records, reserved_programs):
    b = prior_body(records, gen)
    actors = {b["dna"] + "+" + x for x in [*b["cells"], b["trunk"]]}
    fresh = [r for r in current if r.get("gen") == f"g{gen}"]
    held = {self_replay.question(t) for tasks in grow.kept_back(current).values() for t in tasks}
    fresh_q = {m.question(r) for r in fresh}

    def eligible(row, excluded):
        return (
            row.get("type") in ("first", "fix")
            and row.get("kind")
            and m.question(row) not in excluded
            and not partition(m, row)
            and m.code(row["output"]) not in reserved_programs
        )

    def positives(rows, excluded):
        pool = [
            r
            for r in rows
            if eligible(r, excluded) and (r.get("who") == "lesson" or (m.usable(r) and r.get("who") in actors))
        ]
        return sorted(m.unique(pool, lambda r: key(m, r)), key=lambda r: key(m, r))

    if gen == 54:
        historical_held = {self_replay.question(t) for tasks in grow.kept_back(history).values() for t in tasks}
        base = positives(history, historical_held)
    else:
        base = []
    indices = self_replay.select(history, b, "t80", f"g{gen}", fresh_q | held)
    replay = sorted((history[i] for i in indices if eligible(history[i], held)), key=lambda r: key(m, r))
    return base, positives(fresh, held), replay


def study(rows, labels, seed):
    groups = defaultdict(list)
    for i, tag in enumerate(labels):
        groups[tag].append(i)
    hard, web = grow.new_hard(groups)
    return grow.Study(groups, rng=random.Random(seed), hard=hard, web=web)


def plan(m, fresh, old, arm, seed):
    ratio = int(arm[-1]) if arm != "fresh" else 0
    fn = [grow.subject(r, True) for r in fresh]
    on = [grow.subject(r) + " · self-replay" for r in old]
    joint = study(fresh + old, fn + on, seed)
    live = self_replay.Schedule(ratio, fn + on, on, fn)
    new_study = study(fresh, fn, seed)
    old_study = study(old, on, f"old-{seed}")
    completed, used, indices = Counter(), Counter(), {"old": set(), "fresh": set()}
    targets = []
    all_rows = fresh + old
    while sum(used.values()) < BUDGET:
        if arm.startswith("live"):
            got = live.pick(joint)
            if not got:
                raise ValueError("mixed pool exhausted")
            tag, i = got
            chosen = "fresh" if i < len(fresh) else "old"
            row = all_rows[i]
            joint.learned(tag, 1)
            live.learned(tag, i, len(m.code(row["output"]).encode()))
        else:
            old_due = completed["fresh"] >= ratio * (1 + completed["old"]) if ratio else False
            if arm.startswith("stream-byte"):
                old_due = used["fresh"] > ratio * used["old"]
            chosen = "old" if old_due and old else "fresh"
            sampler = old_study if chosen == "old" else new_study
            got = sampler.pick()
            if got is None:
                chosen = "fresh" if chosen == "old" else "old"
                sampler = new_study if chosen == "fresh" else old_study
                got = sampler.pick() if ratio else None
            if not got:
                raise ValueError("training budget exceeds available source passes")
            tag, i = got
            sampler.learned(tag, 1)
            row = (fresh if chosen == "fresh" else old)[i]
        program = m.code(row["output"]).encode()
        target = program[: BUDGET - sum(used.values())]
        targets.append((row, target))
        indices[chosen].add(key(m, row))
        used[chosen] += len(target)
        completed[chosen] += 1
    return targets, dict(
        fresh_bytes=used["fresh"],
        old_bytes=used["old"],
        fresh_rows=completed["fresh"],
        old_rows=completed["old"],
        distinct_fresh=len(indices["fresh"]),
        distinct_old=len(indices["old"]),
    )


def archive_pairs(m, manifest, paths):
    """Only a uniquely identified, individually checked single script with logged matching output supplies a grade."""
    pairs_by_gen, reasons = {}, Counter()
    checked = defaultdict(lambda: defaultdict(set))
    for src in manifest:
        gen = int(src["generation"][1:])
        if gen not in (50, 51, 52, 54, 55, 56):
            continue
        f = paths.get(src["id"])
        if not f:
            reasons["archive absent"] += 1
            continue
        if sha256(f.read_bytes()).hexdigest() != src["sha256"]:
            raise ValueError(f"incorrect archive {src['id']}")
        with ZipFile(f) as z:
            names = set(z.namelist())
            for n in sorted(names):
                if not re.fullmatch(r"[^/]+/[^/]+/exam.json", n):
                    continue
                h = n.removesuffix("exam.json")
                if h + "members/TASK.md" not in names or h + "members/events.jsonl" not in names:
                    continue
                q = self_replay.question(z.read(h + "members/TASK.md").decode())
                events = [json.loads(line) for line in z.read(h + "members/events.jsonl").splitlines()]
                seats = []
                for event in events:
                    if event["agent"] == "hive" and event["kind"] == "seats":
                        seats = event["msg"].partition(": ")[2].split(", ")
                        break
                    if re.fullmatch(r"member\d+", event["agent"]):
                        break
                grades = json.loads(z.read(n))["members"]
                for v in grades:
                    i, actor = v.get("member"), v.get("who")
                    if (
                        type(i) != int
                        or not 1 <= i <= len(seats)
                        or actor != seats[i - 1]
                        or type(v.get("ok")) != bool
                    ):
                        continue
                    if sum(w.get("member") == i for w in grades) != 1:
                        continue
                    folder = h + ("members/work/" if i == 1 else f"members/member{i}/")
                    scripts = sorted(
                        p for p in names if re.fullmatch(re.escape(folder) + rf"member{i}_\d+\.py", p)
                    )
                    if len(scripts) != 1:
                        reasons["multiple or absent scripts"] += 1
                        continue
                    (p,) = scripts
                    output = folder + "." + p.split("/")[-1] + ".out"
                    if output not in names:
                        reasons["missing stdout"] += 1
                        continue
                    answer = [e["msg"] for e in events if e["agent"] == f"member{i}" and e["kind"] == "answer"]
                    stdout = z.read(output).decode(errors="replace").strip()
                    if len(answer) != 1 or not stdout or answer[0] != stdout[:300] or answer[0] == "no answer":
                        reasons["unmatched stdout"] += 1
                        continue
                    checked[(gen, q)][z.read(p).decode(errors="replace").strip()].add(v["ok"])
    for (gen, q), units in checked.items():
        positive = sorted(program for program, grades in units.items() if grades == {True})
        negative = sorted(program for program, grades in units.items() if grades == {False})
        if not positive or not negative:
            continue
        options = [(m.fingerprint(json.dumps(sorted([a, b]))), a, b) for a in positive for b in negative]
        _, a, b = min(options)
        pairs_by_gen.setdefault(gen, []).append((q, a, b))
    return pairs_by_gen, dict(reasons)


def turns(before, after):
    return dict(
        correct=sum(after),
        questions=len(after),
        gained=sum(b and not a for a, b in zip(before, after)),
        lost=sum(a and not b for a, b in zip(before, after)),
    )


def run(args):
    m = measure(args.measure)
    data, inputs = {}, {}
    for gen in range(53, 57):
        p = args.rows / f"g{gen}-rows.jsonl"
        inputs[str(gen)] = sha256(p.read_bytes()).hexdigest()
        data[gen] = [json.loads(r) for r in p.read_text().splitlines() if r]
        if any(self_replay.generation(r.get("gen")) > gen for r in data[gen]):
            raise ValueError("input contains rows collected in a later generation")
    records = {
        int(r["generation"][1:]): r
        for r in map(json.loads, (ROOT / "training/reports/generations.jsonl").read_text().splitlines())
    }
    old_panel = pairs(m, data[53])
    reserved_programs = {s for _, a, b in old_panel for s in (a, b)}
    recent, supplies, seen_tasks, seen_programs, stages = {}, {}, set(), set(), {}
    for gen in range(54, 57):
        base, fresh, old = sources(m, gen, data[gen - 1], data[gen], records, reserved_programs)
        if gen == 54:
            initial = base
        stages[gen] = (fresh, old)
        seen_tasks.update(m.question(r) for r in base + fresh + old)
        seen_programs.update(m.code(r["output"]) for r in base + fresh + old)
        history_q = {m.question(r) for r in data[gen - 1]}
        recent[gen] = [
            (q, a, b)
            for q, a, b in pairs(m, [r for r in data[gen] if r.get("gen") == f"g{gen}"])
            if q not in history_q and a not in seen_programs and b not in seen_programs
        ]
        supplies[gen] = dict(fresh=len(fresh), old=len(old), source_kept=prior_body(records, gen)["generation"])
    initial_counts = m.Counts()
    for r in initial:
        initial_counts.add(r, 120 / len(initial))
    router = m.Router(initial)
    training, scores = {}, {}
    with tempfile.TemporaryDirectory() as tmp:
        for arm in ARMS:
            for seed in SEEDS:
                saved = []
                for gen, (fresh, old) in stages.items():
                    added, stats = plan(m, fresh, old, arm, seed)
                    training[(arm, seed, gen)] = stats
                    path = saved + added
                    for fade in (1.0, 0.98):
                        delta = m.Counts()
                        for i, (r, target) in enumerate(path):
                            delta.add(r, fade ** (len(path) - i - 1), target)
                        state = Path(tmp) / f"{arm}-{seed}-{gen}-{fade}"
                        with state.open("wb") as f:
                            pickle.dump((len(path), delta.next, delta.prev), f)
                    if records[gen]["kept"]:
                        saved = path
        manifest = json.loads(args.manifest.read_text())
        lookup = {
            int(p.stem[len("minority-") :]): p
            for p in args.attachments.glob("*/minority-*.zip")
            if p.stem[len("minority-") :].isdigit()
        }
        for cache in args.cache:
            lookup.update({int(p.stem): p for p in cache.glob("*.zip") if p.stem.isdigit()})
        # Some earlier downloads used the raw artifact ID as the filename.
        for p in args.attachments.glob("*/*.zip"):
            if p.stem.isdigit():
                lookup[int(p.stem)] = p
        sec, omissions = archive_pairs(m, manifest, lookup)
        independent = {}
        for gen, items in sec.items():
            unique = {
                q: (q, a, b)
                for q, a, b in sorted(items)
                if q not in seen_tasks and a not in seen_programs and b not in seen_programs
            }
            independent[gen] = list(unique.values())
        old_independent = {}

        def blind_key(item):
            return m.fingerprint(json.dumps(sorted(item[1:])))

        for gen in (50, 51, 52):
            for item in independent.get(gen, []):
                q = item[0]
                if q not in old_independent or blind_key(item) < blind_key(old_independent[q]):
                    old_independent[q] = item
        earlier_independent = set(old_independent)
        new_independent = {}
        for gen in stages:
            new_independent[gen] = [p for p in independent.get(gen, []) if p[0] not in earlier_independent]
            earlier_independent.update(p[0] for p in independent.get(gen, []))
        # Independently recalculate task kind from request text only, then evaluate each already fitted state.
        names = ["practice_old", "practice_new", "independent_old", "independent_new"]

        def predictions(panel, delta, weight):
            return [
                m.log_likelihood(a, k, initial_counts, weight, delta)
                > m.log_likelihood(b, k, initial_counts, weight, delta)
                for a, b, k in panel
            ]

        accepted_answers = {}
        for gen in stages:
            panels = [old_panel, recent[gen], list(old_independent.values()), new_independent[gen]]
            encoded = {
                name: [(a, b, router.predict(q)) for q, a, b in rows] for name, rows in zip(names, panels)
            }
            frozen = {name: predictions(panel, m.Counts(), 1.0) for name, panel in encoded.items()}
            for arm in ARMS:
                for seed in SEEDS:
                    for fade in (1.0, 0.98):
                        state = Path(tmp) / f"{arm}-{seed}-{gen}-{fade}"
                        with state.open("rb") as f:
                            steps, count, context = pickle.load(f)
                        delta = m.Counts()
                        delta.next, delta.prev = count, context
                        metrics = {}
                        for name, panel in encoded.items():
                            output = predictions(panel, delta, fade**steps)
                            metrics[name] = turns(frozen[name], output)
                            if name.endswith("_old"):
                                actor = (arm, seed, fade, name)
                                parent = accepted_answers.get(actor, frozen[name])
                                metrics[name]["from_kept_parent"] = turns(parent, output)
                                if records[gen]["kept"]:
                                    accepted_answers[actor] = output
                        scores[f"{gen}/{arm}/{seed}/{fade}"] = metrics
    return dict(
        inputs=inputs,
        old_fixed_questions=len(old_panel),
        supplies=supplies,
        missing_receipts=omissions,
        decisions={g: records[g]["kept"] for g in stages},
        scores=scores,
        training={"/".join(map(str, k)): v for k, v in training.items()},
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("measure", "rows", "manifest", "attachments", "out"):
        p.add_argument("--" + arg, type=Path, required=True)
    p.add_argument("--cache", type=Path, action="append", default=[])
    args = p.parse_args()
    args.out.write_text(json.dumps(run(args), sort_keys=True, separators=(",", ":")) + "\n")
