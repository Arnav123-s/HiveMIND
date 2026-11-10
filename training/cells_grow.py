"""Grow cells from the hive's own decisions (team/cells/learn.py).

    python training/cells_grow.py [--min 200] [skills...]
For each learned skill whose log holds at least --min decisions and has grown by a quarter since its cell was last
trained: train a cell (every module, rank 2, 300 steps) on the oldest 70%, keep the edit only if dev agreement beats
the bare base, then measure on the newest 15% (decisions newer than any it learned from): agreement with the member,
and from which confidence (chosen on dev) its answers agree at least learn.AGREE of the time, and how many decisions
that confidence covers. Switched on (cells/wins.json) when, on test, the confident answers agree at least
learn.AGREE - 0.02 of the time and cover at least a fifth of the decisions; the member keeps every other decision.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import learn, runtime, skills as S  # noqa: E402
from training import cells as C  # noqa: E402

GRID = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99]


def confident(skill, rows, t):
    got = []
    for x, y in rows:
        p = runtime.label_probs(skill, x)
        lab, c = max(p.items(), key=lambda kv: kv[1])
        got.append((lab == y, c))
    used = [ok for ok, c in got if c >= t]
    return got, (sum(used) / len(used) if used else 0.0), len(used) / max(1, len(got))


def grow(skill, min_rows):
    tr, dv, te = learn.split(skill)
    n = len(tr) + len(dv) + len(te)
    done = runtime.registry().get(skill, {}).get("rows_trained", 0)
    if n < min_rows or (done and n < done * 1.25):
        print(f"{skill}: {n} decisions logged (trained on {done}): not enough new ones yet", flush=True)
        return None
    C.eval_base(skill, "smol135")
    keys = [f"{i}:{m}" for i in range(30) for m in C.MODS]
    C.train(skill, "smol135", keys, rank=2, steps=300, tag=f"grow{n}")
    from training.cells_promote import promote
    if not promote(skill):
        print(f"{skill}: the trained edit does not beat the bare base on dev; not used", flush=True)
        return None
    runtime.update_registry(skill, {"rows_trained": n})
    dev, _, _ = confident(skill, dv, 0.0)
    t = next((g for g in GRID if (lambda u: u and sum(u) / len(u) >= learn.AGREE)([ok for ok, c in dev if c >= g])), 1.01)
    t0 = time.time()
    test, agree, cover = confident(skill, te, t)
    ms = (time.time() - t0) / max(1, len(te)) * 1000
    overall = sum(ok for ok, _ in test) / max(1, len(test))
    use_it = t <= 1.0 and agree >= learn.AGREE - 0.02 and cover >= 0.2
    entry = {"use": use_it, "learned": True, "threshold": t, "cell": round(overall, 3), "agree_when_sure": round(agree, 3),
             "covers": round(cover, 3), "cell_ms": round(ms, 1), "rows": n,
             "incumbent_name": f"{S.LEARNED[skill]['member']} (the teacher)", "incumbent": None}
    w = json.loads((runtime.CELLS / "wins.json").read_text()) if (runtime.CELLS / "wins.json").exists() else {}
    w[skill] = entry
    (runtime.CELLS / "wins.json").write_text(json.dumps(w, indent=1))
    print(f"{skill}: {n} decisions; on the newest {len(te)}: agrees with {S.LEARNED[skill]['member']} {overall:.3f}; "
          f"from confidence {t} it answers {cover:.0%} of them and agrees {agree:.3f} -> {'ON' if use_it else 'off'}",
          flush=True)
    return entry


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("skills", nargs="*")
    ap.add_argument("--min", type=int, default=200)
    a = ap.parse_args()
    for sk in a.skills or list(S.LEARNED):
        grow(sk, a.min)
    runtime.unload()
