# tiny-hive

A hive-minded swarm of tiny specialist models that acts as **one model**.

One task in, one answer out. Inside: a coordinator decomposes composed
tasks, routes each step to a specialist, fans lists out across **clones**
(bit-identical runtime copies of a specialist), settles disagreements by
clone vote, and records everything on a shared board. Knowledge lives in
two shared places: the **canonical weights** (every clone is born from
them) and **lessons** (`lessons.jsonl`) that every run reads.

There is no refusal layer and nothing to ablate — the members only
compute. When the hive meets something it cannot do, it does not stop:
the gap is declared, logged, and fed to the evolution loop
(diagnose → vary → select on the full domain → socialize). A false stop
is treated as the failure; the climb is the response.

Pure Python, standard library only. No GPU, no API keys, no accounts.

## The roster — 11 members, 2,861 parameters total

Each member is a small DAG of weighted units (its weights are a JSON file
in `members/`, readable and editable by hand). Every score below is
**exhaustive** — every possible input in the domain, checked against an
independent plain-Python reference:

| member | one small task | domain | params | exhaustive result |
|---|---|---|---|---|
| parity8 | parity of an 8-bit number | 0..255 | 63 | 256/256 |
| popcount8 | count of 1-bits | 0..255 | 9 | 256/256 |
| majority5 | majority of 5 bits | 0..31 | 6 | 32/32 |
| compare2 | greater / less / equal | 0..15 × 0..15 | 16 | 256/256 |
| max4 | max of four numbers | 0..9 each | 18 | 10,000/10,000 |
| sort3 | sort three numbers | 0..9 each | 27 | 1,000/1,000 |
| adder | add two numbers | 0..999 × 0..999 | 273 | **1,000,000/1,000,000** |
| subtractor | subtract (signed) | 0..99 × 0..99 | 217 | 10,000/10,000 |
| multiplier | multiply two numbers | 0..9 × 0..9 | 65 | 100/100 |
| seqnext | next term, arithmetic sequence | t 0..68, d 0..9 | 186 | 510/510 |
| divider | integer quotient | 0..99 ÷ 1..9 | 1,981 | 900/900 |

**Total: 1,023,310 exhaustive cases, all correct.** Canonical weights for
the whole hive: ~49 KB on disk. Peak RAM for the full pipeline run:
**16.9 MB** (budget was 10 GB). Full pipeline wall time: ~114 s on a
4-core CPU VM.

## The hive acting as one

- **Composed tasks** (steps chained, one member's output feeding the
  next, 3+ members deep): **30/30** on the founding roster, **38/38** on a
  fresh hive after the divider joined.
- **Fan-out:** a 40-item list task distributed across 4 clones (10 jobs
  each), results identical to reference on every item.
- **Clone voting:** 3 clones per task, majority rules. Clean vote:
  100/100.
- **Fault tolerance, measured:** corrupt **one** clone of three and the
  majority is still wrong **0/100** — the vote fully absorbs it. Corrupt
  **two** and the majority goes wrong **16/100** — that is the vote's
  breaking point, and it is an evolution trigger, not an answer: with the
  reference verifier active every wrong majority is flagged, so silent
  wrong answers stay at 0.

## Evolution — three episodes, all measured (see `optimizer_ledger.jsonl`)

1. **Growth by composition.** Division tasks arrived; the hive had no
   member and declared a capability gap (3/3 probes) instead of guessing.
   A new member, `divider`, was grown by composition —
   q = Σ_k [k·b ≤ a], one threshold unit per test — verified **900/900**
   exhaustively, then socialized: canonical weights saved, lesson
   written. A fresh hive, born afterwards from canonical weights +
   lessons alone, passes divider **900/900** and composed chains using
   it **38/38**. Learning transferred; no individual clone had to
   re-learn it.
2. **Architecture surgery.** Addition tasks arrived beyond the adder's
   0..99 world; the probe (500, 400) was declared out-of-domain, never
   truncated into a guess. The optimizer appended bit stages 7–9 to the
   adder — stages 0–6 keep their **exact original weights** (verified
   weight-identical after signal remapping) — and the grown member was
   verified exhaustively on the full new domain: **1,000,000/1,000,000**
   pairs.
3. **Damage, diagnosis, surgical repair.** Three weight/bias entries in
   the multiplier were wrecked (seeded); routine re-verification caught
   the fall: **100/100 → 0/100**. Blind diagnosis — isolated probes per
   unit, behaviour only, never the damage record — localized exactly the
   damaged units (AND units 6 and 13, plus the sum unit: a perfect match
   to the damage record, no false positives). Only those units were
   rewritten. Result: **100/100**, re-verified exhaustively, lesson
   socialized.

The optimizer's rule throughout: a change is kept only if it is a strict
improvement measured on the member's **full** domain. Every trial,
kept or not, is in the ledger with before/after numbers.

## Files

- `members.py` — the member framework, weight constructions, references, exhaustive verifier
- `hive.py` — the coordinator: composed tasks, fan-out, clone votes, board, lessons
- `evolve.py` — the optimizer: diagnosis, surgical repair, architecture growth, hill-climb fallback, the ledger
- `run.py` — birth → suites → evolution episodes → socialization tests → fault suite → final proof
- `members/*.json` — canonical weights (the socialized state of the hive)
- `lessons.jsonl` — what the hive has learned, in words, shared by every run
- `optimizer_ledger.jsonl` — every optimizer action with before/after measurements
- `results/` — baseline, suites, socialization, faults, and final proof as JSON

## Run it

```
python3 run.py     # regenerates everything from birth; ~2 minutes
```

## Honest limits

- Capability = reliable composition over the members' closed domains.
  There is no language understanding, no open-ended reasoning, no
  coding, no science here — and this README does not claim any. Tasks
  are structured (op + args); routing is by op tag.
- Domains are small and enumerable by design; that is what makes
  exhaustive proof possible. The adder shows the growth path when a
  domain must widen.
- Fan-out distributes work across clone instances in one process;
  results are identical to sequential execution, but no wall-clock
  speedup is claimed.
- The vote alone is not a guarantee: two corrupted clones out of three
  break it (16/100, measured). The verifier is what keeps wrong answers
  from being silent, and evolution is what repairs the damage.
- Evolution episodes so far were run by the optimizer (Muse) driving
  `evolve.py`; the diagnose → vary → select → socialize loop is code,
  and the surgical choices inside it are the optimizer's.
