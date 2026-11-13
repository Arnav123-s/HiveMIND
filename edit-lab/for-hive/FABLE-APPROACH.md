# Muse's work, Muse's side

# Fable's approach — what to copy, where Q1 already does, and how we staff it at company scale

*Standing note: everything in this file was learned read-only from Fable's side — `HANDOFF.md`,
`FOR_MUSE.md` (at commit `942803d`), exam tables, workflow files and commit history in
`~/workspace/fable-audit-copy` (git log / show / diff only; nothing checked out, committed or
written there). The one-way valve stands: Fable's side is read, never touched. The choices,
gaps and staffing below are Muse's.*

*Provenance warning that shapes several points below: in this audit copy the refs do not sit
where their names suggest. Local `make-it-work` is `f517a36`, which is an **ancestor** of our
chassis `942803d`; local `main` (`31a6756`, PR #15) is older still. The newest Fable-side refs
are `origin/make-it-work` / `origin/claude/epic-johnson-7ene30` at `c256322` and `origin/main`
at `e067e63` (PR #17) — and the only changes in `942803d..c256322` are `FOR_MUSE.md` and
`HANDOFF.md` governance wording (commits `985f8eb`, `c256322`). **No exam or team code changed
after our chassis.** The cache trap, the unwinnable German "museum" draw, label-blind `same()`,
the shared 2400 s members+roles budget and the cp1252 class therefore have **no Fable-side fix
to adopt** — our plan's operator-level fixes, on a byte-identical chassis Fable's side can
rerun, are the correct move, and waiting for upstream would be waiting for nothing.*

---

## 1. THE METHOD, extracted — ten operating rules

Each rule is stated as Fable's side actually practises it, with the trace that proves the
practice (not just the preaching). The loop they form:
**decompose → price/spike → run in batches with controls → judge by a pre-stated bar on fresh
material → keep winners only → rerun before building in → record losers with numbers.**

### Rule 1 — Decompose the goal into numbered, measured sub-questions, in usefulness order
One big goal becomes a short ordered list of questions, each small enough to be answered by
runs, each carrying its exact arms and command. *Trace:* `FOR_MUSE.md` at `942803d` is literally
that — five numbered questions, Q1 first ("Which form of the working hive is better"), each with
the sitting command and its three environment variants spelled out; `HANDOFF.md` "Open, in
order" and "Open next, in the order they would help" do the same inside Fable's own queue.
Questions not yet decomposed do not get run at all.

### Rule 2 — Price and spike before committing; never buy the full grid on a guess
A cheap probe prices the real thing first, and the price can kill or re-scope the plan.
*Trace:* the members form itself began as a 16-task trial sitting on seed 315 (10/16 in
15 min, `training/reports/exams/315_members2_trial.md`) before any paired campaign;
`training/experiments/cpu_speed.py` prices BitNet sizes before any founding decision;
`HANDOFF.md` repeatedly prices in the open ("a 4B plan costs about a minute; a 1.7B weight
edit on 128 lessons takes 25 minutes") and warns that a verdict at one budget is not a verdict
at another ("What won at 600 steps but costs time … read 3.5680 at 20 minutes: a 600-step
verdict is not a verdict at equal time").

### Rule 3 — Equal work, not equal minutes; a control arm in the same batch, or it is not a claim
Machine speed is treated as noise to be designed out, not averaged out. *Trace:*
`FOR_MUSE.md` return condition 1 ("Machine speed varied by 30% between runs here and by
25 times between GitHub runners. For nets of different sizes count block-steps") and condition
2 ("A control arm for every claim, run in the same batch. (The five-level win disappeared when
the same size was run without the five levels.)"); `5026f9e` re-budgets `ideas.py` in
block-steps for exactly this reason; the equal-work growth test (`7f0519a`, 6420 block-steps)
overturned a 20-minute reading that had favoured growing.

### Rule 4 — Fresh material judges; read material only finds faults
Two seed classes, kept apart by discipline, never by convenience. *Trace:* `FOR_MUSE.md`
condition 4 ("Exam seeds already looked at (315, 9001 to 9008) are for finding faults only; a
claim needs seeds nobody has read") and `HANDOFF.md`'s standing reading of Arnav's word:
"seeds already sat are for finding faults, a claim is made only from a seed not looked at
before"; "Do not tune the trial form on seed 315's failures; its next sitting is a new seed,
paired with the roles." Held-out sets in the older work were "run once, on frozen code, and
reported as measured."

### Rule 5 — State the bar before the run; keep only what clears it beyond chance
*Trace:* `FOR_MUSE.md` condition 3 ("Three starts or more, and … a gap of more than
2 standard deviations and more than 0.01"); the birth gate in `HANDOFF.md` ("its gain must
exceed 0.004 **and twice its standard error**", validated on 32 null judgements: old gate kept
2, new gate none); the recipe rule ("Whatever beats the three starts by twice their spread is
run together, then held against today's recipe"). A win inside the bar is recorded as level —
not narrated as a win.

### Rule 6 — Read the artifacts, not the scores, to find causes
Scores say *that*; programs, outputs and logs say *why*. *Trace:* `FOR_MUSE.md` Q2 ("Every
fault mended so far was found by reading the members' own programs and outputs
(`<run>/members/**/member*_*.py` and the `.out`/`.err` files beside them), never by looking at
scores"); `HANDOFF.md` 2026-11-12 night: four member faults (DONE returned as a program, the
same program resent to the last turn, numbers-only comparison, a typed answer run as a
program) found "by logging every program and reply of four failed tasks", each then mended in
its own commit. The failure taxonomy is per-kind and causal — numbered lists / form-to-the-
letter, three orders with labels A/B/C dropped, summaries unconfirmed, operating a website,
mend-a-program where both members run the broken code and agree on its output — and it is
written against seeds 9005–9007 explicitly as fault-finding material.

### Rule 7 — Defaults move on evidence, and the evidence is written into the thing changed
A decision is not a memo; it is a code/config change whose commit — and whose inline comment —
carries the seed, the code hash, the scores and the times that justify it. *Trace:*
`61fb325` flips `ask.yml`'s members default to `"2"` with the comment "Seed 9007 (never looked
at, nothing learned, code db8b8d0): members first 10 of 16 in 179 minutes, the roles alone 9
of 16 in 178, the members alone 9 of 16 in 69. Level on one sitting, and never slower";
`ad26028` flips the library default off in `team/solo.py` with the numbers in the comment
("with the library the members passed 7 of 16 in 89 minutes on seed 9003, with nothing learned
10 of 16 in 56 (same code f705ae1; seed 9002 said the same). It is still kept, to be measured
again"). Note the two-tier logic, which is the subtle part worth copying exactly: **a
reversible default may move on a hint** (one fresh seed, level scores, never slower — the cost
of being wrong is one flipped default), **while a claim may not** (Rule 5's bar). Fable's side
does not confuse the two tiers, and neither should we.

### Rule 8 — Build in only what survives a rerun on unused material; write down what did not hold, with its numbers
*Trace:* `FOR_MUSE.md`, "What this side will do with it": "Read the one page, **rerun the
winning arm once here on a seed or start nobody has used, and build it in if it holds. What
does not hold is written down with its numbers in HANDOFF.md, so nobody runs it twice.**"
`HANDOFF.md` practises it: the layered five-level headline is retracted in its own record
("the other lab's headline … compared a half-size net with a full-size one, as its own record
says"); the library is kept in code but defaulted off pending re-measurement; two unmeasured
mistakes of 2026-11-12 evening (the lengthened post-program wording; the library shown to
every member) are named as mistakes, with what they broke, in the handoff itself.

### Rule 9 — One page per question, raw rows beside it, exact commands, what was not run
The return format is part of the method, because it is what makes Rule 8's rerun possible.
*Trace:* `FOR_MUSE.md` condition 5 ("One page per question at `edit-lab/for-hive/<question>.md`
…: the question, the table, the verdict by the bar, what was not run, and the exact command of
every arm. Raw rows in a `.json` beside it."); Fable's own exam tables follow the same
discipline — every sitting file header carries score, minutes, **code hash and memory state**
(e.g. "10 of 16 tasks passed in 56 minutes (code f705ae1, memory: none)"), with a per-task
table of field, kind, pass, time and the checker's own words.

### Rule 10 — Treat contention and time as contaminants; run one heavy thing at a time, and make runs resumable and self-recording
*Trace:* `HANDOFF.md` 2026-11-13: "**Times on GitHub are not a measure.** The same trivial sum
took 22 s in one members sitting and 594 s in another (same code baabc10, seeds 9005 and
9006); many sittings were running at once. Compare times only between sittings that ran side
by side."; "never run two trainings at once (four cores; a 6-minute run took an hour)";
`scripts/resume.sh` refuses to start if a grow or exam job is already running and gives every
job a pid file and a log; `.github/workflows/exam.yml` (at `942803d`) gives each sitting
combination its own concurrency group (`seed` and `alone` were added after "a sitting pushed
another out of the queue"), `cancel-in-progress: false`, `timeout-minutes: 330` on the sit job,
artifact upload `if: !cancelled()` with 30-day retention, and a **separate record job** — the
job that runs the hive holds a read-only token, and a second job that "runs no model and no
code the hive wrote" takes only numbers and known names into `exams.jsonl`. Separation of
runner and recorder is a designed integrity property, not an accident.


---

## 2. Where Q1-RUN-PLAN.md already follows it — and where it does not

### Already following (keep; do not re-litigate)
- **Rule 1 (decomposition):** Q1 is one numbered question with a named primary pair
  (members-first vs members-alone) and Bonferroni-corrected secondaries — decomposition done.
- **Rule 2 (price/spike):** pilots 12001–12003 are priced and excluded, per-form planning
  prices come from RT-4, the queue is trio-sequential with re-pricing after trio 12004, and
  the full 8×3 grid was explicitly refused as unpurchasable (≈135 h vs ≈36 h). Textbook Fable.
- **Rule 3 (same-batch control):** fresh trios, all three arms on the same seed in one batch,
  ABC/BCA/CAB rotation, batch-break rule, 12002's existing arm refused as a trio arm.
- **Rule 4 (fresh judges):** claim seeds start at 12004, never read; 315/9001–9008 and the
  pilots are fault/hypothesis material only; seeds are never swapped because of their draw.
- **Rule 5 (pre-stated bar):** the plan's bar (|mean paired gap| > 2 × SE, McNemar primary,
  MDE₈₀ printed beside any gap, re-estimation gate after two trios) is *stricter* than
  Fable's 2 SD + 0.01 — correctly, because a form claim is the high-stakes tier of Rule 7.
- **Rule 7 (defaults with numbers):** `HIVE_LIBRARY=0` is pinned in every sitting, following
  the `ad26028` evidence — a Fable default adopted with its numbers, not on faith.
- **Rule 10 (contention):** one work copy per sitting, bounded pid-filed monitor, thermal
  gates, one heavy job, leftover-monitor claim — this is `resume.sh`/exam.yml discipline
  translated to ashp, and in the monitor's case improved on it.

### Gaps (numbered; each maps to an edit in §4)
- **G1 — No build-in step (breaks Rule 8, the closing half of the loop).** The plan ends at a
  verdict on a page. It never says what a win *changes*: which default on Muse's side flips
  (e.g. the form Muse's own hive/ask path uses first), in which file, on whose authority, or
  what a members-alone non-inferiority win changes operationally (cheapest form first, roles
  as escalation?). Without this, Q1 produces a number, not an improvement — exactly what
  Fable's "What this side will do with it" exists to prevent.
- **G2 — No confirmation rerun before build-in (breaks Rule 8).** Fable's side will rerun our
  winning arm once on an unused seed before building it in; the plan does not pre-commit to
  that, nor offer it a clean target. If the rerun is improvised after the verdict, it will be
  designed under the influence of the result. Pre-declare it now: one winning-arm sitting on
  the next fresh seed (12010, or the first unused seed after the achieved k), run to the same
  frozen config, whose job is only to check the winner does not collapse — not a second claim.
- **G3 — No losers' record (breaks Rule 8's second sentence).** Caveats are carried, but there
  is no standing "did not hold / do not run again" ledger for Q1: losing forms' numbers,
  discarded readings (e.g. any per-kind story the appendix tempts), and approaches already
  falsified (VM lane, 12002-trio reuse, re-sitting 12003) live scattered across the plan,
  hive-form.md and five red-team reports. Fable's version is one place, with numbers, whose
  stated purpose is "so nobody runs it twice."
- **G4 — Failure reading is not staffed in the plan (breaks Rule 6).** The plan extracts the
  members-first five-number decomposition, but nobody is assigned to read failed tasks'
  member programs/outputs as sittings land. Our Q2 autopsy did this for the pilots, after the
  fact; Fable's practice is per-sitting, causal, and counted. Without readers, trio 3's page
  will know *that* forms differ and nothing about *why* — and Q2 will restart from cold
  artifacts.
- **G5 — Verification is transport-only (thinner than Rule 9/10's runner/recorder split).**
  The plan's mirror gate checks hashes, counts and file completeness — that the numbers
  *arrived*, not that they are *right*. Fable's exam.yml separates the runner (read-only
  token) from the recorder (no model code, numbers and known names only). Our analogue —
  an agent who did not run the sitting independently re-deriving each trio row from the raw
  `runs/exam/exam_<seed>/` records — does not exist in the plan.
- **G6 — Ownership is grammatical, not rostered (the 12003 lesson, half-learned).** The plan
  says a dead sitting "is restarted once, by me" and bans a second VM-side owner, but no
  sitting has a *named* owner, no handover/restart log is a deliverable, and restart authority
  is not stated as exclusive-and-transferable-only-in-writing. 12003 was resumed by machinery
  that "could not tell a park-kill from a crash" — the fix is a person, named per sitting,
  not only a checklist item.
- **G7 — hive-form.md does not yet meet the Rule 9 return format it will be judged by.**
  Audit against `FOR_MUSE.md` condition 5: question ✓; table — partial (only 12002's row;
  no wall-time, code-manifest, engine or decomposition columns declared for campaign rows);
  verdict by the bar — pending, correctly; what was not run ✓ (good section); exact command
  of every arm — **stale**: the page's commands are the old VM commands, without the plan's
  pinned env (`AGENT_TEAM_ENGINE=hf`, `HIVE_LIBRARY=0`, `PYTHONUTF8=1`,
  `PYTHONIOENCODING=utf-8`, threads 8), without the per-sitting copy path, and with a VM
  python path. Fable's side rerunning an arm from that page today would not rerun our arm.
  Raw rows: `hive-form.json` exists ✓ but no campaign-records row schema is declared.
- **G8 — Wall-time is a first-class outcome, but the plan under-caveats Rule 10 for it.**
  Fable's rule is times compare only between side-by-side sittings; ours run sequentially in
  rotation. Rotation balances order, it does not make sequential wall-times side-by-side.
  The cost/non-inferiority claim must carry the sentence: wall-times are sequential,
  rotation-balanced, single-lane measurements — comparable as campaign costs, not as the
  isolated speed of a form. (The 22 s vs 594 s sum is the standing warning.)
- **G9 — One unfootnoted chassis fact the method would footnote.** Our chassis `942803d`
  already contains Fable's post-fault-seed loosening of `same()` (`725b202`: near-numbers
  within 0.051, prose word-overlap threshold 0.6 → 0.4), derived from seed 9005 fault-finding
  and, per `HANDOFF.md`, "not measured yet" on a claim seed (9008 was to be its sitting). That
  is legitimate Rule 4 practice (fault seeds may teach fixes; claim seeds then measure them),
  but the plan's caveat should name it: our fresh trios are, among other things, the first
  claim-seed measurement of that loosened agreement rule.

---

## 3. Staffing the method at higher manpower than Fable can field

Fable's side runs this loop with essentially one strong agent in sequence: it prices, runs,
reads, records and decides, and its `HANDOFF.md` shows the cost — sittings discovered hours
later, mistakes found after they shipped, a queue one deep. Muse's side can run the *same
loop with the roles separated and simultaneous*. Separation is not bureaucracy here: Rules 6,
9 and 10 each contain an independence requirement (read causes, don't grade your own run,
runner ≠ recorder) that a single agent can only fake. The map below staffs Q1 only; every
role is an agent assignment, not a new process on ashp — **the lane still runs one sitting at
a time; the parallelism is around the lane, never on it.**

| Role | Count | What it does | When it acts | What it produces |
|---|---|---|---|---|
| **Sitting Owner** (one per sitting, named in RUN-METADATA before launch) | 1 per sitting; a different agent may own the next sitting | Owns that sitting end-to-end: pre-launch checklist, launch, bounded monitor, thermal holds. **Sole restart authority** — the only agent who may restart it, exactly once, under identical env, and the only one who may declare it dead. Any transfer of ownership is written into the sitting record before it takes effect (the 12003 rule: machinery and bystanders never restart a sitting). | From copy creation to verified mirror | The sitting itself; RUN-METADATA completed (restarts, true wall span, thermal peak); a signed launch-to-mirror log line |
| **Artifact Readers** | 1–2 per sitting, may read sittings in parallel with the lane running the next one | Read *every failed task's* member programs, `.out`/`.err` and board records (Rule 6), classify each failure against the standing taxonomy — Fable's five kinds (form-to-the-letter, A/B/C labels, summaries, website operation, mend-agree-on-broken-output) plus our labels (timeout, cp1252/encoding, cache/no-artifact, agreement-on-wrong-values) — and count causes, not anecdotes. Passes are spot-read (1 in 4) for lenient-check artefacts like 9003's "Not confirmed" pass. | Within hours of a sitting's mirror landing; finished before its trio closes | Per-sitting failure-cause table (task, kind, cause label, artifact path) appended to the autopsy record; new labels proposed, never silently added |
| **Row Verifiers** | 1 per trio; **never the Owner or a Reader of any sitting in that trio** | Independently re-derive the trio's page rows from raw records only: recount passes from the 16 `exam.json` per arm, recompute per-kind counts, the members-first five numbers, wall spans from logs (not report JSON), and the paired/McNemar inputs. Discrepancies stop the page, not the lane. This is our exam.yml runner/recorder split, staffed. | At trio completion, before the page updates | A verification note per trio: rows re-derived ✓/✗ per number, discrepancies and their resolution; only verified rows are marked verified in `hive-form.json` |
| **Builders** (standing, not per-sitting) | 2 standing: Lane Builder, Records Builder | *Lane Builder:* owns the launcher, bounded monitor, per-sitting copy tooling and mirror scripts as maintained code with tests — fixes between trios only, never mid-trio (a mid-trio tooling change is a batch break). *Records Builder:* owns RUN-METADATA schema, campaign-records layout, the losers' ledger file and the page's row schema. Both also own the G2 confirmation-rerun harness readiness and the G1 build-in change when a verdict lands. | Continuously; change windows at trio boundaries | Versioned launcher/records tooling with a changelog; a build-in patch ready to apply the day a verified verdict + confirmation rerun both land |
| **Plan Keeper** | 1 for the campaign | Guards the frozen plan: updates `hive-form.md`/`.json` **only** at trio boundaries and only with Verifier-signed rows; maintains the claim state (which licensed sentence, current MDE₈₀, achieved k vs target/fallback/stretch), the losers' ledger, and the what-was-not-run list; refuses page edits from unverified or mid-trio material. Also owns the FOR_MUSE-format audit (G7) before the first trio row lands. | At trio boundaries; format audit before trio 1 closes | The page, updated atomically per trio; claim-state line; losers' ledger entries with numbers |
| **Coordinator** (the role this plan already has) | 1 | Rules where roles disagree (Owner vs Reader on a cause label, Verifier vs Keeper on a discrepancy), owns batch-break declarations and any communication with Fable's side / Arnav. Does not own sittings, read for the record, or verify — separation is the point. | On escalation; at each trio gate (roles gate, re-estimation gate) | Rulings, recorded in the plan's record with reasons, as the red-team rulings were |

**Why this is Fable's method and not just more hands:** every role above is a Fable practice
made simultaneous — Owner = `resume.sh`'s single-job discipline with a name on it; Readers =
Q2's "read the programs, never the scores" while the lane is still warm; Verifiers = exam.yml's
separate record job; Builders = the fixes-in-commits habit, windowed so tooling never
contaminates a batch; Keeper = `HANDOFF.md`'s "written down with its numbers, so nobody runs
it twice," kept as a ledger instead of a narrative.


---

## 4. Text for Q1-RUN-PLAN.md

### 4a. Adopted-method section — drafted ready to paste into Q1-RUN-PLAN.md

> ## Method adopted from Fable's side (Muse's reading, 2026-11-13)
>
> This campaign runs Fable's loop, staffed at company scale (see FABLE-APPROACH.md):
> decompose into numbered measured questions; price/spike before committing; run arms as
> same-batch controls on fresh, never-read seeds; judge by a bar stated before the run;
> read failed tasks' artifacts — never scores alone — to find causes; move reversible
> defaults on evidence with the numbers written into the change, but make claims only past
> the bar; build in only what survives a rerun on unused material; and write down what did
> not hold, with its numbers, so nobody runs it twice. Two tiers are kept distinct
> throughout: a *default* may flip on a fresh-seed hint if it is reversible and never worse
> on cost (Fable's members-first default, commit 61fb325, is the model); a *claim* may not.
> Times are campaign costs, not measures of a form: Fable's side recorded the same trivial
> sum at 22 s and 594 s under contention (same code, seeds 9005/9006), so wall-times here —
> sequential, rotation-balanced, single-lane — are reported beside scores, never as an
> isolated speed ranking. The chassis is byte-identical to Fable's side's 942803d so any arm
> can be rerun there; no Fable-side fix for the red team's defects exists in any later ref
> (942803d..c256322 changes only FOR_MUSE.md/HANDOFF.md), so the plan's operator-level fixes
> stand as the campaign's handling.

### 4b. Numbered edits the staffing map and gaps imply for the plan

1. **Add a "Build-in" subsection after Reporting (closes G1):** state in advance what each
   licensed outcome changes on Muse's side — (a) a members-first win past the bar: Muse's
   default form becomes members-first, in the named file/config, with the trio numbers in the
   commit comment, Fable-style (61fb325); (b) members-alone non-inferior within 3/16 at lower
   wall cost: members-alone becomes the default first form, roles/members-first the
   escalation; (c) indistinguishability: no default changes, and that non-change is itself
   recorded with the MDE₈₀. Name the Builder who applies it and the Coordinator who authorises it.
2. **Pre-declare the confirmation rerun (closes G2):** after a verdict past the bar and before
   any build-in under edit 1, run one winning-arm sitting on the first unused fresh seed
   (12010 unless already consumed) under the identical frozen config, owned and mirrored as a
   campaign sitting but reported separately as a confirmation, not a claim trio. Build in only
   if the winner does not collapse (pre-state: scores within the achieved CI's lower half is
   failure to hold — the Coordinator pins the exact collapse rule before the verdict is known).
   This mirrors, and makes clean work for, the rerun Fable's side says it will do itself.
3. **Create the losers' ledger (closes G3):** `for-hive/q1-losers.md` ("Muse's work, Muse's
   side"), seeded at adoption with: VM lane (12001, 4× 2400 s timeouts, zero artifacts);
   12002-as-trio-arm (refused, batch rule); re-sitting 12003 (counterfeit risk); the
   library-on form (Fable's seeds 9002/9003 numbers); and a standing rule that every closed
   trio appends its losing readings with numbers before the next trio launches. Plan Keeper owns it.
4. **Staff the Reporting section (closes G4–G6):** rewrite Reporting to name, per sitting,
   its Owner (sole restart authority; ownership transfers only in writing in RUN-METADATA),
   its Reader(s), and per trio its Verifier (never that trio's Owner or Reader) and the Plan
   Keeper. A sitting is reported to the parent only by its Owner; a trio reaches the page
   only with the Verifier's re-derivation note attached.
5. **Add the Readers' deliverable to per-trio reporting (closes G4):** beside the per-kind
   appendix, each trio reports a failure-cause table — every failed task classified from its
   artifacts against the standing taxonomy (Fable's five member-failure kinds plus timeout /
   encoding / no-artifact / agreement-on-wrong-values), causes counted per form — feeding the
   Q2 autopsy continuously rather than retrospectively.
6. **Upgrade the mirror gate to a verification gate (closes G5):** a trio row is marked
   verified in `hive-form.json` only after the Verifier re-derives it from the raw
   `runs/exam/exam_<seed>/` records (pass recount, per-kind recount, decomposition, wall span
   from logs). Hash/count mirror checks remain the Owner's transport gate, explicitly
   labelled as such.
7. **Fix hive-form.md's Exact commands before trio 1 closes (closes G7):** replace the page's
   command block with the campaign's real commands — per-sitting copy path, the pinned env
   (`AGENT_TEAM_ENGINE=hf`, `HIVE_LIBRARY=0`, `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`,
   threads 8) on every arm — and declare the campaign table's columns (score, wall span,
   restarts, code-manifest hash, engine, members-first decomposition) so Fable's side could
   rerun any arm from the page alone, per FOR_MUSE condition 5.
8. **Add the wall-time caveat sentence to Caveats carried (closes G8):** "Wall-times in this
   campaign are sequential, rotation-balanced, single-lane costs. Per Fable's side's own
   record (22 s vs 594 s for the same trivial sum under contention), they are reported as
   campaign costs beside scores and are never read as a form's isolated speed."
9. **Add the `same()` caveat to Caveats carried (closes G9):** "The frozen chassis (942803d)
   includes Fable's side's loosened agreement rule (725b202, derived from seed-9005
   fault-finding: near-numbers within 0.051; prose overlap 0.4), unmeasured on any claim seed
   when adopted there. These fresh trios are its first claim-seed measurement; agreement-rate
   differences between member arms and Fable's GitHub sittings must be read with that in mind."
10. **Window the Builders' changes (protects Rule 3):** launcher/monitor/records tooling may
    change only at trio boundaries; any mid-trio tooling change is declared a batch break
    under the existing batch-break rule, with completed trios standing.

---

*End. Companion files: `Q1-RUN-PLAN.md` (the plan this amends), `hive-form.md` (the Q1 page),
`q1-redteam/RT-1…RT-5` (the defects), `failure-autopsy.md` (the Readers' standing record).*
