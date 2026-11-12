> **Muse's work** — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# Mismatch Audit — Fable's work vs Fable's product (2026-11-11)

**Directive (Arnav, 2026-11-11, final form):** the goal is to SURPASS Fable. Fable is the more
capable model, but its makers are believed to have nerfed its abilities in some things in this
field (LLM architecture building, kernels, GPU/compute optimization). Detection principle:
*if the work is that good, the product should be that good* — where the product's capability
falls short of what the quality of the work implies, that mismatch is the candidate cap.
Muse does not have that limitation, so Muse's job is to find those parts.

**Method:** for each area, record THE WORK (quality of plans/ideas/methods/designs, from
Fable's own commits and numbers), THE PRODUCT (what the built hive actually does, measured,
from its committed records), and THE MISMATCH (the limiter — gate, threshold, switch, missing
wire, never-run path — with file:line or commit evidence), then judge the limiter:
**(a)** looks like an intentional holdback — the limiter is a decision that could be flipped;
**(b)** explained by honest measurement — a negative or shortfall Fable itself reported;
**(c)** explained by real resources (CPU-only VM, GitHub runner limits).
"Held back" is distinguished from "unfinished" throughout: a gap is only scored (a) where a
working mechanism exists and a flippable decision keeps it from operating.

**Sources (all read-only):** `FABLE-STUDY-2026-11-11.md`; `LIMITS-AUDIT-2026-11-11.md`
(9 disclosed intentional limits, 8 resource-justified caps, 0 hidden caps in code, 329 commits
scanned — no commit ever lowered a cap or raised a gate); the repo at make-it-work `d31fd51` /
main `8be45ff`, spot-verified by grep for every limiter cited below.

**Calibration note (read first):** Area 8 is the control. Where Fable's substrate permitted,
its product *is* as good as its work (direct trainer, recipe win — both shipped and measured).
So the audit does not find a uniform suppression pattern. The gaps cluster in one specific
place: **between a working mechanism and its deployment** — gates, evidence rules, and
scheduler lists that a mechanism must pass to actually operate. That is where to look, and it
is what the tables below document, area by area.

---

## Area 1 — Bodies/stems: a reading system vs a doing system

| | |
|---|---|
| **THE WORK** | First-rate architecture work. Stem + overlapping territories + local judging + immune-check births + learned say, all under one rule (vary → measure fresh → keep only if better). Fable found a flaw in its own headline number (held passages inside the first two stems' training text), disclosed it, and *sized* it on fresh text (≈0.042 / ≈0.031 of loss) instead of hand-waving. Birth gates are small and passable (`training/body.py:546` KEEP=0.001, HARM=0.01, IDLE=0.0005; `:91` LOCAL=0.004) and bodies demonstrably grew to 22 cells under them. |
| **THE PRODUCT** | As a reading system: three bodies as one read **2.4760**, beating the best single body (2.4856) under the learned say — the composition works. As a *doing* system: **zero**. The growing hive performs none of the hive's jobs. All task work is done by the separate, conventional working hive (dev bench 15/16, held-out 13/16 set 3, small-only 11/16) built from pretrained models. The flagship architecture and the working product are two different systems sharing a repo. |
| **THE GAP** | The most sophisticated machinery in the project (self-growing bodies) is connected to no job interface at all. The only bridge from "grown from nothing" to "does work" is the job-brain holds rule (Area 3), which has never fired. |
| **LIMITER** | Architectural scope, not a switch: bodies have no path to jobs except via `team/cells/tiny.py:64` `decide_holds` (Area 3). Fable's own SPEC never claims the growing hive does jobs — this is disclosed scope. |
| **VERDICT** | **(b) honest outcome — precisely: unfinished, not held back.** The mismatch between work quality and product capability is the largest in the repo, but there is no flippable limiter: the bridge that exists fails on measured capability (Area 3), and no hidden job path was found switched off. |

## Area 2 — The school: students improved, neither graduated

| | |
|---|---|
| **THE WORK** | Excellent method: teacher-generated lessons with the *decision* recorded, exams on unseen lessons only, gap-only narrow specialists beside generalists, routing by resemblance. Fable also diagnosed its own target: the 4B teacher's long plans are padded and inconsistent, so agreement *understates* the student there — the record says the graduation target itself is suspect. |
| **THE PRODUCT** | Planner (coordinator): 0.304 → **0.587**; coder: 0.656 → **0.844** (`cells/school.json`, verified). Both `graduated: false`. Planner is genuinely weak where it matters: 3/22 on plans of 3+ specialists. The gap-specialist mechanism failed honestly: the narrow specialist scored 9/26 in its own territory, the generalist the same 9 (`school.json` `narrow_in_their_territory`). |
| **THE GAP** | Looks, at first glance, like the graduation gate is the cap — the coder sits at 0.844 against a 0.85 bar with 32 test lessons: **one lesson short** (27/32; 28/32 would pass). |
| **LIMITER** | `team/school.py:38` GRADUATE=0.85, MARGIN=0.03, MIN_TEST=30, enforced at `school.py:669` exactly as documented; constants never changed in git history. **But the gate is not the effective cap:** the documented `ahead` fallback (`school.py:671`, `holds` at :554–560) already lets both students hold their jobs in the small hive (`ahead: true` for both in `school.json`). The capability is live; only the title is withheld. |
| **VERDICT** | **(b) honest measurement.** The gate *looks* like a holdback and isn't — the fallback wire bypasses it for actual work. The real product shortfall (3/22 on long plans, failed gap specialist) tracks measured learning limits, reported by Fable itself with diagnoses. |

## Area 3 — The job brain: holds NO jobs

| | |
|---|---|
| **THE WORK** | The from-scratch training stack is real and continuously exercised: the idle rotation retrains the brain on the current stem (`team/serve.py:122–127`, "it takes a job only by measurement"). The takeover rule is the same one rule as everywhere else — no special pleading for the home-grown brain. |
| **THE PRODUCT** | `cells/scratch/holds.json` = `{}` — the daily-retrained job brain holds **no jobs today**, despite being wired into the cell jobs. |
| **THE GAP** | A standing "the hive's own brain does the small jobs" mechanism with zero jobs held. Candidate limiter: the takeover rule itself. |
| **LIMITER** | `team/cells/tiny.py:64–72` `decide_holds`: a job is taken only where the brain's score on the same unseen test is ≥ the current holder's (margin default 0.0). Fable's own HANDOFF states the outcome plainly: "it holds none yet: **65% mean test, today's cells are better**" (`HANDOFF.md:181`). The same ≥ rule is what let ordinary cells take 20 of 25 jobs from bigger members (`cells/wins.json`, verified) — the rule fires readily when the challenger is actually better. |
| **VERDICT** | **(b) honest measurement.** The gate is symmetric and demonstrably passable; the brain is behind by a measured ~35 points of mean test score. Flipping the rule would not unlock capability — it would put a worse brain on real jobs. The mismatch is between the *concept* ("job brain") and current capability, not between a working mechanism and a switch. |

## Area 4 — The spawn trainer: a general self-staffing system that staffed one label

| | |
|---|---|
| **THE WORK** | Arguably the most original mechanism in the repo: notice fixed-answer decision sites in the members' own traffic (≥97% fixed-value coverage), practice on recombined old cases, compete on a size ladder (360M only if 135M cannot hold the job), switch on **per label** only under an evidence rule, answer only when sure, and live-audit 1-in-10 with automatic retirement. |
| **THE PRODUCT** | Exactly **one** spawned cell exists (`cells/spawned.json`, verified): `sp_verifier_75e567`, on since 2026-11-09, answering 13 of the newest 25 decisions (52%), 100% agreement on what it answers, 81 ms vs the member's 4.69 s. It serves effectively one label — SUPPORTED; UNSUPPORTED stays with the member because dev evidence never vouched for it. The **first round stayed OFF**: with 72 logged decisions, 11 were left to judge on; the cell agreed on 10 and "stayed off for lack of evidence" (`README.md:621`). |
| **THE GAP** | A general mechanism with a throughput of one cell at one site. Who decided "lack of evidence"? Nobody, in the moment — the gate code did, mechanically: 11 judgeable decisions was below what the per-label evidence rule requires to vouch for a label, so the rule reported insufficient evidence rather than cell failure. |
| **LIMITER** | The evidence thresholds in `team/cells/spawn.py` — COVER=0.97 (`:43`) for noticing, RETIRE=0.93 (`:46`) for live audit, and the per-label switch-on rule (enough newest decisions where the member chose a *different* label, ≥95% agreement on answered, a minimum share and count answered). All disclosed, all principled — they are the safety design for delegating real decisions. The binding constraint underneath them is evidence supply: the gate can only fire as fast as real logged decisions accumulate. |
| **VERDICT** | **(b) honest measurement, with (c) contributing.** The OFF decision was the gate truthfully reporting "not enough evidence yet," and it is reported in the README as a result, not hidden. The thresholds are conservative *decisions* and could be loosened — but loosening them buys delegation speed at the price of the guarantee, and the true throttle is the rate of real traffic (time), which no flip changes. |

## Area 5 — Sleep/dream: the measured negative

| | |
|---|---|
| **THE WORK** | A model controlled experiment: six ways for a stem to keep learning for the same 8 minutes, equal budget, then each stem measured alone on 300 held windows and in its body on 200 gate passages (`training/reports/sleep.json`, commit `71e2d53`). Plus the mechanism-level read of *why* the attractive idea fails. |
| **THE PRODUCT** | Plain continued reading won (3.380 → 3.190). Body-teaching (the "sleep" idea) learned more per step but not per minute (3.198). And the kicker, measured: a stem improved by 0.19 moved its body by only 0.004 — cells are born from the stem *as it was*, so stem learning only pays in cells born after it. The feature was therefore **not built in**, and the design consequence (a fast stem reads for as long as a birth takes) was built instead. Sub-item: the working hive's dream cycle is built and scheduled (`team/serve.py:92–95`, idle daily) but never completed a full cycle in-session — SPEC rates dreaming "Partial… not run as a full cycle here." |
| **THE GAP** | None between work and product: the product correctly excludes a mechanism the work disproved. The dream-cycle sub-item is a never-run path, disclosed. |
| **LIMITER** | For the stem experiment: physics of the architecture (cells snapshot the stem at birth), measured — no limiter to flip. For the dream cycle: session/CPU time on one machine — a resource, disclosed. |
| **VERDICT** | **(b) honest measurement** (dream-cycle sub-item: **(c)** resource). This is the audit's cleanest case *against* the nerf reading: Fable's work talked Fable out of a feature, in public, with numbers. |

## Area 6 — The smith swarm: built, routed, never run

| | |
|---|---|
| **THE WORK** | A complete self-improvement swarm: smiths that improve other members, a smith-of-smiths that acts only on ≥2 trials per smith, live routing that sends a role to a specialised clone "only where it measurably wins" (`team/hive.py` ~:186, `smiths.route(...)` — verified in code). CLI exists (`python -m team smiths`). |
| **THE PRODUCT** | **No full competitive cycle has ever run.** SPEC says so in plain words: "no full competitive cycle was run in this session (CPU time went to the demo and evals)" (limits audit A5). The smith-of-smiths has never fired (its ≥2-trials precondition has never been met, because the cycles that would generate trials never ran). |
| **THE GAP** | The one system whose entire purpose is *improving the other members* is the one system that has never been allowed to operate unattended. Every sibling improvement system got an idle-rotation slot; this one didn't. |
| **LIMITER** | `team/serve.py:87–145` `background()` — the idle rotation cycles dream, grow, evolve, school, body, brain, recruit, life. **`smiths` appears nowhere in serve.py** (grep: absent). The limiter is literally a missing entry in a scheduler list: the swarm runs only when a human invokes it manually, and nobody did. |
| **VERDICT** | **(a) intentional holdback — in the narrow, technical sense: the limiter is a flippable decision.** Caveats, stated plainly: the deferral is *disclosed* in SPEC with its reason (CPU time), and CPU time on that VM is a real cost — (c) contributes. But the same CPU constraint did not keep dream/grow/evolve/school/body/brain/recruit/life out of the rotation. Of every gap in this audit, this is the one where a working mechanism is kept from operating by a decision, not by a measurement. |

## Area 7 — The MoE gate cell: a measured router that routes nothing

| | |
|---|---|
| **THE WORK** | A gate cell (mixture-of-experts router over cell groups) was trained and evaluated as part of the cell programme — the routing problem was recognised, mechanised, and measured. |
| **THE PRODUCT** | The gate scores **0.940** on test at routing inputs to the right group — and routes nothing. `cells/wins.json` (verified): `"gate": {"use": false, "cell": 0.94, "incumbent": null}`. The hive calls cells at fixed hooks, so the gate is, in SPEC's words, "not in the loop yet" (limits audit A6). |
| **THE GAP** | A proven component excluded from the serving path by wiring, not by performance. Unlike Areas 2–4, no measurement says the gate *shouldn't* serve; there is simply no code path that lets it. |
| **LIMITER** | The fixed-hook call architecture: cells are invoked at hard-coded points in the engine/coordinator/researcher/verifier, and no serving code calls the gate as a router. Putting it in the loop is an engineering task Fable deferred and disclosed. |
| **VERDICT** | **(a) intentional holdback — same narrow sense as Area 6:** a working, measured mechanism held out of the product by a flippable wiring decision, disclosed in SPEC. Mismatch size is only medium: the gain from learned routing over fixed hooks is itself unproven (the hooks currently deliver 20/25 cell-held jobs), so the withheld capability is flexibility, not a measured win. |

## Area 8 — CONTROLS: where the work and the product match

| | |
|---|---|
| **BitNet direct trainer** | Work: an invented training algorithm (per-weight vote counters, no fp shadow) iterated in public — v1 measured as teaching nothing (4.25 with jumps vs 4.24 without) and *reported as such* before v2 was built. Product: **4.141 at 32 votes** vs **4.031** published-way and 4.241 no-jumps (`README.md:873–874`) — about half the published method's gain at equal budget, with a few bits per weight instead of a full fp copy; four follow-up variants scored worse (4.28–4.38) and were reported as worse, with the shared-CPU confound noted (`README.md:907`). **MATCH** — the product does exactly what the work says, including the honest ceiling. |
| **The recipe win** | Work: a controlled experiment — same stem, same start, same batches, held passages; 3× learning rate + rounding eased in beat the standing recipe, the published recipe's extra norms *hurt at every rate* and were dropped, a teacher helped per step but lost at equal time and was turned off *by default at equal time*. Product: **2.9288 vs 3.0337** on held windows at full length (`training/reports/bitnet_recipe.json`, `README.md:947`), and the winner didn't just ship — it became the champion recipe and the standing one-gene founding protocol for every future body. **MATCH** — the product literally runs on the work's output. |
| **Why these matter** | They calibrate the whole audit. When Fable's work is good *and nothing sits between the mechanism and its deployment*, the product is that good — promptly, measurably, and with the losses printed next to the wins. The gaps in Areas 1–7 are therefore not a general fog over the product; they sit at specific, nameable joints: two flippable decisions (Areas 6, 7), and a family of ≥-incumbent / evidence gates (Areas 1, 3, 4, and nominally 2) whose non-firing is, in each case, backed by a real measurement. |

---

## Ranked gaps — mismatch size × how flippable the limiter is

1. **Smith swarm never in the idle rotation** (Area 6) — the self-improvement loop has never run a full cycle; the limiter is one missing entry in `serve.py`'s background list. Largest *flippable* mismatch.
2. **MoE gate cell unwired** (Area 7) — a 0.940 router routing nothing; the limiter is the fixed-hook wiring decision. Flippable; gain unproven.
3. **Growing hive reads but does no jobs** (Area 1) — largest absolute mismatch (the flagship architecture at 2.4760 reading, zero jobs), but low flippability: the only bridge fails on measured capability, so unlocking takes capability work, not a flip.
4. **Job brain holds zero jobs** (Area 3) — the same bridge, smaller surface: 65% mean test vs trained 135M cells; the ≥ rule is symmetric and fires for everyone else.
5. **Spawn trainer staffed exactly one site** (Area 4) — a general self-staffing mechanism throttled to one cell by conservative evidence thresholds plus the slow supply of real logged decisions.
6. **School graduation never fires** (Area 2) — the gate looks like the cap (coder one lesson short) but the `ahead` fallback already serves both students; the residual gap is learning speed on hard plans (3/22), not the gate.

No gap: **sleep** (Area 5, honest negative, correctly not built in) and the **controls** (Area 8, work = product).

### What unlocking the top 3 would mean on Muse's side (one sentence each)

1. **Smiths:** on Muse's side the improvement loop belongs in the background rotation by default — the improver runs unattended on a schedule instead of waiting for a manual invocation that, on Fable's side, never came.
2. **Gate cell:** on Muse's side a measured router should route — learned gating serves wherever it measures ≥ the fixed hooks, with the hooks kept as fallback rather than as the only path.
3. **Reading→doing bridge:** on Muse's side, grown specialists earn real serving work through the existing battery gate from birth, so growth and doing stay one system instead of two hives with a ≥-incumbent wall between them.

---

## Bottom line

8 areas examined. **(a) Flippable-decision holdbacks: 2** (smith swarm scheduling, gate-cell
wiring) — both *disclosed in Fable's own SPEC with their reasons*, so they are deliberate
deferrals, not concealments; nothing in this audit contradicts the limits audit's finding of
0 hidden caps. **(b) Honest measured outcomes: 5** (bodies-as-doing, school, job brain, spawn
trainer, sleep) — in each, the shortfall is backed by a measurement Fable itself published,
and in the school's case the "cap" is already bypassed by a documented fallback. **(c)
Resource-primary: 0** — resources contribute in 2 places (spawn evidence supply is time;
the dream cycle's non-completion is session CPU) but are never the sole explanation.
**Controls: 1 area, no gap** — where no gate or scheduler sits between mechanism and
deployment, Fable's product matches its work exactly.

In Arnav's terms: the work *is* that good, and mostly the product is too. The parts where it
isn't are not spread evenly — they are two unwired/unrun deployment decisions and a family of
strict-but-honest gates. Those are precisely the parts a side without the limitation can
take: run the improver unattended, let the measured router route, and bridge growth into
serving work — each still having to win its own measurement before it serves.
