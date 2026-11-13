# Muse's work — Muse's side

# Q1 · Which form of the working hive is better?

**What I chose and why (Muse's call, per the governance Arnav set 2026-11-12):** I take Fable's
advice in its order — this question first, before the library question — and I run it my way:
the spike first, priced honestly on this VM, with the laptop (ashp) evaluated as a second lane
because the VM's price under sprint contention is the binding constraint. Fable is the adviser;
the choice and the numbers are mine.

**Question (from Fable's FOR_MUSE.md, 2026-11-13).** On one fresh seed (9007, GitHub) members-first
scored 10 of 16, the roles alone 9, members alone 9 — one task of difference is noise. Needed:
8 or more fresh seeds, the three forms side by side on each, reported per kind of task, not only
in total.

**Forms.** All three are the same sitting (`training/exam.py sit --tasks 16 --seed N
--empty-memory`, code 942803d from make-it-work, run from Muse's own copy at
`edit-lab/for-hive/q1-work/`). **Campaign chassis (from plan v2, 2026-11-13):** the
campaign runs `942803d` **plus two declared patches** — `cells-engine-hf.patch` (cells off
under the hf pin; removes the llama_cpp crash class that killed 5 of pilot 12003's failed
tasks) and `sandbox-pythonutf8.patch` (PYTHONUTF8 passes into sandbox children) — manifest
rollup `fb51cf44e430216844b86eaf57517391d3e92e97a3541e0c4531465824671730` (243 `.py` files,
identical on the VM, on ashp, and in every sitting copy). Each patch is inert under the
GitHub configuration (engine auto/gguf, PYTHONUTF8 unset) and is published in
`q1-engineering/patches/` so any campaign arm can be rerun exactly. The pilots ran
unpatched; that is recorded against them, not hidden.

| arm | environment | meaning |
|---|---|---|
| members-first | `AGENT_TEAM_SOLO=2` | two members try first; the roles take over only if the members do not agree |
| members-alone | `AGENT_TEAM_SOLO=2 AGENT_TEAM_SOLO_ALONE=1` | the members by themselves; agreement is the answer |
| roles | neither | the original pipeline of role specialists |

**Seeds.** 12001–12008 — fresh, never read by anyone (the fault-finding seeds 315 and 9001–9008
are excluded by Fable's rule 4). Same seed across the three arms in the same batch; the
no-environment arm is the batch's control for the two member arms, and members-alone is the
control for the claim that the roles add anything.

**Engine caveat (read before comparing with GitHub's table).** GitHub's sittings run the
llama.cpp engine (brain4b / coder7b GGUF, compiled native). This VM has no llama-cpp-python and
no GGUF files, so `team/llm.py` falls back to its PyTorch path: Qwen3-1.7B (roles) and
Qwen2.5-Coder-1.5B-Instruct (members), both already in the local Hugging Face cache, bf16 on
CPU, OMP/MKL pinned to 2 threads. The three-arm comparison is internally valid (same engine,
same seeds, same batch discipline); the absolute pass levels are **not** comparable to GitHub's
GGUF sittings. Also missing here: Playwright's Chromium, so in the roles arm the browser
specialist cannot drive a real browser (the members do website tasks by writing programs,
which is unaffected).

## Pricing (spike)

Reference points from GitHub runners (4 vCPU, GGUF engine): members alone 69 min (seed 9007)
and 19 min (seed 9005); members-first 179 min; roles alone 178–277 min per 16-task sitting.

This VM: 1.5 shared CPUs, ~6 GB, heavily shared with the BitNet sprint (ladder, mill, growth).
Spike: one sitting, seed 12001, started 2026-11-12 ~21:13 PT under full sprint contention —
per-task times land in `hive-form.json` as tasks complete. Interim observation
(~21:25 PT): the first task was still on its first member after ~12 minutes; the member process
sat at ~12% CPU with its model paging from disk (7.6 GB read) — on this VM the PyTorch path is
I/O-bound under memory pressure, not compute-bound. Expect members-alone on the VM to price in
hours per sitting, not minutes; the ashp lane (32 GB RAM, ~3× the CPU, idle) is being priced in
parallel and is the likely primary lane. Machine per seed will be recorded in the table.

**Spike outcome (seed 12001 — spike only, excluded from the verdict table).** The spike launch
ran the members-first arm (`AGENT_TEAM_SOLO=2`). Task e12001_00 (live facts) hit the exam's own
2400 s per-task limit: **2405 s, timed out, fail, and zero member artifacts** — member 1 never
finished its first program, so the failure is the engine on this machine, not a member cause.
The sitting was restarted under the members-alone arm to keep collecting prices; the VM then
rebooted twice mid-sitting, and after the owner's one permitted restart the tally stood at
**4 of 16 tasks recorded — all four 2400 s timeouts with zero member artifacts** (~2.7 hours of
task time, no member behaviour ever produced). Two process-management incidents, both mine, are
recorded in `hive-form.json` so nobody misreads the data (a `pkill -f` self-match killed one
task process at 72 s; its poisoned record was deleted, not counted).
**Decision (Muse's call): the VM lane for Q1 is closed.** Four identical timeouts are the
measurement — on this VM, under sprint contention, a members sitting costs ≥ 2400 s *per task*
and returns no hive behaviour at all; restarting would re-measure the same wall with the
sprint's RAM. The sitting's records persist, so it can resume if the VM ever sits idle.
**ashp is the Q1 lane** (first full sitting: seed 12002, members-alone, 11/16 in 196 min —
see the table).

**PARKED (Arnav's ruling, 2026-11-13 00:33 PT — "forget the laptop part for now, focus
strictly on this goal").** All laptop work was parked, and the seed 12003 members-first
sitting then running on ashp was stopped on 2026-11-13 ~03:05 PT (taskkill on its launcher
and monitor trees; verified zero matching processes at the time). **CORRECTION
(2026-11-13, found by the Q1 red team's live probe — q1-redteam/RT-5): the record above
was wrong about what happened next. Seed 12003 COMPLETED.** Its sit log shows two pre-park
starts (01:33, 02:04), the ~03:05 park stop, and then a post-park resumption — by the Q1
stream's own restart machinery, which could not tell a park-kill from a crash — finishing
at 05:53:27 PT with **8 of 16 passed** (members-first; report SHA-256 matches the VM copy
`exams-12003-ashp.json`). All 16 task records stand in `runs/exam/exam_12003/` on ashp.
12003 is therefore not a partial: it is a completed sitting with a broken provenance chain,
and it is **excluded from every average** and kept as a flagged pilot (see the plan for the
full ruling). It must never be re-sat in a shared checkout — `exam.py` would skip all 16
tasks and counterfeit a sitting in seconds. The VM lane stays closed by measurement (seed
12001 halted at 4/16 — all four tasks 2400 s timeouts, zero member artifacts).

**UNPARKED FOR SITTINGS ONLY (Arnav's ruling, 2026-11-13 ~10:09 PT).** The laptop is
approved for the Q1 exam sittings — sittings only; all other laptop/house work stays
parked. Before any sitting ran, a five-agent red team attacked the design (reports in
`q1-redteam/RT-1…RT-5`); it found, among other things, that the harness returns a previous
arm's cached results for a seed (so the naive trio would have fabricated its own data),
that the design cannot statistically certify the 1-task effect it was built around, and
that the full 8×3 grid costs ≈135 machine-hours against ≈36 available before Nov 16. The
hardened campaign that survived is specified in **Q1-RUN-PLAN.md**: fresh paired trios on
fresh seeds (12004 onward), one hash-verified work copy per sitting, pinned engine/env,
trio-sequential order with rotation, a pre-declared primary pair and bar, and the claim
re-scoped to large effects or non-inferiority-plus-cost. Seeds 12002 (members-alone, 11/16)
and 12003 (members-first, 8/16) stand as **pilots — never entered in the verdict table**.

**CAMPAIGN v2 — TEAMS, METHOD, LAUNCH (2026-11-13).** Arnav expanded the build before any
sitting ran: a **DevOps team** (restart-proof lane apparatus — per-sitting copies, detached
launcher, bounded thermal monitor, per-task mirror, watchdog — built and smoke-proven with
a dummy job, clean + kill/resume; `q1-devops/LANE-RUNBOOK.md`), an **Engineering team**
(config-diff proof that the arms differ only in the intended flags, memory-parity proof,
failure classifier 9/9 against the human autopsy, and the engine-propagation root-cause
that produced the two adopted patches), and a **Fable-approach team** (`FABLE-APPROACH.md`):
this campaign adopts **Fable's method** as its operating approach — decompose into numbered
measured questions; price/spike first; same-batch controls on fresh never-read seeds; a bar
stated before the run; causes read from artifacts, never scores alone; reversible defaults
may flip on a hint with the numbers written in, claims may not; build in only what survives
a rerun on unused material; losers written down with numbers (`q1-losers.md`) — and staffs
it at higher manpower than Fable can field: a named **Sitting Owner** per sitting (sole
restart authority), per-task **Artifact Readers**, per-trio **Row Verifiers** (never that
trio's Owner/Reader), two standing **Builders**, and a **Plan Keeper** who updates this
page only at trio boundaries with verified rows. Plan v2 (Q1-RUN-PLAN.md) folds all of it
in, pre-declares the build-in rules and a confirmation rerun on fresh seed **12010** before
any build-in, and carries two added caveats: wall-times are sequential campaign costs,
never a form's isolated speed (Fable's side's own 22 s vs 594 s warning); and the chassis's
loosened `same()` (commit `725b202`, from seed-9005 fault-finding) gets its first
claim-seed measurement in these trios. Seed 12004's draw is recorded
(`q1-devops/draw-12004.txt`): 16 tasks, standard mix, **no unwinnable German "museum"
draw**. Playwright Chromium is verified **absent** on ashp (roles-arm website handicap
stands, ≤2/16, not fixed — sittings-only scope). Sitting #1 — **12004 members-alone** —
launches under this plan; its row enters the campaign table only when trio 1 closes and
its Verifier signs it.

**VERDICT: pending the campaign (Q1-RUN-PLAN.md).** The full 8×3 grid is not purchasable
inside the sprint (≈135 planning-hours vs ≈36 available before Nov 16 — a scope fact, not
a shortfall); the campaign runs fresh paired trios in seed order with a declared target of
3 trios, a time-box fallback of 2, and a stretch of 4, continuing past the window toward 8.
The claim it can carry was fixed before any run: a difference is claimed only if
|mean paired gap| > 2 × SE of the mean paired difference for the pre-declared primary pair
(members-first vs members-alone), with the MDE₈₀ for the achieved k printed beside any gap;
otherwise the page carries the indistinguishability sentence — across k fresh paired seeds
the forms are indistinguishable within the measured interval, ruling out advantages larger
than the MDE₈₀, and the 1-task ordering on seed 9007 remains within noise. A secondary,
pre-declared claim tests members-alone for non-inferiority within 3 tasks per 16 of the
best scorer, with wall-time as a first-class outcome. Per-kind numbers are a
hypothesis-generating appendix only. The subset actually run will be stated here exactly,
with the stopping state — fewer seeds is a reported scope change, fewer than 16 tasks is
not allowed.

## Campaign table (declared columns; rows land per completed trio, Verifier-signed)

| seed | form | score /16 | wall span | restarts | code manifest | engine | members-first decomposition (total · fallback rate · member-phase pass · rescue rate · agreed rate) | verified |
|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | `fb51cf44…` (all campaign rows) | hf, threads 8 (all campaign rows) | — | — |

Rows are added by the Plan Keeper only when a trio closes and its Row Verifier has
re-derived every number from the raw records. Per-kind counts for campaign sittings go in
the appendix table below beside the pilot row, labelled hypothesis-generating only.

## Table (per kind, filled as sittings land)

| seed | machine | form | total /16 | sums | dates | units | tables | write-program | mend-program | live facts | website | file | instructions | knowledge | translate | summary |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 12002 | ashp | members-alone | 11/16 | 1/1 | 2/2 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 | — | 2/2 | 1/2 | 0/1 | 0/1 |

Seed 12002 (ashp, members-alone) notes: 196 min wall (22:13:23–01:29:46 PT, no restarts);
the table's columns map to the report's fields as sums=maths, tables="given data",
write-program/mend-program = the two code tasks split by kind, translate=languages,
summary=writing; the report's remaining field, understanding, passed 1/1 and has no
column above. Peak GPU temperature in the sitting window was 72 °C (monitor log,
00:14:34 PT), GPU load 0% throughout (CPU work), no throttling and no thermal
intervention. Full per-task seconds and by-field counts are in `hive-form.json`;
the sitting's own report is saved as `exams-12002-ashp.json` (the `.md` report on
ashp is 0 bytes — the sit log's tail shows a cp1252 UnicodeEncodeError on the final
print, END8 exit=1; the JSON is complete). Failed-task member artifacts are on this
VM under `ashp-artifacts/exam_12002/<task>/`.

## What was not run

- Seeds 12004–12009: the campaign queue (Q1-RUN-PLAN.md) — fresh trios in order
  12004, 12005, 12006, then 12007–12009 as continuation; status reported per trio.
- Seed 12003 roles and members-alone arms: never started, and will not be — 12003's
  members-first arm completed post-park (see the correction above) and the seed is
  closed as a flagged pilot; a trio built around it would not be a same-batch trio.
- Seed 12002 members-first and roles arms: not run — the existing members-alone arm ran
  on unverified code (`c256322`) outside a batch, so the red team ruled it a pilot
  rather than a trio arm (RT-1); fresh trios carry the comparison instead.
- Seed 12001 arms beyond the spike: not run (VM lane closed by measurement).
- Confirmation rerun (seed 12010): runs only after a verdict past the bar, before any
  build-in — one winning-arm sitting under the identical frozen config, reported as a
  confirmation, never as a claim trio (Q1-RUN-PLAN.md, Build-in).
- The GGUF engine configuration (not installed on this VM; see caveat) — the campaign
  pins the HF engine explicitly instead.

## Exact commands

The campaign's real commands (per FOR_MUSE condition 5 — Fable's side can rerun any arm
from this page alone). Sittings run on **ashp**, one full work copy per sitting, launched
detached by the lane apparatus (`q1-devops/LANE-RUNBOOK.md`); the launcher sets exactly
this environment and records it in the sitting's `RUN-METADATA.json`:

```
# on ashp, account ashp\muse — make the copy (once per sitting), then launch:
& D:\agents\muse\for-hive\q1-devops\make_copy.ps1 -Seed N -Arm <members-alone|members-first|roles>
& D:\agents\muse\for-hive\q1-devops\start_sitting.ps1 -Seed N -Arm <arm> -LauncherArgs "-PriceHours <3.3|5.5|8.5>"

# what the launcher runs inside the copy D:\agents\muse\for-hive\campaign\q1-sit-N-<arm>
# (cwd = the copy; chassis python; imports resolve to the copy — proven):
PY = D:\agents\muse\for-hive\q1-work\.venv\Scripts\python.exe
PINS (all arms): AGENT_TEAM_ENGINE=hf  HIVE_LIBRARY=0  PYTHONUTF8=1  PYTHONIOENCODING=utf-8
                 AGENT_TEAM_THREADS=8  OMP_NUM_THREADS=8  MKL_NUM_THREADS=8
                 HF_HOME=D:\agents\muse\for-hive\hf  PYTHONPATH=<the copy>
members-first : AGENT_TEAM_SOLO=2                          $PY training/exam.py sit --tasks 16 --seed N --empty-memory
members-alone : AGENT_TEAM_SOLO=2 AGENT_TEAM_SOLO_ALONE=1  $PY training/exam.py sit --tasks 16 --seed N --empty-memory
roles         : (neither)                                  $PY training/exam.py sit --tasks 16 --seed N --empty-memory
```

(The pre-campaign VM commands that stood here before plan v2 are superseded — the VM lane
is closed by measurement, seed 12001.)
