# QUEUE-WORKER — gen-0 pass queue worker, build report

<!-- Muse's work — Muse's side of the BitNet lab. Fable's side untouched. -->

Built 2026-11-12 (code only; NO live probes run, live queue/ledger untouched).
Implements the minimal wiring owed at E-3 in ENDGAME-STATUS.md's
DECOMPOSITION DIRECTIVE §1: claims → runs → ledgers → completes/fails.

## Files

- `mill/queue_worker.py` — the whole deliverable (submitter + worker +
  self-test in one thin file; all execution and ledger logic is delegated
  to `mill/screen.py` / `mill/sweep_probe.py` / `compute/queue/labqueue.py`,
  nothing re-implemented).
- This report. ENDGAME-STATUS.md was NOT edited (executor folds this in);
  train.py / train_next.py NOT touched.

## Design, as built

- **Jobs.** One job per runnable pool entry: `kind=probe` (labqueue
  priority 20), payload `{entry_id, gen, probe_minutes, mode, argv:<token>}`,
  per-job queue timeout = probe budget + 900 s (the reap threshold).
  Trials stay `kind=trial` priority 10, submitted by the coordinator —
  this worker never submits, claims, or judges them.
- **Submitter** (`submit` subcommand): runnable subset =
  `screen.parse_pool()` filtered by `screen.validate()` against
  `train.py --help` (the post-merge flags, exactly screen.py's own
  runnability test), minus entries already ledger-done/benched for the
  generation (`screen.ledger_state()`), minus MILL-000. Idempotent:
  entries with a probe job already pending/running for that
  entry+generation are skipped ("already queued"). Deferrals are
  ledgered through `screen.ledger_deferrals()` — no new ledger lines
  invented anywhere.
- **Hard probes-only property.** Lanes claim with `kinds=["probe"]` AND
  `validate_job()` re-checks every claimed job before the executor is
  touched: kind ≠ probe, a `shell` payload, any verdict-bearing payload
  key (trial/judgment/confirmation/control/baseline/job_zero/verdict/…),
  a non-`MILL-<n>` entry id, or MILL-000 itself → refused, queue job
  failed (retry→park), never executed, never ledgered as a probe.
  The payload's argv is never executed: the worker looks the entry up in
  IDEA-POOL.md by id and re-validates its run string from the pool.
- **Ledgering.** Only via `screen.ledger_probe()` (stamp/code_sha,
  verdict vs this pass's job-zero baseline, exception list, error-bench
  after 3) with the job's own probe budget. A probe with a held value →
  queue `complete` (result JSON: entry, gen, lane, held, verdict, delta;
  a "promote" verdict is noted as coordinator's-trial business, NOT
  queued from here). No held value → the error line is ledgered and the
  queue job is `fail`ed, so labqueue's retry policy mirrors screen's
  error re-queue. A probe preempted before it ran (sweep MILLSTOP) →
  queue `release`, nothing ledgered — mirroring screen's lane behaviour.
  No baseline for the generation yet → `release` unexecuted; the lane
  waits instead of spinning.
- **Heartbeat.** A daemon thread heartbeats the claimed job every 20 s
  for the whole execution; completion/failure stamps it finally.
- **VM lane.** Sweep-mode entries: `screen.run_sweep_batch()` with a
  batch of exactly 1 (`mill/sweep_probe.py`); process-mode entries:
  `screen.run_subprocess_probe()`. OMP from `screen.load_concurrency()`
  (default 2). Yields without claiming while `screen.lab_busy()` is
  non-None.
- **ashp lane.** Reached ONLY via
  `weights-reader/tools/ashp_ssh.sh`. Preflight before every claim:
  reachable + GPU sensor ≤ 65 °C start gate + zero other python
  processes (one heavy job at a time); any failure = idle-report, no
  claim, no crash. Probes run detached (SSH drops at ~23 s, per
  COMPUTE-ASHP.md): an EncodedCommand PowerShell launch
  (Start-Process) runs ashp's `train.py` copy in
  `D:\muse\compute-bench` under `D:\muse\work\edit-lab\venv` at
  OMP/MKL = 8, writing `out.txt`/`done.txt` under
  `queue-probes\<tag>\`; the lane polls with short SSH calls, aborts
  best-effort if the sensor passes 80 °C, and parses the RESULT line.
  Ledger lines from this lane are stamped `omp=8`, so ashp numbers never
  mix silently with VM numbers. Assumption to re-check at E-3: ashp's
  train.py copy must carry the same post-merge flags as the VM's — a
  drifted copy surfaces as probe error lines, not silent wrong numbers.
- **Flags/arms** are read once per lane start, not per job.

## Dry verification (the only runs made)

- `python3 -m py_compile mill/queue_worker.py` — OK.
- `python3 mill/queue_worker.py selftest` — **17/17 checks passed**,
  against a scratch LabQueue under `/tmp/queue-worker-selftest-*` with
  fake entries/lanes (never the live queue): submitter submits exactly
  the runnable entries (MILL-000 and deferred excluded), priority 20,
  payloads carry entry ids; re-submit idempotent; dry-run submitter
  writes nothing; a trial job in the queue is never claimed and
  `validate_job` refuses it; job-zero / confirmation / shell payloads
  refused pre-execution; a poison verdict-bearing probe job is failed
  unexecuted; an error probe is ledgered once and queue-failed for
  retry; an unreachable ashp lane idle-reports and claims nothing; a
  missing baseline releases the job unexecuted.
- `--dry-run` against a scratch root `/tmp/qw-dry/state`:
  `submit --dry-run` → **34 would submit, 0 already queued, 0
  ledger-done, 345 deferred** at today's pre-merge flag state (the
  deferred count falls as E-3's flags land); `work --lane vm --dry-run`
  and `work --lane ashp --dry-run` print the claim plan and execute
  nothing. Scratch state dirs verified empty afterwards; the live
  `compute/queue/state/` was never instantiated by these runs and
  `mill/ledger.jsonl` still does not exist.

## Starting the live gen-0 pass (executor — after the E-3 merge)

Prerequisites per ENDGAME-STATUS.md: E-3 merged (FLAGS-BUILT green);
the free-slot order stands (preflight noise → bench_concurrency →
gen-0 pass), and if preflight's required PROMOTE_DELTA exceeds 0.05 it
is raised in screen.py/PROMOTE.md before any pass is judged. Then,
from `~/workspace/edit-lab/bitnet-lab`:

```bash
# 1. Coordinator SOLO — job zero for gen 0 (never queued):
python3 -c "import sys; sys.path.insert(0, 'mill'); import screen; \
c = screen.load_champion(); \
print(screen.measure_baseline(c, screen.SOLO_OMP, 1.25))"
#    (lanes release-and-wait if started before this lands, so order
#     with step 3 is not fragile — but job zero first is the clean run)

# 2. Submit the gen-0 probe jobs (idempotent; safe to re-run):
python3 mill/queue_worker.py submit --gen 0

# 3. The two lanes (separate terminals / nohup; one job at a time each):
python3 mill/queue_worker.py work --lane vm   --max-wall-min 240
python3 mill/queue_worker.py work --lane ashp --max-wall-min 240

# Monitor:  python3 compute/queue/labqueue.py stats
# Fallback if the wiring slips: mill/run-forever.sh (screen.py serial
# pass), per the directive's own note.
```
