# Factory Architecture — portable, low-stress design for the automated HiveMIND factory

Directives: Arnav, 2026-11-09 ~14:14 PT (compute-adapted architecture), **revised
2026-11-09 ~14:19 PT** — this revision supersedes the original machine-specific
framing: the architecture is **machine-agnostic and low-stress by design**. It does not
assume this VM, this laptop, or any particular host. The factory is built to run
anywhere, politely, and to size itself to what it finds. The unification build follows
this document.

Thesis (Arnav's, 2026-11-09): abilities are created by COMBINING training + surgical
editing + chaining/composition + architecture editing/growth — not any one alone. This
architecture is where the four combine, tiered so the cheapest mechanism that can own
a job does own it — which is also what makes the factory cheap to run anywhere.

---

## 1. Portable by default (design rule 1)

- **The core is dependency-light and portable.** Precedent: the tiny-hive ran an entire
  hive in pure Python stdlib (11 constructed specialists, 2,861 params, exhaustive
  verification, ~17 MB peak RAM). The factory core — loop, lineage, gates, Tier-0
  production, composition, scheduling — is written to that standard: stdlib-first,
  accelerators and heavy frameworks are *adapters at the edges* (an eval engine, a GPU
  trainer), each replaceable, none load-bearing for correctness.
- **No host facts in the design.** No core counts, GPU models, paths, or memory figures
  appear as assumptions anywhere in this architecture or in the code built to it. Host
  facts exist only as **detected profiles** (§2): data the factory measures about the
  machine it happens to be on, stored with its run state, cited in reports as "measured
  on profile X" — never baked in.
- **Win-gates are host-invariant.** Dev selects, test confirms once, paired per-case
  deltas, per-case regression gates, pre-registered win bars: identical on every host.
  A weak host runs the same factory slower and in smaller pieces; it never runs a
  sloppier one.

## 2. Runtime adaptation — probe, then size (design rule 2)

On startup (and periodically thereafter) the factory probes its host and derives a
**host profile**:

- CPU: cores available, current load (owner activity is a signal, not noise).
- Memory: total and currently free RAM; any cgroup/container cap.
- Accelerator: GPU presence, model, VRAM; whether a usable inference/training stack
  exists for it.
- Thermal: temperature sensors where readable (GPU/CPU), plus the host's recent
  thermal history if a watcher log exists.
- Power: on-battery vs plugged in, where readable.
- Storage: free space on the working volume.
- Liveness: whether the host (or its container/VM) shows a restart cadence — inferred
  from uptime history / prior run state; the loop plans chunk sizes against the
  shortest plausible interruption horizon it has evidence for.

The profile drives, by formula rather than by table: tier availability (§4), batch and
chunk sizes, eval budgets expressed in wall-clock (§6), concurrency (default: one
heavy leg at a time on any host), and duty-cycle parameters (§3). On a strong host the
same formulas yield bigger batches, more parallel Tier-0/1 work, and shorter cycles;
on a weak host they yield fewer concurrent specialists, smaller batches, longer
cycles — **the loop, the stage order, and the gates do not change.**

Two example profiles, measured 2026-11-08/09, illustrate what a probe finds. They are
evidence about those hosts on those days, nothing more:

- *Profile "small cloud cell":* ~1.5 shared vCPU, ~6 GB cap, no GPU; host restarts on
  a ~2 h cadence; a 1.7B bf16 eval case cost ~5–8.5 min of CPU; a checkpointed trainer
  peaked ~3.55 GB after patching (5.74 GB unpatched → OOM). Consequences the formulas
  produce here: chunk ceiling ~20 min, evals are the dominant cost, Tier 2 unavailable
  locally.
- *Profile "older gaming laptop":* 4 GB VRAM GPU, 32 GB RAM, impaired cooling (a
  thermal trip is in its history); idle GPU ~45 °C cold / ~56 °C heat-soaked;
  generation ~37–43 s per item at ~20 W; GPU-only load plateaus ~78–81 °C, but a
  co-running CPU-heavy owner job drove ~+2.3 °C/min with no plateau. Consequences:
  burst budgets sized by *regime* (what else the host is doing), thermal gating on,
  heavy legs short and checkpointed.

## 3. Low-stress as a design rule (design rule 3)

The factory is a **polite tenant** on any device, including the owner's own machines.
Stress is a budget, spent rarely and deliberately:

- **Utilization caps.** The factory never pegs CPU or GPU: per-leg caps are part of
  the host profile's config (defaults gentle; raising them is an explicit per-host
  opt-in, never a default the loop chooses for itself).
- **Duty-cycling.** Heavy legs run in bursts separated by idle gaps; sustained 100%
  anything is a design violation, not a throughput strategy.
- **Automatic backoff.** The scheduler yields — pauses or shrinks the current leg —
  when the host is hot (its own sensors approaching profile limits), busy with its
  owner's own work (load the factory didn't create), or on battery. Resumption is
  automatic when conditions clear; the lineage records every backoff and its cause.
- **Tier-0 dominance is the stress strategy.** Most factory work (production,
  screening, verification, composition bookkeeping) is Tier-0/Tier-1 work that costs
  almost nothing (§4). The expensive substrates are invoked the way the eval funnel
  invokes tests: rarely, for finalists, with a reason logged. Within Tier 0, the
  **ternary substrate (§4) is the low-stress ideal** — ~10× smaller, addition-
  dominated, cool — and is preferred wherever the head-to-head protocol says it
  proves; full precision stays where it wins.
- **One heavy leg at a time**, on any host, unless the host profile explicitly opts
  into more — politeness first, parallelism when the host is clearly idle and cool.

## 4. Tiered specialists — cheapest first (pillar 1)

A job enters at the lowest tier that could own it and is promoted only on measured
failure (§5). Tier *availability* is a probe result: a host without a suitable
accelerator simply has no local Tier 2 — Tier 2 work queues, degrades to Tier-1
composition, or is explicitly routed elsewhere by config; it never crashes the loop.

### Tier 0 — Tiny specialists (the DEFAULT), two substrates
Small MLPs (hundreds to ~10 K params) over engineered features; verifiable
*exhaustively* when the input space is enumerable. Tier 0 has **two first-class
substrates**, and bit-width is a per-specialist choice (§ Tier-0 substrate protocol):

**(a) Full-precision tiny nets** — trained in-process or constructed directly.
Evidence: tiny-hive (2,861 params total, 1,023,310 exhaustive cases all correct,
~17 MB peak RAM, pure stdlib); the swarm factory's adopted specialists (468–9,228
params, 0.878–0.992 held-out); a "failed" decomposition still composed to 0.7931
from per-class tinies. Cost: seconds to train, ~free to serve, KBs on disk.

**(b) Ternary (BitNet-style) specialists — weights in {−1, 0, +1}, ~1.58 bits/weight**
(Arnav's addition, 2026-11-09 ~14:20 PT: "BitNet specialists?? Custom trained and
made. With editing."). Born either way, both first-class: **trained** at small scale
with quantization-aware training (straight-through estimator), or **constructed**
directly — then verified the same way, per the standing born-either-way rule.
Why this substrate fits the portable/low-stress design (§1, §3):
- **Footprint:** ~10× smaller than fp16 at equal params (1.58 vs 16 bits/weight) —
  more specialists resident, more running at once, on any host.
- **Inference is addition-dominated:** ternary matmul is adds/subtracts/skips, no
  multiplier pressure — CPU-fast, low-energy, cool. The polite tenant gets its ideal
  substrate, and "maximize specialists running at once" scales much further.
- **Ternary-aware surgery — editing changes character at 3 states per weight.** An
  edit is a discrete **flip** (−1→0→+1). At specialist scale, per-weight
  flip-ablation maps are cheap and *near-exact*: knock out or flip each weight and
  measure — indictment stops being an estimate (contrast the LM tiers, where locator
  maps are statistical and, in this lab's coordinator probes, found harm diffuse
  with no indictable slot). Protocol unchanged, instrument sharper: classify the
  defect → flip-map indicts → flip only indicted weights → held-out gate. Frontier-
  model defect repair by reasoning (the Nov 7 pattern: an optimizer model fixed 8
  planted defects in constructed nets by reasoning, verified exhaustively) gets
  *more* tractable here: each indicted weight has exactly **2 alternative states**
  to reason over.
- **Honest constraint, settled by measurement:** per-parameter capacity is lower
  than full precision, so a ternary specialist may need more params for the same
  job. That is a per-niche empirical question, never a dogma in either direction
  (see the head-to-head protocol below).

- Exists: `coding/swarm/factory.py` — `TinyNet(Specialist)`, numpy trainer, pruning,
  `produce_model` / `train_candidate`, **`repair_by_surgery`** (Tier-0's fp edit
  path: fix from wrong probes + guard probes instead of retraining), persistence;
  `constructed.py`, `niches.py`, `field*.py` (a 205-specialist registry, 148 running
  alone, on one host's profile).
- Missing: the standard front door — unified-loop intake must attempt Tier 0 for every
  job (fixed-value / few-class decisions over featurizable input) and log why a job
  was or wasn't Tier-0-shaped. The discovery mechanism (mining logged calls for
  fixed-value call sites) exists on the sibling line (`team/cells/spawn.py`); wiring
  it to this factory is a build item. **For the ternary substrate, all of it is
  missing and is build work:** the QAT (STE) trainer, the direct-construction path,
  the per-weight flip-ablation mapper, ternary persistence in the registry — plus
  the head-to-head harness below.

**Tier-0 substrate protocol (head-to-head, per niche).** For each niche where both
substrates are candidates: train/construct a ternary and a full-precision specialist
for the *same* job, on the *same* splits, and compare on held-out score, footprint
(bytes on disk / resident), and latency on the current host profile. The win-gates
decide the niche's default substrate; the outcome is recorded in the registry with
the specialist, so the choice is evidence, not preference. Expect a split verdict —
ternary where it proves, fp where it doesn't — and expect the boundary to move with
params (a ternary specialist at 2–3× params may match fp at a fraction of the bytes;
the protocol measures exactly that trade).

### Tier 1 — Small quantized LMs (the language-shaped layer)
- Per-role LoRA edits on small LMs (roughly 0.1–2B class), 4-bit serving where the
  host is tight; the size ladder applies inside the tier: smallest first, checked,
  up a size only on measured failure.
- Evidence: this lab's anchors and its honest negatives both live here — base scores
  that edits couldn't beat (dose-scaling interpolates to base, never crosses; souping
  two sub-base adapters averages their failure modes; locator maps show a target
  skill diffuse across all probed layers, no indictable slot). Tier 1 is powerful
  and its failure modes are measured, not guessed.
- Exists: the pristine verdict harness (`observe.py`, byte-identical), dev screeners
  with raw-output capture and adapter-resolution guards (`dev_eval.py`,
  `multi_eval.py`), checkpointed trainers for CPU and GPU hosts (`train_ckpt.py`,
  `train_gpu_ckpt.py`), surgery/scale/merge tools (`layer_surgery.py`,
  `scale_adapter.py`, `merge_n.py`, `soup.py`, `probe_locator.py`).
- Missing: (a) a batched/quantized fast-screen runner as the default screen substrate
  (the slow path becomes the exception); (b) per-case cost accounting on every eval
  output (wall-clock per case, recorded — budgets in §6 are unenforceable without
  it); (c) Tier-1 composition as a *served product*, not an experiment (§5).

### Tier 2 — Large LMs (bursts only, proof of need required)
- The biggest local models (multi-B class) for jobs measurement proves Tier 0/1
  cannot own: defect-hunt statistics, sealed verdict suites at scale, whole-hive
  benchmarks. Quantization is chosen by the probe: the tier loads the largest
  precision the host profile fits *with headroom*, and if no precision fits, the
  host doesn't offer Tier 2 (see above).
- Design precedent (sibling line): chunked reading — a small model extracts from
  short chunks, a cell merges and checks, the large model is the comparison, not the
  default reader. Tier 2 as referee, not laborer.
- Exists: the NO-GRADIENT-EDITING.md Phases 0–4 work program; chunked/composed
  reading patterns on the sibling line.
- Missing: a chunked, restart-native large-suite eval runner (suite sizes in the
  hundreds make per-case checkpointing and batching prerequisites, not
  optimizations); weights staged per host by the probe/config, not by assumption.

### Tier 3 — Frontier models via the interface (tools, never the brain)
- Diagnosis from raw outputs, failure clustering, suite drafting, indictment review,
  judging where no checker exists. Text-scale; every proposal logged verbatim in
  lineage so the reasoning is auditable, not just the picks.
- Evidence and limits: the weight-space-programming result is this tier used
  correctly (frontier model as engineer inside a harness, edit independently
  verified); its documented boundary — it indicts well only when an indictable
  defect exists — is why Tier 3 proposes and checkers/sealed tests dispose.
- Exists: this lab's working method (diagnosis, METHODS addenda, contamination
  checking of drafted suites).
- Missing: the interface contract as code — what the loop may ask Tier 3, and what
  it must never delegate (verdicts, gate decisions, anything a checker can decide).

## 5. Composition over escalation (pillar 2)

**Rule:** a job that doesn't fit its tier gets **decomposed, not promoted** — split
any job that can split in two; hard tasks are solved by composition, never by
enlarging one model. Promotion requires a logged, measured capability gap after
decomposition has been attempted.

- **Exists:** the swarm's split/join machinery (`coding/swarm/decomposers.py`,
  `composers.py`; a 27-niche map and a 6/6 composition proof ran on it); the lab's
  composition analysis (`compose.py` — oracle as bound only, jury pick, family
  router, per-case regression gate); the sibling line's honesty rules (a chain that
  can't beat the single model is "trained but not called"; compositions earn their
  place via live audit with a retirement threshold — adopted here as doctrine).
- **Missing:** one composition registry shared by swarm and lab (today the two keep
  separate books); serve-time audit wiring (audit rate + retirement) as code on this
  side; a *served* composition format (today composition is analysis, not a runtime).
- **Changes:** the unified loop composes from the shared registry; every composition
  ships with its audit plan and its fallback (the best single measured candidate)
  or it does not ship.

## 6. Eval economy + restart-native (pillars 3 + 4)

Evals are the scarcest resource on every host profile — a verdict's cost in
wall-clock swings by orders of magnitude across hosts, so the economy is expressed
in two currencies: **item counts** (statistical caps, host-free) and **probe-derived
wall-clock budgets** (mechanical caps, sized by §2's formulas).

**The funnel** (each stage kills cheaply; only finalists reach the expensive end):
1. **Tier-0 verification** — exhaustive where enumerable; else large cheap samples.
2. **Proxy screens** — computable checks, no model (e.g., the lab's synth audit gate
   re-verifying every generated row against its spec before any training).
3. **Dev screens** — small dev suites, pinned protocol (fixed decoding, fixed thread
   policy), chunked under the profile's chunk ceiling. Dev *ranks*; it never crowns
   (recorded precedent: this lab's rejected adapter led dev and lost the sealed test
   by a wide margin).
4. **Confirm split** — held out from selection; sanity-checks any search winner
   before its single test run.
5. **Pristine test** — sealed suites, exactly one run per finalist, frozen code,
   verdicts by paired per-case deltas (sign test), not bare means.

**Budget caps (defaults; config may tighten, never loosen silently):**
- Scalar/coefficient searches: **≤300 dev evaluations**, logged with the running
  best; dev/dev-confirm split mandatory.
- Steering before baking: no weight edit is committed until its inference-time
  version has moved dev (the reversible measurement precedes the permanent one).
- **Ceiling-kill:** every long eval maintains its running arithmetic ceiling; when
  the verdict is mathematically settled, the run stops and records "dead by
  ceiling" with its partials. (This rule, applied by hand, ended three doomed
  candidates early in the repair job and returned hours to the queue.)
- Defect-vs-capability decomposition is mandatory in every gain report (how many
  fixed cases were defect-class vs capability-class flips) — the headline-inflation
  guard.

**Restart-native — stronger here than on a controlled host, because the host is not
ours:**
- **The lineage log is the state.** Append-only, written by every stage; any session
  — human, agent, or a later run of the loop — can reconstruct exactly where every
  candidate stands from the run directory alone.
- **No irreplaceable state outside the run directory, by construction:** caches and
  weights are re-derivable; results, lineage, and registries are the only artifacts
  that matter, and every stage writes them before it needs them.
- **Idempotent, resumable stages:** skip-if-done is the standard contract (generator
  attempts logs, per-case eval checkpoints, trainer checkpoints); a stage re-entered
  after a kill resumes, it does not restart.
- **Chunk ceiling:** no single chunk of work exceeds the host profile's interruption
  horizon divided by a safety factor (on the example "small cloud cell" profile:
  ~2 h horizon → ~20 min chunks). An interruption — reboot, OOM, the owner closing
  the lid — costs minutes, never legs.

## 7. Scheduling layer (pillar 5)

Scheduling is an architectural layer with a queue, not a habit:

- **Sensor-gated queue:** heavy legs start only when the host profile's gates pass
  (temperature headroom where sensors exist, owner-load below threshold, on AC
  power where the host is a laptop, per-host opt-in for heavy work present). The
  gates are parameters read from the profile + config, never constants in code.
- **Burst budgets by regime:** a leg's size is set from the host's *measured* recent
  behavior (rise rates under load, what else is running), the way this lab learned
  to size generation bursts differently when a second heavy job shared the chassis.
  Legs end at their budget or their backoff trigger, whichever comes first —
  mid-leg checkpoints make both cheap.
- **The single-heavy-leg lock** (default on every profile; a profile may opt into
  more only explicitly).
- **Backoff is a first-class event:** cause, duration, and resume are lineage
  entries, so the factory's politeness is auditable — and so is any claim that a
  delay was the host's, not the loop's.

## 8. The unified loop, priced

Stages (each gated by §6; each writes lineage before and after itself):

| Stage | Default substrate | Budget character |
|---|---|---|
| Diagnose (classify failures from raw outputs) | Tier 3 proposes clusters; checkers verify | text-scale |
| Map / indict | Tier 0 flip-maps (near-exact) at Tier 0; activation statistics at LM tiers | one burst, statistics small |
| Edit (ablate / dose / merge / flip / surgery) | closed-form tensor ops; flips at Tier 0 | ~free; evals are the cost |
| Train — indicted units only | Tier 0 in-process; Tier 1 checkpointed trainer | bounded by indictment size |
| Dream (self-generated practice, §10.1) | Tier 0 generators + execution checkers; thermostat-steered | idle-time; generated pools are count-capped per cycle |
| Chain / compose | registry + audit plan | screens only until adopted |
| Grow (spawn a specialist for an ownerless job) | Tier 0 first (both substrates) | one production cycle; births gated (§10.2) |

**Graduation bar:** the loop runs these stages end-to-end without hand-driving and
surfaces only verdicts (per `coding/IDEA.md`).

**Build list for the unification phase (ordered):**
1. **Host probe + profile module** (§2) — the factory's first component; every other
   component reads sizing from it.
2. **Scheduler** (§7) — sensor-gated queue, burst budgets, backoff, the
   single-heavy-leg lock.
3. **Tier-0 front door + spawn-mining intake** (§4) — every job attempts Tier 0
   first; logged fixed-value call sites feed new-specialist proposals.
3b. **BitNet substrate** (§4, Tier 0b) — QAT (straight-through estimator) trainer +
    direct-construction path for ternary specialists; per-weight flip-ablation
    mapper (ternary-aware surgery); ternary persistence in the shared registry;
    the head-to-head harness (ternary vs fp per niche: held-out score, footprint,
    latency) whose results set each niche's default substrate.
4. **Shared composition registry + serve-time audit** (§5) — swarm and lab
   candidates in one book; audit/retirement wired.
5. **Fast-screen runner** (§4, Tier 1) — batched/quantized screens with per-case
   cost accounting on every eval output.
6. **Tier-3 interface contract** (§4) — what the loop may ask, what it must never
   delegate.
7. **The loop itself** (§8 table) — stages wired behind the gates; verdict-only
   surfacing.

## 9. Final factory report contract

Alongside the whole-hive benchmark and per-suite verdicts, the final report carries
the factory's **measured compute profile**, so the architecture is judged by the
numbers it was designed to move:

- **Cost per verdict** (wall-clock and machine profile) for each sealed test run.
- **Cost per adopted specialist** (production + all screening that led to it).
- **Eval budget spent vs caps** (§6), per search/screen.
- **Stress ledger:** heavy-leg count, backoff events with causes, any thermal
  incidents — the politeness record, stated plainly.
- **Substrate line:** per niche, which Tier-0 substrate (ternary / low-bit / full
  precision) the head-to-head protocol chose, with its held-out score, footprint,
  and latency beside the losing substrate's — the substrate must be seen to earn
  its place, niche by niche.
- **Portability line:** which host profile(s) the results were produced on, and any
  result re-verified on a second profile, stated as such.

## 10. Phase C — dreaming, growth, and the harvested ideas (2026-11-10)

Added at Arnav's direction (2026-11-10 ~12:54 PT: "add that in your part with
increasing number of specialists and all other ideas"), built the same day.
Sources harvested: Ripple-65B's post-training recipe
(`~/workspace/research_notes/ripple-small-coding-model-2026-11-10.md`) and the
LeCun / Fei-Fei Li small-specialist research
(`~/workspace/research_notes/lecun-feifei-small-specialists-2026-11-10.md`).

### 10.1 The dream cycle (new loop stage)

An idle-time stage in which a subject **generates its own practice tasks** and
trains on them, following the recipe the research verified three times in one
day (Ripple's steep-ascent RL, s1's selection, this lab's Phase B widen):

- **Capability matching — the difficulty thermostat.** Generation is steered
  per class by fresh probes: the training band is the lowest difficulty band
  whose positive-class recall is not yet mastered (mastery ≥ 0.90); mastery
  steps the band up, weakness holds the band. Recall, not accuracy — binary
  accuracy is dominated by the negative majority and hides the weakness being
  treated. Thermostat state is persisted per subject/class across cycles and
  logged every round.
- **Execution/checker verification ONLY.** Every dreamed task carries a
  programmatic proof: for code families the correct program must run cleanly
  on probes and each labelled mutation must be *observably* different
  (behavioral signature, including across repeated calls for state bugs).
  Unverifiable dreams are discarded and counted, never trained on. There is
  no label-by-assertion anywhere in the stage.
- **Coverage metrics + diversity quota.** Kept dreams are tallied by
  class × band × slice; within a class no slice may exceed half the positive
  groups (s1's diversity lesson, priced by its ablations at ~30%).
- **s1 filters.** What the incumbent already solves is deleted (group-aware
  difficulty filter: a case and its second view stay or go together); a
  quota of already-solved groups is kept for stability, nothing more.
- **Good views.** Every kept case is stored in two surface forms — the
  original and an identifier-renamed rendering, itself execution-verified to
  behave identically (for the clean case) or differently in exactly the same
  way (for a mutation).
- **Probe hygiene (standing rule, all stages).** Probes, screens, and
  confirm sets are generated from disjoint draws and contamination-filtered
  against *all* training data (original train, prior dream corpora, and the
  current cycle's dream-train pool). No factory measurement ever again runs
  on training rows — the internals lab's regime lesson (a verdict model
  trusted fingerprints measured on gold rows and failed its real exam) is
  factory law now. Screens that share *skeletons* with training data are
  not screens: the screen gets its own structurally distinct generators.

Dreaming is the legitimate executor for subjects with no harvestable external
surface (the bug-pattern composition, which Phase B had to BLOCK): the data
is synthetic, but the labels are proved by execution and the win-gate is the
same gate every other executor faces — threshold + per-class no-regression,
confirm spent once.

### 10.2 Specialist growth — intake and split births

The registry grows only through measured births:

- **Intake** scans the lab's own evidence: adopted versions feed back into
  diagnosis (a subject *is* its adopted v2 — Phase B's stale-intake defect,
  fixed); decidable slices of a class with no specialist of their own are
  enumerated against the serving parents' per-slice scores.
- **Split rule.** When a subject's errors cluster into a coherent sub-class
  (a decidable slice) with enough verified cases, intake proposes a split:
  a narrower child is trained for the slice (parent keeps the rest).
- **Birth gate (binding).** The child must *beat* the parent on the slice's
  held-out subset, strictly. The remainder is served by the parent unchanged
  (routing is by slice), so remainder regression is impossible by
  construction; the child's remainder score is still measured and recorded.
  A tie is not a birth. Under-data candidates are not attempted. Every
  attempt — born or rejected — is a lineage entry with its numbers.

### 10.3 Cross-family agreement (verification signal)

Harvested read-only from the sibling line's measured finding (two different
model families printing the same answer were right 58/58): at verification,
agreement between *different* substrates/families is an extra trust signal.
Where they agree, confidence rises; where they disagree, the served verdict
routes to abstain/recheck instead of being trusted. First wiring: the
ternary head-to-head reports fp↔ternary agreement per niche (0.74–0.99
measured); disagreement counts are reported beside every substrate verdict.

### 10.4 Consultation composition (compose-stage direction)

The compose stage matures from routing/jury composition toward
**consultation**: members are trained *together but separately* — separate
weights, but each member's training inputs include the other members'
outputs (cross-fitted, so no member trains on its own echo), and a learned
consult head is trained on the chain's cross-fit outputs where no checker
exists. Adoption requires the composed system to beat BOTH the best single
member and the rule-routed composition on the same held-out set — the
three-way comparison (a) best single, (b) rule-routed, (c)
consultation-trained. **Dependency:** the design follows the
internals-specialist's Phase 5 spec (`internals-specialist/SURGERY.md`,
"composition: trained together, separate weights, one diagnosis"); its
verdict section was still a placeholder when this was written, so factory
consultation is specified here but ships only after that verdict lands.
The fail-closed shell (loading, run loop, IO, gate enforcement) stays code,
per the harness-of-models directive: a learned part that measures worse
than the rule it replaces does not ship.

### 10.5 Ternary mapper stage (build item 3b, delivered)

The Tier-0 substrate protocol now runs: per-row-scale quantization
(calibrated on training data only), a born-ternary QAT (STE) trainer
mirroring the swarm optimizer, and the per-weight **flip-ablation mapper** —
at three states per weight the indictment map is near-exact, and it is the
map evidence `contracts.Indictment.weight_edit_justified` requires. The
head-to-head decides each niche's default substrate by the standing rule
(ternary ships only where it measures ≥ fp on held-out), recorded in the
registry either way. First results in FACTORY-LOOP.md (Phase C): fp kept
all five niches; QAT ≫ naive quantization on words-mode niches; flip
surgery repaired a quantized model measurably (+2.3 pts held-out) without
closing the gap to fp — the instrument works, the substrate verdict is
honest.

### 10.6 Scheduling and reporting (pillars 5 and §9, delivered)

- **Scheduling:** the cross-process single-heavy-leg lock (staleness-broken,
  contention reported rather than slept on) and a persistent cycle queue
  now exist as code (`factory/scheduler.py`); the governor remains the
  admission decision. No heavy leg has ever been admitted — every leg so
  far is seconds-class Tier-0 — but the discipline is built before the
  first heavy leg needs it.
- **Reporting:** `factory/reporter.py` computes the §9 contract from the
  factory's own records (cost per verdict, cost per adopted specialist,
  eval budget vs caps, stress ledger, substrate line, portability line)
  into `factory/reports/`.
