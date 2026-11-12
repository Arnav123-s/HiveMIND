# Factory Loop — Phase A (dry-run skeleton)

Built 2026-11-10 under Arnav's grant of the same day (~12:23 PT): Muse's side of
the lab is open autonomy within his boundaries. Hard boundaries held in this job:
Fable's `make-it-work` branch was never touched (not even read by this build —
subjects come from this side's own records); nothing was pushed anywhere; no
edits and no training were performed; no GPU was used; no heavy leg ran (the
lab's one-heavy-job slot belongs to the internals job right now); nothing was
written outside `factory/` (the lab's `results/lineage.jsonl` was **not**
appended — the factory keeps its own lineage in the same format, below).

Implements `FACTORY-ARCHITECTURE.md` §8 (the unified loop) and follows
`coding/IDEA.md` — in particular §6 (no change before the map exists), §5
(growth instead of refusal), and §10 (scope only as far as proved — which is
why every verdict in this phase is a *shadow* verdict, stated as such).

## What was built

All stdlib-only Python, in `~/workspace/edit-lab/factory/`:

| File | What it is |
|---|---|
| `contracts.py` | Typed stage contracts (dataclasses, all serializable): `Subject`, `Diagnosis`/`FailureCluster`, `Indictment`, `InterventionPlan`/`WinGate`, `Verification`, `CompositionPlan`, `GrowthPlan`, `StageResult`; `Mode` (`dry_run` / `real`). |
| `host.py` | Host layer: `probe_host()` → `HostProfile` (CPU, load, RAM + cgroup cap, disk, uptime, GPU *presence* — detected, never invoked — thermal sensors where readable, battery where readable), sizing derived by formula (`derive()`: concurrency = cores/2, chunk ceiling = interruption horizon / 6 capped at 20 min, heavy legs = 1). `Governor` + `GovernorConfig`: utilization cap, duty-cycle parameters, backoff on owner-busy load / heat / battery, heavy legs require explicit per-host opt-in. |
| `lineage.py` | Append-only lineage in the lab's existing format (`{"ts", "kind", ...}` single-line JSON, fsync'd). |
| `state.py` | Restart-native cycle state: atomic save (tmp + fsync + replace), `STAGES` order, skip-if-done semantics. |
| `subjects.py` | Read-only loaders wiring the loop to existing lab evidence: adopted coding specialists (`coding/swarm/phase3_results.json`) cross-checked against the fresh-surface battery (`results/hive_battery.json`), the bug-pattern composition (`phase4_results.json`), and the coordinator winner (`results/test_synthv1_r4.json` + its `training_meta.json`). |
| `stages.py` | The six stages as pure callables (below). Diagnosis is deterministic and checker-style over recorded evidence — no model is called. |
| `loop.py` | `FactoryLoop`: orchestrates stages behind the gates, checkpoints after **every stage**, consults the governor before the intervention stage, writes lineage before/after every stage, emits `cycle_report.json`. Phase A accepts `Mode.DRY_RUN` only — `Mode.REAL` raises, because the real executors do not exist yet and the loop must not pretend otherwise. |
| `run_dry.py` | CLI: `python3 -m factory.run_dry [--cycle-id ID] [--resume ID]` (run from `edit-lab/`). |
| `tests/test_factory.py` | 10 unit tests (stdlib `unittest`), all passing: governor backoff (owner-busy, hot), heavy-needs-opt-in, chunk formula, verify-gate fail-closed cases, diagnosis fail-closed case, state save/load/skip, real-mode refusal. |
| `runs/dry-phaseA-001/` | The first dry-run cycle: `state.json`, `lineage.jsonl`, `cycle_report.json`, `host_profile.json`. |
| `lineage.jsonl` | Factory-level lineage (one `factory_cycle` entry per completed cycle). |

## The cycle contract

Stages, in order, per subject — each gated, each checkpointed:

1. **diagnose**(`Subject`) → `Diagnosis`. Classifies failures from recorded
   evidence (held-out vs fresh-surface decomposition for Tier-0; per-class
   recall decomposition for compositions; pristine per-case check
   decomposition, paired against base, for the Tier-1 adapter).
   **Gate:** a diagnosis with no evidence (`has_evidence=False`) blocks the
   subject — the cycle does not advance it.
2. **indict**(`Subject`, `Diagnosis`) → `Indictment`. Names the specific
   indicted unit or says `indictable=False`. **Rule enforced here:** score
   gaps indict *coverage* (training surfaces, second views, per-class data) —
   never weights. A weight edit is justified only by map evidence (Tier-0
   flip-ablation / knockout / locator), and no subject in this cycle had any.
3. **edit_train**(`Subject`, `Diagnosis`, `Indictment`) → `InterventionPlan`.
   In Phase A this *plans* the edit/train step: action, ordered steps, a
   `WinGate`, budget character. `executed` is always `False`,
   `shadow_only` always `True`.
4. **verify**(`Subject`, `InterventionPlan`, `Indictment`) → `Verification`.
   The win-gate stage, fail-closed. `BLOCKED` if: a weight edit lacks a
   map-backed indictment; an intervention has no indictment; the win-gate
   (threshold + regression gate + confirm protocol) is missing or incomplete;
   the plan needs a heavy leg; or the plan is not shadow-only. `NO_OP` plans
   verdict `HOLD`. Passing plans verdict `SHADOW_PASS` with
   `measured=False` — the gate contract was validated, **nothing was
   measured**.
5. **compose**(`Subject`, `InterventionPlan`, `Verification`) →
   `CompositionPlan`. Only for `SHADOW_PASS`/`HOLD`. Every composition names
   its members, its fallback (best single measured candidate), and a
   serve-time audit plan with a retirement rule (architecture §5).
6. **grow**(`Subject`, `Diagnosis`, `CompositionPlan`) → `GrowthPlan`.
   Smallest-specialist proposals for ownerless/binding gaps only, each with
   its own gate. Proposals, not spawns.

Cross-cutting: the governor is consulted before stage 3 for every subject
and its decision is recorded in state + lineage; lineage is written before
and after every stage; state is saved after every stage, so a reboot costs
at most the stage in flight.

## Dry-run result — cycle `dry-phaseA-001`

Host profile probed on this VM at cycle time (measured, not assumed):
4 CPUs visible, load/cpu 0.72 (below the 0.85 owner-busy line — no backoff),
no thermal sensor readable (gate inert, burst budgets still recorded),
no GPU detected, chunk ceiling derived at 20 min, heavy legs: not granted
(Phase A + no opt-in). Full profile: `runs/dry-phaseA-001/host_profile.json`.

The loop walked all 7 subjects through all 6 stages. **Nothing was blocked,
nothing was executed.** Per subject:

| Subject | Diagnosis | Indictment | Plan (shadow) | Verify |
|---|---|---|---|---|
| `error-class-model` (Tier-0, debugging) | No material failure: held-out 0.958, fresh 12/12 (1.000) | none — healthy | `NO_OP` (hold) | HOLD |
| `contract-judgment-model` (Tier-0, review) | **Fresh-surface gap:** held-out 0.938, fresh 7/12 (0.583) vs bar 9/12 | training-surface coverage + second-view coverage (**not** weights — no map indicts any) | `TRAIN_DATA_WIDEN`: harvest disjoint fresh surfaces w/ difficulty filter + diversity quota → add second view per case → Tier-0 retrain → screen on a *new* fresh set. Gate: fresh ≥ 0.75, held-out regression ≤ 0.02 | SHADOW_PASS |
| `gap-move-model` (Tier-0, meta) | **Fresh-surface gap:** held-out 0.878, fresh 4/10 (0.400) vs bar 6/10 | same coverage indictment | same widen shape. Gate: fresh ≥ 0.60, held-out regression ≤ 0.02 | SHADOW_PASS |
| `secret-line-model` (Tier-0, security) | Fresh-surface *drift*: held-out 0.992, fresh 10/12 (0.833) passes bar but trails by 0.159 | coverage indictment (preventive) | widen plan as above. Gate: fresh ≥ 0.75 | SHADOW_PASS |
| `commit-type-model` (Tier-0, vcs) | Fresh-surface *drift*: held-out 0.938, fresh 10/12 (0.833), trails by 0.104 | coverage indictment (preventive) | widen plan as above. Gate: fresh ≥ 0.75 | SHADOW_PASS |
| `bug-pattern-composed` (Tier-0 composition, debugging) | 0.7931 vs bar 0.800 — not cleared; 8 composition rounds plateaued at the identical score → information/surface floor, not a strategy defect | per-class surface coverage for the weak-recall classes: off-by-one (0.50), wrong-operator (0.667), swapped-operands (0.667) | widen weak classes only → retrain only their binaries → recompose (jury/max-margin) with the plateau composition as fallback. Gate: composed ≥ 0.800, no per-class recall regression; a screen that does not beat 0.7931 stops the plan | SHADOW_PASS |
| `synthv1-r4-coordinator` (Tier-1 adapter) | Pristine **WIN** 0.954 vs 0.930 gate; 2 sub-1.0 cases (case 1: checks clean/size/ends_writer, 0.50; case 9: for_each, 0.857), **both tie the base anchor** — residual capability, no introduced defect | residual case classes recorded *for the record* | `NO_OP` — **HOLD**: the coordinator contest is closed by Arnav's binding decision (2026-11-09); the loop generates no candidates against this gate | HOLD |

Composition plans (stage 5, all shadow): each widened specialist rejoins its
niche pipeline only after passing its gate, with the incumbent as fallback
and a serve-time audit + retirement rule; the bug-pattern composition keeps
the 0.7931 plateau as its fallback; the coordinator serves as the single
adopted adapter with the base (0.930 anchor) as fallback.

Growth proposals (stage 6, all shadow): a Tier-0 **second-view generator**
specialist for each drift/gap niche (review, meta, security, vcs) — the
growth-shaped fix for a coverage indictment — and **slice-variant
specialists** for the three weak bug classes. No growth proposed for the
healthy error-class specialist or the closed coordinator contest.

**Resume proof:** the cycle was re-run with `--resume dry-phaseA-001` after
completion: it finished in 0.3 s and re-executed **zero** stages (lineage
stage counts unchanged at 42 `stage_start`/`stage_done` = 7 subjects × 6
stages) — skip-if-done works; a mid-cycle reboot resumes the same way.

## What remains before real cycles (Phase B) — honest list

1. **Executors don't exist.** Stage 3 returns plans; nothing can yet run
   them. Needed: a Tier-0 retrain executor wired to `coding/swarm/factory.py`
   (`train_candidate` / `produce_model`), a harvest executor for fresh
   surfaces, and a second-view generator (itself a growth proposal above).
2. **The verify gate validates contracts, it does not measure.** Phase B
   needs the eval funnel wired in (arch. §6): fresh-surface screen →
   confirm split → one pristine-style run, with per-case cost accounting
   and ceiling-kill. Until then no `SHADOW_PASS` may be read as a win.
3. **Tier-0 surgery path is contract-only.** The flip-ablation mapper
   (arch. build item 3b, incl. the ternary substrate + head-to-head harness)
   is not built; without it, `weight_edit_justified` can never become True
   on this side and surgery stays correctly unavailable.
4. **Tier-1 executors are absent by design here.** The coordinator plan
   space is HOLD-only (contest closed). Any future Tier-1 work needs its
   own authorization, the checkpointed trainers, and the one-heavy-job
   lock integrated with the governor — none of which this skeleton does.
5. **Governor limits.** No thermal sensor is readable on this host, so the
   heat gate is inert here; on hosts with sensors (ashp tempwatch) the
   governor needs a sensor adapter. Backoff currently *annotates* a
   dry-run; in Phase B it must actually pause/resume legs, with backoff
   events as first-class lineage (partly present: `governor_backoff` is
   emitted when a probe trips).
6. **Composition is planned, not served.** There is no shared composition
   registry and no serve-time audit wiring (arch. §5 "missing"); the
   compose stage emits plans with fallbacks and audit rules, but nothing
   serves or retires a composition yet.
7. **Tier-3 interface contract is not implemented** (arch. build item 6):
   diagnosis is deterministic over recorded evidence. If frontier-model
   cluster proposals are ever added, they must land as *proposals* that
   the checker-style diagnosis disposes — the contract for that is unwritten.
8. **Subject intake is hand-wired** to three evidence files. A real factory
   needs the Tier-0 front door + spawn-mining intake (arch. build item 3)
   so new jobs arrive as subjects instead of being coded in.
9. **Scheduling is a decision function, not a queue.** No persistent queue,
   no cross-process single-heavy-leg lock file, no duty-cycle enforcement
   during a leg — all Phase B (arch. §7).
10. **Whole-hive/final-report contract (§9) is untouched**: cost per
    verdict, cost per adopted specialist, stress ledger, substrate line,
    portability line — the loop records enough lineage to compute most of
    these, but no reporter exists yet.


---

# Phase B — real executors, first real cycles (2026-11-10)

Built under the same grant and boundaries as Phase A: Muse's side only,
Fable's `make-it-work` never touched, nothing pushed anywhere, no GPU,
`internals-specialist/` never written (read nothing there either — the
other worker's lane). All legs are Tier-0 (seconds-class); OMP/MKL = 2.

## What was built

| File | What it is |
|---|---|
| `harvest_data.py` | Hand-written fresh-surface pools per subject — widen / screen / confirm sets. Every widened case ships in **two views** (the same item in an independent surface form). Contract pools cross guard-combination × class (mutations *after* both guards; scalar defaults after a None guard — the two battery blind spots); gap pools are natural-sentence registers with no template scaffolding; secret/commit pools target their battery failure shapes. |
| `executors.py` | The real TRAIN_DATA_WIDEN executor: **contamination filter** (exact + anonymized-shape + featurized-keyset/ngram overlap vs train ∪ held-out ∪ battery ∪ other pools — near-duplicates are dropped, never trained on) → **group-aware difficulty filter** (keep every case-group the incumbent gets wrong, plus a per-class diversity quota of fully-right groups) → **retrain** smallest-first (linear → mlp4 → mlp8) via the swarm factory's `train_candidate` + prune → **measured verify**: candidates ranked on the screen set, the finalist spends the confirm set **once**, the win-gate (threshold + ≤0.02 held-out regression) decides WIN/REVERT. Per-subject checkpoints under `runs/<cycle>/subjects/<id>/`. |
| `loop.py` (changed) | `Mode.REAL` enabled: execution happens between the plan and verify stages for Tier-0 widen plans; a governor backoff holds execution (verify then BLOCKs); any other non-NO_OP plan in REAL mode BLOCKs at verify — fail-closed, as contracted. DRY_RUN behaviour is byte-for-byte the Phase A behaviour (regression-checked). |
| `stages.py` (changed) | `compose` handles measured verdicts: WIN → v2 serves, incumbent is the fallback; REVERT → incumbent continues. |
| `run_real.py` | CLI: `python3 -m factory.run_real [--cycle-id ID] [--subjects ID ...]`. |
| `tests/test_factory.py` (changed) | 14 tests, all passing. The Phase A "REAL is refused" test is replaced by the Phase B contract (REAL constructs; a Tier-1 subject in REAL mode HOLDs and executes nothing) plus measured-verify tests (WIN/REVERT are `measured=True`; unsupported subjects BLOCK unmeasured). |

Honesty rules kept: `measured=False` remains the default everywhere a
number was not produced by running a model in-process; a SHADOW_PASS is
still never a win; the original battery items are re-measured as a
**reference only** (they were the diagnosis evidence, never the gate).

## Real cycle results — all measured

Gates: fresh = win-gate threshold on the one-shot confirm set; regression
= same-distribution held-out may not fall > 0.02 below the incumbent.

### contract-judgment-model — cycle `real-phaseB-001` — **WIN, adopted**

| | held-out (n=80) | screen (n=14) | confirm (n=9) | battery ref (n=12) |
|---|---|---|---|---|
| incumbent v1 | 0.9375 | 0.3571 | 0.5556 | 0.5833 (7/12) |
| **v2 (mlp8, 1,100 params)** | **1.0000** | **0.7857** | **0.8889** | **0.9167 (11/12)** |

Widen: pool 80 → 44 after contamination (36 dropped — anonymized-shape
duplicates and keyset-Jaccard ≥ 0.92; the code-trigram space is dense and
many authored shapes collided with existing surfaces, including my own
screen/confirm pools; the filter dropped them all rather than train on
near-duplicates) → difficulty filter kept 38 (29 incumbent-wrong + 9
quota) → train 100 → 138. Screen/confirm sets shrank under the same
filter (24 → 14, 12 → 9) — small-n, stated plainly. Corroboration: the
saved v2 file, re-measured cold on the **full raw** pools, scores
screen 0.875 (21/24) and confirm 0.9167 (11/12). Candidates: linear
0.9375/0.5714, mlp4 0.9375/0.5000, mlp8 1.0000/0.7857 (held/screen) —
the linear improved on the incumbent's fresh scores too, but ranked
below mlp8 on the screen, and the gate's ranking rule is the screen.
Adopted as `coding/swarm/models/contract-judgment-model-v2.json`
(28,642 B footprint record); v1 file untouched, kept as fallback.

### gap-move-model — cycle `real-phaseB-002` — **WIN, adopted**

| | held-out (n=90) | screen (n=20) | confirm (n=10) | battery ref (n=10) |
|---|---|---|---|---|
| incumbent v1 | 0.8778 | 0.6500 | 0.7000 | 0.4000 (4/10) |
| **v2 (mlp4, 3,673 params)** | **0.9333** | **0.9500** | **0.9000** | **0.8000 (8/10)** |

Widen: pool 100, **zero** contamination drops (the natural-language
pools were genuinely disjoint); filter kept 68 of 100 (40 hard + 28
quota; the incumbent already had wait-for-backend fully right, so that
class contributed no hard cases); train 240 → 308. Candidates
(held/screen): linear 0.8778/0.95, mlp4 0.9333/0.95, mlp8 0.8889/0.90 —
screen tie between linear and mlp4 broken by fewer params, per the
selection rule; mlp4 also held the best held-out. Confirm 9/10 vs the
0.60 gate. Adopted as `gap-move-model-v2.json`; v1 untouched.

### secret-line-model — cycle `real-phaseB-003` (preventive) — **WIN, adopted**

| | held-out (n=130) | screen (n=11) | confirm (n=11) | battery ref (n=12) |
|---|---|---|---|---|
| incumbent v1 | 0.9923 | 0.7273 | 0.6364 | 0.8333 (10/12) |
| **v2 (mlp8, 2,466 params)** | **1.0000** | **0.8182** | **0.9091** | 0.8333 (10/12) |

The preventive plan found real drift my screen/confirm sets expose
(the incumbent is much weaker on new literal shapes than the battery
suggested). Widen 36 → 32 after contamination; filter kept 23; train
140 → 163. The linear candidate *regressed* held-out to 0.9308 (below
the 0.9723 floor — ineligible, exactly what the regression gate is
for); mlp8 cleared everything. Battery reference unchanged at 10/12:
the widen fixed the new-surface drift, not the two original battery
items. Adopted as `secret-line-model-v2.json`; v1 untouched.

### commit-type-model — cycle `real-phaseB-003` (preventive) — **WIN, adopted**

| | held-out (n=80) | screen (n=12) | confirm (n=12) | battery ref (n=12) |
|---|---|---|---|---|
| incumbent v1 | 0.9375 | 0.8333 | 0.8333 | 0.8333 (10/12) |
| **v2 (linear, 2,700 params)** | **0.9625** | **1.0000** | 0.8333 | **1.0000 (12/12)** |

Widen 52, zero contamination drops; filter kept 36; train 380 → 416.
The smallest architecture won this one. Stated honestly: on the
confirm set v2 only **ties** the incumbent (10/12) — the gate passed
on threshold + no-regression, and the measured gains are the screen
(10/12 → 12/12), held-out (+0.025), and the battery reference
(10/12 → 12/12, both original failure shapes fixed). Adopted as
`commit-type-model-v2.json`; v1 untouched.

### Fail-closed evidence — cycle `real-phaseB-004`

REAL cycle over the remaining subjects: `error-class-model` HOLD
(healthy incumbent), `synthv1-r4-coordinator` HOLD (contest closed;
nothing executed, no candidates generated — Arnav's binding decision
untouched), `bug-pattern-composed` **BLOCKED** at verify ("no executor
exists for this plan in Phase B") — out of scope this phase, by design.

## Caveats (read before quoting any number above)

- **Single-author fresh sets.** All Phase B screen/confirm pools were
  written by the same hand that wrote the widen pools (disjoint and
  contamination-checked, but one author). That is a weaker independence
  guarantee than the battery had. The battery-reference column is the
  cross-check: it moved the right way on 3 of 4 subjects.
- **Small confirms.** Contract's confirm ran at n=9 after filtering.
  The corroborating full-pool re-measurement is recorded above.
- **Architecture grew on 3 of 4 wins** (contract 468 → 1,100 params,
  secret 512 → 2,466, commit 2,376 → 2,700; gap shrank 3,825 → 3,673).
  Selection ranks by screen score among regression-eligible candidates,
  smallest only as tie-break — that is the gate contract as written in
  Phase A, but it is a real trade against the smallest-specialist
  preference, recorded here rather than smoothed over. All v2s remain
  Tier-0 tiny (≤ 2,466–3,673 params, ≤ ~118 KB on disk).

## What remains of the Phase A 10-item list

1. **Executors** — DONE for Tier-0 TRAIN_DATA_WIDEN. Still missing: a
   general harvester (pools are hand-written per subject) and the
   second-view *generator* specialist (views are hand-authored pairs;
   the growth proposal stands).
2. **Verify measures** — DONE for widen cycles (held-out + screen +
   one-shot confirm, per-case records, ceiling discipline). No funnel
   exists yet for other plan shapes.
3. **Tier-0 surgery path** — still contract-only: no flip-ablation
   mapper, no ternary substrate; `weight_edit_justified` still can
   never become True on this side.
4. **Tier-1 executors** — still absent by design; coordinator HOLD.
5. **Governor** — backoff now genuinely holds real execution (verify
   BLOCKs, reason in lineage). Still no thermal-sensor adapter (none
   readable on this host) and no mid-leg pause/resume — legs are
   seconds-class, so chunking is per-subject, not per-leg.
6. **Composition serving** — compose now records measured compositions,
   but there is still no shared composition registry and no serve-time
   audit wiring.
7. **Tier-3 interface contract** — still unwritten.
8. **Subject intake** — still hand-wired, and now visibly stale:
   `subjects.py` reads the v1 adoption table, so a future cycle would
   diagnose the v1s, not the adopted v2s. Feeding v2 adoptions back
   into intake is Phase C work (the adoptions themselves are recorded
   in factory lineage + the cycle reports + each v2 record's
   `supersedes` field).
9. **Scheduling** — still a decision function: no persistent queue, no
   cross-process heavy-leg lock. This phase's legs are light and the
   one-heavy-job rule was honored by construction.
10. **Whole-hive / §9 final report** — still no reporter. This phase
    adds per-cycle counts (examples, evals, drops) to the record, not
    the full cost/stress/substrate/portability contract.

---

# Phase C — dream cycle, ternary substrate, growth, scheduling, reporter (2026-11-10)

Built under Arnav's direction of 2026-11-10 ~12:54 PT ("add that in
your part with increasing number of specialists and all other
ideas"), harvesting the day's research: Ripple's steep-ascent recipe,
s1's selection filters, LeCun's good views, and the sibling line's
cross-family agreement finding (read-only — the one-way valve held;
nothing was written outside `factory/`, `coding/swarm/models/`
(adoptions + composer config), and the architecture/loop docs).
Design: `FACTORY-ARCHITECTURE.md` section 10. All legs Tier-0,
seconds-class; OMP/MKL = 2; the coordinator was never touched.

## What was built

| File | What it is |
|---|---|
| `dream_gen.py` | Parameterized bug-family generators, 3 difficulty bands (~20 skeleton kinds), plus **screen-only skeletons** (structurally distinct idioms). Every family is **execution-verified**: correct code runs on probes; each mutation must be observably different (behavioral signatures; repeated-call signatures for mutable-default); missing-return variants must actually return None. Kept cases ship in **two views** (original + identifier-renamed, itself execution-verified). |
| `dream.py` | The dream executor: **Thermostat** (per-class edge band from fresh-probe positive recall; persisted in `factory/dream_state.json`), coverage tally + slice diversity quota, contamination filter (vs train ∪ held-out ∪ the swarm's phase-4 dream corpus), group-aware difficulty filter, per-class retrain ladder, composed screen → **one-shot confirm**, measured verify. Harness calibration first: the eval must reproduce the recorded plateau exactly or the cycle BLOCKs. |
| `ternary.py` | Tier-0 substrate (arch. build item 3b): per-row-scale PTQ calibrated on train only; **QAT (STE) trainer** mirroring the swarm optimizer; **flip-ablation mapper** (near-exact indictment at 3 states/weight); head-to-head harness (held-out, footprint, latency, cross-substrate agreement). |
| `growth.py` | Intake scan (adopted versions, missing slice variants, per-slice parent scores) + the **split-birth protocol**: child trained on slice data + slice dreams; born only if it strictly beats the parent on the slice held-out; only then are the model file and the composer strengths entry written. |
| `scheduler.py` | Cross-process single-heavy-leg lock (staleness-broken, contention reported) + persistent cycle queue + duty-cycle pause helper (arch. section 7). |
| `thermal.py` | Governor thermal adapter for hosts whose temperature lives in a watcher log (ashp's tempwatch): latest reading only, and only if the log is fresh (< 10 min) — a stale watcher leaves the heat gate inert rather than trusting old data. Wired into `host._thermal()` via `FACTORY_TEMPWATCH_LOG`. |
| `reporter.py` | The section-9 reporter: cost per verdict, cost per adopted specialist, budget vs caps, stress ledger, substrate line, portability line → `factory/reports/`. |
| `subjects.py` (changed) | **Intake fix:** subjects now diagnose their adopted **v2s** (artifact, held-out, one-shot confirm as fresh evidence; v1 numbers kept in metadata). `executors.load_incumbent` likewise starts from the v2, and a win over a v2 saves as v3. |
| `stages.py` / `loop.py` / `contracts.py` (changed) | New `Action.DREAM_TRAIN`; the bug-pattern plan shape changed from widen to dream (widen had no executor — there is nothing to harvest for this subject); REAL dispatch + measured verify for dream plans; a Phase C compose branch for composition wins. |
| `run_dream.py`, `run_ternary.py`, `run_growth.py` | CLIs. |
| `tests/test_phase_c.py` | 17 new tests (31 total, all passing): checker drops unobservable mutations, thermostat edges, slice quota, QAT learns, flip map, lock/queue, v2 intake, dream plan shape. |

## The dream cycle — first run and the flaw it caught (`dream-phaseC-001`, REVERT)

The first cycle executed end-to-end and reverted at the screen: the
screen pool had been generated from the **same skeletons** as the
training pool, so the contamination filter (anonymized-shape match)
correctly zeroed it — 238 in, 0 kept; composed screen 0.0 vs 0.0;
the plan stopped and the confirm set was **not** spent. Two fixes,
both kept as design rules: the screen gets its own structurally
distinct generators, and the thermostat reads positive **recall**
(binary accuracy had hidden the weakness — it is dominated by the
"other" majority).

## The dream cycle — measured WIN (`dream-phaseC-002`)

Harness calibration: incumbent composition re-measured **0.7931** =
the recorded plateau, recalls matching, before any candidate was
judged. Thermostat round 0: all three weak classes sit at **band 1**
(no band mastered). Telling detail: off-by-one probe recall is 0.00
at band 1 (index shapes, n=4 positives), 0.43 at band 2, 0.08 at
band 3 — the binary is specifically blind to band-1 index forms.

Generation and hygiene: 108 families → 628 verified items (the
execution checker dropped **nothing** — every designed mutation was
observably a bug; every kept case carries both views) →
contamination kept **172** (456 dropped against train ∪ held-out ∪
phase-4 dream corpus; the anonymized-shape rule is brutal on simple
code and that is intended) → slice quota dropped 4 groups. Screen
(own skeletons): 172 → 154 kept.

Per class (binary held / binary screen, incumbent → winner):

| class | edge | kept dreams | train | binary held | binary screen | winner |
|---|---|---|---|---|---|---|
| off-by-one | 1 | 14 | 48 → 62 | 0.931 (inc.) | 0.708 (inc.) | none — no candidate beat the incumbent's screen |
| wrong-operator | 1 | 39 | 48 → 87 | 0.862 → **0.897** | 0.578 → **0.779** | text/linear, 1,252 params |
| swapped-operands | 1 | 11 | 48 → 59 | 0.966 (inc.) | 0.948 (inc.) | none — incumbent already strong |

Composed screen (fresh dreamed structures): incumbent 0.4221 →
candidate **0.4610** — both weak on truly novel structures, stated
plainly; the screen gain is mostly the clean class (0.46 → 0.88).
**Confirm, spent once** on the phase-4 held-out set: **0.8276 ≥
0.80 bar** (plateau 0.7931), per-class recalls clean 0.90,
off-by-one 0.75, swapped 0.667, wrong-operator 0.667,
missing-return 1.0, mutable-default 1.0 — every one at or above its
phase-4 recorded value. **WIN, adopted:** `bug-wrong-operator-model
.json` retrained in place (phase-4 record backed up inside the run
directory); the other two weak classes keep their incumbents.

Read the win at its true size: the net gain is **one case** (23 →
24 of 29), arriving via the clean class; the three weak classes'
*composed* recalls did not move — their binding constraint is
margin competition between classes, not their binaries' accuracy
(the wrong-operator binary itself improved substantially). The bar
the lab set in Phase A is cleared, by the margin the numbers say
and no more. Thermostat round 1: edges unmoved (all band 1, nothing
mastered) — persisted for the next cycle. **Consequence:** the
phase-4 held-out set has now been spent as a confirm; future
bug-pattern verdicts need a new held-out set first — the dreamed
screen is interim evidence only.

## Ternary head-to-head (`phaseC-ternary-002`) — fp keeps all five niches

Gate: ternary ships only where held-out ≥ fp. (Run 001, PTQ-only,
is in the record; run 002 adds the QAT path. Candidates ranked by
training-set calibration; held-out judged the winner once.)

| subject | fp held | ternary held (path) | packed | fp artifact | agreement |
|---|---|---|---|---|---|
| error-class | 0.9583 | 0.9500 (ptq) | 4,941 B | 264,151 B | 0.975 |
| contract-judgment (v2) | 1.0000 | 0.9375 (ptq) | 311 B | 35,286 B | 0.938 |
| gap-move (v2) | 0.9333 | 0.8667 (qat-h4) | 680 B | 117,639 B | 0.933 |
| secret-line (v2) | 1.0000 | 0.9923 (qat-h4) | 252 B | 67,047 B | 0.992 |
| commit-type (v2) | 0.9625 | 0.7625 (qat-h4) | 397 B | 85,910 B | 0.738 |

Two honest findings: (1) naive post-training quantization is the
wrong birth path — gap-move collapsed to 0.2667 under PTQ and
recovered to 0.8667 when **born ternary** via QAT; (2) at Tier-0
scale fp is already nearly free, so a 100–500× footprint win does
not compensate *any* accuracy loss under the gate as contracted.
Ternary's day here is as the low-stress substrate if a host ever
needs thousands of resident specialists, not as today's default.

**Flip-map surgery trial (the mapper works):** on the secret-line
PTQ pack, probes from training data only (n=64, base 0.859) —
**114 improving flips indicted**; the ≥0.015-delta subset was
applied and judged once on held-out: **0.9154 → 0.9385, ADOPTED**
as a coexisting ternary artifact (`secret-line-model-ternary.json`,
still below fp's 1.0 — fp remains the niche default). Map-backed
indictment is no longer theoretical on this side: it indicted,
flipped, and measurably repaired.

## Growth (`phaseC-growth-001`) — intake works; two births measured and rejected

Intake enumerated the slice gaps. Most candidates were non-starters
on the numbers (parent already 1.0 on the slice, or the slice is
empty in held-out). The two attemptable births:

| child | train (pos) | parent slice held | child slice held | verdict |
|---|---|---|---|---|
| bug-wrong-operator-expression-model | 102 (19) | 0.85 (n=20) | 0.85 | **rejected — tie is not a birth** |
| bug-off-by-one-index-model | 223 (45) | 0.95 (n=20) | 0.95 | **rejected — tie is not a birth** |

Dream-augmented slice training taught both children to *match*
their parents exactly, including the same hard cases — the slice
signal appears genuinely insufficient to separate those cases,
which is itself a finding about where the composition's remaining
errors live. No files were changed by either attempt. The registry
grew this phase only through measured routes that passed their
gates: the dream-retrained wrong-operator binary (a replacement,
not a birth) and the surgery-repaired ternary artifact (a new
substrate member). Registry growth stays exactly as fast as
measurement allows — that is the design working, not failing.

## What remains of the Phase A 10-item list (updated)

1. **Executors** — widen (B) and dream-for-bug-pattern (C) done.
   Still missing: a general harvester (pools are hand-written /
   generated per subject), dream generators for the other niches
   (the engine is generic; only bug-pattern has a generator), and
   the standalone second-view generator specialist (views are
   produced inside dream_gen today).
2. **Verify measures** — done for widen and dream cycles.
3. **Tier-0 surgery path** — DONE in ternary form (C): flip mapper,
   PTQ, QAT. An fp-side zeroing-ablation mapper is not built; the
   ternary mapper is the sharper instrument and the one the
   architecture specified.
4. **Tier-1 executors** — still absent by design; coordinator HOLD.
5. **Governor** — backoff holds real execution (unchanged from B);
   the thermal adapter is built (C: tempwatch-log hosts, freshness-
   gated) but inert on this host, which exposes no sensor and runs
   no watcher log; legs remain seconds-class so mid-leg
   pause/resume is still unneeded.
6. **Composition serving** — the bug composition serves its
   dream-retrained member; consultation composition is *designed*
   (arch. section 10.4) but not built, pending the
   internals-specialist Phase 5 verdict it follows. Shared
   composition registry + serve-time audit still missing.
7. **Tier-3 interface contract** — still unwritten.
8. **Subject intake** — v2 feedback DONE (C); slice intake DONE for
   the bug classes (C). The Tier-0 front door / spawn-mining for
   new jobs is still missing.
9. **Scheduling** — heavy-leg lock + persistent queue DONE (C);
   nothing consumes the queue yet (no scheduler daemon), and
   duty-cycling is a helper, not yet a loop behavior.
10. **Whole-hive / section-9 report** — DONE (C): `reporter.py`,
    first report in `factory/reports/`. Whole-hive benchmark
    re-runs remain the battery's job, separately.
11. **New (C): a fresh bug-pattern held-out set** — the phase-4 set
    is spent as a confirm; the next gated bug-pattern cycle needs
    new sealed surfaces before it can be judged.

# Phase D — the final product: registry, serving, Tier-3 contract, daemon, acceptance (2026-11-10)

## What was built

1. **Sealed bug-pattern held-out v2** (`factory/bug_heldout_v2.py`,
   `coding/swarm/bug_heldout_v2.json`): 15 new template families,
   decontaminated against train + spent held + dream corpora;
   n=36 sealed by sha256 (cd17c922…). Baseline, measured once:
   composed **0.4444** vs the 0.80 bar — BELOW on novel structures.
   Per-class binary accuracies stayed decent (0.69–1.0); the
   composition is what falls. This closes Phase C's item 11.
2. **Niche dream generators** (`factory/dream_gen_niches.py`,
   `factory/dream_niches.py`): contract-judgment (labels PROVED by
   execution — behavioral signature on None/[]/[3,1,2] probes) and
   commit-type (labels proved by a signal-dominance checker),
   structurally disjoint train/screen/confirm pools, thermostat
   bands, the widen executor's full gate discipline. Contract
   cycle `dream-niche-contract-001` = WIN (confirm 0.9048 vs
   incumbent 0.7619 paired) → adopted `contract-judgment-model-v3`.
   Commit cycle via the daemon = REVERT (candidates 0.9125–0.9375
   held-out vs floor 0.9425; confirm never spent). gap-move and
   secret-line HOLD — respected, not manufactured.
3. **Shared registry + serve-time audit** (`factory/registry.py`,
   `factory/registry.json`, `factory/audit.py`,
   `factory/serve.py`): one book for every adopted artifact —
   serving + fallbacks + substrates (ternary secret-line as
   coexisting alternative, fp default), the 14-member bug
   composition, the Tier-1 coordinator for provenance. Every
   entry sha256'd; `ServingHive.load()` verifies files AND the
   standing serving rule at load and refuses on any mismatch.
   Full audit re-measures every serving score — all reproduce.
4. **The standing serving rule** (created by the contract v3
   case; Arnav's direction 2026-11-10 13:51 PT): an adopted
   artifact serves only when its measured battery slice
   (`factory/battery_evidence.json`) is >= the incumbent's;
   until then it is SHADOW — audited, never served, never a
   fallback. v3 passed its win-gates and still measured 5/12 on
   the acceptance battery vs v2's 11/12, because its confirm
   surfaces were its own generator's idioms. The registry now
   derives serving from evidence; `audit.verify_rule` re-derives
   it and fails closed (tested: a hand-forged book serving v3 is
   refused at load). Under the rule: contract serves v2
   (promoted 0.9167 >= 0.5833), v3 is shadow.
5. **Tier-3 contract** (`factory/TIER3-CONTRACT.md`,
   `factory/tier3.py`): typed stub — kind allowlist,
   never-delegate list (gate verdicts, adoptions,
   checker-decidable questions, weight edits, sealed contents,
   spend/send), budget caps, verbatim audit logging, fail-closed.
   No keys, no backend, no calls; a valid request is logged and
   refused with Tier3NotConfigured.
6. **Scheduler daemon** (`factory/daemon.py`): consumes the
   Phase C queue under the governor (probe-aware, holds never
   pop, heavy-leg lock for declared-heavy requests), runs cycles
   through FactoryLoop, files the §9 report after each, appends
   outcomes to `factory/queue_history.jsonl`. Proof: two queued
   cycles processed end-to-end (the real commit dream cycle and
   a full dry-run sweep).

## The bug-pattern fix attempts (2026-11-10, Arnav: "make it work")

Diagnosis first, on training-side data only: on novel structures
the weak classes lose by BINARY MISS, not margin competition —
competition losses were ZERO on the dreamed screen corpus; each
weak binary's margin on its own true positives is negative
(medians: swapped-operands −9.96, off-by-one −6.44,
wrong-operator −4.20). This CORRECTS the Phase C note above,
which inferred margin competition from the spent phase-4 set;
on-distribution the losses are also mostly binary misses.
Calibration cannot create signal that is not there.

Four attempts (`factory/fix_bug_pattern.py`, runs
bugfix-2026-11-10-001..004), all judged on spent sets only, the
sealed set used solely as a contamination reference:
001 instrument faults (a "fresh" screen seed was empty — screen
seeds differ only in names/literals, which contamination
normalization erases; band-starved pools). 002 all-band pools,
dream-swamped mix → candidates gained screen accuracy
(wrong-operator 0.88 vs 0.78) but cratered on held (0.55–0.79 vs
0.90), no winners. 003 rebalanced mix + positive-recall
selection → per-class floors vetoed every recall gain before the
composition could rule. 004 floors removed, composition gates
alone decide: winners for wrong-operator and off-by-one;
candidate composition screen **0.5649 vs incumbent 0.461
(+0.104)**, held **0.7586 vs 0.8276 (−0.069)** — the held gate
(≤0.02 regression) refused adoption. Nothing was adopted in any
attempt. The one post-fix sealed judge
(`factory/run_bug_heldout_postfix.py`): **0.4444, delta +0.0,
every per-class delta 0.0 — unmoved.** The measured conclusion:
at this representation, novel-structure recall is bought only
with template fit or false fires the gates correctly refuse.

Postscript (side lab, not this build): the waking-dream
answer-time layer (`~/workspace/edit-lab/waking-dream/`) later
measured 0.8333 on the same sealed set with the serving
binaries untouched. It is recorded in FINAL-PRODUCT.md as a
PENDING ADOPTION CANDIDATE under the standing rule — not
adopted, not served; the decision is Arnav's.

## Acceptance battery (WI-6)

`factory/run_battery.py` → `results/hive_battery_acceptance.json`
(the 2026-11-09/10 battery's items, bars and checks, served
through the registry). Specialists: secret-line 10/12 ✓,
error-class 12/12 ✓, commit-type 12/12 ✓, contract-judgment
(served v2) 11/12 ✓, gap-move 8/10 ✓ — all bars met. Ternary
substrate on the secret items: 11/12 (informational; fp serves
on the held-out head-to-head). Bug composition on sealed v2:
0.4444 vs 0.80 — MISSED (see fix attempts). Tiny-hive: 21/21
in-domain, 3/3 out-of-domain refused. Composites: b1 FAILED
environmentally (arXiv API unreachable for the whole 5400s run;
the same task passed 3/3 in 1376s in the previous battery);
b2's first run was killed by a VM restart and b2–b6 were
re-queued — outcomes land in the acceptance JSON and a closing
addendum here. Guard integrity: every score above is what its
checks measured; crashed/killed runs score 0, never a pass.

Tests: 50/50 (factory/tests: Phase A/B 13, Phase C 18, Phase D
19 incl. the serving-rule enforcement tests).

## Phase D addendum — composites, final tally (2026-11-10)

All six composites reached recorded verdicts, after two VM
restarts killed chains mid-flight (partial runs were scored on
their artifacts and labeled, never passed): b1 FAILED
(environmental — arXiv API unreachable for the full 5400s;
passed 3/3 in 1376s in the prior battery), b2 FAILED (restart
kill, then a 3600s re-run with no deliverable), b3 FAILED
(1608s, report missed the required year 1856), b4 FAILED
(restart kill before mad.py existed; also failed in the prior
battery), b5 FAILED (1703s, fixed.py never produced), b6 FAILED
(591s, 0/3 title checks in the same arXiv outage window).
Composites: **0/6** this battery (prior: 1 of 3 attempted).
The Tier-0 serving tier met every bar it was given except the
bug composition's; the Tier-1 composite tier is the product's
weak tier, and FINAL-PRODUCT.md says so in those words.
