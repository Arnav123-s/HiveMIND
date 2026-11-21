"""Evaluate the live replay scheduler on the same model-free G55/G56 preference measure as PR 132.

Pass --measure pointing at the immutable replay.py from commit 7fb2786 in PR 132. Its checksum
locks the old preference model and reporting code; selection, scheduling and held-back filtering come from this tree.
"""
import argparse
from hashlib import sha256
from types import ModuleType
import json
from pathlib import Path
import random

from team import ternary
from training import grow, self_replay


def run(measure, old, new, budget):
    if sha256(measure.read_bytes()).hexdigest() != "86f3d33c55f3f8d7aee78934596a6cb0c8dd7b58c1a17e6a9250bb54ecf4fc33":
        raise ValueError("unexpected PR 132 measurement source")
    m = ModuleType("pr132_measure")
    # The historical code locates the repository relative to its own path, even if a user extracted it to /tmp.
    m.__file__ = str(Path(__file__).with_name("pr132_measure.py"))
    exec(compile(measure.read_bytes(), str(measure), "exec"), m.__dict__)
    body = json.loads(ternary.BODY.read_text())
    if body["generation"] != 55:
        raise ValueError("run this at the G55 checkout")
    history, current = ([json.loads(x) for x in path.read_text().splitlines() if x.strip()] for path in (old, new))
    fresh = [r for r in current if r.get("gen") == "g56"]
    excluded = {self_replay.question(r.get("task")) for r in fresh}
    excluded.update(self_replay.question(task) for tasks in grow.kept_back(current).values() for task in tasks)
    answers = {m.code(r[k]) for rows in (m.partition(history), m.partition(fresh))
               for r in rows for k in ("output", "rejected")}
    def clean(r):
        return (int(m.fingerprint(m.question(r)), 16) % 4 != 0 and m.code(r["output"]) not in answers)
    selected = [history[i] for i in sorted(self_replay.select(history, body, "t80", "g56", excluded))]
    selected = sorted((r for r in selected if clean(r)), key=m.identity)

    # Keep the prior study's data splits, frozen question classifier, byte model and exact evaluation.
    # Replace its reversed repeat-old schedule; unavailable rows and per-row caps follow the real Study.
    def schedule(new_rows, old_rows, ratio):
        new_rows = [r for r in new_rows if clean(r) and self_replay.question(r["task"]) not in held]
        old_rows[:] = selected
        rows = [*new_rows, *(old_rows if ratio else [])]
        new_subjects, replay_subjects, groups, tags = set(), set(), {}, []
        for i, r in enumerate(rows):
            tag = grow.subject(r, i < len(new_rows))
            if i < len(new_rows):
                new_subjects.add(tag)
            else:
                tag += " · self-replay"
                replay_subjects.add(tag)
            tags.append(tag)
            groups.setdefault(tag, []).append(i)
        hard, web = grow.new_hard(groups)
        study = grow.Study(groups, rng=random.Random(42), hard=hard, web=web)
        mixer = self_replay.Schedule(ratio, tags, replay_subjects, new_subjects) if ratio else None
        out = []
        while len(out) < 120:
            pick = mixer.pick(study) if mixer else study.pick()
            if not pick:
                break
            tag, i = pick
            study.learned(tag, 1.0)  # No 8B loss exists for the archived proxy.
            if mixer:
                mixer.learned(tag, i, len(m.code(rows[i]["output"]).encode()))
            out.append(rows[i])
        return out
    held = {self_replay.question(t) for ts in grow.kept_back(current).values() for t in ts}
    m.schedule = schedule
    result = m.main(old, new, budget)
    keep = ("g55_sha256", "g56_sha256", "target_byte_limit", "old_eval_questions_excluded_from_new")
    out = {k: result[k] for k in keep}
    out["eligible_live_replay_questions"] = len(selected)
    out["arms"] = {k: {"exposure": v["exposure"], "scores": {
        s: [w["correct"], w["pairs"]] for s, w in v["slices"].items()}} for k, v in result["results"].items()}
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("measure", "g55", "g56"):
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument("--budget", type=int, default=30000)
    a = p.parse_args()
    print(json.dumps(run(a.measure, a.g55, a.g56, a.budget), indent=2))
