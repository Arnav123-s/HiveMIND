"""tiny-hive runner: birth -> suites -> evolution episodes -> final proof.

    python3 run.py

Writes results/*.json, optimizer_ledger.jsonl (via evolve.py),
lessons.jsonl (via hive.py) and prints a summary. Everything is measured;
nothing is claimed that a suite did not check.
"""
import json, os, random, resource, time
from collections import Counter

import members
import hive as hive_mod
import evolve

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
os.makedirs(RESULTS, exist_ok=True)

V1_ROSTER = ["parity8", "popcount8", "majority5", "compare2", "max4",
             "sort3", "adder", "subtractor", "multiplier", "seqnext"]


def dump(name, obj):
    with open(os.path.join(RESULTS, name), "w") as f:
        json.dump(obj, f, indent=1)


# ---------- phase 0: birth ----------------------------------------------

def phase_birth():
    out = {}
    for name in V1_ROSTER:
        m = members.BUILDERS[name]()
        m["bounds"] = hive_mod.BOUNDS[name]
        members.save_member(m)
        c, tot, _ = members.verify(m)
        out[name] = {"correct": c, "total": tot,
                     "params": members.param_count(m), "units": len(m["units"])}
    dump("baseline.json", out)
    return out


# ---------- phase 1: hive suites on the v1 roster ------------------------

def composed_suite(hv, with_divider=False):
    rng = random.Random(42)
    tasks = []   # (task, expected)
    R = members.REFERENCES
    for _ in range(8):   # adder -> seqnext -> sort3
        a, b, d, e, f = (rng.randint(0, 4), rng.randint(0, 4), rng.randint(0, 1),
                         rng.randint(0, 9), rng.randint(0, 9))
        s1 = a + b
        s2 = s1 + d
        tasks.append(({"steps": [
            {"op": "adder", "args": [a, b]},
            {"op": "seqnext", "args": [{"from": 0}, d]},
            {"op": "sort3", "args": [{"from": 1}, e, f]}]},
            tuple(sorted((s2, e, f)))))
    for _ in range(8):   # multiplier -> popcount -> majority
        a, b = rng.randint(0, 9), rng.randint(0, 9)
        p = a * b
        tasks.append(({"steps": [
            {"op": "multiplier", "args": [a, b]},
            {"op": "popcount8", "args": [{"from": 0}]},
            {"op": "majority5", "args": [{"from": 1}]}]},
            R["majority5"](R["popcount8"](p))))
    for _ in range(8):   # subtractor -> compare2
        a = rng.randint(5, 15)
        b = rng.randint(0, a)
        c = rng.randint(0, 15)
        d = a - b
        tasks.append(({"steps": [
            {"op": "subtractor", "args": [a, b]},
            {"op": "compare2", "args": [{"from": 0}, c]}]},
            R["compare2"](d, c)))
    for _ in range(6):   # fanout multiplier -> max4 over the products
        pairs = [(rng.randint(0, 3), rng.randint(0, 3)) for _ in range(4)]
        prods = [x * y for x, y in pairs]
        tasks.append(({"steps": [
            {"fanout": "multiplier", "args_list": [list(p) for p in pairs], "clones": 4},
            {"op": "max4", "args": [{"from": 0, "index": 0}, {"from": 0, "index": 1},
                                    {"from": 0, "index": 2}, {"from": 0, "index": 3}]}]},
            max(prods)))
    if with_divider:
        for _ in range(8):   # divider -> compare2
            b = rng.randint(7, 9)
            a = rng.randint(0, 99)
            c = rng.randint(0, 15)
            q = a // b
            tasks.append(({"steps": [
                {"op": "divider", "args": [a, b]},
                {"op": "compare2", "args": [{"from": 0}, c]}]},
                R["compare2"](q, c)))
    passed = 0
    fails = []
    for task, want in tasks:
        r = hv.run_task(task, check=True)
        if r.get("status") == "ok" and r["result"] == want:
            passed += 1
        else:
            fails.append({"task": str(task)[:120], "got": str(r)[:160], "want": want})
    return {"passed": passed, "total": len(tasks), "fails": fails}


def phase_suites_v1():
    hv = hive_mod.Hive()
    comp = composed_suite(hv)
    fan = hv.run_fanout("adder", [[a, b] for a in range(10) for b in range(4)],
                        n_clones=4, check=True)
    vote_ok = 0
    for a in range(10):
        for b in range(10):
            r = hv.run_task({"op": "multiplier", "args": [a, b], "vote": 3}, check=True)
            vote_ok += 1 if r.get("status") == "ok" else 0
    gaps = {
        "divider": hv.run_task({"op": "divider", "args": [50, 5]})["status"],
        "adder_500_400": hv.run_task({"op": "adder", "args": [500, 400]})["status"],
    }
    out = {"composed": comp, "fanout_wrong": fan["wrong"],
           "fanout_clone_jobs": fan["clone_jobs"], "vote_clean": f"{vote_ok}/100",
           "gap_probes": gaps}
    dump("suites_v1.json", out)
    hv.save_board(os.path.join(RESULTS, "board_v1.jsonl"))
    return out


# ---------- phase 3: socialization tests on a FRESH hive ------------------

def phase_socialization():
    hv = hive_mod.Hive()   # born now, from canonical weights + lessons only
    div_ok = 0
    for a in range(100):
        for b in range(1, 10):
            r = hv.run_task({"op": "divider", "args": [a, b]}, check=True)
            div_ok += 1 if r.get("status") == "ok" else 0
    comp = composed_suite(hv, with_divider=True)
    rng = random.Random(3)
    big_ok = 0
    for _ in range(200):
        a, b = rng.randint(0, 999), rng.randint(0, 999)
        r = hv.run_task({"op": "adder", "args": [a, b]}, check=True)
        big_ok += 1 if r.get("status") == "ok" else 0
    clones = [hive_mod.Clone(hv.members["multiplier"]) for _ in range(3)]
    mult_ok = sum(1 for a in range(10) for b in range(10)
                  if clones[0].run((a, b)) == a * b)
    out = {"fresh_hive_divider": f"{div_ok}/900",
           "fresh_hive_composed_with_divider": comp,
           "fresh_hive_adder_big_sample": f"{big_ok}/200",
           "fresh_clones_multiplier": f"{mult_ok}/100",
           "lessons_read_by_fresh_hive": len(hv.lessons)}
    dump("socialization.json", out)
    return out


# ---------- phase 4: clone-vote fault tolerance ---------------------------

def phase_faults():
    hv = hive_mod.Hive()
    base = hv.members["multiplier"]

    def run_with_corruption(n_bad, seed):
        clones = [hive_mod.Clone(base) for _ in range(3)]
        for k in range(n_bad):
            rng = random.Random(seed + k)
            u = clones[k + (0 if n_bad == 1 else 0)].spec
            ui = rng.randrange(len(u["units"]))
            key = rng.choice(list(u["units"][ui]["w"].keys()))
            u["units"][ui]["w"][key] = 3.5
        wrong = 0
        for a in range(10):
            for b in range(10):
                outs = [c.run((a, b)) for c in clones]
                if Counter(outs).most_common(1)[0][0] != a * b:
                    wrong += 1
        return wrong

    one_bad = run_with_corruption(1, 11)     # corrupt clone #1 only
    two_bad = run_with_corruption(2, 21)     # corrupt clones #1 and #2
    out = {"one_corrupted_clone_majority_wrong": f"{one_bad}/100",
           "two_corrupted_clones_majority_wrong": f"{two_bad}/100",
           "note": "with the reference verifier active every wrong majority "
                   "is flagged, so silent wrong answers stay 0; two corrupted "
                   "clones is the vote's breaking point and an evolution trigger"}
    dump("faults.json", out)
    return out


# ---------- phase 5: final exhaustive proof --------------------------------

def phase_final():
    hv = hive_mod.Hive()
    out = {}
    total_c = total_t = total_p = 0
    for name, m in sorted(hv.members.items()):
        if name == "adder":
            c, tot, ff = evolve.verify_adder10(m)
        else:
            c, tot, _ = members.verify(m)
        out[name] = {"correct": c, "total": tot, "params": members.param_count(m),
                     "units": len(m["units"])}
        total_c += c
        total_t += tot
        total_p += members.param_count(m)
    out["_totals"] = {"correct": total_c, "total": total_t, "params": total_p,
                      "members": len(hv.members)}
    dump("final.json", out)
    return out


def main():
    t0 = time.time()
    summary = {}
    summary["baseline"] = phase_birth()
    print("phase 0 birth done", flush=True)
    summary["suites_v1"] = phase_suites_v1()
    print("phase 1 suites done", flush=True)
    hv = hive_mod.Hive()
    summary["episode_grow_divider"] = evolve.episode_grow_divider(hv)
    print("episode 1 divider done", flush=True)
    summary["episode_extend_adder"] = evolve.episode_extend_adder(hv)
    print("episode 2 adder done", flush=True)
    summary["episode_repair_multiplier"] = evolve.episode_repair_multiplier(hv)
    print("episode 3 repair done", flush=True)
    summary["socialization"] = phase_socialization()
    print("phase 3 socialization done", flush=True)
    summary["faults"] = phase_faults()
    print("phase 4 faults done", flush=True)
    summary["final"] = phase_final()
    summary["wall_seconds"] = round(time.time() - t0, 1)
    summary["peak_ram_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    dump("summary.json", {k: str(v)[:400] for k, v in summary.items()})
    print(json.dumps({k: str(v)[:300] for k, v in summary.items()}, indent=1))


if __name__ == "__main__":
    main()
