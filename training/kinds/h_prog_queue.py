"""The kind h_prog_queue: a desk that serves waiting customers by priority, as the task describes it (who goes first,
who gives up waiting), two functions put to hidden tests (programs).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed. It is
held out: never practised or taught. `solution` writes a right program for a task of it, used only by the tests
(tests/test_k2c.py) to prove the check passes a right module and fails a wrong one.
"""
import heapq
import random
import re

from training.kinds._common import HARD_NAMES, _fill
from training.kinds._programs import module_check, program

KIND = "h_prog_queue"
FAMILY = "programs"
HARD = True
ORDER = 560
HELD_OUT = True

FIRST = {"low": "the lowest priority number goes first", "high": "the highest priority number goes first"}


def _serve(customers, first, patience):
    """[[name, start, end]] of those served and the sorted names of those who left."""
    sign = 1 if first == "low" else -1
    todo = sorted(customers, key=lambda c: (c[1], c[0]))
    t, i, wait, served, left = 0, 0, [], [], []
    while i < len(todo) or wait:
        if not wait and t < todo[i][1]:
            t = todo[i][1]
        while i < len(todo) and todo[i][1] <= t:
            name, arr, pri, dur = todo[i]
            heapq.heappush(wait, (sign * pri, arr, name, dur))
            i += 1
        keep = []
        for w in wait:
            (left if t - w[1] > patience else keep).append(w)
        wait = keep
        heapq.heapify(wait)
        if not wait:
            continue
        _, arr, name, dur = heapq.heappop(wait)
        served.append([name, t, t + dur])
        t += dur
    return served, sorted(w[2] for w in left)


def _customers(r, n=None):
    names = r.sample(HARD_NAMES, n or r.randrange(1, 9))
    return [[nm, r.randrange(0, 30), r.randrange(1, 6), r.randrange(1, 9)] for nm in names]


def h_prog_queue(r):
    first, patience = r.choice(sorted(FIRST)), r.randrange(4, 15)
    ask = _customers(r, r.randrange(4, 8))
    served, left = _serve(ask, first, patience)
    want = [[s[0] for s in served], left]
    seed = r.random()

    def draw():
        h = random.Random(f"hidden:{seed}")
        steps = []
        for _ in range(30):
            cs = _customers(h)
            s, lf = _serve(cs, first, patience)
            steps += [["serve", [cs], s], ["left", [cs], lf]]
        steps += [["serve", [[]], []], ["left", [[]], []]]
        return [{"new": None, "steps": steps}]
    return (FAMILY, "a queue served by priority, with hidden tests",
            "Write a Python module and save it as desk.py for one desk that serves customers one at a time. A customer is a list "
            "[name, arrival, priority, duration] of whole minutes; the list of customers may be in any order. Whenever the desk is "
            f"free it takes one of the customers who have arrived and are waiting: {FIRST[first]}, then the one who arrived first, "
            "then the name first in alphabetical order. It serves that customer for the duration without a break. When nobody is "
            "waiting it waits for the next arrival. A customer arriving at the very minute the desk becomes free is waiting by then. "
            f"A customer still waiting when more than {patience} minutes have passed since they arrived leaves without being served "
            f"(one who has waited exactly {patience} minutes can still be taken). The module has two functions. 1) serve(customers) "
            "returns the list [name, start, end] of every customer served, in the order they are served. 2) left(customers) returns "
            "the names of those who left, in alphabetical order. Test both yourself before you finish. Then tell me, on two lines, "
            f"the names in the order they are served and left(customers) for these customers: {ask!r}.", module_check("desk", draw, want))


SOURCE = '''import heapq

FIRST = __SIGN__  # 1: the lowest priority number first; -1: the highest
PATIENCE = __PATIENCE__


def _run(customers):
    todo = sorted(customers, key=lambda c: (c[1], c[0]))
    t, i, waiting, served, gone = 0, 0, [], [], []
    while i < len(todo) or waiting:
        if not waiting and t < todo[i][1]:
            t = todo[i][1]
        while i < len(todo) and todo[i][1] <= t:
            name, arrival, priority, duration = todo[i]
            heapq.heappush(waiting, (FIRST * priority, arrival, name, duration))
            i += 1
        gone += [w[2] for w in waiting if t - w[1] > PATIENCE]
        waiting = [w for w in waiting if t - w[1] <= PATIENCE]
        heapq.heapify(waiting)
        if waiting:
            _, arrival, name, duration = heapq.heappop(waiting)
            served.append([name, t, t + duration])
            t += duration
    return served, sorted(gone)


def serve(customers):
    return _run(customers)[0]


def left(customers):
    return _run(customers)[1]'''


def solution(task):
    m = re.search(r"free it takes .*?: the (lowest|highest) priority.*?more than (\d+) minutes.*?for these customers: (\[.*\])\.\s*$", task, re.S)
    if not m or "desk.py" not in task:
        return None
    tests = ["assert serve([]) == [] and serve([['a', 3, 1, 2]]) == [['a', 3, 5]]"]
    prints = [f"cs = {m.group(3)}", "print([s[0] for s in serve(cs)])", "print(left(cs))"]
    return program("desk", _fill(SOURCE, sign=1 if m.group(1) == "lowest" else -1, patience=int(m.group(2))), tests, prints)


make = h_prog_queue
lesson = None
