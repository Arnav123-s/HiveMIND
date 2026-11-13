#!/usr/bin/env python3
"""labqueue — a small file-based job queue (Muse's work, Muse's side).

Stdlib only. No daemon: workers claim a job, run its payload themselves,
heartbeat while running, then complete/fail/release it.

Design: one JSON file per job under state/{pending,running,done,failed}/.
State changes are an os.rename() between those dirs (atomic on one
filesystem) followed by an atomic in-place rewrite of the JSON. Every
mutation holds an exclusive flock on state/.lock across scan+rename, so
two workers claiming at the same instant can never take the same job.
See QUEUE.md for the full design and adoption notes.
"""
# Muse's work — Muse's side of the BitNet lab. Fable's side untouched.

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

KINDS = ("ladder", "growth", "trial", "probe", "benchmark", "other")
# Lower number = claimed first. ladder/growth > trial > probe > benchmark.
PRIORITY = {"ladder": 0, "growth": 0, "trial": 10, "probe": 20,
            "other": 30, "benchmark": 40}
STATES = ("pending", "running", "done", "failed")
DEFAULT_STALE_AFTER_S = 300.0
DEFAULT_MAX_ATTEMPTS = 3

DEFAULT_ROOT = Path(__file__).resolve().parent / "state"


def priority_for(kind: str) -> int:
    return PRIORITY.get(kind, PRIORITY["other"])


def _now() -> float:
    return time.time()


def _new_id() -> str:
    return f"q-{int(_now())}-{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------------------
# Queue
# --------------------------------------------------------------------------

class LabQueue:
    """File-based queue rooted at `root` (created on first use)."""

    def __init__(self, root=None):
        if root is None:
            root = os.environ.get("LABQUEUE_ROOT") or DEFAULT_ROOT
        self.root = Path(root)
        self._ensure()

    # -- filesystem helpers ------------------------------------------------

    def _ensure(self):
        for state in STATES:
            (self.root / state).mkdir(parents=True, exist_ok=True)
        lock = self.root / ".lock"
        if not lock.exists():
            lock.touch()

    @contextmanager
    def _locked(self):
        self._ensure()
        f = open(self.root / ".lock", "a+")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(f, fcntl.LOCK_UN)
            finally:
                f.close()

    def _path(self, state: str, job_id: str) -> Path:
        return self.root / state / f"{job_id}.json"

    @staticmethod
    def _read(path: Path) -> dict | None:
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            return None

    @staticmethod
    def _write_atomic(path: Path, job: dict) -> None:
        tmp = path.with_name(f".tmp-{job['id']}-{os.getpid()}-{uuid.uuid4().hex[:6]}")
        tmp.write_text(json.dumps(job, indent=2, sort_keys=True) + "\n")
        with open(tmp, "r") as fh:
            os.fsync(fh.fileno())
        os.rename(tmp, path)

    def _find(self, job_id: str):
        """Return (state, path, job) or (None, None, None)."""
        for state in STATES:
            p = self._path(state, job_id)
            if p.exists():
                job = self._read(p)
                if job is not None:
                    return state, p, job
        return None, None, None

    def _move(self, job: dict, src: Path, dst_state: str) -> Path:
        """Rename src into dst_state, then rewrite contents atomically.

        Caller must hold the lock. Rename-first keeps exactly one copy of
        the job on disk at all times, even if the process dies mid-move.
        """
        dst = self._path(dst_state, job["id"])
        if src != dst:
            os.rename(src, dst)
        job["state"] = dst_state
        self._write_atomic(dst, job)
        return dst

    def _all_jobs(self):
        jobs = []
        for state in STATES:
            d = self.root / state
            if not d.exists():
                continue
            for p in sorted(d.glob("*.json")):
                job = self._read(p)
                if job is not None:
                    job.setdefault("state", state)
                    jobs.append(job)
        return jobs

    @staticmethod
    def _sort_key(job: dict):
        return (job.get("priority", priority_for(job.get("kind", "other"))),
                job.get("submitted_at", 0.0), job.get("id", ""))

    # -- API ----------------------------------------------------------------

    def submit(self, kind="other", payload=None, submitted_by="unknown",
               timeout=None, max_attempts=DEFAULT_MAX_ATTEMPTS,
               argv=None, shell=None, cwd=None, env=None, job_id=None):
        """Create a job in pending/ and return it.

        payload may be a dict {argv|shell, cwd, env}; alternatively pass
        argv=/shell=/cwd=/env= directly.
        """
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
        if payload is None:
            payload = {}
            if argv is not None:
                payload["argv"] = list(argv)
            if shell is not None:
                payload["shell"] = shell
            if cwd is not None:
                payload["cwd"] = cwd
            if env is not None:
                payload["env"] = dict(env)
        if "argv" not in payload and "shell" not in payload:
            raise ValueError("payload needs an 'argv' list or a 'shell' string")
        job = {
            "id": job_id or _new_id(),
            "kind": kind,
            "priority": priority_for(kind),
            "payload": payload,
            "submitted_by": submitted_by,
            "submitted_at": _now(),
            "attempts": 0,
            "max_attempts": int(max_attempts),
            "heartbeat_at": None,
            "worker": None,
            "claimed_at": None,
            "timeout": timeout,
            "state": "pending",
            "result": None,
            "error": None,
            "history": [{"event": "submitted", "at": _now(), "by": submitted_by}],
        }
        with self._locked():
            if self._find(job["id"])[0] is not None:
                raise ValueError(f"duplicate job id {job['id']}")
            self._write_atomic(self._path("pending", job["id"]), job)
        return job

    def list_jobs(self, state=None, kind=None):
        jobs = [j for j in self._all_jobs()
                if (state is None or j["state"] == state)
                and (kind is None or j["kind"] == kind)]
        jobs.sort(key=self._sort_key)
        return jobs

    def get(self, job_id: str):
        _, _, job = self._find(job_id)
        return job

    def claim(self, worker: str, kinds=None):
        """Atomically claim the highest-priority pending job for `worker`.

        Returns the job (now in running/, attempts incremented, heartbeat
        set) or None if nothing claimable is pending.
        """
        if not worker:
            raise ValueError("worker id required")
        with self._locked():
            pending = []
            d = self.root / "pending"
            for p in d.glob("*.json"):
                job = self._read(p)
                if job is None:
                    continue
                if kinds and job["kind"] not in kinds:
                    continue
                pending.append((self._sort_key(job), p, job))
            if not pending:
                return None
            pending.sort(key=lambda t: t[0])
            _, path, job = pending[0]
            now = _now()
            job["worker"] = worker
            job["heartbeat_at"] = now
            job["claimed_at"] = now
            job["attempts"] = int(job.get("attempts", 0)) + 1
            job["history"].append(
                {"event": "claimed", "at": now, "by": worker,
                 "attempt": job["attempts"]})
            self._move(job, path, "running")
            return job

    def _running_job_for(self, job_id: str, worker: str | None):
        state, path, job = self._find(job_id)
        if job is None:
            raise KeyError(f"no such job {job_id}")
        if state != "running":
            raise ValueError(f"job {job_id} is {state}, not running")
        if worker is not None and job.get("worker") not in (None, worker):
            raise PermissionError(
                f"job {job_id} is held by {job.get('worker')!r}, not {worker!r}")
        return path, job

    def heartbeat(self, job_id: str, worker: str | None = None):
        with self._locked():
            path, job = self._running_job_for(job_id, worker)
            job["heartbeat_at"] = _now()
            self._write_atomic(path, job)
            return job

    def complete(self, job_id: str, worker: str | None = None, result=None):
        with self._locked():
            path, job = self._running_job_for(job_id, worker)
            now = _now()
            job["result"] = result
            job["finished_at"] = now
            job["heartbeat_at"] = now
            job["history"].append({"event": "completed", "at": now, "by": worker})
            self._move(job, path, "done")
            return job

    def fail(self, job_id: str, worker: str | None = None, error=None):
        """Fail a running job: back to pending/ for a retry, or parked in
        failed/ once attempts >= max_attempts."""
        with self._locked():
            path, job = self._running_job_for(job_id, worker)
            now = _now()
            job["error"] = error
            job["worker"] = None
            job["heartbeat_at"] = None
            exhausted = int(job.get("attempts", 0)) >= int(job.get("max_attempts", DEFAULT_MAX_ATTEMPTS))
            dst = "failed" if exhausted else "pending"
            if exhausted:
                job["finished_at"] = now
            job["history"].append(
                {"event": "failed-parked" if exhausted else "failed-retry",
                 "at": now, "by": worker, "error": error})
            self._move(job, path, dst)
            return job

    def release(self, job_id: str, worker: str | None = None):
        """Voluntary preemption: running -> pending WITHOUT consuming an
        attempt (the attempt counted at claim time is given back)."""
        with self._locked():
            path, job = self._running_job_for(job_id, worker)
            job["attempts"] = max(0, int(job.get("attempts", 0)) - 1)
            job["worker"] = None
            job["heartbeat_at"] = None
            job["claimed_at"] = None
            job["history"].append(
                {"event": "released", "at": _now(), "by": worker})
            self._move(job, path, "pending")
            return job

    def reap(self, stale_after=None, now=None):
        """Reclaim running jobs whose heartbeat is stale.

        Stale means now - heartbeat_at > threshold, where the threshold is
        `stale_after` if given, else the job's own timeout if set, else
        DEFAULT_STALE_AFTER_S. A reaped job returns to pending/ (attempt
        already counted at claim) unless its attempts are exhausted, in
        which case it is parked in failed/. Returns the list of reaped jobs.
        """
        now = _now() if now is None else now
        reaped = []
        with self._locked():
            d = self.root / "running"
            for p in sorted(d.glob("*.json")):
                job = self._read(p)
                if job is None:
                    continue
                hb = job.get("heartbeat_at")
                if hb is None:
                    hb = job.get("claimed_at") or job.get("submitted_at") or now
                if stale_after is not None:
                    threshold = float(stale_after)
                elif job.get("timeout"):
                    threshold = float(job["timeout"])
                else:
                    threshold = DEFAULT_STALE_AFTER_S
                if now - float(hb) <= threshold:
                    continue
                exhausted = int(job.get("attempts", 0)) >= int(
                    job.get("max_attempts", DEFAULT_MAX_ATTEMPTS))
                dst = "failed" if exhausted else "pending"
                job["error"] = job.get("error") or "reaped: stale heartbeat"
                job["worker"] = None
                job["heartbeat_at"] = None
                job["claimed_at"] = None
                if exhausted:
                    job["finished_at"] = now
                job["history"].append(
                    {"event": "reaped-parked" if exhausted else "reaped",
                     "at": now})
                self._move(job, p, dst)
                reaped.append(job)
        return reaped

    def stats(self, now=None):
        now = _now() if now is None else now
        by_state = {s: 0 for s in STATES}
        by_kind: dict[str, int] = {}
        oldest_pending_age = None
        for job in self._all_jobs():
            by_state[job["state"]] = by_state.get(job["state"], 0) + 1
            by_kind[job["kind"]] = by_kind.get(job["kind"], 0) + 1
            if job["state"] == "pending":
                age = now - float(job.get("submitted_at", now))
                if oldest_pending_age is None or age > oldest_pending_age:
                    oldest_pending_age = age
        return {"by_state": by_state, "by_kind": by_kind,
                "total": sum(by_state.values()),
                "oldest_pending_age_s": oldest_pending_age,
                "root": str(self.root)}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _parse_env(pairs):
    env = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--env expects KEY=VALUE, got {pair!r}")
        k, v = pair.split("=", 1)
        env[k] = v
    return env or None


def _print_job(job):
    print(json.dumps(job, indent=2, sort_keys=True))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="labqueue", description=__doc__)
    parser.add_argument("--root", default=None,
                        help="state root (default: ./state next to this file, "
                             "or $LABQUEUE_ROOT)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("submit", help="submit a job")
    p.add_argument("--kind", default="other", choices=KINDS)
    p.add_argument("--submitted-by", default=os.environ.get("USER", "unknown"))
    p.add_argument("--timeout", type=float, default=None,
                   help="per-job stale timeout in seconds")
    p.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    p.add_argument("--cwd", default=None)
    p.add_argument("--env", action="append", default=[],
                   help="KEY=VALUE pin, repeatable (e.g. --env OMP_NUM_THREADS=2)")
    p.add_argument("--shell", default=None, help="shell command string payload")
    p.add_argument("argv", nargs="*", help="argv payload, after --")

    p = sub.add_parser("list", help="list jobs by state/priority")
    p.add_argument("--state", choices=STATES, default=None)
    p.add_argument("--kind", choices=KINDS, default=None)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("claim", help="claim highest-priority pending job")
    p.add_argument("--worker", required=True)
    p.add_argument("--kind", action="append", dest="kinds", default=None,
                   help="restrict to this kind, repeatable")

    p = sub.add_parser("heartbeat", help="refresh a running job's lease")
    p.add_argument("--worker", default=None)
    p.add_argument("job_id")

    p = sub.add_parser("complete", help="mark a running job done")
    p.add_argument("--worker", default=None)
    p.add_argument("--result", default=None, help="result string to record")
    p.add_argument("job_id")

    p = sub.add_parser("fail", help="fail a running job (retry or park)")
    p.add_argument("--worker", default=None)
    p.add_argument("--error", default=None)
    p.add_argument("job_id")

    p = sub.add_parser("release", help="release a running job back to pending")
    p.add_argument("--worker", default=None)
    p.add_argument("job_id")

    p = sub.add_parser("reap", help="reclaim stale running jobs")
    p.add_argument("--stale-after", type=float, default=None,
                   help="seconds (default: per-job timeout, else 300)")

    sub.add_parser("stats", help="counts by state/kind + oldest pending age")

    args = parser.parse_args(argv)
    q = LabQueue(args.root)

    try:
        if args.cmd == "submit":
            payload = {}
            if args.shell is not None:
                payload["shell"] = args.shell
            elif args.argv:
                payload["argv"] = args.argv
            else:
                parser.error("submit needs --shell STR or argv after --")
            if args.cwd:
                payload["cwd"] = args.cwd
            env = _parse_env(args.env)
            if env:
                payload["env"] = env
            job = q.submit(kind=args.kind, payload=payload,
                           submitted_by=args.submitted_by,
                           timeout=args.timeout, max_attempts=args.max_attempts)
            _print_job(job)
        elif args.cmd == "list":
            jobs = q.list_jobs(state=args.state, kind=args.kind)
            if args.json:
                print(json.dumps(jobs, indent=2, sort_keys=True))
            else:
                for j in jobs:
                    print(f"{j['id']}  {j['state']:<7} pri={j['priority']:<3} "
                          f"{j['kind']:<9} attempts={j['attempts']}/{j['max_attempts']} "
                          f"by={j['submitted_by']}")
                if not jobs:
                    print("(no jobs)")
        elif args.cmd == "claim":
            job = q.claim(worker=args.worker, kinds=args.kinds)
            if job is None:
                print("null")  # machine-readable: nothing to claim
                return 3
            _print_job(job)
        elif args.cmd == "heartbeat":
            _print_job(q.heartbeat(args.job_id, worker=args.worker))
        elif args.cmd == "complete":
            _print_job(q.complete(args.job_id, worker=args.worker,
                                  result=args.result))
        elif args.cmd == "fail":
            _print_job(q.fail(args.job_id, worker=args.worker, error=args.error))
        elif args.cmd == "release":
            _print_job(q.release(args.job_id, worker=args.worker))
        elif args.cmd == "reap":
            reaped = q.reap(stale_after=args.stale_after)
            print(json.dumps([j["id"] for j in reaped], indent=2))
        elif args.cmd == "stats":
            print(json.dumps(q.stats(), indent=2, sort_keys=True))
    except (KeyError, ValueError, PermissionError) as exc:
        print(f"labqueue: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
