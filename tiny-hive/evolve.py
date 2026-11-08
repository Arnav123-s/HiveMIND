"""tiny-hive evolution: the optimizer at work.

Failure is not a stop. When the hive meets something it cannot do, or a
member degrades, this module is the response:
  diagnose  - find exactly which units are responsible, from behaviour
  vary      - clone the member and change it: surgical unit edits first,
              architecture growth when the shape itself is the limit,
              perturbation search as the fallback
  select    - keep only strict improvements, measured on the FULL domain
  socialize - the winning weights become canonical (every future clone is
              born knowing them) and a lesson is written to the shared
              board-lessons file every run reads

Every event is appended to optimizer_ledger.jsonl.
"""
import copy, json, os, random, time

import members
import hive as hive_mod

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(HERE, "optimizer_ledger.jsonl")


def ledger(episode, member, action, before, after, kept, note=""):
    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "episode": episode,
            "member": member, "action": action, "before": before,
            "after": after, "kept": kept, "note": note}) + "\n")


def forward_trace(m, x):
    vals = list(x)
    for u in m["units"]:
        s = u["b"]
        for i, w in u["w"].items():
            s += w * vals[int(i)]
        vals.append(s if u["act"] == "lin" else (s if s > 0.0 else 0.0))
    return vals


# ---------- episode 1: grow a divider by composition ---------------------

def episode_grow_divider(hv):
    probes = [(50, 5), (99, 9), (7, 3)]
    gaps = sum(1 for a, b in probes
               if hv.run_task({"op": "divider", "args": [a, b]})["status"] == "capability_gap")
    ledger("grow_divider", "divider", "probe: division tasks arrive", 
           f"{gaps}/{len(probes)} capability_gap", None, None,
           "hive declares the gap; it does not guess")
    m = members.build_divider()
    m["bounds"] = [(0, 99), (1, 9)]
    c, tot, fails = members.verify(m)
    ledger("grow_divider", "divider",
           "grew a new member by composition: q = sum_k [k*b <= a], "
           "each test one threshold unit over the bit inputs",
           "no member", f"{c}/{tot} exhaustive", c == tot)
    if c == tot:
        members.save_member(m)
        hive_mod.add_lesson("divider",
                            "Division arrived with no member. Grew 'divider' by "
                            "composition (threshold indicators over k*b <= a). "
                            "Verified 900/900 exhaustive before joining the hive.")
    return c, tot


# ---------- episode 2: extend the adder's architecture -------------------

def _stage(bd, a_s, b_s, carry):
    p = bd.parity2(a_s, b_s)
    if carry is None:
        s = p
        carry = bd.relu({a_s: 1.0, b_s: 1.0}, -1.0)
    else:
        s = bd.parity2(p, carry)
        carry = bd.majority3(a_s, b_s, carry)
    return s, carry

def extend_adder():
    """v1 adder speaks 7-bit inputs (domain 0..99). Grow it to 10 bits:
    the original 7 stages keep their exact weights (signal-remapped);
    3 new stages are appended. Domain becomes 0..999."""
    v1 = members.build_adder()
    SHIFT = 6  # unit signals move from base 14 to base 20
    units = []
    for u in v1["units"]:
        units.append({"w": {(k + SHIFT if k >= 14 else k): v
                            for k, v in u["w"].items()},
                      "b": u["b"], "act": u["act"]})
    outputs = [o + SHIFT if o >= 14 else o for o in v1["outputs"]]
    bd = members.Builder(20)
    bd.units = units
    bd.next_sig = 20 + len(units)
    a_sig = lambda i: i if i < 7 else 14 + (i - 7)
    b_sig = lambda i: 7 + i if i < 7 else 17 + (i - 7)
    carry = outputs[-1]
    sums = outputs[:-1]
    for i in range(7, 10):
        s, carry = _stage(bd, a_sig(i), b_sig(i), carry)
        sums.append(s)
    sums.append(carry)
    m = {"name": "adder", "n_inputs": 20, "decode": "bits",
         "encode": "adder10", "units": bd.units, "outputs": sums,
         "bounds": [(0, 999), (0, 999)]}
    return m

def verify_adder10(m):
    """Exhaustive over the full 1000x1000 domain."""
    enc = members.ENCODERS["adder10"]
    mm = dict(m)
    correct = 0
    total = 0
    first_fail = None
    for a in range(1000):
        for b in range(1000):
            got = members.decode_member(m, members.forward(m, enc(a, b)))
            total += 1
            if got == a + b:
                correct += 1
            elif first_fail is None:
                first_fail = (a, b, got)
    return correct, total, first_fail

def episode_extend_adder(hv):
    r = hv.run_task({"op": "adder", "args": [500, 400]})
    ledger("extend_adder", "adder", "probe: (500, 400) on the 7-bit member",
           r["status"], None, None,
           "inputs beyond the encoding are declared, never truncated into a guess")
    m = extend_adder()
    # the original 7 stages must be weight-identical after remapping
    v1 = members.build_adder()
    same = all(
        {(k + 6 if k >= 14 else k): v for k, v in u1["w"].items()} == u2["w"]
        and u1["b"] == u2["b"] and u1["act"] == u2["act"]
        for u1, u2 in zip(v1["units"], m["units"]))
    ledger("extend_adder", "adder",
           "architecture surgery: appended bit stages 7-9; stages 0-6 keep "
           "their exact v1 weights (remapped signal indices)",
           "domain 0..99", "domain 0..999", None,
           f"stages 0-6 weight-identical to v1: {same}")
    c, tot, ff = verify_adder10(m)
    ledger("extend_adder", "adder", "exhaustive verification on the new domain",
           "0..99 exact", f"{c}/{tot} on 0..999", c == tot,
           f"first failure: {ff}" if ff else "none")
    if c == tot:
        members.save_member(m)
        hive_mod.add_lesson("adder",
                            "Tasks arrived beyond 0..99. The adder's architecture "
                            "grew 3 bit stages (weights of stages 0-6 untouched) and "
                            "now covers 0..999, verified exhaustively (1,000,000 pairs).")
    return c, tot


# ---------- episode 3: corruption -> diagnosis -> surgical repair --------

def corrupt_member(m, seed=7, n_hits=3):
    """Simulated damage: n_hits random weight/bias entries wrecked."""
    rng = random.Random(seed)
    dmg = copy.deepcopy(m)
    spots = [(ui, k) for ui, u in enumerate(dmg["units"]) for k in list(u["w"].keys()) + ["b"]]
    hits = rng.sample(spots, n_hits)
    for ui, k in hits:
        if k == "b":
            dmg["units"][ui]["b"] = rng.choice([2.5, -3.0, 1.7])
        else:
            dmg["units"][ui]["w"][k] = rng.choice([0.0, -2.0, 3.5])
    return dmg, hits

def diagnose_multiplier(m):
    """Blind behavioural diagnosis. The multiplier is 16 AND units feeding
    one linear sum unit. Probe each AND unit in isolation through the
    trace; check the sum unit against the traced partial products."""
    n_in = m["n_inputs"]
    damaged_and = []
    for t in range(16):
        i, j = divmod(t, 4)
        sig = n_in + t
        ok = True
        for (av, bv, want) in [(1, 1, 1.0), (1, 0, 0.0), (0, 1, 0.0), (0, 0, 0.0)]:
            x = members.ENCODERS["multiplier"](av << i, bv << j)
            if forward_trace(m, x)[sig] != want:
                ok = False
        if not ok:
            damaged_and.append(t)
    sum_bad = False
    for a in range(10):
        for b in range(10):
            x = members.ENCODERS["multiplier"](a, b)
            vals = forward_trace(m, x)
            want = sum((1 << (t // 4 + t % 4)) * vals[n_in + t] for t in range(16))
            if abs(vals[m["outputs"][0]] - want) > 1e-9:
                sum_bad = True
    return damaged_and, sum_bad

def repair_multiplier(m, damaged_and, sum_bad):
    fixed = copy.deepcopy(m)
    n_in = m["n_inputs"]
    for t in damaged_and:
        i, j = divmod(t, 4)
        fixed["units"][t] = {"w": {i: 1.0, 4 + j: 1.0}, "b": -1.0, "act": "relu"}
    if sum_bad:
        t = len(fixed["units"]) - 1
        fixed["units"][t] = {"w": {n_in + u: float(1 << (u // 4 + u % 4))
                                   for u in range(16)},
                             "b": 0.0, "act": "lin"}
    return fixed

def episode_repair_multiplier(hv):
    good = members.load_member("multiplier")
    dmg, hits = corrupt_member(good)
    members.save_member(dmg)  # the damage lands on the canonical weights
    hv2 = hive_mod.Hive()
    c0, tot, _ = members.verify(hv2.members["multiplier"])
    ledger("repair_multiplier", "multiplier",
           "damage event: 3 weight/bias entries wrecked (seeded); routine "
           "suite re-verification detects the degradation",
           "100/100", f"{c0}/{tot}", None, f"damaged entries: {hits}")
    damaged_and, sum_bad = diagnose_multiplier(hv2.members["multiplier"])
    ledger("repair_multiplier", "multiplier",
           "blind diagnosis: isolated probes per AND unit + sum check",
           f"{c0}/{tot}",
           f"damaged AND units: {damaged_and}, sum unit damaged: {sum_bad}",
           None, "diagnosis used behaviour only, never the damage record")
    fixed = repair_multiplier(hv2.members["multiplier"], damaged_and, sum_bad)
    c1, tot, _ = members.verify(fixed)
    ledger("repair_multiplier", "multiplier",
           "surgical repair: rewrote exactly the diagnosed units to the "
           "constructed pattern; every other weight untouched",
           f"{c0}/{tot}", f"{c1}/{tot}", c1 == tot)
    if c1 == tot:
        members.save_member(fixed)
        hive_mod.add_lesson("multiplier",
                            "Multiplier weights were damaged and the hive caught it "
                            "on re-verification (score dropped). Diagnosis isolated "
                            "the faulty AND/sum units by probing; only those units "
                            "were rewritten. Back to 100/100, verified exhaustively.")
    return c0, c1, tot, damaged_and, sum_bad


# ---------- generic fallback: perturbation hill-climb --------------------

def hill_climb(m, budget=300, seed=1):
    """Clone-and-vary search on the member's full domain. Keeps only strict
    improvements. Returns (best_member, start_score, end_score)."""
    rng = random.Random(seed)
    dom = members.DOMAINS[m["name"]]
    best, _, _ = members.verify(m)
    cur = copy.deepcopy(m)
    start = best
    for _ in range(budget):
        cand = copy.deepcopy(cur)
        for u in cand["units"]:
            for k in list(u["w"].keys()):
                if rng.random() < 0.3:
                    u["w"][k] += rng.gauss(0, 0.3)
            if rng.random() < 0.3:
                u["b"] += rng.gauss(0, 0.3)
        s, _, _ = members.verify(cand)
        if s > best:
            best, cur = s, cand
            if best == len(dom):
                break
    return cur, start, best
