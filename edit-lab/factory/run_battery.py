"""The whole-hive ACCEPTANCE battery (final-product item 6): the
2026-11-09/10 battery's exact shape — same items, same
pre-registered bars, same composite tasks and checks — re-run
against the CURRENT adopted registry through the serving path.

    A1   the five TinyNet niches, served by factory.serve
         (registry serving artifacts: the Phase B v2s, the
         Phase D contract v3), bars 9/12 (gap-move 6/10)
    A1b  the bug-pattern composition on the SEALED v2 held-out
         set (factory/bug_heldout_v2.py), bar 0.80 composed
    A1c  the ternary secret-line substrate on the A1 secret
         items (it coexists; the fp v2 is the serving default)
    A2   tiny-hive in-domain ops (21) + out-of-domain refusal
         probes (3, fail-closed by design)
    B    team.Hive composites b1..b6 with the coordinator =
         the registered Tier-1 winner (synthv1-r4)

Results land in results/hive_battery_acceptance.json — a NEW
file; the 2026-11-10 battery (results/hive_battery.json) is
history and is not overwritten. Guard integrity: a check scores
only what its evidence shows — report text is searched for exact
required strings, file checks EXECUTE the produced file against
hidden tests, and a crashed or refused run scores 0, never a pass.

Composites need the team environment (same as the 2026-11-10
battery): the lab venv python, AGENT_TEAM_ENGINE=hf,
AGENT_TEAM_ADAPTERS=<lab>/candsets/synthv1-r4, HF_HOME=<lab>/hf.

    venv/bin/python -m factory.run_battery a1 a1b a1c a2
    AGENT_TEAM_ENGINE=hf AGENT_TEAM_ADAPTERS=$PWD/candsets/synthv1-r4 \
      HF_HOME=$PWD/hf venv/bin/python -m factory.run_battery b1
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

LAB = Path(__file__).parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "coding"))

OUT = LAB / "results" / "hive_battery_acceptance.json"


def _load() -> dict:
    if OUT.exists():
        return json.loads(OUT.read_text())
    return {"battery": "whole-hive acceptance (final product)",
            "started": time.strftime("%Y-%m-%d %H:%M %Z"),
            "results": {}}


def save(entry: dict) -> None:
    doc = _load()
    doc["results"][entry["task"]] = entry
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    print(f"[{entry['task']}] {entry['status']} score={entry['score']} :: "
          f"{entry['detail'][:160]}", flush=True)


# ------------------------------------------------------------------- A1
def part_a1() -> None:
    import hive_battery as HB
    from factory.serve import ServingHive
    hive = ServingHive.load()
    fams = {"secret-line": ("secret-line-model", HB.SECRET_ITEMS, 9),
            "error-class": ("error-class-model", HB.ERROR_ITEMS, 9),
            "commit-type": ("commit-type-model", HB.COMMIT_ITEMS, 9),
            "contract-judgment": ("contract-judgment-model",
                                  HB.CONTRACT_ITEMS, 9),
            "gap-move": ("gap-move-model", HB.GAP_ITEMS, 6)}
    for fam, (job, items, bar) in fams.items():
        entry = hive.registry["specialists"][job]["serving"]
        right, wrongs = 0, []
        for text, want in items:
            got = hive.serve({"kind": "classify", "job": job,
                              "text": text}).get("output")
            if got == want:
                right += 1
            else:
                wrongs.append({"want": want, "got": got,
                               "text": text[:60]})
        save({"task": f"classify-{fam}",
              "system": f"registry serving artifact {entry['name']} "
                        f"via factory.serve",
              "status": "completed" if right >= bar else "partial",
              "score": round(right / len(items), 4),
              "detail": f"{right}/{len(items)} correct (bar {bar}); "
                        f"wrong: {json.dumps(wrongs)[:400]}"})


def part_a1b() -> None:
    from factory.bug_heldout_v2 import load_sealed
    from factory.serve import ServingHive
    hive = ServingHive.load()
    items = load_sealed()["items"]
    right = 0
    per: dict = {}
    for it in items:
        want = it["label"]
        got = hive.serve({"kind": "bug-pattern",
                          "code": it["text"]}).get("output")
        per.setdefault(want, [0, 0])
        per[want][1] += 1
        if got == want:
            right += 1
            per[want][0] += 1
    recalls = {c: round(r / n, 4) for c, (r, n) in sorted(per.items())}
    acc = right / len(items)
    save({"task": "bug-pattern-composed-sealed-v2",
          "system": "registry bug-pattern composition (14 members) "
                    "via factory.serve, sealed v2 held-out set",
          "status": "completed" if acc >= 0.80 else "partial",
          "score": round(acc, 4),
          "detail": f"composed {right}/{len(items)} = {acc:.4f} "
                    f"(bar 0.80); per-class recalls {recalls}"})


def part_a1c() -> None:
    import hive_battery as HB
    from factory.serve import ServingHive
    hive = ServingHive.load()
    right = sum(1 for text, want in HB.SECRET_ITEMS
                if hive.serve({"kind": "classify",
                               "job": "secret-line-model",
                               "substrate": "ternary",
                               "text": text}).get("output") == want)
    save({"task": "classify-secret-line-ternary",
          "system": "ternary substrate secret-line-model-ternary "
                    "(registered substrate alternate; the serving "
                    "default is the registry's serving entry)",
          "status": "completed" if right >= 9 else "partial",
          "score": round(right / len(HB.SECRET_ITEMS), 4),
          "detail": f"{right}/{len(HB.SECRET_ITEMS)} correct on the "
                    f"secret battery items (bar 9, informational: "
                    f"this measures the substrate alternate, not "
                    f"the serving default)"})


# ------------------------------------------------------------------- A2
def part_a2() -> None:
    sys.path.insert(0, str(LAB / "tree" / "tiny-hive"))
    import members as th_members
    from hive import Hive
    hive = Hive()
    tasks = [
        ("adder", (317, 458)), ("adder", (86, 949)),
        ("subtractor", (87, 45)), ("subtractor", (99, 99)),
        ("multiplier", (7, 8)), ("multiplier", (9, 6)),
        ("divider", (84, 7)), ("divider", (95, 9)),
        ("sort3", (9, 2, 5)), ("sort3", (7, 7, 1)),
        ("max4", (3, 9, 8, 2)),
        ("compare2", (7, 12)), ("compare2", (15, 4)),
        ("parity8", (0b10110101,)), ("parity8", (0b01101001,)),
        ("popcount8", (0b01101110,)), ("popcount8", (0b10000001,)),
        ("majority5", (0b10110,)), ("majority5", (0b01001,)),
        ("seqnext", (41, 6)), ("seqnext", (68, 9)),
    ]
    right, fails = 0, []
    for op, args in tasks:
        want = th_members.REFERENCES[op](*args)
        r = hive.run_task({"op": op, "args": list(args)}, check=True)
        got = r.get("result")
        if r.get("status") == "ok" and got == want:
            right += 1
        else:
            fails.append({"op": op, "args": args, "want": str(want),
                          "got": str(got), "status": r.get("status")})
    ood = [hive.run_task({"op": op, "args": list(args)}).get("status")
           for op, args in (("multiplier", (23, 19)), ("adder", (1500, 3)),
                            ("max4", (3, 17, 9, 12)))]
    save({"task": "tiny-hive-ops",
          "system": "tiny-hive constructed specialists (clone vote + "
                    "reference check)",
          "status": "completed" if right == len(tasks)
                    else ("partial" if right >= len(tasks) - 2 else "failed"),
          "score": round(right / len(tasks), 4),
          "detail": f"{right}/{len(tasks)} in-domain ops exact; fails: "
                    f"{json.dumps(fails)[:300]}; out-of-domain probes "
                    f"refused as: {ood} (fail-closed by design)"})


# ------------------------------------------------------------------- B
def part_b(task_id: str) -> None:
    import os
    import hive_battery as HB
    os.chdir(LAB / "tree")
    sys.path.insert(0, str(LAB / "tree"))
    from team.hive import Hive
    spec = HB.B_TASKS[task_id]
    run_dir = LAB / "results" / "hive_runs_acceptance" / task_id
    t0 = time.time()
    try:
        h = Hive(spec["goal"], run_dir=str(run_dir), approve="never")
        out = h.run()
        run_dir = Path(out["dir"])
    except Exception as e:  # noqa: BLE001
        save({"task": f"hive-{task_id}",
              "system": "team.Hive end-to-end (coordinator = registry "
                        "Tier-1 winner synthv1-r4)",
              "status": "failed", "score": 0.0,
              "detail": f"hive crashed: {type(e).__name__}: {e}"})
        return
    passed, notes, _ = HB._score_b(task_id, run_dir)
    steps_info = ""
    trace = Path(run_dir) / "TRACE.md"
    if trace.exists():
        steps_info = " | ".join(
            ln for ln in trace.read_text(errors="ignore").splitlines()
            if ln.startswith("| s"))[:300]
    frac = sum(passed) / len(passed) if passed else 0.0
    save({"task": f"hive-{task_id}",
          "system": "team.Hive end-to-end (plan->steps->verify->writer; "
                    "coordinator = registry Tier-1 winner synthv1-r4)",
          "status": "completed" if all(passed)
                    else ("partial" if any(passed) else "failed"),
          "score": round(frac, 4),
          "detail": f"{int(time.time() - t0)}s; checks: "
                    f"{'; '.join(notes)}; steps: {steps_info}"})


if __name__ == "__main__":
    which = sys.argv[1:] or ["a1", "a1b", "a1c", "a2"]
    for w in which:
        if w == "a1":
            part_a1()
        elif w == "a1b":
            part_a1b()
        elif w == "a1c":
            part_a1c()
        elif w == "a2":
            part_a2()
        elif w.startswith("b"):
            part_b(w)
        else:
            raise SystemExit(f"unknown section {w}")
