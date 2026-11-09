"""tiny-hive members: tiny specialist networks, constructed weight by weight.

Every member is a small DAG of units. Signals 0..n-1 are the inputs; each unit
appends one new signal:  s = b + sum(w[i] * vals[i]), optionally ReLU.
Outputs are chosen signals, decoded back to a semantic answer.

Weights are constructed by design (see build_* functions), then verified
EXHAUSTIVELY against independent plain-Python reference functions.
Canonical weights live in members/*.json; this module can regenerate the
v1 (birth) weights and load the current canonical ones.
"""
import json, os, itertools

HERE = os.path.dirname(os.path.abspath(__file__))
MEMBERS_DIR = os.path.join(HERE, "members")


# ---------- framework ----------

def U(w, b=0.0, act="relu"):
    return {"w": {int(k): float(v) for k, v in w.items()}, "b": float(b), "act": act}

def member(name, n_inputs, units, outputs, encode, decode):
    return {"name": name, "n_inputs": n_inputs, "units": units,
            "outputs": outputs, "encode": encode, "decode": decode}

def forward(m, x):
    vals = list(x)
    for u in m["units"]:
        s = u["b"]
        for i, w in u["w"].items():
            s += w * vals[int(i)]
        vals.append(s if u["act"] == "lin" else (s if s > 0.0 else 0.0))
    return [vals[i] for i in m["outputs"]]

def decode_out(kind, outs):
    if kind == "bits":                      # LSB-first bit signals -> int
        v = 0
        for i, o in enumerate(outs):
            if o > 0.5:
                v |= (1 << i)
        return v
    if kind == "round":
        return int(round(outs[0]))
    if kind == "round_each":
        return tuple(int(round(o)) for o in outs)
    if kind == "step":
        return 1 if outs[0] > 0 else 0
    if kind == "argmax":
        return max(range(len(outs)), key=lambda i: outs[i])
    raise ValueError(kind)

def run_member(m, args):
    return decode_out(m["decode"], forward(m, ENCODERS[m["name"]](*args)))

def param_count(m):
    return sum(len(u["w"]) + 1 for u in m["units"])


# ---------- encoders / references / domains ----------

def bits(x, n):
    return [float((x >> i) & 1) for i in range(n)]

ENCODERS = {
    "parity8":    lambda x: bits(x, 8),
    "popcount8":  lambda x: bits(x, 8),
    "majority5":  lambda x: bits(x, 5),
    "compare2":   lambda a, b: [float(a), float(b)],
    "max4":       lambda a, b, c, d: [float(a), float(b), float(c), float(d)],
    "sort3":      lambda a, b, c: [float(a), float(b), float(c)],
    "adder":      lambda a, b: bits(a, 7) + bits(b, 7),
    "subtractor": lambda a, b: bits(a, 8) + bits(b, 8),
    "multiplier": lambda a, b: bits(a, 4) + bits(b, 4),
    "seqnext":    lambda t, d: bits(t, 7) + bits(d, 7),
    "divider":    lambda a, b: bits(a, 7) + bits(b, 4),
    "adder10":    lambda a, b: bits(a, 7) + bits(b, 7) + bits(a >> 7, 3) + bits(b >> 7, 3),
}

REFERENCES = {
    "parity8":    lambda x: bin(x).count("1") % 2,
    "popcount8":  lambda x: bin(x).count("1"),
    "majority5":  lambda x: 1 if bin(x).count("1") >= 3 else 0,
    "compare2":   lambda a, b: 0 if b > a else (1 if a > b else 2),  # GT,LT,EQ
    "max4":       lambda a, b, c, d: max(a, b, c, d),
    "sort3":      lambda a, b, c: tuple(sorted((a, b, c))),
    "adder":      lambda a, b: a + b,
    "subtractor": lambda a, b: a - b,
    "multiplier": lambda a, b: a * b,
    "seqnext":    lambda t, d: t + d,
    "divider":    lambda a, b: a // b,
}

DOMAINS = {
    "parity8":    [(x,) for x in range(256)],
    "popcount8":  [(x,) for x in range(256)],
    "majority5":  [(x,) for x in range(32)],
    "compare2":   [(a, b) for a in range(16) for b in range(16)],
    "max4":       [(a, b, c, d) for a in range(10) for b in range(10)
                   for c in range(10) for d in range(10)],
    "sort3":      [(a, b, c) for a in range(10) for b in range(10) for c in range(10)],
    "adder":      [(a, b) for a in range(100) for b in range(100)],
    "subtractor": [(a, b) for a in range(100) for b in range(100)],
    "multiplier": [(a, b) for a in range(10) for b in range(10)],
    "seqnext":    [(a + 2 * d, d) for a in range(51) for d in range(10)],
    "divider":    [(a, b) for a in range(100) for b in range(1, 10)],
}


# ---------- unit-DAG construction helpers ----------

class Builder:
    def __init__(self, n_inputs):
        self.n = n_inputs
        self.units = []
        self.next_sig = n_inputs
    def add(self, w, b=0.0, act="relu"):
        self.units.append(U(w, b, act))
        s = self.next_sig
        self.next_sig += 1
        return s
    def relu(self, w, b=0.0):
        return self.add(w, b, "relu")
    def lin(self, w, b=0.0):
        return self.add(w, b, "lin")
    def absdiff(self, p, q):
        """|p - q| as one signal (exact for signals in {0,1} or equal ranges)."""
        d1 = self.relu({p: 1.0, q: -1.0})
        d2 = self.relu({p: -1.0, q: 1.0})
        return self.lin({d1: 1.0, d2: 1.0})
    def parity2(self, p, q):
        return self.absdiff(p, q)
    def step_from_sum(self, s):
        """map integer sum signal s in 0..3 to a bit: 1 iff s >= 2."""
        cA = self.relu({s: 1.0}, -1.0)
        cB = self.relu({s: 1.0}, -2.0)
        return self.lin({cA: 1.0, cB: -1.0})
    def majority3(self, p, q, r):
        s = self.lin({p: 1.0, q: 1.0, r: 1.0})
        return self.step_from_sum(s)


def _bit_adder(n_bits, name):
    """a + b over n_bits input bits each (LSB first). Returns (member, sum_signals)."""
    bd = Builder(2 * n_bits)
    a_sig = list(range(0, n_bits))
    b_sig = list(range(n_bits, 2 * n_bits))
    sums = []
    carry = None
    for i in range(n_bits):
        p = bd.parity2(a_sig[i], b_sig[i])
        if carry is None:
            s = p
            carry = bd.majority3(a_sig[i], b_sig[i], bd.lin({}, 0.0)) if False else None
            # carry out of bit0 = AND(a0,b0)
            carry = bd.relu({a_sig[i]: 1.0, b_sig[i]: 1.0}, -1.0)
        else:
            s = bd.parity2(p, carry)
            carry = bd.majority3(a_sig[i], b_sig[i], carry)
        sums.append(s)
    sums.append(carry)
    return member(name, 2 * n_bits, bd.units, sums, None, "bits")


# ---------- member constructions (v1 / birth weights) ----------

def build_parity8():
    bd = Builder(8)
    p = 0
    for i in range(1, 8):
        p = bd.parity2(p, i)
    return member("parity8", 8, bd.units, [p], None, "raw01")

def build_popcount8():
    bd = Builder(8)
    s = bd.lin({i: 1.0 for i in range(8)})
    return member("popcount8", 8, bd.units, [s], None, "round")

def build_majority5():
    bd = Builder(5)
    s = bd.relu({i: 1.0 for i in range(5)}, -2.5)
    return member("majority5", 5, bd.units, [s], None, "step")

def build_compare2():
    bd = Builder(2)
    d = bd.lin({0: -1.0, 1: 1.0})                    # b - a
    ad1 = bd.relu({d: 1.0})
    ad2 = bd.relu({d: -1.0})
    absd = bd.lin({ad1: 1.0, ad2: 1.0})
    gt = bd.relu({d: 1.0}, -0.5)
    lt = bd.relu({d: -1.0}, -0.5)
    eq = bd.relu({absd: -2.0}, 1.0)
    return member("compare2", 2, bd.units, [gt, lt, eq], None, "argmax")

def build_max4():
    bd = Builder(4)
    def mx(p, q):
        r = bd.relu({p: 1.0, q: -1.0})
        return bd.lin({q: 1.0, r: 1.0})
    m = mx(mx(0, 1), 2)
    m = mx(m, 3)
    return member("max4", 4, bd.units, [m], None, "round")

def build_sort3():
    bd = Builder(3)
    def ce(p, q):
        r = bd.relu({p: 1.0, q: -1.0})
        mn = bd.lin({p: 1.0, r: -1.0})
        mx = bd.lin({q: 1.0, r: 1.0})
        return mn, mx
    a, b = ce(0, 1)
    b, c = ce(b, 2)
    a, b = ce(a, b)
    return member("sort3", 3, bd.units, [a, b, c], None, "round_each")

def build_adder():
    return _bit_adder(7, "adder")

def build_seqnext():
    return _bit_adder(7, "seqnext")

def build_subtractor():
    bd = Builder(16)
    a_sig = list(range(0, 8))
    b_sig = list(range(8, 16))
    diffs = []
    borrow = None
    for i in range(8):
        p = bd.parity2(a_sig[i], b_sig[i])
        if borrow is None:
            d = p
            # borrow out = majority(NOT a, b, 0) = AND(NOT a, b)
            na = bd.lin({a_sig[i]: -1.0}, 1.0)         # 1 - a_i
            borrow = bd.relu({na: 1.0, b_sig[i]: 1.0}, -1.0)
        else:
            d = bd.parity2(p, borrow)
            s = bd.lin({a_sig[i]: -1.0, b_sig[i]: 1.0, borrow: 1.0}, 1.0)  # (1-a)+b+borrow
            borrow = bd.step_from_sum(s)
        diffs.append(d)
    m = member("subtractor", 16, bd.units, diffs, None, "bits8signed")
    return m

def build_multiplier():
    bd = Builder(8)
    terms = []
    for i in range(4):
        for j in range(4):
            u = bd.relu({i: 1.0, 4 + j: 1.0}, -1.0)    # AND(a_i, b_j)
            terms.append((u, float(1 << (i + j))))
    s = bd.lin({u: w for u, w in terms})
    return member("multiplier", 8, bd.units, [s], None, "round")

def build_divider():
    """Quotient a//b for a in 0..99, b in 1..9, built by COMPOSITION:
    q = sum over k>=1 of [k*b <= a]. Each test is a constructed threshold unit
    over the bit inputs: k*b <= a  <=>  a - k*b >= 0; a and b enter as bits, so
    a - k*b is a linear form in the input bits. Threshold via step pair."""
    bd = Builder(11)
    a_bits = list(range(0, 7))        # a: 7 bits
    b_bits = list(range(7, 11))       # b: 4 bits
    indicators = []
    for k in range(1, 100):
        # value = a - k*b as linear form: a bits weighted 2^i ; b bits weighted -k*2^j
        w = {}
        for i in range(7):
            w[a_bits[i]] = float(1 << i)
        for j in range(4):
            w[b_bits[j]] = -float(k * (1 << j))
        s = bd.lin(w)                                  # exact integer, may be negative
        ge = bd.step_from_sum_shifted(s) if False else None
        # 1 iff s >= 0 : relu(s+0.5) - relu(s-0.5) gives 1 for s>=1... use ramp on integers:
        # f(s) = relu(s + 1) - relu(s)  -> s<=-1: 0 ; s=0: 1 ; s>=0: 1  (for integer s)
        r1 = bd.relu({s: 1.0}, 1.0)
        r2 = bd.relu({s: 1.0}, 0.0)
        ind = bd.lin({r1: 1.0, r2: -1.0})
        indicators.append(ind)
    q = bd.lin({u: 1.0 for u in indicators})
    return member("divider", 11, bd.units, [q], None, "round")


BUILDERS = {
    "parity8": build_parity8, "popcount8": build_popcount8,
    "majority5": build_majority5, "compare2": build_compare2,
    "max4": build_max4, "sort3": build_sort3, "adder": build_adder,
    "subtractor": build_subtractor, "multiplier": build_multiplier,
    "seqnext": build_seqnext, "divider": build_divider,
}

# decode kinds that differ from the generic table
DECODE_OVERRIDES = {"parity8": "raw01", "subtractor": "bits8signed"}

def decode_member(m, outs):
    kind = DECODE_OVERRIDES.get(m["name"], m["decode"])
    if kind == "raw01":
        return 1 if outs[0] > 0.5 else 0
    if kind == "bits8signed":
        v = 0
        for i, o in enumerate(outs):
            if o > 0.5:
                v |= (1 << i)
        return v - 256 if v >= 128 else v
    return decode_out(kind, outs)

def run_member2(m, args):
    return decode_member(m, forward(m, ENCODERS[m.get("encode") or m["name"]](*args)))


# ---------- canonical weight storage ----------

def to_json(m):
    return {"name": m["name"], "n_inputs": m["n_inputs"], "decode": m["decode"],
            "encode": m.get("encode"), "bounds": m.get("bounds"),
            "units": [{"w": {str(k): v for k, v in u["w"].items()},
                       "b": u["b"], "act": u["act"]} for u in m["units"]],
            "outputs": m["outputs"]}

def from_json(d):
    return {"name": d["name"], "n_inputs": d["n_inputs"], "decode": d["decode"],
            "encode": d.get("encode"), "bounds": d.get("bounds"),
            "units": [{"w": {int(k): v for k, v in u["w"].items()},
                       "b": u["b"], "act": u["act"]} for u in d["units"]],
            "outputs": d["outputs"]}

def save_member(m):
    os.makedirs(MEMBERS_DIR, exist_ok=True)
    with open(os.path.join(MEMBERS_DIR, m["name"] + ".json"), "w") as f:
        json.dump(to_json(m), f)

def load_member(name):
    with open(os.path.join(MEMBERS_DIR, name + ".json")) as f:
        return from_json(json.load(f))

def load_all():
    out = {}
    if os.path.isdir(MEMBERS_DIR):
        for fn in sorted(os.listdir(MEMBERS_DIR)):
            if fn.endswith(".json"):
                out[fn[:-5]] = load_member(fn[:-5])
    return out


# ---------- exhaustive verification ----------

def verify(m, domain=None):
    """Returns (correct, total, first_failures). Exhaustive over the domain."""
    dom = DOMAINS[m["name"]] if domain is None else domain
    ref = REFERENCES[m["name"]]
    correct = 0
    fails = []
    for args in dom:
        got = run_member2(m, args)
        want = ref(*args)
        if got == want:
            correct += 1
        elif len(fails) < 25:
            fails.append((args, got, want))
    return correct, len(dom), fails
