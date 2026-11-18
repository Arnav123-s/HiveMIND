"""The kind h_prog_calc: a parser for a tiny language of arithmetic with an operator of the task's own (its meaning,
how tightly it binds, which way it groups), put to hidden tests (programs).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import random
import re

from training.kinds._common import _fill
from training.kinds._programs import module_check, program

KIND = "h_prog_calc"
FAMILY = "programs"
HARD = True
ORDER = 530

MEANS = {"max": ("the larger of a and b", "max(a, b)"),
         "min": ("the smaller of a and b", "min(a, b)"),
         "monus": ("a minus b, or 0 when that is below 0", "max(a - b, 0)"),
         "mean": ("(a + b) divided by 2, rounded down", "(a + b) // 2")}
BINDS = {6: "more tightly than *", 3: "more tightly than + and -, less tightly than *", 1: "less tightly than + and -"}


def _calc(sym, mean, level, right):
    prec = {"+": 2, "-": 2, "*": 4, sym: level}
    do = {"+": lambda a, b: a + b, "-": lambda a, b: a - b, "*": lambda a, b: a * b,
          sym: {"max": max, "min": min, "monus": lambda a, b: max(a - b, 0), "mean": lambda a, b: (a + b) // 2}[mean]}

    def tokens(text):
        return re.findall(r"\d+|[-+*()]|" + re.escape(sym), text)

    def expr(ts, i, least):
        if ts[i] == "(":
            left, i = expr(ts, i + 1, 0)
            i += 1
        else:
            left, i = int(ts[i]), i + 1
        while i < len(ts) and ts[i] in prec and prec[ts[i]] >= least:
            op = ts[i]
            right_, i = expr(ts, i + 1, prec[op] + (0 if op == sym and right else 1))
            left = do[op](left, right_)
        return left, i

    return tokens, lambda text: expr(tokens(text), 0, 0)[0]


def _expr(r, sym, depth=2):
    parts = []
    for _ in range(r.randrange(2, 5)):
        parts.append(f"({_expr(r, sym, depth - 1)})" if depth and r.random() < 0.25 else str(r.randrange(0, 21)))
        parts.append(r.choice(["+", "-", "*", sym, sym]))
    sp = r.choice(["", " "])
    return sp.join(parts[:-1])


def h_prog_calc(r):
    sym, mean, level, right = r.choice("#@&$"), r.choice(sorted(MEANS)), r.choice(sorted(BINDS)), r.random() < 0.5
    tokens, evaluate = _calc(sym, mean, level, right)
    ask = _expr(r, sym)
    want = evaluate(ask)
    seed = r.random()

    def draw():
        h = random.Random(f"hidden:{seed}")
        steps = []
        for _ in range(40):
            e = _expr(h, sym, h.randrange(0, 3))
            steps.append(["evaluate", [e], evaluate(e)])
            if h.random() < 0.3:
                steps.append(["tokens", [e], tokens(e)])
        return [{"new": None, "steps": steps}]
    return (FAMILY, "a parser for a tiny language, with hidden tests",
            "Write a Python module and save it as calc.py for a tiny language of arithmetic on whole numbers. An expression has "
            f"numbers (0 or more), the operators +, -, * and {sym}, round brackets, and maybe spaces. a {sym} b is {MEANS[mean][0]}. "
            f"* binds more tightly than + and -, as usual; {sym} binds {BINDS[level]}. +, - and * group from the left; {sym} groups from the "
            f"{'right' if right else 'left'} (a {sym} b {sym} c is {'a ' + sym + ' (b ' + sym + ' c)' if right else '(a ' + sym + ' b) ' + sym + ' c'}). "
            f"Brackets are worked out first. The module has two functions. 1) tokens(text) returns the list of the expression's "
            f"pieces as strings, spaces left out (tokens('12 *(3{sym}4)') is ['12', '*', '(', '3', '{sym}', '4', ')']). 2) evaluate(text) "
            f"returns the expression's value as an int. Test both yourself before you finish. Then tell me the value of "
            f"evaluate({ask!r}).", module_check("calc", draw, [want]))


SOURCE = """import re

P = {"+": 2, "-": 2, "*": 4, __SYM__: __LEVEL__}


def tokens(t):
    return re.findall(r"\\d+|\\S", t)


def evaluate(t, m=0):
    if type(t) == str:
        t = tokens(t)[::-1]
    x = t.pop()
    if x == "(":
        a = evaluate(t)
        t.pop()
    else:
        a = int(x)
    while t and P.get(t[-1], 0) > m:
        o = t.pop()
        b = evaluate(t, P[o]__RIGHT__)
        a = {"+": a + b, "-": a - b, "*": a * b}.get(o, __MEANS__)
    return a"""


def calc(task):
    m = re.search(r"the operators \+, -, \* and (\S), round.*? is (.+?)\. \* binds.*?binds (more tightly than \*|more tightly than \+ and -, less "
                  r"tightly than \*|less tightly than \+ and -)\..*?groups from the (right|left).*?the value of evaluate\((.+)\)\.\s*$", task, re.S)
    if not m or "calc.py" not in task:
        return None
    sym, means, binds, side, ask = m.groups()
    mean = next((code for said, code in MEANS.values() if said == means), None)
    level = next((lv for lv, said in BINDS.items() if said == binds), None)
    if mean is None or level is None:
        return None
    # the stack of pieces is read from its end; an operator takes on its right only what binds more tightly than it
    # (or as tightly, for the one that groups from the right)
    src = _fill(SOURCE, sym=sym, level=level).replace("__RIGHT__", f" - (o == {sym!r})" if side == "right" else "").replace("__MEANS__", mean)
    return program("calc", src, ["assert evaluate('(2+3)*4') == 20"], [f"print(evaluate({ask}))"])


make = h_prog_calc
lesson = calc
