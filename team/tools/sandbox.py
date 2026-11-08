"""Runs Python the coder wrote, in the run's workspace folder, with a timeout.

Not an isolation boundary: code runs as the current user. The guard checks
the code for deleting, sending and spending before it runs.
"""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .. import config


def run_python(code, workdir, name="main.py", timeout=None, args=()):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    path = workdir / name
    path.write_text(code)
    t0 = time.time()
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    from .. import stop
    limit = timeout or config.CODE_TIMEOUT
    out_f, err_f = open(workdir / f".{name}.out", "w+"), open(workdir / f".{name}.err", "w+")
    p = subprocess.Popen([sys.executable, name, *args], cwd=workdir, stdout=out_f, stderr=err_f, text=True, env=env,
                         start_new_session=True)  # own process group: the kill switch takes children too
    rc, killed = None, None
    while rc is None:
        try:
            rc = p.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            if stop.requested():
                killed = "STOPPED by the kill switch"
            elif time.time() - t0 > limit:
                killed = f"TIMEOUT after {limit}s"
            if killed:
                os.killpg(p.pid, signal.SIGKILL)
                rc = p.wait()
    out_f.seek(0)
    err_f.seek(0)
    out, err = out_f.read(), err_f.read() + (f"\n{killed}" if killed else "")
    out_f.close()
    err_f.close()
    if killed and killed.startswith("STOPPED"):
        stop.check()
    return {"returncode": rc, "stdout": out[-6000:], "stderr": err[-4000:], "seconds": round(time.time() - t0, 1),
            "path": str(path)}
