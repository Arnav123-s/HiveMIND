"""The kind h_log: a log given in the task, read and counted into a file (hard: files).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import datetime
import json
import re

from training import hive_bench as B
from training.kinds._common import _file, _says

KIND = "h_log"
FAMILY = "hard: files"
HARD = True
ORDER = 100
LESSON_ORDER = 210
LEVELED = True
GIVEN_FILE = True


SERVICES = ["auth", "billing", "search", "mail", "storage"]


def h_log(r):
    day = datetime.date(2026, r.randrange(1, 13), r.randrange(1, 28))
    lines = []
    for _ in range(r.randrange(16, 24) + 10 * getattr(r, "level", 0)):  # harder: a longer log
        t = datetime.time(r.randrange(8, 13), r.randrange(60), r.randrange(60))
        lines.append((t, r.choice(["ERROR", "ERROR", "WARN", "INFO"]), r.choice(SERVICES[:4]), r.choice(["timeout", "retry", "started", "disk full", "bad token"])))
    lines.sort()
    count = {}
    for _, lv, sv, _ in lines:
        if lv == "ERROR":
            count[sv] = count.get(sv, 0) + 1
    hours = {}
    for t, lv, _, _ in lines:
        if lv == "ERROR":
            hours[t.hour] = hours.get(t.hour, 0) + 1
    def tie():  # no ERROR line at all, or two hours share the top: no single answer, so one more ERROR line is written
        v = sorted(hours.values(), reverse=True)
        return not v or (len(v) > 1 and v[0] == v[1])
    while tie():
        t = datetime.time(max(hours, key=hours.get) if hours else 9, r.randrange(60), r.randrange(60))
        lines.append((t, "ERROR", SERVICES[0], "timeout"))
        count[SERVICES[0]] = count.get(SERVICES[0], 0) + 1
        hours[t.hour] = hours.get(t.hour, 0) + 1
        lines.sort()
    hour = max(hours, key=hours.get)
    text = "\n".join(f"{day} {t.isoformat()} {lv} {sv}: {msg}" for t, lv, sv, msg in lines)

    def check(run, report):
        f = _file(run, "errors.json")
        if not f:
            return False, "no errors.json saved"
        try:
            got = json.loads(f.read_text())
        except ValueError:
            return False, "errors.json is not JSON"
        ok = got == count and _says(B._body(report), hour, 0.1)
        return ok, f"errors.json {str(got)[:80]} against {count}; the hour {hour} in the answer: {ok}"
    return ("hard: files", "a log read and counted into a file", "Here is a log:\n" + text + "\nSave a file errors.json: one JSON object that maps "
            "each service that has ERROR lines to the number of its ERROR lines (services without errors are left out). Then tell me in which "
            "hour of the day (0 to 23) the most ERROR lines were written.", check)


LOG_COUNT = '''errors, hours = {}, {}
for line in __LINES__:
    day, clock, level, rest = line.split(" ", 3)
    if level == "ERROR":
        service = rest.split(":")[0]
        errors[service] = errors.get(service, 0) + 1
        hours[int(clock[:2])] = hours.get(int(clock[:2]), 0) + 1
with open("errors.json", "w") as f:
    json.dump(errors, f)
print("errors.json saved:", errors)
print("hour:", max(hours, key=hours.get))
'''


def log(task, copy=False):
    """The log is data the task gives: the runtime saves it as a file (team/tools/sandbox.give), so the program reads
    log.txt and stays short whatever the log's length. (T4: the program that copied the log in was about 1300 pieces,
    left out of training on every runner that trains in 32 bits.) copy: the log copied into the program instead, for a
    task of several parts whose first block of data is another part's, which log.txt would then hold."""
    m = re.search(r"Here is a log:\n(.*?)\nSave a file errors\.json", task, re.S)
    if not m:
        return None
    if copy:
        return 'import json\n\nlog = """' + m.group(1) + '"""\n' + LOG_COUNT.replace("__LINES__", "log.splitlines()")
    return "import json\n\n" + LOG_COUNT.replace("__LINES__", 'open("log.txt")')


make = h_log
lesson = log
