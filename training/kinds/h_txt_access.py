"""The kind h_txt_access: the lines of a web server's log that match a described pattern, counted by class (hard: text).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import _fill

KIND = "h_txt_access"
FAMILY = "hard: text"
HARD = True
ORDER = 430
GIVEN_FILE = True

PATHS = ["/api/users", "/api/orders/17", "/api/login", "/apiary/index.html", "/static/api/app.js", "/index.html", "/api", "/docs/api/"]
STATUS = [200, 200, 201, 204, 301, 304, 400, 401, 404, 404, 500, 502, 503]
CLASSES = ["2xx", "3xx", "4xx", "5xx"]


def h_txt_access(r):
    ips = [f"10.0.{r.randrange(0, 9)}.{r.randrange(2, 250)}" for _ in range(5)]
    method = r.choice(["GET", "POST"])
    rows = []
    for _ in range(r.randrange(14, 22)):
        rows.append((r.choice(ips), f"{r.randrange(8, 18):02d}:{r.randrange(60):02d}:{r.randrange(60):02d}", r.choice(["GET", "GET", "POST", "DELETE"]),
                     r.choice(PATHS), r.choice(STATUS), r.randrange(80, 9000)))
    lines = [f'{ip} - - [12/Mar/2026:{t} +0000] "{m} {p} HTTP/1.1" {s} {n}' for ip, t, m, p, s, n in rows]
    count = {c: sum(1 for _, _, m, p, s, _ in rows if m == method and p.startswith("/api/") and str(s)[0] == c[0]) for c in CLASSES}
    clients = len({ip for ip, _, _, _, s, _ in rows if s >= 500})

    def check(run, report):
        body = B._body(report)
        got = {}
        for ln in body.splitlines():
            m = re.match(r"\W*(2xx|3xx|4xx|5xx|clients)\W*:?\s*(\d+)\b", ln.strip(), re.I)
            if m and m.group(1).lower() not in got:
                got[m.group(1).lower()] = int(m.group(2))
        want = count | {"clients": clients}
        return got == want, f"wants {want}; got {got}"
    return ("hard: text", "a server log's matching lines counted by class", "Here is a web server's access log:\n" + "\n".join(lines)
            + f"\nTake the {method} requests whose path begins with '/api/' (so '/api' alone, '/apiary/...' and '/docs/api/' do not "
            "count) and count them by the class of their status code. Then count the distinct client addresses that got a status "
            "of 500 or more, on any path and with any method. Answer in five lines: '2xx: ', '3xx: ', '4xx: ', '5xx: ', 'clients: '.", check)


def access(task, copy=False):
    """The log is data the task gives: the runtime saves it as a file, so the program reads access.log and stays short
    (as h_log's lesson does); copy: the log copied into the program instead (a task of several parts whose first block
    of data is another part's)."""
    m = re.search(r"Here is a web server's access log:\n(.*?)\nTake the (\w+) requests whose path", task, re.S)
    if not m:
        return None
    lines = repr(m.group(1)) + ".splitlines()" if copy else 'open("access.log")'
    return _fill('''c = {k: 0 for k in ("2xx", "3xx", "4xx", "5xx")}
s = set()
for l in __LINES__:
    w = l.split()
    if w[5] == '"' + __METHOD__ and w[6].startswith("/api/"):
        c[w[8][0] + "xx"] += 1
    if int(w[8]) >= 500:
        s.add(w[0])
for k in c:
    print(f"{k}: {c[k]}")
print("clients:", len(s))
''', method=m.group(2)).replace("__LINES__", lines)


make = h_txt_access
lesson = access
