"""Train a spawned cell on its member's logged decisions and decide whether it gets the job (team/cells/spawn.py).

    python training/cells_spawn.py <spawned skill> [--steps 300]
Rows are split by time: oldest 70% train, next 15% dev, newest 15% test (decisions newer than any it learned from).
Two edits of the 135M base compete (every module at rank 2 and at rank 8); the better one on dev is kept, and only
if it beats the untouched base there. On dev, each label the cell may answer gets the lowest confidence from which
the cell agreed with the member at least AGREE of the time. On test, with those confidences: how many calls it would
answer, and how often it agrees with the member on them. It gets the job (status "on") only if it agrees on at least
PASS of the calls it answers, answers at least COVERS of all calls, and that is at least MIN_ANSWERED test calls.
A label keeps its confidence only if the test can vouch for it (verified(): enough decisions where the member chose
another label, and at most half the mistakes of answering that label blindly).
Otherwise it is marked "failed" with the numbers, and is tried again only when the log has grown by half.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import learn, runtime, spawn, use  # noqa: E402
from training import cells as C  # noqa: E402

GRID = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99]
AGREE, PASS, COVERS, MIN_ANSWERED, MIN_OTHER = learn.AGREE, learn.AGREE - 0.02, 0.2, 10, 3


def predictions(skill, rows):
    out = []
    for x, y in rows:
        p = runtime.label_probs(skill, x)
        lab, c = max(p.items(), key=lambda kv: kv[1])
        out.append((lab, c, y))
    return out


def thresholds(dev, answers):
    """Per label the cell may answer: the lowest confidence from which it agreed with the member AGREE of the time
    on at least 5 dev decisions; 1.01 (never) when there is none."""
    out = {}
    for lab in answers:
        out[lab] = 1.01
        for g in GRID:
            hit = [y == lab for p, c, y in dev if p == lab and c >= g]
            if len(hit) >= 5 and sum(hit) / len(hit) >= AGREE:
                out[lab] = g
                break
    return out


def verified(test, thr):
    """Confidences the newest real decisions can vouch for. A site where the member says PASS nine times in ten is
    agreed with nine times in ten by a cell that has learned nothing, so a label keeps its confidence only if
    - the test holds at least MIN_OTHER decisions where the member chose another label (else nothing was tested), and
    - the cell, where it answers that label, is wrong at most half as often as answering it blindly would be."""
    out = {}
    for lab, t in thr.items():
        other = sum(y != lab for _, _, y in test)
        hit = [y == lab for p, c, y in test if p == lab and c >= t]
        blind = other / max(1, len(test))
        ok = t <= 1.0 and other >= MIN_OTHER and hit and (1 - sum(hit) / len(hit)) <= blind / 2
        out[lab] = t if ok else 1.01
    return out


def judged(test, thr):
    ans = [(p == y) for p, c, y in test if c >= thr.get(p, 1.01)]
    return {"answered": len(ans), "agree_when_sure": round(sum(ans) / len(ans), 3) if ans else 0.0,
            "covers": round(len(ans) / max(1, len(test)), 3),
            "cell": round(sum(p == y for p, _, y in test) / max(1, len(test)), 3)}


def passes(j):
    return j["agree_when_sure"] >= PASS and j["covers"] >= COVERS and j["answered"] >= MIN_ANSWERED


def grow(skill, steps=300):
    sp = spawn.spawned()[skill]
    tr, dv, te = learn.split(skill)
    n = len(learn.rows(skill))
    n_practice = len(tr) + len(dv) + len(te) - n
    gen = f"sp{n}p{n_practice}"
    print(f"{skill}: {n} real decisions and {n_practice} practice ones ({len(tr)} train, {len(dv)} dev, {len(te)} test)",
          flush=True)
    C.eval_base(skill, "smol135")
    every = [f"{i}:{m}" for i in range(30) for m in C.MODS]
    for tag, rank in (("r2", 2), ("r8", 8)):  # two candidates compete; dev picks
        C.train(skill, "smol135", every, rank=rank, steps=steps, tag=f"{gen}_{tag}")
    from training.cells_promote import promote
    entry = promote(skill, measure=False, prefix=gen)
    stamp = {"rows": n, "tried": time.strftime("%Y-%m-%d %H:%M")}
    if not entry:
        spawn.set_status(skill, "failed", rows_at_fail=n, failed_why="no edit beat the untouched base on dev", **stamp)
        print(f"{skill}: no edit beats the bare base on dev -> the member keeps the job", flush=True)
        return None
    runtime.unload()
    dev_thr = thresholds(predictions(skill, dv), sp["answers"])
    t0 = time.time()
    test = predictions(skill, te)
    ms = (time.time() - t0) / max(1, len(te)) * 1000
    thr = verified(test, dev_thr)
    j = judged(test, thr)
    j["members_labels_in_test"] = {lab: sum(y == lab for _, _, y in test) for lab in sp["labels"]}
    j["thresholds_from_dev"] = dev_thr
    ok = passes(j)
    w = json.loads(use.WINS.read_text()) if use.WINS.exists() else {}
    w[skill] = {"use": ok, "learned": True, "spawned": True, "thresholds": thr, **j, "test_rows": len(te),
                "cell_ms": round(ms, 1), "rows": n, "practice_rows": n_practice, "variant": entry["variant"],
                "incumbent_name": f"{sp['member']} (the teacher)", "incumbent": None,
                "member_seconds_per_call": sp.get("member_seconds_per_call")}
    use.WINS.write_text(json.dumps(w, indent=1))
    runtime.update_registry(skill, {"rows_trained": n})
    if ok:
        spawn.set_status(skill, "on", on_since=time.time(), **stamp)
    else:
        spawn.set_status(skill, "failed", rows_at_fail=n, **stamp,
                         failed_why=f"on the newest {len(te)} decisions it would answer {j['answered']} "
                                    f"({j['covers']:.0%}) and agree on {j['agree_when_sure']:.0%} of them "
                                    f"(needs {COVERS:.0%} answered, at least {MIN_ANSWERED}, {PASS:.0%} agreement)")
    print(f"{skill}: on the newest {len(te)} decisions: agrees with {sp['member']} on {j['cell']:.3f} overall; with "
          f"confidences {thr} it answers {j['answered']} ({j['covers']:.0%}) and agrees on {j['agree_when_sure']:.3f} "
          f"-> {'ON: it takes those calls' if ok else 'FAILED: the member keeps the job'}", flush=True)
    return w[skill]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("skills", nargs="+")
    ap.add_argument("--steps", type=int, default=300)
    a = ap.parse_args()
    for sk in a.skills:
        grow(sk, a.steps)
    runtime.unload()
