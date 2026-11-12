"""The scheduler daemon (arch. section 7; final-product item 5):
the process that CONSUMES the persistent cycle queue.

Phase C built the queue and the lock; nothing consumed them. This
daemon closes the loop:

    probe host -> governor decides -> peek the queue
      -> backoff or heavy-leg not admitted: HOLD the request
         (never popped, never dropped; the hold is recorded)
      -> pop -> run the cycle through FactoryLoop (checkpointed,
         resumable, lineage-written by the loop itself)
      -> file the section-9 report (reporter) after each cycle
      -> append the outcome to factory/queue_history.jsonl

Queue request shape (scheduler.CycleQueue items):
    {cycle_id, mode: "real"|"dry_run", subjects: [subject_id, ...]
     (optional — absent means all subjects), requires_heavy: bool
     (default False), requested_by, note}

The daemon is polite by construction: it takes the heavy-leg lock
only for requests that declare a heavy leg (none exist today —
every factory leg is seconds-class Tier-0 — but the discipline is
wired before it is needed), pauses between polls with
scheduler.polite_pause, and stops cleanly on its bounds. Run it
supervised:

    python3 -m factory.daemon --max-cycles 2
    python3 -m factory.daemon --enqueue '{"cycle_id": "...", "mode": "real", "subjects": ["commit-type-model"]}'
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from . import reporter as reporter_mod  # noqa: E402
from .contracts import Mode  # noqa: E402
from .host import Governor, probe_host  # noqa: E402
from .lineage import now_ts  # noqa: E402
from .loop import FactoryLoop  # noqa: E402
from .scheduler import CycleQueue, HeavyLegLock, polite_pause  # noqa: E402
from .subjects import load_subjects  # noqa: E402

FACTORY_DIR = Path(__file__).parent
LAB_ROOT = FACTORY_DIR.parent
HISTORY_PATH = FACTORY_DIR / "queue_history.jsonl"


class FactoryDaemon:
    def __init__(self, lab_root: Path = LAB_ROOT,
                 queue: Optional[CycleQueue] = None,
                 history_path: Optional[Path] = None,
                 reports_dir: Optional[Path] = None):
        self.lab_root = Path(lab_root)
        self.queue = queue or CycleQueue()
        self.history_path = Path(history_path) if history_path \
            else HISTORY_PATH
        self.reports_dir = Path(reports_dir) if reports_dir \
            else FACTORY_DIR / "reports"
        self.governor = Governor()

    # ------------------------------------------------------------ history
    def _history(self, record: Dict[str, Any]) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": now_ts(), **record},
                                ensure_ascii=False) + "\n")

    # ------------------------------------------------------------ one step
    def process_one(self) -> Optional[Dict[str, Any]]:
        """One daemon step. Returns a record of what happened, or
        None when the queue is empty. A held request (governor
        backoff, heavy leg not admitted, lock contention) is NOT
        popped — it stays at the head for a later, healthier step."""
        req = self.queue.peek()
        if req is None:
            return None
        profile = probe_host(str(self.lab_root))
        decision = self.governor.decide(profile, heavy_opt_in=False)
        if decision.backoff:
            rec = {"event": "held", "reason": f"governor backoff "
                                              f"({decision.cause})",
                   "request": req}
            self._history(rec)
            return rec
        lock = None
        if req.get("requires_heavy"):
            if not decision.allow_heavy:
                rec = {"event": "held",
                       "reason": "heavy leg not admitted by the "
                                 "governor on this host profile",
                       "request": req}
                self._history(rec)
                return rec
            lock = HeavyLegLock()
            got = lock.acquire(owner=f"daemon:{req.get('cycle_id')}")
            if not got["acquired"]:
                rec = {"event": "held",
                       "reason": f"heavy-leg lock held by "
                                 f"{(got.get('holder') or {}).get('owner')}",
                       "request": req}
                self._history(rec)
                return rec
        try:
            self.queue.pop()
            cycle_id = req.get("cycle_id") or \
                time.strftime("daemon-%Y%m%d-%H%M%S")
            mode = Mode(req.get("mode", "dry_run"))
            loop = FactoryLoop(lab_root=self.lab_root,
                               cycle_id=cycle_id, mode=mode)
            subjects = load_subjects(self.lab_root)
            wanted = req.get("subjects")
            if wanted:
                subjects = [s for s in subjects
                            if s.subject_id in wanted]
            report = loop.run_cycle(subjects)
            # section-9 report after every processed cycle
            rep = reporter_mod.collect()
            self.reports_dir.mkdir(parents=True, exist_ok=True)
            (self.reports_dir / "factory-report.json").write_text(
                json.dumps(rep, indent=1, ensure_ascii=False))
            (self.reports_dir / "factory-report.md").write_text(
                reporter_mod.render(rep))
            rec = {"event": "processed", "cycle_id": cycle_id,
                   "mode": mode.value,
                   "verdicts": {sid: (e.get("verify") or {}).get("verdict")
                                for sid, e in
                                report["subjects"].items()},
                   "blocked": report["blocked"],
                   "run_dir": f"factory/runs/{cycle_id}",
                   "request": req}
            self._history(rec)
            return rec
        finally:
            if lock is not None:
                lock.release()

    # ------------------------------------------------------------ the loop
    def run(self, max_cycles: Optional[int] = None,
            max_idle_polls: int = 3,
            poll_seconds: float = 2.0) -> Dict[str, Any]:
        processed = held = idle = 0
        records: List[Dict[str, Any]] = []
        while True:
            if max_cycles is not None and processed >= max_cycles:
                break
            rec = self.process_one()
            if rec is None:
                idle += 1
                if idle > max_idle_polls:
                    break
                polite_pause(poll_seconds)
                continue
            records.append(rec)
            if rec["event"] == "processed":
                processed += 1
                idle = 0
            else:
                held += 1
                idle += 1
                if idle > max_idle_polls:
                    break
                polite_pause(poll_seconds)
        return {"processed": processed, "held": held,
                "records": records}


def main() -> int:
    ap = argparse.ArgumentParser(description="Factory scheduler daemon")
    ap.add_argument("--max-cycles", type=int, default=None)
    ap.add_argument("--max-idle-polls", type=int, default=3)
    ap.add_argument("--poll-seconds", type=float, default=2.0)
    ap.add_argument("--enqueue", default=None,
                    help="JSON cycle request to enqueue before running")
    args = ap.parse_args()
    queue = CycleQueue()
    if args.enqueue:
        req = json.loads(args.enqueue)
        n = queue.enqueue(req)
        print(f"enqueued {req.get('cycle_id', '?')} (queue depth {n})")
    daemon = FactoryDaemon(queue=queue)
    summary = daemon.run(max_cycles=args.max_cycles,
                         max_idle_polls=args.max_idle_polls,
                         poll_seconds=args.poll_seconds)
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
