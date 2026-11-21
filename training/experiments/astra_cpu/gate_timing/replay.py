"""Replay complete exam receipts under a fixed 20-worker limit without rerunning inference."""
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIMIT = 20
HOLD_BACK = 9  # eight join workers and one spare during overlap with training


@dataclass
class Unit:
    name: str
    parent: str
    ordinals: tuple
    seconds: int
    estimate: float
    phase: int
    before: bool


def slot_count(key):
    part, _, digit = key.split("-")
    return 8 if part == "fresh" else (4 if int(digit) <= 6 else 3)


def phase(key):
    part, _, digit = key.split("-")
    return 0 if part != "fresh" or int(digit) <= 4 else (1 if int(digit) <= 6 else 2)


def build(trace, calibration, split, cold):
    units = []
    for key, row in sorted(trace["seats"].items()):
        part, arm, seat = key.split("-")
        c = calibration["seats"][key]
        values = row.get("seconds", [])
        positions = tuple(range(len(values)))
        # Freeze candidate seats, boundary and priority using G55 only. Full fresh seats and
        # the talk job retain their original execution, artifact upload and smoke test.
        divide = split and part == "held" and arm == "after" and c["elapsed"] > 25*60
        if not divide:
            units.append(Unit(key, key, positions, row["elapsed"], c["elapsed"], phase(key), arm == "before"))
            continue
        if len(positions) != slot_count(key):
            raise ValueError(f"cannot time shards of interrupted original seat {key}")
        assert len(c["seconds"]) == slot_count(key)
        boundary = (len(positions)+1)//2
        for i, ordinals in enumerate((positions[:boundary], positions[boundary:])):
            # Repeat original setup, upload and all exam-step overhead. Any cold-start penalty
            # beyond the launch cost embedded in the original first question is extra on shard two.
            overhead = row["pre"] + row["post"] + max(0, row["residual"])
            predicted = c["elapsed"] - sum(c["seconds"]) + sum(c["seconds"][o] for o in ordinals)
            duration = overhead + sum(values[o] for o in ordinals) + i*cold
            units.append(Unit(f"{key}.{i}", key, ordinals, duration, predicted, 0, False))
    expected = Counter((k,o) for k,r in trace["seats"].items() for o in range(len(r.get("seconds", []))))
    assigned = Counter((u.parent,o) for u in units for o in u.ordinals)
    assert expected == assigned
    return units


def schedule(trace, units, *, early=False, paired=False, gap=10, barrier=0, assemble=0):
    # Baseline time zero is the first recorded gate-job start, after the candidate model was available.
    upstream = trace["upstream"]
    # Incumbent requires only its immutable body. All slices must have started first. A continuing
    # nine-slot reserve lets join and merge retain the original start times with no foreknowledge.
    start = max(s for kind,s,e in upstream if kind == "train") if early else 0
    t, stage = start, 0
    waits, active, done = units.copy(), [], []
    other_events = sorted({x for _,s,e in upstream for x in (s,e) if start <= x < 0} | {0})
    while waits:
        active = [(release,u) for release,u in active if release > t]
        other = sum(s <= t < e for _,s,e in upstream)
        if paired and stage < 2:
            prior = [v for v in done if v[2].phase == stage]
            if prior and not any(u.phase == stage for u in waits) and max(end for _,end,_ in prior) + barrier <= t:
                stage += 1
        capacity = LIMIT - other - len(active)
        if t < 0:
            capacity = min(capacity, LIMIT - HOLD_BACK - len(active))
        choices = [u for u in waits if (u.before or t >= 0) and (not paired or u.phase <= stage)]
        # The scheduler reads prior-generation duration estimates only; actual time appears on completion.
        choices.sort(key=lambda u:(-u.estimate, u.name))
        for u in choices[:max(0, capacity)]:
            waits.remove(u)
            done.append((t, t+u.seconds, u))
            active.append((t+u.seconds+gap, u))
        if waits:
            events = [v for v in other_events if v > t] + [release for release,_ in active if release > t]
            if paired:
                prior = [end for _,end,u in done if u.phase == stage]
                if prior and max(prior)+barrier > t: events.append(max(prior)+barrier)
            assert events, (t, stage, len(waits))
            t = min(events)
    points = {p for s,e,_ in done for p in (s,e)} | {p for _,s,e in upstream for p in (s,e)}
    used = max(sum(s <= p < e for s,e,_ in done) + sum(s <= p < e for _,s,e in upstream) for p in points)
    assert used <= LIMIT
    after_ready = [(s,e,u) for s,e,u in done if s < 0 < e]
    return dict(seconds=max(e for s,e,u in done) + assemble,
                runner_seconds=sum(u.seconds for u in units) + assemble,
                peak=used, before_started_early=sum(s < 0 for s,_,u in done),
                before_running_at_candidate_ready=len(after_ready), jobs=len(units) + int(assemble > 0),
                final_unit=max(done, key=lambda x:x[1])[2].name)


def healthy_tail(trace):
    # Sensitivity only. Remove the delay *after* the final successful slice, preserving join and merge.
    tail = trace["cancelled_slice_tail"]
    train_finish = max(e for k,s,e in trace["upstream"] if k=="train")
    upstream = [[k,s+tail,min(e,train_finish-tail)+tail] if k=="train" else [k,s,e]
                for k,s,e in trace["upstream"]]
    return dict(trace, upstream=upstream)


def report(all_traces):
    calibration = all_traces["g55"]
    result = {}
    for gen, trace in sorted(all_traces.items()):
        plain = build(trace, calibration, False, 0)
        raw = [v["start"] + v["elapsed"] for v in trace["seats"].values()]
        r = result[gen] = dict(actual_seconds=max(raw), paired_net_gains=trace["paired_net_gains"],
            completed_fresh=sum(len(v["seconds"]) for k,v in trace["seats"].items() if k.startswith("fresh")),
            completed_fixed=sum(len(v["seconds"]) for k,v in trace["seats"].items() if k.startswith("held")))
        # Full paired look is comparable only when the historical grades do not cross 8 net discordances.
        if all(abs(net) < 8 for net in trace["paired_net_gains"]):
            r["paired_zero_look_cost"] = schedule(trace, plain, paired=True, gap=0)
        r["ranked"] = schedule(trace, plain)
        r["early_only"] = schedule(trace, plain, early=True)
        r["optimistic_remaining_work_floor"] = max(
            min(u.seconds for u in plain if u.parent == "talk-after-1"),
            (sum(u.seconds for u in plain) -
             sum(max(0, LIMIT-sum(s<=p<e for _,s,e in trace["upstream"])) for p in
                 range(max(s for k,s,e in trace["upstream"] if k == "train"), 0))) / LIMIT)
        try:
            for cold, gap, assemble in [(0,10,0),(60,10,60),(120,30,120)]:
                shards = build(trace, calibration, True, cold)
                r[f"early_split_cold{cold}_gap{gap}"] = schedule(trace, shards, early=True, gap=gap, assemble=assemble)
                if cold == 60:
                    r["split_only"] = schedule(trace, shards, assemble=assemble)
                    if trace["cancelled_slice_tail"]:
                        r["early_split_without_cancellation_tail"] = schedule(healthy_tail(trace), shards,
                            early=True, gap=gap, assemble=assemble)
        except ValueError as exc:
            r["exclusion"] = str(exc)
    return result


if __name__ == "__main__":
    print(json.dumps(report(json.loads((HERE / "traces.json").read_text())), sort_keys=True, indent=2))
