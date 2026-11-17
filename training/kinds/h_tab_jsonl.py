"""The kind h_tab_jsonl: a file of JSON lines given in the task, its events of one type counted by a nested field
(hard: tables).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import json
import re

from training import hive_bench as B
from training.kinds._common import _file, _fill, _says, HARD_NAMES as NAMES
from training.kinds import _tab

KIND = "h_tab_jsonl"
FAMILY = "hard: tables"
HARD = True
ORDER = 350

TYPES = ["purchase", "refund", "signup", "login"]
# the nested field counted: (its name in "user", its values)
FIELDS = [("plan", ["free", "pro", "team"]), ("country", ["PE", "NO", "KE", "VN", "PT"]), ("device", ["phone", "laptop", "tablet"])]


def h_tab_jsonl(r):
    field, values = r.choice(FIELDS)
    kind = r.choice(TYPES[:3])
    name = r.choice(["events.txt", "activity.log", "stream.txt"])
    out = r.choice(["counts.json", "by_field.json", "tally.json"])
    lines = []
    for i in range(r.randrange(14, 22)):
        user = {"name": r.choice(NAMES)}
        if r.random() < 0.85:  # some users do not say it: counted as "unknown"
            user[field] = r.choice(values)
        event = {"id": i + 1, "type": r.choice(TYPES[:3] + [kind]), "user": user}
        if event["type"] in ("purchase", "refund"):
            event["amount"] = r.randrange(100, 9000) / 100
        lines.append(event)
    if not any(e["type"] == kind for e in lines):  # none of the type asked: the first event is made one
        lines[0]["type"] = kind
        if kind == "signup":
            lines[0].pop("amount", None)
        else:
            lines[0]["amount"] = 10.0
    count = {}
    for e in lines:
        if e["type"] == kind:
            v = e["user"].get(field, "unknown")
            count[v] = count.get(v, 0) + 1
    n = sum(count.values())
    text = "\n".join(json.dumps(e) for e in lines)

    def check(run, report):
        f = _file(run, out)
        if not f:
            return False, f"no {out} saved"
        try:
            got = json.loads(f.read_text())
        except ValueError:
            return False, f"{out} is not JSON"
        ok = got == count and _says(B._body(report), n, 0.1)
        return ok, f"{out} {str(got)[:80]} against {count}; {n} events in the answer: {ok}"
    return ("hard: tables", "JSON lines read and counted by a nested field", _tab.given(name, text,
            f"The file holds one JSON object a line. Save a file {out}: one JSON object that maps each value of user.{field} among the "
            f"events of type \"{kind}\" to how many of those events have it (an event whose user has no {field} counts under \"unknown\"; "
            f"values with no such event are left out). Then tell me how many events of type \"{kind}\" there are."), check)


def jsonl(task):
    m = re.search(r"Here is the file (\S+):\n.+Save a file (\S+): one JSON object that maps each value of user\.(\w+) among the "
                  r"events of type \"(\w+)\"", task, re.S)
    if not m:
        return None
    return _fill('''import json

count = {}
for line in open(__NAME__):
    if line.strip():
        event = json.loads(line)
        if event["type"] == __TYPE__:
            value = event["user"].get(__FIELD__, "unknown")
            count[value] = count.get(value, 0) + 1
with open(__OUT__, "w") as f:
    json.dump(count, f)
print(__OUT__, "saved")
print("events:", sum(count.values()))
''', name=m.group(1), out=m.group(2), field=m.group(3), type=m.group(4))


make = h_tab_jsonl
lesson = jsonl
