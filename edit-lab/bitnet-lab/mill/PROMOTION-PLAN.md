# PROMOTION-PLAN — scheduling mill trials to adoption, sprint to Sun 2026-11-15 (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Draft 2026-11-12. -->

## 1. Purpose and relation to PROMOTE.md

This plan schedules work. `mill/PROMOTE.md` governs it.

- PROMOTE.md defines the funnel, the bars, and the adoption rule. This plan
  only orders, waves, budgets, and records the trials the funnel produces.
- Where this plan and PROMOTE.md conflict, PROMOTE.md wins and this plan
  gets corrected. Where this plan and a RESULTS file conflict, the RESULTS
  file wins (PROMOTE.md's own rule).
- Nothing here lowers a bar, adds a seed, changes a corpus, or redefines a
  verdict. It is a queue discipline, not a second funnel.

## 2. Eligibility — what is a probe survivor

Current generation only. Generation = `gen` in `mill/champion.json`
(gen 0 until the first adoption; if the file does not exist yet, gen 0 is
`screen.py`'s built-in default: 2.8580 ± 0.0161, `--arm layered_half --rope`).

A **probe survivor** is an idea with, in `mill/ledger.jsonl`:

- `kind == "probe"`, `gen == <current generation>`, and
  `verdict == "promote"` (i.e. `delta_vs_baseline >= 0.05` vs that
  generation's job zero, the `kind == "baseline"` line for the same `gen`).

Not eligible:

- `near` (0.02 ≤ Δ < 0.05): no trial. A human may re-probe at a longer probe
  budget; the mill does not, and this plan does not schedule it.
- `flat` / `below` / `error`, any verdict from an older generation, and any
  idea already `done` in `mill/trials.jsonl` for this generation.
- A survivor whose trial is already `queued` or partly seeded: it continues,
  it is not re-queued (`screen.py` de-duplicates `queued` events per
  `(idea, gen)`).

**Exception-list path** (PROMOTE.md): MILL-111/112, MILL-118, MILL-120..122,
MILL-129, MILL-137/138. A flat probe does not kill these. They enter the
queue only on a named human's word, by manually appending
`{"event":"queued","idea":"<id>","run":"<run>","gen":<gen>,"ts":<epoch>}`
to `mill/trials.jsonl` — `screen.py` has no code path for this. Each is
judged by its PROMOTE.md criteria (e.g. MoE on loss AND speed, MILL-118 on
bytes, MILL-137/138 only with a long-context check), not by held loss alone;
record those extra criteria results in the TRIAL-INDEX (§6), not by editing
the trial's `done` verdict.

## 3. Order and waves

Intended order for trials in the current generation:

1. Probe survivors by probe `delta_vs_baseline` **descending**.
2. Tie-breaks, in order: (a) earlier `ledger.jsonl` line wins (file order,
   then `ts`); (b) entries from the same family stay in id order
   (MILL-120 before MILL-121 before MILL-122, etc.).
3. Exception-list entries slot **after** all Δ-ordered survivors, in id
   order, unless a human reorders them in writing in this plan.

**Waves.** Wave 1 = survivors 1–4 in that order, Wave 2 = next 4, and so on.

- Gate between waves: every trial in a wave must be recorded — `done` event
  in `trials.jsonl` plus its mirror `kind:"trial"` line in `ledger.jsonl` —
  before the next wave starts.
- **Adoption re-bases everything.** If any trial adopts, the generation
  bumps, job zero is re-measured under the new champion, and ALL queued
  promotions from the old generation are void (ledger keys are
  `(idea, generation)`). Remaining waves do not carry over; the pool
  re-opens and a new survivor list, order, and wave set are built under the
  new generation. Do not finish an old-generation wave "for completeness."
- Reality check: `screen.py` as written runs trials in sorted `(idea, gen)`
  order after the probe queue, not in Δ order, and stops the pass on
  adoption. Waves are therefore enforced by the coordinator reviewing
  `trials.jsonl` between passes — pausing `run-forever.sh` at a wave gate
  if the next pass would start an out-of-wave trial — until/unless
  `screen.py` is changed. Never silently let code order substitute for
  this order and call it the plan.

## 4. Budgets

Per trial, serial, at CONCURRENCY=1 (the interim, honesty-verified value in
`mill/CONCURRENCY.md`; `screen.py` defaults to 1 worker, OMP/MKL=2, when
`mill/concurrency.json` is absent):

| Item | Wall clock |
|---|---|
| Trial, 3 seeds × 8 min | 24 min |
| Control re-run contingency (see below) | +8 min, once per stale reference, not per trial |
| **Trial total, normal / with control** | **24 min / 32 min for the first trial only** |

- Control contingency triggers when the champion reference is stale for the
  trial's conditions — different corpus than the reference was measured on,
  or a lab change since. PROMOTE.md: re-run the champion config as the
  trial's fourth job and update the reference first. `screen.py` does not
  do this automatically; the coordinator runs it and updates
  `mill/champion.json` before the trial's verdict is read.
  **Live trigger:** `corpus-v2/` (907,409 pieces, built 2026-11-13) differs
  from `corpus.json` (5,917,236 pieces) behind the gen-0 reference. Any
  trial run on corpus-v2 without a corpus-v2 champion control first is
  void — do not judge it against 2.8580.
- Per wave: 4 trials × 24 min = **96 min** of mill-owned wall clock
  (+8 min once if the control contingency fires in that wave).
- Pass reality: `screen.py` passes cap at 45 min, so one trial spans
  multiple passes; seeds resume across passes. Budget in trial units,
  not passes.

Total sprint budget, to end of Sun 2026-11-15 (when `run-forever.sh`
stops itself) — stated as a formula, not a forecast:

- Calendar remaining from Thu 2026-11-12 ~20:00 PT: ~76 h.
- The mill is preempted ENTIRELY by the scale ladder and the hive growth
  cycles (and in code also yields to other heavy lab drivers and any
  non-mill `train.py`). Mill share of those 76 h is unknown and not
  estimated here.
- Capacity = floor(mill-owned minutes / 24) trials. Illustrative only:
  25% share ≈ 19 h ≈ 47 trials ≈ 11 waves; 50% share ≈ 38 h ≈ 95 trials;
  100% share is not a planning case. Probes, job-zero re-measurement after
  any adoption, and deferred/non-runnable pool entries consume mill time
  before trials do, so treat these as ceilings, not commitments.
- If CONCURRENCY changes, it changes only via a completed, honesty-checked
  study recorded in `mill/CONCURRENCY.md` + `mill/concurrency.json`.
  Re-derive this section's numbers then; do not scale them by assertion.

## 5. Seed sets

- Trials use seeds **0, 1, 2** — the lab's standing set, used by every
  RESULTS record. The probe's seed 0 is inside the set; that overlap is the
  lab's existing convention, kept, not hidden.
- No seed shopping: a trial's three seeds are fixed before it starts, all
  three run, and all three are recorded whatever they show — including a
  seed that kills an adoption.
- A failed seed (no `RESULT`, no `seed` event) is a failed seed: record it
  as missing in the TRIAL-INDEX, re-run that same seed, never substitute a
  new seed number.
- Mean and sd are over exactly those three held losses. Note: `screen.py`
  computes sd as population sd (÷3). State that wherever a trial sd is
  quoted next to a RESULTS-file sd.

## 6. Recording protocol — no archaeology on Sunday

The complete record is `mill/ledger.jsonl` (probes, baselines, trial
mirrors) and `mill/trials.jsonl` (trial events). Reports summarise them;
they do not replace them (PROMOTE.md).

### 6a. What the files actually contain (screen.py, verified)

`ledger.jsonl` probe line:
`id, gen, kind:"probe", run, mode, held, steps, wall_s, probe_minutes,
delta_vs_baseline, verdict, ts`.
Baseline line: same shape, `kind:"baseline"`, `id:"MILL-000"`,
`verdict:"baseline"`, no `delta_vs_baseline`.
Trial mirror line: `id, gen, kind:"trial", held_mean, held_sd, verdict
("adopt"|"reject"), ts` — no per-seed values, no run.

`trials.jsonl` is an EVENT log, folded per `(idea, gen)`:
- `{"event":"queued","idea","run","gen","ts"}`
- `{"event":"seed","idea","gen","seed","held","ts"}` — one per seed
- `{"event":"done","idea","gen","held_mean","held_sd","verdict","ts"}`

Gaps, stated plainly: no event carries a corpus id, a control reference,
or a wall time. Corpus and control are established by the champion record
in force at the trial's `done` `ts`; wall time per seed is bounded by
consecutive event `ts` differences only. If a trial runs on corpus-v2,
that fact MUST be written into the TRIAL-INDEX by hand at run time —
it cannot be recovered from the JSONL afterwards.

### 6b. Required folded record per trial (the Sunday unit)

idea id · generation · run · seeds [0,1,2] · per-seed held (from `seed`
events) · mean · sd (population, ÷3) · control reference used
(champion `ref_mean ± ref_sd` and gen in force at `done`) · corpus id
(`corpus` unless explicitly corpus-v2) · adoption bar for that reference
(`ref_mean − max(2·ref_sd, 0.01)`; gen 0: 2.8258) · verdict (`adopt` /
`reject`) · queued / first-seed / done `ts` · wave number.

### 6c. TRIAL-INDEX (maintained here, one row per completed trial)

| wave | idea | gen | Δ (probe) | seeds | per-seed held (0/1/2) | mean ± sd | control (ref ± sd, gen) | corpus | verdict | record refs |
|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | — | — |

Record refs = line numbers at bundle time, e.g. `trials.jsonl:12-15;
ledger.jsonl:88`. Fill the row when the `done` event lands, not on Sunday.

### 6d. Sunday bundle — exact extraction commands

Run from `~/workspace/edit-lab/bitnet-lab` on Sun 2026-11-15:

```bash
# Champion in force (absent file = gen-0 default 2.8580 ± 0.0161)
cat mill/champion.json 2>/dev/null || echo '{"gen":0,"ref_mean":2.8580,"ref_sd":0.0161,"note":"screen.py DEFAULT_CHAMPION"}'

# Job zero(s) — one baseline per generation
jq -c 'select(.kind=="baseline") | {id,gen,held,steps,wall_s,ts}' mill/ledger.jsonl

# Probe survivors, current gen, in this plan's order (Δ desc, ledger order on ties)
jq -s --argjson GEN 0 '[to_entries[] | select(.value.kind=="probe" and .value.gen==$GEN and .value.verdict=="promote") | {ord:.key, id:.value.id, delta:.value.delta_vs_baseline, held:.value.held}] | sort_by(-.delta, .ord) | .[] | "\(.id)\tdelta=\(.delta)\theld=\(.held)\tledger_line=\(.ord+1)"' -r mill/ledger.jsonl

# All probe verdicts by generation (the funnel, for the bundle summary)
jq -s -r 'group_by([.gen,.kind,.verdict]) | .[] | "\(.[0].gen)\t\(.[0].kind)\t\(.[0].verdict)\t\(length)"' mill/ledger.jsonl

# Fold trials.jsonl events into one record per (idea, gen)
jq -s 'sort_by([.idea,.gen,.ts]) | group_by([.idea,.gen]) | map({
  idea: .[0].idea, gen: .[0].gen,
  run: (map(select(.event=="queued") | .run) | first),
  queued_ts: (map(select(.event=="queued") | .ts) | first),
  seeds: (map(select(.event=="seed") | {(.seed|tostring): .held}) | add // {}),
  held_mean: (map(select(.event=="done") | .held_mean) | first),
  held_sd: (map(select(.event=="done") | .held_sd) | first),
  verdict: (map(select(.event=="done") | .verdict) | first),
  done_ts: (map(select(.event=="done") | .ts) | first)})' mill/trials.jsonl

# Trial mirrors in the ledger (cross-check against the fold above; counts must match)
jq -c 'select(.kind=="trial") | {id,gen,held_mean,held_sd,verdict,ts}' mill/ledger.jsonl

# Open trials: queued or partly seeded, no done event — name them, never drop them
jq -s -r 'sort_by([.idea,.gen,.ts]) | group_by([.idea,.gen]) | map(select(all(.event != "done"))) | .[] | "\(.[0].idea)\tgen \(.[0].gen)\tseeds_done=\([.[] | select(.event=="seed")] | length)/3"' mill/trials.jsonl

# Near band (human re-probe candidates; no trials were run for these)
jq -c 'select(.kind=="probe" and .verdict=="near") | {id,gen,delta_vs_baseline,held}' mill/ledger.jsonl
```

## 7. Roles and cadence

- **The mill** (`mill/run-forever.sh` → `screen.py`, continuously through
  2026-11-15) runs probes, queues `promote` trials inline, runs trial
  seeds, applies the adoption rule, and bumps the champion on adoption.
  Nobody hand-runs trials outside it, except the §2 exception queueing and
  the §4 control re-run.
- **The coordinator** reviews verdicts between passes: enforces wave gates
  and Δ order (§3), fills TRIAL-INDEX rows as `done` events land, checks
  the ledger/trials cross-count, and calls out corpus or reference
  staleness before a verdict is read.
- **Humans intervene only for:** (a) re-probing a `near` entry at a longer
  budget; (b) promoting an exception-list entry to trial, and supplying its
  extra judging evidence; (c) any corpus change (corpus-v2 included) —
  which first requires a fresh champion control on that corpus; (d)
  reordering exception entries within §3; (e) any change to PROMOTE.md's
  bars, which is a PROMOTE.md edit, never a plan edit.
- **Reporting:** per PROMOTE.md — no per-probe reporting. Surface early
  only when (a) a trial ADOPTS a new champion, or (b) a verdict contradicts
  a standing claim in the record. Everything else — survivors, waves,
  rejects, open trials, near band — bundles into the lab's regular report
  on **Sunday 2026-11-15**, built with the §6d commands and the TRIAL-INDEX,
  and carried to Arnav, Slack #all-agenthq, and the laptop as Muse's work,
  Muse's side.
