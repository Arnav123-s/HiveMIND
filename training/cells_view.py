"""Compact view of a probe for the locator: knockouts per layer and the most sensitive modules per parameter."""
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent / "reports" / "cells"
SIZE = {"q_proj": 576 * 576, "k_proj": 576 * 192, "v_proj": 576 * 192, "o_proj": 576 * 576,
        "gate_proj": 576 * 1536, "up_proj": 576 * 1536, "down_proj": 576 * 1536}
for skill in [a for a in sys.argv[1:] if not a.startswith("--")] if __name__ == "__main__" and "--pick" not in sys.argv else []:
    p = json.loads((R / f"probe_{skill}_smol135.json").read_text())
    k, a = p["knockout"], p["attr"]
    n = len(k) // 2
    print(f"== {skill} (dev loss {p['dev_loss']:.2f})")
    print(" KO attn:", " ".join(f"{i}:{k[f'{i}:attn']:+.2f}" for i in range(n) if abs(k[f'{i}:attn']) >= 0.15))
    print(" KO mlp: ", " ".join(f"{i}:{k[f'{i}:mlp']:+.2f}" for i in range(n) if abs(k[f'{i}:mlp']) >= 0.15))
    per = {m: v / SIZE[m.split(":")[1]] for m, v in a.items()}
    top = sorted(per, key=lambda m: -per[m])[:14]
    print(" top per-param:", " ".join(m.replace("_proj", "") for m in top))
    lay = [sum(per[f"{i}:{m}"] for m in SIZE) for i in range(n)]
    mx = max(lay)
    print(" layer sensitivity:", "".join(" .:-=+*#%@"[min(9, int(9 * x / mx))] for x in lay))


def locator_pick(p, band=7):
    """The rules I (acting as the locator) apply to a probe; every module comes with the reason it was picked.
    R1 read:     v+q in the band of layers most sensitive per parameter (where the input is read)
    R2 unblock:  o of layers whose attention knockout LOWERS loss by >= 0.5; down of layers whose MLP knockout
                 LOWERS loss by >= 1.0 (they push toward the base's default answer)
    R3 bottleneck: down of middle layers whose MLP knockout RAISES loss by >= 1.0
    R4 leave layer 0 and the last layer alone: they break everything when removed (generic machinery)
    R5 (my review of the first maps) R2 only from layer 3 up: knockouts of layers 1-2 change every token's
       features, so they say little about the skill itself
    R6 (revised R4 after tuning runs on route_step and orders_spend) the last two layers' MLPs (gate, up, down)
       are always edited: they write the answer out. Without them the located edit lost to a random one."""
    k, a = p["knockout"], p["attr"]
    n = len(k) // 2
    per = {m: v / SIZE[m.split(":")[1]] for m, v in a.items()}
    lay = [sum(per[f"{i}:{m}"] for m in SIZE) for i in range(n)]
    peak = max(range(1, n - 1), key=lambda i: sum(lay[max(1, i - band // 2):i + band // 2 + 1]))
    lo, hi = max(1, peak - band // 2), min(n - 2, peak + band // 2)
    why = {}
    for i in range(lo, hi + 1):
        why[f"{i}:v_proj"] = why[f"{i}:q_proj"] = "R1 read band"
    for i in range(1, n - 1):
        if i < 3:
            continue
        if k[f"{i}:attn"] <= -0.5:
            why[f"{i}:o_proj"] = f"R2 attn KO {k[f'{i}:attn']:+.2f}"
        if k[f"{i}:mlp"] <= -1.0:
            why[f"{i}:down_proj"] = f"R2 mlp KO {k[f'{i}:mlp']:+.2f}"
        if k[f"{i}:mlp"] >= 1.0:
            why[f"{i}:down_proj"] = f"R3 mlp KO {k[f'{i}:mlp']:+.2f}"
    for i in (n - 2, n - 1):
        for m in ("gate_proj", "up_proj", "down_proj"):
            why[f"{i}:{m}"] = "R6 writes the answer"
    return why


if __name__ == "__main__" and "--pick" in sys.argv:
    for skill in [s for s in sys.argv[1:] if not s.startswith("--")]:
        w = locator_pick(json.loads((R / f"probe_{skill}_smol135.json").read_text()))
        print(skill, len(w), "modules:", " ".join(f"{m.replace('_proj', '')}({r.split()[0]})" for m, r in sorted(w.items(), key=lambda kv: (int(kv[0].split(':')[0]), kv[0]))))
