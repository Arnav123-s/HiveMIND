"""The kind h_sim: a simulation followed step by step (a robot, an account) (hard: simulation).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
it has no lesson: the hive is never shown it done.
"""
import re

from training import hive_bench as B
from training.kinds._common import _nums, _says

KIND = "h_sim"
FAMILY = "hard: simulation"
HARD = True
ORDER = 120
HELD_OUT = True


def h_sim(r):
    if r.random() < 0.5:
        prog = "".join(r.choice("FFFLR") + (str(r.randrange(2, 9)) if r.random() < 0.4 else "") for _ in range(r.randrange(14, 24)))
        x = y = 0
        dx, dy = 0, 1
        for c, n in re.findall(r"([FLR])(\d*)", prog):
            for _ in range(int(n or 1)):
                if c == "F":
                    x, y = x + dx, y + dy
                elif c == "L":
                    dx, dy = -dy, dx
                else:
                    dx, dy = dy, -dx
        facing = {(0, 1): "north", (1, 0): "east", (0, -1): "south", (-1, 0): "west"}[(dx, dy)]

        def check(run, report):
            body = B._body(report)
            ok = facing in body.lower() and (x in [int(v) for v in _nums(body)]) and (y in [int(v) for v in _nums(body)]) and _says(body, abs(x) + abs(y), 0.1)
            return ok, f"ends at ({x}, {y}) facing {facing}, {abs(x) + abs(y)} steps from the start; in the answer: {ok}"
        return ("hard: simulation", "a simulation followed step by step", "A robot stands at x=0, y=0 on a grid and faces north (north is y+1, east "
                f"is x+1). It follows the program {prog} where F is one step forward, L a quarter turn left, R a quarter turn right, and a "
                "number after a letter repeats that letter so many times (F3 is three steps, L2 is two left turns). Where does it end, which "
                "way does it face, and how many grid steps is that from the start (|x| + |y|)? Answer in four lines: 'x: ', 'y: ', "
                "'facing: ', 'distance: '.", check)
    bal, rate = r.randrange(200, 2000), r.choice([1, 2, 3])
    moves = [(r.choice(["deposit", "withdraw", "withdraw"]), r.randrange(20, 900)) for _ in range(r.randrange(9, 14))]
    b, refused = bal, 0
    for i, (kind, amt) in enumerate(moves, 1):
        if kind == "deposit":
            b += amt
        elif amt > b:
            refused += 1
        else:
            b -= amt
        if i % 4 == 0:
            b = round(b * (1 + rate / 100), 2)
    b = round(b, 2)

    def check(run, report):
        body = B._body(report)
        ok = _says(body, b, 0.011) and _says(body, refused, 0.1)
        return ok, f"ends with {b}, {refused} refused; in the answer: {ok}"
    return ("hard: simulation", "a simulation followed step by step", f"An account starts with {bal} dollars. These movements happen in order: "
            + "; ".join(f"{k} {a}" for k, a in moves) + f". A withdrawal larger than the balance is refused and changes nothing. After every "
            f"fourth movement (refused ones count as movements) {rate}% interest is added to the balance, rounded to cents. What is the final "
            "balance, and how many withdrawals were refused? Answer in two lines: 'balance: ' and 'refused: '.", check)


make = h_sim
lesson = None
