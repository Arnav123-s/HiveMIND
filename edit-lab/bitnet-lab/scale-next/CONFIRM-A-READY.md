# CONFIRM-A-READY.md — CONFIRM-PLAN Set A launch readiness (Muse's work, Muse's side)

Checked 2026-11-12 ~23:25 PT. **No training was run.** All checks below are
compile/guard runs only. The driver was delivered unlaunched on purpose.

## Verdict: READY TO FIRE (Set A only)

Driver: `scale-next/run_confirm_a.py` (Muse's work, Muse's side).
It implements CONFIRM-PLAN.md §2 **Set A** exactly — 6 runs, no recipe
changes, no Set B. Set B (448 steps) stays behind the §3 decision
checkpoint after Set A and is not in this driver.

## The 6 jobs, as the script sees them (guard output, verbatim values)

Recipe for every run: `--arm layered --rope` (layered + rotary + plain
votes), `--steps 280` = 2,293,760 tokens/run (38.8% of the corpus),
standard fixed 128 held windows. Total est: 15,120 s ≈ 4.2 h.

| # | Recorded arm (label) | Seed | Shape | `--tag` | est | `--minutes` cap | Subprocess timeout (est×1.8+300) | Status at check |
|---|---|---|---|---|---|---|---|---|
| 1 | `layered_rope_confirmA10m` | 0 | `--dim 512 --layers-n 3` | `confirmA10m` | 3600 s | 100 | 6780 s | pending |
| 2 | `layered_rope_confirmA10m` | 1 | `--dim 512 --layers-n 3` | `confirmA10m` | 3600 s | 100 | 6780 s | pending |
| 3 | `layered_rope_confirmA10m` | 2 | `--dim 512 --layers-n 3` | `confirmA10m` | 3600 s | 100 | 6780 s | pending |
| 4 | `layered_rope_confirmA2m` | 0 | `--dim 288 --layers-n 2` | `confirmA2m` | 1440 s | 40 | 2892 s | pending |
| 5 | `layered_rope_confirmA2m` | 1 | `--dim 288 --layers-n 2` | `confirmA2m` | 1440 s | 40 | 2892 s | pending |
| 6 | `layered_rope_confirmA2m` | 2 | `--dim 288 --layers-n 2` | `confirmA2m` | 1440 s | 40 | 2892 s | pending |

Winner = 10M rung (dim 512, layers 3) first, then runner-up = 2M rung
(dim 288, layers 2), per the established ladder verdict.

Example invocation the driver builds (job 1; ladder pattern, cwd = lab):

```
~/workspace/edit-lab/fable-validation/venv/bin/python train.py --arm layered --rope --seed 0 --steps 280 --minutes 100 --dim 512 --layers-n 3 --tag confirmA10m
```

## How the CLI / record identity was matched (read from train.py, not assumed)

- `train.py` argparse: `--steps N` is the fixed step budget (0 = time-boxed);
  `--minutes` **still applies as a safety cap** alongside it — the loop
  breaks on whichever comes first. Hence the caps above (100 / 40 min) sit
  above the per-run estimates (60 / 24 min), and the driver's subprocess
  timeout (6780 / 2892 s) sits above the cap.
- Recorded arm name, from `train.py:main()`:
  `arm + "_rope" (if --rope) + "_carry" / "_cooldown" (if set) + "_" + tag`.
  With `--arm layered --rope --tag confirmA10m` that is exactly
  `layered_rope_confirmA10m` (and `layered_rope_confirmA2m` for the 2M rung).
- Skip detection keys on the **full identity
  (recorded arm label, seed, steps_target)**. Records carry both `steps`
  (actual) and `steps_target` (the `--steps` budget); `steps_target` is
  the identity component, with actual `steps` as fallback for pre-ladder
  records that have no `steps_target` field. The ladder's 56-step records
  (`layered_rope_scale10m` / `layered_rope_scale2m`, `steps_target=56`)
  differ in **both** tag and steps identity, so they cannot cause a skip —
  verified live: the guard reports all 6 Set A jobs **pending** against
  the current `runs.jsonl` (46 lines, containing those 56-step records).

## Etiquette copied from `run_scale_ladder.py`

- One process at a time; before each run, waits 120 s at a time while
  `pgrep` finds `growth_cycle`, `python -m team`, or `bitnet-lab/train.py`.
- Growth-cycle window: no run may be scheduled to end inside
  [06:50 UTC − 10 min, 06:50 UTC + 35 min]; it waits the window out, or
  DROPs the job if waiting would pass the hard stop (10:30 UTC, ladder's
  convention, copied unchanged).
- Skips jobs already recorded (identity above), re-reading `runs.jsonl`
  per job.
- Per-job timeout = `int(est × 1.8) + 300` s; a timeout is logged and the
  driver moves on.
- The driver appends **nothing** to `runs.jsonl` itself — `train.py`
  writes it. Driver events go to the lab's `sweep.log` with a
  `confirmA:` prefix (launch mode only), as the ladder driver does.
- Child env: `OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2`, minimal
  `PATH`/`HOME`/`LANG`, cwd = `bitnet-lab/`.

## Guard mode

Without `--launch` (or with `--dry-run`) the script prints the plan
above and exits 0, writing nothing — a guard the ladder driver does not
have, added here following `run_overlap.py`'s no-`--launch` convention.

## Verification performed (this check)

| Check | Result |
|---|---|
| `py_compile scale-next/run_confirm_a.py` | **OK** (exit 0) |
| Guard, no args | prints 6-job plan, **exit 0**, all 6 pending |
| Guard, `--dry-run` | same plan, **exit 0** |
| Writes during both guards | none — `runs.jsonl` (17,349 B) and `sweep.log` (36,617 B) size + mtime unchanged |

## Exact launch command (for the executor)

From `~/workspace/edit-lab/bitnet-lab`:

```
~/workspace/edit-lab/fable-validation/venv/bin/python scale-next/run_confirm_a.py --launch
```

Expected: ~4.2 h of VM time if no window/busy waits intervene; results
land in the lab's `runs.jsonl` as `layered_rope_confirmA10m` /
`layered_rope_confirmA2m`, seeds 0/1/2, `steps_target=280`; progress in
`sweep.log` (`confirmA:` lines). Fire only when the lab is free (no
ladder/growth/heavy job), same discipline as every lab driver. After Set
A completes, stop at the CONFIRM-PLAN §3 checkpoint — do not proceed to
Set B on autopilot.

## Gate 0 readiness — re-verified separately (this same check)

Gate 0 (`scale-next/run_overlap.py`, phase `gate0`) is independent of
Set A (CONFIRM-PLAN §5); both fire when the ladder verdict lands.

| Check | Result |
|---|---|
| `py_compile scale-next/run_overlap.py` | **OK** (exit 0) |
| Guard, no `--launch`, `--phase gate0` | prints the plan JSON (`phase: gate0`, seeds [0], shape dim 288 / layers 2, tilts german/prose, results path `scale-next/overlap-runs.jsonl`), **exit 0** |
| Writes during the guard | none — `scale-next/overlap-runs.jsonl`, `scale-next/window-index.json`, and `scale-next/byte-manifest.json` were absent before and **still absent after**; lab `runs.jsonl` / `sweep.log` unchanged |

Note: the guard run is slow to start (~3–4 min wall in this check)
because `run_overlap.py`'s top-level imports load `bucket_probe`
(tokenizer + corpus memmap) before `main()` reaches the guard — the
guard itself launches nothing and trains nothing. Gate 0 remains
READY TO FIRE as recorded in `GATE0-READY.md` (v1, labeled; ~45 min
expected for seed 0 at launch).
