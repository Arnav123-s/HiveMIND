"""Always on: the personal agent that runs as long as the device is on.

    python -m team serve [--port 8766]          (python -m team install starts it with the device)
One process, one queue, models loaded once:
- the API on http://127.0.0.1:8766 (OpenAI/Anthropic-compatible, jobs, the chat page at /); `hive "prompt"` sends
  its prompts here when the service is up
- the inbox: drop a .md or .txt file into inbox/ (or `python -m team add "task"`); the report lands in
  outbox/<name>.REPORT.md and the task file moves to inbox/done/
- the schedule: recurring tasks in memory/schedule.json, e.g. [{"task": "...", "every_hours": 24}]
- open long projects (team/project.py) are worked on whenever nothing else is asked, and resume after a restart
- when idle, plugged in, cool and not busy: dreaming (lessons, weight edits) once a day and growing cells from the
  hive's own decisions (team/cells/learn.py)
Device health (team/health.py): low priority, one core left free, models unloaded after 10 idle minutes, heavy work
only when it can't hurt, a pause when the CPU runs hot, no new job when the disk is nearly full (nothing is ever
deleted to make room). Only one service runs at a time.
KILL SWITCH: `python -m team stop`, POST /v1/stop, or a file named STOP in inbox/: the running jobs halt at once
(what they finished is kept) and the service stays up for the next task.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import config, health, memory

INBOX = config.ROOT / "inbox"
OUTBOX = config.ROOT / "outbox"
SCHEDULE = memory.HOME / "schedule.json"
LOCK = memory.HOME / "serve.lock"
LOG = memory.HOME / "serve.log"


def add(task):
    INBOX.mkdir(exist_ok=True)
    p = INBOX / f"task-{time.strftime('%Y%m%d-%H%M%S')}.md"
    p.write_text(task.strip() + "\n")
    return p


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def single_instance():
    """Hold a lock for as long as the service runs; None if another service already holds it."""
    f = open(LOCK, "a+")
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    f.seek(0)
    f.truncate()
    f.write(str(os.getpid()))
    f.flush()
    return f


def write_outbox(name, job):
    OUTBOX.mkdir(exist_ok=True)
    text = job.report or f"(no report: {job.status} {job.error})"
    if job.pending_approvals:
        text += "\n\n## Waiting for your approval\n" + "\n".join(
            f"- {a.get('agent')} wants to {a.get('kind')}: {a.get('detail')}" for a in job.pending_approvals)
    (OUTBOX / f"{name}.REPORT.md").write_text(text)
    log(f"done: {name} ({job.status}) -> {OUTBOX / (name + '.REPORT.md')}")


def unload_models():
    from . import llm
    from .cells import pool, runtime
    llm.unload_all()
    runtime.unload()
    pool.shutdown()


def background(last, dream_every_hours):
    """Dreaming and growing cells, only when the device can take it. Each runs in its own low-priority process."""
    why = health.why_not_heavy(config.ROOT)
    if why:
        return last
    if time.time() - last.get("dream", 0) > dream_every_hours * 3600:
        log("idle and healthy: dreaming (lessons from past runs, weight edits)")
        subprocess.run([sys.executable, "-m", "team", "dream"], cwd=config.ROOT)
        last["dream"] = time.time()
    elif time.time() - last.get("grow", 0) > dream_every_hours * 3600:
        log("idle and healthy: growing cells from the hive's own decisions")
        subprocess.run([sys.executable, "-m", "team", "grow"], cwd=config.ROOT)
        last["grow"] = time.time()
    elif time.time() - last.get("evolve", 0) > dream_every_hours * 3600:
        # the specialist that failed most in recent work gets its instructions evolved: the examiner diagnoses its
        # failures, the prompt-smith breeds variants, and one is kept only if it scores strictly higher on that
        # specialist's held-out evals (team/evolve.py). Nobody has to look at the failures first.
        from . import dream
        role = dream.worst_role()
        last["evolve"] = time.time()
        if role:
            log(f"idle and healthy: {role} failed most in recent work; evolving its instructions (gated)")
            subprocess.run([sys.executable, "-m", "team", "evolve", role, "--variants", "2"], cwd=config.ROOT)
    elif time.time() - last.get("school", 0) > dream_every_hours * 3600:
        # a small model learns a bigger member's job from that member, and takes it after an exam (team/school.py)
        log("idle and healthy: school (a small model learns a bigger member's job; it takes the job only after its exam)")
        subprocess.run([sys.executable, "-m", "team", "school"], cwd=config.ROOT)
        last["school"] = time.time()
    elif time.time() - last.get("recruit", 0) > dream_every_hours * 3600:
        # one small open model the hive does not have yet takes the roles' exams; it is enrolled where it measures
        # up, and taught where it is the better student (team/recruit.py). No login, nothing deleted, disk floor kept.
        log("idle and healthy: recruiting (a new small model takes the roles' exams)")
        subprocess.run([sys.executable, "-m", "team", "recruit"], cwd=config.ROOT)
        last["recruit"] = time.time()
    elif time.time() - last.get("life", 0) > dream_every_hours * 3600:
        log("idle and healthy: a turn of the hive's life (new jobs noticed in its own calls, cells grown, checked, retired)")
        subprocess.run([sys.executable, "-m", "team", "life"], cwd=config.ROOT)
        last["life"] = time.time()
    return last


def serve(port=8766, host="127.0.0.1", poll=10, dream_every_hours=24, idle_minutes=30, rounds=1):
    lock = single_instance()
    if lock is None:
        print(f"another HiveMIND service is already running (see {LOCK}); `hive` talks to it", flush=True)
        return 1
    health.lower_priority()
    from . import api
    from .sdk import Swarm
    swarm = Swarm(approve="never")  # nobody at the terminal: risky actions he did not order wait for him
    api.start(port, host, until_done=rounds, swarm=swarm, block=False)
    INBOX.mkdir(exist_ok=True)
    (INBOX / "done").mkdir(exist_ok=True)
    log(f"HiveMIND is on: http://{host}:{port}  inbox {INBOX}  outbox {OUTBOX}")
    waiting, last_work, loaded, last_bg = {}, time.time(), True, {}
    try:
        while True:
            for f in sorted(INBOX.glob("*.md")) + sorted(INBOX.glob("*.txt")):
                task = f.read_text().strip()
                f.rename(INBOX / "done" / f.name)
                if task:
                    try:
                        waiting[f.stem] = swarm.submit(task, until_done=rounds)
                        log(f"inbox: {f.stem} queued as job {waiting[f.stem].id}")
                    except ValueError as e:  # e.g. the disk is nearly full
                        OUTBOX.mkdir(exist_ok=True)
                        (OUTBOX / f"{f.stem}.REPORT.md").write_text(f"Not started: {e}\n")
                        log(f"inbox: {f.stem} not started: {e}")
            sched = json.loads(SCHEDULE.read_text()) if SCHEDULE.exists() else []
            changed = False
            for item in sched:
                if time.time() - item.get("last", 0) >= item.get("every_hours", 24) * 3600:
                    name = f"scheduled-{time.strftime('%Y%m%d-%H%M')}"
                    try:
                        waiting[name] = swarm.submit(item["task"], until_done=rounds)
                    except ValueError as e:
                        log(f"schedule: not started: {e}")
                    item["last"] = time.time()
                    changed = True
            if changed:
                SCHEDULE.write_text(json.dumps(sched, indent=1))
            for name, job in list(waiting.items()):
                if job.status in ("done", "stopped", "error"):
                    write_outbox(name, waiting.pop(name))
            if not any(j.status in ("queued", "running") for j in swarm.jobs.values()):
                from . import project  # open projects are worked on whenever nothing else is asked
                for p in project.open_projects()[:1]:
                    project.launch(p, swarm, log=log)
            busy = any(j.status in ("queued", "running") for j in swarm.jobs.values())
            if busy:
                last_work, loaded = time.time(), True
            elif loaded and time.time() - last_work > health.IDLE_UNLOAD:
                unload_models()  # RAM goes back to the device while nothing is asked
                loaded = False
                log("idle: models unloaded")
            if not busy and time.time() - last_work > idle_minutes * 60:
                last_bg = background(last_bg, dream_every_hours)
            time.sleep(poll)
    except KeyboardInterrupt:
        log("service stopped")
    finally:
        lock.close()
    return 0
