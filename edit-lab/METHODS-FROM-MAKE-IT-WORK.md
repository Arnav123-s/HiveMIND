# Methods taken from the make-it-work line (read 2026-11-09 from its README + training/cells.py)

Their line is ahead on product and measurement. This is what transfers to the repair job, and how.

## Their locator (how they find where a skill lives)
`training/cells.py probe`, two cheap loss-based maps per skill — no generation evals:
1. Gradient map: |W x dL/dW| per module — first-order loss change if that module moved.
2. Knockout map: loss when one layer's attention or MLP output is removed.
Rules over the maps are written down explicitly (target / unblock / bottleneck), and every
pick is logged with its reason (locator_log.jsonl) as training data for a future locator cell.

## Their measured lesson: breadth beats concentration
Across 15 skills, the locator's concentrated pick (edit only the indicted modules, rank 8)
was best on 2, tied on 2, and LOST on 11 — to rank 2 on every module, or the pick plus
rank 2 everywhere else ("thin"). A random pick of the same size beat the concentrated pick
where that control ran. Their conclusion: "A skill is not stored in one small set of
modules: a small change in every module edits it best."

## Their selection discipline
- Winners chosen on a DEV split (held-out training words); the TEST split is never used to
  choose. Where dev and test disagree, it is reported, not fixed by peeking at test.
- Every number is a held-out measurement; evals are small (3-18 cases) and they state
  plainly that single-case differences are noise.
- Dead layers found by knockout were pruned: 8 layers removed, 144 MB -> 115 MB base.

## What changes in the repair job
1. MAP FIRST, CHEAPLY: run gradient + knockout probes over the coordinator failure cases
   (base + rejected adapter) before spending generation evals on ablation. The map
   prioritizes; evals confirm.
2. ADD THE THIN CANDIDATE: a rank 2-4 edit across ALL of layers 14-27 at the gentle dose —
   their winning shape. Never tried here; every candidate so far was rank 16 (thick), and
   thick is also what let the researcher cook its loss to 0.06.
3. KEEP THE ABLATION, REFRAME IT: leave-one-out still answers "which layers actively harm"
   (adapter repair is removal, not addition — the breadth lesson may not transfer cleanly),
   but a layer is dropped only if the map AND the eval both indict it.
4. DEV/TEST SPLIT FOR SELECTION: build a small dev split from the eval distributions for
   choosing between candidates; the held-out suites get run once per finalist. Stops
   iterating against the test set (the no-benchmaxxing rule, formalized).
5. LINEAGE LOG: every candidate, its map evidence, and its dev/test scores in one log
   (their wins.json / locator_log pattern) — the LEDGER gains a per-candidate table.

Caveat kept honest: their breadth result comes from ADDING skills to a 135M base.
Repairing a harmful rank-16 adapter on a 4B is a different operation; these are
hypotheses to test under the same win-gate, not conclusions imported as fact.

## Addendum — their HANDOFF.md (read 2026-11-09, commit 21ce2534, the old
## session's handoff to the new Fable session; head of make-it-work at read time)

State of their line: whole-hive bench on fresh held-out sets, run once on
frozen code — set 1: 9/16, set 2: 11/16, set 3: 13/16; dev 15/16. 117 tests
pass. Nothing running; PR #5 merge needs Arnav's explicit yes.

More transfers, adopted here:
6. CONTAMINATION CHECK: they verify new held-out tasks against training data
   with a script (training/contamination_check.py) before a set is run. The
   expanded held-out suite in this lab gets the same treatment: n-gram overlap
   of every new case's task text against every training corpus (original,
   specialized, rebalanced, micro, synth), logged before any measurement.
7. REAL-INPUT VALIDATION: two of their cells that aced synthetic tests failed
   on real text (3/15 real pairs) and lost their jobs. Lesson applied here:
   synthetic-bank success (dev, synth-distribution performance) is never
   evidence of held-out success; the expanded suite is written in the original
   suite's real-world style (named sites, real packages, concrete numbers),
   not in the synth bank's template style.
8. COMPOSITION HONESTY: their measured chain (small model -> cell -> big
   model) could not beat the big model alone, so the cell is "trained but not
   called" — reported, not shipped. Same rule for this lab's router/jury: if
   the composition does not beat base on the pristine measurement, it is
   recorded as measured and not adopted.
9. REPORT SHAPE: their final reports use Blocked on me / Changed / Found and
   mark anything unconfirmed. The lab's final report adopts the same shape.

---

## Addendum 2 — Fable session, 2026-11-09 ~13:00 PT (commits 2f5c90f, 28cca6e, 3591845, 3447210; HANDOFF live-status 20:30 UTC)

Their state: 126 tests pass (was 117); held-out 1/2/3 still 9/11/13 of 16 on frozen code; PR #5 merge still needs Arnav's explicit yes. New since the first read:

1. **Self-spawning cells from logged calls** (`team/life.py`, `team/cells/spawn.py`, `training/cells_spawn.py`): mine the hive's own logged calls for call sites whose replies take a few fixed values -> declare each a spawned skill -> the member generates practice cases -> train a cell (size ladder 135M, then 360M) -> switch it on ONLY if the newest real decisions vouch for it -> it serves when sure; **1 call in 10 is audited live against the member; under 93% live agreement it is retired.**
   - Import for this lab (router/jury stage): a composition earns its place via audit against real decisions, with an automatic retirement threshold — not via a one-off bench. My per-case regression gate is the static version; add the serve-time version: jury/router decisions get spot-audited against the base model's raw choice, and a composition that falls under threshold is retired, not tuned.
   - Also importable directly: mine my own eval logs for fixed-value decision points adjacent to coordinator failures (for_each presence, plan size) — a tiny checker cell for those is a stage-3 candidate.
2. **Chunked reading** (`chunk_read.py`, promised item 1 in their handoff): the 1.7B extracts facts from short chunks of a page, a cell merges and checks; compared against the 4B reading the page whole, **on logged real inputs**. Import: researcher extract's weakness (base 0.733, one weak case at 0.17) may be a context/chunking problem, not a weights problem. A chunked-extract composition is a legitimate serve-time candidate for the researcher gate (extract > 0.733 AND plan >= 1.000) that touches no weights — measure it the same way (real inputs, per-case).
3. **Size ladder as a standing rule** (spawn trainer + promised per-job ladder): smallest model first, checked; move up a size only when the check fails; track the big models' share per job as a list that should shrink. Matches this lab's thin-first retrain order (r2/r4 before r16) — keep it explicit.
4. **Live-status handoff header**: their HANDOFF now opens with a kept-current "Live status" section so any new session can resume cold. Adopted here: REPORT.md will carry the same header at final assembly.
5. Process confirmations: held-out sets run once on frozen code (snapshot copy + symlinked weights so edits can't reach a run) — same as this lab's pristine-test rule; unconfirmed items are listed as unconfirmed, not smoothed over (their life_drill is mid-run; no cell has been spawned from real work yet — stated plainly).

## Addendum 3 — 2026-11-09 ~23:50 PT sync (their head 428c6fc, 2026-11-10 07:23 UTC)

What their line built since addendum 2:
- **The School (apprenticeship)**: a small model learns a bigger member's job FROM that member (its logged tasks + the 4B's plans as lessons), then takes an exam on UNSEEN lessons; only on passing does it take the job. New specialists learn ONLY their gap (the cases incumbents get wrong) and are asked only inside that gap; role ensembles answer together meanwhile. The School runs inside their always-on idle loop and shows in the org chart.
- **Bench state**: normal hive 15/16 after shared fixes; csv, chart and fib pass in the normal hive. The small-models-only line still fails csv and chart (and arxiv in an earlier run) — their harder constraint remains harder.
- **Verifier hardening**: a research result that says it found nothing is NOT a pass; when dropped items leave fewer than ordered, the researcher is asked once for other items.
- **Coder**: a narrow sort-direction check asked of a small model BEFORE the expensive review; an unchanged program after feedback is retried once WITH sampling.

Folded into this lab / the factory design:
1. **School = the factory's growth mechanism, exam-gated.** Distill a working large member into a small specialist using the member's own logged work as curriculum; train hardest on incumbent errors (gap-only data); takeover only after an unseen-lessons exam. This is spawn-mining grown up: mining says WHERE a cell can exist, the School says HOW it earns the job. (FACTORY-ARCHITECTURE build item 3/3b gains this as the Tier-1->Tier-0 demotion path.)
2. **"Found nothing" is not a pass** — adopted as a scoring rule in our hive battery and verifier stance: an empty/null result never counts as success.
3. **No-change retry gets sampling** — if a retry reproduces the failed output verbatim, one sampled retry is cheaper than a third identical greedy one.
4. **Cheap narrow pre-checks before expensive review** — one more instance of the eval-economy funnel: a tiny checker (even a small LM asked one narrow question) gates the costly judge.

---

## Adopted into the growth loop 2026-11-11

Arnav's direction (2026-11-11): "Use fables methods learn from it if thats better improvise if u really can." Implemented in `factory/growth.py` (`_methods_arms`, switched on by the new `methods` argument of `attempt_birth`) and `factory/growth_cycle.py` (`run_cycle3`). The cycle-3 strategy is the AUTO path's default — the cron's bare `python3 -m factory.growth_cycle` runs it — while an explicit `--cycle-id` without `--strategy` still reproduces the legacy cycle-1/3 behaviour exactly, and `--strategy cycle2` is untouched. The dual pristine gate, battery verification, and audit/rollback are unchanged; the arms change only how candidates are GENERATED. First real use: growth-cycle-004 (next cron run).

**Adopted from Fable:**
1. **Recipe head-to-head with dev-split selection.** Per target, 3 training recipes (scratch-text-h4, init-lr03, init-lr10) run at a fixed small budget (120 epochs) on the target's TRAIN diet; the winner is picked on a stratified DEV split carved from that diet (never from a judging slice), and only the winner is retrained at full budget as a gate candidate. The head-to-head record (every recipe's dev score, the winner) is stored in the cycle JSON and printed in the report's Methods provenance section.
2. **Breadth beats concentration — as a gated hypothesis, not an imported conclusion.** One parent-initialized probe fine-tune supplies a weight delta. The THIN candidate applies α=0.3 of that delta to EVERY weight group; the CONCENTRATED control applies the full delta to only the group that moved most. Both are judged by the same dual gate, so this substrate votes on whether their lesson transfers (their result came from adding LoRA skills to a 135M base; these are tiny MLPs trained by gradient descent — the caveat at the top of this file applies).
3. **Winners chosen on dev, never on the judging slices** — already the standing gate's property for births; now formalized for recipe selection too (item 1). Per-candidate provenance (arm + method on every judged row, plus the head-to-head table) extends the lineage-log pattern (their wins.json / locator_log discipline).

**Improvised here (not Fable's):**
4. **Dream-first repair arm.** Before a child is trained from the parent, the parent is REPAIRED: a gentle fine-tune (200 epochs, lr 0.3) on a diet of difficulty-filtered, execution-verified dream items concentrated on the parent's measured train-side failures, plus the parent's own wrong train items and a capped replay slice. The arm's candidates are then seeded from the repaired parent. Honest limit: the full dream-cycle executor (`dream.run_dream_subject`) is a whole-composition pipeline with its own state and judging and cannot run inside a birth attempt, so this arm composes its machinery pieces (`dream_gen.gen_pool`, `contamination_filter`, `difficulty_filter`) at birth scale. It is the closest honest version, and the cycle record labels it improvised.

**Deliberately NOT adopted, and why:**
- **The locator (gradient + knockout module maps) as a selection input.** There are no per-module adapters in this substrate to indict — models are single tiny MLPs (hidden ≤ 8) trained whole. The probe fine-tune's per-tensor |Δ| is the cheap map that exists here, and it is used exactly where a map is needed (picking the concentrated control's module).
- **The literal rank-2-on-every-module LoRA shape.** No adapters exist here; the scaled full-network delta (α-blend over every weight group) is the equivalent operation in this substrate.
- **The School, spawn-mining, and live-audit retirement.** Those are serving-time mechanisms; this upgrade is candidate generation only. Births still happen only through the dual pristine gate + served battery + full audit, with automatic rollback.
- **Dead-layer pruning from knockout maps.** Nothing to prune at this scale, and every candidate already passes through weight-level pruning (`F._prune`) in the standard judging path.

Smoke evidence (2026-11-11, wrong-operator/expression, tiny budgets, models dir redirected so serving state could not change): head-to-head picked init-lr03 (dev 0.8889 vs scratch 0.8384 / init-lr10 0.8586, dev n=99); all five arm candidates were judged; the gate rejected every one (best slice 0.85 = parent's 0.85 — a tie is not a win; dream-first posted the best intent score, 0.6758 vs parent 0.6326). No birth, no state change — the machinery works and the gate still decides.
