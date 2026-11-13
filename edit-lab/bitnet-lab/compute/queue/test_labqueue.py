#!/usr/bin/env python3
"""Tests for labqueue (Muse's work, Muse's side).

Stdlib unittest only — runs under system python3 and the lab venv python:
    python3 -m unittest test_labqueue -v
    python3 test_labqueue.py
"""
# Muse's work — Muse's side of the BitNet lab. Fable's side untouched.

import json
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labqueue
from labqueue import LabQueue


class QueueTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.q = LabQueue(Path(self._tmp.name) / "state")

    def submit(self, kind="probe", **kw):
        kw.setdefault("argv", ["python3", "train.py", "--arm", "x"])
        kw.setdefault("submitted_by", "test")
        return self.q.submit(kind=kind, **kw)


class TestSubmitAndList(QueueTestCase):
    def test_submit_creates_pending_job_with_all_fields(self):
        job = self.submit(kind="ladder", env={"OMP_NUM_THREADS": "2"},
                          cwd="/tmp", timeout=600)
        self.assertEqual(job["state"], "pending")
        self.assertEqual(job["kind"], "ladder")
        self.assertEqual(job["priority"], labqueue.PRIORITY["ladder"])
        self.assertEqual(job["attempts"], 0)
        self.assertIsNone(job["worker"])
        self.assertIsNone(job["heartbeat_at"])
        self.assertEqual(job["timeout"], 600)
        self.assertEqual(job["payload"]["argv"][0], "python3")
        self.assertEqual(job["payload"]["env"], {"OMP_NUM_THREADS": "2"})
        self.assertEqual(job["payload"]["cwd"], "/tmp")
        path = Path(self._tmp.name) / "state" / "pending" / f"{job['id']}.json"
        self.assertTrue(path.exists())
        self.assertEqual(json.loads(path.read_text())["id"], job["id"])

    def test_priority_derivation_order(self):
        self.assertLess(labqueue.priority_for("ladder"),
                        labqueue.priority_for("trial"))
        self.assertLess(labqueue.priority_for("growth"),
                        labqueue.priority_for("trial"))
        self.assertLess(labqueue.priority_for("trial"),
                        labqueue.priority_for("probe"))
        self.assertLess(labqueue.priority_for("probe"),
                        labqueue.priority_for("benchmark"))

    def test_shell_payload_and_bad_kind_rejected(self):
        job = self.q.submit(kind="other", shell="echo hi", submitted_by="t")
        self.assertEqual(job["payload"]["shell"], "echo hi")
        with self.assertRaises(ValueError):
            self.q.submit(kind="bogus", argv=["true"], submitted_by="t")
        with self.assertRaises(ValueError):
            self.q.submit(kind="probe", submitted_by="t")  # no argv/shell


class TestClaim(QueueTestCase):
    def test_claim_moves_to_running_and_sets_lease(self):
        job = self.submit()
        claimed = self.q.claim(worker="w1")
        self.assertEqual(claimed["id"], job["id"])
        self.assertEqual(claimed["state"], "running")
        self.assertEqual(claimed["worker"], "w1")
        self.assertIsNotNone(claimed["heartbeat_at"])
        self.assertEqual(claimed["attempts"], 1)
        self.assertEqual(self.q.list_jobs(state="pending"), [])

    def test_claim_empty_returns_none(self):
        self.assertIsNone(self.q.claim(worker="w1"))

    def test_priority_order_respected_in_claims(self):
        bench = self.submit(kind="benchmark")
        probe = self.submit(kind="probe")
        ladder = self.submit(kind="ladder")
        trial = self.submit(kind="trial")
        growth = self.submit(kind="growth")
        order = [self.q.claim(worker="w")["kind"] for _ in range(5)]
        # ladder & growth first (either order), then trial, probe, benchmark
        self.assertEqual(set(order[:2]), {"ladder", "growth"})
        self.assertEqual(order[2:], ["trial", "probe", "benchmark"])
        self.assertIsNotNone(bench and probe and ladder and trial and growth)

    def test_fifo_within_same_priority(self):
        a = self.submit(kind="probe")
        time.sleep(0.01)
        b = self.submit(kind="probe")
        self.assertEqual(self.q.claim(worker="w")["id"], a["id"])
        self.assertEqual(self.q.claim(worker="w")["id"], b["id"])

    def test_claim_kind_filter(self):
        self.submit(kind="probe")
        bench = self.submit(kind="benchmark")
        got = self.q.claim(worker="w", kinds=["benchmark"])
        self.assertEqual(got["id"], bench["id"])

    def test_parallel_claimers_never_get_same_job(self):
        n_jobs, n_workers = 20, 20
        ids = {self.submit(kind="probe")["id"] for _ in range(n_jobs)}
        root = Path(self._tmp.name) / "state"
        barrier = threading.Barrier(n_workers)

        def claim_one(i):
            q = LabQueue(root)  # separate instance/fds, same state dir
            barrier.wait(timeout=10)
            job = q.claim(worker=f"worker-{i}")
            return job["id"] if job else None

        with ThreadPoolExecutor(max_workers=n_workers) as ex:
            results = list(ex.map(claim_one, range(n_workers)))
        self.assertNotIn(None, results)
        self.assertEqual(len(results), len(set(results)),
                         "two workers claimed the same job")
        self.assertEqual(set(results), ids)
        self.assertIsNone(self.q.claim(worker="late"))


class TestLifecycle(QueueTestCase):
    def test_complete_moves_to_done(self):
        job = self.submit()
        self.q.claim(worker="w1")
        done = self.q.complete(job["id"], worker="w1", result="loss=2.85")
        self.assertEqual(done["state"], "done")
        self.assertEqual(done["result"], "loss=2.85")
        self.assertEqual(self.q.stats()["by_state"]["done"], 1)

    def test_wrong_worker_cannot_complete_or_heartbeat(self):
        job = self.submit()
        self.q.claim(worker="w1")
        with self.assertRaises(PermissionError):
            self.q.complete(job["id"], worker="w2")
        with self.assertRaises(PermissionError):
            self.q.heartbeat(job["id"], worker="w2")

    def test_heartbeat_refreshes_lease(self):
        job = self.submit()
        claimed = self.q.claim(worker="w1")
        time.sleep(0.02)
        beat = self.q.heartbeat(job["id"], worker="w1")
        self.assertGreater(beat["heartbeat_at"], claimed["heartbeat_at"])

    def test_fail_retries_then_parks_in_failed(self):
        job = self.submit(max_attempts=2)
        self.q.claim(worker="w1")
        retried = self.q.fail(job["id"], worker="w1", error="boom")
        self.assertEqual(retried["state"], "pending")
        self.assertEqual(retried["attempts"], 1)
        self.q.claim(worker="w1")
        parked = self.q.fail(job["id"], worker="w1", error="boom again")
        self.assertEqual(parked["state"], "failed")
        self.assertIsNone(self.q.claim(worker="w1"))

    def test_release_does_not_consume_attempt(self):
        job = self.submit(max_attempts=1)
        self.q.claim(worker="w1")
        released = self.q.release(job["id"], worker="w1")
        self.assertEqual(released["state"], "pending")
        self.assertEqual(released["attempts"], 0)
        self.assertIsNone(released["worker"])
        # Even with max_attempts=1 the released job is claimable again,
        # and a subsequent genuine failure is what parks it.
        self.assertEqual(self.q.claim(worker="w2")["id"], job["id"])
        self.assertEqual(self.q.fail(job["id"], worker="w2")["state"], "failed")


class TestReap(QueueTestCase):
    def test_stale_job_reaped_and_rerunnable(self):
        job = self.submit()
        claimed = self.q.claim(worker="dead-worker")
        stale_now = claimed["heartbeat_at"] + 10_000
        reaped = self.q.reap(stale_after=300, now=stale_now)
        self.assertEqual([j["id"] for j in reaped], [job["id"]])
        again = self.q.claim(worker="w2")
        self.assertEqual(again["id"], job["id"])
        self.assertEqual(again["worker"], "w2")

    def test_fresh_job_not_reaped(self):
        self.submit()
        self.q.claim(worker="w1")
        self.assertEqual(self.q.reap(stale_after=300), [])
        self.assertEqual(self.q.stats()["by_state"]["running"], 1)

    def test_heartbeat_keeps_job_alive_past_original_claim(self):
        job = self.submit()
        self.q.claim(worker="w1")
        self.q.heartbeat(job["id"], worker="w1")
        hb = self.q.get(job["id"])["heartbeat_at"]
        self.assertEqual(self.q.reap(stale_after=60, now=hb + 30), [])
        self.assertEqual(len(self.q.reap(stale_after=60, now=hb + 3600)), 1)

    def test_reap_parks_exhausted_job(self):
        job = self.submit(max_attempts=1)
        claimed = self.q.claim(worker="w1")
        reaped = self.q.reap(stale_after=10,
                             now=claimed["heartbeat_at"] + 100)
        self.assertEqual(reaped[0]["state"], "failed")


class TestStats(QueueTestCase):
    def test_stats_counts_and_oldest_pending_age(self):
        old = self.submit(kind="probe")
        self.submit(kind="trial")
        self.q.claim(worker="w")  # claims the trial (higher priority)
        stats = self.q.stats(now=time.time() + 120)
        self.assertEqual(stats["by_state"]["pending"], 1)
        self.assertEqual(stats["by_state"]["running"], 1)
        self.assertEqual(stats["by_kind"], {"probe": 1, "trial": 1})
        self.assertEqual(stats["total"], 2)
        self.assertGreaterEqual(stats["oldest_pending_age_s"], 120)
        self.assertIsNotNone(old)

    def test_stats_empty_queue(self):
        stats = self.q.stats()
        self.assertEqual(stats["total"], 0)
        self.assertIsNone(stats["oldest_pending_age_s"])


class TestCLI(QueueTestCase):
    def test_cli_round_trip(self):
        import subprocess
        script = str(Path(__file__).resolve().parent / "labqueue.py")
        root = str(Path(self._tmp.name) / "cli-state")

        def run(*a, expect=0):
            r = subprocess.run([sys.executable, script, "--root", root, *a],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, expect, r.stderr)
            return r.stdout

        out = run("submit", "--kind", "probe", "--submitted-by", "cli-test",
                  "--env", "OMP_NUM_THREADS=2", "--",
                  "python3", "train.py", "--arm", "x")
        job = json.loads(out)
        self.assertEqual(job["payload"]["env"], {"OMP_NUM_THREADS": "2"})
        claimed = json.loads(run("claim", "--worker", "cli-w1"))
        self.assertEqual(claimed["id"], job["id"])
        run("claim", "--worker", "cli-w2", expect=3)  # nothing left
        run("heartbeat", "--worker", "cli-w1", job["id"])
        run("complete", "--worker", "cli-w1", "--result", "ok", job["id"])
        stats = json.loads(run("stats"))
        self.assertEqual(stats["by_state"]["done"], 1)
        self.assertIn(job["id"], run("list", "--json"))


if __name__ == "__main__":
    unittest.main()
