"""The kind h_prog_schedule: tasks put in an order that keeps their dependencies, ties broken by the task's own rule,
a cycle refused; two functions put to hidden tests (programs).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import random
import re

from training.kinds._programs import module_check, program, raises

KIND = "h_prog_schedule"
FAMILY = "programs"
HARD = True
ORDER = 540

JOBS = ["build", "test", "lint", "pack", "ship", "docs", "fetch", "clean", "sign", "deploy", "bench", "audit", "tag", "mail"]
TIES = {"alpha": ("the one whose name comes first in alphabetical order", "min(ready)"),
        "omega": ("the one whose name comes last in alphabetical order", "max(ready)"),
        "short": ("the one with the shortest name, and of names as long the one first in alphabetical order", "min(ready, key=lambda t: (len(t), t))"),
        "given": ("the one that comes first in the dict as it was given", "next(t for t in tasks if t in ready)")}


def _key(tie, tasks):
    pos = {t: i for i, t in enumerate(tasks)}
    return {"alpha": lambda t: t, "omega": lambda t: tuple(-ord(c) for c in t) + (1,), "short": lambda t: (len(t), t),
            "given": lambda t: pos[t]}[tie]


def _order(tie, tasks):
    done, out, key = set(), [], _key(tie, tasks)
    while len(out) < len(tasks):
        ready = [t for t in tasks if t not in done and all(d in done for d in tasks[t])]
        if not ready:
            raise ValueError("a cycle")
        t = min(ready, key=key)
        out.append(t)
        done.add(t)
    return out


def _levels(tasks):
    out = {}
    for t in _order("alpha", tasks):
        out[t] = 1 + max((out[d] for d in tasks[t]), default=-1)
    return out


def _safe(f, *a):
    try:
        return f(*a)
    except ValueError:
        return raises()


def _tasks(r, cycle=False):
    names = r.sample(JOBS, r.randrange(3, 9))
    rank = {n: i for i, n in enumerate(r.sample(names, len(names)))}  # dependencies go to tasks earlier in this order
    tasks = {n: sorted(d for d in names if rank[d] < rank[n] and r.random() < 0.3) for n in names}
    if cycle and len(names) >= 2:
        a, b = sorted(names, key=rank.get)[:2]
        tasks[a] = sorted(set(tasks[a]) | {b})
        if a not in tasks[b]:
            tasks[b] = sorted(set(tasks[b]) | {a})
    return tasks


def h_prog_schedule(r):
    tie = r.choice(sorted(TIES))
    ask = _tasks(r)
    want = _order(tie, ask)
    seed = r.random()

    def draw():
        h = random.Random(f"hidden:{seed}")
        steps = []
        for i in range(30):
            ts = _tasks(h, cycle=i % 5 == 4)
            steps.append(["order", [ts], _safe(_order, tie, ts)])
            steps.append(["levels", [ts], _safe(_levels, ts)])
        steps.append(["order", [{}], []])
        return [{"new": None, "steps": steps}]
    return (FAMILY, "an order of tasks by their dependencies, with hidden tests",
            "Write a Python module and save it as schedule.py. A plan is a dict from a task's name to the list of the tasks it "
            "depends on (every one of them is a key of the dict too). The module has two functions. 1) order(tasks) returns the "
            "list of all the task names in the order they are done: a task only after every task it depends on. When several "
            f"tasks could be done next, the one done is {TIES[tie][0]}. 2) levels(tasks) returns a dict from each task's name to "
            "its level: 0 for a task that depends on nothing, else 1 more than the highest level of the tasks it depends on. "
            "When the dependencies go round in a circle, both raise ValueError. Test both yourself before you finish. Then tell me "
            f"the value of order({ask!r}).", module_check("schedule", draw, [want]))


SOURCE = """def order(t):
    d = []
    while len(d) < len(t):
        r = [k for k in t if k not in d and all(x in d for x in t[k])]
        if not r:
            raise ValueError
        d.append(__NEXT__)
    return d


def levels(t):
    o = {}
    for k in order(t):
        o[k] = 1 + max([o[x] for x in t[k]], default=-1)
    return o"""
# the task done next of those ready (r, in the order of the dict), for each rule of TIES
PICK = {"alpha": "min(r)", "omega": "max(r)", "short": "min(r, key=lambda k: (len(k), k))", "given": "r[0]"}


def schedule(task):
    m = re.search(r"the one done is (.+?)\. 2\).*?the value of order\((\{.*\})\)\.\s*$", task, re.S)
    if not m or "schedule.py" not in task:
        return None
    tie = next((k for k, (said, _) in TIES.items() if said == m.group(1)), None)
    if tie is None:
        return None
    return program("schedule", SOURCE.replace("__NEXT__", PICK[tie]), ["assert levels({'a': [], 'b': ['a']}) == {'a': 0, 'b': 1}"],
                   [f"print(order({m.group(2)}))"])


make = h_prog_schedule
lesson = schedule
