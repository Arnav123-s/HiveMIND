"""Give the swarm a task and let it run unattended until it is done.

    from team.sdk import Swarm
    swarm = Swarm()
    job = swarm.submit("Find the three cheapest Mystery books on books.toscrape.com and save them to a CSV",
                       until_done=2)
    for ev in job.events(follow=True):        # live: what each specialist is doing
        print(ev["agent"], ev["kind"], ev["msg"])
    print(job.report)                         # the finished deliverable (Markdown)
    print(job.files)                          # files the team made
    print(job.unmet)                          # anything still not done after every round (empty when done)

Unattended: nobody is asked anything. Risky actions (spend, delete, send, log in, sign up) happen only where the task
orders them; anything else is not done and listed in job.pending_approvals for you.
until_done=N: after a round, instructions the critic marked not done and steps the team could not confirm go back to the
swarm as a follow-up round (at most N more rounds). The job's report is the round with the fewest left undone.
Jobs run one at a time (the CPU is the limit), are kept in runs/<job id>/ and survive a restart.
"""
import json
import queue
import re
import secrets
import threading
import time
from pathlib import Path

from . import config, stop

FINISHED = ("done", "stopped", "error")


def unmet(report):
    """What a report says is still not done: its ❌ instructions and the steps the team could not confirm."""
    out = [ln[len("- ❌"):].strip() for ln in report.splitlines() if ln.startswith("- ❌")]
    m = re.search(r"\n## Not confirmed by the team\n(.*?)(?:\n## |\Z)", report, re.S)
    if m:
        out += [ln[2:].strip() for ln in m.group(1).splitlines() if ln.startswith("- ")]
    return out


def body(report):
    return report.split("\n## ")[0].strip()


class Job:
    def __init__(self, swarm, jid, task, until_done=0, allow_login=(), context="", created=None):
        self.swarm, self.id, self.task, self.until_done = swarm, jid, task, until_done
        self.allow_login, self.context = list(allow_login), context
        self.dir = swarm.root / jid
        self.status, self.error, self.rounds = "queued", "", []
        self.created, self.finished = created or time.time(), None
        self.best = None  # the round whose report is the job's report
        self._done = threading.Event()

    # ---- results -------------------------------------------------------------------------------------------
    def _round_dirs(self):
        return [self.dir / r["dir"] for r in self.rounds]

    @property
    def report(self):
        d = self.dir / self.best if self.best else (self._round_dirs() or [None])[-1]
        return (d / "REPORT.md").read_text() if d and (d / "REPORT.md").exists() else ""

    @property
    def unmet(self):
        return unmet(self.report)

    @property
    def files(self):
        return [str(p) for d in self._round_dirs() if (d / "work").exists()
                for p in sorted((d / "work").rglob("*")) if p.is_file() and not p.name.startswith(".")]

    @property
    def pending_approvals(self):
        return [a for r in self.rounds for a in r.get("pending_approvals", [])]

    def events(self, follow=False, poll=0.5, heartbeat=None):
        """The board's events, round after round; with follow=True, live until the job finishes. With heartbeat=S,
        None is yielded after S quiet seconds (a streaming server sends a keep-alive then)."""
        seen, quiet = {}, time.time()
        while True:
            finished = self.status in FINISHED
            for d in self._round_dirs() or ([self.dir / "r1"] if self.status == "running" else []):
                f = d / "events.jsonl"
                if not f.exists():
                    continue
                lines = f.read_text().splitlines()
                for line in lines[seen.get(d, 0):]:
                    try:
                        ev = json.loads(line) | {"round": d.name}
                    except json.JSONDecodeError:  # a line still being written: read it next time
                        lines = lines[:lines.index(line)]
                        break
                    quiet = time.time()
                    yield ev
                seen[d] = len(lines)
            if not follow or finished:
                return
            if heartbeat and time.time() - quiet > heartbeat:
                quiet = time.time()
                yield None
            time.sleep(poll)

    def wait(self, timeout=None):
        self._done.wait(timeout)
        return self

    def to_dict(self, report=True):
        d = {"id": self.id, "task": self.task, "status": self.status, "error": self.error, "created": self.created,
             "finished": self.finished, "until_done": self.until_done, "rounds": self.rounds, "dir": str(self.dir)}
        if report and self.status in FINISHED:
            d |= {"report": self.report, "unmet": self.unmet, "files": self.files,
                  "pending_approvals": self.pending_approvals}
        return d

    def _save(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "job.json").write_text(json.dumps(self.to_dict(report=False) | {"best": self.best,
                                                                                   "allow_login": self.allow_login}, indent=1))

    @classmethod
    def load(cls, swarm, path):
        d = json.loads((path / "job.json").read_text())
        j = cls(swarm, d["id"], d["task"], d.get("until_done", 0), d.get("allow_login", ()), created=d.get("created"))
        j.status = d["status"] if d["status"] in FINISHED else "error"  # a job cut off by a restart did not finish
        j.error = d.get("error") or ("" if d["status"] in FINISHED else "the swarm stopped before this job finished")
        j.rounds, j.finished, j.best = d.get("rounds", []), d.get("finished"), d.get("best")
        j._done.set()
        return j


class Swarm:
    """One swarm per process: jobs queue and run one at a time in a background thread."""

    def __init__(self, root=None, approve="never"):
        self.root = Path(root or config.RUNS)
        self.root.mkdir(parents=True, exist_ok=True)
        self.approve = approve
        self.jobs, self._q, self._lock, self._worker = {}, queue.Queue(), threading.Lock(), None

    def submit(self, task, until_done=0, allow_login=(), context=""):
        task = (task or "").strip()
        if not task:
            raise ValueError("empty task")
        jid = time.strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)
        job = Job(self, jid, task, max(0, int(until_done)), allow_login, context)
        job._save()
        (job.dir / "TASK.md").write_text(task + "\n")
        with self._lock:
            self.jobs[jid] = job
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._work, daemon=True, name="swarm-worker")
                self._worker.start()
        self._q.put(job)
        return job

    def run(self, task, **kw):
        return self.submit(task, **kw).wait()

    def get(self, jid):
        if jid in self.jobs:
            return self.jobs[jid]
        p = self.root / jid
        if re.fullmatch(r"[\w-]+", jid or "") and (p / "job.json").exists():
            return Job.load(self, p)
        return None

    def list(self, limit=20):
        ids = sorted({p.parent.name for p in self.root.glob("*/job.json")} | set(self.jobs), reverse=True)[:limit]
        return [j for j in (self.get(i) for i in ids) if j]

    def stop(self, reason="sdk: Swarm.stop()"):
        """Kill switch: the running job halts now (what it finished is kept); queued jobs still run."""
        return stop.request(reason)

    # ---- the worker ------------------------------------------------------------------------------------------
    def _work(self):
        while True:
            job = self._q.get()
            try:
                self._run(job)
            except Exception as e:  # noqa: BLE001 - a crash ends this job, never the swarm
                job.status, job.error = "error", f"{type(e).__name__}: {e}"
            finally:
                job.finished = time.time()
                job._save()
                job._done.set()

    def _run(self, job):
        from .hive import Hive
        job.status = "running"
        job._save()
        context, best = job.context, None
        for n in range(1, job.until_done + 2):
            rdir = job.dir / f"r{n}"
            # the order is always his task as written: an earlier round's answer is context, never read as orders
            out = Hive(job.task, rdir, approve=self.approve, allow_login=job.allow_login, context=context,
                       triage=n == 1).run()
            report = (rdir / "REPORT.md").read_text() if (rdir / "REPORT.md").exists() else out.get("report", "")
            left = unmet(report)
            job.rounds.append({"dir": rdir.name, "unmet": left, "pending_approvals": out.get("pending_approvals", [])})
            if best is None or len(left) <= best[1]:
                best = (rdir.name, len(left))
            job.best = best[0]
            job._save()
            if (rdir / "STOPPED.md").exists():
                job.status = "stopped"
                return
            if not left or n > job.until_done:
                break
            context = ((job.context + "\n\n") if job.context else "") + (
                f"An earlier round already did part of this task. Its verified answer:\n{body(report)[:3000]}\n\n"
                "Still not done (plan for these):\n" + "\n".join(f"- {x}" for x in left[:10]))
        job.status = "done"
