# ENDGAME-STATUS — Muse's work, Muse's side

Executor log for mill/ENDGAME.md (E-1…E-11). Each item closes here with evidence + numbers.
Plan copied to mill/ENDGAME.md at start.

## E-2 (ledger fixes) — CLOSED 2026-11-13 18:29Z (code verified + hand-inspection PASS, zero defects)

Hand-inspection landed 2026-11-13 18:29Z (mill/LEDGER-INSPECTION.md; snapshot 18:28Z, ledger 162 lines, live pass): ALL 7 checks PASS, zero defects — baseline line matches JOBZERO.log field-for-field; all 154 probe lines carry the full fingerprint with one identical code_sha; verdict arithmetic 0/139 wrong and screen.py band edges match PROMOTE.md as amended exactly; error discipline exact (15 error lines held=null; benched MILL-120/121/122, MILL-222, MILL-306 each 3 errors + benched line; no double-counting); deferrals single line (157 items, distinct ids); trials fold clean and recompute to the recorded MILL-304 reject; census cross-checks the queue exactly (done 139/222 = 62.6% at snapshot, promotes 1 / nears 71 / flat 5 / below 62). A final tally re-check at pass completion feeds the Sunday bundle (bookkeeping only). Original code-side verification record follows.

## E-2 code-side verification (2026-11-12 ~21:05 PT)
All RIGOR-AUDIT §4 fixes confirmed present in screen.py by direct inspection:
- code_sha stamped on every ledger/trial line (stamp(), screen.py:152); corpus fingerprint (sha+bytes+pieces) on baseline lines (:470).
- "seed" explicit on probe lines (:432) and baselines (:467); trial seed events carry steps + wall_s.
- kind:"deferrals" line per pass per generation (ledger_deferrals :615, called :875).
- verdict=="error" = not-done, re-queues; explicit benched line after 3 errors (ERROR_BENCH_AFTER=3).
- sample_sd (÷n−1) at :160; per-seed adoption guard (≥2/3 seeds beat ref mean) in judge_trials; confirmation set (offset windows, run_confirmation :555); champion install inside one Locked() flock section.
- sweep_probe.py validates its copied argparse against train.py --help at startup, refuses loudly on drift.
REMAINING for E-2: nothing — the gen-0 pass is running (below) and the hand-inspection closed above.

## E-1 (preflight) — PARITY PASS; noise pending a genuinely free slot
- Parity: **PASS, twice** — sweep seed-0 champion held_init = **8.3138 exactly** both runs. The sweep is bit-faithful at init; sweep verdicts are licensed on that axis.
- Probe-noise: NOT yet measured. Both preflight attempts aborted at noise seed 0 ("did not complete"). Root cause found by a hand-run sweep job: sweep_probe prints `MILLSTOP busy:run_scale_ladder` — **the scale ladder is active again** and the sweep yields mid-preflight (parity's 15 s job slips through; the 75 s noise job gets stopped). Per hard rules the ladder is never preempted: the noise half (3 × 75 s) runs in the first slot where lab_busy() is clear at job start. PREFLIGHT-RESULTS.md on disk records parity PASS / noise FAIL-incomplete.
- PROMOTE_DELTA decision waits on the noise sd. Note E-11's bar audit (below) independently supports treating 0.05 as a floor, not a given.

## E-11 (fidelity floor) — ANALYSIS HALF CLOSED 2026-11-12 ~21:11 PT (mill/FIDELITY.md, mill/OVER-HORIZON.md)
- Scope finding: runs.jsonl contains **zero probe-budget runs** — true 75 s→8 min fidelity is unmeasured; the filed stand-in (seed-0 at full budget) was scored instead. 13 comparable arms × 3 seeds (snapshot reproduced champion ref 2.8580 ± 0.0161 exactly).
- Spearman ρ vs 3-seed mean-held ranking: seed-0 held **+0.934 global but +0.371 in the |Δ|≤0.10 decision band**; train_last100 +0.846 (near-band +0.257); mean_flip_share **−0.193 (no fidelity)**; null control held_init ρ +0.730 → most headline correlation is chassis structure, not treatment signal.
- Bar audit at PROMOTE_DELTA=0.05: sign flips 2/12 (16.7%); **false-promote 1/1 promotions issued (100%)** — ste_half, Δ_seed0 +0.0615 vs true +0.0374 (39% winner's-curse shrink); false kills 0 but vacuously (kill side untested). J-028 admission test FAILS → probe demoted to advisory judge, serviceable as bottom-killer.
- Over-horizon (J-027 minimal): **95/380 entries = 25.0%** (44 HARD 11.6% — mechanisms arithmetically cannot act in ~25 steps; 51 SOFT 13.5%) — their flat probes must ledger INCONCLUSIVE—horizon, never kills.
- REMAINING for E-11: concurrency — bench_concurrency.py in a free slot, or the bundle confesses CONCURRENCY=1 for all gen-0 numbers.

## E-3 (merge) — GATED
FLAGS-BUILT.md results section still unfilled — flag factory verification suites not yet complete (re-running from flaglab/ after runtime restart). NO MERGE until its completion report shows baseline-identity suite green.

## COMPUTE AUDIT folded in 2026-11-12 ~21:46 PT (compute/COMPUTE-AUDIT.md)
- Measured under live sprint load: CPU efficiency during a champion-shape step loop = **0.108 (~9× contention tax)**; 46.5 s CPU across 431 s wall; load avg 26.8 on a 1.5-vCPU quota. Step CPU split: backward 43%, forward 39%, vote update 15%, **data loading 0.4% — closed as a non-issue**.
- Target order: **SCHEDULING FIRST** (queue adoption + ashp offload) > matmul kernels > data pipeline never.
- Scheduling consequences adopted for the endgame: (1) when the ladder frees the lab, order is **preflight noise → bench_concurrency.py → gen-0 pass** (the pass's concurrency setting must be measured, not the interim default); (2) **heavy VM jobs stay serialized** — the 9× tax is now measured proof, not etiquette; (3) E-11's concurrency half is upgraded from "run or confess" to RUN (bench_concurrency is the audit's scheduling evidence and sits second in the free-slot queue).
- **Resume proof PROVEN exact** (compute/RESUME-PROOF.md): kill -9 mid-step after the step-20 checkpoint; resume reproduced the control at every checkpoint including the step-40 flip burst. If any endgame trial grows long enough to fear a restart, the compute/train_ckpt.py pattern is proven insurance (drivers don't adopt it yet — noted, not blocking).
- State at fold-in: ladder still running (relaunched driver), corpus-v3 build still running (file at 44,672,138 B and growing — final piece count only when it settles), flaglab suite logs were in /tmp (wiped by the restart); FLAGS-BUILT results still unfilled → E-3 gate still closed.

## DECOMPOSITION DIRECTIVE adopted 2026-11-12 ~22:11 PT (Arnav, via head of ops)
Everything decomposes into small runs owned by many agents; monolithic runs are out. Applied to this endgame:
1. **Gen-0 pass = probe micro-jobs, not one serial loop.** When E-3 lands, each runnable pool entry becomes ONE claimable job in compute/queue/labqueue.py (kind=probe, priority 20; trials kind=trial priority 10) and is executed by worker lanes claiming jobs one at a time — **two lanes: VM + ashp** (ashp measured ~3× VM per step for probes; thermal discipline; ONE heavy job at a time on ashp). Each probe keeps its own ledger line via screen.py's existing ledger discipline; verdict-bearing work (job zero, trial judging, confirmations, control re-runs) stays SOLO in the coordinator — decomposition applies to probes, never to judgments. Minimal wiring owed at E-3: a thin worker that claims → runs (sweep batch-of-1 on VM; subprocess probe on ashp) → ledgers → completes/fails the queue job with heartbeat. run-forever.sh remains the fallback driver if the wiring slips, noted here so the swap is a decision, not a drift.
2. **Analysis never queues behind execution.** Each analysis item owns a specialist in parallel: anatomies (J-022/J-013/J-047) already run as their own specialist; J-025 ran as its own (closed); the E-2 ledger hand-inspection gets its own specialist the moment the first ledger exists; E-4's split check is a standalone run by whoever is free when the v3 build settles.
3. **Long trials get chopped, not endured.** Any trial long enough to fear a restart runs as checkpointed segments under the proven compute/train_ckpt.py pattern (RESUME-PROOF exact) instead of one monolithic run.
4. **The measured limit stands:** raw VM training steps do NOT multiply with agents (9× contention tax, COMPUTE-AUDIT) — decomposition multiplies everything around the steps and splits steps across machines; heavy jobs stay serialized PER MACHINE.

## E-4 (corpus-v3) — IN PROGRESS (corpus stream)
SOURCES.md now exists (6,569 B); build.log shows Gutenberg ingestion past the blocklist step; corpus-v3.u16 currently 4,776,400 B = 2,388,200 pieces and growing. check_v3_split.py runs when the build settles. True count TBD from finished file — never ~21.4M.

## HANDOVER — executor 2 took over 2026-11-12 ~23:14 PT (2026-11-13 ~07:14Z)
First executor's phase complete; items below re-verified against disk at handover.

## LADDER — TRUE STATE ESTABLISHED 2026-11-12 ~23:16 PT (driver log + runs.jsonl)
- **Driver is DEAD.** Last log write 07:10:35Z, parked "waiting out the growth-cycle window
  before layered_rope_scale50m s0"; no process at 07:16Z check (its wait loop logged every
  ~2 min — silence = gone, same infra-death pattern as tonight's other agents).
- **Recorded results (runs.jsonl):** 2M layered+rope ×3 seeds = **3.2878 / 3.2649 / 3.2709
  (mean 3.2746)**; 10M layered+rope seed 0 = **2.9472**. Log-only partial: 10M seed 1
  finished short at 39/56 steps, held 3.2069 (driver log RESULT line; never landed in
  runs.jsonl — NOT comparable, fewer steps).
- **Failed:** 50M seed 0 rc=-9 (~12 min in, restart window); 10M seed 1 re-run rc=-9;
  plain 2M seed 0 TIMEOUT at 894 s under load.
- **Never ran:** plain 2M seeds 1/2, laddercal seed 0, 10M seed 2, 50M seed 1.
- **VERDICT as it stands:** winner = **10M rung** (2.9472, n=1, provisional), runner-up =
  **2M rung** (3.2746, n=3) — exactly CONFIRM-PLAN's planning assumption, so Set A is
  10M vs 2M at 280 steps × 3 seeds with no substitution.
- **EXECUTOR DECISION: ladder is CONCLUDED as it stands; driver NOT relaunched.**
  Relaunch would run 50M seed 0 first — work ENDGAME §3 explicitly excludes ("confess and
  move on"; the rung has died twice) — and the informative remainder (10M seeds at 56
  steps) is superseded by Set A's 280-step × 3-seed confirmation. 50M stays UNMEASURED
  and is confessed as such in the ladder record. RESULTS-SCALE-LADDER write-up delegated
  to a specialist (numbers above are its source of truth).

## GROWTH CYCLE — fired and SKIPPED cleanly 2026-11-13 06:53Z (ledger cycle-007 entry)
Cron fired on schedule under Gate 3′; preflight found the lab busy (Q1 exam sitting +
flaglab verification trains) and skipped. No collision, no births, battery untouched.
(Note: the growth ledger numbers this run "cycle-007"; earlier records called the
Nov 12 16:50 PT run cycle 7 — a numbering overlap in the ledger, flagged here so the
Sunday bundle does not double-count. Next cycle ~6 h later will skip likewise while
the lab is busy.)

## E-4 (corpus-v3) — CORRECTED 2026-11-12 ~23:16 PT (supersedes the stale section above)
- v3 is **BUILT: 191,256,252 pieces**, cross-checked three ways; record at
  corpus-v3/COMPLETION-2026-11-12.md; SOURCES.md exists. The "1.78M / ~21.4M" figures in
  ENDGAME.md §E-4 are pre-build history.
- Split check: first run crashed on a one-line mmap bug; **re-run IN PROGRESS at handover**
  (check_v3_split.py, PID 2063 at 07:13Z, ~547 MB RSS). E-4 closes when
  corpus-v3/split-check.json lands with its overlap number; until then every v3 figure
  carries "split unverified."

## FREE-SLOT CHAIN — armed 2026-11-12 ~23:2x PT (mill/freeslot_watch.py)
The lab is crowded with other streams' heavy work (Q4 map, Q1 exam sitting, Q3
llama-cli, kernel-attn verify, flaglab verifies, split check) — a genuinely free slot
is an event, not a schedule. A detached watcher now waits for one (mill's own lab_busy()
clear + foreign-heavy patterns clear, 3 consecutive minutes) and then runs, serialized:
**(1) preflight.py (E-1 noise half) → (2) bench_concurrency.py (E-11 concurrency half,
upgraded to RUN) → (3) Gate 0** (exact firing command from scale-next/GATE0-READY.md;
ladder verdict has landed per the conclusion above; growth cycles skip themselves
while the lab is busy). Stops and logs on any stage failure. Log:
mill/freeslot-chain.log; state: mill/freeslot-chain.state.
- After stage 1: read PREFLIGHT-RESULTS.md — if the printed required PROMOTE_DELTA
  exceeds 0.05, raise it in screen.py AND PROMOTE.md before any gen-0 pass is judged.
- Set A does NOT auto-chain: its driver (scale-next/run_confirm_a.py) is being built +
  reviewed in parallel; executor launches Set A once Gate 0 is underway/done.
- Anatomy driver (E-5a/E-6) has been waiting since 05:09Z and yields to this chain's
  processes by its own pattern list; it takes the following clear slot. Do not duplicate it.

## LADDER RECORD — WRITTEN 2026-11-12 ~23:19 PT (RESULTS-SCALE-LADDER-2026-11-12.md)
Specialist write-up landed, verified against runs.jsonl + driver log + NUMBERS.md.
Verdict line as recorded: **10M provisional winner (n=1) over 2M (n=3) at equal tokens —
held 2.9472 vs 3.2745; 50M unmeasured; provisional until CONFIRM Set A lands.**
- Correction to the handover section above: the 2M mean re-derived from runs.jsonl is
  3.27453… → **3.2745** (not 3.2746; 0.0001, immaterial, record carries the derived value).
- Log/records disagreements now on record: the 10M seed-1 partial (39/56, 3.2069) exists
  only in the driver log; two attempts (first 10M s0, plain s1) stopped silently at
  driver restarts; all 4 completed runs agree exactly between log and runs.jsonl.

## CONFIRM SET A DRIVER — BUILT + DRY-VERIFIED 2026-11-12 ~23:24 PT (specialist)
- scale-next/run_confirm_a.py + scale-next/CONFIRM-A-READY.md landed. Launch (executor
  only, after Gate 0): `~/workspace/edit-lab/fable-validation/venv/bin/python
  scale-next/run_confirm_a.py --launch` from bitnet-lab.
- 6 jobs, all pending, est total 15,120 s ≈ 4.2 h: layered_rope_confirmA10m seeds 0/1/2
  (dim 512×3, 280 steps, min cap 100) then layered_rope_confirmA2m seeds 0/1/2
  (dim 288×2, 280 steps, min cap 40). Skip keys on (recorded arm, seed, steps_target) —
  the 56-step scale records cannot skip these. Ladder etiquette copied (busy-yield,
  growth-window wait-out, 10:30 UTC hard stop). Guard + --dry-run: exit 0, wrote nothing.
- Gate 0 guard re-verified in the same pass: py_compile OK; no---launch guard printed the
  plan, exit 0, overlap-runs.jsonl / window-index.json / byte-manifest.json still absent.

## GEN-0 QUEUE WORKER — BUILT + DRY-VERIFIED 2026-11-12 ~23:47 PT (specialist)
- mill/queue_worker.py + mill/QUEUE-WORKER.md landed. All execution/ledger logic delegates
  to screen.py's own functions (parse_pool/validate/ledger_probe/ledger_deferrals) — no
  parallel ledger format. Worker claims kind=probe ONLY (priority 20); validate_job()
  refuses trial/judgment/confirmation/control/job-zero payloads and MILL-000 — refused jobs
  are queue-failed, never executed. A "promote" verdict is ledgered and noted in the queue
  result for the coordinator (judging stays solo, never queued).
- Selftest 17/17 passed (scratch queue dirs under /tmp only). --dry-run vs scratch root:
  34 would-submit / 345 deferred at the CURRENT pre-merge flag state (matches the 35-ish
  runnable count); live queue state untouched; mill/ledger.jsonl still does not exist.
- Executor start sequence (after E-3 merge; from bitnet-lab): (1) coordinator SOLO job
  zero via screen.measure_baseline; (2) `python3 mill/queue_worker.py submit --gen 0`;
  (3) lanes `work --lane vm` and `work --lane ashp` (max-wall 240 min each); monitor via
  compute/queue/labqueue.py stats. Full commands in QUEUE-WORKER.md.
- Flagged assumption for E-3: ashp's train.py copy must carry the same post-merge flags
  as the VM's — drift surfaces as probe error lines (ledgered, re-queued), not silent
  wrong numbers. Lane ledger lines are omp-stamped (ashp omp=8) so numbers never mix silently.

## CORRECTION — ladder driver ALIVE (supersedes "DRIVER IS DEAD / NOT RELAUNCHED" above)
2026-11-12 ~23:50 PT: `pgrep -af run_scale_ladder` shows the driver running (PID 5893),
relaunched via setsid/nohup by its owning stream (wrapper bash PID 5891; a 25-min
monitor loop from the same stream is also present). The 07:16Z death read was a sampling
gap: the driver had died (or was between restarts) at that check and its owner brought
it back — the earlier silent gap in ladder-driver.log (after 07:10:35Z) was real but
temporary. Current facts:
- The ladder's queue is AGAIN the incumbent heavy job; it sits parked before 50M seed 0
  (growth-window wait) and will proceed through its remaining jobs (50M s0, plain 2M
  ride-along, laddercal, 10M s2, 50M s1) unless its owner or the head of ops stands it down.
- The VERDICT section above stands unchanged (10M provisional winner, n=1, over 2M n=3;
  50M unmeasured) — it describes the record as it stands, which is what CONFIRM Set A
  (built, reviewed, staged) will confirm. Set A does NOT fire while the ladder driver
  lives: CONFIRM-PLAN fires it when the ladder verdict lands, and the confirm driver
  would only add contention against the ladder's own queue.
- Gate 0 checklist step 1 (pgrep run_scale_ladder empty) is again UNSATISFIED. The
  freeslot watcher's chain therefore remains correctly parked: its stage order is
  unchanged, and it will take the first slot after the ladder actually concludes.
- Executor's no-relaunch decision is moot (the owner relaunched first). Recorded here so
  the Sunday bundle never inherits the wrong driver state.
- Split check (PID 2063) still running at this check (~35 min in, log still 0 B — it
  writes on completion); flag factory verify loop (verify.py base→neutral→pairs→smoke,
  logs in flaglab/) still running; E-3 still gated.

## SEQUENCER TAKEOVER — executor 3, 2026-11-12 ~23:54 PT (2026-11-13 ~07:54Z)
Standing owner of the trigger points through Sun Nov 15 (re-dispatch; first spawn died
at birth on a transport error). Trigger state verified against disk/processes at takeover:
- **T1 split check:** PID 2063 alive ~40 min, split-check.json ABSENT, log 0 B (writes
  on completion). Not fired. E-4 stays open; v3 figures keep "split unverified."
- **T2 flag factory:** verify loop alive, still inside the base suite. FLAGS-BUILT.md
  results section still the unfilled placeholder (line 24). E-3 stays GATED.
  ⚠ Sequencer watch item: flaglab/base.log so far = layered_half **PASS** identity
  (7.6694 = 7.6694) but plain_half and ste_half **FAIL with held=None and EMPTY output
  tails on both live and next** — no numbers at all, which reads as the runs being
  stopped in the crowded lab (or dying instantly), NOT as an identity mismatch (a
  mismatch would print differing held values). When FLAGS-BUILT fills, "green" will be
  judged on this distinction: empty-output FAILs are a re-run-in-a-free-slot problem,
  not merge evidence either way. Flag factory stream owns its loop; sequencer does
  not interfere.
- **T3 ladder:** driver ALIVE (PID 5893), currently yielding — log shows "another
  heavy job is running (python -m team)" (the Q1 exam harness owns the moment). Its
  remaining queue (50M s0, plain ride-along, laddercal, 10M s2, 50M s1) has NOT
  concluded. Gate 0 / Set A stay parked. Provisional verdict unchanged: 10M (n=1,
  2.9472) over 2M (n=3, 3.2745); 50M unmeasured.
- **Freeslot chain:** watcher ALIVE (mill/freeslot_watch.py, PID 3216, up since
  07:18:31Z), still waiting for 3 consecutive clear minutes. Chain order on a slot:
  preflight noise (E-1) → bench_concurrency (E-11) → Gate 0. Sequencer monitors;
  does not duplicate the chain.
- **Anatomies:** driver ALIVE (PID 2192), waiting on lab-busy (run_scale_ladder);
  layered_half_rope s0 not yet started. No J-022/J-013/J-047 numbers yet; harvest
  when the driver logs results.
- Sequencer polls trigger sources on a ~15–20 min cadence (mill/sequencer-poll.log)
  and acts per the brief: T1 → close E-4 (hold E-8 if overlap nonzero); T2 green →
  E-3 merge + free-slot sequence (job zero solo → submit → VM + ashp lanes);
  T3 → Gate 0 + CONFIRM Set A.
- **Poll 2026-11-13 08:09Z:** no trigger fired. T1 still running (~56 min, JSON
  absent). T2: base.log now PASS=1 / FAIL=3 — a third empty-output FAIL accumulated
  while the loop grinds in the crowded lab (same pattern; still no identity-mismatch
  evidence anywhere). T3 ladder still yielding to `python -m team`. Freeslot watcher
  and anatomy driver still parked on lab-busy. Next poll ~08:25Z.
- **Poll 2026-11-13 08:25Z + T2 ESCALATION:** no trigger fired. T1 still running
  (~72 min). T3/freeslot/anatomy unchanged. **T2 is now environmentally blocked,
  stated plainly:** base suite stands at 5 of 8 configs reported — layered_half PASS
  (7.6694 = 7.6694); plain_half, ste_half, layered_half+cooldown FAIL None/None;
  layered_half+carry FAIL live=7.6694 / next=None. **Every FAIL is a run that
  produced no output on one or both sides; every number that exists on either side
  is 7.6694, identical.** There is still zero evidence of an identity mismatch —
  but the suite also cannot reach an honest green at this rate: its tiny runs die
  silently in the crowded lab, and neutral/pairs/smoke behind it are far larger.
  Sequencer's ruling request to head of ops (reported 08:26Z): the operative green
  for E-3 should be the merge-gate identity re-run executed inside a protected free
  slot (freeslot chain), not FLAGS-BUILT's crowd-killed suite; alternatively the
  flag factory re-runs under the chain's protection. Until ruled, E-3 stays gated
  and the sequencer keeps polling. Next poll ~08:41Z.

## SCOPE CHANGE — Arnav, 2026-11-13 00:33 PT (via head of ops): NO ASHP, VM-ONLY
Forget the laptop part for now — focus strictly on the hive goal. Effective
immediately for all sequencing in this file:
- **No ashp lanes anywhere.** The gen-0 pass runs **VM-only**: the queue-worker start
  sequence (QUEUE-WORKER.md step 3) drops the `work --lane ashp` lane; only
  `work --lane vm` runs. This supersedes the two-lane split recorded in the
  DECOMPOSITION DIRECTIVE section (§1) and the GEN-0 QUEUE WORKER section above,
  for as long as this scope change stands.
- No laptop/house/shared-memory work, no ashp drops, in any endgame step.
- Everything else stands unchanged: triggers T1/T2/T3, the E-3 merge, Gate 0,
  CONFIRM Set A, and the priced trials — all on the VM, Muse's side only.

- **Poll 2026-11-13 08:41Z:** no trigger fired. T1 still running (~88 min).
  T2: base.log PASS=1 / FAIL=5 (6 of 8 configs reported; pattern unchanged —
  escalation from 08:25Z stands, awaiting ruling). T3 ladder still yielding to
  `python -m team`. Freeslot watcher + anatomy still parked. Next poll ~08:57Z.
- **Poll 2026-11-13 08:56Z — T2 base suite COMPLETE (2/8 PASS):** final base tally:
  PASS layered_half (7.6694 = 7.6694), PASS mag (7.6694 = 7.6694); FAIL plain_half,
  ste_half, layered_half+cooldown, layered full, anneal (all None/None) and
  layered_half+carry (live 7.6694 / next None). **Every measured pair is identical;
  every failure is a silent no-output run. Baseline identity holds wherever it
  could be measured — the suite's 6 FAILs are environmental, full stop.** The loop
  has moved into the neutral suite (neutral.log created, 0 checks yet); at base's
  rate (~100 min for 8 configs in this crowd) neutral+pairs+smoke are many hours
  away and will read the same. FLAGS-BUILT therefore cannot show an honest green
  from this run — the 08:25Z ruling request is now ripe: base is done, and its
  verdict-worthy content is "identity exact on 2/2 measurable configs, 6 configs
  unmeasurable in this lab state." T1 still running (~103 min). T3 unchanged.
  Next poll ~09:12Z.

## RESTART EVENT + T1 VERDICT — 2026-11-13 ~09:04–09:12Z (sequencer re-dispatch)
A runtime restart hit ~09:04Z (sequencer's poll process SIGTERM'd; all lab
processes show ~09:04:30Z start times). Consequences, verified by direct ps:
- **T1 split check:** the old run (PID 2063, ~103 min, zero output) died in the
  restart. The owning stream relaunched it (PID 1886) and in the freer
  post-restart lab it produced its checks within minutes. From
  corpus-v3/split-check.log, verbatim:
  - check1 (eval windows): **128 total occurrences of 128 windows, 0 in the
    training region** — held overlap = **0 at window granularity**.
  - check2 (aligned blocks): **747,094 blocks, 1 duplicate block, 0 involving
    held blocks** — held overlap = **0 at block granularity**; the one duplicate
    is train-side.
  - check3 (lines): **2,145,543 segments, 1,149 duplicate occurrences** (~0.054%)
    — line-level repetition inside the stream; held involvement read from the
    JSON when it lands.
  A final stage was still running at ~09:12Z and split-check.json had not yet
  landed. **E-4 closes the moment the JSON confirms these lines** (check3/check4
  held breakdowns included); the headline is already fixed — v3 held-set overlap
  is ZERO on both the window and block measures, so the E-8 hold (nonzero
  overlap) does NOT engage on the evidence so far. Standing construction caveats
  survive closure: WikiText's own valid/test splits sit inside the v3 stream
  (bites only if a v3-trained model is judged on WikiText itself); Gutenberg was
  tokenized BOS-per-line as built.
- **T2 flag factory:** the verify loop also died in the restart and was relaunched
  by its own stream as `remainder.py` (smoke-remainder; running at 09:06Z on
  annealflip smoke). The base-suite record stands (2 PASS exact / 6 env-FAIL).
  The T2 trigger (FLAGS-BUILT green) is still pending; the 08:25Z ruling request
  still stands.
- **T3 ladder:** driver exited 09:01Z (manual continuation by its owning agent:
  remaining jobs run one at a time with the driver's exact invocations). T3
  detection now tracks runs.jsonl growth + the ladder record, not driver pgrep
  (sequencer_check.sh updated accordingly in intent — see poll log). Not fired.
- **Freeslot watcher: DOWN post-restart, deliberately NOT relaunched by the
  sequencer.** Its stage 3 auto-fires Gate 0 on any genuinely free slot; with the
  ladder finishing via manual one-at-a-time jobs, a gap between manual jobs could
  read as "free" and fire Gate 0 before the ladder concludes — violating T3's
  ordering and colliding with the next manual job. Gate 0 will be fired under
  sequencer control at T3 instead; chain stages 1–2 (preflight noise, concurrency
  bench) can run then as well. Next poll ~09:27Z.
- **Poll 2026-11-13 09:25Z:** T1 final stage still running (PID 1886; 21 min
  elapsed / ~3 min CPU — starved by the Q4×5 + Q3 + flaglab crowd, but alive and
  past check3). T2 verify loop running (remainder). T3: runs.jsonl flat at 46, no
  bare train.py — the manual ladder continuation has NOT resumed post-restart
  yet (its owning agent's recovery pending; T3 ETA lengthens accordingly).
  **Anatomy driver (E-5a/E-6) was also killed by the restart (log dead since
  09:04Z, no owner relaunch in 25 min, no lock/pidfile in the driver) — the
  sequencer relaunched it detached (PID 5845, 09:26Z); it immediately resumed
  its designed behavior (yielding: "lab busy (train_next.py)").** If its original
  owner also relaunches, a duplicate could double-run evals — none appeared.
  Next poll ~09:41Z.

## E-4 — CLOSED 2026-11-13 09:41Z (T1 fired; split-check.json landed)
Final verdict, exactly as recorded in `corpus-v3/split-check.json` (addendum in
corpus-v3/COMPLETION-2026-11-12.md):
- pieces 191,256,252; eval windows 128.
- check1: 128 window occurrences, **0 extra in training** — window-level held
  leakage = **0** (all 128 held windows occur only at their aligned positions).
- check2: **1 duplicate aligned block, 0 held-involving.**
- check3: 2,145,543 segments, **1,149 duplicate BOS-segment occurrences** in-stream.
- check4: **58 of 2,000 sampled 24-piece shingles from held blocks also touch
  training blocks (~2.9%)**.
- **Script verdict: `split_clean: false`** — driven by the sub-window duplication
  (check4 + check3), NOT by window-level leakage.
**Quoting rule (binding on all endgame reporting): never quote v3 held overlap as
zero; quote it as "0 at window level, ~2.9% fragment shingle touch."** The interim
headline in the restart note above ("overlap is ZERO on both measures") is
superseded by this wording.

### E-8 RULING (head of ops, 2026-11-13): E-8 MAY PROCEED after E-3
Window-level cleanliness is the operative property for a re-baseline. The ~2.9%
fragment touch rate is a **recorded caveat that must travel with every v3 held
figure** (the same way v1's leak is carried) — it is not a blocker. The earlier
conditional hold on E-8 (nonzero overlap) is therefore LIFTED; E-8 (K-001) runs
in its normal ENDGAME order position (after E-3, in the priced-trial sequence),
carrying the caveat in its record.
- **Poll 2026-11-13 09:57Z:** T2 unchanged (verify loop running; FLAGS-BUILT
  unfilled; ruling request stands). T3 progressing: runs.jsonl 46 → **47** (one
  manual ladder job landed); between jobs at poll time. Anatomy yielding to
  train_next.py. Next poll ~10:12Z.

## T2 FIRED — FLAGS-BUILT GREEN (2026-11-13 10:12Z poll) — E-3 EXECUTING
FLAGS-BUILT.md results section is filled (verify.py, workspace flaglab/):
**base 8/8 identical, neutral 28/28 identical, kernel pairs 6/6 identical,
smoke1 25/25, smoke2 66/66 — every flag passed.** The factory's process notes
resolve the sequencer's 08:25Z escalation completely: the suites were first run
from /tmp and lost to a restart; the completed run is the workspace re-run; the
base.log PASS=2/FAIL=6 tallies the sequencer tracked were from later
confirmation re-runs under heavy contention, whose failures were subprocess
*timeout* (empty records) — **never a value mismatch; every run that completed
on both sides matched exactly**, with per-step bitwise proofs behind the
identity claims. The escalation's question is answered by evidence: the suite
IS green, no protected-slot ruling needed. Verify loop finished (not running).
**E-3 (merge) is now executing** per the standing sequence: backup train.py →
merge train_next.py → v3 resolver fix → sweep_probe --corpus/--votes/--wd →
J-002 counter-permutation flag (default-off) → smoke --corpus v2 + v3 →
identity suite re-run as the merge gate → free-slot sequence (preflight noise →
bench_concurrency → gen-0 pass, VM-only lane) → priced trials E-7, E-9, E-5b,
E-8 (unheld per ruling), E-10.
Same poll: T3 ladder record updated 09:58Z (runs.jsonl 47, between jobs);
**anatomies got their slot — first eval running 10:02Z** (layered_half_rope s0,
154 steps).

## E-3 MERGE MECHANIC — DONE 2026-11-13 10:19Z (report: mill/E3-MERGE-MECHANIC.md)
- Backup `train.py.pre-merge-2026-11-13` sha256 fc417bab… (byte-identical to
  pre-merge live, cmp-verified). Merged `train.py` sha256 6f038c1f…, installed
  atomically; `train_next.py` untouched (e840eee3…).
- Resolver factored into `train.resolve_corpus(name)`: v1 → corpus.u16 (legacy);
  others try corpus-<name>.u16, <name>.u16, corpus-v2/corpus-<name>.u16 (kept),
  **corpus-<name>/corpus-<name>.u16 (new)**. Verified live: v2 →
  corpus-v2/corpus-v2.u16, v3 → corpus-v3/corpus-v3.u16, unknown → loud error.
- J-002 flag `--counter-permute` (default-off, Layered only): at every 10th step
  after vote/flip processing, each component counter array is randomly permuted
  within its layer (histograms, gate, flip mechanics exactly preserved; only
  weight↔counter correspondence broken); dedicated generator seeded seed+2002.
  Flagged ambiguity: J-002 doesn't specify shared-vs-independent permutation
  across component arrays — implemented independent per array (most literal).
- Sweep parity BY CONSTRUCTION: train.py's parser factored into build_parser();
  sweep_probe.make_parser() now returns train.build_parser() (so --corpus/
  --votes/--wd/--counter-permute are train.py's own); run_one rewired for the
  merged trainer internals; parser_drift() = [] and the sweep self-check exits 0.
- Two disclosed deviations: (1) v2's hard-coded branch folded into the generic
  candidate list (v2 matched by two candidates; one consistent rule); (2)
  layered_kw now actually passes votes=a.votes to Layered (staging documented it
  but never wired it; default 32 = trainer default, neutral at default — the
  gate's layered configs test this empirically).
**MERGE GATE RUNNING** (mill/e3_gate.sh, detached, log mill/E3-GATE.log):
flaglab/train.py snapshot updated to the merged file (hash-verified in the log),
then verify.py base (merged vs staging, 8 configs), then from the lab dir:
--corpus v2 smoke, --corpus v3 smoke, --counter-permute smoke (tiny layered
shape). Gate verdict on completion; E-3 closes only on a green gate.
- **GATE IDENTITY: 8/8 IDENTICAL (2026-11-13 ~10:2xZ, in E3-GATE.log):**
  layered_half 7.6694=7.6694, plain_half 7.6694=7.6694, ste_half 8.2215=8.2215,
  layered_half+carry 7.6694=7.6694, layered_half+cooldown 7.7875=7.7875,
  layered full 7.6694=7.6694, mag 7.6694=7.6694, anneal 7.6694=7.6694. **Merged
  train.py ≡ staging on every chassis config** — including all layered configs,
  which empirically clears the mechanic's deviation (2) (votes pass-through is
  neutral at the default). Note: verify.py printed results to the gate log;
  flaglab/base.log still holds the factory's 07:13Z confirmation re-run (2/8,
  timeouts) — FLAGS-BUILT's filled results section + this gate log are the
  operative records. Smokes (v2, v3, --counter-permute) in flight; E-3 closes
  when they pass.

## E-3 — CLOSED 2026-11-13 10:29Z (merge gate fully green)
Smokes (from E3-GATE.log, tiny layered shape, seed 0, 8 steps):
- **--corpus v2:** RESULT corpus_pieces **907,409** (v2's exact count),
  held_init 8.3183 → held_final 7.7748, `corpus: "v2"` recorded. ✓
- **--corpus v3:** RESULT corpus_pieces **191,256,252** (v3's exact count),
  held_init 8.3199 → held_final 7.9075, `corpus: "v3"` recorded. ✓ (v3 figures
  carry the E-4 caveat: 0 at window level, ~2.9% fragment shingle touch.)
- **--counter-permute (J-002):** run completes clean, held_final 7.6694.
  Honest note: at 8 steps the every-10th-step permutation never actuates (first
  fires at step 10) — this smoke proves parse/run integration only; actuation
  coverage is E-9's full trial. ✓ as an integration smoke.
train.py is now the merged file (sha 6f038c1f…); runnable pool coverage moves
from ~35 to the post-merge set (E-015/E-017 now executable via sweep parity;
--corpus unlocks E-018…E-021). **Free-slot sequence started immediately:**
preflight.py launched 10:4xZ (PID 15812; log mill/PREFLIGHT-RUN.log) — it did
not refuse, and its parity half now re-tests the MERGED sweep path (held_init
must read 8.3138). On preflight completion: if 2× noise sd > 0.05, raise
PROMOTE_DELTA in screen.py + PROMOTE.md BEFORE any pass is judged; then
bench_concurrency.py; then the gen-0 pass (solo job zero → queue submit →
VM-lane only).
Same window: T3 runs.jsonl 47 → **50** (manual ladder continuation landing
jobs); anatomy on seed 1. T3 still open.

## E-1 — CLOSED 2026-11-13 ~10:5xZ (preflight complete, both halves)
PREFLIGHT-RESULTS.md (mill/preflight.py, on the MERGED code, code_sha dea7235b…):
- **(b) Sweep parity: held_init 8.3138 vs expected 8.3138 → PASS** (third
  confirmation, and the first on the merged train.py/sweep path).
- **(a) Probe noise: job-zero helds [6.0755, 5.8445, 5.5811] (seeds 0/1/2 at
  75 s probe budget), sample sd 0.2474, range 0.4944.** PROMOTE_DELTA 0.05 <
  2× sd (0.4948) → the old bar sat inside probe noise.
**Action taken per the standing instruction, before any pass is judged:
PROMOTE_DELTA raised 0.05 → 0.495** in mill/screen.py (line 66, compiles) and
mill/PROMOTE.md (threshold, near-band upper edge, and the "Why" section
rewritten to cite the measurement; the old "loose on purpose" rationale is
recorded there as refuted). PROBE-NOISE.md written by the script. Consequence
for the gen-0 pass: probes now promote only on very large effects (Δ ≥ 0.495);
the pass's value shifts to bottom-killing and honest flats, with trials queued
rarely — the E-11 demotion (probe = advisory/bottom-killer) is now priced into
the bar itself.
**Free-slot sequence stage 2 launched:** bench_concurrency.py detached
(mill/BENCH-CONCURRENCY-RUN.log; self-guards against a busy lab). Stage 3
(gen-0 pass) waits on its verdict for CONCURRENCY. T3: runs.jsonl 54.
- **Restart #2 (~11:00Z) + bench deferral, resolved 11:0xZ:** the runtime
  restart killed the sequencer's poll and the anatomy driver (again). Bench
  launch #1 had already self-deferred ("another mill process is active
  ['17612']") — that PID proved transient and is gone; no mill loop/screen/
  queue process is running. Anatomy driver relaunched (PID 1975) and resumed
  correctly ("skip layered_half_rope s1: already done" — it tracks completion).
  Bench relaunched clean (PID 2079, log mill/BENCH-CONCURRENCY-RUN.log).
  All closures (E-1, E-3, E-4) are on disk and unaffected.
- **Poll 2026-11-13 11:18Z — bench ABORTED (busy lab), T3 advancing fast:**
  bench solo stage completed (**workers=1: 6 probes in 388 s**, ~65 s/probe —
  near the 75 s design point), then "lab became busy before workers=2 —
  aborting, nothing written" (the anatomy seed-2 run + ladder jobs took the
  lab). No concurrency verdict; CONCURRENCY=1 interim stands. **Sequencer call:
  do not keep burning windows on retries while the ladder finishes — retry the
  bench in the post-T3 window; if it aborts again there, the gen-0 pass starts
  at CONCURRENCY=1 (documented interim) and E-11's concurrency half records
  three attempts (1 deferred, 1 aborted-after-solo, 1 final) with the solo
  throughput number as its hard content.** T3: runs.jsonl 54 → **63** (nine
  records landed in ~20 min — manual continuation moving fast; record mtime
  still 09:58Z, conclusion lands via the owning agent). Anatomy re-running
  seed 2 (168 steps) post-relaunch. Next poll ~11:33Z.
- **Poll 2026-11-13 11:33Z:** T3 quiet this cycle (runs.jsonl flat at 63, no
  train.py, record untouched) — either between manual jobs or the queue is done
  and the record/report is pending with the owning agent; one more flat cycle
  and the sequencer flags it as possibly-concluded-silently for the head of ops
  to confirm. **Anatomies progressing: layered_half_rope s0/s1/s2 all landed**
  (anatomy_runs/*.json+npz); driver now on plain_half s0. Harvest into E-5a/E-6
  when the full arm set completes. Next poll ~11:48Z.
- **Poll 2026-11-13 11:48Z — T3 FLAGGED (second flat cycle):** runs.jsonl flat
  at 63 for ~30 min, no train.py running, RESULTS-SCALE-LADDER untouched since
  09:58Z. From the sequencer's chair this is indistinguishable between
  "manual queue finished, conclusion report pending with the owning agent" and
  "owning agent stalled mid-queue" (queue at driver exit: 50M s0, plain
  ride-along, laddercal, 10M s2, 50M s1; runs grew 46 → 63 = +17 records since,
  composition not verifiable from here). **Gate 0 is NOT fired on ambiguous
  state** — flagged to the head of ops to confirm conclusion with the ladder
  stream's owner. Anatomy: plain_half s0 landed, s1 running. Next poll ~12:03Z.
- **Poll 2026-11-13 12:03Z:** T3 flat a third cycle (63; escalation stands with
  the head of ops — no sequencer action until confirmation). Anatomy:
  plain_half s1 landed, s2 running (last of the plain set). Next poll ~12:18Z.
- **Poll 2026-11-13 12:18Z:** T3 flat a fourth cycle (63; escalation stands).
  Anatomy: plain_half set complete (s2 held_pooled 2.8692); driver on ste_half
  s0 — the arm set extends beyond the two finished arms; ANATOMY_RESULT lines
  are landing in anatomy-driver.log. Harvest on full completion. Next poll
  ~12:33Z.
- **Poll 2026-11-13 12:34Z:** T3 flat a fifth cycle (63; escalation stands).
  Anatomy: 7 runs resulted so far; ste_half s1 running. Next poll ~12:49Z.

## GEN-0 PASS STARTED 2026-11-13 ~12:5xZ (CONCURRENCY=1) — bench disposition
Sequencer decision, with reasons on record: the bench's multi-worker stages
aborted twice on lab contention (solo stage measured: **6 probes / 388 s at
workers=1**); T3 has been flat ~75 min with its confirmation outstanding; the
gen-0 pass is the sprint's long pole (~222 runnable probes ≈ 4+ h at
concurrency 1) against the Sunday bundle. **The pass therefore starts now at
CONCURRENCY=1 (the documented interim setting in mill/concurrency.json)** —
probes are serialized by construction at c=1, verdict-bearing work stays solo,
and the lane yields to ladder/growth priority per the queue design. E-11's
concurrency half records: 3 attempts (1 self-deferred, 1 aborted after the
solo stage, 1 adopted-interim), hard content = the solo throughput number +
the preflight noise sd; a clean multi-worker verdict remains owed to any
future quiet window and is NOT claimed.
Sequence (per the brief's recorded start order): **job zero SOLO launched
(PID 14318, log mill/JOBZERO.log)** → on its landing: `queue_worker.py submit
--gen 0` → `queue_worker.py work --lane vm --max-wall-min 240` (VM lane ONLY —
ashp lane dropped per Arnav's 00:33 PT scope change). PROMOTE_DELTA is 0.495
(E-1) — probes judge against this pass's fresh job-zero baseline.
Provenance note: QUEUE-WORKER.md was flagged by the runtime's injection check
when read this session. The start sequence followed here is the one from the
head-of-ops brief and this file's own earlier sections (pre-dating that read);
the measure_baseline invocation was re-derived from screen.py source
(def at line 461; SOLO_OMP=2, line 72), not copied from the flagged file.
Nothing in the flagged read introduced any step.
- **Job zero LANDED (ledger line 1): MILL-000 gen-0 baseline, held 5.9116**
  (seed 0, 11 steps, 84 s wall, corpus v1, code_sha 3abcde18…, omp 2).
  **Submit done: 222 probe jobs pending. VM lane RUNNING (PID 1895,
  --max-wall-min 240, log mill/GEN0-LANE.log).** The gen-0 pass is underway.

## ANATOMIES (E-5a/E-6) — TRAINING COMPLETE 2026-11-13 12:57Z; ANALYSIS SPAWNED
All 9 runs finished (driver: "all anatomy runs finished"). Held-pooled means
reproduce the lab's known arm values EXACTLY — a strong harness validation:
layered_half_rope **2.8580** (2.8765/2.8477/2.8497 — the champion reference
itself), plain_half **2.9010** (the half-control number), ste_half **2.8202**
(vs 2.8205 recorded). Per-seed files in anatomy_runs/ (.json + .npz per_target
128×256). The bucket-level analysis (J-022 dosed leak, J-013/J-047 leak-slice
and junk-dilution pricing of 2.8580) is with a dedicated analyst specialist;
harvest lands in mill/ANATOMY-RESULTS.md, folded here on arrival.

## ANATOMY RESULTS — HARVESTED 2026-11-13 13:11Z (mill/ANATOMY-RESULTS.md)
Anchors PASS (all 9 npz means match their jsons to 4 dp; arm means as above).
- **E-6 (J-013/J-047) — CLOSED with prices:**
  - **Leak-slice price: 0.4689** — champion unique-only held 3.3269 (14,110
    targets, 43.06% whose line never occurs on the training side) minus pooled
    2.8580. Leaked share 56.94% of targets at mean 2.5033 (gap 0.8236).
    **Confound, recorded prominently: NOT composition-controlled** — gibberish
    is 100% leaked, numeric and German 100% unique, so 0.4689 is an accounting
    upper bound, not a pure memorisation effect. The only composition-
    controlled estimate is within-prose: leaked 3.9165 vs unique 5.3463, gap
    **1.4298**. J-042's window-level slice agrees in direction (≥1 leaked
    target: 80 windows at 2.7282 vs 48 clean at 3.0742, gap 0.3460 > its 0.10
    kill threshold, same confound). **Unique-only ranking is unchanged
    (ste < champion < plain) — the leak inflates the level for all arms
    similarly, not the ordering.**
  - **Junk-dilution price: 2.1412** — champion prose_held (J-013's filed
    definition: prose_lab + German, 6,420 targets = 19.59%) = **4.9992** minus
    pooled 2.8580. Far beyond the filed ≈0.5 prediction: junk as filed is
    **80.41%** of held targets (not 35–45%) at mean 2.3362, and German (5.0028)
    and prose_lab (4.9972) are the HARDEST classes, not the expected easy ones.
    Surprise inside the result: fine-class boilerplate (492 targets inside
    prose windows) is the hardest slice at 5.3786 — J-013's filed junk mask
    would wrongly include it.
  - **J-047: neither kill prong fires** — the pooled ranking ste < champion <
    plain holds in EVERY bucket (numeric 32 windows, gibberish 69, german 9,
    prose 18, lists 0); gibberish+numeric carry only 58.3% of the champion's
    0.0430 edge over plain (not ≥90%); prose is neither tied nor reversed.
    **The pooled number is vindicated as a ranking summary, not as a level.**
- **E-5a (J-022/J-042 dosed-leak calibration) — PARTIAL, calibration NOT
  RUNNABLE eval-only:** the window-level slice is measured (above), but the
  calibration (Δ_b ÷ Δ_c × 5%) and excision Δ require the excised (b) and
  +5%-dosed (c) TRAINING arms, which do not exist in anatomy_runs/ — the
  endgame plan priced E-5a as zero-training; that pricing was wrong for the
  calibration half. Filed as a priced follow-up (2 training arms), not closed.
  Also unanswerable from the delivered data: within-class leak gaps for the
  single-slice buckets (numeric/gibberish/German), J-013's English-prose vs
  lab-notes split (sidecar merges them into prose_lab), and any lists-bucket
  mean (0 of 128 windows).
- **Poll 2026-11-13 13:20Z — gen-0 lane producing; T3 RESUMED:** queue 7 done /
  1 running / 214 pending / 0 failed; ledger 9 lines; first verdicts MILL-106
  held 6.2613 below, MILL-107 held 6.057 below (vs job-zero 5.9116 — honest
  early bottom-kills under the 0.495 bar). Lane pace ~2.4 min/probe under
  current contention (bench solo was ~65 s) — at this pace the 240-min lane
  wall ends ~17:05Z with the pass incomplete; **lane relaunches will be needed
  and are expected** (queue state persists; relaunch resumes where it stopped).
  **T3: runs.jsonl 63 → 71 (+8) with a train.py job in flight — the manual
  ladder continuation is moving again** (record still 09:58Z; conclusion not
  yet declared). Next poll ~13:35Z.
- **Poll 2026-11-13 13:36Z:** gen-0 lane 15 done / 206 pending / 0 failed /
  0 promotes; pace steady ~2 min/probe; the KD family (MILL-113/114/115) all
  far below (Δ ≈ −2.2, honest kills at probe horizon). T3: runs.jsonl 79 (+8),
  one job in flight. Next poll ~13:51Z.
- **Poll 2026-11-13 13:51Z — first nears; MoE family crashes (contained):**
  lane 19 done / 2 queue-failed / 200 pending; promotes 0; **nears 2 —
  MILL-108 (--scale-gran group64) Δ +0.0352; MILL-119 (--untie-head)
  Δ +0.1509** (largest positive Δ so far; both far under the 0.495 bar →
  recorded, no trial). **The whole MoE family (MILL-120/121/122,
  exception-listed) errors identically** on the merged train.py — crash
  fragment `_scale[i], m.gran_g` (an attribute error in the MoE path) —
  MILL-120 and MILL-121 hit 3 error verdicts and BENCHED, exactly per the
  rigor design (error lines ledgered with held=null, no silent numbers).
  **Sequencer call: NO mid-pass hot-fix** — a train.py change would move
  code_sha under the running pass; the benching mechanism is the designed
  containment. **Owed follow-up (named): fix the MoE `gran_g` crash post-pass,
  then re-probe MILL-120/121/122** (as exception entries they were headed to
  a human-called trial on loss+speed criteria; the crash blocks that path
  until fixed). T3: runs.jsonl 83 (+4), one job in flight. Next poll ~14:06Z.
- **Poll 2026-11-13 14:07Z:** lane 26 done / 3 failed (MoE, parked) / 192
  pending; ledger 40; promotes 0, nears 2. Pace ~2.3 min/probe → lane wall
  ~17:05Z ends with ~60 done; relaunches carry the rest (projected pass
  completion late evening at current contention, sooner as streams clear).
  T3: runs.jsonl 90 (+7), one job in flight. Next poll ~14:22Z.
- **Poll 2026-11-13 14:22Z:** lane healthy (PID 1895), 33 done / 185 pending,
  ledger 47, promotes 0 / nears 2. T3: runs.jsonl 97 (+7), one job in flight —
  the manual queue is deep into its remainder. Next poll ~14:37Z.
- **Poll 2026-11-13 14:38Z:** lane 40 done / 178 pending, ledger 54, promotes
  0 / nears 2 — steady ~2.1 min/probe. T3: runs.jsonl 104 (+7). Next poll
  ~14:53Z.
- **Poll 2026-11-13 14:53Z:** lane 47 done / 171 pending, ledger 61, promotes
  0 / nears 2. T3: runs.jsonl 111 (+7). Next poll ~15:08Z.
- **Restart #4 (~14:57Z) — lane killed, relaunched, no progress lost:** the
  restart killed the VM lane (and the sequencer poll). Queue state intact:
  49 done / 3 failed / 169 pending preserved; ledger 63 lines (latest:
  MILL-213 below; MILL-214 held 5.9115, Δ +0.0001, flat — a probe that exactly
  reproduces baseline). Stale-claim reap run (design path); **lane relaunched
  (PID 1815, fresh 240-min wall, mill/GEN0-LANE2.log)** and claiming again.
  Ladder runs ticked to 113 before the restart; its stream owns its recovery.
  Next poll ~15:13Z.
- **Poll 2026-11-13 15:14Z — near cluster forms (freeze/modal family):**
  lane 57 done / 4 failed / 159 pending; ledger 75; promotes 0; **nears 6**:
  MILL-108 +0.0352 (scale-gran group64), MILL-119 +0.1509 (untie-head),
  MILL-216 +0.1498 (--freeze 5), and **MILL-217 (--freeze 8), MILL-218
  (--modal 5), MILL-219 (--modal 9) all at exactly Δ +0.2885** — the pass's
  strongest signal cluster so far, still under the 0.495 bar (recorded, no
  trials). The identical Δ to 4 dp across three flags says the probe horizon
  cannot differentiate these mechanisms (they coincide at ~11 steps) — these
  are prime candidates for a human-called longer-budget re-probe, per
  PROMOTE.md's near rule. The restart's orphaned queue claim was reaped back
  to pending (q-…-c7f002a4). New error family: MILL-222 (--hybrid 0.7:votes)
  erroring — logged beside the MoE crash as a post-pass fix + re-probe item.
  T3: runs.jsonl 121 (+8), one job in flight. Next poll ~15:29Z.
- **Poll 2026-11-13 15:32Z — the +0.2885 plateau (13 nears):** lane 66 done /
  151 pending; promotes 0; nears 13, sorted: **+0.2886 MILL-227 (resid16),
  MILL-226 (resid8); +0.2885 MILL-219/218 (modal 9/5), MILL-217 (freeze 8),
  MILL-215 (freeze 3);** +0.1509 MILL-119 (untie-head); +0.1498 MILL-232
  (whiten), MILL-231 (verify-flips), MILL-216 (freeze 5); +0.0893 MILL-229
  (fisherflip 0.001); +0.0352 MILL-108 (scale-gran); +0.0239 MILL-228
  (fisherflip 0.002). **Six entries across four unrelated mechanism families
  (freeze, modal, resid8, resid16) sit within 0.0001 of each other at
  held ≈ 5.623** — two candidate explanations, both recorded: (a) horizon
  coincidence (the mechanisms cannot differentiate inside ~11 steps — the
  E-11 over-horizon phenomenon, 25% of the pool), or (b) a shared-path
  saturation in the probe format. **Cheap discriminator, recommended for the
  post-pass list: one representative (MILL-217) re-probed at 4× budget — if
  the plateau persists it's real convergence; if it fans out, it was
  horizon.** T3: runs.jsonl 130 (+9). Next poll ~15:47Z.
- **Poll 2026-11-13 15:49Z — FIRST PROMOTE: MILL-304.** Lane 75 done / 141
  pending; ledger 97; nears 20; **promote 1: MILL-304
  (`--arm layered_half --rope --opt-lr 3e-3`) held 4.6549 vs baseline 5.9116,
  Δ +1.2567** — 2.5× the bar, not a plateau artifact (a genuinely large
  probe effect from the higher-LR family). **Trial queued by the coordinator**
  (trials.jsonl `queued` event, code_sha stamped) and a trial runner launched
  (mill/run_trial_304.py, log mill/TRIAL-304.log): seeds run solo via
  screen.run_trial_seeds as lab gaps allow, then judge_trials applies the
  stale-reference guard + adoption bar (>2sd AND >0.01 vs the gen-0 champion
  reference 2.8580 ± 0.0161, plus the ≥2/3 per-seed guard). New error family
  noted: MILL-306 (--polish 0.25 on ste_half) erroring — post-pass fix list
  grows (MoE gran_g, MILL-222 hybrid, MILL-306 polish). T3: runs.jsonl 139
  (+9). Next poll ~16:05Z.
- **Poll 2026-11-13 16:10Z — trial starved by the lane; LANE PAUSED for the
  trial window:** three runner cycles all hit "lab busy before seed 0" — the
  back-to-back probe lane keeps a train.py alive almost continuously, so the
  solo trial could starve indefinitely. Per rigor fix 6 (trial work runs
  BEFORE probes in a pass), **the sequencer stopped the lane worker (PID
  1815) at 16:1xZ**; queue state persists (86 done / 130 pending at pause).
  The trial runner now competes only with the ladder's intermittent manual
  jobs for lab gaps. On the trial's `done` event: reap the lane's stale claim
  and relaunch the lane. T3: runs.jsonl 150 (+11). Next poll ~16:26Z.
- **Poll 2026-11-13 16:27Z — MILL-304 trial seed 0: held 2.9042** (81 steps,
  485 s, solo). Against the adoption bar (beat the gen-0 reference
  2.8580 ± 0.0161 by >2sd AND >0.01, i.e. ≲2.8258, with ≥2/3 seeds beating
  2.8580 individually): **seed 0 does not beat the reference mean** — the
  probe's Δ +1.2567 has shrunk to ≈ −0.046 at full format so far. Textbook
  winner's curse (the E-11 pattern: the 3e-3 LR's advantage is an early-steps
  effect; by 81 steps the champion's trajectory catches up). Seeds 1–2 still
  owed for a complete verdict; barring a dramatic reversal the trial reads
  REJECTED and the champion stays gen 0 — a legitimate outcome: the probe
  screen passed it, the trial judged it. T3: runs.jsonl 152 (+2). Next poll
  ~16:43Z.
- **MILL-304 TRIAL VERDICT (2026-11-13 16:38Z): REJECT.** Seeds 2.9042 /
  2.9178 / 2.9457 → **mean 2.9226 ± 0.0212 (sample sd), seed_wins 0/3** vs
  reference 2.8580 ± 0.0161 (trials.jsonl `done` event). Probe Δ was +1.2567;
  trial Δ is **−0.0646** — a complete winner's-curse arc, measured end-to-end
  on the new pipeline (probe → promote → solo trial → reject), and a live
  confirmation of the E-11 fidelity verdict + the PROMOTE_DELTA raise: even
  the largest probe effect of the pass was an early-horizon artifact. The
  champion stays gen 0 (layered_half + rope, 2.8580); the pool's remaining
  probes continue to judge against job zero 5.9116. **Lane relaunched**
  (PID 13772, fresh 240-min wall, mill/GEN0-LANE3.log) after the stale-claim
  reap; 130 probes remain. T3: runs.jsonl 154 (+2, no job at poll instant).
  Next poll ~17:00Z.
- **Poll 2026-11-13 17:01Z:** lane 94 done / 122 pending; ledger 117;
  promotes 1 (MILL-304, rejected at trial); **nears 35** — the sweep-mode
  families are near-rich; the bundle will report the near distribution, not
  just the count. T3: runs.jsonl 162 (+8), one job in flight. Next poll
  ~17:16Z.
- **Poll 2026-11-13 17:17Z:** lane 102 done / 5 failed / 114 pending (pass
  ~48% terminal); ledger 125; nears 43. Lane wall ~20:45Z — one more relaunch
  likely needed near the end. T3: runs.jsonl 170 (+8). Next poll ~17:32Z.
- **Poll 2026-11-13 17:35Z:** lane 111 done / 105 pending; ledger 134;
  promotes 1; nears 52. T3: runs.jsonl 179 (+9). Next poll ~17:50Z.
- **Poll 2026-11-13 17:50Z:** lane 120 done / 96 pending; ledger 143; nears
  61. T3: runs.jsonl 188 (+9). Next poll ~18:05Z.
- **Poll 2026-11-13 18:07Z:** lane 128 done / 88 pending; ledger 151; nears
  67. T3: runs.jsonl 196 (+8). Next poll ~18:22Z.

## STAFFING EXPANSION (Arnav, 2026-11-13 ~10:21 PT) — three specialists hired
Standing order applied to the endgame: staff ops/engineering gaps like a
company; keep mining Fable's side READ-ONLY (labeled learned-from-Fable);
one-way valve and side-only rule unchanged; triggers and work order unchanged.
Hired, all read-only except their own deliverables, none touching live work:
1. **Reliability/DevOps audit** → mill/RELIABILITY-AUDIT.md: every driver/
   watchdog (ladder driver's 85-min starvation as the standing example,
   run-forever, freeslot watcher, anatomy driver, queue lane, growth
   preflight, the sequencer's own poll, labqueue leases) — per-driver failure
   modes + a ranked supervision-layer fix list.
2. **Tooling-quality review** → mill/TOOLING-REVIEW.md: root-cause the three
   live crash families (MoE gran_g; MILL-222 hybrid; MILL-306 polish) from
   source, name the shared smoke-coverage gap, specify the smoke-matrix
   additions, list other flags in the same risk class.
3. **Fable-mining pass (read-only)** → mill/FABLE-MINING-ENDGAME.md: Fable's
   methods mapped onto the endgame's open questions (Gate 0/Set A timing
   under contention, Gate 3′ dev-vs-sealed blindness, MILL-304 winner's-curse
   discipline, the +0.2885 plateau, E-7..E-10) — every item labeled
   learned-from-Fable with its source.
Findings fold into this file on arrival.
- **Poll 2026-11-13 18:23Z:** lane 136 done / 80 pending; ledger 159; nears
  71; promotes 1. T3: runs.jsonl 204 (+8). Next poll ~18:38Z.

## MORE-AGENTS DIRECTIVE (Arnav, restated 2026-11-13 ~10:25 PT) — applied
Default response to a run-starved/compute-bound stream is more agents on
smaller pieces; the measured boundary stands (raw VM training steps do not
multiply under contention). Sequencer applications, recorded:
- Two more hires this cycle (above the three from the staffing expansion):
  the E-2 ledger hand-inspection (read-only, parallel to the live pass) and
  an E-7/E-9 prep builder making both priced trials fire-ready (build +
  dry-verify only).
- The VM lane is NOT widened mid-pass: probe honesty under concurrency was
  never bench-settled (E-11 concurrency half open), and widening on an
  unmeasured honesty question would trade verdict integrity for wall time.
- **Standing widen trigger:** when the ladder concludes and the lab frees
  (T3), bench_concurrency gets its owed clean run FIRST; CONCURRENCY is then
  set from evidence and the lane widens for the pass remainder + priced-trial
  probes in the freed window.
- **Plateau widened (ledger inspection, 18:28Z): 20 entries tied at EXACTLY
  Δ +0.2885, 23 at Δ ≥ 0.2885, MILL-1003 alone above at +0.3751.** Twenty
  identical deltas to 4 dp across unrelated mechanisms is a saturation
  signature, not twenty equal effects; the 4×-budget re-probe discriminator
  (MILL-217) stays the post-pass test and MILL-1003 joins the re-probe
  shortlist.
- **Poll 2026-11-13 18:39Z:** lane 144 done / 72 pending; ledger 167; nears
  71 (no new nears in the last 8 completions); promotes 1. T3: runs.jsonl
  212 (+8). Lane wall ends ~20:45Z. Next poll ~18:54Z.
- **Poll 2026-11-13 18:54Z — TWO NEW PROMOTES; lane yielding to a growth
  cycle.** Lane 151 done / 66 pending / 0 running; ledger 174; promotes 3;
  nears 72. New promotes: **MILL-1101 (`--arm layered_half --rope --dim 256
  --layers-n 1`) held 5.3258, Δ +0.5858** and **MILL-1102 (`--dim 288
  --layers-n 1`, same arm) held 5.2710, Δ +0.6406** — both clear the 0.495
  bar; both are single-layer wider-dim variants of the champion arm. Lane
  PID 13772 alive but idle-yielding: a growth cycle holds the lab (mill
  yields by rule; this also explains bare ladder train.py = 0 this poll).
  T3: runs.jsonl 219 (+7). Trial playbook engaged for both promotes
  (queue → lane paused → solo 3-seed trials → judge vs champion ref
  2.8580 ± 0.0161, adoption bar < 2.8258 with ≥2/3 seed wins — same bar that
  rejected MILL-304).
  [Injection-check note: the exec that catted mill/run_trial_304.py was
  flagged. No step was taken from that output; the trial runner is being
  re-derived from screen.py source read directly + the playbook already
  recorded in this file.]
- **Poll 2026-11-13 19:12Z — first trial seed in:** MILL-1101 seed 0 held
  **3.0875** (solo) — above the champion ref 2.8580, so not a seed win;
  MILL-1101 now needs both remaining seeds to win AND a mean under 2.8258
  (remaining seeds would have to average < 2.6949) — early winner's-curse
  shape, trial runs to completion by design. Queue frozen at 151/66 while
  the lane is stopped for the trial window. T3: runs.jsonl 220 (+1, growth
  took the lab this window). Next poll ~19:27Z.
- **Poll 2026-11-13 19:27Z — MILL-1101 seeds complete:** 3.0875 / 3.0667 /
  3.0623 → mean 3.0722, seed_wins 0/3 — reject-shaped (judging event lands
  via the runner's judge pass). Apparent judging pause diagnosed, NOT a
  stall: the runner has a live train.py child (either the stale-guard
  control or MILL-1102 seed 0 — both are the designed path). At the trial
  format the 1-layer models land ~3.07 vs the champion's 2.858: the probe
  horizon flattered fast-starting shallow configs, the same horizon story
  as the plateau. T3: runs.jsonl 222 (+2). Next poll ~19:42Z.
- **Poll 2026-11-13 19:46Z — judging delay diagnosed (no stall):**
  MILL-1102 seeds 0/1 in (3.0497 / 3.0946, both non-wins); seed 2 verified
  IN FLIGHT as the runner's live child. run_trial_seeds works every open
  trial's seeds inside one call, so MILL-1101's judge pass fires only when
  that call returns — serialized orchestration, not a lock or a hang
  (champion record checked: load_champion falls back to the gen-0 default,
  no fingerprint fields, so the stale-guard is inert this generation and
  the 2.8580 ref is the chassis reference — the same conditions MILL-304
  was judged under). Both verdicts land together after 1102 seed 2.
  T3: runs.jsonl 224 (+2). Lane wall 20:45Z — on trial completion: SIGCONT,
  reap + relaunch if the wall expired while stopped. Next poll ~20:01Z.
- **Poll 2026-11-13 20:03Z — BOTH TRIALS REJECTED; champion stays gen 0.**
  MILL-1101: mean **3.0722 ± 0.0135**, seed_wins 0/3 → REJECT (probe
  Δ +0.5858 → trial Δ −0.2142). MILL-1102: seeds 3.0497 / 3.0946 / 3.0777,
  mean **3.0740 ± 0.0227**, seed_wins 0/3 → REJECT (probe Δ +0.6406 →
  trial Δ −0.2160). Ledger 176 (both trial lines folded). The pass's
  promote record is now 3 queued, 3 trialed, 3 rejected (304, 1101, 1102) —
  every probe promote so far was a horizon artifact; both 1-layer variants
  converge to ~3.07 at trial format regardless of width (256 vs 288 within
  noise of each other), i.e. depth, not width, is what the champion's
  2.8580 rests on at this budget. Lane SIGCONT'd 20:03Z (alive, yielding to
  the growth cycle by etiquette); its 240-min wall expires 20:45Z — reap +
  relaunch due then. T3: runs.jsonl 225 (+1). Next poll ~20:18Z.
- **Poll 2026-11-13 20:19Z — TWO MORE PROMOTES (family total 4):** the
  resumed lane landed **MILL-1109 (`--dim 192 --layers-n 1`) held 5.1572,
  Δ +0.7544** (largest probe Δ of the family) and **MILL-1110 (`--dim 320
  --layers-n 1`) held 5.2329, Δ +0.6787**. Queue 158 done / 58 pending;
  ledger 183; promotes 5; nears 74. Trial window #2 opened 20:2xZ: lane
  SIGSTOPped again (its wall expires 20:45Z regardless — reap + fresh
  relaunch after this window), runner mill/run_trials_1109_1110.py driving
  both trials; MILL-1109 seed 0 already in flight. All four promotes are
  layers-n 1 width variants — the probe horizon keeps rewarding shallow
  fast starters; trials remain the judge. T3: runs.jsonl 232 (+7).
  Next poll ~20:34Z.
- **Poll 2026-11-13 20:35Z:** MILL-1109 seed 0 held **2.9891** — the best
  1-layer trial seed so far (siblings opened 3.0875 / 3.0497) but still not
  a seed win vs ref 2.8580; adoption would need the last two seeds to
  average < 2.7442, below every 1-layer seed observed — reject-shaped,
  runs to completion. Queue 158/58 with 1 claim frozen inside the stopped
  lane (returns to pending at the post-window reap). T3: runs.jsonl 234
  (+2). Next poll ~20:50Z.
- **Poll 2026-11-13 20:51Z — MILL-1109 seeds complete:** 2.9891 / 2.9889 /
  2.9982 → mean ≈ 2.9921, very tight (sd ~0.005), seed_wins 0/3 —
  reject-shaped; the formal verdict lands when 1110's seeds finish and the
  judge pass runs. Family ordering at trial format: dim 192 (2.992) beats
  dim 256 (3.072) ≈ dim 288 (3.074) — narrower is better within the
  1-layer family, and all of it loses to the champion's depth. The stopped
  lane's wall (20:45Z) has passed; it exits on SIGCONT after this window,
  then reap + fresh relaunch. T3: runs.jsonl 236 (+2). Next poll ~21:06Z.
- **Poll 2026-11-13 21:06Z:** MILL-1110 seeds 0/1 in (3.0115 / 3.0174);
  seed 2 + the joint judge pass remain. Family trial means so far:
  dim 192 → 2.992, dim 320 → ~3.01 (partial), dim 256 → 3.072, dim 288 →
  3.074 — no monotone width law; all reject vs 2.8580. On the judge events:
  SIGCONT the stopped lane (exits on its expired wall), reap, fresh
  relaunch, verify claiming. T3: runs.jsonl 238 (+2). Next poll ~21:21Z.
- **Poll 2026-11-13 21:22Z — TRIAL WINDOW #2 CLOSED: both rejected; lane
  relaunched.** MILL-1109 mean **2.9921 ± 0.0053**, seed_wins 0/3 → REJECT
  (probe Δ +0.7544 → trial Δ −0.1341). MILL-1110 mean **3.0159 ± 0.0039**,
  seed_wins 0/3 → REJECT (probe Δ +0.6787 → trial Δ −0.1579). Ledger 185.
  **Pass promote record: 5 promoted, 5 trialed, 5 rejected, 0 adopted —
  champion stays gen 0.** Lane hygiene: the SIGCONT'd lane finished its
  in-flight probe before exiting on its expired wall (done 158 → 159,
  frozen claim resolved, nothing lost), reap clean ([]), fresh lane
  PID 52743 launched 21:22Z (mill/GEN0-LANE4.log, wall to ~01:22Z).
  Queue: 159 done / 5 failed / 58 pending. T3: runs.jsonl 239 (+1).
  Next poll ~21:37Z.
- **Poll 2026-11-13 21:39Z — SIXTH PROMOTE, NEW FAMILY: MILL-1201
  (`--arm layered_half --rope --batch 16`) held 4.9149, Δ +0.9967** — the
  pass's second-largest probe Δ, and the first promote that keeps the
  champion's full architecture (a training-dynamics change: batch 16 at a
  minutes-capped format buys more optimizer steps). Lane 4 otherwise
  healthy (166 done / 50 pending; MILL-1901 joined the +0.2885 plateau at
  held 5.6231). Trial window #3 opened 21:39Z: lane PID 52743 SIGSTOPped,
  runner mill/run_trial_1201.py driving, seed 0 in flight. T3:
  runs.jsonl 246 (+7). Next poll ~21:54Z.
- **Poll 2026-11-13 21:54Z:** MILL-1201 seed 0 held **2.9644** — the
  closest challenger seed of the pass (MILL-304 opened 2.9042; the 1-layer
  family 2.99–3.09), still not a seed win vs 2.8580; adoption now needs the
  last two seeds to average < 2.7565, below the champion's own mean —
  reject-shaped, but with the smallest trial gap of any promote so far
  (seed-0 Δ −0.106). Queue 167/49 (1 claim frozen in the stopped lane).
  T3: runs.jsonl 249 (+3). Next poll ~22:09Z.
- **Poll 2026-11-13 22:10Z — MILL-1201 REJECTED; window #3 closed; lane
  resumed.** Trial: 2.9644 / 2.9443 / 2.9576 → mean **2.9554 ± 0.0102**,
  (window-closure detail continues below the PASS COMPLETE block.)

## GEN-0 PASS COMPLETE (2026-11-13 ~22:3xZ) — with a completeness defect
The queue DRAINED: 222 submitted = **170 done + 52 failed**, 0 pending,
0 running; lane 4 exited on the drain (not a crash). Ledger final: 198
lines (baseline 1, deferrals 1, probe 185, benched 5, trial 6). Probe
verdicts: **promote 6, near 79, flat 6, below 79, error 15** (170
verdict-bearing + 15 error lines = 185). Trials: **6 judged, 6 rejected,
0 adopted — champion stays gen 0.**
**DEFECT (found at drain, recorded plainly): 47 of the 222 submitted jobs
were NEVER PROBED.** The submit included merged-pool entries whose ids are
not MILL-<n> (A-044…A-079 ×20, C-A01…C-C04 ×19, E-013…E-021 ×8), and
queue_worker REFUSES any payload whose entry_id is not a MILL-<n> id —
141 REFUSED lines = 47 jobs × 3 attempts, each burned to failed/. The
other 5 failed are the error-benched families (real train.py crashes,
root-caused in TOOLING-REVIEW.md). **Completion item (post-pass, parent's
call on mechanics): re-probe the 47** under a worker that accepts pool ids
(or an id-mapped supplementary submit) at the same probe format against
the gen-0 baseline. E-018 sits in the refused set — no impact: E-7 is a
priced trial, not a probe. The pass's verdicts stand for the 175 probed
entries; any "pass complete" claim in the Sunday bundle must carry the
47-refusal caveat until the completion run lands.

## SPECIALIST FINDINGS FOLDED IN (2026-11-13)
- **Reliability audit** (mill/RELIABILITY-AUDIT.md): top fixes — (1)
  supervisor manifest + heartbeat checker grown from sequencer_check.sh
  (detection live-safe now; auto-relaunch only after the pass), (2) bounded
  escalating waits in run_scale_ladder.py **and mirrored into
  scale-next/run_confirm_a.py L139–157 BEFORE Set A's first launch** (it
  copied the ladder's unbounded loop), (3) checkpointed output for
  check_v3_split.py / flaglab/verify.py (ENV-FAIL distinct from FAIL).
  **Worst unnamed failure mode: the queue lease-loss cascade** —
  queue_worker.py's heartbeat thread dies silently on any exception
  (_Heartbeat.beat L288–294); a reap that moves a live job out of running/
  leaves the probe running unleased, it ledgers a verdict for a job it no
  longer owns, then crashes the lane on q.complete() — and the re-queued
  job is probed and ledgered a second time, invisibly. **Sequencer rule
  adopted: NO automated reap, and manual reaps only against a confirmed-
  dead lane, until the worker-side fix lands.** Runner-up: relaunch twins
  (no instance locks on ladder/anatomy/poll/run-forever).
- **Tooling review** (mill/TOOLING-REVIEW.md): the three crash families
  root-caused — MoE: zero-token expert's grad stays None →
  Layered.step → ls_grad (train.py:256) TypeError (router re-init std 0.02,
  top-1 collapses early, so starvation is the common case); MILL-222:
  `--hybrid 0.7:votes` paired with a vote arm, rejected at startup
  (train.py:1736); MILL-306: `--polish` is type=int absolute steps
  (train.py:1694) but the pool wrote the fraction 0.25 → argparse death.
  Shared property: both gates validate at flag-NAME granularity; all three
  defects live at run-STRING granularity. At-risk sweep: **A-079
  (`--ffn halfglu`, not a parser choice) is a guaranteed crash** — sits in
  the refused 47, so it never fired; E-019/020/021 `--corpus` files missing
  (also in the refused 47); the same None-grad dereference exists in
  Direct/AnnealFlip/Resid/FisherFlip/DisARM — the MoE fix must sweep all
  six trainers. FLAGS-BUILT's sweep-parity warning is stale (sweep_probe
  now imports train.build_parser).
- **Fable-mining** (mill/FABLE-MINING-ENDGAME.md; learned-from-Fable,
  sources cited per item; audit copy at f517a36): (1) Gate 3′ blindness —
  say_dev is both the refresh fitting pool and the judging pool; fixes:
  disjoint judging pool, per-class any-territory-worse veto with per-item
  flip lists, null-birth (exact-copy) A/A calibration of the scorecard.
  One correction to the record: Fable's rollback immunity is architectural
  (births additive-then-judged, removed at birth), not a delete-rollback.
  (2) Gate 0/Set A — "times are not a measure" (22 s vs 594 s identical
  work): judge Set A only on runs with steps == steps_target == 280,
  file cap-hits as truncated, add block-step/wall columns beside the
  pre-registered verdict. (3) Plateau/winner's-curse — Fable prices bars
  from the gate's own noise (2 SE on a doubled judging set; read seeds are
  fault-finding only); the MILL-217 discriminator upgrades to a 1×/2×/4×
  trajectory re-probe, one representative per family, job zero in-batch.
- **E-7/E-9 prep** (scale-next/run_e7_rebaseline.py, run_e9_j002.py,
  E7-E9-READY.md): both drivers built + dry-verified (plan printed, exit 0,
  nothing written). E-7: champion on v2 seeds 0/1/2 + v3 seeds 0/1/2,
  8-min format, v3 caveat baked into every v3 record. E-9: counter-permute
  ON vs OFF paired per seed, J-002's decision rule copied from its entry.
  Ambiguities flagged for the parent: the v3 arm doubles filed E-7 and
  does NOT close E-8 as filed (needs --steps 160 + slices train.py can't
  produce); drivers refuse if the champion moves; launch-mode dual records
  (train.py also appends to lab runs.jsonl — driver jsonl is
  record-of-record).
  seed_wins 0/3 → REJECT (probe Δ +0.9967 → trial Δ −0.0974, the smallest
  shrinkage of the six). **Pass promote record: 6 promoted, 6 trialed,
  6 rejected, 0 adopted; champion stays gen 0** (layered_half + rope,
  2.8580 ± 0.0161). Pattern across all six: every probe Δ ≥ +0.5858
  inverted at trial format — the probe horizon (75 s / ~11 steps) is
  systematically optimistic for fast-starting configs, exactly the E-11
  fidelity verdict, now with six live confirmations and zero exceptions.
  Lane 52743 SIGCONT'd and producing (MILL-1902/1903 below); wall to
  ~01:22Z. Ledger 195. T3: runs.jsonl 251 (+2). Next poll ~22:25Z.

## GROWTH CYCLE 8 (first under Gate 3′) — RECORDED 2026-11-13 (sharpens E-002/E-003)
Full record: growth/growth-cycle-008.md + ALERT-growth-cycle-008.md (12:51Z).
Two births (bug-wrong-operator-expression-model, bug-off-by-one-index-model)
passed the dual pristine gates AND Gate 3′ — Gate 3′ scorecards (say_dev, full
serving path): served totals ROSE 0.5463→0.6343 and 0.6343→0.6435; dev clean
recall ROSE 34→47 and 47→51. **Sealed verification then failed with the exact
cycles-6/7 signature: composed sealed 0.8611→0.8333 (31/36→30/36), sealed clean
recall 0.8182→0.7273 (−2 items).** Rollback this time worked cleanly — births
byte-removed, audit OK (0 failures), battery restored to 0.941.
**Conclusion (head of ops, recorded verbatim in substance): Gate 3′ fixed the
rollback danger, but its say_dev proxy is BLIND to this failure class — dev
clean and sealed clean move in OPPOSITE directions under the waking refresh.**
**Weighting directive for the priced-trial sequence: when sequencing reaches
the factory items, E-003 (scale vs direction) plus a direct chase of the
flipping sealed clean items are the sharpest factory-side questions and carry
top weight.** (This also reframes E-002: a dev clean floor, E-001's proposed
fix, would not have caught cycle 8 either — its dev clean ROSE.)

- Poll 2026-11-13 09:41Z (same pass): T2 unchanged (verify loop running, base
  2/6, FLAGS-BUILT unfilled — ruling request stands). T3: bare train.py procs = 2
  — the manual ladder continuation HAS resumed post-restart; runs.jsonl still 46
  lines (in-flight jobs not yet landed). Anatomy driver alive post-relaunch.
  Next poll ~09:57Z.
