# GATE0-READY.md — Gate 0 launch readiness (Muse's work, Muse's side)

Checked 2026-11-12 ~20:15 PT, while the scale ladder still owns the lab.
**No training was run.** All checks below are compile/guard runs and
measurement-only bucket counts.

## Verdict: READY TO FIRE (v1, labeled)

Both blockers below are resolved. The blocker-1 patch is applied and
re-verified: `gate0()` now measures criterion (2) live at each dose and
records `gate0_held` lines, and every Gate 0 record carries
`"corpus": "v1"`. The blocker-2 decision is made (head of ops, 2026-11-12):
**Gate 0 fires on corpus v1** — both criteria are arm-vs-arm on the same
corpus, so the comparison is internally valid; the leakage caveat in the
pass/fail read below governs how a v1 criterion-(2) margin is called.
Fire when the ladder verdict lands, in the checklist order below.

---

## Blocker 1 — RESOLVED: the own-bucket half of Gate 0 was not implemented (patch applied)

Design §3 pass = **both**:

1. `dist(U,T) ≥ 2× dist(U,U′)` (Hamming on served states), **and**
2. T beats U on T's own bucket by **> 0.02 held loss**, at the same dose.

`run_overlap.py:gate0()` implements only (1). It never calls `held_loss`,
never builds a per-bucket held slice, and records no held number at all.
Worse, the trained models are discarded when `gate0()` returns — criterion
(2) can never be recovered post-hoc from `overlap-runs.jsonl`.

**Patch — APPLIED 2026-11-12** (in `gate0()`, ~25 lines): at each dose the
U and T models are measured live with `held_loss` on the german
held-candidate slice (built once: aligned starts `w·256`, `w % 40 == 0`,
bucketed `german` by `bucket_probe.bucket_of` — 40 windows on v1, tensor
built the same way `train.held_windows` builds its 128), before the models
go out of scope; per dose the driver records
`{"phase": "gate0_held", "corpus": "v1", "seed":…, "dose":…, "held_german_T":…, "held_german_U":…}`.
Re-verified after the patch: compiles, and the no-`--launch` guard (both
phases) prints the plan, exits 0, and writes nothing.

## Blocker 2 — RESOLVED: corpus contradiction (decision: fire on v1, labeled)

- Design §4: "Program corpus: **corpus-v2**."
- Driver: `main()` hard-codes `LAB / "corpus.u16"` (v1); its own docstring
  says the v2 swap is "not wired here yet."
- The 578-candidate per-bucket counts in design §4 are **v1 measurements**
  (verified exactly, below). On v2 they are false — see the table.

**Decision (made by head of ops, 2026-11-12): fire Gate 0 on v1, as the
skeleton intends; the driver is NOT rewired to v2.** Gate 0 asks a mechanism
question (does tilt register in served weights at all?) and both of its
criteria are arm-vs-arm on the same corpus, so a v1 read is internally
valid; BUCKETS.md option (b) sanctions exactly this german-vs-prose use of
v1. Every Gate 0 record carries `"corpus": "v1"` in code, and the result
file is labeled "v1" — never quote its losses beside v2 or ladder numbers.
(The road not taken: running on v2 would need the corpus swap **and** a new
held scheme first — v2 has only 89 held candidates total, and
`train.held_windows(data, 128)` on v2 silently returns duplicate windows,
only 89 distinct of 128 picks, which would corrupt the composite metric.)

## Verified facts (measured, not assumed)

| Check | Result |
|---|---|
| `py_compile scale-next/run_overlap.py` | **OK** |
| Guard, no `--launch` (phases gate0 and smoke) | prints plan, **exit 0**, writes nothing — `overlap-runs.jsonl`, `window-index.json`, `byte-manifest.json` all still absent |
| Smoke phase with `--launch` | raises `NotImplementedError` by design — Gate 0 is the only launchable phase |
| v1 corpus | 5,917,236 pieces, 23,113 aligned windows, **578 held candidates** |
| v1 held per bucket (measured) | gibberish 313, numeric 144, **prose 78, german 40**, lists 3 — matches BUCKETS.md / design §4 exactly |
| corpus-v2 files | `corpus-v2/corpus-v2.u16` (907,409 pieces) + `corpus-v2.json` **exist**; per-category: german 414,201 / HiveMIND docs 380,569 / edit-lab notes 112,639 pieces |
| v2 held candidates (measured) | **89 total — german 40, prose 49, nothing else.** Design §4's 578 / 78 / 40 do **not** transfer to v2. German sits exactly at the design's `MIN_BUCKET_HELD = 40` floor |
| Ladder interim (NUMBERS.md, re-read) | 2M mean **3.2745** (3 seeds), 10M seed 0 **2.9472** (n=1); 50M has **no** completed run (2-step smoke only) |

## Caveats the firing agent must carry

- **Wall time is ~45 min, not 15–25.** Design §3's estimate is superseded by
  NUMBERS.md's measured 2M rate (5.06 s/step): Gate 0 as coded trains
  3 arms × 168 cumulative steps = 504 steps ≈ 42.5 min for seed 0, plus
  ~1 min first-run `WindowIndex` build (23k windows bucketed, cached to
  `window-index.json` afterwards). Each extra seed costs another ~43 min.
- **Dose records are incremental.** Doses are cumulative targets on one
  trajectory per arm: the dose-168 record shows `steps_done: 112`
  (168 − 56) and a per-segment `flip_share_total`. Sum segments to read a
  dose; don't read the 168 line as a standalone run.
- **Only the german tilt is tested.** `gate0()` uses `TILTS[0]`; prose is
  never tilted in Gate 0. German is the defensible choice (only real
  specialty on v1; 45.7% of v2), but the report must say "german tilt,"
  not "tilt" generally.
- **Noise floor is one pair.** Default `--seeds 0`: `dist(U,U′)` is a single
  sample (U′ also differs in init, per design — it is not a pure data-order
  floor). If the Hamming ratio lands in the grey zone (≈1.5–2.5×), escalate
  to seeds 0/1/2 before calling pass or fail; don't decide on n=1.
- **Leakage asymmetry on criterion (2), v1 only.** The data audit: ~31% of
  v1 pieces are duplicates, and the german source files (Tatoeba train
  *and test*) sit inside the corpus. Both arms train on the same universe,
  but the tilted arm oversamples the german bucket — so near-duplicate
  leakage flatters T's own-bucket score more than U's. A criterion-(2) win
  of barely > 0.02 on v1 is suspect; a win ≥ ~0.05 clears this worry, and
  v2 (line-deduped) is the clean re-check if it ever matters.
- **Index cache has no corpus identity.** `window-index.json` is keyed by
  nothing; if the corpus file is ever swapped, delete the cache first or
  the sampler silently uses stale windows.
- **Ladder numbers do not block Gate 0.** Gate 0 is fixed at the 2M shape
  regardless of the ladder verdict. What the verdict *does* gate is
  everything downstream (member shape, CONFIRM-PLAN sets). Note the 10M
  "winner" is still n=1, and if the finished ladder crowns 50M, its
  confirmation is unrunnable as specified (CONFIRM-PLAN §4) — that delays
  the smoke/full run, not Gate 0.

## Launch checklist (fire in this order, when the ladder verdict lands)

1. **Confirm the lab is free:** `pgrep -af run_scale_ladder` → empty; no
   growth cycle running. (Mill yielding is fine — it preempts itself.)
2. ~~Apply the blocker-1 patch~~ **DONE** (2026-11-12) — patch applied to
   `gate0()`, recompiled, guard re-run for both phases: plan printed,
   exit 0, no files written.
3. ~~Decide the corpus~~ **DONE** — v1, labeled (decision recorded under
   Blocker 2 above). The launch report still states the choice.
4. **Fire** (from `~/workspace/edit-lab/bitnet-lab`):
   ```
   OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 ~/workspace/edit-lab/fable-validation/venv/bin/python scale-next/run_overlap.py --launch --phase gate0 --seeds 0
   ```
   Expected wall: **~45 min** (504 steps ≈ 5.06 s/step, plus ~1 min
   first-run `WindowIndex` build).
5. **Files it writes:** `scale-next/overlap-runs.jsonl` (appended; per seed:
   6 training records — 3 arms × 2 dose segments — plus 2 `gate0_pairs`
   records, plus 2 `gate0_held` records, one per dose; every record carries
   `"corpus": "v1"`) and `scale-next/window-index.json` (first run only).
   It writes **nothing** to the ladder's `runs.jsonl` and no byte manifest
   (Gate 0 path never calls `write_manifest`).
6. **Pass/fail read, exact:** for each dose d ∈ {56, 168}, from the
   `gate0_pairs` line: `ratio = hamming_tilt_vs_uniform / hamming_seed_noise`;
   from the `gate0_held` line: `margin = held_german_U − held_german_T`.
   **PASS** if at some single dose, `ratio ≥ 2.0` **and** `margin ≥ 0.05`.
   That dose sets the program's flip-denominated round budgets.
   **SUSPECT** if some dose has `ratio ≥ 2.0` and `0.02 < margin < 0.05`:
   on v1, asymmetric duplicate leakage flatters T (the tilted arm
   oversamples the german bucket, whose near-duplicates leak into held), so
   that band is **not** a pass/fail call — it routes to a clean v2 re-check
   later. Only `margin ≥ 0.05` clears the leakage worry outright.
   **FAIL** if neither dose reaches `ratio ≥ 2.0` with `margin > 0.02` →
   the overlap program stops; the finding ("tilt does not register in the
   artifact at lab budgets") is the report, and any retry (lower V during
   tilt, smaller members, longer dose) is a *new* Gate 0, not a tweak.
7. **Then, in parallel** (design §11): CONFIRM-PLAN Set A (280 steps,
   winner + runner-up, 3 seeds, ~4.2 h). The smoke stays blocked until
   Gate 0 passes **and** Set A/B set the member shape.
