# PREFLIGHT — the mill's two pre-first-run validations (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. -->

From `RIGOR-AUDIT.md` §5a and §2b. Both checks are implemented in
`mill/preflight.py`; this page is the exact command and how to read the
result. Run them **before the first generation's verdicts are trusted**.

## The command

```
cd ~/workspace/edit-lab/bitnet-lab
~/workspace/edit-lab/fable-validation/venv/bin/python mill/preflight.py
```

The script refuses while the lab is busy (exit 3, nothing written — the
scale ladder and growth cycles preempt everything) and otherwise takes
~5 minutes: one 15-second parity run plus three 75-second noise runs, all
solo. Exit 0 = both checks pass; exit 1 = a check failed (see below).

## What it checks

**(b) Sweep-vs-subprocess parity (audit §2b).** A seed-0 sweep run of the
champion config must report `held_init` = **8.3138** exactly — the value
recorded in the lab's `runs.jsonl` for `layered_half_rope` seed 0. This is
a free, exact invariant: if the sweep's init/stream replication were
broken, its first number would already disagree. **On FAIL: no sweep
verdict stands** — fix the sweep before any probe result is read.

**(a) Probe-noise basis for the promotion bar (audit §5a).** Job zero at
probe budget (1.25 min) on seeds 0, 1, 2. The observed spread (sample sd)
is written to `mill/PROBE-NOISE.md`. The promotion bar `PROMOTE_DELTA`
(0.05) must be **≥ 2× that spread**; below that, the bar is a coin flip
that would promote a large share of the pool on noise alone and drown the
trial queue. **On FAIL:** raise `PROMOTE_DELTA` to the value the script
prints (ceil of 2× sd) in BOTH places it lives — `mill/screen.py`
(the constant) and `mill/PROMOTE.md` (the probe-bar section, with the
measured noise cited as the new rationale). `mill/PREFLIGHT-RESULTS.md`
records both outcomes, the code fingerprint, and any required action.

## Status

Scripted and ready. As of the 2026-11-12 rigor-fix pass, the scale ladder
owns the lab, so the checks have not yet run — they are the first thing to
fire when a free slot appears, and their results land in
`mill/PROBE-NOISE.md` + `mill/PREFLIGHT-RESULTS.md`.
