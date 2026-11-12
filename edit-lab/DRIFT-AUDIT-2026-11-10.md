# Drift Audit — 2026-11-10

**Charge (Arnav, 2026-11-10 13:43 PT):** *"Wdym surgery failed? Consulting
specialists are worse — then maybe something is off, or maybe you drifted from
the idea or interpreted it wrong. Check, read and understand Fable's side."*

**Clarification (Arnav, 2026-11-10 13:46 PT):** *"Surgery on your own models
that we just trained right now."* His spec for surgery: it applies to OUR OWN
freshly TRAINED models — train first (capability must exist), then edit.

**Question:** did my side implement Arnav's ideas (weight surgery;
together-but-separate consultation) in a way that drifted from the ideas as
Fable's side implements them successfully?

**Method.** Fable's side read read-only at make-it-work head `c9b1e2aa`
(detached worktree `~/workspace/fable-audit-copy`; nothing written to their
branch, ever). My side read at `~/workspace/edit-lab/internals-specialist/`.
Spec sources: `~/workspace/IDEA-LOG.md`, `~/workspace/edit-lab/coding/IDEA.md`
(the swarm constitution), `~/workspace/edit-lab/METHODS-FROM-MAKE-IT-WORK.md`
(my own earlier harvest from their line), and the surgery round's own record,
`internals-specialist/SURGERY.md`.

---

## 1. The reference implementation — how Fable's side actually does it

### (a) Improving a specialist
- **School** (`team/school.py`, module docstring): lessons are real tasks from
  the logs plus tasks the teacher writes itself; **the teacher does the job on
  every lesson** and the lesson is kept only if the answer is usable (a plan
  that parses; a program that runs and prints). The student is then edited
  (LoRA) on the non-exam lessons — the training target is **the teacher's
  actual work product** (the plan text, the program text). Exam on lessons
  never trained on; graduation requires ≥ 0.85 agreement with the teacher AND
  ≥ +0.03 over the untouched student (`school.py:36`: GRADUATE 0.85, MARGIN
  0.03). Later visits: the lessons the current specialists get wrong are a
  **gap**; the teacher writes more tasks of that kind; a NEW narrow specialist
  learns that gap and nothing else; nobody is retrained or replaced.
- **teach_fixes** (`school.py`): fix-lessons are built from the students' REAL
  wrong programs plus **the hive's own feedback text** (`coder.plain_feedback`);
  the teacher's fix is a lesson only if it reproduces the teacher's original
  output. Consultation artifacts (feedback) become training data.
- **Dream** (`team/dream.py`): `distil` turns every model call inside a step
  the verifier PASSED into a training example for that specialist — its own
  verified work. `retrain` trains a candidate LoRA and promotes it **only if
  it does not score lower** on the role's held-out eval suites
  (`promoted = after >= before`, scored via `training/observe.py`).
- **Evolve** (`team/evolve.py`): prompt variants are bred from examiner
  diagnoses of real failures; the selector promotes a variant **only if it
  scores strictly higher** on held-out evals; every candidate and decision is
  logged (lineage).

### (b) Consultation / composition — what actually passes between models
Three distinct mechanisms, all over a **shared object**:
1. **Hive level** (`team/hive.py`): full WORK PRODUCTS pass — the
   coordinator's plan (itself reviewed against a checklist,
   `coordinator.reviewed_plan`, hive.py:117), step results, and the
   verifier's written reason (`verifier.verify` → `(verdict, why)`,
   hive.py:204). A failed step is **retried with the feedback text inside the
   task** (`"Previous attempt was rejected: {feedback}"`, hive.py:178), the
   coordinator may **reroute** the step to another specialist (hive.py:229),
   bounded by MAX_RETRIES. A judge's output REVISES the work in further
   rounds; it does not merely score it.
2. **Cell level** (`training/scratch.py`, class `Brain`, lines 293–312):
   ONE shared trunk reads the input; a small head per job; with `--consult`,
   each head's final layer sees **[trunk representation ‖ the concatenation
   of EVERY head's softmax distribution on the SAME input]** before deciding
   ("the cells consult each other"). Trained **jointly** on all jobs at once
   with loss = CE(final) + CE(own first-pass) (scratch.py, `together()`), on
   the same rows/dev/test as the cells trained alone. The brain takes a job
   only where it measured at least as well as the present holder
   (`tiny.decide_holds`). The jobs are different closed-label questions about
   **the same input text** — their answers are correlated through the input
   itself.
3. **School level** (`school.py` `exam()`/`majority()`): each specialist
   produces a COMPLETE answer; composition is a majority over extracted
   **decision keys** (what a plan decides = the specialist sequence; what a
   program decides = what it prints when run), or territory routing. A scheme
   with more specialists is used **only where it measures better** (MARGIN).

### (c) Weight editing — what is edited, at what scale, gated how
- The edit is a **trained LoRA delta** (`training/train_lora.py`: low-rank
  delta restricted to chosen layers/projections, loss on the specialist's
  reply tokens only), trained by gradient descent on verified work products —
  never a post-hoc zeroing of weights chosen by a knockout map.
- The subject is a **pretrained LLM** (135M–7B) whose capability comes from
  pretraining; the edit steers/exposes existing capability. Arnav's direction
  as recorded in their HANDOFF.md: *"A weight edit may do nothing where the
  model has no capability; train specialists, then edit"* — and the
  weight-space-programming finding they logged from his research pointer:
  *"tiny localized edits expose an ability a model has, do not create one."*
  Measured instance in HANDOFF: the planner edit taught 24/24 short plans and
  3/22 long ones — it worked exactly where capability existed to expose (the
  teacher's long plans are themselves padded/inconsistent, so there was
  nothing sound to expose).
- Their one zeroing-style edit: **dead layers found by knockout were pruned**
  (8 layers, 144 MB → 115 MB base; `METHODS-FROM-MAKE-IT-WORK.md`) — removal
  of provably zero-contribution structure; capability-neutral compression,
  not accuracy repair.
- Their locator study (gradient + knockout maps over modules) measured the
  **concentrated indicted-set pick LOSING on 11 of 15 skills** to thin
  edits spread across all modules (`METHODS-FROM-MAKE-IT-WORK.md`, with the
  caveat recorded there that this was for ADDING skills). Selection
  discipline: winners chosen on a DEV split, test run once; *"single-case
  differences are noise"* is stated plainly in their reports.

---

## 2. My implementations, as built

### Surgery round (`internals-specialist/surgery_*.py`, SURGERY.md Phases 1–2)
- Protocol: per-weight/per-unit knockout map on a frozen validation set →
  indict by a pre-registered rule → apply ONLY the indicted edit (zeroing a
  weight; flipping ternary weights) → ONE evaluation on the frozen held-out
  set → gate: held-out improves AND no class recall regresses > 2 pts
  (`surgery_t3.py` docstring). This is the swarm constitution's protocol
  (`coding/IDEA.md` point 6: trace → find every responsible weight → make the
  map → change only what the map indicts) implemented literally.
- Subjects: **T3**, a LINEAR model — 13 kept summary features × 3 classes =
  39 weights + 3 biases; **T2 fp**, a linear class head (44 params) + an
  MLP-24 scorer (458 params); and their ternary twins. All were trained that
  morning on **constructed data** (planted-truth synthetic nets), and their
  ONLY inputs are hand-crafted summary statistics of a fixed-budget probe
  (features.py `edit_features` / `global_map_features` / `per_layer_features`).
- Results: T3's one validation-passing edit (+1.0 pt on n=94 = one case)
  failed held-out (0.806 → 0.800) — reverted. T2 fp: 64 individually-positive
  zeroings cratered validation jointly (0.734 → 0.679) — null. T2 ternary:
  123 individually-positive flips collapsed validation jointly
  (0.761 → 0.587) — null. Headroom fact: the ternary scorer's validation
  argmax (0.744) **exactly equals the probe instrument's own argmax ceiling**
  (0.744 val / 0.736 held).

### Composition Phase 5 (`internals-specialist/composition.py`, SURGERY.md Phase 5)
- What "consultation" passed (`cross_feats`, composition.py:230–240):
  **three scalars** computed by FROZEN specialists about the MAP part —
  `t1_dead_frac`, `t2_p_conc`, `t2_top_score` (plus optionally the regime
  detector's P(gold), which failed its own gate and was excluded). T3/T4 were
  then **retrained as separate models** on [own features ‖ these scalars].
  No shared representation, no joint gradient, consultants never adapted.
  Chain = one forward pass T1→T2→T3→T4. The chain gate (judge) is a small
  MLP over confidences/agreement bits that can only **abstain**, never send
  work back.
- The testbed's causal structure (`gen_composed2.py:143–162` +
  `gen_constructed.py:gen_edit_case`): the map part's profile is
  `PROFILES[i % 5]` and the edit part's regime is
  `EDIT_REGIMES[i % len(EDIT_REGIMES)]` — independent cycles on the case
  index. The edit is built by `gen_edit_case(base_pack)` where the base pack
  carries the bare base net: **the incumbent adapter exists only inside the
  map case's fingerprints; it is never applied when the edit's dose-response
  labels are measured** (labels are computed against the adapter-free base
  loss). The two parts' truths are therefore **causally independent given
  the base**, and everything shared (the base itself) is already visible to
  T3 through its own fingerprint of the edit.
- Results (98 scored held-out chains): singles (a) chain 0.214; rule-routed
  (b) 0.214 (rules inert — with T1 exact, the guarded situations never
  arose); consultation-trained (c) 0.194, with T3c at 0.786 vs the frozen
  model's 0.816. SURGERY.md's own interpretation — "independent by design…
  almost no cross-signal for consultation to exploit" — is **verified
  correct about the testbed** by the generator code above.

---

## 3. Verdict — SURGERY

**Protocol implemented faithfully. Subject selection and claim scope
drifted. The null result is TESTBED-INVALID for Arnav's surgery idea as
specified; it refutes only a much narrower hypothesis.**

1. **The protocol was not the drift.** Map → indict → edit only the indicted
   → re-measure under a pre-registered gate is exactly `coding/IDEA.md`
   point 6, and it was followed to the letter, including reverting on gate
   failure.
2. **The capability precondition (Arnav, 13:46) was satisfied only in the
   thinnest literal sense.** The subjects were freshly trained — but:
   - **T3 is linear.** There is no representation/readout distinction in a
     linear model: every weight IS a readout weight. Zeroing can only delete
     a feature's vote; it cannot "expose an ability the model has" because
     there is no latent ability beneath the readout. The mechanism Arnav's
     spec (and the weight-space-programming finding) relies on does not
     exist in this substrate.
   - **Both models sat at the information ceiling of their inputs.** The
     ternary scorer's argmax equals the probe's own ceiling exactly; T3's
     errors were dominated by probe-protocol/regime information that is
     simply not present in its 13 summary features. No weight configuration
     — edited or fully retrained on the same features — can recover
     information that never entered the network. The data-regime fix won
     precisely because it changed the INFORMATION, not the weights. On
     Fable's side the edited subjects are pretrained bases whose capability
     vastly exceeds any single behaviour, so an edit has something to expose;
     and their edits are **trained** (LoRA on verified work products),
     gated on behavioural held-out suites — a different operation from a
     post-hoc defect hunt, aimed at a different failure mode (capability
     not yet steered, not "a few bad weights").
3. **The joint-collapse results were predictable under Fable-side
   discipline.** Individually-positive single-weight changes measured on
   n≈94–109 validation cases are mostly noise (their rule: single-case
   differences are noise; dev selects, test confirms, run once). T3's
   val +1.0 pt was literally one case. Their locator study had already
   measured concentrated indicted-set edits losing to breadth on 11/15
   skills; my T2 joint application (64 "improvements" → −5.5 pts) is the
   same phenomenon from the removal side.
4. **Counter-evidence on my own side, same day:** the factory's flip-map
   surgery on **secret-line** — a real swarm specialist trained on real
   niche data — indicted 114 improving flips on TRAINING probes, applied
   them, and was judged ONCE on held-out: **0.9154 → 0.9385, ADOPTED** as a
   coexisting ternary artifact (`edit-lab/LEDGER.md:404`;
   `factory/runs/phaseC-ternary-002/ternary_results.json`: heldout_before
   0.9154, heldout_after 0.9385, flips_applied 114). Surgery per protocol,
   on a real trained specialist, passed its gate. The internals round's
   headline — "surgery lost… the defects were never in the weights" —
   overreached its testbed and is rescoped in §6.

**What the surgery result actually proves:** in these two
feature-bottlenecked verdict models, the errors are not carried by a small
set of indicted weights, and no zero/flip edit generalizes — the binding
constraint was the instrument and the input information. **What it does not
say:** anything, in either direction, about surgery on freshly trained REAL
specialists whose capability exceeds their readout — the population Arnav's
spec (13:46) and Fable's practice actually concern. The corrective test of
the full spec — a surgery arm on the weights-reader pilot's just-trained
reader and part-specialists, gated the same way — is already in flight on
my side; it settles the question only if its subjects are trained on real
(weight) data to a capability above their current readout and the edit is
judged once on held-out families.

---

## 4. Verdict — CONSULTATION (together-but-separate)

**DRIFTED — in mechanism and in testbed. The Phase 5 negative result does
not transfer to Arnav's idea; it falsifies only the mechanism actually
built, on data where consultation had provably nothing to work with.**

Divergences, ranked by how much they plausibly explain the negative result:

1. **The data: causal independence (deepest cause).** Every Fable-side
   consultation operates over a SHARED object — the same input rows
   (scratch Brain), the same task and step result (hive loop), the same job
   (school voters). Mine consulted across two causally disjoint objects:
   T3 was handed summaries of an incumbent adapter that played no role in
   generating T3's labels (§2, generator evidence). With mutual information
   ≈ 0 by construction, consultation features are pure noise dimensions,
   and the observed degradation (T3 0.816 → 0.786; chain 0.214 → 0.194) is
   the expected cost of fitting noise — not evidence about consultation.
   **Testbed-invalid.**
2. **What passes: 3 scalars vs work products / full distributions.** Fable
   passes complete answers (plan/program text), critique TEXT that re-enters
   the task, full per-head softmax distributions over the same input, or
   decision keys of complete answers. Mine passed three scalar summaries of
   a *different* object's profile into a downstream model. Even where signal
   exists, that channel is orders of magnitude narrower.
3. **No jointness.** Fable's Brain trains all heads jointly through a shared
   trunk, with an own-pass loss keeping each head honest and a final loss on
   the consulted decision — the consultees adapt to being consulted. Mine
   froze the consultants and retrained only the consumer on donated
   features; nothing about T1/T2 was shaped by T3's needs.
4. **No iteration; the judge cannot send work back.** Fable's verifier's
   written feedback re-enters the task for bounded retries and reroutes.
   Mine ran a single pass; the chain gate could only abstain, and it read
   confidences rather than the work product. (Partial exception on my side:
   the T2-scorer arm — T1's per-layer dead-probability appended for the SAME
   map object — is structurally Fable-like, same object, per-layer signal.
   It performed at parity: val 0.744 = frozen, held 0.704 vs 0.714. No harm,
   no gain — at an instrument ceiling, on the one arm where the mechanism
   was closest to spec.)
5. **Not drifted:** the adoption discipline. Phase 5 pre-committed to
   "the ensemble earns its place only if (c) beats (a) and (b)" — the same
   measure-or-it-doesn't-ship rule Fable's school exam applies (a scheme is
   used only where it measures better, by a margin). The rules arm (b)
   being inert is a testbed property (T1 exact ⇒ guarded situations never
   arose), recorded as such at the time.

---

## 5. Re-test — consultation on coupled data (PRE-REGISTERED)

*Registered 2026-11-10, before the re-test code was run. The re-test
changes ONE variable at a time relative to Phase 5: the DATA gets the
shared-object property Fable's consultation requires; then the MECHANISM
arms are compared on that data.*

**Coupled generator** (`gen_composed3.py`): as gen_composed2, except the
candidate edit is **evaluated and fingerprinted on top of the incumbent**:
labels are dose-response relative to the incumbent-carrying baseline
(`base + incumbent` vs `base + incumbent + dose·edit`), and the edit's
probe maps are measured in situ on the combined adapter. The incumbent's
planted profile (dead layers, concentration) now causally affects the
edit's truths. New seed (404); 320 train / 128 held-out cases (as amended below); edit regimes
restricted to the five single-adapter regimes (matched / narrow / overfit /
shuffled / random); profiles and (L, width) cycling as in gen_composed2.

**Arms** (all trained on the same coupled train split, judged once on the
same held-out split; primary metric = T3 verdict accuracy, paired vs (a)):
- **(a) Singles:** v1-recipe T3 on the edit's own in-situ features only.
- **(b) Phase-5 mechanism:** (a) + the same 3 frozen-specialist cross
  scalars (`composition.cross_feats`).
- **(a2) Oracle:** (a) + the incumbent's TRUE descriptors (true dead
  fraction, true T2 class, true dominant-layer precise share, top share) —
  the upper bound on what any consultation channel could carry.
- **(c) Fable-style:** shared trunk over [edit features ‖ map global
  features]; per-job first-pass heads (T3, T4-band, T2-class, dead-fraction)
  each with an own loss; second-pass T3/T4 heads over [trunk ‖ concatenated
  first-pass distributions] with final losses — the scratch-Brain mechanism
  (joint training, full distributions, own+final losses).

**Compute amendment (recorded before any re-test results exist):**
generation profiling showed ~20–55 s per case on this VM, 75% of it the
8192-row precise-knockout labeling — the pre-registered 544 cases would
take ~3 h. The generator therefore labels from a 4096-row pool
(`LABEL_POOL` in gen_composed3.py) for BOTH parts' labels. Every arm
shares identical labels, so the paired comparisons and the bars below
are unaffected; absolute label noise is slightly higher than the
8192-row family and is carried as a stated limitation in §6.
**Amendment 2 (same status — before any results):** live pacing still
projected >3 h, so counts are reduced to **320 train / 128 held-out**
and the map generator's profile-refinement iterations (which only push
planted shares toward their targets) run on a 1024-row pool; final
labels still come from the 4096-row precise knockout. Consequence,
stated now rather than after the fact: at n=128, 1 case ≈ 0.8 pt, so
gaps of 3–5 pts are WEAK evidence and only gaps ≥ 5 pts or the paired
win/loss pattern will be read as decisive.

**Bars (fixed now):**
- **P1 — signal exists:** (a2) − (a) ≥ +3.0 pts held-out T3 accuracy ⇒
  exploitable cross-signal exists in coupled data. (n=128 ⇒ 1 case ≈
  0.8 pt; paired win/loss counts reported alongside every gap.)
- **P2 — mechanism verdict (only if P1 passes):** (c) − (a) ≥ +3.0 AND
  (c) ≥ (b) ⇒ Phase 5's failure was mechanism + data (drift confirmed on
  both layers). If (b) − (a) ≥ +3.0 AND |(c) − (b)| < 3.0 ⇒ the failure
  was data-only: testbed-invalid, mechanism exonerated.
- **P3 — if P1 fails:** folding the incumbent into the evaluation does not
  create exploitable signal through these instruments; the consultation
  question for this task family stays OPEN. The named stronger test (not
  run here): school-style coupling — edit lessons generated FROM the
  incumbent system's own failures (their `teach_fixes` pattern), where
  consultation is over the incumbent's actual work products.

**Surgery re-test:** none run in this audit — a decisive one already
exists on my side (secret-line flip surgery, §3.4, executed and adopted)
and the full-spec corrective (surgery on the just-trained weights-reader)
is in flight in that pilot. Running a third, weaker surgery test here
would add noise, not evidence.

## 6. Re-test results (appended after the run, per the §5 pre-registration)

Generation: 448 coupled cases (320 train / 128 held-out; seeds 404/505),
`data/composed3_{train,held}.jsonl`; arms run by `audit_retest.py`,
raw output in `data/audit_retest_results.json`. Held-out T3 class counts:
HELPS 47 / HURTS 39 / INERT 42.

**First, the coupling sanity check — did the shared-object property
actually bite? Yes, hard, at the label level.** Conditioning the edit's
verdict on the incumbent's true dead-layer fraction:

| | P(HURTS \| low dead) | P(HURTS \| high dead) | P(INERT \| low) | P(INERT \| high) |
|---|---|---|---|---|
| composed3 (coupled, this re-test) | 0.275 | **0.592** | 0.413 | **0.122** |
| composed2 (Phase 5, independent) | 0.417 | 0.430 | 0.324 | 0.246 |

In Phase 5's family the incumbent's profile says nothing about the
edit's verdict (flat conditionals — the independence of §2/§4, now also
visible at the label level). In the coupled family it shifts the
verdict distribution strongly. The re-test's data has the property
Fable's consultation requires.

**Arms (held-out, n=128; primary metric T3 accuracy):**

| Arm | T3 acc | Δ vs (a) | Paired vs (a): both / a-only / arm-only / neither | T4 acc (secondary) |
|---|---|---|---|---|
| (a) singles | 0.672 | — | — | 0.617 |
| (b) Phase-5 mechanism (3 scalars) | 0.664 | −0.8 pts | 74 / 12 / 11 / 31 | 0.508 |
| (a2) oracle descriptors | 0.672 | 0.0 pts | 73 / 13 / 13 / 29 | 0.594 |
| (c) Fable-style (shared trunk, distributions, joint) | 0.656 | −1.6 pts | 72 / 14 / 12 / 30 | 0.617 |

**Applying the pre-registered bars:**
- **P1 FAILS.** (a2) − (a) = 0.0 pts < +3.0. Even the incumbent's TRUE
  descriptors — information no consultation channel could exceed — add
  nothing over the edit's own features. Per the pre-registration this
  triggers **P3**: the consultation question for this task family stays
  open, and the mechanism verdict (P2) is not reached.
- **Why P1 fails is itself measured, not guessed:** the edit's
  fingerprint in this family is probed **in situ** — its gradient and
  knockout maps are measured on the combined (base + incumbent + edit)
  system — so the incumbent's entire causal influence on the edit is
  already mediated by the edit's own instrument readings. The oracle
  descriptors are cleaner measurements of quantities whose *effect* the
  fingerprint already carries. A consultation channel is redundant for
  a diagnostician who can probe the combined system directly.
- Arm (b) replicating Phase 5's small T4 degradation (0.508 vs 0.617)
  on coupled data confirms the 3-scalar donation is at best inert for
  the verdict and mildly harmful for the band call, independent of the
  data's coupling — that narrow mechanism is falsified twice now.
- Arm (c) caveat, stated plainly: its validation split was small
  (n=48; best-epoch val 0.771 vs held 0.656), so its model selection
  was noisy. But no configuration — final head 0.656, own head 0.664 —
  approached beating (a), and under P1's failure the mechanism
  comparison is moot: there was no unexploited signal for any
  mechanism to capture.

**What this settles and what it does not.** It settles that Phase 5's
negative verdict was overdetermined: its data had no cross-signal
(§4.1) AND its channel was the weakest form (§4.2) — and it shows the
deeper reason consultation cannot pay *in this constructed family
even when coupled*: the parts share an instrument, and the shared
instrument already sees everything. Fable's consultation operates in
the opposite regime — the consulted signal is **not recoverable from
the subject's own view**: a different model family's complete answer
to the same question, a teacher's work product, a verifier's feedback
text about a real run. None of my arms — including the Fable-style
one — reproduced THAT property, because in this family there is only
one instrument and it belongs to the subject. The §5-named stronger
test (school-style coupling: edit lessons generated from the
incumbent system's own failures, the verdict chain consulting the
incumbent's actual failure record — information the edit's probe
cannot contain) remains the decisive one for Arnav's idea, and it is
still unrun.

## 7. Corrected statements (rescoped honestly)

- **Surgery.** OLD (SURGERY.md headline): "Surgery lost; the defects were
  never in the weights." CORRECTED: "Post-hoc zero/flip defect-hunting
  found no generalizing edit in two tiny verdict models that sit at the
  information ceiling of their hand-crafted input features — one of them
  linear, where the expose-latent-ability mechanism cannot exist. The
  result is silent on surgery applied per Arnav's spec — train a real
  specialist first, then edit — and my own side has a same-day positive:
  flip-map surgery on the real secret-line specialist, +2.3 pts held-out,
  adopted."
- **Consultation.** OLD (as reported upward): "training them to consult
  each other made it worse — their jobs don't inform each other."
  CORRECTED: "the jobs were BUILT not to inform each other: the consulted
  summaries described a causally unrelated object, through a 3-scalar
  channel, into frozen consultees, in a single pass. That falsifies
  cross-object scalar feature-donation, not consultation. On the one arm
  where consultation was over the same object (T2 scorer), it was neutral
  at an instrument ceiling. The §5–§6 re-test then showed that even on
  coupled data with the Fable-style mechanism, consultation adds
  nothing in this family — because the subject's own in-situ probe
  already mediates everything the other parts know. Arnav's idea
  remains untested in the regime Fable's side actually operates in:
  consulted signals that are NOT recoverable from the subject's own
  instrument (work products, other families' answers, feedback text)."
- **The 'data beats weights' pattern** reported to Arnav on 2026-11-10 is
  likewise rescoped: every DATA-side win today was on real or
  regime-realistic data with capability present; every WEIGHT-side loss
  was on feature-bottlenecked or causally-disjoint testbeds. The pattern
  is at least partly an artifact of where each lever was tried.

## 8. What would settle what remains open

- **Consultation:** §5–§6 ran with this audit and P3 triggered. The
  remaining decisive test is the teach_fixes-style one, now with a
  sharper hypothesis from §6: consultation pays only when the consulted
  signal is NOT recoverable from the subject's own probe. Design:
  generate edit lessons from the incumbent system's own failures and
  let the verdict chain consult the incumbent's actual failure record
  (which cases it fails, its verifier feedback) — information the
  edit's fingerprint cannot contain. Cost: one generator variant +
  one training run, same scale as §5.
- **Surgery on real specialists:** the weights-reader pilot's surgery arm
  (in flight) — provided its subjects are trained on real weight data and
  judged once on held-out families. A second, independent instance is
  cheap on the coding swarm: pick a Phase-B v2 specialist with a measured
  residual error class, run map → indict → edit under dev-select /
  test-confirm discipline (dev split ≥ 300 cases so an indictment is more
  than one case), judge once. Cost: hours of CPU, no new machinery.
