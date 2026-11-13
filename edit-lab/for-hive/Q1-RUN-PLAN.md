# Muse's work, Muse's side

# Q1 · Hardened run plan — which form of the working hive is better

**What I chose and why (Muse's call, per the governance Arnav set 2026-11-12):** Arnav approved
ashp for the Q1 sittings only (2026-11-13 ~10:09 PT), on the condition that a multi-agent red
team attack the design first and the design be developed from its findings — his full style.
Five red-team agents ran in parallel (measurement validity, statistics, harness integrity,
cost/schedule, lane discipline); their full reports are in `q1-redteam/RT-1…RT-5`. The red
team broke the naive design in four places; this plan is what survived. Where the red-team
agents disagreed, I ruled, and each ruling is marked with its reason. Fable advises; the
choices and the numbers are mine.

**v2 (2026-11-13, pre-launch):** Arnav's expansion landed on top of the red team — a DevOps
team (lane apparatus built and smoke-proven, `q1-devops/`), an Engineering team (harness
verdicts + the two adopted patches, `q1-engineering/`), and a Fable-approach team
(`FABLE-APPROACH.md`: Fable's *method* extracted and adopted as this campaign's operating
approach, staffed at higher manpower — see "Method adopted" below). v2 folds all three in:
the chassis delta (rows 11–12 + adoption record), the adopted method and staffing roster,
the build-in subsection with its pre-declared confirmation rerun (seed 12010), the losers'
ledger, the verification gate, and the G8/G9 caveats. Nothing in the frozen design — seeds,
rotation, bar, margins, queue — changed in v2.

## What the red team killed (naive design → this plan)

| # | Finding (source) | Consequence adopted |
|---|---|---|
| 1 | **Cache trap:** all arms share `runs/exam/exam_<seed>` and `sit_one()` silently returns an existing `exam.json` — arm B of a seed would return arm A's scores without running (RT-1 I-2, RT-3 I-2) | **One full work copy per sitting.** No two sittings ever share a checkout. A sitting's results can only be its own. |
| 2 | **No provenance in output:** sitting summaries record no form/engine/threads/machine; per-seed report files overwrite arm-over-arm (RT-1 I-1, RT-3 I-1) | Operator-level fix: per-sitting copies, a `RUN-METADATA.json` written by the launcher into every sitting (arm env, engine, threads, code hash, machine, start/end, restarts), and the report renamed `exams-<seed>-<arm>.json` at mirror time. (The original "zero chassis edits" stance is superseded by rows 11–12 below: two one-purpose patches were adopted after the engineering follow-up proved them necessary; both are inert under Fable's side's own configuration, so any arm remains rerunnable there.) |
| 3 | **Engine never pinned:** `AGENT_TEAM_ENGINE` defaults to `auto` and can flip if a GGUF stack appears (RT-1 I-3) | Launcher sets `AGENT_TEAM_ENGINE=hf` explicitly, plus `HIVE_LIBRARY=0` explicitly (RT-3: library read-back is gated by that var, not by `--empty-memory`), plus `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8` (kills both cp1252 crashes — report-time and in-sandbox; RT-3, RT-5 B-1). All recorded in RUN-METADATA. |
| 4 | **The statistics cannot carry the original claim:** the hinted effect is 1 task (seed 9007: 10 vs 9 vs 9); detecting it needs ≈42–60 trios. At 8 trios the detectable gap is ≈2.3 tasks, at 4 ≈3.2, at 3 ≈3.7 (RT-2) | Claim re-scoped before any run (below): large effects, or the pre-declared non-inferiority-plus-cost claim. No ranking claim below the achieved MDE₈₀, ever. |
| 5 | **The full 8×3 design does not fit the windows:** ≈135 planning-hours vs ≈36 machine-hours before Nov 16 at realistic availability (RT-4) | Trio-sequential queue with declared target/fallback/stretch (below). Fewer trios is a reported scope state, not a silent shortfall; 16 tasks per sitting is never cut. |
| 6 | **12002's existing arm cannot be reused** in a trio (RT-1 Q3: breaks the same-batch control rule). RT-4's cheaper "complete the 12002 trio" queue is therefore rejected | **Fresh trios on fresh seeds only.** The code question underneath is now settled empirically (2026-11-13, hash audit): all 243 `.py` files under `team/` and `training/` on ashp's q1-work are byte-identical to the VM's `942803d` copy — the `c256322` diff touches no executable code, so the pilots ran on this campaign's code. What still bars reuse is the same-batch rule itself (arms of a trio run together, in rotation, under one frozen setup), not a code difference. 12002 stands as a pilot. |
| 7 | **Seed 12003 is not a stopped partial — it completed** (RT-5 I-1, RT-1 C-1): after the ~03:05 PT park stop it was resumed by the Q1 stream's own restart machinery and finished 05:53 PT, 8/16, members-first; report hash-verified | The record is corrected in hive-form.md/json. 12003 is a **flagged pilot, excluded from every average** (RT-2 rule 9: provenance chain broken — two pre-park starts, a kill, a post-park resumption inside the parked window; Arnav's 10:09 approval covers sittings from that moment, not retroactively). It is never re-sat: in a shared checkout `exam.py` would skip all 16 tasks and counterfeit a sitting in seconds. |
| 8 | **No CPU temperature exists on ashp** (RT-5 I-2): ACPI zones return fixed nonsense; the only sensor is the GPU heatpipe proxy | Thermal law restated in enforceable terms (below): GPU-proxy gates + a throttling witness. The house tempwatch is dead (since Nov 12 22:08 PT) and restarting it is parked house work — not done under a sittings-only approval. |
| 9 | **A leftover monitor from the 12002 sitting is still running** on ashp (RT-5 I-3), and both old monitors are unbounded loops with no lifecycle | The new launcher claims/stops the lane's leftover monitor before first launch and ships a **bounded** monitor with pid file and a stop condition tied to the sitting's life. |
| 10 | **Members-first is structurally time-starved** (RT-3 B-1): members + roles fallback share ONE 2400 s subprocess budget per task; the other arms get 2400 s per phase | NOT "fixed" — that budget is part of the form as Fable's side ships and ran it (seed 9007's members-first had the same property); changing it would invent a fourth form. Instead, members-first sittings get the 5-number decomposition (below) so the starvation is visible in the data. Recorded as a caveat. |
| 11 | **The roles path crashes on ashp under the hf pin** (engineering follow-up, ENGINE-PROPAGATION.md): `Hive._run` → `cells.ensure_built()` builds the 24 missing GGUF cell files, flipping `cells/runtime.py:available()` to true — it never reads `AGENT_TEAM_ENGINE` — and the first cell call dies on `from llama_cpp import Llama` (not installed on ashp). **5 of pilot 12003's 8 failed tasks died this way**; a 6th (passed) task carries the same crash note. Unpatched, the roles arm and the members-first fallback would keep scoring platform crashes as hive failures | **Patch adopted (campaign chassis delta 1 of 2):** `q1-engineering/patches/cells-engine-hf.patch` — `available()` returns False and `ensure_built()` skips the GGUF build when `config.ENGINE == "hf"`. Proven at the resolution layer: the unpatched tree under the pin reproduces 12003's exact crash note through the identical call chain; the patched tree resolves everything to HF. Inert under auto/gguf (Fable's side's configuration, which has llama_cpp installed); under hf it only removes the crash — cells fall back to their designated HF holders, exactly as the chassis already behaves where GGUF files are absent. |
| 12 | **A member program's own file writes inside the sandbox get NEITHER encoding pin** (engineering, ENCODING-VERDICT.md): the pinned pair covers the two observed cp1252 crash sites (report-time via `PYTHONUTF8=1`; sandbox prints via `PYTHONIOENCODING=utf-8`, because `program_env()`'s PASS filter drops `PYTHONUTF8` from the sandbox child's env), but a member program's own `open().write()` of non-ASCII text inside the sandbox would still crash on cp1252 | **Patch adopted (campaign chassis delta 2 of 2):** `q1-engineering/patches/sandbox-pythonutf8.patch` — adds `PYTHONUTF8` to the sandbox PASS filter (one line). Inert where `PYTHONUTF8` is unset (Fable's side's configuration). Removes a platform artifact Fable's GitHub environment never produced; arm-symmetric. |

**Adoption record (2026-11-13, coordinator's ruling):** both patches applied identically to the
VM q1-work and ashp q1-work before trio 1, for all arms. Campaign code manifest (ordinal-sorted
SHA-256 rollup over `team/`+`training/` *.py, 243 files): unpatched chassis `5eb74e0c…` →
**patched campaign chassis `fb51cf44e430216844b86eaf57517391d3e92e97a3541e0c4531465824671730`**,
verified identical on the VM, the ashp chassis, and the remade 12004 copy. `config_diff.py`
re-run on the patched tree: PASS — the arms still differ in exactly the 7 SOLO/ALONE-derived
keys, nothing else. Engineering tests on the patched tree: 14 passed; the 2 "unpatched-baseline"
tests now fail *by design* — they stage their "before" tree from the live q1-work, which is now
patched (their failure is the adoption's signature; the pristine baseline is recoverable from
git HEAD `942803d` on the VM copy). The DevOps apparatus (q1-devops/LANE-RUNBOOK.md) is built
and smoke-proven (clean run + kill/resume run, mirror 12/12 hash-verified both times); the
leftover 12002 monitor is stopped and logged; the 12004 draw is recorded (16 tasks, no
unwinnable German "museum" draw).

## Frozen configuration (every sitting, no exceptions)

- Machine: ashp only, account `ashp\muse` only, work area `D:\agents\muse\for-hive\campaign\`.
- One work copy per sitting: `q1-sit-<seed>-<arm>`, robocopied from the single hash-verified
  chassis before the sitting starts. **Campaign chassis = Fable's side's `942803d` + the two
  declared patches (table rows 11–12), manifest rollup `fb51cf44…` (243 files)** — verified
  identical on the VM, on ashp's q1-work, and in every sitting copy (the launcher/make_copy
  gate refuses a copy whose rollup differs). The unpatched `942803d` base was verified
  2026-11-13: 243/243 `.py` files under `team/` + `training/` byte-identical between ashp
  and the VM.
- Command (from FOR_MUSE, unchanged): `python training/exam.py sit --tasks 16 --seed N --empty-memory`
- Arm env — members-first: `AGENT_TEAM_SOLO=2`; members-alone: `AGENT_TEAM_SOLO=2` +
  `AGENT_TEAM_SOLO_ALONE=1`; roles: neither.
- Pinned env for all arms: `AGENT_TEAM_ENGINE=hf`, `HIVE_LIBRARY=0`, `PYTHONUTF8=1`,
  `PYTHONIOENCODING=utf-8`, threads = 8 (the ashp sittings' established setting).
- Models: the ashp HF cache as used by the 12002/12003 sittings (roles Qwen3-1.7B,
  members Qwen2.5-Coder-1.5B-Instruct, bf16). No downloads, no installs.
- Any forced change to any of the above is a **batch break**: completed trios stand,
  the break is printed beside the result (RT-2 rule 2).

## Method adopted from Fable's side (Muse's reading, 2026-11-13)

*Full extraction, traces, and the gap list: `FABLE-APPROACH.md`. Learned read-only; the
one-way valve stands — nothing was written to Fable's side.*

This campaign runs Fable's loop, staffed at company scale: decompose into numbered measured
questions; price/spike before committing; run arms as same-batch controls on fresh, never-read
seeds; judge by a bar stated before the run; read failed tasks' artifacts — never scores
alone — to find causes; move reversible defaults on evidence with the numbers written into
the change, but make claims only past the bar; build in only what survives a rerun on unused
material; and write down what did not hold, with its numbers, so nobody runs it twice. Two
tiers are kept distinct throughout: a *default* may flip on a fresh-seed hint if it is
reversible and never worse on cost (Fable's members-first default, commit `61fb325`, is the
model); a *claim* may not. Times are campaign costs, not measures of a form: Fable's side
recorded the same trivial sum at 22 s and 594 s under contention (same code, seeds 9005/9006),
so wall-times here — sequential, rotation-balanced, single-lane — are reported beside scores,
never as an isolated speed ranking. The chassis base is Fable's side's `942803d`; no Fable-side
fix for the red team's defects exists in any later ref (`942803d..c256322` changes only
FOR_MUSE.md/HANDOFF.md), so the plan's operator-level fixes stand — plus the two declared
patches (rows 11–12), each inert under Fable's side's own configuration and published in
`q1-engineering/patches/` so any arm can be rerun there exactly.

**Staffing (the method at higher manpower than Fable can field — Arnav's directive,
2026-11-13):** the lane stays serial; everything around it is staffed. **Sitting Owner** —
one named agent per sitting, recorded in RUN-METADATA before launch; sole restart authority
(the VM watchdog acts only as the Owner's pre-authorized machinery, under the Owner's standing
instruction, identical env, max 3 relaunches; any manual restart is the Owner's alone, and
ownership transfers only in writing in the sitting record — the 12003 rule). **Artifact
Readers** — read every failed task's member programs/outputs the moment its mirror lands,
classify against the standing taxonomy, count causes. **Row Verifiers** — one per trio, never
that trio's Owner or a Reader; independently re-derive every page row from the raw records
before the page updates. **Builders** — two standing (Lane, Records); tooling changes only at
trio boundaries (a mid-trio change is a batch break). **Plan Keeper** — updates the page only
at trio boundaries, only with Verifier-signed rows; owns claim state and the losers' ledger.
**Coordinator** — rulings only; does not own sittings, read for the record, or verify.

## The claim, the bar, the analysis — declared before any run

**Primary pair (named in advance): members-first vs members-alone** — the live question,
since Fable's side made members-first the default on a 1-task hint: does the roles fallback
earn anything over the members alone? Secondary pairs (members-first vs roles,
members-alone vs roles) are Bonferroni-corrected.

**Primary analysis:** pooled McNemar on discordant task pairs for the primary pair; paired
mean difference with a t-interval reported alongside; the stratified common-effect
(kind-as-stratum) estimate as the supporting analysis.

**The bar, pinned in writing (RT-2 rule 5):** a difference is claimed only if
|mean paired gap| > 2 × SE of the mean paired difference. Fable's ">0.01" is dropped as
vacuous. The MDE₈₀ for the k actually achieved is printed next to any gap, claimed or not.

**One-sentence claim the finished design supports** (RT-2 §5, adapted to the fresh-seed
campaign; the sentence for the achieved k is the one that runs, verbatim in structure):

- At the achieved k: *"Across k fresh paired seeds ([seed range]; 16k tasks per form, same
  tasks, same batch), [form X] averaged [D̄]/16 more tasks than [form Y] (paired 95% CI
  [lo, hi]) — a large-effect difference this design can certify; no per-kind difference is
  established at these counts, and differences smaller than ≈[MDE₈₀] tasks would have been
  invisible to it."*
- If the gap is below threshold (the likely outcome if the true gap resembles the 1-task
  hint): *"…the three forms are indistinguishable within ±[CI half-width] tasks per 16:
  this run rules out any advantage larger than ≈[MDE₈₀] tasks for any form, and the 1-task
  ordering seen on seed 9007 remains within noise."*

**Cost claim, pre-declared (RT-2 rule 11):** members-alone is tested for non-inferiority
within a margin of **3 tasks per 16** against the best scorer, with wall-time per sitting
recorded as a first-class outcome beside every score. No post-hoc cost stories.

**Per-kind reporting:** raw `x/n` counts per kind per form, pooled across trios, printed as
a descriptive appendix labelled *"hypothesis-generating only — n = 1–2 per sitting; no
kind-level conclusion is supported."* No per-kind winners. The only pooled breakdown with
claims attached is the pre-registered macro-bucket split (defined now, before any new
result is seen — RT-2 §3): **programmatic** (code 2 + given data 1 + maths 1 + units 1 = 5),
**retrieval** (knowledge 2 + dates 2 + live facts 1 = 5), **language-and-instruction**
(instructions 2 + languages 1 + understanding 1 + websites 1 + writing 1 = 6) — and even
buckets support only large claims at k ≤ 4.

**Members-first decomposition (RT-1 Q4):** every members-first sitting is also reported as
five numbers — total; fallback rate (tasks where the roles took over); member-phase pass
rate; rescue rate (roles passed after the members disagreed — a lower bound, since the
members might have passed with more time); members' agreed rate. Extracted from the
sitting's own exam/board records at mirror time.

**Re-estimation gate (RT-2 rule 10):** after the first two complete trios, σ_D is
re-estimated from observed discordants and the power table re-issued; if MDE₈₀ at target k
then exceeds 3 tasks, the claim re-scopes to non-inferiority-plus-cost before more sittings
run.

## Pilots — excluded from every average, rate, and pooled count (RT-2 rule 9)

- **12001** (VM spike): 4/16 recorded, all 2400 s timeouts, zero member artifacts. A machine
  measurement, not a sitting. Uses: pricing/feasibility, process evidence.
- **12002** (ashp, members-alone, 11/16, 196 min, code `c256322` unverified): pilot.
  Uses: per-form pricing anchor, draw/task evidence, hypothesis generation.
- **12003** (ashp, members-first, 8/16, completed 2026-11-13 05:53 PT after interruption
  and post-park resumption, code `c256322` unverified): flagged pilot. Uses: same as 12002,
  plus the process lesson that produced this plan's ownership rules. **Never re-sat.**

## Run queue (trio-sequential; rotation ABC/BCA/CAB per RT-2 rule 1)

Prices (planning, from RT-4): alone 3.3 h (2.5–4.5) · members-first 5.5 h (3.5–8.0) ·
roles 8.5 h (6.0–11.0) · trio ≈ 17.3 h.

| # | sitting | price | cum. | note |
|---|---|---|---|---|
| 1 | 12004 × members-alone | 3.3 h | 3.3 | also prices 12004's disagreement set |
| 2 | 12004 × members-first | 5.5 h | 8.8 | primary-pair arm |
| 3 | 12004 × roles | 8.5 h | 17.3 | **trio 1 complete; ROLES GATE** — systematic roles failure → stop and report |
| 4 | 12005 × members-first | 5.5 h | 22.8 | rotation B |
| 5 | 12005 × roles | 8.5 h | 31.3 | |
| 6 | 12005 × members-alone | 3.3 h | 34.6 | **trio 2 complete → σ_D re-estimation gate; declared fallback k = 2** |
| 7 | 12006 × roles | 8.5 h | 43.1 | rotation C; **plan target k = 3** |
| 8 | 12006 × members-alone | 3.3 h | 46.4 | |
| 9 | 12006 × members-first | 5.5 h | 51.9 | trio 3 complete |
| 10+ | 12007 trio (alone/first/roles), then 12008, 12009 | 17.3 h ea | — | stretch / post-window continuation toward the full 8 |

**Declared in advance (RT-2 rule 3):** target k = 3 fresh trios; time-box fallback k = 2;
stretch k = 4. No adding seeds because a gap "is close"; no stopping early because it
"looks decided." Re-price members-first and roles from trio 12004's measurements before
committing past trio 2. No new sitting starts after Sun Nov 15 18:00 PT unless it closes
an open trio.

## Per-sitting procedure

**Pre-launch checklist (from RT-5, adopted):**
1. On ashp: zero python processes box-wide; zero lane powershell/cmd (incl. any leftover
   monitor — claim and stop it; it is the lane's own process); no other heavy job.
2. Count `exam.json` in the target copy: a fresh copy must show 0. (16 = done seed, never
   launch; 1–15 = resume only under identical arm env — see stop/resume.)
3. Thermal start gate: GPU proxy ≤ 65 °C and `% of Maximum Frequency` at full under a
   short load sample; disk space for one more run dir (~1 MB) + chassis copy (~0.4 GB).
4. Verify the copy's code hash set matches the frozen chassis manifest; write
   RUN-METADATA.json (arm, env pins, threads, code manifest hash, machine, start time).
5. Confirm no VM-side process references the campaign (no second owner — the 12003 lesson).
6. **Engine-evidence gate (added 2026-11-13, plan v2.1 — prompted by Fable's side's
   fallback discovery, their commit 7171805):** a sitting counts only if its records
   affirmatively show the serving stack: (i) RUN-METADATA carrying the pinned env
   (`AGENT_TEAM_ENGINE=hf`, arm vars, threads, manifest rollup); (ii) the sit log's START
   line matching it; (iii) the chassis code-path proof at that rollup (`llm.py`:
   `gguf_available()` is False by construction under `ENGINE=hf`; members serve
   `CODER_MODEL`, roles serve `BASE_MODEL`, both via the PyTorch loader); (iv) the lane's
   HF cache inventory (which models exist on ashp to be served at all). A sitting whose
   records cannot show this is excluded as unprovenanced, like a pilot — regardless of its
   score. The proof for the live 12004 sitting is written at `ENGINE-PROOF-12004.md`
   (verdict: the declared PyTorch stack serves; no silent fallback; the GGUF models cannot
   be served on ashp in any mode — no GGUF repos cached, `llama_cpp` absent). Each trio's
   Row Verifier re-derives this gate for all three sittings before the page updates.

**Monitor (bounded, pid-filed, dies with the sitting):** samples GPU temp + CPU
`% of Maximum Frequency` every 30 s to the sitting's monitor log.
- **Hold** (pause new task starts via the STOP file, resume when clear): GPU ≥ 78 °C.
- **Abort** (STOP file, then verify zero python): GPU ≥ 80 °C on 2 consecutive samples,
  OR throttling witness: `% of Maximum Frequency` < 80 % sustained 5 min under load.
- These numbers replace the unenforceable "CPU 88–90 °C" line for this lane; they are set
  from the lane's own evidence (12002 peaked at 72 °C GPU in-sitting with load 0 % GPU —
  CPU work warms the shared heatpipe slowly; 78/80 leaves margin below the house abort band).

**Stop / resume:** clean stop = drop the `STOP` file in the sitting copy (the hive's own
kill switch, `team/stop.py`); taskkill by pid-file tree only as fallback; `taskkill /IM
python.exe` is banned (box-wide). Restart authority belongs **solely to the sitting's named
Owner**. The VM watchdog is the Owner's pre-authorized machinery: on a confirmed death
(2 consecutive dead probes, zero python box-wide) it deletes any poisoned in-progress task
dir (a task dir with no `exam.json` is re-run by the harness; one with an `exam.json` is
final) and relaunches **once per incident, max 3, under identical env**, then stops and
reports — it never launches while any python lives on ashp (smoke-proven, including a
fail-closed first attempt). Any manual restart is the Owner's alone, under identical env,
same poisoned-dir rule. Restarts are recorded in RUN-METADATA — with the semantics the smoke
exposed: `restart_count` counts relaunch *attempts* (a failed attempt that never started a
process still bumps it), so reports quote the sit log's START lines beside the count, and
true wall span comes from the logs (RT-5 B-2: report JSON understates interrupted spans).

**Mirror (incremental during the sitting, final gate before it is reported):** the DevOps
mirror puller copies records back to this VM *per task, as tasks land* (so Artifact Readers
start while the sitting still runs), and completes a final verified pass after END —
`exams-<seed>-<arm>.json` (renamed report), the full `runs/exam/exam_<seed>/` dir, the sit
log, the monitor log, RUN-METADATA.json — into `for-hive/campaign-records/<seed>-<arm>/`.
Transport gate (the Owner's): SHA-256 of every file matches the ashp original,
`exam.json` count = 16, `MIRROR-STATUS.json` shows `complete: true`. Budget note (DevOps
smoke): the proxy costs ~4 s/file, so a cold full pass over a real ~300-file run dir takes
~20 min — incremental pulls during the sitting keep up; only a late watchdog start pays the
cold-pass cost. A sitting is never reported from half-copied records. The transport gate is
not the verification gate: trio rows reach the page only after the Row Verifier's
re-derivation (see Reporting).

## Caveats carried (recorded, not silently borne)

- **Ashp ↔ GitHub incomparability (RT-1 Q2):** different engine (HF/PyTorch vs llama.cpp
  GGUF), different member/brain models (Coder 1.5B vs 7B; Qwen3-1.7B vs brain 4B). Totals,
  per-kind rates, per-task pairing and times are NOT comparable across the two engines;
  only a ranking, read as a hypothesis with engine as a blocking factor, crosses over.
  All claims in this campaign are internal to the ashp/HF batch.
- **Sampling is unseeded on every engine** (RT-1 I-6, RT-3): each sitting is one stochastic
  draw; arms are paired by task and seed, not by sample. The paired analysis is the
  correct handling; 1–2 task gaps are noise by construction.
- **Unwinnable-by-construction tasks exist** (RT-3 I-3): the German "museum" translation
  draw forbids the very word the correct answer needs. The chassis is not edited (any edit
  breaks rerun-comparability with Fable's side); the bug is form-symmetric, so paired
  comparisons stand; affected sittings are footnoted from their seed draw
  (`exam.py show --seed N`), and the bug is reported on the Q1 page as a fault found for
  Fable's side. Seeds are never swapped because of their draw — that would be tuning on
  the test.
- **Agreement is label-blind in the members' `same()` check** (RT-3, empirically confirmed:
  label-swapped answers count as agreement) and number-subset-based — this is part of why
  the mend-a-program trap confirms. It is the members' shipped behaviour, identical across
  member arms; recorded as a mechanism caveat behind any members-vs-roles gap.
- **Within-sitting recall:** `--empty-memory` empties memory between sittings (verified),
  but inside a sitting the roles' recall reads earlier tasks' reports — the form's design,
  identical on GitHub. Not a leak between arms or seeds.
- **Roles-arm website handicap — VERIFIED at setup:** Playwright Chromium is **absent** on
  ashp (checked 2026-11-13; also absent on the VM), so the roles arm's browser specialist
  cannot drive a real browser while members write programs — an asymmetric handicap on
  ≤2/16 tasks (the two websites tasks per draw). **Not** fixed by installing anything
  (sittings-only scope; identical environment across arms outranks a mid-design fix).
  Seed 12004's draw carries the standard 2 website tasks; no draw is ever swapped.
- **Wall-time comparability (Fable's side's own warning):** wall-times in this campaign are
  sequential, rotation-balanced, single-lane costs. Per Fable's side's record (the same
  trivial sum at 22 s and 594 s under contention, same code, seeds 9005/9006), they are
  reported as campaign costs beside scores and are never read as a form's isolated speed —
  including inside the pre-declared non-inferiority-plus-cost claim.
- **The loosened `same()` in the frozen chassis:** chassis `942803d` already includes
  Fable's side's loosened agreement rule (`725b202`, derived from seed-9005 fault-finding:
  near-numbers within 0.051; prose word-overlap threshold 0.6 → 0.4), unmeasured on any
  claim seed when adopted there. These fresh trios are its first claim-seed measurement;
  agreement-rate differences between member arms and Fable's side's GitHub sittings must be
  read with that in mind.
- **Campaign chassis delta:** the two adopted patches (rows 11–12) are the campaign's only
  code divergence from `942803d`. Each is inert under Fable's side's configuration (patch 1
  activates only under `ENGINE=hf`; patch 2 only passes a variable Fable's runs never set),
  each removes a platform artifact that environment never produced, and both are published
  (`q1-engineering/patches/`) with the campaign manifest rollup `fb51cf44…` so Fable's side
  can reproduce the exact campaign code. The pilots (12002/12003) ran unpatched: 12003's
  score carries the cells-crash artifact in 5 of its 8 failures — one more reason it is a
  flagged pilot, never an average input.
- **Timeouts** are distinguishable only via the per-task `note`; per-kind counts footnote
  timeout counts per sitting so a timeout is never silently read as a genuine fail.

## Reporting

Per completed sitting, reported **by its Owner**: score /16, wall span (from logs, with the
sit log's START lines beside any restart count), restarts, thermal peak, mirror verification
(transport gate). Per completed trio: the per-form table + per-kind counts appendix +
members-first decomposition + a **failure-cause table** (every failed task classified by the
Readers from its artifacts against the standing taxonomy — Fable's five member-failure kinds
plus timeout / encoding / no-artifact / agreement-on-wrong-values — causes counted per form,
feeding the Q2 autopsy continuously) + updated claim state (which sentence the achieved k
licenses, with MDE₈₀). The Q1 page (hive-form.md/json) is updated **only at trio boundaries,
only by the Plan Keeper, and only with rows the trio's Row Verifier has independently
re-derived from the raw `runs/exam/exam_<seed>/` records** (pass recount, per-kind recount,
decomposition, wall span from logs) — the Verifier is never that trio's Owner or a Reader,
and a discrepancy stops the page, not the lane. The page carries the pilots, the caveats,
and the stopping state exactly (RT-2 rule 12).

## Build-in — what a verdict changes (declared before any run)

A verdict on a page is not an improvement; this subsection states in advance what each
licensed outcome changes on Muse's side, Fable-style (default flips carry their numbers in
the change, per commit `61fb325`):

- **(a) Members-first wins past the bar** (primary pair): members-first becomes Muse's
  side's default form, in the serving/ask path the Records Builder names at build-in time,
  with the trio numbers written into the change.
- **(b) Members-alone non-inferior within 3/16 of the best scorer at lower wall cost**:
  members-alone becomes the default first form; members-first/roles become the escalation.
- **(c) Indistinguishable within the achieved CI**: no default changes — and that non-change
  is itself recorded on the page with the MDE₈₀, so nobody re-runs the question to rediscover it.

**Confirmation rerun, pre-declared (before build-in, mirroring what Fable's side says it
will do with our result):** after a verdict past the bar and *before* any build-in under
(a)/(b), one winning-arm sitting runs on the first unused fresh seed — **12010** unless
already consumed — under the identical frozen config (patched chassis, pins, rotation slot
n/a), owned and mirrored as a campaign sitting but reported separately as a confirmation,
never as a claim trio. **Collapse rule, pinned now by the Coordinator, before any verdict
exists:** the win fails to hold if the confirmation score falls below the winner's
per-sitting mean across the achieved trios minus the achieved MDE₈₀. Build-in proceeds only
if the winner does not collapse; if it collapses, the verdict is written down as not holding,
with its numbers, in the losers' ledger.

**Losers' ledger:** `for-hive/q1-losers.md` (Muse's work, Muse's side), owned by the Plan
Keeper, seeded at adoption with: the VM lane (12001: 4× 2400 s timeouts, zero artifacts);
12002-as-trio-arm (refused — batch rule); re-sitting 12003 (counterfeit risk via the cache
skip); the library-on form (Fable's side's seeds 9002/9003 numbers); the unpatched chassis
on ashp (cells-crash class, 5 of 12003's 8 failures). Standing rule: every closed trio
appends its losing readings, with numbers, before the next trio launches — so nobody runs
them twice.
