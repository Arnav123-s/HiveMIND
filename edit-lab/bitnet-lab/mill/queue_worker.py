#!/usr/bin/env python3
"""queue_worker.py — the mill's gen-0 pass queue worker (Muse's work, Muse's side).

Thin wiring for the DECOMPOSITION DIRECTIVE (mill/ENDGAME-STATUS.md,
2026-11-12 ~22:11 PT): the gen-0 pass is not one serial screen.py loop.
Each runnable IDEA-POOL entry becomes ONE claimable job in
compute/queue/labqueue.py (kind=probe, priority 20) and worker lanes claim
jobs one at a time, execute them, ledger them, and complete/fail the
queue job with heartbeat.

    python3 mill/queue_worker.py submit [--gen N] [--dry-run]
    python3 mill/queue_worker.py work --lane vm|ashp [--once] [--dry-run]
    python3 mill/queue_worker.py selftest        # scratch queue in /tmp only

Hard properties (enforced in code, not by convention):

  * PROBES ONLY. The worker claims with kinds=["probe"] only, and
    validate_job() refuses — before any execution — any job whose kind is
    not "probe", any payload carrying verdict-bearing work (trial /
    judgment / confirmation / control / baseline / job-zero keys or a
    shell payload), and MILL-000 itself. Job zero, trial judging,
    confirmations and control re-runs stay SOLO in the coordinator
    (screen.py's main pass); they are never queued and never executed here.
    Trials (kind=trial, priority 10) are submitted by the coordinator;
    this worker never submits, claims or judges them — a "promote" probe
    verdict is ledgered and reported in the queue result for the
    coordinator to act on, nothing more.
  * THE POOL IS THE SOURCE OF TRUTH. A job payload carries only an entry
    id + generation (+ probe budget). The worker looks the entry up in
    mill/IDEA-POOL.md via screen.parse_pool() and re-validates its flags
    with screen.validate(); the payload's argv (a descriptive token that
    satisfies labqueue's payload shape) is NEVER executed, and a payload
    "shell" is refused outright.
  * ONE LEDGER. Probe lines are written ONLY by screen.ledger_probe()
    (screen.py's existing discipline: stamp/code_sha, verdict vs this
    pass's job-zero baseline, exception list, error-bench after 3).
    This file invents no ledger format and writes no other mill file.
  * ONE HEAVY JOB PER MACHINE. Each lane claims one job at a time and
    runs it to completion before claiming the next. The ashp lane adds
    the COMPUTE-ASHP.md gates (GPU-sensor start gate <= 65 C, no other
    python heavy job on the box, preflight before every claim); if ashp
    is unreachable the lane idle-reports and exits its step — it never
    crashes and never claims work it cannot run.

Lanes:
  * vm   — sweep-mode entries via screen.run_sweep_batch() with a batch
           of exactly 1 (mill/sweep_probe.py, shared-data runner);
           process-mode entries via screen.run_subprocess_probe()
           (isolated train.py subprocess), exactly as screen's lanes do.
           Yields (no claim) while screen.lab_busy() is non-None.
  * ashp — subprocess probe on the laptop, reached ONLY through
           weights-reader/tools/ashp_ssh.sh. Per COMPUTE-ASHP.md the SSH
           session drops at ~23 s, so the probe is launched detached
           (Start-Process, EncodedCommand) writing out.txt/done.txt under
           D:\\muse\\compute-bench\\queue-probes\\<tag>\\, and the lane
           polls with short SSH calls (heartbeating the queue job between
           polls) until done.txt lands, then parses the RESULT line.
           OMP/MKL = 8 (the measured ashp setting); ledger lines stamped
           omp=8 are therefore identifiable as ashp-measured.

screen.py imports no torch, and neither does this file: both are safe
under the system python3. All training runs under the lab venv python
(VM lane, via screen) or ashp's CPU venv (ashp lane).
"""
# Muse's work — Muse's side of the BitNet lab. Fable's side untouched.

from __future__ import annotations

import argparse
import base64
import json
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

MILL = Path(__file__).resolve().parent
LAB = MILL.parent
QUEUE_DIR = LAB / "compute" / "queue"
sys.path.insert(0, str(MILL))
sys.path.insert(0, str(QUEUE_DIR))

import screen  # noqa: E402  (mill/screen.py — pool, ledger, executors)
from labqueue import LabQueue  # noqa: E402  (compute/queue/labqueue.py)

# --------------------------------------------------------------------------
# Constants — the decomposition, as numbers
# --------------------------------------------------------------------------

PROBE_KIND = "probe"            # labqueue maps this to priority 20
TRIAL_KIND = "trial"            # priority 10; coordinator's, never ours
DEFAULT_PROBE_MINUTES = 1.25    # screen.py's probe budget
HEARTBEAT_S = 20.0              # queue lease refresh while a probe runs
ENTRY_ID_RE = re.compile(r"^MILL-\d+$")

# Payload keys that mark verdict-bearing work. A probe payload carrying
# any of these is refused before execution, however it was submitted.
FORBIDDEN_PAYLOAD_KEYS = {
    "trial", "trials", "judge", "judging", "judgment", "judgement",
    "confirmation", "confirm", "control", "controls", "baseline",
    "job_zero", "jobzero", "verdict", "adoption", "champion",
}

ASHP_SSH = (LAB.parent / "weights-reader" / "tools" / "ashp_ssh.sh")
ASHP_REMOTE_DIR = r"D:\muse\compute-bench"                    # train.py copy + corpus.u16 (COMPUTE-ASHP.md)
ASHP_PY = r"D:\muse\work\edit-lab\venv\Scripts\python.exe"    # torch CPU venv on ashp
ASHP_OMP = 8                    # measured best on ashp (COMPUTE-ASHP.md §2)
ASHP_TEMP_START_MAX_C = 65      # start gate on the GPU sensor (proxy for CPU)
ASHP_TEMP_ABORT_C = 80          # stricter than the house 88-90 C line: sensor is a proxy
ASHP_POLL_S = 15.0
ASHP_SSH_TIMEOUT_S = 30


def log(msg):
    print(f"[queue-worker] {msg}", flush=True)


class RefusedJob(Exception):
    """A claimed/peeked job is not a plain probe. Never executed."""


class Preempted(Exception):
    """The lab/machine was taken by heavier work mid-probe: release the
    queue job (attempt given back), ledger NOTHING — mirroring screen.py's
    lane behaviour when a sweep batch stops before an entry runs."""


class LaneUnavailable(Exception):
    """The lane's machine cannot run right now (ashp unreachable / hot /
    busy). Idle-report; do not claim, or release if already claimed."""


# --------------------------------------------------------------------------
# Job payloads + the hard probes-only property
# --------------------------------------------------------------------------

def payload_for(entry, gen, probe_minutes=DEFAULT_PROBE_MINUTES):
    """The queue payload for one pool entry. Carries the entry id and
    generation ONLY as work identity; `argv` is a descriptive token that
    satisfies labqueue's payload shape and is never executed."""
    return {
        "entry_id": entry["id"],
        "gen": int(gen),
        "probe_minutes": float(probe_minutes),
        "mode": entry.get("mode", "process"),
        "argv": ["queue-probe", entry["id"], "--gen", str(int(gen))],
    }


def validate_job(job):
    """Return (entry_id, gen, probe_minutes) for a legitimate probe job.

    Raises RefusedJob for anything else. This is the hard property:
    verdict-bearing work is never queued, and if a verdict-bearing (or
    malformed, or shell-carrying) payload ever reaches this worker anyway,
    it is refused before execution — the executor is not called.
    """
    if not isinstance(job, dict):
        raise RefusedJob("job is not a dict")
    if job.get("kind") != PROBE_KIND:
        raise RefusedJob(
            f"kind={job.get('kind')!r} is not {PROBE_KIND!r}: verdict-bearing "
            "and non-probe work stays solo in the coordinator")
    payload = job.get("payload")
    if not isinstance(payload, dict):
        raise RefusedJob("payload missing or not a dict")
    if "shell" in payload:
        raise RefusedJob("payload carries a shell command; the worker never "
                         "executes payload commands — it runs pool entries by id")
    bad = FORBIDDEN_PAYLOAD_KEYS & {str(k).lower() for k in payload}
    if bad:
        raise RefusedJob(f"payload carries verdict-bearing key(s): {sorted(bad)}")
    entry_id = payload.get("entry_id")
    if not isinstance(entry_id, str) or not ENTRY_ID_RE.match(entry_id):
        raise RefusedJob(f"payload entry_id {entry_id!r} is not a MILL-<n> id")
    if entry_id == "MILL-000":
        raise RefusedJob("MILL-000 is job zero — the coordinator measures the "
                         "baseline solo; it is never queued")
    gen = payload.get("gen")
    if not isinstance(gen, int) or gen < 0:
        raise RefusedJob(f"payload gen {gen!r} is not a non-negative int")
    minutes = payload.get("probe_minutes", DEFAULT_PROBE_MINUTES)
    if not isinstance(minutes, (int, float)) or minutes <= 0:
        raise RefusedJob(f"payload probe_minutes {minutes!r} is not positive")
    return entry_id, gen, float(minutes)


# --------------------------------------------------------------------------
# Submitter — runnable pool subset -> idempotent probe jobs
# --------------------------------------------------------------------------

def _existing_probe_keys(q):
    """(entry_id, gen) pairs with a probe job already pending or running."""
    keys = set()
    for state in ("pending", "running"):
        for job in q.list_jobs(state=state, kind=PROBE_KIND):
            p = job.get("payload") or {}
            if isinstance(p.get("entry_id"), str) and isinstance(p.get("gen"), int):
                keys.add((p["entry_id"], p["gen"]))
    return keys


def submit_pass(q, entries, gen, validate_fn, done_ids=frozenset(),
                probe_minutes=DEFAULT_PROBE_MINUTES, dry_run=False,
                submitted_by="queue-worker"):
    """One probe job per runnable, not-yet-ledgered entry. Idempotent:
    an entry+generation with a probe job already pending/running is
    skipped, as are MILL-000 (coordinator solo), ledger-done entries and
    deferred entries (validate_fn returns a reason). Returns a report
    dict; with dry_run=True nothing is submitted."""
    existing = _existing_probe_keys(q)
    report = {"gen": gen, "submitted": [], "already_queued": [],
              "ledger_done": [], "deferred": [], "dry_run": dry_run}
    timeout = float(probe_minutes) * 60.0 + 900.0  # probe + startup + slack; reap threshold
    for entry in entries:
        eid = entry["id"]
        if eid == "MILL-000":
            continue  # job zero: NEVER queued (coordinator, solo)
        if eid in done_ids:
            report["ledger_done"].append(eid)
            continue
        why = validate_fn(entry)
        if why is not None:
            report["deferred"].append({"id": eid, "reason": why})
            continue
        if (eid, gen) in existing:
            report["already_queued"].append(eid)
            continue
        if not dry_run:
            q.submit(kind=PROBE_KIND,
                     payload=payload_for(entry, gen, probe_minutes),
                     submitted_by=submitted_by, timeout=timeout)
            existing.add((eid, gen))
        report["submitted"].append(eid)
    return report


def _production_pool():
    """(champion, gen, entries, flags, arms) from screen.py's own readers."""
    champ = screen.load_champion()
    entries = screen.parse_pool()
    flags, arms = screen.valid_flags_and_arms()
    return champ, entries, flags, arms


def submit_command(args):
    champ, entries, flags, arms = _production_pool()
    gen = champ["gen"] if args.gen is None else args.gen
    st = screen.ledger_state(gen)
    done_ids = st["done"]  # ledger_state already folds in benched ids
    q = LabQueue(args.root)
    report = submit_pass(
        q, entries, gen,
        validate_fn=lambda e: screen.validate(e, flags, arms),
        done_ids=done_ids, probe_minutes=args.probe_minutes,
        dry_run=args.dry_run)
    if not args.dry_run:
        # Deferrals are ledgered through screen.py's own function (one
        # kind="deferrals" line per pass per generation, only on change) —
        # the submitter invents no ledger lines of its own.
        workers, _ = screen.load_concurrency()
        n = screen.ledger_deferrals(gen, entries, done_ids, flags, arms, workers)
        report["deferrals_ledgered"] = n
    log(f"submit gen {gen}: {len(report['submitted'])} "
        f"{'would submit' if args.dry_run else 'submitted'}, "
        f"{len(report['already_queued'])} already queued, "
        f"{len(report['ledger_done'])} ledger-done, "
        f"{len(report['deferred'])} deferred")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


# --------------------------------------------------------------------------
# Heartbeat — keep the queue lease alive while a probe runs
# --------------------------------------------------------------------------

class _Heartbeat:
    def __init__(self, q, job_id, worker, interval=HEARTBEAT_S):
        self._q, self._job_id, self._worker = q, job_id, worker
        self._interval = interval
        self._stop = threading.Event()
        self._thread = None

    def __enter__(self):
        def beat():
            while not self._stop.wait(self._interval):
                try:
                    self._q.heartbeat(self._job_id, worker=self._worker)
                except Exception:
                    return  # lease lost/parked elsewhere; execution result decides
        self._thread = threading.Thread(target=beat, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)


# --------------------------------------------------------------------------
# VM lane executor — screen.py's own runners, batch-of-1
# --------------------------------------------------------------------------

class VMLane:
    name = "vm"
    omp = None  # from screen.load_concurrency() at construction

    def __init__(self, omp=None):
        self.omp = omp if omp is not None else screen.load_concurrency()[1]

    def preflight(self):
        busy = screen.lab_busy()
        if busy:
            raise LaneUnavailable(f"lab busy ({busy}) — mill yields")
        return None

    def run_probe(self, entry, probe_minutes, deadline):
        if entry.get("mode", "process") == "sweep":
            job = {"id": entry["id"], "run": entry["run"],
                   "minutes": probe_minutes, "seed": 0,
                   "tag": screen.tag_for(entry["id"])}
            results = screen.run_sweep_batch([job], self.omp, deadline)
            rec = results.get(entry["id"])
            if rec is None:
                # Stopped before this entry ran (MILLSTOP / deadline kill):
                # screen's lanes ledger nothing in that case. Mirror it.
                raise Preempted("sweep batch produced no result for "
                                f"{entry['id']} (stopped or preempted)")
            return rec
        return screen.run_subprocess_probe(entry, probe_minutes, self.omp)


# --------------------------------------------------------------------------
# ashp lane executor — detached subprocess probe via ashp_ssh.sh only
# --------------------------------------------------------------------------

def _ps_encoded(script):
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


class AshpLane:
    name = "ashp"
    omp = ASHP_OMP

    def __init__(self, ssh_runner=None, ssh_script=ASHP_SSH,
                 poll_s=ASHP_POLL_S):
        # ssh_runner(remote_command_str, timeout_s) -> (rc, stdout, stderr);
        # injectable so the self-test never touches the real laptop.
        self._ssh_runner = ssh_runner or self._default_ssh_runner
        self.ssh_script = Path(ssh_script)
        self.poll_s = poll_s

    @staticmethod
    def _default_ssh_runner(remote_command, timeout_s):
        r = subprocess.run([str(ASHP_SSH), remote_command],
                           capture_output=True, text=True, timeout=timeout_s)
        return r.returncode, r.stdout, r.stderr

    def _ps(self, script, timeout_s=ASHP_SSH_TIMEOUT_S):
        cmd = f"powershell -NoProfile -EncodedCommand {_ps_encoded(script)}"
        return self._ssh_runner(cmd, timeout_s)

    def preflight(self):
        """Reachability + thermal + one-heavy-job gate. Any failure is a
        LaneUnavailable (idle-report), never an exception that crashes
        the lane."""
        script = ("$t = (nvidia-smi --query-gpu=temperature.gpu "
                  "--format=csv,noheader); "
                  "$p = (Get-Process python -ErrorAction SilentlyContinue "
                  "| Measure-Object).Count; Write-Output $t; Write-Output $p")
        try:
            rc, out, _ = self._ps(script)
        except Exception as e:
            raise LaneUnavailable(f"ashp unreachable via ashp_ssh.sh: {e}")
        if rc != 0:
            raise LaneUnavailable(f"ashp preflight failed (rc={rc})")
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        try:
            temp_c = int(float(lines[0]))
            n_python = int(lines[1])
        except (IndexError, ValueError):
            raise LaneUnavailable(f"ashp preflight unparsable: {out!r}")
        if temp_c > ASHP_TEMP_START_MAX_C:
            raise LaneUnavailable(
                f"ashp hot: GPU sensor {temp_c} C > start gate "
                f"{ASHP_TEMP_START_MAX_C} C — deferring (thermal discipline)")
        if n_python > 0:
            raise LaneUnavailable(
                f"ashp busy: {n_python} python process(es) already running — "
                "one heavy job at a time on ashp")
        return None

    def run_probe(self, entry, probe_minutes, deadline):
        tag = screen.tag_for(entry["id"]) + "ashp"
        jobdir = ASHP_REMOTE_DIR + "\\queue-probes\\" + tag
        args = shlex.split(entry["run"]) + ["--seed", "0", "--minutes",
                                            str(probe_minutes), "--tag", tag]
        args_ps = " ".join("'" + a.replace("'", "''") + "'" for a in args)
        # The probe script runs train.py (ashp's copy) in ASHP_REMOTE_DIR,
        # captures ALL output to out.txt, then drops done.txt with the exit
        # code. Launched detached: SSH sessions drop at ~23 s (COMPUTE-ASHP).
        probe_ps = (
            f"New-Item -ItemType Directory -Force -Path '{jobdir}' | Out-Null; "
            f"Set-Location '{ASHP_REMOTE_DIR}'; "
            f"$env:OMP_NUM_THREADS='{ASHP_OMP}'; $env:MKL_NUM_THREADS='{ASHP_OMP}'; "
            f"& '{ASHP_PY}' train.py {args_ps} *> '{jobdir}\\out.txt'; "
            f"$LASTEXITCODE | Out-File -Encoding ascii '{jobdir}\\done.txt'")
        launch_ps = (
            f"$p = Start-Process powershell -PassThru -WindowStyle Hidden "
            f"-ArgumentList '-NoProfile','-EncodedCommand','{_ps_encoded(probe_ps)}'; "
            f"$p.Id | Out-File -Encoding ascii '{jobdir}\\pid.txt'; Write-Output $p.Id")
        # jobdir must exist before pid.txt can be written into it
        try:
            rc, _, err = self._ps(
                f"New-Item -ItemType Directory -Force -Path '{jobdir}' | Out-Null")
            if rc != 0:
                raise LaneUnavailable(f"ashp mkdir failed (rc={rc}): {err[-200:]}")
            rc, out, err = self._ps(launch_ps)
        except LaneUnavailable:
            raise
        except Exception as e:
            raise LaneUnavailable(f"ashp launch failed: {e}")
        if rc != 0:
            raise LaneUnavailable(f"ashp launch failed (rc={rc}): {err[-200:]}")
        # Poll for done.txt with short SSH calls; the worker's heartbeat
        # thread keeps the queue lease alive between polls.
        misses = 0
        while time.time() < deadline:
            time.sleep(self.poll_s)
            poll_ps = (f"if (Test-Path '{jobdir}\\done.txt') {{ "
                       f"Write-Output 'DONE'; Get-Content '{jobdir}\\out.txt' }} "
                       f"else {{ Write-Output 'RUNNING' }}")
            try:
                rc, out, _ = self._ps(poll_ps)
                misses = 0
            except Exception as e:
                misses += 1
                if misses >= 3:
                    raise LaneUnavailable(
                        f"ashp unreachable mid-probe (3 poll failures): {e} — "
                        "remote probe may finish orphaned; nothing ledgered")
                continue
            if rc != 0:
                misses += 1
                if misses >= 3:
                    raise LaneUnavailable("ashp poll failed 3x (rc!=0)")
                continue
            if out.startswith("DONE"):
                for line in out.splitlines():
                    if line.startswith("RESULT "):
                        return json.loads(line[len("RESULT "):])
                return {"error": f"ashp probe finished with no RESULT line: "
                                 f"{out[-300:]}"}
            # still RUNNING: thermal watch on the proxy sensor
            try:
                rc2, tout, _ = self._ps(
                    "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader")
                if rc2 == 0 and int(float(tout.strip().splitlines()[0])) > ASHP_TEMP_ABORT_C:
                    self._best_effort_kill(jobdir)
                    return {"error": f"ashp thermal abort: GPU sensor > "
                                     f"{ASHP_TEMP_ABORT_C} C during probe"}
            except Exception:
                pass  # a failed temp read never kills a probe by itself
        self._best_effort_kill(jobdir)
        return {"error": "ashp probe exceeded the lane deadline; killed best-effort"}

    def _best_effort_kill(self, jobdir):
        try:
            self._ps(f"$pid_ = Get-Content '{jobdir}\\pid.txt' -ErrorAction SilentlyContinue; "
                     f"if ($pid_) {{ Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue }}")
        except Exception:
            pass


# --------------------------------------------------------------------------
# Worker core — claim one, execute, ledger via screen, complete/fail
# --------------------------------------------------------------------------

def worker_step(q, worker_id, lane, entries_by_id, gen, baseline_held,
                ledger_fn, validate_entry_fn=None):
    """One claim -> execute -> ledger -> complete/fail cycle.

    Returns an outcome dict. Never executes a non-probe job: the claim is
    restricted to kind=probe AND validate_job() re-checks the claimed job
    before the executor is touched. `ledger_fn(entry, rec, probe_minutes)
    -> line` is screen.ledger_probe in production (baseline/gen/omp bound
    by the caller); the minutes stamped are the JOB's own budget.
    """
    try:
        lane.preflight()
    except LaneUnavailable as e:
        log(f"{worker_id}: idle — {e}")
        return {"outcome": "idle", "reason": str(e)}
    job = q.claim(worker=worker_id, kinds=[PROBE_KIND])
    if job is None:
        return {"outcome": "idle", "reason": "no claimable probe job"}
    job_id = job["id"]
    try:
        entry_id, job_gen, probe_minutes = validate_job(job)
    except RefusedJob as e:
        # Poison payload: fail it (queue retries, then parks it in
        # failed/) — it is NEVER executed and NEVER ledgered as a probe.
        log(f"{worker_id}: REFUSED job {job_id}: {e}")
        q.fail(job_id, worker=worker_id, error=f"refused: {e}")
        return {"outcome": "refused", "job_id": job_id, "reason": str(e)}
    if job_gen != gen:
        q.release(job_id, worker=worker_id)
        return {"outcome": "released", "job_id": job_id,
                "reason": f"job gen {job_gen} != worker gen {gen} "
                          "(generation moved; coordinator re-submits)"}
    entry = entries_by_id.get(entry_id)
    if entry is None:
        q.fail(job_id, worker=worker_id,
               error=f"entry {entry_id} not in IDEA-POOL.md")
        return {"outcome": "failed", "job_id": job_id,
                "reason": "entry not in pool"}
    if validate_entry_fn is not None:
        why = validate_entry_fn(entry)
        if why is not None:
            q.fail(job_id, worker=worker_id, error=f"deferred: {why}")
            return {"outcome": "failed", "job_id": job_id,
                    "reason": f"deferred at claim time: {why}"}
    if baseline_held is None:
        q.release(job_id, worker=worker_id)
        return {"outcome": "released", "job_id": job_id,
                "reason": "no job-zero baseline for this generation — the "
                          "coordinator measures it solo before probes run"}
    deadline = time.time() + probe_minutes * 60 + 900
    try:
        with _Heartbeat(q, job_id, worker_id):
            rec = lane.run_probe(entry, probe_minutes, deadline)
    except Preempted as e:
        q.release(job_id, worker=worker_id)
        log(f"{worker_id}: {entry_id} preempted — released, nothing ledgered ({e})")
        return {"outcome": "released", "job_id": job_id, "reason": str(e)}
    except LaneUnavailable as e:
        q.release(job_id, worker=worker_id)
        log(f"{worker_id}: {entry_id} lane unavailable mid-job — released ({e})")
        return {"outcome": "released", "job_id": job_id, "reason": str(e)}
    except Exception as e:  # executor blew up: that IS a probe error record
        rec = {"error": f"{type(e).__name__}: {e}"}
    line = ledger_fn(entry, rec, probe_minutes)
    held = line.get("held")
    if held is not None:
        result = {"entry_id": entry_id, "gen": gen, "lane": lane.name,
                  "held": held, "verdict": line.get("verdict"),
                  "delta_vs_baseline": line.get("delta_vs_baseline")}
        if line.get("verdict") == "promote":
            # Trial submission/judging is the coordinator's solo work.
            result["note"] = ("promote verdict ledgered; the coordinator "
                              "submits and judges the trial — not queued here")
        q.complete(job_id, worker=worker_id, result=json.dumps(result, sort_keys=True))
        log(f"{worker_id}: {entry_id} held={held} verdict={line.get('verdict')} "
            f"-> queue job {job_id} done")
        return {"outcome": "completed", "job_id": job_id, **result}
    # No held value: screen.ledger_probe has written the error line (and
    # benches the entry after ERROR_BENCH_AFTER). Fail the queue job so
    # labqueue's retry policy mirrors that re-queue discipline.
    err = (rec or {}).get("error") or "probe produced no held value"
    q.fail(job_id, worker=worker_id, error=str(err)[:500])
    log(f"{worker_id}: {entry_id} ERROR ledgered -> queue job {job_id} failed "
        f"(retry/park per labqueue): {str(err)[:200]}")
    return {"outcome": "failed", "job_id": job_id, "reason": str(err)[:500]}


def _step_context(args):
    """Fresh per-step context: champion/gen, baseline, pool. Cheap file
    reads only — flags/arms are computed ONCE per lane start by the
    caller (valid_flags_and_arms() shells out to train.py --help; doing
    that per job would tax every probe with a torch-import subprocess)."""
    champ = screen.load_champion()
    gen = champ["gen"] if args.gen is None else args.gen
    entries = screen.parse_pool()
    st = screen.ledger_state(gen)
    baseline = st["baseline"]
    baseline_held = baseline["held"] if baseline else None
    return gen, {e["id"]: e for e in entries}, baseline_held


def work_command(args):
    worker_id = args.worker or f"queue-{args.lane}-1"
    lane = VMLane() if args.lane == "vm" else AshpLane()
    q = LabQueue(args.root)
    if args.dry_run:
        gen, entries_by_id, baseline_held = _step_context(args)
        pending = [j for j in q.list_jobs(state="pending", kind=PROBE_KIND)]
        print(f"[queue-worker] DRY RUN — lane={args.lane} worker={worker_id} "
              f"root={q.root} gen={gen} baseline_held={baseline_held}")
        print(f"[queue-worker] pending probe jobs: {len(pending)}; "
              f"trials are never claimed by this worker")
        for j in pending[:5]:
            try:
                eid, jgen, minutes = validate_job(j)
                entry = entries_by_id.get(eid)
                plan = ("sweep batch-of-1 via mill/sweep_probe.py"
                        if entry and entry.get("mode") == "sweep" and args.lane == "vm"
                        else "process train.py subprocess"
                        if args.lane == "vm"
                        else "detached subprocess probe on ashp via ashp_ssh.sh")
                print(f"[queue-worker] would claim {j['id']}: {eid} gen {jgen} "
                      f"({minutes} min) -> {plan} -> screen.ledger_probe -> "
                      f"complete/fail with heartbeat")
            except RefusedJob as e:
                print(f"[queue-worker] would REFUSE {j['id']}: {e}")
        return 0
    flags, arms = screen.valid_flags_and_arms()  # once per lane start
    deadline = time.time() + args.max_wall_min * 60
    done = 0
    while time.time() < deadline:
        gen, entries_by_id, baseline_held = _step_context(args)
        omp = lane.omp if lane.omp is not None else screen.load_concurrency()[1]

        def ledger_fn(entry, rec, minutes, _gen=gen, _base=baseline_held, _omp=omp):
            return screen.ledger_probe(entry, rec, _gen, _base,
                                       minutes, workers=1, omp=_omp)

        outcome = worker_step(
            q, worker_id, lane, entries_by_id, gen, baseline_held, ledger_fn,
            validate_entry_fn=lambda e: screen.validate(e, flags, arms))
        done += 1 if outcome["outcome"] in ("completed", "failed") else 0
        if args.once or (args.max_jobs and done >= args.max_jobs):
            print(json.dumps(outcome, indent=2, sort_keys=True, default=str))
            return 0
        if outcome["outcome"] == "idle":
            if args.lane == "ashp":
                log(f"{worker_id}: ashp lane idle — exiting step loop "
                    "(idle-report, not a crash)")
                return 0
            time.sleep(args.idle_sleep)
        elif outcome["outcome"] == "released":
            # e.g. baseline not measured yet, or a mid-probe preemption:
            # wait before re-claiming instead of claim/release spinning.
            time.sleep(args.idle_sleep if args.lane == "vm" else 5.0)
    log(f"{worker_id}: wall cap reached after {done} finished job(s)")
    return 0


# --------------------------------------------------------------------------
# Self-test — fake entries/jobs, scratch queue under /tmp, NO live anything
# --------------------------------------------------------------------------

class _FakeLane:
    name = "fake"
    omp = 2

    def __init__(self, rec=None, preflight_error=None):
        self.rec = rec if rec is not None else {"held_final": 2.5, "seed": 0,
                                                "steps": 10, "wall_s": 1.0}
        self.preflight_error = preflight_error
        self.calls = 0

    def preflight(self):
        if self.preflight_error:
            raise LaneUnavailable(self.preflight_error)
        return None

    def run_probe(self, entry, probe_minutes, deadline):
        self.calls += 1
        return dict(self.rec)


def selftest():
    from labqueue import LabQueue as LQ
    scratch = Path(tempfile.mkdtemp(prefix="queue-worker-selftest-", dir="/tmp"))
    q = LQ(scratch / "state")
    passed = []

    def check(name, cond):
        if not cond:
            raise AssertionError(f"selftest FAILED: {name}")
        passed.append(name)
        print(f"  ok: {name}")

    entries = [
        {"id": "MILL-000", "mode": "sweep", "run": "--arm layered_half --rope"},
        {"id": "MILL-900", "mode": "sweep", "run": "--arm layered_half --rope"},
        {"id": "MILL-901", "mode": "process", "run": "--arm plain_half --rope"},
        {"id": "MILL-902", "mode": "process", "run": "--arm layered_half --rope --nope-flag"},
    ]
    validate_fn = lambda e: ("flag --nope-flag not in train.py"
                             if "--nope-flag" in e["run"] else None)

    # 1. submitter: runnable only, MILL-000 excluded, deferred excluded
    rep = submit_pass(q, entries, 0, validate_fn)
    check("submitter submits exactly the 2 runnable entries",
          rep["submitted"] == ["MILL-900", "MILL-901"])
    check("deferred entry reported, not submitted",
          rep["deferred"] == [{"id": "MILL-902",
                               "reason": "flag --nope-flag not in train.py"}])
    pend = q.list_jobs(state="pending", kind="probe")
    check("pending probe jobs carry kind=probe priority=20",
          len(pend) == 2 and all(j["priority"] == 20 for j in pend))
    check("payloads carry entry ids",
          {j["payload"]["entry_id"] for j in pend} == {"MILL-900", "MILL-901"})

    # 2. idempotency: re-submit adds nothing
    rep2 = submit_pass(q, entries, 0, validate_fn)
    check("re-submit is idempotent (0 new, 2 already queued)",
          rep2["submitted"] == [] and len(rep2["already_queued"]) == 2
          and len(q.list_jobs(state="pending", kind="probe")) == 2)
    rep3 = submit_pass(q, entries, 0, validate_fn, done_ids={"MILL-900"})
    check("ledger-done entries are not re-submitted",
          rep3["ledger_done"] == ["MILL-900"])

    # 3. dry-run submitter writes nothing
    q2 = LQ(scratch / "state2")
    repd = submit_pass(q2, entries, 0, validate_fn, dry_run=True)
    check("dry-run submitter reports but writes no jobs",
          len(repd["submitted"]) == 2 and q2.stats()["total"] == 0)

    # 4. trial jobs are never claimed by the worker; validate_job refuses them
    trial = q.submit(kind="trial", payload={"argv": ["train.py", "--arm", "x"]},
                     submitted_by="coordinator-selftest")
    fake = _FakeLane()
    ledgered = []
    ledger_fn = lambda e, rec, minutes: ledgered.append((e["id"], rec)) or {
        "held": rec.get("held_final"), "verdict": "flat", "delta_vs_baseline": 0.1}
    # claim order: trial (pri 10) sorts first in the queue, but the worker's
    # claim is restricted to probes, so the step must take a probe instead.
    out = worker_step(q, "selftest-vm", fake,
                      {e["id"]: e for e in entries}, 0, 2.6, ledger_fn, validate_fn)
    check("worker completes a probe while a trial job sits in the queue",
          out["outcome"] == "completed" and fake.calls == 1 and len(ledgered) == 1)
    check("trial job untouched (still pending, never claimed)",
          q.get(trial["id"])["state"] == "pending")
    try:
        validate_job(q.get(trial["id"]))
        check("validate_job refuses trial jobs", False)
    except RefusedJob:
        check("validate_job refuses trial jobs", True)

    # 5. verdict-bearing / job-zero / shell payloads are refused pre-execution
    for payload, label in (
            ({"entry_id": "MILL-000", "gen": 0, "argv": ["x"]}, "job zero"),
            ({"entry_id": "MILL-900", "gen": 0, "argv": ["x"],
              "confirmation": {}}, "confirmation payload"),
            ({"entry_id": "MILL-900", "gen": 0, "shell": "rm -rf /"}, "shell payload")):
        try:
            validate_job({"kind": "probe", "payload": payload})
            check(f"validate_job refuses {label}", False)
        except RefusedJob:
            check(f"validate_job refuses {label}", True)

    # 6. poison probe job in the queue: failed, executor never called
    poison = q.submit(kind="probe",
                      payload={"entry_id": "MILL-900", "gen": 0,
                               "argv": ["x"], "judgment": {}},
                      submitted_by="selftest")
    fake2 = _FakeLane()
    out = worker_step(q, "selftest-vm", fake2,
                      {e["id"]: e for e in entries}, 0, 2.6, ledger_fn, validate_fn)
    # FIFO inside the probe tier: the remaining legit probe may be claimed
    # first; loop until the poison job has been stepped on (max 3 steps).
    steps = 0
    while out["outcome"] != "refused" and steps < 3:
        out = worker_step(q, "selftest-vm", fake2,
                          {e["id"]: e for e in entries}, 0, 2.6, ledger_fn, validate_fn)
        steps += 1
    check("poison verdict-bearing payload is refused, not executed",
          out["outcome"] == "refused" and q.get(poison["id"])["error"].startswith("refused:"))

    # 7. error probe: ledgered as error, queue job failed (retry discipline)
    q3 = LQ(scratch / "state3")
    submit_pass(q3, entries[1:2], 0, validate_fn)
    err_ledger = []
    out = worker_step(q3, "selftest-vm", _FakeLane(rec={"error": "boom"}),
                      {e["id"]: e for e in entries}, 0, 2.6,
                      lambda e, rec, minutes: err_ledger.append(rec) or
                      {"held": None, "verdict": "error", "delta_vs_baseline": None},
                      validate_fn)
    check("error probe is ledgered once and the queue job fails for retry",
          out["outcome"] == "failed" and len(err_ledger) == 1
          and q3.list_jobs(state="pending", kind="probe"))

    # 8. ashp unreachable: idle-report, no claim, no crash
    q4 = LQ(scratch / "state4")
    submit_pass(q4, entries[1:2], 0, validate_fn)
    dead = AshpLane(ssh_runner=lambda cmd, timeout: (_ for _ in ()).throw(
        subprocess.TimeoutExpired(cmd, timeout)))
    out = worker_step(q4, "selftest-ashp", dead,
                      {e["id"]: e for e in entries}, 0, 2.6, ledger_fn, validate_fn)
    check("unreachable ashp lane idle-reports and claims nothing",
          out["outcome"] == "idle"
          and len(q4.list_jobs(state="pending", kind="probe")) == 1)

    # 9. no baseline: claimed job is released, nothing executed/ledgered
    q5 = LQ(scratch / "state5")
    submit_pass(q5, entries[1:2], 0, validate_fn)
    fake5 = _FakeLane()
    out = worker_step(q5, "selftest-vm", fake5,
                      {e["id"]: e for e in entries}, 0, None, ledger_fn, validate_fn)
    check("missing baseline releases the job unexecuted",
          out["outcome"] == "released" and fake5.calls == 0
          and len(q5.list_jobs(state="pending", kind="probe")) == 1)

    print(f"selftest: {len(passed)}/{len(passed)} checks passed "
          f"(scratch queue: {scratch})")
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="queue_worker", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None,
                    help="labqueue state root (default: compute/queue/state "
                         "or $LABQUEUE_ROOT)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("submit", help="turn the runnable gen-N pool subset "
                                      "into idempotent probe queue jobs")
    p.add_argument("--gen", type=int, default=None,
                   help="generation (default: champion's current gen)")
    p.add_argument("--probe-minutes", type=float, default=DEFAULT_PROBE_MINUTES)
    p.add_argument("--dry-run", action="store_true",
                   help="print what would be submitted; write nothing")

    p = sub.add_parser("work", help="run one worker lane")
    p.add_argument("--lane", choices=("vm", "ashp"), required=True)
    p.add_argument("--worker", default=None,
                   help="queue worker id (default: queue-<lane>-1)")
    p.add_argument("--gen", type=int, default=None)
    p.add_argument("--probe-minutes", type=float, default=DEFAULT_PROBE_MINUTES,
                   help="accepted for symmetry with submit; each job's own "
                        "payload budget is what gets executed and stamped")
    p.add_argument("--once", action="store_true", help="one step, then exit")
    p.add_argument("--max-jobs", type=int, default=None,
                   help="exit after this many finished (completed/failed) jobs")
    p.add_argument("--max-wall-min", type=float, default=45.0)
    p.add_argument("--idle-sleep", type=float, default=30.0)
    p.add_argument("--dry-run", action="store_true",
                   help="print what the lane would claim/run; execute nothing")

    sub.add_parser("selftest", help="unit-style checks against a scratch "
                                    "queue under /tmp (never the live queue)")

    args = ap.parse_args(argv)
    if args.cmd == "submit":
        return submit_command(args)
    if args.cmd == "work":
        return work_command(args)
    if args.cmd == "selftest":
        return selftest()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
