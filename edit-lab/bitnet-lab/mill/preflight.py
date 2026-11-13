#!/usr/bin/env python3
"""preflight.py — the mill's two pre-first-run validations (Muse's work, Muse's side).

From RIGOR-AUDIT.md sections 5a and 2b — run these BEFORE the first
generation's verdicts are trusted:

  (b) SWEEP PARITY: a seed-0 sweep run of the champion config must report
      held_init == 8.3138 exactly (the value recorded in runs.jsonl for
      layered_half_rope seed 0). If it does not, the sweep's init/stream
      replication is broken and no sweep verdict stands.
  (a) PROBE NOISE: job zero at probe budget (1.25 min) on seeds 0, 1, 2.
      The promotion bar PROMOTE_DELTA (0.05) must be >= 2x the observed
      spread (sample sd); if it is not, the bar is a coin flip and must be
      raised to the measured value in screen.py + PROMOTE.md.

Refuses to run while the lab is busy (exit 3, nothing written) — the ladder
and the growth cycles preempt everything. Writes mill/PROBE-NOISE.md and
mill/PREFLIGHT-RESULTS.md. Run with the lab venv python:

  ~/workspace/edit-lab/fable-validation/venv/bin/python mill/preflight.py

Exit codes: 0 = both checks pass; 1 = a check failed or could not complete;
3 = lab busy, nothing run.
"""
import json, math, sys, time
from pathlib import Path

MILL = Path(__file__).resolve().parent
sys.path.insert(0, str(MILL))
import screen as S  # the mill's own driver: busy check, sweep runner, fingerprints

EXPECTED_HELD_INIT = 8.3138
PROBE_MINUTES = 1.25


def sweep_one(run, seed, minutes, tag):
    job = {"id": "MILL-000", "run": run, "minutes": minutes, "seed": seed, "tag": tag}
    res = S.run_sweep_batch([job], S.SOLO_OMP, time.time() + minutes * 60 + 600)
    return res.get("MILL-000")


def main():
    busy = S.lab_busy()
    if busy:
        print(f"[preflight] lab busy ({busy}) — refusing to run; nothing written")
        return 3
    champ = S.load_champion()
    out = {"ts": time.time(), "champion_gen": champ["gen"], "champion_run": champ["run"],
           "code_sha": S.code_fingerprint()}
    print(f"[preflight] champion gen {champ['gen']}: {champ['run']}")

    # (b) parity — cheap and fatal if broken
    rec = sweep_one(champ["run"], 0, 0.25, "mill000pf")
    hi = (rec or {}).get("held_init")
    parity_ok = hi == EXPECTED_HELD_INIT
    out["parity"] = {"held_init": hi, "expected": EXPECTED_HELD_INIT, "pass": parity_ok}
    print(f"[preflight] (b) sweep parity: held_init={hi} expected={EXPECTED_HELD_INIT} "
          f"-> {'PASS' if parity_ok else 'FAIL'}")

    # (a) probe noise: job zero at probe budget, seeds 0/1/2
    helds = []
    for seed in (0, 1, 2):
        rec = sweep_one(champ["run"], seed, PROBE_MINUTES, f"mill000pf{seed}")
        if not rec or rec.get("held_final") is None:
            print(f"[preflight] (a) noise seed {seed} did not complete — aborting")
            out["noise"] = {"helds": helds, "pass": False, "reason": "incomplete"}
            (MILL / "PREFLIGHT-RESULTS.md").write_text(render(out))
            return 1
        helds.append(rec["held_final"])
        print(f"[preflight] (a) noise seed {seed}: held_final={rec['held_final']}")
    sd = S.sample_sd(helds)
    rng = max(helds) - min(helds)
    bar_ok = S.PROMOTE_DELTA >= 2 * sd
    required = S.PROMOTE_DELTA if bar_ok else math.ceil(2 * sd * 1000) / 1000
    out["noise"] = {"helds": helds, "sample_sd": round(sd, 4), "range": round(rng, 4),
                    "promote_delta": S.PROMOTE_DELTA, "bar_is_2x_spread": bar_ok,
                    "required_delta": required, "pass": bar_ok}
    print(f"[preflight] (a) probe noise: helds={helds} sample sd={sd:.4f} range={rng:.4f}; "
          f"PROMOTE_DELTA={S.PROMOTE_DELTA} vs 2x sd={2 * sd:.4f} -> "
          f"{'PASS' if bar_ok else 'FAIL — bar must rise to ' + str(required)}")

    (MILL / "PROBE-NOISE.md").write_text(render_noise(out))
    (MILL / "PREFLIGHT-RESULTS.md").write_text(render(out))
    print("[preflight] wrote mill/PROBE-NOISE.md and mill/PREFLIGHT-RESULTS.md")
    return 0 if (parity_ok and bar_ok) else 1


def render_noise(out):
    n = out.get("noise", {})
    lines = ["# PROBE-NOISE — job zero at probe budget (Muse's work, Muse's side)",
             "",
             f"Measured by mill/preflight.py. Champion: `{out['champion_run']}` "
             f"(gen {out['champion_gen']}), probe budget {PROBE_MINUTES} min, seeds 0/1/2.",
             "",
             f"- held_final by seed: {n.get('helds')}",
             f"- sample sd (n-1): {n.get('sample_sd')}",
             f"- range (max-min): {n.get('range')}",
             f"- PROMOTE_DELTA in force: {n.get('promote_delta')}",
             f"- bar >= 2x spread: {n.get('bar_is_2x_spread')}",
             ""]
    if n.get("bar_is_2x_spread"):
        lines.append("Verdict: the 0.05 promotion bar is at least 2x the observed probe "
                     "spread — a real screen, not a coin flip. No change.")
    else:
        lines.append(f"Verdict: the bar is BELOW 2x the observed spread. Raise "
                     f"PROMOTE_DELTA to {n.get('required_delta')} in mill/screen.py and "
                     f"mill/PROMOTE.md, and record the change with this file as evidence.")
    lines.append("")
    return "\n".join(lines)


def render(out):
    p, n = out.get("parity", {}), out.get("noise", {})
    lines = ["# PREFLIGHT-RESULTS — the mill's pre-first-run validations (Muse's work, Muse's side)",
             "",
             f"Run by mill/preflight.py at ts {out['ts']:.0f}; champion gen "
             f"{out['champion_gen']} (`{out['champion_run']}`); code_sha {out['code_sha'][:12]}…",
             "",
             f"- (b) sweep parity: held_init {p.get('held_init')} vs expected "
             f"{p.get('expected')} -> {'PASS' if p.get('pass') else 'FAIL'}",
             f"- (a) probe noise: helds {n.get('helds')}, sample sd {n.get('sample_sd')}, "
             f"PROMOTE_DELTA {n.get('promote_delta')} >= 2x sd: {n.get('bar_is_2x_spread')} "
             f"-> {'PASS' if n.get('pass') else 'FAIL'}",
             ""]
    if n and not n.get("bar_is_2x_spread", True):
        lines.append(f"ACTION REQUIRED: raise PROMOTE_DELTA to {n.get('required_delta')} "
                     f"(mill/screen.py + mill/PROMOTE.md).")
    if p and not p.get("pass", True):
        lines.append("ACTION REQUIRED: sweep parity failed — the sweep's init/stream "
                     "replication is broken; no sweep verdict stands until this passes.")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
