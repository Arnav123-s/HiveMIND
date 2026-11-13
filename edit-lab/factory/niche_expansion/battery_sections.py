"""Hand-authored battery sections for the niche-expansion subjects.

Muse's side, Hive growth department. These items were written BY
HAND for the battery only, in an idiom deliberately different from
the generators' template families (different library calls, names,
literal styles and code shapes) — the contract-judgment v3 lesson
(plan 5.5): a subject that only passes its own generator's surfaces
has proved nothing. They are never trained on; the runner uses them
only as contamination references and as the BEFORE-state probe.

run_sections() evaluates the sections through the real serving path
(factory.serve.ServingHive). Pre-adoption the jobs are unregistered,
so the expected result is the serving path's documented
no-specialist gap — recorded as the BEFORE state, not a failure.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

OUT = Path(__file__).parent / "battery_results.json"

Item = Tuple[str, str]

# ------------------------------------------------------------ sec-code
SEC_CODE_ITEMS: List[Item] = [
    # clean (near-misses in a fresh idiom)
    ("from pathlib import Path\n"
     "def load_banner():\n"
     "    return Path('assets/banner.txt').read_text()", "clean"),
    ("import random\nimport yaml\n"
     "def deal_and_load(deck, blob):\n"
     "    random.shuffle(deck)\n"
     "    return yaml.load(blob, Loader=yaml.SafeLoader)", "clean"),
    # path-traversal
    ("def fetch_upload(filename):\n"
     "    with open(os.path.join(UPLOADS, filename)) as fh:\n"
     "        return fh.read()", "path-traversal"),
    ("def peek():\n"
     "    return open('../../etc/app/secrets.txt').read()",
     "path-traversal"),
    # insecure-random
    ("import random\n"
     "def issue_temp_password():\n"
     "    return ''.join(random.choices('0123456789', k=6))",
     "insecure-random"),
    ("import random\n"
     "def next_api_token():\n"
     "    return '%032x' % random.getrandbits(128)", "insecure-random"),
    # unsafe-yaml-load
    ("import yaml\n"
     "def load_cfg(stream):\n"
     "    return yaml.load(stream, Loader=yaml.FullLoader)",
     "unsafe-yaml-load"),
    ("import yaml as y\n"
     "def parse(blob):\n"
     "    return y.unsafe_load(blob)", "unsafe-yaml-load"),
    # tls-verify-off
    ("def ping_hook():\n"
     "    return requests.head('https://hooks.example.net/ping', "
     "verify=False)", "tls-verify-off"),
    ("def check_site():\n"
     "    with requests.Session() as s:\n"
     "        return s.get('https://status.example.net/', verify=False)",
     "tls-verify-off"),
    # ssrf
    ("import requests\n"
     "def probe(target):\n"
     "    return requests.get(target, timeout=3).ok", "ssrf"),
    ("import urllib.request\n"
     "def grab(u):\n"
     "    return urllib.request.urlopen(u).read()", "ssrf"),
]

# ------------------------------------------------------------ data-format
DATA_FORMAT_ITEMS: List[Item] = [
    ('{"compass": {"bearing": 270, "marks": ["n", "w"]}, "active": true}',
     "json"),
    ("[3, 1, 4, 1, 5, 9]", "json"),
    ('{"harbor": "north", "berths": 12,}', "malformed-json"),
    ('["apple", "pear", "plum",]', "malformed-json"),
    ("day,high,low\nmon,21,14\ntue,23,15\nwed,19,12", "csv"),
    ('song,artist\n"Blue Sky","The Lanterns"\n"Red Door","Copper Club"\n'
     '"Long Road","Mesa Band"', "csv"),
    ('[kitchen]\noven = "gas"\nshelves = 4', "toml"),
    ('title = "Field Notes"\npage = 12\npublished = false', "toml"),
    ("The lighthouse keeper climbs the stairs at dusk each evening.",
     "plain-text"),
    ("Bring two chairs, a table, and the blue umbrella to the porch.",
     "plain-text"),
]

# ------------------------------------------------------------ sql
SQL_ITEMS: List[Item] = [
    ("SELECT last_name FROM employees WHERE dept = 'sales' "
     "ORDER BY last_name", "select"),
    ("select count(*) from invoices where paid = 0", "select"),
    ("INSERT INTO employees (last_name, dept) VALUES ('Ng', 'ops')",
     "insert"),
    ("insert into invoices (id, paid) values (44, 0)", "insert"),
    ("UPDATE employees SET dept = 'support' WHERE last_name = 'Ng'",
     "update"),
    ("UPDATE invoices SET paid = 1", "update"),
    ("DELETE FROM employees WHERE id = 9", "delete"),
    ("delete from invoices", "delete"),
    ("CREATE TABLE shifts (id INTEGER, label TEXT)", "create"),
    ("create table if not exists depots (code text, city text)", "create"),
    ("ALTER TABLE employees ADD COLUMN email TEXT", "alter"),
    ("alter table invoices rename to invoices_archive", "alter"),
    ("DROP TABLE shifts", "drop"),
    ("drop table if exists depots", "drop"),
]

SECTIONS: Dict[str, Dict[str, Any]] = {
    "classify-sec-code": {"job": "sec-code-model",
                          "items": SEC_CODE_ITEMS, "bar": 9},
    "classify-data-format": {"job": "data-format-model",
                             "items": DATA_FORMAT_ITEMS, "bar": 8},
    "classify-sql-statement": {"job": "sql-statement-model",
                               "items": SQL_ITEMS, "bar": 11},
}


def _sql_no_where_detail(items, results) -> str:
    subset = [(t, l) for (t, l), r in zip(items, results)
              if l in ("update", "delete")
              and not re.search(r"(?i)\bwhere\b", t)]
    if not subset:
        return "no update/delete-without-where items"
    right = sum(1 for (t, l), r in zip(items, results)
                if l in ("update", "delete")
                and not re.search(r"(?i)\bwhere\b", t)
                and r.get("output") == l)
    return (f"update/delete-without-where subset: "
            f"{right}/{len(subset)} correct")


def run_sections(hive=None) -> Dict[str, Any]:
    """Evaluate every section through ServingHive; write results to
    battery_results.json beside this module and return them."""
    if hive is None:
        from factory.serve import ServingHive
        hive = ServingHive.load()
    out: Dict[str, Any] = {}
    for name, sec in SECTIONS.items():
        results = [hive.serve({"kind": "classify", "job": sec["job"],
                               "text": text})
                   for text, _ in sec["items"]]
        n = len(sec["items"])
        right = sum(1 for (_, label), r in zip(sec["items"], results)
                    if r.get("output") == label)
        gaps = [r.get("gap") for r in results if r.get("gap")]
        detail = (f"{right}/{n} correct; bar {sec['bar']}/{n}")
        if gaps:
            detail += f"; gaps: {gaps[0]}"
        if name == "classify-sql-statement":
            detail += "; " + _sql_no_where_detail(sec["items"], results)
        out[name] = {"job": sec["job"], "right": right, "n": n,
                     "acc": round(right / n, 4) if n else 0.0,
                     "bar": sec["bar"], "detail": detail}
    OUT.write_text(json.dumps(out, indent=1))
    return out
