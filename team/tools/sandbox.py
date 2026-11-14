"""Runs Python the coder wrote, in the run's workspace folder, with a timeout.

Not an isolation boundary: code runs as the current user. The guard checks
the code for deleting, sending and spending before it runs.
"""
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

from .. import config


# what a program needs to run, read files and reach the web (proxies, certificates); never tokens, keys or passwords
# from the environment: model-written code got GH_TOKEN and cloud keys with everything else
PASS = re.compile(r"^(PATH|HOME|USER|LOGNAME|SHELL|LANG|LANGUAGE|LC_\w+|TZ|TMPDIR|TEMP|TMP|VIRTUAL_ENV|PYTHONPATH|"
                  r"PYTHONHOME|PYTHONIOENCODING|SSL_CERT_FILE|SSL_CERT_DIR|REQUESTS_CA_BUNDLE|CURL_CA_BUNDLE|"
                  r"(HTTPS?|NO|ALL)_PROXY|(https?|no|all)_proxy|HF_HOME|HF_HUB_OFFLINE|TRANSFORMERS_CACHE|XDG_\w+_HOME|"
                  r"MPLBACKEND|MPLCONFIGDIR|PLAYWRIGHT_BROWSERS_PATH|SYSTEMROOT|WINDIR|COMSPEC|PATHEXT|APPDATA|"
                  r"LOCALAPPDATA|USERPROFILE|HOMEDRIVE|HOMEPATH)$")
SECRET = re.compile(r"TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|ACCESS_KEY|CREDENTIAL|AUTH", re.I)


def program_env():
    """The environment model-written code runs with: only PASS names, and never one that looks like a secret."""
    env = {k: v for k, v in os.environ.items() if PASS.match(k) and not SECRET.search(k)}
    env["PYTHONUNBUFFERED"] = "1"
    # charts are drawn to files, never to a window: on his desktop plt.show() would open one and wait until the timeout
    env.setdefault("MPLBACKEND", "Agg")
    return env


# every program the hive runs reports the web requests that came back as errors, on stderr: a program that read the
# listing's "next" link joined to the site's home page got a 404 page, parsed it as an empty listing and finished
# "successfully" with two of the three cheapest books (nothing raised, so nothing told the coder)
HOOK = Path(__file__).resolve().parent / "program_hooks"
HTTP_LINE = re.compile(r"^HIVE-HTTP: (\w+) (\S+) returned (\d{3})$", re.M)
_HOOK_SRC = """import sys
try:
    import requests as _rq
    _orig = _rq.Session.request
    def _request(self, method, url, *a, **k):
        r = _orig(self, method, url, *a, **k)
        if r.status_code >= 400:
            sys.stderr.write("HIVE-HTTP: %s %s returned %d\\n" % (method, r.url, r.status_code))
        return r
    _rq.Session.request = _request
except Exception:
    pass


def look(x, _depth=0, _most=14):
    '''The hive's eyes, built into every program a member writes: prints what is really there. JSON data: its
    keys, types and short values, nested. The text of a web page: its title, its links (text -> address) and its
    first lines of text. A requests response: whichever of the two it holds.'''
    pad = "  " * _depth
    if hasattr(x, "status_code") and hasattr(x, "text"):
        try:
            return look(x.json(), _depth, _most)
        except Exception:
            return look(x.text, _depth, _most)
    if isinstance(x, bytes):
        x = x.decode("utf-8", "replace")
    if isinstance(x, str) and "<" in x[:3000] and "</" in x:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(x, "html.parser")
            print("PAGE title:", (soup.title.get_text(strip=True) if soup.title else "")[:100])
            seen, n = set(), 0
            for a in soup.find_all("a", href=True):
                key = (a.get_text(" ", strip=True)[:60], a["href"])
                if key in seen or not key[0]:
                    continue
                seen.add(key)
                n += 1
                if n <= 70:
                    print("  link %r -> %s" % key)
            if n > 70:
                print("  ... %d links in all" % n)
            for t in soup(["script", "style"]):
                t.decompose()
            lines = [ln.strip() for ln in soup.get_text("\\n").splitlines() if ln.strip()]
            print("TEXT (%d lines; the first 30):" % len(lines))
            for ln in lines[:30]:
                print("  " + ln[:110])
            return
        except Exception as e:
            print("(not read as a page: %s)" % e)
    if isinstance(x, dict):
        if len(x) > 20:  # many keys of one kind (versions, dates, ids): two of them, and the last ones by name
            _most = 2
        for i, (k, v) in enumerate(x.items()):
            if i >= _most:
                print(pad + "... %d keys in all; the last ones: %s" % (len(x), ", ".join(repr(k) for k in list(x)[-3:])))
                break
            if isinstance(v, (dict, list)):
                print(pad + "%r: %s of %d" % (k, type(v).__name__, len(v)))
                if _depth < 3:
                    look(v, _depth + 1, 6)
            else:
                print(pad + "%r: %s" % (k, repr(v)[:90]))
    elif isinstance(x, (list, tuple)):
        print(pad + "[%d items; the first:]" % len(x))
        if x and _depth < 4:
            look(x[0], _depth + 1, 8)
    else:
        print(pad + repr(x)[:300])


try:
    import builtins as _b
    _b.look = look
except Exception:
    pass
"""


def http_errors(stderr):
    """[(url, status)] of the requests a program made that came back as errors."""
    return [(u, int(c)) for _, u, c in HTTP_LINE.findall(stderr or "")]


def run_python(code, workdir, name="main.py", timeout=None, args=()):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    path = workdir / name
    path.write_text(code)
    t0 = time.time()
    env = program_env()
    HOOK.mkdir(exist_ok=True)
    if not (HOOK / "sitecustomize.py").exists() or (HOOK / "sitecustomize.py").read_text() != _HOOK_SRC:
        (HOOK / "sitecustomize.py").write_text(_HOOK_SRC)
    env["PYTHONPATH"] = str(HOOK) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
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
