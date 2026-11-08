"""Kill switch: stop the running task immediately, everywhere at once.

Any of these sets the stop flag:
  terminal   Ctrl+C in the window running the task, or `python -m team stop` from any other terminal
  web page   the Stop button (python -m team web)
  serve      drop a file named STOP into agent-team/inbox/ (or create agent-team/STOP)

Every specialist checks the flag: the models between every generated token, the browser before every action,
running code is killed as a whole process group, and the hive between every step. Nothing runs after the flag is
seen. The run folder records what was finished, what was running, and who stopped it (STOPPED.txt, TRACE.md).
"""
import json
import time

from . import config

FLAG = config.ROOT / "STOP"
INBOX_FLAG = config.ROOT / "inbox" / "STOP"


class Stopped(Exception):
    """Raised wherever work is cut off by the kill switch."""


def requested():
    return FLAG.exists() or INBOX_FLAG.exists()


def request(by="terminal"):
    FLAG.write_text(json.dumps({"by": by, "at": time.strftime("%F %T")}))
    return FLAG


def info():
    for f in (FLAG, INBOX_FLAG):
        if f.exists():
            try:
                return json.loads(f.read_text() or "{}") | {"file": str(f)}
            except json.JSONDecodeError:
                return {"by": "STOP file", "at": time.strftime("%F %T"), "file": str(f)}
    return {}


def check():
    if requested():
        raise Stopped(info().get("by", "stop"))


def archive(run_dir):
    """Move the flag into the stopped run's folder (kept as a record, not deleted) so the next task can start."""
    for f in (FLAG, INBOX_FLAG):
        if f.exists():
            f.rename(run_dir / "STOP.flag")
