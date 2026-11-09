"""Always on: watch an inbox, run scheduled tasks, dream when idle.

    python -m team serve
Drop a task as a .md or .txt file into agent-team/inbox/ (or use `python -m team add "task"`).
KILL SWITCH: drop a file named STOP into agent-team/inbox/ - the running task halts at once (everything it
finished is recorded in its run folder) and serve stays up for the next task.
The report lands in agent-team/outbox/<name>.REPORT.md; the task file moves to inbox/done/.
Recurring tasks live in memory/schedule.json:
    [{"task": "Check the latest versions of my pinned packages", "every_hours": 24}]
"""
import json
import time
from pathlib import Path

from . import config, memory
from .hive import Hive

INBOX = config.ROOT / "inbox"
OUTBOX = config.ROOT / "outbox"
SCHEDULE = memory.HOME / "schedule.json"


def add(task):
    INBOX.mkdir(exist_ok=True)
    p = INBOX / f"task-{time.strftime('%Y%m%d-%H%M%S')}.md"
    p.write_text(task.strip() + "\n")
    return p


def _run(task, name):
    OUTBOX.mkdir(exist_ok=True)
    out = Hive(task, approve="never").run()  # nobody at the terminal: risky actions wait for Arnav
    report = Path(out["dir"]) / "REPORT.md"
    text = report.read_text() if report.exists() else out["report"]
    if out["pending_approvals"]:
        text += "\n\n## Waiting for your approval\n" + "\n".join(
            f"- {a['agent']} wants to {a['kind']}: {a['detail']}" for a in out["pending_approvals"])
    (OUTBOX / f"{name}.REPORT.md").write_text(text)
    print(f"done: {name} -> {OUTBOX / (name + '.REPORT.md')}", flush=True)


def serve(poll=20, dream_every_hours=24, idle_minutes=30):
    INBOX.mkdir(exist_ok=True)
    (INBOX / "done").mkdir(exist_ok=True)
    last_work = time.time()
    print(f"agent-team serving. Inbox: {INBOX}  Outbox: {OUTBOX}", flush=True)
    while True:
        for f in sorted(INBOX.glob("*.md")) + sorted(INBOX.glob("*.txt")):
            task = f.read_text().strip()
            f.rename(INBOX / "done" / f.name)
            if task:
                _run(task, f.stem)
                last_work = time.time()
        sched = json.loads(SCHEDULE.read_text()) if SCHEDULE.exists() else []
        changed = False
        for item in sched:
            if time.time() - item.get("last", 0) >= item.get("every_hours", 24) * 3600:
                _run(item["task"], f"scheduled-{time.strftime('%Y%m%d-%H%M')}")
                item["last"] = time.time()
                changed = True
                last_work = time.time()
        if changed:
            SCHEDULE.write_text(json.dumps(sched, indent=1))
        dreams = [json.loads(x) for x in memory.DREAMS.read_text().splitlines()] if memory.DREAMS.exists() else []
        last_dream = time.mktime(time.strptime(dreams[-1]["started"], "%Y-%m-%d %H:%M:%S")) if dreams else 0
        if time.time() - last_work > idle_minutes * 60 and time.time() - last_dream > dream_every_hours * 3600:
            from .dream import dream
            dream()
        time.sleep(poll)
