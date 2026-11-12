# ASSEMBLY — the final product, switched on / usable / growing (2026-11-10)

Arnav's ruling (18:31 PT): the final product was **not ready**,
because (1) proven fixes weren't switched on, (2) he couldn't use
it, (3) it didn't grow. This file is the work record for all
three, with before/after measurements. Run record:
`factory/runs/assembly-2026-11-10/` (pre-assembly snapshots,
candidate measurements, diagnosis). Serving rule held throughout:
nothing serves unless its measured battery slice is >= the
incumbent's, and `factory.audit` (files + `verify_rule` + score
re-measurement) passes on the final book.

## Item 1 — what's switched on now

### (a) Bug-pattern: the waking-dream layer is the serving path

`factory/serve.py` now answers `bug-pattern` through the
waking-dream wrapper (registered in the registry as the
composition's `serving_layer`, its code file sha256-hashed into
the book and audited like an artifact). Margins from the
untouched fp member binaries nominate candidates; a candidate
serves only if it proves its behavioral signature by execution;
when nothing verifies, the raw composer verdict stands, flagged.
Provenance on every answer says whether verification fired.

Evidence: sealed v2 **0.8333** served (was 0.4444 raw) — the full
audit now re-measures both numbers and both reproduce exactly
(raw baseline 0.4444; serving-layer sealed 0.8333).

### (b) BitNet scale-arm singles: adopted per niche, under the gate

Each candidate was re-measured in the factory's own harness
(subject held-out sets + the acceptance battery items) BEFORE
adoption — the scale-arm's numbers reproduced exactly
(`candidate_measurements.json` in the run record). Serving goes
through a new runtime (`factory/tern_runtime.py`): the corrected
BitNet forward (RMSNorm + int8 activation quantization) is not
the TinyNet forward, so the npz payloads serve as themselves,
behind registry records whose payload sha256 the audit verifies.

| niche | before (fp) | now serving | battery (inc → cand) | held-out (inc → cand) |
|---|---|---|---|---|
| error-class | error-class-model (fp) | **error-class-model-v2 (ternary)** | 1.0 → 1.0 | 0.9583 → **0.9833** |
| gap-move | gap-move-model-v2 (fp) | **gap-move-model-v3 (ternary)** | 0.8 → **1.0** | 0.9333 → **0.9444** |
| secret-line | secret-line-model-v2 (fp) | **secret-line-model-v3 (ternary)** | 0.8333 → 0.8333 | 1.0 → 1.0 |
| contract-judgment | contract-judgment-model-v2 (fp) | unchanged (fp) | 0.9167 → 0.9167 (tie) | 1.0 → 1.0 (tie) |
| commit-type | commit-type-model-v2 (fp) | unchanged (fp) | 1.0 → 1.0 | 0.9625 vs cand 0.9375 |

- **Contract stays fp, by the task's own condition:** the scale
  single ties on battery and held-out but regresses on the fresh
  confirm set (0.7778 vs the incumbent's 0.8889, n=9). "If in
  doubt, leave contract fp" — both the regression and the doubt
  apply. The candidate measurement is on record.
- **Commit-type stays fp:** held-out 0.9375 < 0.9625 — fails the
  dual criterion outright.

### (c) Secret-line reconciliation: one default, one alternate

- **Default:** secret-line-model-v3, the scale-arm single — the
  only secret-line ternary that satisfies BOTH adoption criteria
  (battery >= incumbent AND held-out >= incumbent; it ties both).
- **Registered alternate:** the founder pack
  (secret-line-model-ternary, Phase C PTQ + flip surgery) stays
  in the registry's substrate slot, audited and reachable via
  `--substrate ternary`. Its battery slice is the best ever
  measured for this niche (0.9167), but its held-out (0.9385)
  trails the fp incumbent's 1.0, so under the dual criterion it
  does not take the default. Under a battery-only reading it
  would serve — the numbers for both readings are here; the
  stricter one was applied.
- The fp v2 remains in the fallback chain (`--substrate fp`).

### Battery: before / after (acceptance battery, served path)

| check | bar | pre-assembly | post-assembly | Δ |
|---|---|---|---|---|
| classify-secret-line | 9/12 | 0.8333 | 0.8333 | 0 |
| classify-error-class | 9/12 | 1.0 | 1.0 | 0 |
| classify-commit-type | 9/12 | 1.0 | 1.0 | 0 |
| classify-contract-judgment | 9/12 | 0.9167 | 0.9167 | 0 |
| classify-gap-move | 6/10 | 0.8 | **1.0** | +0.20 |
| bug-pattern composed, sealed v2 | 0.80 | 0.4444 (missed) | **0.8333 (met)** | +0.3889 |
| classify-secret-line-ternary (alternate) | 9/12 | 0.9167 | 0.9167 | 0 |
| tiny-hive ops + OOD refusal | 21/21 | 1.0 | 1.0 | 0 |
| **overall (these 8 checks)** | | **0.8639** | **0.9375** | **+0.0736** |

No slice regressed (worst Δ = 0). Composites b1–b6 measure
team.Hive end-to-end — a system this assembly did not touch
(coordinator and LM backend byte-identical); they were re-run in
the same pass (log: `battery_b.log`). First result in: b1 failed
again on its external dependency — the coordinator gave up after
3 attempts because the arXiv API answered HTTP 400 (pre-assembly
it was a full outage; same dependency, different weather). The
composites remain Tier-1's known weakness and are not an
assembly effect either way.

Full audit on the assembled book: **OK** — every file hash
(records + ternary payloads + waking-dream layer), the serving
rule re-derived, and every serving score re-measured to its
recorded value (incl. both bug-pattern sealed numbers above).

## Item 2 — usable: one command

`~/workspace/edit-lab/hive.py` (+ `USAGE.md`). Plain text in,
answer + provenance out, through the audited serving path only.
Demonstrated end-to-end (real outputs, 2026-11-10):

```console
$ python3 hive.py secret 'api_key = "sk-live-9f27ac41bd"'
ANSWER: secret
served by: secret-line-model-v3 (ternary, held-out 1.0)
artifact:  coding/swarm/models/secret-line-model-v3.json sha256:2cd39132633392ae…

$ python3 hive.py error 'Traceback (most recent call last):
  File "app.py", line 14, in <module>
    print(user["email"])
KeyError: email'
ANSWER: KeyError
served by: error-class-model-v2 (ternary, held-out 0.9833)

$ python3 hive.py commit 'repair the broken cart total calculation'
ANSWER: fix
served by: commit-type-model-v2 (fp, held-out 0.9625)

$ python3 hive.py contract --file snippet.py      # def head(xs): if xs is None: return None; return xs[0]
ANSWER: no-empty-guard
served by: contract-judgment-model-v2 (fp, held-out 1.0)

$ python3 hive.py gap 'the model keeps failing on inputs it has never seen; we need broader training coverage'
ANSWER: harvest
served by: gap-move-model-v3 (ternary, held-out 0.9444)

$ python3 hive.py bug --file buggy.py             # def slope(x1, y1, x2, y2): return (x2 - x1) / (y2 - y1)
ANSWER: swapped-operands
served by: bug-pattern-composed (14 members) + waking-dream serving layer
waking-dream: VERIFIED swapped-operands by execution (composer alone said clean)
sealed evidence: served path 0.8333 vs raw composition 0.4444 (bar 0.8)
```

The bug example is the layer earning its keep: the raw composer
called that snippet **clean**; verification proved the operands
are swapped and overruled it.

## Item 3 — growth: NO BIRTH. A measured floor, with numbers.

The intake scan finds exactly **two** live birth candidates —
every other slice's parent already scores 1.0, has no held items,
or already has a child:

| candidate | parent slice acc | held n | to be born, child needs |
|---|---|---|---|
| wrong-operator / expression | 0.85 | 20 | >= 0.90 (18/20) |
| off-by-one / index | 0.95 | 20 | 1.00 (a perfect 20/20) |

### Diagnosis (per-item, before any repair)

On the gate's held slice, the parent misses 3 items
(wrong-operator) and 1 item (off-by-one). Fresh children across
all six training configs (text/code x hidden 0/4/8) miss
**the same items** (record:
`factory/runs/assembly-2026-11-10/growth_diagnosis.json`):

- wrong-operator #6: `def remainder(a, b): return a - b` —
  missed by the parent and **6/6 configs**.
- wrong-operator #9: `def minutes(hours, mins): return
  hours * 60 - mins` — missed by the parent and **6/6 configs**.
- off-by-one #3: `def first_two(xs): return xs[1], xs[2]` —
  missed by the parent and every text config.

All three labels are **intent read from the function's name**:
`a - b` is behaviorally a perfectly good function; it is only
"wrong" because the name says *remainder*. That fact drives
everything below.

### Repairs — one mechanism at a time, win-gate untouched

Parent and child were always measured on the same held slice in
the same process; the gate (child must strictly beat parent)
never moved. Each cycle: 6 configs, best child reported.

| cycle | mechanism changed | child train (wrong-op) | wrong-op child | off-by-one child |
|---|---|---|---|---|
| Phase C baseline | slice-only, default dream pool | 102 items / 19 pos | 0.85 (tie) | 0.95 (tie) |
| assembly-growth-001 | dream pool **x8** (data quantity) | 558 / 119 | **0.80 (worse)** | 0.95 (tie) |
| assembly-growth-002 | full template distribution + slice x3 | 354 / 69 | 0.85 (tie) | 0.95 (tie) |
| assembly-growth-003 | full dream-pool distribution + slice x3 | 2,918 / 697 | **0.65 (much worse)** | 0.95 (tie) |

Capacity is not the lever either: in the diagnosis grid, hidden
4 and hidden 8 never beat the linear config on either slice,
and code features never beat text features. (One caveat on
cycle 002, on record: the phase-3 template generator's set size
varies with process RNG state — 48 items in that run vs ~240 in
the intake scan — so its "full distribution" leg was thin.
Cycle 003 is the proper test of the same idea, with the
deterministic 1,244-item verified pool, and it is the worst
result of the four: breadth dilutes the slice signal.)

### What blocks births — the floor, stated exactly

1. **The data supply cannot express the missing signal.** The
   dream engine's labels are execution-verified by construction:
   a family's "correct" and "mutated" versions are proven apart
   by behavioral probes. Name-intent labels are not
   execution-verifiable — no probe can prove `remainder` must
   use `%`. The three stubborn items all live on exactly that
   axis, so no amount of dream data teaches them; scaling the
   supply only dilutes what the child does learn (0.85 -> 0.80
   slice-only x8; -> 0.65 full-pool).
2. **Gate granularity.** The held slices are n=20, so one item
   is 0.05. Off-by-one's parent sits at 0.95: a birth requires
   perfection, and the single blocking item is one every
   learner tried has missed. Wrong-operator needs 18/20 while
   2 of its items are missed by every model trained under every
   regime above.
3. Best child score ever recorded on either slice, across
   4 regimes x 6 configs: **equal to the parent, never above.**

What would change this (named, not done): a name-intent data
family whose labels come from naming convention instead of
execution — a new generator class, which this task scoped out
("use the dream engine as the data supply rather than building
a new generator"); or parent-initialized fine-tuning, which the
training code cannot currently do (`train_candidate` has no
init-weights path). Neither is a knob on the existing machine.

**Registry and battery are unchanged by Item 3** — no birth, so
nothing was adopted and nothing regressed. The growth machinery
itself works end to end (intake scan, gated attempts, lineage
records in `factory/runs/assembly-growth-001..003/`); what is
missing is a demonstrated birth, and this section is the
evidence of why.

## Readiness, against Arnav's three tests

1. **Switched on — YES.** The waking-dream layer serves
   bug-pattern (sealed 0.8333 vs 0.4444 raw); three BitNet
   scale-arm singles serve error-class, gap-move and secret-line
   under the dual battery + held-out gate; contract and
   commit-type stay fp for measured reasons stated above.
   Battery overall 0.8639 -> 0.9375 with no slice regressing;
   full audit passes; test suite 50/50.
2. **Usable by Arnav — YES.** `python3 hive.py <niche> 'text'`
   from `~/workspace/edit-lab`, with USAGE.md; every niche
   demonstrated end-to-end above, including a bug-pattern case
   where verification overruled the raw composer.
3. **Grows — NO, not yet.** Zero births across four training
   regimes with the win-gate intact. The block is measured and
   mechanistic (execution-verified data cannot carry name-intent
   labels; n=20 gate slices demand near-perfection), not a
   tuning gap. The product improves by adoption (Item 1) and
   serves (Item 2); it does not yet grow by birth.


---

## Addendum — Growth Cycle 1 (2026-11-11)

Arnav authorized a real growth loop ("keep growing and getting smarter and better too, learn from Fable or better ways if needed, improvise if needed"). Both named levers were built, plus the runner, and Cycle 1 was run end-to-end. **Result: no births. Served battery unchanged at 0.9375; full audit OK; tests 50/50; registry, composer config, and waking-dream results byte-identical to pre-cycle snapshots (hash-verified).**

### What was built

- **Lever 1 — name-intent data family** (`factory/name_intent.py`; data in `growth/data/`): labels defined by construction — a function's declared name intent vs its body — not by execution. Intent specs (remainder→%, quotient→//, difference→−, product, sum_pair, max/min, minutes, percent, average_pair, clamp, average_list, total_list, first_two, last_element, first_k, element_at, last_two, sum_first_k) with correct bodies, intent-violating mutations (wrong-operator / swapped-operands / off-by-one), and neutral-name controls (compute/calc/do_op) so a specialist cannot learn "name always lies" or "name always tells". Held partition is disjoint in intent-bearing names, variable pairs, and idioms. Train 757 items; held 694 items. The family filters in text mode (name-preserving) — the code-mode anonymized-shape contamination filter would delete the name signal, which is the entire point of this family.
- **Lever 2 — parent-initialized fine-tuning** (`coding/swarm/factory.py`): `_init_arrays()` seeds a candidate from its parent TinyNet's sparse weights (parent features first in vocab, new features appended at zero); `train_candidate(..., init_from=..., lr_scale=...)` inherits the parent's architecture/classes and raises on incompatible init (fail-closed). Verified: 5 steps at lr_scale 0.01 drifted shared weights by max 0.0025.
- **Growth machinery** (`factory/growth.py::attempt_birth`): optional `extra_train`/`extra_held` (dual gate — a winner must beat the parent strictly on the phase-3 held slice AND the name-intent held slice), failure weighting (parent-wrong diet items duplicated once; borrowed from Fable's found-on-failure), and an init arm (parent architecture, epochs {300, 800} × lr_scale {0.3, 1.0}, diet = slice + name-intent + 85-item replay). All new parameters are keyword-with-defaults; the legacy call path is unchanged. Registry sealed-evidence chain extended to supersede with `results/bug_heldout_v2_growth-<cycle>.json`; a rolled-back birth deletes its judge file and the chain falls back.
- **Runner**: `python3 -m factory.growth_cycle [--cycle-id growth-cycle-001]` — served battery BEFORE → failure harvest → learned-say experiment (measured only) → dual-gate birth attempts (scratch + init arms) → on birth: sealed judge + waking-dream refresh + registry rebuild + battery AFTER + full audit, with whole-cycle rollback on any regression or audit failure → report to `growth/<cycle>.md` + `<cycle>.json`, append-only `growth/ledger.jsonl`, factory lineage entries. The sealed v2 set is touched only the way the audit touches it; candidates are never selected on it.

### Cycle 1 results (85.7 s wall)

| target | parent phase-3 (n=20) | parent intent | best child phase-3 | best child intent | verdict |
|---|---|---|---|---|---|
| wrong-operator/expression | 0.85 | 0.6326 (n=694) | 0.90 (scratch code h=4) | 0.7882 (scratch text h=4) | **no birth** — no single candidate passed both gates |
| off-by-one/index | 0.95 | 0.9566 (n=692) | 0.95 (tie) | 0.9971 (init text h=0, ep 800, lr 0.3) | **no birth** — no single candidate passed both gates |

- Best joint candidates each failed gate 1 (phase-3) by exactly one item: wrong-op scratch text h=4 (phase-3 0.85 tie, intent 0.7882); off-by-one init text h=0 ep800 lr0.3 (phase-3 0.95 tie, intent 0.9971 — a perfect 20/20 is still required to birth). The code-fmode child that reached 0.90 on phase-3 scored 0.572 on intent — anonymized code features cannot carry names, as expected.
- The levers work as mechanisms: the name-intent family moved intent-slice scores by large margins (parent 0.6326 → best child 0.7882; parent 0.9566 → 0.9971), and parent-init produced the best joint off-by-one candidate. What did not move is the n=20 phase-3 gate slice, where a tie is not a birth and one item is the whole margin.
- Parent failure harvest (training-side): wrong-op parent 0.6803 on intent train (242/757 wrong; worst intents remainder 76, sum_pair 54, product 22); off-by-one parent 0.9115 (67/757 wrong; first_two 12, element_at 14, last_two 14, first_k 13). Both parents are 1.0 on phase-3 train slices (trained distribution).
- **Learned say (Fable borrow, measured, NOT adopted):** composed accuracy on phase-3 held (n=29, spent surface): routed 0.8276 > mean 0.7931 = learned 0.7931. Learned per-member weighting does not beat the current routed rule here.

### Test 3, updated

**Grows — machinery YES, births still NO.** The growth loop now exists, runs end-to-end under the battery gate, and both named levers are real and verified. Cycle 1 produced candidates that beat their parents by large margins on the new pristine intent judge and still failed the dual gate by one item each on the n=20 phase-3 slice. Gate semantics were NOT changed after seeing the results — the strict-beat rule stands.

**Cycle 2 prescription** (recorded in `growth/growth-cycle-001.md`): (1) enlarge the pristine phase-3-style gate slices with new disjoint template families (n=20 → n≥60) so the strict gate measures signal, not single items — parent and child judged identically on the bigger surface; (2) focused data for the exact stubborn shapes (minutes-style compound expressions under temp idioms; first_k/first_two variants under more idioms); (3) more init-arm configs around the near-miss (lr 0.15/0.5, epochs 1200); (4) learned-say stays unadopted; revisit only with a bigger fit set.
