"""The kind h_txt_ini: a config text in the INI form read by its rules, and a lookup answered from it (hard: text).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed. It is
held out: never practised or taught, so what the hive scores on it is what carries over from the kinds it was taught.
"""
import re

from training import hive_bench as B
from training.kinds._common import _says

KIND = "h_txt_ini"
FAMILY = "hard: text"
HARD = True
ORDER = 470
HELD_OUT = True

SECTIONS = ["server", "database", "mail", "cache", "logging"]
KEYS = ["host", "port", "user", "timeout", "level", "path", "retries"]


def _value(r, key):
    return {"host": f"10.0.{r.randrange(0, 9)}.{r.randrange(2, 250)}", "port": str(r.randrange(1024, 9999)),
            "user": r.choice(["shop", "admin", "relay", "batch"]), "timeout": f"{r.randrange(5, 120)}s",
            "level": r.choice(["debug", "info", "warn"]), "path": r.choice(["/var/data", "/srv/app", "/tmp/cache"]),
            "retries": str(r.randrange(1, 9))}[key]


def h_txt_ini(r):
    names = r.sample(SECTIONS, r.randrange(3, 5))
    lines, data = [r.choice(["; settings for the shop", "# written by hand, read with care"])], {}
    for s in names:
        lines.append(r.choice([f"[{s}]", f"[ {s} ]", f"[{s.upper()}]"]))
        data[s] = {}
        for k in r.sample(KEYS, r.randrange(2, 5)):
            v = _value(r, k)
            if r.random() < 0.3:  # an old value commented out
                lines.append(f"{r.choice([';', '#'])} {k} = {_value(r, k)}")
            lines.append(f"{k if r.random() < 0.7 else k.upper()}{r.choice(['=', ' = ', '  =  ', ' ='])}{v}")
            data[s][k] = v
            if r.random() < 0.25:  # set again further down: the later one counts
                v = _value(r, k)
                lines.append(f"{k} = {v}")
                data[s][k] = v
    ask = r.choice(names)
    key = r.choice(sorted(data[ask]))
    other = r.choice(names)
    value, n = data[ask][key], len(data[other])

    def check(run, report):
        body = B._body(report)
        got = [ln.split(":", 1)[1].strip().strip("'\"`") for ln in body.splitlines() if re.match(r"\W*value\s*:", ln.strip(), re.I)]
        keys = [ln for ln in body.splitlines() if re.match(r"\W*keys\s*:", ln.strip(), re.I)]
        ok = bool(got) and got[0] == value and bool(keys) and _says(keys[0], n, 0.1)
        return ok, f"wants value: {value}, keys: {n}; got {got[:1]} and {keys[:1]}"
    return ("hard: text", "a lookup in a config text", "Here is a config file:\n" + "\n".join(lines) + "\nRead it by these rules: a "
            "line that begins with ';' or '#' is a comment; section names and keys do not care about capital letters or about "
            "spaces around them; spaces around '=' do not count; a key set twice in one section takes its later value. What is "
            f"the value of '{key}' in the section '{ask}', and how many distinct keys does the section '{other}' have? Answer in "
            "two lines: 'value: ', 'keys: '.", check)


make = h_txt_ini
lesson = None
