# FABLE-CANDIDATES — transferable ideas mined from Fable's side (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Fable's side was read READ-ONLY; nothing here touches it. -->

Filed 2026-11-12 ~20:12 PT from the Fable trace re-check. Source push: two new commits on
`make-it-work` / `claude/epic-johnson-7ene30`, 725b2020 → f517a363:

- `61fb32539fc6d76b7c44c81e76a3dbd186045347` — members-first default (seed 9007), exam tables
  (9006, 9007), BitNet runtime check changes in exam.yml
- `f517a363bb0d064d71213fe4ded0ef3a2c8b7921` — HANDOFF.md note recording the Jamie history
  rewrite landed on GitHub (already known on Muse's side; Muse executed that rewrite)

`main` (31a67562) and `hivemind_muse` (980c0b5f) did not move.

---

## FABLE-CAND-01 · Paired side-by-side timing — wall-clock comparisons are only valid between concurrent runs

- **source:** `61fb325`, HANDOFF.md 2026-11-13 04:15 UTC section: "Times on GitHub are not a
  measure. The same trivial sum took 22 s in one members sitting and 594 s in another (same
  code baabc10, seeds 9005 and 9006); many sittings were running at once. Compare times only
  between sittings that ran side by side."
- **mechanism:** shared/contended CPU makes a fixed `--minutes` budget buy a variable number
  of steps (here: a 27× swing on identical work). Any speed or equal-minutes comparison made
  across non-concurrent runs is measuring load, not the arm.
- **maps onto Muse's side:** `mill/` methodology, not a train.py arm. train.py budgets are
  wall-clock (`--minutes`), and the mill's probes/trials inherit that. Concrete adoption:
  (a) any future "X is faster / equal-minutes" claim in the lab requires a paired,
  side-by-side re-run of both arms (the concurrency study's honesty protocol already pairs
  solo-vs-concurrent; extend the same pairing rule to arm-vs-arm timing claims);
  (b) ledger lines for verdict-bearing runs should be read alongside concurrent load —
  a held-loss delta from a contended window is suspect until re-run solo.
  This independently confirms the rigor audit's contention-asymmetry finding with an
  external, quantified example.
- **status:** candidate — methodology adoption, no code change needed to start applying it.

## FABLE-CAND-02 · Microsoft BitNet runtime validation recipe — use the runtime's own gguf-py; build the May-2025 runtime without its requirements

- **source:** `61fb325`, exam.yml `bitnet` job changes + `training/reports/bitnet_runtime_check_2026-11-13_second.txt`.
- **what Fable's side found:** converting the published bf16 weights with the public gguf
  package fails with `KeyError: <MODEL_ARCH.BITNET_25: 83>` — the converter needs the
  runtime tree's own package: `pip install ./3rdparty/llama.cpp/gguf-py`. The May-2025
  (2025-05-31, c1e9a9a) runtime's `requirements.txt` does not build on a modern Python
  (sentencepiece wheel fails); since the model GGUF is already built, the fix is to install
  only the runtime's gguf-py and run `setup_env.py` directly, skipping requirements.
  Second check still reproduces the fault with the published file: **PPL = 70.2536 ± 7.71118**
  and the same repetition loop — current-runtime fault stands; the two fixes above are
  queued in exam.yml but their results have **not landed yet**.
- **maps onto Muse's side:** NOT a train.py arm — train.py trains from scratch and never
  converts GGUF. It maps to the kernel/runtime cross-check work: if Muse's side validates
  its own kernels or numbers against Microsoft's published BitNet-b1.58-2B-4T model or the
  May-2025 runtime, use this exact recipe (runtime-bundled gguf-py; requirements-free old
  build) instead of rediscovering the two failures. Until Fable's re-run lands, treat
  PPL ~70 as the standing reference fault, not as a target to reproduce against.
- **status:** candidate — reference recipe for the kernels phase; no mill entry until a
  runtime cross-check job is actually scheduled.

## FABLE-CAND-03 · Members-first routing — clean-sitting evidence for soloists-first, roles as fallback

- **source:** `61fb325`, seed 9007 sitting (never looked at before, nothing learned, code
  db8b8d0, all three arms run at the same time): **members first 10/16 in 179 min; roles
  alone 9/16 in 178 min; members alone 9/16 in 69 min.** Fable's side changed `ask.yml` to
  default to members-first (`members: "2"`; `"0"` = roles alone) on this evidence.
  Seed 9006 table (also newly filed): members alone **8/16 in 181 min** (code baabc10).
- **mechanism:** generalist members attempting the whole task first, with the role pipeline
  only taking what members cannot confirm, matched the full pipeline's score at ~40% of the
  wall time (members alone) and beat it by one task when combined (members first).
- **maps onto Muse's side:** NOT train.py / the BitNet mill — this is a factory serving
  composition finding. It maps to `factory/serve.py` routing and the composition research
  queue: a "soloist-first, specialists-as-fallback" routing arm is now evidence-backed on
  Fable's side and worth a dev-only composition test on Muse's side (alongside, not
  replacing, the learned-say work). Note the correlated-failure caveat from the same
  HANDOFF section: on "mend a program," both members ran the broken program and *agreed on
  its wrong output* — agreement between members who used the same method is not independent
  verification; any members-first gate on Muse's side must check by a different method.
- **status:** candidate — for the factory composition queue, not the mill pool.

---

## Checked in this push — NOT new, deliberately not filed as candidates

- **Growth at equal work** (6420 block-steps: 4 blocks 3.1017, grown 4→6 3.1704, 6 blocks
  3.2837) — restated in the new HANDOFF section; already in Muse's side's records from the
  previous trace. No change.
- **Seed 9008** — mentioned only as the *pending* sitting for the looser summary comparison
  (e312329). No 9008 table or result exists in the push. Still outstanding.
- **New recipe defaults** — none. The only default changed is `ask.yml` routing
  (FABLE-CAND-03). Founding recipe defaults (rotary + falling rate + EMA readout) unchanged.
- **BitNet runtime verdict** — unchanged: PPL 70.2536 on GitHub's CPU with the published
  file in the second check; the gguf-py and requirements-free-build fixes are in the
  workflow but no post-fix measurement has landed yet.
