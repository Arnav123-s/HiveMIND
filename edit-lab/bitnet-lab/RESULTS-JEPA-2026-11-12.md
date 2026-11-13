# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# JEPA-in-BitNet — does LeCun's objective beat next-token training for a ternary trunk? (2026-11-12)

Arnav's idea (IDEA-LOG, 2026-11-12 13:01 PT): "LeCun's JEPA paper — the way he made the
small model insanely good — how about doing that, but the same thing in BitNets, for what
we are building." The reference result (Balestriero & LeCun, arXiv:2610.39302; research
note `lecun-feifei-small-specialists-2026-11-10.md`): a 109M text JEPA beat 70B LMs on
representation alignment, because its positive pairs are "good views" — two independent
observations of one underlying thing — and it predicts in representation space instead of
token space. This experiment transplants the OBJECTIVE into Muse's side's BitNet lab.

## Design (fixed before any probe number existed)

- **Chassis — the lab's current best stack, unchanged:** layered vote trainer (two-component
  layered ternary weights), half size (2 blocks, 884,736 ternary weights, 1,725,696 total
  params), rotary positions. Round 2 (carry / cooldown) produced no winner, so nothing
  displaced it (baseline held token loss 2.8580 ± 0.0161). **Vote mechanics are identical
  in both arms — only the training objective differs.**
- **Control (`jepa_ctrl_half_rope`):** next-token loss — the lab's `layered_half_rope` arm
  re-run inside this experiment so the trained trunk could be saved and probed. Same seed →
  same init (held-init matched the recorded values exactly, all three seeds) and the same
  window stream as the JEPA arm.
- **JEPA (`jepa_half_rope`):** the student trunk sees each 256-token window with one
  contiguous block of 64 positions replaced by a learned mask embedding (view 1: the span
  with a hole). A small fp predictor (2-layer MLP, 192→192→192) maps the context
  representations at the masked positions to the representations a **target encoder** —
  an EMA (momentum 0.99) copy of the student, stop-gradient — produces for the same
  positions from the clean window (view 2: the complete span). Loss: smooth-L1. This is
  the standard I-JEPA recipe. The predictor is training scaffolding (AdamW-trained with
  the trunk's other non-ternary parts) and is discarded at probe time.
  - *"Good views" for text, concretely:* partial vs complete observation of the same
    underlying text. Stated caveat: the views share tokens, so they are not as independent
    as the Platonic paper's cross-modal pairs; masked-span prediction is the canonical
    JEPA adaptation to a single token stream, and this corpus (one flat stream, no paired
    renderings) can honestly supply nothing more independent.
- **Budget:** 3 seeds × 8 minutes per arm, same corpus (~5.92M pieces), same wall-clock
  discipline as every prior arm. JEPA steps are cheaper (its loss has no vocab-head
  matmul), so it took more steps (mean 185 vs control 142) — equal time, not equal steps.
- **Yardstick — linear probe (token loss cannot judge a JEPA model):** freeze each trunk;
  fit ONE fresh linear readout (192→4096, Adam lr 1e-2, 150 steps, batch 32, positions
  strided ×2, fixed probe seed) on non-held windows; measure next-token cross-entropy of
  the probe on the lab's standard 128 held windows. The **untrained init trunk** of each
  seed was probed too (the floor). The probe measures how much next-token information is
  linearly readable from the frozen representations. It does NOT measure generation
  quality or cross-modal-style alignment, and it is structurally generous to the control,
  whose training signal is exactly next-token prediction — a JEPA win here would have
  been a conservative claim; a JEPA loss here is a real loss *for this lab's purpose*.
- **Pre-registered verdict rule:** JEPA WIN = probe CE below control on ≥2 of 3 seeds with
  mean margin > 0.02; LOSS = mirror; else TIE/INCONCLUSIVE. Sanity gates: control held
  token loss within ~0.10 of the 2.8580 baseline mean; trained arms probe clearly below
  the init floor.

## Results — probe CE on held windows (lower is better)

| seed | control | JEPA | init floor | steps ctrl / jepa |
|------|---------|------|-----------|-------------------|
| 0 | 2.8547 | 3.2792 | 3.2475 | 159 / 211 |
| 1 | 2.9167 | 3.2657 | 3.2725 | 129 / 171 |
| 2 | 2.9091 | 3.1834 | 3.2134 | 139 / 172 |
| **mean ± sd** | **2.8935 ± 0.0338** | **3.2428 ± 0.0519** | **3.2445 ± 0.0297** | |

- Control beats JEPA on **3 of 3 seeds**; paired margins −0.4245 / −0.3490 / −0.2743,
  mean **−0.3493** — seventeen times the 0.02 bar.
- **JEPA vs the untrained floor is a coin flip:** paired differences +0.0317 / −0.0068 /
  −0.0300, mean −0.0017. After 8 minutes of JEPA training, the trunk's representations
  carry no more linearly-readable next-token information than the random init's.
- Per byte: serving bytes are identical for both arms (mechanism state 2,211,840 B, same
  chassis), so the ranking above *is* the per-byte ranking. JEPA additionally spent
  7,794,432 B of training-only state (EMA copy 6,902,784 B + predictor AdamW state) that
  the control does not need.
- Sanity gates: control held token loss 2.8631 / 2.9606 / 2.9283 (mean 2.9173, within
  0.06 of the 2.8580 baseline mean — gate passed; the per-seed elevation on seeds 1–2 is
  step count: the VM ran slower during the re-run window, 129–139 steps vs the original
  154–170, the same machine-speed variance the half-control round documented; probe wall
  times rose in step, ~121 s → ~155–170 s). Control probes clearly below the floor
  (−0.3510 mean) — training and yardstick both demonstrably work. JEPA fails the
  below-floor gate *on the probe*, which is the finding, not a malfunction (next section).

## The JEPA machinery worked — the transfer didn't

JEPA training itself was healthy on every seed: prediction loss fell ~4–5×
(first-50 mean 0.086–0.092 → last-50 0.019–0.023), and target-representation diversity
*rose* (per-dimension std 0.29–0.32 → 0.36–0.48) — **no representation collapse**. The
trunk genuinely learned to predict masked-span representations. What it learned simply
does not include the token-level information a linear readout can use: at this scale the
JEPA signal reaches the trunk only through 64 masked positions per window and only
through the predictor, while the EMA target (momentum 0.99 over ~170–210 steps) is still
partly the random init early in the run — the trunk spends much of its budget learning to
match a moving, partly-random target's geometry instead of organizing token information.

## Verdict

**LOSS for the JEPA objective in this lab, under this yardstick, at this scale and
budget.** Transplanting LeCun's objective onto the vote-trained ternary trunk produced
representations indistinguishable from untrained ones for next-token readability, while
the same trunk trained on next-token loss improved the probe by ~0.35 nats. The layered +
rotary + plain-votes stack trained on the token objective stands unchanged.

Honest bounds on the claim — what this does NOT show:
- It does not test JEPA's home metric. LeCun's win is on representation *alignment* and
  abstraction-style probes; this probe measures token readability, the home metric of the
  opposing method. A JEPA trunk might still win an alignment-style contest; this lab has
  no such yardstick built, and building one to rescue a loss would be moving the posts.
- It does not refute JEPA at scale. The reference result is 109M parameters trained far
  longer; this is a 0.885M-weight trunk at 8 minutes. The claim is bounded to: at lab
  scale and budget, for the token work this lab's models actually do, the objective
  transplant does not pay.
- The likeliest mechanism (sparse indirect signal + partly-random EMA target early) is a
  hypothesis consistent with the traces, not a separately tested result.

## Code and records (all in this lab, Muse's side only)

- `run_jepa.py`: the experiment — chassis import from `train.py`, `JepaModel`
  (trunk + predictor + mask embedding, trained by the unmodified `Layered` vote trainer),
  EMA target, probe implementation, pre-registered verdict rule in the docstring.
- `runs.jsonl`: 6 records appended (`jepa_ctrl_half_rope` ×3, `jepa_half_rope` ×3) with
  probe fields (`probe_held_ce`, `probe_init_floor_ce`) and JEPA's extra training state.
- `jepa-states/`: the six saved trunk state dicts; `jepa-runs/`: per-seed checkpoints.
- Logs: `jepa-smoke.log` (1-minute validation: control held-init 8.3138 matched the
  recorded value exactly before any full run), `jepa-driver.log`, `jepa-driver2.log`.

## Run-integrity note

A runtime restart killed the first full run during seed 1's JEPA arm (seed 0 was complete
and checkpointed; seed 1's control trunk survived on disk but its in-memory stats did
not). The driver was relaunched under identical settings: seed 0 skipped from its
checkpoint, seed 1 re-run from scratch (same seeds, same budgets, no changes of any
kind), seed 2 fresh. Only the completed runs are recorded — the same recovery the
round-2 note documents for its two restart-killed runs.
