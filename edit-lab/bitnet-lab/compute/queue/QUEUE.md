# QUEUE — labqueue, a file-based job queue for the BitNet lab

<!-- Muse's work — Muse's side of the BitNet lab. Fable's side untouched. -->

`labqueue.py` is a coordination service, **not an executor and not a daemon**:
a stream claims a job, gets its payload back, runs the payload itself, and
reports `complete` / `fail` / `release`. Nothing here starts work on its own,
and nothing in the mill, the ladder driver, or the growth cycle has been
rewired — adoption below is incremental and documented, not done.

## Design (one page)

- **State:** `compute/queue/state/` (created at runtime; override with
  `--root PATH` or `$LABQUEUE_ROOT`), one JSON file per job, in
  `pending/`, `running/`, `done/`, or `failed/`.
- **Design choice (two lines):** Directory-per-state + atomic `os.rename()`
  between dirs was chosen over a single flock'd file because a rename is
  atomic, keeps exactly one copy of a job even if the VM dies mid-move, and
  the whole queue stays inspectable with `ls`/`cat`. A single exclusive
  `flock` on `state/.lock`, held across the claim scan+rename, is what makes
  concurrent claims safe — the directories alone would not be.
- **Job fields:** `id`, `kind`, `priority` (derived, see below), `payload`
  (`{argv: [...]}` or `{shell: "..."}`, plus optional `cwd` and `env` pins
  such as `OMP_NUM_THREADS=2`), `submitted_by`, `submitted_at`, `attempts`,
  `max_attempts` (default 3), `heartbeat_at`, `worker`, `claimed_at`,
  `timeout` (per-job stale threshold, optional), `state`, `result`, `error`,
  and an append-only `history` of events.
- **Priority (lower claims first, FIFO inside a tier):**

  | priority | kinds |
  |---|---|
  | 0 | `ladder`, `growth` |
  | 10 | `trial` |
  | 20 | `probe` |
  | 30 | `other` |
  | 40 | `benchmark` |

- **Leases, not ownership:** `claim` stamps `worker`, `heartbeat_at`, and
  increments `attempts`. A live worker refreshes with `heartbeat`. A worker
  that dies simply stops heartbeating.
- **Preemption safety:** `reap` returns any `running/` job whose heartbeat is
  older than its threshold (`--stale-after`, else the job's `timeout`, else
  300 s) to `pending/` — or parks it in `failed/` if its attempts are
  exhausted. A dead worker can therefore never wedge the queue.
- **Retry policy:** `fail` returns the job to `pending/` until
  `attempts >= max_attempts`, then parks it in `failed/`. `release`
  (voluntary preemption, e.g. a heavier stream arrived) returns it to
  `pending/` and **gives the attempt back** — it does not count as a try.
- **Robustness:** every write is tmp-file + fsync + rename; mutations hold
  the flock; a VM restart loses nothing — in-flight jobs are just stale
  `running/` files waiting for the next `reap`. Stdlib only; runs under
  system `python3` and the lab venv python alike.

## CLI reference

Global flag (before the subcommand): `--root PATH`. All commands print JSON,
except `list` (human table; add `--json`). `claim` exits `3` and prints
`null` when nothing is claimable — loops can branch on that.

```bash
Q="python3 ~/workspace/edit-lab/bitnet-lab/compute/queue/labqueue.py"

# submit: argv payload after --, or --shell "..."; pin env/cwd on the job
$Q submit --kind probe --submitted-by mill --env OMP_NUM_THREADS=2 \
    -- python3 train.py --arm layered_half --rope
$Q submit --kind ladder --submitted-by ladder-driver --timeout 3600 \
    --shell "python3 run_scale_ladder.py --rung 10m"

$Q list [--state pending|running|done|failed] [--kind probe] [--json]
$Q claim --worker mill-1 [--kind probe]     # highest-priority pending job
$Q heartbeat --worker mill-1 <job-id>       # keep the lease alive
$Q complete  --worker mill-1 --result "loss=2.858" <job-id>
$Q fail      --worker mill-1 --error "OOM" <job-id>   # retry, then failed/
$Q release   --worker mill-1 <job-id>       # preempted; attempt not consumed
$Q reap [--stale-after 300]                 # reclaim dead workers' jobs
$Q stats   # by_state, by_kind, total, oldest_pending_age_s
```

As a library: `from labqueue import LabQueue; q = LabQueue()` — the methods
(`submit / list_jobs / get / claim / heartbeat / complete / fail / release /
reap / stats`) mirror the CLI exactly.

Tests: `python3 -m unittest test_labqueue -v` in this directory —
**21 tests**, covering parallel claimers (20 workers, 20 jobs, barrier-
released: no job claimed twice), priority + FIFO claim order, release not
consuming attempts, fail-retry-then-park, reap of a crashed worker and
re-running its job, heartbeat keeping a job alive, stats, and a CLI
round-trip subprocess test.

## Adoption — switching each stream over, incrementally

Each step is independent, can land alone, and leaves the old path working
until the new one has run clean. No step requires a flag day.

### 1. Mill (`mill/screen.py`, `mill/run-forever.sh`)
- **Step 1a (submit):** when a probe beats the promotion bar, instead of (then
  in addition to) appending to `mill/trials.jsonl`, submit it:
  `submit --kind trial --submitted-by mill -- <trial argv>`. Probes
  themselves can be submitted as `--kind probe` by whoever builds the pool.
- **Step 1b (claim):** replace the `lab_busy()` pgrep check at the top of a
  pass with: try to `claim --kind probe` jobs; trials claim at their higher
  priority, so a queued trial is naturally taken before the next probe —
  the mill no longer polls process names to guess whether it may work, it
  asks the queue. Keep the solo rule for verdict-bearing runs in the worker,
  not the queue: claim one, run it solo, heartbeat during it,
  `complete`/`fail` after.
- **Retires:** the `pgrep` etiquette in `screen.py:lab_busy()` /
  `run-forever.sh` ("mill yields if a heavier process name is visible") and
  the hand-rolled `mill/claims.jsonl` + `mill.lock` claim bookkeeping for
  anything that moves to the queue.

### 2. Ladder driver (`run_scale_ladder.py`)
- Submit its 12 rung jobs **once** at the start
  (`submit --kind ladder --timeout <rung budget> -- <rung argv>` × 12),
  then loop `claim --worker ladder-1` → run → `complete`/`fail` until
  `claim` returns exit 3. Claims come back in submission order inside the
  `ladder` tier, so rung order is preserved; a crashed driver is recovered
  by `reap`, and its current rung is re-claimed instead of restarted by hand.
- **Retires:** the driver's own `pgrep -fc` self/peer checks and any
  "is the ladder already running?" polling by other streams — they submit
  or claim; the queue arbitrates.

### 3. Growth cycle (growth cron)
- The cron submits one job per cycle instead of launching work directly:
  `submit --kind growth --submitted-by growth-cron -- <growth argv>`.
  A growth worker (or the cron's next tick, acting as worker) claims it —
  `growth` shares the top tier with `ladder`, so growth is never starved
  behind probes/benchmarks, and never double-runs: a second claim while
  one growth job is running gets the next job or nothing.
- **Retires:** the watchdog-restarts-the-loop pattern for growth and the
  implicit "only the cron may start this" convention.

### 4. Watchdog
- Replace bespoke restart logic with two queue calls on its existing tick:
  `reap` (reclaim anything whose worker died — this is what un-wedges the
  lab after a VM restart) and `stats` (report counts by state/kind and
  `oldest_pending_age_s`; alert only if pending age or `failed/` count
  crosses a threshold the main agent sets).
- **Retires:** per-stream pid/log babysitting — drivers no longer write
  heartbeat-ish logs for the watchdog to interpret; heartbeats are in the
  job files, and a stale one has exactly one meaning.

### What adoption does *not* change
Priorities on paper stay the lab's real priorities (ladder/growth preempt
trials, which preempt probes, which preempt benchmarks) — the queue just
enforces them at claim time instead of by every stream politely checking
everyone else's process names first.
