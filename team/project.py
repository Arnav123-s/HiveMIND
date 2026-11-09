"""Long projects: a goal too big for one job (a program built over days, a study with experiments) is split into
milestones, each one a job that must be checked done before the next starts.

    python -m team project "Build a command-line expense tracker in Python with tests"
    python -m team projects                       every project and how far it got
or say it in a hive conversation ("build me ...", "a project to ..."): it starts a project and you can ask how it goes.
- planner (4B coordinator): 3 to 12 milestones in order, each a concrete deliverable with how to check it
- each milestone runs as a hive job until nothing is left undone, in the project's own workspace
  (projects/<id>/workspace/): files accumulate across milestones and days, and every job sees what is there
- a milestone that is still not done after its attempts blocks the project: the reason is recorded and reported
- progress is saved after every milestone (projects/<id>/project.json): a restart, or the device turning off,
  resumes at the first milestone not done; the always-on agent works on open projects whenever it is idle
"""
import json
import re
import secrets
import time
from pathlib import Path

from . import config, llm

DIR = config.ROOT / "projects"
PLAN = """You plan a long project for Arnav's team of AI specialists (researcher, browser, coder, calculator, writer).
Split the PROJECT into 3 to 12 milestones, in order. Each milestone is one concrete deliverable the team can finish and
check in one job: a module or file with tests that pass, a dataset collected, an experiment run and measured, a
section written. Later milestones build on the files earlier ones made. Keep his names and requirements word for word.
Reply with JSON only:
{"milestones": [{"title": "short name", "task": "what to do, complete and specific", "done_when": "how to check it"}]}"""
BIG = re.compile(r"\b(project|multi[- ]day|over (the next |a few |several )?(days|weeks)|from scratch|build (me |us )?"
                 r"(an?|the|my) [\w -]{0,30}(app|application|tool|program|system|library|website|game|bot|service|api|"
                 r"pipeline|dashboard)|implement (an?|the) (full|complete|whole)|research (study|project)|literature "
                 r"review|write (a|the) (paper|thesis|book))\b", re.I)


def big(msg):
    """Is this a long project rather than one job?"""
    return bool(BIG.search(msg or ""))


class Project:
    def __init__(self, pid, goal, milestones=None, status="planned", created=None):
        self.id, self.goal, self.milestones, self.status = pid, goal, milestones or [], status
        self.created = created or time.time()
        self.dir = DIR / pid
        self.workspace = self.dir / "workspace"

    # ---- state ----------------------------------------------------------------------------------------------
    def save(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self.workspace.mkdir(exist_ok=True)
        (self.dir / "project.json").write_text(json.dumps({"id": self.id, "goal": self.goal, "status": self.status,
                                                           "created": self.created, "milestones": self.milestones},
                                                          indent=1))

    @classmethod
    def load(cls, pid):
        d = json.loads((DIR / pid / "project.json").read_text())
        return cls(d["id"], d["goal"], d["milestones"], d["status"], d.get("created"))

    @classmethod
    def all(cls):
        return [cls.load(p.parent.name) for p in sorted(DIR.glob("*/project.json"))] if DIR.exists() else []

    def progress(self):
        done = sum(m["status"] == "done" for m in self.milestones)
        nxt = next((m["title"] for m in self.milestones if m["status"] != "done"), None)
        return (f"project {self.id}: {self.status}, {done}/{len(self.milestones)} milestones done"
                + (f"; next: {nxt}" if nxt and self.status not in ("done",) else ""))

    # ---- planning -------------------------------------------------------------------------------------------
    @classmethod
    def start(cls, goal):
        pid = time.strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)
        data, _ = llm.chat_json("coordinator", [{"role": "system", "content": PLAN},
                                                {"role": "user", "content": f"PROJECT: {goal}"}], max_new_tokens=1200)
        ms = [m for m in (data or {}).get("milestones", []) if isinstance(m, dict) and m.get("task")] \
            if isinstance(data, dict) else []
        if not ms:  # no usable plan: the whole goal as one milestone (the hive still plans its steps)
            ms = [{"title": goal[:60], "task": goal, "done_when": "the goal is met"}]
        p = cls(pid, goal, [{"title": str(m.get("title") or m["task"])[:80], "task": str(m["task"]),
                             "done_when": str(m.get("done_when", "")), "status": "todo", "attempts": 0, "jobs": [],
                             "summary": ""} for m in ms[:12]], status="running")
        p.save()
        return p

    # ---- doing ----------------------------------------------------------------------------------------------
    def context(self):
        """What the project has so far: for every milestone job (context, never orders)."""
        done = [m for m in self.milestones if m["status"] == "done"]
        files = sorted(str(f.relative_to(self.workspace)) for f in self.workspace.rglob("*")
                       if f.is_file() and not f.name.startswith("."))[:60] if self.workspace.exists() else []
        out = [f"This job is one milestone of a longer project: {self.goal}"]
        if done:
            out.append("Milestones already done:\n" + "\n".join(f"- {m['title']}: {m['summary'][:400]}" for m in done))
        if files:
            out.append("Files in the project's workspace (the work so far; build on them, keep them working):\n"
                       + "\n".join(f"- {f}" for f in files))
        return "\n\n".join(out)

    def run(self, swarm, rounds=2, attempts=2, log=print):
        """Work through the milestones not done yet. Returns the project's status."""
        from .sdk import body
        self.status = "running"
        self.save()
        for m in self.milestones:
            if m["status"] == "done":
                continue
            while m["attempts"] < attempts:
                m["attempts"] += 1
                log(f"{self.id}: milestone '{m['title']}' (attempt {m['attempts']})")
                task = m["task"] + (f"\nDone when: {m['done_when']}" if m["done_when"] else "")
                job = swarm.submit(task, until_done=rounds, context=self.context(), workdir=self.workspace).wait()
                m["jobs"].append(job.id)
                if job.status == "stopped":
                    self.status = "stopped"
                    self.save()
                    return self.status
                if job.status == "done" and not job.unmet:
                    m["status"], m["summary"] = "done", body(job.report)[:1500]
                    break
                m["summary"] = f"not done: {'; '.join(job.unmet[:5]) or job.error or job.status}"
                self.save()
            self.save()
            if m["status"] != "done":
                m["status"], self.status = "blocked", "blocked"
                self.save()
                log(f"{self.id}: blocked at '{m['title']}': {m['summary'][:200]}")
                self.report()
                return self.status
        self.status = "done"
        self.save()
        self.report()
        log(f"{self.id}: done ({len(self.milestones)} milestones)")
        return self.status

    def report(self):
        lines = [f"# Project: {self.goal}", "", self.progress(), ""]
        for m in self.milestones:
            mark = {"done": "✅", "blocked": "❌"}.get(m["status"], "…")
            lines += [f"## {mark} {m['title']}", m["summary"] or "(not started)", ""]
        files = sorted(str(f.relative_to(self.workspace)) for f in self.workspace.rglob("*")
                       if f.is_file() and not f.name.startswith(".")) if self.workspace.exists() else []
        if files:
            lines += ["## Files", *[f"- workspace/{f}" for f in files]]
        (self.dir / "PROJECT_REPORT.md").write_text("\n".join(lines) + "\n")
        return self.dir / "PROJECT_REPORT.md"


def open_projects():
    return [p for p in Project.all() if p.status in ("running", "planned")]


def status_text():
    ps = Project.all()
    return "\n".join(p.progress() for p in ps[-10:]) if ps else "no projects yet"


_RUNNING = {}


def launch(goal_or_project, swarm, log=print, rounds=2):
    """Start (or resume) a project in the background on this swarm. Returns the project."""
    import threading
    p = goal_or_project if isinstance(goal_or_project, Project) else Project.start(goal_or_project)
    t = _RUNNING.get(p.id)
    if t and t.is_alive():
        return p

    def work():
        try:
            p.run(swarm, rounds=rounds, log=log)
        except Exception as e:  # noqa: BLE001 - a crash blocks the project, never the agent
            p.status = "blocked"
            p.save()
            log(f"{p.id}: stopped by an error: {type(e).__name__}: {e}")
    _RUNNING[p.id] = threading.Thread(target=work, daemon=True, name=f"project-{p.id}")
    _RUNNING[p.id].start()
    return p


def started_text(p):
    return (f"Started project {p.id} with {len(p.milestones)} milestones:\n"
            + "\n".join(f"{i + 1}. {m['title']}" for i, m in enumerate(p.milestones))
            + "\nI'm working through them now and keep going until they are done (it resumes after a restart). "
              "Ask me how it is going any time.")
