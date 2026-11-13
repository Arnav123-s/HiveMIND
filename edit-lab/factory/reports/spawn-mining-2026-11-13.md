# Spawn mining over the factory's serving history
**Muse's work, Muse's side** (Fable-study Build 3, 2026-11-12 PT)
Machine record: `spawn-mining-2026-11-13.json` (same run, UTC stamp).
Miner: `factory/spawn_mining.py`. The decision log it will mine
from now on was added to `factory/serve.py` by this build
(`factory/serve_log.jsonl`, append-only, one line per serve()
call — it starts accumulating today; the history below is the
recorded battery/growth record).

## Decision sites noticed (spawn-trainer signal)
- **coordinate** — every call takes the same fixed answer (gap:
  tier1-backend-required). Not Tier-0 staffable (it needs the LM
  backend). Recorded, not built.
- **unregistered job / unknown kind** — fixed fail-closed gap
  answer naming its growth move. Working as designed.
- The serve log's first 37 calls (one battery run): bug-pattern
  mechanisms verified 31 / fallback-unverified 6; the waking layer
  overruled the raw composer on **14 of 37** calls — the raw
  composer is wrong often enough that the layer's correction is a
  standing failure site of the composition, counted per call from
  now on.

## Failure shapes, ranked by evidence
1. **swapped-operands, plain slice — no effective coverage.**
   Raw composed recall on the sealed set is **0.0 in all 11
   recorded measurements** (never once named on fresh material);
   dev routed recall on the plain slice is **0.0667 (1/15)** while
   every swapped seat is individually strong (binary dev accuracy
   0.88–0.96) and the strengths table routes the plain slice to
   "whole", never to the plain seat. The class is carried entirely
   by execution verification at serving time (sealed recall 1.0).
2. **wrong-operator, expression slice.** Dev routed recall 0.2581
   (8/31); the expression seat's binary dev accuracy is 0.5231 —
   chance. Already the growth lane's standing target (attacked in
   all 6 cycles; births there keep failing the serving gate). Not
   duplicated by this build.
3. **off-by-one, index slice.** Sealed raw recall frozen at
   0.3333 across all 11 measurements; dev routed recall 0.3333
   (17/51). Also a standing growth target (6/6 cycles).
4. **contract-judgment confusions** (battery wrongs, both eras):
   ok → no-empty-guard ×3, mutates-input → ok ×2 — the largest
   classify confusion cluster, but the niche has since improved
   (0.5833 → 0.9167), so this is a watch item, not a candidate.
5. **mutable-default evidence is thin everywhere** — 5 dev items,
   one seat. No failure measured; the gap is measurement depth,
   noted for the next dev-pool build.

## Candidate #1 and its gates (factory/spawn_candidate.py)
Candidate: a re-trained swapped-operands plain-slice specialist
(F.train_candidate, fmode "code", the parent seat's architecture),
data from new phase-3-style generator families, contamination-
filtered against the sealed set + phase-3 train + the dev pool.
Gate 1 = strictly beat the incumbent plain seat on BOTH of two
pristine held slices (disjoint family groups). Gate 2 (only if
Gate 1 passes) = sealed serving path, candidate configuration vs
incumbent, same session. Records:
`factory/runs/spawn-candidate-001/gate-record.json` (round 1),
`gate-record-round2.json` (round 2).

- Round 1: one-line families collapsed under the anonymized-shape
  contamination rule (train surface 44 → 12 items). Candidate
  0.5714 / 0.7143 vs parent 0.7143 / 0.7143 — **Gate 1 failed.**
- Round 2: multi-statement families (train 38, held 15 + 16 items,
  few drops). Candidate 0.5333 / 0.625 vs parent 0.6667 / 0.625 —
  **Gate 1 failed again** (loses A, ties B). Gate 2 never ran.

**Disposition: no birth. The candidate stays a recorded shadow.**
Twice measured, the conclusion is consistent: a specialist trained
on tens of fresh items does not beat a seat trained on the factory
corpus at the seat's own job — data scale is the binding
constraint, and corpus-scale training is the growth lane's
machinery (harvest + dream pools), not a mining side-build. The
mined shape itself stands: swapped-operands' raw blindness is a
composition/margin-competition problem (the learned say's
territory — currently shadow for the clean-recall reason in
`learned-say-2026-11-12.md`) or a corpus-scale growth target for a
future cycle's intake. Both follow-ups are recorded here, neither
is forced.

## What serving looks like after this build
Unchanged numbers, new instrumentation: every serve() call is
logged; future mining runs read the log first. Battery after the
build (same day): sealed bug-pattern 0.8611, classify slices
0.8333 / 1.0 / 1.0 / 0.9167 / 1.0, ternary 0.9167, tiny-hive 1.0;
audit clean; factory suite 100 passed.
