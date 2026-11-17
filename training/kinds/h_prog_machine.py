"""The kind h_prog_machine: a state machine from a table the task gives, three functions put to hidden tests
(programs).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import random
import re

from training.kinds._common import _fill
from training.kinds._programs import module_check, program, raises

KIND = "h_prog_machine"
FAMILY = "programs"
HARD = True
ORDER = 510

STATES = ["idle", "ready", "running", "paused", "stopped", "broken", "waiting", "done"]
EVENTS = ["start", "stop", "pause", "resume", "reset", "fail", "tick"]
OTHERWISE = {"stay": "the machine stays in the state it is in",
             "fail": "step raises KeyError (and so do run and visits)"}


def _step(table, rule, sink, s, e):
    if (s, e) in table:
        return table[(s, e)]
    if rule == "stay":
        return s
    if rule == "sink":
        return sink
    raise KeyError((s, e))


def _walk(table, rule, sink, start, events):
    s, seen = start, [start]
    for e in events:
        s = _step(table, rule, sink, s, e)
        seen.append(s)
    return seen


def _safe(f, *a):
    try:
        return f(*a)
    except KeyError:
        return raises("KeyError")


def _along(r, table, events, start, n):
    """n events the table has for the states they meet (every state has one at least)."""
    out, s = [], start
    for _ in range(n):
        out.append(r.choice([e for e in events if (s, e) in table]))
        s = table[(s, out[-1])]
    return out


def h_prog_machine(r):
    states = r.sample(STATES, r.randrange(3, 6))
    events = r.sample(EVENTS, r.randrange(3, 5))
    start = states[0]
    table = {(s, e): s if r.random() < 0.15 else r.choice([t for t in states if t != s])
             for s in states for e in r.sample(events, r.randrange(1, len(events)))}
    rule = r.choice(["stay", "sink", "fail"])
    sink = r.choice(states)
    otherwise = f"the machine goes to {sink}" if rule == "sink" else OTHERWISE[rule]
    ask = [r.choice(events) for _ in range(r.randrange(4, 8))]
    if rule == "fail":  # the events asked about never raise: the answer is a state
        ask = _along(r, table, events, start, r.randrange(4, 8))
    want = _walk(table, rule, sink, start, ask)[-1]
    seed = r.random()

    def draw():
        h = random.Random(f"hidden:{seed}")
        steps = [["step", [s, e], _safe(_step, table, rule, sink, s, e)] for s in states for e in events]
        for _ in range(30):
            evs = _along(h, table, events, start, h.randrange(0, 9)) if h.random() < 0.5 else [h.choice(events) for _ in range(h.randrange(0, 9))]
            st = h.choice(states)
            steps.append(["run", [evs], _safe(lambda: _walk(table, rule, sink, start, evs)[-1])])
            steps.append(["visits", [evs, st], _safe(lambda: _walk(table, rule, sink, start, evs).count(st))])
        return [{"new": None, "steps": steps}]
    lines = "\n".join(f"{s}, {e} -> {t}" for (s, e), t in table.items())
    return (FAMILY, "a state machine from a table, with hidden tests",
            f"Write a Python module and save it as machine.py for a machine with the states {', '.join(states)} and the events "
            f"{', '.join(events)}. It starts in {start}. This table says where an event takes it (state, event -> new state):\n"
            f"{lines}\n"
            f"For a state and an event the table does not have, {otherwise}. The module has three functions. 1) step(state, event) "
            f"returns the state the event takes the machine to from that state. 2) run(events) takes a list of events, starts in "
            f"{start}, and returns the state it ends in. 3) visits(events, state) returns how many times the machine is in that "
            f"state while it runs those events, the start counted (visits([], '{start}') is 1). Test the functions yourself before "
            f"you finish. Then tell me the value of run({ask!r}).", module_check("machine", draw, [want]))


SOURCE = '''START = __START__
TABLE = __TABLE__
OTHERWISE = __RULE__


def step(state, event):
    if (state, event) in TABLE:
        return TABLE[(state, event)]
    if OTHERWISE == "stay":
        return state
    if OTHERWISE == "fail":
        raise KeyError((state, event))
    return OTHERWISE


def path(events):
    states = [START]
    for event in events:
        states.append(step(states[-1], event))
    return states


def run(events):
    return path(events)[-1]


def visits(events, state):
    return path(events).count(state)'''


def machine(task):
    m = re.search(r"It starts in (\w+)\. This table.*?:\n(.+?)\nFor a state and an event the table does not have, (.+?)\. The module.*?"
                  r"the value of run\((\[.*?\])\)\.", task, re.S)
    if not m or "machine.py" not in task:
        return None
    start, rows, otherwise, ask = m.groups()
    table = {(s, e): t for s, e, t in re.findall(r"^(\w+), (\w+) -> (\w+)$", rows, re.M)}
    sink = re.match(r"the machine goes to (\w+)$", otherwise)
    rule = sink.group(1) if sink else "fail" if "KeyError" in otherwise else "stay"
    tests = [f"assert visits([], {start!r}) == 1", f"assert run([]) == {start!r}"]
    return program("machine", _fill(SOURCE, start=start, table=table, rule=rule), tests, [f"print(run({ask}))"])


make = h_prog_machine
lesson = machine
