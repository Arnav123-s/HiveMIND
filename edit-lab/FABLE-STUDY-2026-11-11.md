> **Muse's work** — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# Study: Fable's HiveMIND work — its style, ideas, mechanisms — and what they mean for Muse's side

Written 2026-11-11, read-only against `~/workspace/fable-audit-copy` (make-it-work `d31fd51`,
main `8be45ff`, 329 commits), its `README.md` / `SPEC.md` / `HANDOFF.md`, the repo's own
`training/reports/`, and this lab's validation notes (`fable-validation/VALIDATION.md` +
`VALIDATION-ADDENDUM-2026-11-11.md`, independently re-run: 199 tests pass at `d31fd51`).

Directive (Arnav, 2026-11-11, final form): Fable improved the hive's architecture and
kernel/compute optimization a lot; the key is *understanding its work* — style, ideas, what it
is doing — then using that understanding to make **Muse's side** better. One-way valve held:
this study writes nothing to Fable's side. It supersedes `METHODS-FROM-MAKE-IT-WORK.md` where
it goes deeper; the three methods arms adopted from that note on 2026-11-11 (recipe
head-to-head, breadth edit, dream-first repair) are **not** re-proposed here.

Honesty rule used throughout: every Fable number below is cited from its own committed
records, and where its records say a thing failed, was not run, or is unproven, this study
says so too.

---

## 1. Fable's style — how it works as an engineer

Eight habits, visible across all 329 commits. Each is stated as a rule because Fable states
its own rules the same way.

### 1.1 One rule at every level: vary, measure on fresh material, keep only what is better

The README's own summary of the whole system: *"One rule at every level: try a variation,
measure it on fresh material nobody tuned on, keep only what is better."* This is not a
slogan — it is the literal control flow of every subsystem: cells take jobs only where they
measured ≥ the incumbent (`cells/wins.json`); a body keeps a newborn cell only if the body
then predicts better on a gate set; a founding changes exactly one recipe gene and the new
recipe becomes the one to beat only if its stem cell reads better; the school promotes a
student at 85% teacher agreement **and** +3 over the untouched student. Nothing in the repo
is adopted on argument. Commit `bea40f6` ("The say of each member is learned: the body stops
being winner-takes-all") shows the rule applied even to a *combination rule*: the fixed
winner-take-all mixer was itself replaced by a learned one because the learned one measured
better (`learn_say`, §2.5).

### 1.2 The commit is the lab notebook

Commit subjects are written as *findings*, not as file operations. A large share of the 329
read like results lines:

- `b234b97` "The third body is founded with the better recipe and measured; three bodies as one read 2.4760"
- `825ade8` "The hive is measured on a fixed yardstick too; the held-passage flaw is sized (about 0.04)"
- `334603b` "The measured BitNet recipe comparison as a report; the teacher is off by default (it loses at equal time)"
- `6249578` "Direct BitNet training, second attempt… The first attempt measured: its jumps taught nothing on real text (4.25 with, 4.24 without, 4.03 the published way)"

Negative results get the same prominence as wins (`71e2d53`: "The sleep experiment as measured
(**not built in**)"). Numbers ride in the subject line, so `git log` alone reconstructs the
project's measured history. Style detail: subjects never name the model that wrote them
(Arnav's rule: no model identifiers in commits), and they are written in plain declarative
sentences — findings first, mechanism second.

### 1.3 Held-out sets are sacred, single-use, and run on frozen code

The bench protocol, repeated identically for three held-out sets: tasks written *before* the
fixes they test, contamination-checked before they run, executed **once** against a frozen
copy of the code (snapshot folder + symlinked weights, so an edit cannot reach a run in
progress), and reported as measured forever after — even when a later fix makes the number
look stale. Dev 15/16 vs held-out 9/16 → 11/16 → 13/16 is kept side by side in the README
with the explicit gloss: *"The gap is the measurement."* When set 2 was re-run after fixes,
it is labelled "13/16 (**not clean**)" (`03a8988`). When two bench *checks* themselves were
wrong (a check wanted `apache-2.0` for a correct "Apache License 2.0"), the check was
corrected and the correction is documented — but the original score stays in the record.

Contamination is treated as an engineering problem, not a virtue signal:
`training/contamination_check.py` scans all training data, cell generators and prompts
against bench specifics; leaks were *found in its own work and removed* — a calculator
prompt example that was a dev task, cell generators naming bench model ids/units/versions
(the cells were retrained: `d20193b`, `c6e6b28`, `b63f20d`). Older member training data that
still names dev-task entities gets the dev passes explicitly marked "not evidence of
generalisation" rather than quietly enjoyed.

### 1.4 Every failure is read for its cause, and the fix is general or it is not a fix

The held-out failure notes (`training/reports/hive_bench/heldout*_notes.md`, summarised in
SPEC round 4) are the clearest window into the working method. Each failure gets a cause at
the level of *mechanism*, and the fix lands in code as a general check, never as a patch for
the task: a chart drawn with `plt.show()` and never saved passed the jury → *a drawn chart
with no image file is sent back and never passes*, plus a non-window plotting backend for all
programs. A value never found was covered with "Unknown" in every row and three jurors
passed it → *a placeholder column is a broken file*, in code. His own text handed back
instead of translated → a report that repeats his text is marked not-done in code. A weekday
printed as `6` → the calculator checks the *form asked for*, in code. The pattern: **model
judgment is the last resort; anything that can be a deterministic check becomes one.**

### 1.5 Small evals, stated as small

Every improvement section opens with the caveat: *"Evals are small (3–18 cases), so treat
single-case differences as noise."* Where dev and test disagree, it is reported, not repaired
by peeking (the `next_move` cell: dev picked MLP-only rank-2, 0.880 on test, while the `thin`
variant scored 0.973 — both numbers printed). Where a margin is inside noise, the text says
so ("+1.8 chrF over the writer, *not clear*"; the 4B's +3.2 given with its CI, +0.7 to +5.6).
This is the discipline that makes the big claims believable: the same voice that reports
2.4760 also reports that the number is inflated by ~0.03–0.04 for two of the three bodies
(§2.2) — and *sizes the inflation on fresh text* instead of just confessing it.

### 1.6 Design for the session's death; design for nobody watching

The machine this work ran on is reclaimed when idle, background jobs are cut at two hours,
and the cloud account itself was being vacated mid-project. The engineering answers are
everywhere: school visits are resumable (`<role>_visit.json`); every file that matters is
written whole-or-not-at-all (`scratch.whole`), so a cut-off run leaves no half cell; bodies
*regenerate* lost parts before doing anything else in a turn (`heal`, `c86e93f` — verified by
this lab: the real 14.5M-piece text stream was rebuilt byte-identical in 12 s); `HANDOFF.md`
opens with a kept-current "Live status" block so a *new session on a new account* can resume
cold, and ends with a START HERE block written for exactly the account move that then
happened (`3ca4b83`, `d31fd51`). The end state of that habit is §2.7: the system no longer
needs a session at all — it grows on GitHub's runners and sits its own daily exam.

### 1.7 Rehearse the unattended path in the environment it will actually meet

Before the GitHub growth run ever executed, it was rehearsed in a *fresh clone with only the
packages the workflow installs*. Two faults that would have ruined the hive were caught only
that way: a non-first body re-learned the vocabulary every turn (harmless while the text was
static, ruinous once the harvest grew — every cell would have read noise), and a text stream
that did not match its book was trusted. Both are fixed in code (`scratch.tokenizer` never
re-learns once a stem cell exists; the stream is checked against its book). The same instinct
produced the fetch-guard: the runner run *aborts saving nothing* if the hive cannot be
fetched (`1a8426f`) — an unattended system must fail toward doing nothing, not toward
starting over.

### 1.8 Cost honesty: speed and memory are reported as results, not footnotes

Every parallelism or size idea is measured *with its price attached* and then usually left
**off**: two jobs at once = 4% faster for +2.2 GB (off); the cell pool = 1.2× for +1 GB
(off — its first measurement was a 75× *slowdown*, 728 s vs 9.8 s, because llama.cpp reads
prompts on every core unless told otherwise; fixed, re-measured, still off); two ternary
layers per cell help per step and are "not built in" because they double the disk. The
default is whatever won the measurement, and the losing configuration stays documented with
its numbers. Section 3 is this habit applied to the kernel level.

**What the style adds up to:** Fable behaves like an experimental scientist who happens to
write code — hypothesis, controlled variation, fresh measurement, keep/discard, write the
finding down where the next worker (possibly itself, possibly a stranger) will trip over it.
The artifacts (SPEC checklist with Done/Partial/Not done per requirement, per-failure cause
notes, `.rejected/` adapter graveyard kept "for the record") are built so that *its own
future claims can be audited*. This lab's validation could verify its numbers precisely
because it kept them that way.

---

## 2. The architecture ideas, deeply

Two hives share the repo. The **working hive** (pretrained small models + tools + checks)
does tasks today: dev 15/16, held-out 13/16 (set 3, `0147aa4`). The **growing hive**
(from-nothing BitNet bodies) does no tasks; it reads simple text and improves unattended.
The ideas below are ordered from the working hive's micro-level to the growing hive's
system level; each gets problem → mechanism → evidence, including where the evidence is
negative.

### 2.1 Cells: one tiny weight delta per smallest decision, on one shared frozen base

**Problem.** The big members (1.7B–7B) spend 1–11 s per call, and most calls in a run are
tiny fixed-shape judgments (is this action ordered? which specialist takes this step? does
this quote support this claim?). Using a 4B for those is slow and, measured, often *worse*
than a specialist.

**Mechanism.** All cells share one frozen SmolLM2-135M (144 MB at 8-bit) resident in RAM.
A cell is only a LoRA-style weight delta (0.38–0.85M edited parameters, a few MB), hot-swapped
per call in llama.cpp; label cells answer through a grammar restricted to their labels, so
the output is a valid label by construction. A cell **takes a job only where it measured at
least as well as the incumbent** on the same test inputs (`cells/wins.json`); hooks in the
engine/coordinator/researcher/verifier/guard/loop call the cell only at the point it won.

**Evidence.** 25 cells, 12.4M edited parameters total, 50 MB of deltas on the 144 MB base.
Examples (test split, unseen words/frames/sites): `route_step` 0.19 → **0.99** at 87 ms vs the
4B coordinator's 0.9746 at 7,095 ms; `split_orders` 0.01 → **0.91** vs 0.28; `pick_source`
0.93 vs 0.70. 14 cells hold jobs, 2 measured losers keep the member (`claim_support` cell
0.827 vs verifier 0.880; `licence_open` 0.741 vs juror 0.933 — the 135M lacks the world
knowledge, stated plainly). Two structural refinements matter: an **organizer** pattern (a
too-big skill is split again — `element_match` asked per element scores 1.000 on the test
pages vs 0.927 for the single `pick_element` cell reading the whole list), and a **gate**
cell (MoE router over cell groups, 0.940 on test) that exists but is honestly marked *not in
the loop yet* because the hive calls cells at fixed hooks (SPEC: Partial).

### 2.2 Bodies and stems: from-nothing specialists with a shared inner language

**Problem.** Arnav's direction (2026-11-10): thousands of cells, each the smallest model
that can be made, none doing the same job, specialties overlapping, no cell important alone,
more cells grown with more data, nobody watching.

**Mechanism** (`training/scratch.py`, `training/body.py`). The hive harvests its own text
(own logged work + licence-checked open datasets + a Wikipedia trickle; scouts admit new
sources only if a sample reads like running prose — `1bf3389`). A 4,096-piece vocabulary is
learned from the harvest; a **stem cell** (~2.6M weights) trains from random numbers as a
next-piece predictor. A **body** is grown from the stem: every text window is embedded by
the stem and assigned to its **two nearest territories** (overlap by construction); one cell
grows per territory, early-stopped on held-out windows of its territory so it cannot just
memorise; the stem stays a member of the body. Reading is sparse — the stem plus the two (now
four) nearest cells wake, the rest sleep on disk — so a turn costs the same at ten cells and
at ten thousand. Growth goes where the body fails: first tried as "grow on the worst-read
windows" (failed — those windows are mostly lists and noise; both such cells were removed at
birth), then as **cell division**: split the worst-read territory, grow a daughter on the
worse half. A newborn is judged *locally*, on unseen passages near its territory, body-with
vs body-without (`judge_local`); a cell that does not help is removed at birth (the "immune
check"). Bodies in turn are **founded on what the existing bodies read worst** — half of a
founding body's reading diet is the worse-read half of a window sample — and founding cadence
is self-throttling (`body_is_due`: one more body when bodies average eight cells, then two
more per existing body, "for ever, each a little later", `dfd4767`).

**Evidence.** First body: a failure, recorded as one — cells trained ten minutes unstopped
hit loss 0.29 on their own windows vs 5.33 on new text, body 2.498 **worse** than its stem
2.428; one cell retired by the immune check, a birth refused. Second body (early stopping +
stem as member): **2.294 vs stem 2.428** on 300 unseen passages, every cell alone worse
(2.60–3.08) than the stem, waking two cells ≈ waking all (2.295) — the composition, not any
cell, is the win. BitNet body: 2.574 vs its stem 2.748, grown by two kept divisions
(+0.0074, +0.0016 kept gains). Three bodies as one: **2.4760** (yardstick; §2.7), the first
time the ensemble beat its best member (2.4856) under the learned say. **The flaw, found and
sized by Fable itself:** the first two stem cells trained on text that included the held
passages (cells never did, so *relative* gains are fair, but absolute stem numbers are
flattered); measured on later-harvested text, the flattery is ≈0.042 and ≈0.031 of loss.
From `scratch.offsets` onward no stem cell reads a held window; body 3 is the first with
clean numbers (stem 3.1146 → body 2.7806 at six cells). This lab's validation confirmed the
figures exist in the committed records (`hive_of_bodies.json`, final entry 2026-11-11) and
that the no-overwrite guard is real code.

### 2.3 The seed: living state as one portable, guarded file

**Problem.** A hive that grows on rented/ephemeral machines must be able to move, resume,
and — critically — never be accidentally replaced by a smaller or foreign self.

**Mechanism** (`training/hive_state.py`, `6ae9f83`, `5e4bcc0`, `88f6a27`). The whole living
state packs into one file (`pull`/`pack`/`save`). Three guards do the real work: (1) a save
is written **after every body's turn**, each under a new name on the release `hive-state`,
which keeps its two newest states — a cut-off run loses at most one body's turn, a cut-off
save loses nothing; (2) a hive is **never saved over one it did not come from, or one smaller
than it came from** — `pull` refuses to overwrite a hive with as many living cells or more
(verified in code by this lab); (3) unknown members in a state file are refused on unpack.
Install (`setup.sh`) pulls the grown hive once, so a fresh device starts from the grown
state, not from zero.

**Evidence.** The `hive-seed` branch (`be80d6e`, 2026-11-11) holds three bodies / 22 cells as
one 2.4760 as the bootstrap state. The rehearsal in a fresh clone (fetch, harvest, founding,
turns, measure, pack) passed; the first real unattended run was **not confirmed** at the
time of writing (HANDOFF says so; this lab's addendum agrees — no Actions data is readable
from here).

### 2.4 Founding and birth gates: nothing enters the population without beating the status quo, where it will live

**Problem.** Unattended growth degenerates in two classic ways: newborns that memorise, and
global metrics that hide local damage.

**Mechanism.** Four nested gates, each at the level it protects: (i) a **cell** is kept only
if the body predicts better with it on a *gate set* of never-trained passages (a separate
*report* set is only ever reported, never gated on — the gate/report split keeps the judging
set from becoming a training target); (ii) a newborn is judged **locally** (`judge_local`:
unseen passages nearest its territory), so a cell cannot be carried by distant improvements,
and a birth is refused if any known territory gets worse (the immune check, `e5ff3eb`);
(iii) a **body** is founded only when due (`body_is_due`) and is kept whatever its recipe
experiment shows — the *recipe*, not the body, is what gets selected (§2.8); (iv) in the
working hive, the same shape repeats: cells take jobs at ≥ incumbent, school students
graduate at 85% + 3, spawned cells switch on per-label only under §2.6's evidence rule.

**Evidence.** Births refused and cells removed are in the record with numbers (first body's
retired cell; both worst-window cells removed at birth; two of six newborns in the first full
unattended turn removed by the immune check while four were kept, bodies 2.5715 → 2.4856 and
2.8973 → 2.8412). The gate's strictness is the reason the growth curve is believable at all.

### 2.5 The learned say: combination weights are learned, per seat, and re-learned

**Problem.** Reading a passage "by whichever member fits best" (near winner-take-all) wastes
the ensemble: different members are right on different text, and a fixed mixer can't know the
proportions.

**Mechanism** (`body.learn_say`, `body._say`, `bea40f6`, `06b536a`, `7a11fcc`). Every awake
member gets a *share* of the say. Two things are learned on passages nobody trained on: how
sharply the say follows fit, and a **standing per seat** (stem, nearest cell, next nearest…;
between bodies, one standing per body). The say is *re-made at every measurement and every
turn* and is deliberately **not kept in git** — it is a function of the current population,
not an artifact.

**Evidence.** First full unattended turn under the learned say: bodies as one **2.4807** —
the first time the ensemble beat the better body alone; under the old winner-take-all rule
the same population scored 2.5754 as one vs 2.5715 for the best body (i.e. combining *hurt*).
Per-body: body 1 improved to 2.4856 with ten cells (stem alone 2.6446; same cells under the
old rule 2.5582).

### 2.6 The spawn trainer: the hive notices its own micro-jobs and staffs them

**Problem.** Every cell in §2.1 existed because somebody named the job first. The interesting
jobs are the ones nobody named — small fixed-answer decisions buried in the members' own
traffic.

**Mechanism** (`team/life.py`, `team/cells/spawn.py`, `2f5c90f`, `28cca6e`). The loop:
**Notice** — scan logged calls per call site (one member + one instruction); if ≥97% of
replies are a few fixed values (`COVER = 0.97`), it is a candidate job; text beside a label is
allowed only as explanation — a label that needs member-written text is never delegated.
**Practice** — the member re-decides recombined older cases (near misses, mismatches).
**Compete** — candidate edits of the 135M base; the **size ladder** applies: 360M only if
the 135M cannot hold the job, and *no bigger base when the evidence, not the cell, is what
is missing* (`47960f0`). **Gate** — judged only on real decisions *newer* than anything it
trained on, **per label**: a label switches on only if the newest decisions contain ≥3 cases
where the member chose a different label, the cell is wrong at most half as often as blind
answering would be, then ≥95% agreement on what it answers, ≥⅕ of calls answered, ≥10
answered. Too little evidence is reported as too little evidence — not as cell failure.
**Work** — the cell answers only when sure; the member answers the rest and those answers
keep being logged (the training stream never dries up). **Audit** — 1 sure call in 10 is
also sent to the member; live agreement under 93% (`RETIRE = 0.93`) retires the cell,
automatically.

**Evidence.** From 5 whole tasks + 35 live research questions, the hive noticed 2 decision
sites among 15. One had enough decisions: the verifier's fact check, 162 distinct real
decisions. The spawned cell (`sp_verifier_75e567`, 135M + rank-2) answered 13 of the newest
25 (52%), agreed 13/13 on what it answered (92% over all 25), at 81 ms vs the member's 4.7 s.
It answers only SUPPORTED; UNSUPPORTED stays with the verifier because dev never vouched for
that label — per-label honesty. Live audit on 12 further questions: sure on 20, agreed 19
(95%); the one miss is recorded in the README with its exact shape (claim "−196 °C" vs quote
"−195.8 °C" — a near-miss number, "the kind that matters most"), and its confidences were
*left as the gate set them, not tuned on these calls*. First round (72 decisions) the cell
stayed off for lack of evidence — the gate refusing to fire is itself reported as a result.
Honest limit, also from the README: the small checks are ~5% of the hive's time; the 4B
reading sources dominates — which is why §2.9 exists.

### 2.7 Unattended growth turns + the fixed yardstick + the daily fresh exam

**Problem.** A system that improves only while its author watches isn't autonomous; and a
system that grades itself on a moving target can't prove it's improving.

**Mechanism.** Three workflows, one philosophy:
- `.github/workflows/hive.yml` (cron `17 */6 * * *`, on `main` since PR #11): fetch state
  (abort, saving nothing, if unfetchable — `1a8426f`), harvest a little (+2 MB/source), every
  body takes its turn **longest-waiting first** within a 180-minute budget (`body --budget
  180`), found a body if due, measure, save after every turn, append one line to
  `training/reports/hive_growth.jsonl` — and that commit-per-turn is also what keeps GitHub
  from auto-disabling the schedule after 60 days without a commit.
- **The yardstick** (`body.YARD`): the same 300 held passages from the text as of
  2026-11-11, every time. The all-its-text number moves whenever the harvest grows (stories
  read ~2.2, Wikipedia 3.2–4.0), so only the yardstick says whether the hive got better.
  Two-number reporting — moving corpus for texture, fixed yardstick for truth.
- `.github/workflows/exam.yml` (daily, `training/exam.py`): the *working* hive sits a fresh
  exam that **code makes and code checks** — 16 generated tasks across maths, dates, units,
  tables, programs, live facts, websites, instruction-following, knowledge, languages,
  writing, understanding; one line per sitting in `training/reports/exams.jsonl`. Security
  shape worth copying: the job that runs the hive holds a **read-only** token; a second job
  (`exam_record.py`) that runs no model and none of the hive's code takes only numbers and
  known names from it and writes the record.
- `.github/workflows/ask.yml`: the working hive as a stateless appliance — type a task in
  the Actions tab, get the answer as the run summary and every file as an artifact; no write
  token, no logins, nothing spent.

**Evidence.** Verified in code by this lab's addendum (workflows present as described;
fetch-guard commit in tree; 199 tests pass). **Not confirmed:** the first scheduled growth
run and release upload had not been observed when either Fable or this lab last looked —
the design is rehearsed, the unattended execution is (yet) unproven. The exam rehearsal
(six tasks, seed 315) was cut mid-run at the account pause; result unknown, stated as
unknown.

### 2.8 The hive finds its own recipe: every founding is a one-gene experiment

**Problem.** Training recipes for from-nothing BitNets were being tuned by hand (rate,
easing, norms, teacher…). Hand tuning doesn't scale to an unattended system, and sequential
hand experiments confound each other.

**Mechanism** (`body.next_recipe`, `body.GENES`/`SHAPES`, `cells/scratch/recipes.json`,
`dfd4767`). `NEW_BODY = {shape:{}, lr 3e-3, warm 200, ease 0.5, taught 0.0, batch 32}` is the
champion recipe. Each founding mutates **exactly one gene** of the champion (multiplicative
rate jitter ×0.6/×1.6, easing, warm-up, batch, width/depth via `SHAPES`). The body is kept
whatever happens — population growth is not hostage to the experiment — but the mutated
recipe becomes the new champion **only if its stem cell reads better than every stem cell
before it**, on the same held windows. A hand-set recipe is tried once as it stands, then
enters the same competition.

**Evidence.** The champion it started from was itself won this way by hand (§3.3): 3× rate +
rounding eased in → 2.9288 vs 3.0337 at 40 minutes, re-verified at full length on 400 held
windows. The mechanism generalises that one experiment into the standing founding protocol.

### 2.9 The school: distillation with an exam, gap-only specialists, and routing by resemblance

**Problem.** Big members are slow; small members can't do their jobs. Retraining one small
model on everything a big one does just moves the ceiling.

**Mechanism** (`team/school.py`, `cde4f4b` onwards). The teacher (4B/7B) generates lessons —
fresh tasks it performs itself; a lesson is task + teacher's answer + *what the answer
decides* (for a plan: the specialist sequence; for a program: what it prints). The student
(1.7B/1.5B) gets a LoRA edit on the lessons (128 lessons ≈ 25 CPU-minutes). **Exam on lessons
never trained on.** Graduation: 85% agreement with the teacher **and** +3 over the untouched
student. Failed gaps spawn **narrow specialists trained on the gap alone**, which sit *beside*
the generalists — nobody is replaced or retrained; a task routes to the specialist whose
known lessons it most resembles; generalists can vote. In the small-only hive (no teacher
present at serve time), a taught specialist that is merely *ahead* of the untouched student
holds the job (`school.holds`) — a deliberately weaker gate for a deliberately weaker
deployment, labelled as such.

**Evidence.** Planner (4B → 1.7B), two visits, 232 lessons: unseen-lesson agreement 30% →
**59%** (24/24 on one/two-specialist plans, **3/22** on plans of 3+); independent 14-case
suite 0.449 → 0.663 (4B: 0.872). **Not graduated** — and the record says why the target itself
is suspect: the 4B's long plans are padded and inconsistent, so agreement understates the
student there. The first narrow specialist *did not help* (9/26 in its territory, the
generalist the same 9) — reported, with the diagnosis that cleaner lessons (plans *after*
review, or from passed runs) are the fix, not more specialists. Coder (7B → 1.5B), 160
lessons: prints-what-teacher-prints on 32 unseen lessons 59% → **81%**, then 84% after two
*exam-key* corrections (long decimals compared to 10 significant digits; an unused import no
longer disqualifies) — the key corrections are documented and the exam "stays as scored."
84% is one lesson short of graduating; it holds the job in the small-only hive under the
weaker rule. Second lesson-kind (fixing a program from the hive's own feedback,
`school.teach_fixes`) is built, no class held yet — stated as such.

### 2.10 Sleep: the experiment that measured a negative and was not built in

**Problem.** Does a body teach its stem cell (distil the ensemble back into the stem), and
how should a still-learning stem divide its turn between reading and births?

**Mechanism/result** (`training/reports/sleep.json`, `71e2d53`, `3ca4b83`). Six ways for the
third body's stem to keep learning for 8 minutes: plain continued reading at 3e-4 won
(3.380 → 3.190 on held windows; 1e-3: 3.227; 3e-3: 3.292). Body-teaching learned more *per
step* but not *per minute* (3.198). And the kicker: a stem improved by 0.19 moved its body by
only 0.004 — cells are made from the stem *as it was*, so stem learning pays off only in
cells born after it. The design consequence was built instead of the dream-distillation:
a fast-learning stem reads for as long as a birth takes (`body.stem_minutes`), a third of
that once it has slowed. Filed under the study's honesty rule: **the sleep/dream idea, as
distillation-into-the-stem, is a measured negative on Fable's side** — dreams there earn
their keep elsewhere (harvest dreaming, §3.4; the working hive's `dream` replay→lessons→
distil→gated-retrain loop exists but, per SPEC, was *not run as a full cycle* in-session).

### 2.11 Chunked reading and cross-family agreement: two composition results worth stealing carefully

- **Chunked reading** (`training/chunk_read.py`): the 1.7B reads sources in 1,800-char
  chunks, one job per chunk; a cell merges/checks. On the same 26 logged real inputs through
  the hive's own checks: the chunked 1.7B found **more** checkable facts than the 4B reading
  whole (62 vs 38 after the instruction fix below), in ~55% of the model-seconds — but the
  two *miss different things* (neither contains the other; the 1.7B is good on long pages,
  bad on short results/lists). The decisive detail: the first run measured the *instruction*,
  not the model — the reader's example value ("X has 0.135B parameters") was being returned
  as a fact; removing example values from small-model instructions moved facts-found 52 → 62
  and full-coverage inputs 7 → 14. Not yet built (either side of the Atlantic): small reader
  first, 4B only where it comes back empty.
- **Cross-family agreement as a free verifier** (`training/diverse.py`): recruits from other
  families share fewer mistakes (joint-error overlap near chance vs ~2× chance for
  same-model pairs) but are individually weaker, so *voting gained nothing* (27/32 = best
  alone). But whenever two different families printed the same program output, it was right —
  **58/58 across five pairs** (this lab's validation confirms the record). Agreement =
  trust without a jury; disagreement = where to spend effort. Explicitly "not built into the
  run loop yet" on Fable's side either.
- **Recruits** (`team/recruit.py`): the hive finds/licence-checks/downloads/tries other
  small models itself (≤2.0B, ungated, permissive licence, own-maker or known converter,
  never a safety-stripped variant). First two recruits (Yi-Coder-1.5B, SmolLM2-1.7B) both
  **failed enrolment** — weaker than the untouched students on both exams — and that negative
  is the headline of the section, not a footnote.

---

---

## 3. Kernel / compute-optimization work specifically

This is the layer Arnav singled out ("Fable improved … kernel and compute optimization a
lot"). The record supports him — with the honest caveat that the wins are all *measured
systems decisions on CPU inference and ternary training*, not GPU kernel work (there is no
GPU anywhere in this project; llama.cpp CPU is the whole engine story).

### 3.1 The engine: llama.cpp discipline on a 4-core CPU

- **Repacked weight copies off** (`dad84d0`, `b8a99d8`): llama.cpp by default keeps a
  repacked second copy of the weights; disabling it took the 4B from 6.1 GB → 3.6 GB
  resident (team peak 12.9 GB → 7.8 GB) *at the same speed and the same answers* — verified
  by re-running decisions, not assumed.
- **16-bit attention (KV) cache on** (`372edf4`, `48ef89f`): 1.6× faster at 8.2 GB peak, same
  decisions, measured on the hive's real prompts via `training/arch_bench.py`. (8-bit KV was
  the earlier setting; the bench, not the intuition, picked 16-bit.)
- **Prompt-lookup decoding: off** — it *crashed* in llama-cpp-python 0.3.36; a crashed
  optimization is not an optimization, and it stays off with the reason recorded.
- **Shared base + hot-swapped deltas + LRU residency**: three 1.7B specialists share one
  copy of the base weights, edits (9–17 MB) swapped per call; at most 2 models resident,
  least-recently-used unloaded (reload ≈ 4 s). Measured operating point: whole team ≈ 10 GB
  peak with browser; 4B at 7.6 tok/s / 3.9 GB; shared 1.7B + three edits 3.3 GB; coder 7B
  4.8 tok/s.
- **Grammar-constrained JSON**: replies are valid JSON by construction (llama.cpp grammars),
  deleting a whole failure class instead of parsing-and-praying; PyTorch engine kept as the
  training/scoring path (`AGENT_TEAM_ENGINE=hf`).
- **Prompt-window fitting in the engine**: a long page crashed a model call (prompt over
  window) → the engine now fits every prompt to the model's window (middle of the longest
  message cut). A kernel-adjacent robustness fix at the harness/kernel boundary.

### 3.2 The parallelism lessons (both learned by failing first)

- **Cell pool** (`7cf29e9` → `2a2297a` → `d45bc04`): first measurement catastrophic —
  160 questions: 9.8 s serial vs **728 s** with 2 workers, because llama-cpp-python reads
  prompts on *every core* unless thread counts are pinned, so workers fought over the same
  cores; orphaned workers of killed runs also kept computing (now they exit with their
  parent). After the thread fix: 7.9 s (2 workers, +1.0 GB), 7.7 s (4 workers, +2.8 GB) vs
  9.5 s serial. Verdict kept in code: **off by default** (`AGENT_TEAM_CELL_WORKERS=1`) — a
  1.2× for +1 GB fails the project's own cost rule, with the exact conditions under which to
  enable it written down. This is the same lesson this lab runs by (pin OMP/MKL=2, one heavy
  job at a time), learned independently on both sides.
- **Two jobs at once** (`01bf2ff`): shared models, one CPU lock — 196 s vs 205 s serial
  (4% faster) for +2.2 GB peak. Off by default. On a CPU the models already use every core;
  jobs mostly take turns. Measured, documented, declined — the hat trick of §1.8.

### 3.3 BitNet: the ternary mechanism, two training algorithms, and a recipe won by experiment

- **The mechanism** (`c580c4c`, `scratch.BitLinear`): every weight in a cell is −1, 0 or +1
  times one per-layer scale; cells share the stem's piece table and pack at **2 bits per
  weight → 0.61 MB per cell** vs 10.5 MB full precision. That 17× storage cut is what makes
  "thousands of cells, only the disk grows" an arithmetic fact instead of a hope. Converting
  the fp stem cost accuracy, measured: loss 2.70 → 3.02 after 30 minutes of ternary reading
  — the price is in the record next to the benefit.
- **Published-way training** (latent fp weights underneath, rounded each step) is the
  production path. **Direct training** — no fp weights at all — was invented for this hive
  and iterated in public: v1, move-with-probability ∝ gradient (`add5984`): *taught nothing*
  on real text (4.25 with jumps, 4.24 without). v2, **per-weight vote counters** (`6249578`,
  `9711292`): a small counter per weight accumulates gradient evidence; at 32 votes-to-jump,
  loss **4.141** vs 4.241 no-jumps and **4.031** published-way — about half the published
  gain with a few bits per weight instead of a full fp shadow. Four follow-up variants
  (votes-must-repeat, leaky counters, stricter threshold) scored 4.28–4.38, none better —
  reported as not better, with the confound noted (shared CPU, fewer steps, "not a clean
  comparison"). For *growing* a cell from the stem there is a third method, `_flip_read`:
  move the highest-value share of ternary weights at once, measure on unseen text, keep or
  undo — a discrete, auditable edit operator. This lab's validation: "BitNet cell mechanism
  faithful b1.58; direct trainer works, ~half the published gain."
- **The recipe search** (`training/reports/bitnet_recipe.json`, `69723bf`, `55ca2b0`,
  `4049ba4`): same stem, same start, same batches, 600 steps, held passages — as-was 4.2315;
  **3× learning rate 4.0220** (10×: 4.0501); 3× + rounding-to-ternary eased in over the first
  half **3.9963**. The published recipe's extra pre-output norms *hurt at every rate*
  (4.43–4.54) → off. A teacher (body 1's stem) helps per step (3.8081) but costs 1.7× time;
  the same wall-time spent on more steps wins (3.6988) → teacher off **by default at equal
  time** — the comparison is always at equal budget, which is the only honest way to compare
  training methods on a fixed machine. Also measured and not built in: two summed ternary
  layers (3.9474, 2× disk; no gain with easing), width 256 (3.9547 at 1.5× time). Newborn
  cells keep the *old* rate (5e-4: +0.0177 locally; 3e-3: +0.0092) — the recipe is
  age-dependent, and that too is a measurement, not a vibe. At full length the champion held:
  **2.9288 vs 3.0337** over 40 minutes (400 held windows, later re-verified by this lab at
  `d31fd51`). Full precision at the same rate/steps: 3.8966 — a BitNet this size is ~0.10
  behind step-for-step, stated in the same paragraph as the win.
- **Architecture edit by knockout** (`training/cells_cut.py`): the locator's knockout maps
  indicted 8 layers as near-dead across all probed skills; removing them gave a 22-layer,
  106M base, 1.70× faster per call — and cells retrained on it dropped 0.936 → 0.789 average
  test. **Rejected.** Speed that costs the capability it was speeding up is not kept, and the
  failed measurement (including a SIGILL that killed two skills' timing runs, cause not
  found — stated) stays in the README.

### 3.4 Time, heat, and machine discipline as first-class mechanisms

- **Health gates** (`team/health.py`): heavy background work (dreaming, growing, school,
  recruiting) runs only when plugged in, CPU < 75 °C, ≥3 GB RAM and ≥2 GB disk spare;
  between model calls a CPU above 90 °C waits until under 80 °C; <1 GB disk free refuses new
  jobs *with the reason*; models unload after 10 idle minutes; nice 10 + idle IO; systemd
  caps at half the CPU and 10 GB. One instance only; never keeps the device awake.
- **Time-budgeted turns**: the runner turn takes `--budget 180` and bodies run
  longest-waiting-first inside it; newborn cells get a fixed 10 minutes; school lessons are
  sized to the 2-hour background-job cut and resume. Every long process in the repo is
  written assuming it will be killed mid-flight (§1.6).
- **Harvest dreaming** (`cd1f735`, `harvest.dream`): dreams as a *data* mechanism — the small
  member writes practice passages on what the body reads worst, difficulty rising every 40,
  folded into every harvest. Tested with the member mocked; **not run with a real model
  yet** — recorded as such in both README and HANDOFF.

### 3.5 What section 3 adds up to

Fable's compute work is not "optimisation" in the benchmarketing sense; it is a chain of
small, individually measured systems decisions, each with its price printed next to it, and
a willingness to leave the clever thing **off** when the measurement says so. The two real
inventions — vote-counter direct ternary training and the flip-and-measure cell grower —
exist because the substrate (2-bit cells by the thousand, CPU only) demanded them, and both
were validated *against the published method at equal budget* before being believed.

---

## 4. Translation table — Fable idea → Muse's factory: has it / weaker version / lacks it

Muse's substrate, for honest comparison: `factory/` serves Tier-0 TinyNet specialists
(hidden ≤ 8 MLPs, trained whole) plus the bug-pattern composition through a **battery-gated,
fail-closed** `ServingHive` (hash-checked registry; an artifact serves only if its measured
battery slice ≥ incumbent, else SHADOW). Growth is by **dual-gate births** (child must beat
parent strictly on *both* pristine held slices; battery + full audit verify adoption;
rollback on regression). A dream engine (`dream.py`, `dream_gen.py`), a ternary runtime
(`tern_runtime.py`, corrected b1.58 forward), lineage, a scheduler/daemon, and a thermal
governor exist. Cycles 1–3 are complete (2 births); cycle 4 is the first under today's
methods arms.

| # | Fable idea | Muse's factory today | Gap → concrete improvement (size · gate) |
|---|---|---|---|
| 1 | One rule everywhere: vary → measure fresh → keep only if better | **Has it** — dual-gate births + battery-gated serving are the same rule, stricter (two pristine slices, audit, rollback) | None. Keep. |
| 2 | Fixed yardstick vs moving-corpus two-number reporting | **Weaker** — battery slices are fixed, but growth reports lean on the same held slices the gate uses; no permanently-frozen, never-gated-on yardstick set exists | Add a sealed YARD set (report-only, never a gate, never trained on) so cycle-over-cycle drift is readable (S · report-only, no serving change) |
| 3 | Gate/report split (gate set decides, report set only reports) | **Weaker** — two held slices both act as gates; nothing is report-only | Same fix as #2; the split is what keeps a judging set from becoming a target |
| 4 | Contamination check before any held-out run | **Has it** — contamination filter in the dream/growth pipeline; held slices contamination-filtered at construction (cycle-3 surfaces) | Extend the check to *every* new surface at registration time, logged (S · process gate) |
| 5 | Local judging of newborns (judge where it will live) + territory-regression refusal | **Lacks it** — births are judged on whole slices; a child can win globally while damaging a sub-region | Add per-slice-family breakdown to the birth gate: no family may regress beyond noise (M · dual gate gains a no-local-regression clause) |
| 6 | The learned say (learned per-seat mixture weights, re-fit each measurement, never versioned) | **Lacks it** — the bug-pattern composition serves through the waking-dream layer with fixed composition behaviour; cycle-1 "learned say" was measured (0.7931 learned vs 0.8276 routed) and not adopted as a *static* fit | Re-fit per-seat standings at every battery run over the composer's members (M · battery slice for bug-pattern must not regress; adoption only via battery gate) — see Build 2 |
| 7 | Spawn mining: notice fixed-answer decision sites in own logged calls | **Lacks it** — intake scan finds *missing slices* in labelled data, not decision sites in serving traffic | Log serve() calls with inputs/outputs; mine for fixed-value sites; propose new niches from traffic (M · new niches enter only through the normal birth gate) — see Build 3 |
| 8 | Live audit + automatic retirement (1-in-10 audited, <93% retires) | **Lacks it** — serving is static between cycles; a served artifact that degrades in the wild is caught only by the next cycle's battery | Serve-time spot-audit of Tier-0 answers against the shadow/fallback artifact; auto-demote to SHADOW under threshold (M · audit is code+log first; demotion only after the audit itself is validated offline) |
| 9 | Per-label switch-on (a label serves only if the evidence vouches for that label) | **Lacks it** — adoption is per-artifact, all-or-nothing per slice | Per-class adoption mask inside a born child: classes that didn't beat parent fall back to parent per class (S–M · dual gate applied per class) |
| 10 | School: teacher-generated lessons, exam on unseen lessons, gap-only narrow specialists beside generalists | **Weaker** — dream-first repair trains on the parent's *measured failures* (gap-focused) but there is no teacher generating fresh lessons, no exam distinct from the gate, no routing-by-resemblance among sibling specialists | Add a sibling-specialist registry per niche (parent + born children coexist; route by nearest known case) (M · routing must beat the single-server on the battery slice before it serves) |
| 11 | Recipe-as-genes: every founding mutates one gene of the champion; champion changes only on a held-set win | **Weaker** — today's head-to-head picks a recipe per target per cycle; no persistent champion recipe carried across cycles, no one-gene mutation discipline | Persist a champion training recipe in the registry; each cycle mutates one knob; champion replaced only on held-slice evidence (S · the dual gate already judges outcomes; champion record is bookkeeping) — see Build 1 |
| 12 | Founding on what the others read worst (weakness-directed growth targets) | **Has it, partially** — cycle targets are registered from intake/failure scans (weakness-directed), but not from *serving* failures | Feed serve-time failures (from #7's log) into target registration (S · targets only; gate unchanged) |
| 13 | Self-throttling population growth (`body_is_due`) | **Weaker** — cycles run on a fixed ~6 h cron regardless of marginal gains | Make cycle cadence adaptive: lengthen when the last cycles produced no births, shorten after births (S · scheduler policy only) |
| 14 | Regeneration + whole-or-not-at-all writes + heal-before-work | **Has it, mostly** — state.py atomic save (tmp+fsync+replace), registry hash audit fail-closed at load, rollback on regression | Add a pre-cycle integrity pass that *rebuilds* a corrupted artifact from its lineage record instead of only refusing (M · rebuilt artifact must re-pass its adoption battery before serving) |
| 15 | Portable guarded state (never overwrite a state as large as the one you hold) | **Weaker** — registry is local; no pack/pull of the whole factory state with a no-downgrade guard | Pack factory state (registry + artifacts + lineage) as one file with the ≥-living-cells-style guard (M · guard verified by tests, as theirs was) |
| 16 | Unattended turns on foreign runners with fail-toward-nothing fetch guard | **Lacks it** — growth runs on this VM's cron only | Runner-based cycle: fetch state or abort, run one cycle, save per stage (L · only after #15; abort-on-fetch-failure is the load-bearing piece) |
| 17 | Daily code-generated fresh exam for the *working* system, field-by-field line | **Lacks it** — the battery is fixed; it can be (and is) slowly adapted to | A generated-exam harness over the six served niches (fresh cases by code, checked by code) run daily, report-only (M · report-only; never a gate, to keep it honest) |
| 18 | Read-only runner + separate recorder job (privilege split for unattended measurement) | **Lacks it** (single VM, single trust domain today) | Becomes relevant only with #16; design note kept (— · n/a until then) |
| 19 | Cross-family agreement as a free verifier (58/58) | **Lacks it** — the factory has one model family (TinyNets) + the Tier-1 LM path; no second family to agree with | Where the Tier-1 composer and a Tier-0 specialist answer the same question, log agreement; use disagreement to prioritise dream data (S · measurement only) |
| 20 | Chunked reading for the LM tier (small reader first, big reader where empty) | **Lacks it** on the Tier-1/researcher path (composites b4/b6 territory); Tier-0 doesn't read pages | Researcher-path composition candidate, measured on logged real inputs exactly as Fable did (M · whole-hive battery slice, same as the waking-dream adoption path) — not in Top-3 because the Tier-1 line is not tonight's substrate |
| 21 | Direct ternary training by vote counters; flip-and-measure edits | **Has the substrate, lacks the trainers** — `tern_runtime.py` serves born-ternary models via the corrected b1.58 forward; ternary flip surgery exists in the lab's history (secret-line pack 0.9154 → 0.9385) | Add a vote-counter direct trainer as a *candidate-generation arm* beside today's three (M · candidates still face the dual gate; arm provenance recorded like the others) |
| 22 | Health/thermal gating of heavy work | **Has it** — `thermal.py` governor + host.py duty-cycle/backoff | None. Keep. |
| 23 | "Found nothing is not a pass" + ask-once-for-more-items verifier rules | **Has it** — adopted into this lab's verifier stance from the earlier note (METHODS addendum 3) | None. Keep. |
| 24 | Instructions for small models carry no example values | **Lacks it as a written rule** — a real, measured failure mode (52 → 62 facts) with a one-line fix | Adopt as a standing rule for any prompt shown to a Tier-1 small member; add a lint check for example values in member instructions (S · process) |
| 25 | Rehearse the unattended path in a bare environment before trusting it | **Weaker** — preflight exists for growth cycles; no fresh-environment rehearsal of the cron path | One bare-venv rehearsal of the exact cron invocation before cycle 5 (S · process gate) |

---

## 5. Top-3 recommended builds for Muse's side

Ordered by (value × fit to the current substrate) ÷ risk. None of these is implemented by
this study; cycle 4 stays attributable to today's methods arms, and each build below names
the measurement that would prove it — under the existing dual gate / battery / audit, with
nothing serving on argument.

### Build 1 — The champion recipe: persistent, one-gene-mutated, held-slice-crowned
*Fable principle: §2.8 — the hive finds its own recipe; every founding is a one-gene
experiment; the recipe, not the body, is what gets selected.*

**What changes in `factory/`:** a `champion_recipe` record in the registry (the current best
training configuration for TinyNet births: init source, lr, epochs, mixture leans — the same
knobs today's head-to-head already varies). Each growth cycle, *one* target's candidate is
trained with a one-knob mutation of the champion; the per-cycle head-to-head continues for
the other targets. If the mutated candidate is born *and* its dev-split margin over the
champion-recipe candidate (same target, same budget) is positive, the mutation becomes the
new champion; otherwise the champion stands. Full provenance in the cycle JSON, in the style
of the existing methods block.
**Proof it is better:** over the next N cycles, champion-lineage candidates' birth rate and
mean dev margin vs the per-cycle head-to-head's picks, on identical targets/budgets. If the
champion lineage does not out-birth the head-to-head within a stated number of cycles, the
record is dropped and per-cycle selection stands — Fable's own rule, applied to the import
itself.

### Build 2 — The learned say for the bug-pattern composition, re-fit at every battery run
*Fable principle: §2.5 — combination weights are learned per seat, re-made at every
measurement, and never frozen into an artifact.*

**What changes in `factory/`:** the waking-dream composer currently combines its members
with fixed behaviour. Add a `learn_say` step to `run_battery.py`: on the battery's own
training-side cases (never the sealed slice), fit per-seat standings for the composer's
members (raw members + dream layer) and the sharpness of the fit-following; store the say in
the *run record*, not in the registry — serving uses the latest battery-fitted say, exactly
as Fable's say is re-made at every measurement and kept out of git. Cycle 1's static
learned-say failure (0.7931 vs 0.8276 routed, measured once, on a spent surface) is the
cautionary record: the Fable version differs in the two ways that plausibly matter — re-fit
every measurement, and fitted on fresh cases each time rather than once.
**Proof it is better:** the sealed bug-pattern slice (today 0.8333 served via the dream
layer) must not regress, and the battery's bug-pattern slice must beat the fixed
composition's across two consecutive battery runs before the fitted say serves; a single
run's win is recorded, not adopted — the battery-gated serving law decides.

### Build 3 — Spawn mining over the factory's own serving log, feeding weakness-directed targets
*Fable principle: §2.6 + §2.2's scouts — the system notices its own micro-jobs and grows
where it measurably fails; nothing is staffed on a hunch.*

**What changes in `factory/`:** `serve.py` gains an append-only decision log (input,
artifact, answer, provenance — the calls already carry provenance; add the log). A new
intake stage in `growth_cycle.py` mines the log two ways: (a) *decision sites* — repeated
near-identical Tier-1/composer calls whose answers take a few fixed values become candidate
Tier-0 niches, entering the registry as unproven targets; (b) *failure sites* — serve-time
disagreements and fallbacks (shadow wins, dream-layer overrides) are counted per niche and
fed into target registration alongside the existing intake scan, so cycles attack what
serving actually gets wrong, not only what labelled data lacks. Candidates from (a) are born
only through the ordinary dual gate on constructed held slices; the log itself is never a
judging surface.
**Proof it is better:** the first mined niche that is born and serves — or, within a stated
number of cycles, an honest zero (mining found nothing the gate would pass), reported the
way Fable reported its first round staying off for lack of evidence. Secondary measure:
share of cycle targets sourced from serving failures vs labelled-data intake, tracked in the
cycle JSON.

**Deliberately not in the Top-3** (in the table, for when their turn comes): runner-based
unattended cycles (#16 — premature until state is portable, #15), the daily generated exam
(#17 — valuable, but it measures the working system rather than improving it, and the
battery suffices until serving traffic exists), and the vote-counter ternary trainer (#21 —
a candidate-generation arm to add *after* cycle 4 shows which of today's three arms earn
their keep; adding a fourth arm now would muddy exactly the attribution Arnav asked to
preserve).

---

*Sources: `fable-audit-copy` README.md, SPEC.md, HANDOFF.md (START HERE + Live status),
`.github/workflows/{hive,exam,ask}.yml`, `training/body.py` (GENES/next_recipe/body_is_due),
`team/cells/spawn.py` (COVER/RETIRE constants), `training/reports/` as cited per section;
this lab's `fable-validation/VALIDATION.md` and `VALIDATION-ADDENDUM-2026-11-11.md`
(199 tests passing at d31fd51; figures cross-checked); `edit-lab/factory/` (FACTORY-LOOP.md,
serve.py, growth.py) for the translation target; commit hashes cited inline throughout.*
