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
from pathlib import Path
import threading
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


_ACTIVE, _ALOCK = set(), threading.Lock()


def enter(run_dir):
    """A task starts in this process. True if it is the only one running."""
    with _ALOCK:
        _ACTIVE.add(str(run_dir))
        return len(_ACTIVE) == 1


def leave(run_dir):
    with _ALOCK:
        _ACTIVE.discard(str(run_dir))


def active():
    with _ALOCK:
        return len(_ACTIVE)


def archive(run_dir):
    """Keep the flag in the stopped run's folder as a record (never deleted). While other tasks of this process are
    still running, the flag stays (a copy is kept here): the kill switch stops every task, and the last one to stop
    moves the flag away so the next task can start."""
    with _ALOCK:
        others = len(_ACTIVE - {str(run_dir)})
    for f in (FLAG, INBOX_FLAG):
        if f.exists():
            if others:
                (Path(run_dir) / "STOP.flag").write_text(f.read_text())
            else:
                f.rename(Path(run_dir) / "STOP.flag")
