"""Runs Python the coder wrote, in the run's workspace folder, with a timeout.

Not an isolation boundary: code runs as the current user. The guard checks
the code for deleting, sending and spending before it runs.
"""
import os
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
    try:
        p = subprocess.run([sys.executable, name, *args], cwd=workdir, capture_output=True, text=True,
                           timeout=timeout or config.CODE_TIMEOUT, env=env)
        rc, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        rc, out, err = -9, (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), \
            f"TIMEOUT after {timeout or config.CODE_TIMEOUT}s"
    return {"returncode": rc, "stdout": out[-6000:], "stderr": err[-4000:], "seconds": round(time.time() - t0, 1),
            "path": str(path)}
