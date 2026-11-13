# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# Mill flag factory — FLAGS-BUILT (2026-11-12/13)

**What this is.** The mill pool (380 entries after the round-2 merge) had only **35 entries
runnable** against the live `train.py`; the rest were deferred on flags/arms that did not
exist. All flags below were implemented in the staging copy **`bitnet-lab/train_next.py`**
— the live `train.py` was **not** touched (the scale ladder is still running against it).
When the main agent merges `train_next.py` into `train.py`, the runnable count becomes
**222 of 380** (measured by re-running screen.py's validation logic against
`train_next.py --help`; the remaining 158 deferrals are itemised at the bottom — most are
not train.py flags at all).

**Verification method.** Every run at a tiny config (`--dim 64 --layers-n 2 --batch 8
--steps 8 --seed 0 --rope`, in `bitnet-lab/flaglab/`, records never touch the lab's runs.jsonl):
- *Baseline identity:* `train_next.py` with no mill flags vs live `train.py`, same seed —
  held_init / held_final / train_last100 / state_hist / mech_state_bytes must be
  **identical** (8 arm configs incl. `--carry` and `--cooldown`).
- *Neutral identity:* each flag present at its neutral value vs absent, same seed/config —
  identical held loss. (Store-true flags are covered by the baseline identity.)
- *Smoke:* each flag on at a pool-like value — trains, finite losses, mechanism evidence
  in the record where the design has some (e.g. `mag_thr` for --mag-cal, `level_hist` for
  --log-level-hist, `held_final_state` for --modal).
Results (2026-11-13, verify.py in flaglab/): **base 8/8 identical, neutral 28/28
identical, kernel pairs 6/6 identical, smoke1 25/25, smoke2 66/66** — every flag below
passed. Two process notes: (1) the suites were first run from /tmp and lost to a runtime
restart; the completed run above is the workspace re-run, and later confirmation re-runs
under heavy cross-stream contention produced subprocess *timeouts* (empty records) on
some base cases — never a value mismatch: every run that completed on both sides matched
exactly, and the identity claims are independently backed by per-step bitwise proofs
(flaglab/proof.py: identical per-step losses for layered_half/plain_half/ste_half vs live
train.py; fused-vs-current trainer state torch.equal; proof2.py: repeated-run
determinism). (2) The smoke case for --verify-flips originally passed the flag bare; the
pool's own run lines use `--verify-flips 200`, which is what the implementation takes
(the case was corrected to `--verify-flips 4` and passes).

**Merge notes for the main agent.**
1. `mill/sweep_probe.py` carries its own copy of the chassis argparse + run_one and has
   **neither --votes nor --wd**. Sweep-mode entries E-015 (`--cooldown --wd 0.1`) and
   E-017 (`--votes 8 --carry`) validate against train.py but cannot *execute* in the
   sweep until sweep_probe.py gains those two flags too.
2. If any new flag ever becomes champion, `sweep_probe.py` needs it as well
   (champion.json's run string is executed by the sweep for job zero). All entries using
   the flags below are process-mode today except E-015/E-017 (note 1).
3. Records gain two additive fields: `corpus` (always) and `mill_flags` (non-default
   flag values); plus `mag_thr` (mag-cal), `held_final_state` (modal), `level_hist`
   (E-013) when relevant. No existing field changed shape.

## Round-2 priority flags (parent's list, 2026-11-12 20:23 PT)

| flag | pool ids | notes |
|---|---|---|
| `--corpus NAME` | E-018, E-019, E-020, E-021 | `v1` = corpus.u16 (default, chassis), `v2` = corpus-v2/corpus-v2.u16, any other name resolves to `corpus-<name>.u16` (variant streams E-019..021 are built by the data stream; the flag errors loudly if the file is absent). Held windows always follow the same every-40th rule on the chosen stream (E-018's "v2-native held windows"). Neutral: `--corpus v1` ≡ absent. |
| `--wd X` | E-015 (also the C-B07 concept — but C-B07's run line names `--opt-wd`, a *different* flag string; see Blocked) | AdamW weight decay of the shared parts on all vote-family trainers; on Layered it is also the cooldown schedule's base — the chassis cooldown multiplied a base_wd of 0.0, so its wd component was a silent no-op; `--wd` closes that confound. On STE arms it overrides `--ste-wd`. Neutral: `--wd 0.0` (votes) / `--wd 0.01` (STE) ≡ absent. |
| `--votes N` | 27 entries: MILL-402, 501–509, 511–515, 641, 642, 651–654, 1402, 1601, 1602, A-031, A-096, E-017 | Direct + Layered threshold; counter dtype grows int8 → int16 (>127) → int32 (>32767); state bytes recorded from the real dtype. Neutral: `--votes 32` ≡ absent. |
| `--buffer B` | A-050 (D-007's `--buffer 25` is the dream *runner's* ring size — different flag, see --dream) | Sampler exclusion: training windows within B window-positions of a held window are excluded (adjacency distance on window indices, both span endpoints). Neutral: `--buffer 0` ≡ absent (chassis branch kept verbatim). |
| `--log-level-hist` | E-013 | Layered only: records `level_hist` snapshots (level-population shares + cumulative per-component flips) every 100 steps and at the end. |
| `--cooldown-noemb` | E-016 | Layered + `--cooldown`: embeddings (tok/pos/+head) form their own AdamW group whose lr/wd the schedule never scales. |

## Kernel landings (2026-11-13, from kernels/RESULTS-KERNELS.md)

| item | status | evidence |
|---|---|---|
| Complex-multiplication RoPE | **staging default** (replaces `rotated()`'s slice/stack body, same interface — no flag, per the kernel stream's recommendation) | Measured by the kernel stream: err 0.0 (bitwise) at champion + 2M shapes, 1.4–2.9× on the rope+attention path. Re-proven here in `flaglab/proof.py`: `rotated()` torch.equal at 3 shapes; full 12-step training runs (layered_half / plain_half / ste_half, rope on) bitwise identical per-step losses + held_init/held_final vs live train.py; cross-checked by flaglab/micro.py (Direct per-step state) and proof2.py (repeated-run determinism). |
| `--vote-kernel fused` | **built** (Direct + Layered; default `current`) | The kernel stream's fused update: sign computed once, flip test `(t+s).clamp(-1,1) != t` replaced by the exactly-equivalent `(s != 0) & (t != s)`, flipped value written as `t + s`, counters updated in place. Measured err 0.0, 1.7–1.8× on the update block at champion size. Verified here: proof.py part 2 (per-step losses + full trainer state torch.equal across layered default / carry / comps-3-counter / leak and Direct plain / mag), micro.py leak case, and the verify.py `pairs` suite end-to-end through main(). |
| `--matmul` (C-family: int matmul, TL2-style LUT) | **NOT built — measured and rejected by the kernel stream** | int32 matmul loses 1.7–14× and LUT loses 12–160× to plain fp32 `F.linear` in torch on this VM; a flag would only slow the mill down. The C-family entries naming a matmul variant stay deferred-by-measurement, not by missing code. |
| `--attn` manual | **NOT built — measured and rejected** | Manual attention is exact (~2e-7) but 2–7× slower than SDPA at both shapes. |
| `--rope-impl` | **covered** by the complex-RoPE staging default above | No separate flag needed; the winning implementation is simply what `rotated()` now is. |

## New arms (chassis: layered_half shape, 2 blocks, per the pool header)

| arm | pool ids | mechanism as implemented |
|---|---|---|
| `annealflip` | MILL-223, 224 | Per step, per weight: propose a neighbour move (extreme → 0; zero → ±1 **at random**), estimate dL ≈ g·Δw from the gradient already computed, accept with prob min(1, exp(−dL/T)); T anneals `--temp A:B` (default 1.0:0.05). Random proposals are deliberate: greedy proposals make dL ≤ 0 identically and the Metropolis test vacuous. |
| `disarm` | MILL-225 | Two Bernoulli logits per weight; installed state = modal b+ − b−; antithetic pair (u, 1−u) forwards per step; logits updated by the antithetic **score-function** estimator ½[(L_A−L̄)(b_A−p) + (L_B−L̄)(b_B−p)]. **Caveat:** this is the DisARM family's antithetic-coupling idea in score-function form, not the paper's exact correction term. State bytes counted STE-style: 24n + n//4 (logits + AdamW moments + packed states). |
| `resid8` / `resid16` | MILL-226, 227 | Residual accumulator r += −rate·g/quantum per step (rate 0.05 — chosen so a consistent gradient flips a weight in ~20–50 steps at lab gradient scales); a flip fires when |r| crosses one installed quantum, which is then subtracted. resid8 stores r on an int8 grid of 127 steps/quantum, resid16 in fp16; r saturates at ±1 quantum (boundary pressure is capped, not accumulated). |
| `fisherflip` | MILL-228, 229, 230 (`--share`) | Every 4 batches: rank candidate flips by ΔL̂ = ḡ·Δw + ½·F·Δw² (F = mean g² over the 4 batches); top `--share` applied tentatively, kept or undone by measured loss on a fixed check batch drawn from the *training* distribution (separate RNG 4242, never held windows); share halves on rejection, floor = initial/16. |

## Architecture flags (§A + round-2 sampler family)

| flag | pool ids |
|---|---|
| `--qk-norm` / `--qk-norm-q` / `--qk-norm-k` | MILL-101, 102, 103, A-062 |
| `--gated-attn` / `--gated-attn-lr R` | MILL-104, 106, A-062 |
| `--sink-logit` | MILL-105 |
| `--qk-clip TAU` | MILL-131, 132 |
| `--rope-frac F` / `--rope-base B` / `--nope-every N` | MILL-133, 134, 135, 905, 906, A-071 |
| `--swa L:G:W` | MILL-137, 138 |
| `--gqa G` / `--heads N` | MILL-901, 902, 903, 904 |
| `--scale-gran tensor\|channel\|group32\|group64\|group128\|boundary` | MILL-107, 108, 701, 702, 703, A-063 |
| `--wquant absmax` / `--agrid balanced` / `--learn-scale` | MILL-1011, 1012, 1013 |
| `--lowrank R` / `--hadamard` | MILL-233, 234, 129, A-063 |
| `--norm rms\|prepost\|post\|none` / `--subln` / `--no-ffn-norm` | MILL-801–804, 127, 128, A-064 |
| `--ffn gelu\|swiglu\|relu2\|relu` / `--ffn-width M` | MILL-136, 1001–1004, A-079 |
| `--emb-int8` / `--untie-head` / `--init-std S` | MILL-118, 119, 1021, 1022 |
| `--deltanet N` / `--rwkv N` | MILL-116, 117 |
| `--moe E` `--moe-top K` `--moe-shared` `--moe-hash-first` | MILL-120, 121, 122 |
| `--act-sparsify F` | MILL-130 |
| `--mtp W` / `--kd A` / `--kd-attn` | MILL-123, 124, 113, 114, 115, A-064 |
| `--repeat N` / `--ctx-curr [rev]` / `--dedup` / `--freq-balance` / `--shift-aug` | A-044, A-045, A-046, A-047, A-049, A-051 |

## Vote-trainer flags (§B/§C/§E)

| flag | pool ids |
|---|---|
| `--gate-q Q` | MILL-601–606, 611, 612, 651–654, A-002, A-067 |
| `--mag-cal X` | MILL-201, 202, 203, A-059, A-067 |
| `--vsched A:B` / `--vlayer T` | MILL-204–208, A-060 |
| `--leak L` / `--ileak N` / `--agree` | MILL-209–214, A-058 |
| `--freeze K` | MILL-215, 216, 217, A-058 (A-072 also names `--zero-bias` — still deferred) |
| `--clamp F\|none` | MILL-631, 632, 633 |
| `--flip-rule t1-first\|counter\|sign-agree\|alternate` | MILL-621, 622, 623, 624 |
| `--comps N` / `--comp-v A,B,…` | MILL-401–405, 1401, 1402, A-066 |
| `--modal K` / `--verify-flips N` / `--whiten` | MILL-218, 219, 231, 232, A-061, A-068, A-070 |
| `--hybrid F:ste\|F:votes` | MILL-220, 221, 222, A-068 |
| `--opt-lr LR` | MILL-304, 305, C-B01–C-B04 |
| `--fp-first F` / `--ease F` / `--ease-off` | MILL-111, 112, 301, 302, 303, 1308, 1309, A-060, A-065 |
| `--failweight W` | MILL-406, 407, A-061 |

## STE-recipe flags

| flag | pool ids |
|---|---|
| `--ste-lr` / `--ste-warmup` / `--ste-wd` | MILL-1301–1307 |
| `--two-stage` / `--two-stage-wd` | MILL-109, 110, A-065 |
| `--muon` / `--muon-split` | MILL-125, 126, A-068 |
| `--polish F` | MILL-306 |

## Interpretation disclosures (choices made where the pool spec left a parameter open)

1. **--mag-cal threshold:** measured once, at the first step from the first layer's
   increments: thr = max(1, round(cal × 32 × mean|inc|)); the measured value is recorded
   as `mag_thr` in the run record.
2. **--freeze window:** flip counts are taken over trailing 40-step windows; the modal
   state comes from state snapshots taken every 10 steps inside the window.
3. **--verify-flips parameters:** candidates are weights with |counter| ≥ V−4, tried in
   descending |counter| order, at most 32 per call, judged on one fixed check batch from
   the training distribution (never held windows — no leakage by construction).
4. **--clamp 0.5 (MILL-633) consequence, implemented literally:** counters saturate at
   ±16 < V=32, so **no flip can ever fire** under that entry as written. The flag does
   what the run line says; the entry's premise (a tighter clamp as a regulariser) cannot
   express itself through this mechanism — flagged here rather than silently reinterpreted.
5. **MILL-621–624 vs the code:** the entries describe the chassis as flipping both
   components at once; the actual chassis Layered flips at most one component per weight
   per step (first component first, boundary no-ops pass the turn). So `--flip-rule
   t1-first` (MILL-622) **is** the current chassis behaviour, implemented as the explicit
   control; counter / sign-agree / alternate differ as designed.
6. **--fp-first on vote arms** acts through the EASE path (FP forward = ease 0), per the
   pool's own definition of the schedule.
7. **--kd budget split:** the run's first half trains an FP twin (same arch, STE trainer,
   EASE pinned 0) on the same batch stream; the second half trains the student with
   CE + α·T²·KL (T=2); `--kd-attn` adds last-block attention-probability KL.
8. **--whiten form:** per-layer RMS normalisation of the gradient field + orthonormal
   Hadamard rotation before signing; the log-scale gradient keeps the original g.
9. **--two-stage-wd:** "cosines to 0.1" read as a stage-1 cosine ramp 0 → 0.1, wd = 0 in
   stage 2.
10. **--vlayer controller:** per-layer, per-component threshold multiplier tracking the
    flip-rate EMA (×1.05 above target, ×0.95 below half-target).
11. **--agree first step:** step 1 has no previous pull, so no votes count on step 1.
12. **New arms' chassis:** annealflip/disarm/resid8/resid16/fisherflip run on the
    layered_half chassis (2 blocks) per the pool header ("unless an entry says
    otherwise, probes run on layered_half + rotary").
13. **--src-balance (A-048) NOT built — impossible as written:** corpus.json lists the
    393 source *names* but no per-file piece counts or offsets, so file boundaries in
    the flat stream are unrecoverable from train.py. Needs a corpus sidecar (per-file
    piece counts) from the data stream; the flag was deliberately *not* added, so
    screen.py keeps A-048 deferred instead of failing it at runtime.
14. **E-019/E-020/E-021 corpus variants** (`v1-leak-excised`, `v1-nomega`,
    `v1-node-test`) do not exist as files yet — `--corpus` resolves the names the day
    the data stream builds them; today those entries still defer at the *file* level
    (the flag itself is in place and E-018 runs).

## Still deferred after this round (158) — by owner, not by flag-factory capacity

- **Companion dream runner** (`dream.py`/`run_dream.py`): D-001..D-007 (`--dream …` are
  runner flags; the pool itself specifies train.py stays untouched). Separate build.
- **Hive factory / kernel streams:** E-001..E-009, E-024 (`--factory`), C-C01..C-C06,
  B-023..B-031 (`--matmul`, `--vote-kernel`, `--kernel-bench`, decode/layout flags).
- **Corpus build pipeline:** B-001..B-013 (`--corpus-filter`, `--corpus-dedup`,
  `--corpus-rewrite`, `--tokenizer`, `--mixture`, `--epochs`, `--filter-sweep`,
  `--mix-synth`) — make_corpus-side tooling, plus A-048 (note 13).
- **Methodology markers, not flags:** E-014 (`--long-format`), E-022 (`--audit`),
  E-023 (`--probe-format`), FABLE-CAND-01 (`--paired-timing`) — these entries run by
  hand/audit, by their own text.
- **JEPA arm:** E-011, E-012 (`jepa_half_rope` lives in the run_jepa.py lineage).
- **Round-2 A-wave long tail (~90 single-entry flags):** --soft-gate, --gate-scope,
  --vote-every, --vote-stat, --deadband, --race, --hyst, --thrash-tax, --zero-bias,
  --vote-norm, --vote-ema, --vote-ema2, --tokw-loss, --shared-counter, --flip-prob,
  --flip-batch, --flip-cap, --flip-stagger, --quarantine, --comp-reset, --rebound,
  --vtail, --vwarm, --flip-eps, --vdepth, --vrole, --mixed-depth, --hybrid-depth,
  --vhead, --vscale, --width-depth, --role-split, --vcycle, --gate-ease, --grow-comps,
  --collapse, --freeze-tern, --alt-phase, --opt-warmup, --gclip, --curr, --span-noise,
  --batch-mix, --regress-weight, --coverage, --drop-worst, --ema-readout,
  --verify-fisher, --polish-votes, --zero-init-out, --deepnet-scale, --softcap,
  --act-ternary-v, --qk-scale, --attn-temp, --rope-nopos, --head-ternary, --premix,
  --bigram-emb, --act-clip, --layerscale, --qk-norm-post, --rope-v, --head-dim, --ctx,
  --gate-resid, --emb-norm, --no-final-norm, --median-readout, --avg-readout,
  --best-ckpt, --counter-w, --opt, --opt-wd, --betas, --accum, --ls, --zloss, --aux-nn,
  --ema-teach, --dropout, --loss-clip, --focal, --attn-ent, --dual-vote,
  --counter-reset, --revive, --scale-polish, --init-majority, --init-hist,
  --cautious-votes, --ewgs, --spinquant, --quarot-full. (Note: several are near-aliases
  of built flags under different names — --opt-wd vs --wd, --opt vs --opt-lr — a pool
  naming decision, not an implementation gap.)
