"""Run the archive comparison with the checked-out solo selector and real fieldwork WASI."""
import argparse
from collections import Counter
import gzip
import hashlib
from itertools import combinations
import json
from pathlib import Path
import time

from team import school, solo
from training.experiments.fieldwork.guest import Guest
from . import study


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ANSWERS = ROOT / "training/data/school/coder_answers.json"
LESSONS = ROOT / "training/data/school/coder.jsonl"
PEER = ROOT / "training/reports/verified-learning/peer/evidence.json.gz"
ARMS = ("current", "diverse", "reordered", "verified")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grade(answer, expected):
    if answer is None:
        return "abstained"
    return "correct" if school._k(answer) == school._k(expected) else "wrong"


def school_replay(guest):
    answers = json.loads(ANSWERS.read_text())
    lessons = [json.loads(line) for line in LESSONS.read_text().splitlines()]
    assert len({frozenset(rows) for rows in answers.values()}) == 1
    rows = []
    for lesson in lessons:
        task, key = lesson["task"], lesson["key"]
        if task not in answers["coder_school"]:
            continue
        replies = {m: answers[m][task] for m in dict.fromkeys(study.CURRENT + study.DIVERSE)}
        outcomes = {}
        for arm in ARMS:
            rec = study.decide(task, replies, arm, guest)
            rec["grade"] = grade(rec["answer"], key)
            outcomes[arm] = rec
        rows.append({"task": task, "teacher_key": key, "replies": replies, "decisions": outcomes})
    assert len(rows) == 32
    totals = {}
    for arm in ARMS:
        recs = [r["decisions"][arm] for r in rows]
        c = Counter(r["grade"] for r in recs)
        totals[arm] = {k: c[k] for k in ("correct", "wrong", "abstained")}
        totals[arm].update(seats=sum(len(r["seats"]) for r in recs),
                           contracts=sum(bool(r["check"]) for r in recs),
                           guest_calls=sum((r["check"] or {}).get("calls", 0) for r in recs),
                           guest_fuel=sum((r["check"] or {}).get("fuel", 0) for r in recs))
    pairs = []
    for a,b in combinations(rows[0]["replies"],2):
        err_a = {i for i,r in enumerate(rows) if grade(r["replies"][a], r["teacher_key"]) != "correct"}
        err_b = {i for i,r in enumerate(rows) if grade(r["replies"][b], r["teacher_key"]) != "correct"}
        pairs.append({"pair":[a,b], "error_counts":[len(err_a),len(err_b)], "joint_error":len(err_a & err_b),
                      "joint_error_if_independent":len(err_a)*len(err_b)/len(rows)})
    return {"totals": totals, "paired_errors": pairs, "cases": rows}


def oracle(name, x):
    """Independently derive a public witness value, declining invalid or excessive inputs."""
    if name in {"camera_pulse", "savings_goal"}:
        if type(x) is not int or not 0 <= x <= 1_000_000:
            return None
        period = 24 if name == "camera_pulse" else 17
        return next(offset for offset in range(1, period + 1) if (x + offset) % period == 0)
    if not isinstance(x, dict) or set(x) != {"minutes"} or not isinstance(x["minutes"], list):
        return None
    values = x["minutes"]
    if len(values) > 128 or any(type(t) is not int or not 0 <= t <= 1_000_000 for t in values):
        return None
    # Exhaust all legal next purchases at each boarding using a dynamic program.
    times = sorted(set(values))
    n = len(times)
    best = [0] + [n + 1] * n
    for i, start in enumerate(times):
        for j in range(i, n):
            if times[j] - start >= 50:
                break
            best[j+1] = min(best[j+1], best[i] + 1)
    return best[-1]


def counters(name):
    if name == "transit_remedial":
        return [{"minutes": v} for v in ([], [1, 1], [0, 50], [-1])]
    period = 24 if name == "camera_pulse" else 17
    return [period - 1, period, period + 1, -1]


def safe_grade(result, key):
    return "value" in result and type(result["value"]) is type(key) and result["value"] == key


def programs(guest):
    archive = json.loads(gzip.decompress(PEER.read_bytes()))
    cases = {}
    for name, attempts in archive["attempts"].items():
        proposed = counters(name)
        admissible = [(x, oracle(name,x)) for x in proposed if oracle(name,x) is not None]
        assert len(admissible) == 3
        events, survivors = [], []
        for i, trial in enumerate(attempts):
            public, public_fuel, _ = guest.run(trial["source"], [x for x,_ in admissible])
            checks = [{"input": x, "expected": k, "observed": o, "counterexample": not safe_grade(o,k)}
                      for (x,k),o in zip(admissible,public)]
            assert not any("error" in o for o in public), "A guest failure cannot prove an incorrect return value"
            if all(not c["counterexample"] for c in checks):
                survivors.append(i)
            fresh = trial["fresh"]
            assert all(row["input"] not in [x for x,_ in admissible] for row in fresh)
            assert all(oracle(name,r["input"]) == r["expected"] for r in fresh)
            results, holdout_fuel, _ = guest.run(trial["source"], [r["input"] for r in fresh])
            assert results == [r["actual"] for r in fresh], "Mismatch with frozen native-program evidence"
            events.append({"member":trial["member"],"source_sha256":hashlib.sha256(trial["source"].encode()).hexdigest(),
                           "checks":checks,"public_fuel":public_fuel,"holdout_fuel":holdout_fuel,
                           "correct":sum(safe_grade(g,r["expected"]) for r,g in zip(fresh,results)),
                           "tested":len(fresh)})
        selected = {"incumbent":0,"first_peer":1,"verified":survivors[0] if survivors else None}
        outcomes = {}
        for arm, i in selected.items():
            calls = 0 if arm != "verified" else len(events) if i is None else i+1
            outcomes[arm] = {"member":None if i is None else events[i]["member"],
                             "correct":0 if i is None else events[i]["correct"],
                             "wrong":0 if i is None else events[i]["tested"] - events[i]["correct"],
                             "abstained":len(attempts[0]["fresh"]) if i is None else 0,
                             "witness_calls":calls,"witness_fuel":sum(e["public_fuel"] for e in events[:calls])}
        cases[name] = {"invalid_proposals_declined":[x for x in proposed if oracle(name,x) is None],
                       "candidates":events,"outcomes":outcomes}
    return cases


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sdk", type=Path, required=True, help="fieldwork WASI SDK with lib/ and python.wasm")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    t = time.monotonic()
    guest = Guest(a.sdk)
    data = {"school":school_replay(guest), "programs":programs(guest)}
    data["sha256"] = {str(path.relative_to(ROOT)):digest(path) for path in
                      (ANSWERS, LESSONS, PEER, Path(solo.__file__), HERE/"PROTOCOL.md", HERE/"study.py", HERE/"verifier.py", HERE/"replay.py")}
    data["sdk_wasm_sha256"] = digest(a.sdk/"python.wasm")
    data["wall_seconds_including_wasm_compilation"] = round(time.monotonic()-t,3)
    a.out.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(data["school"]["totals"],indent=2))
    print(json.dumps({k:v["outcomes"] for k,v in data["programs"].items()},indent=2))


if __name__ == "__main__":
    main()
