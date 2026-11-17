"""The kind h_prog_bank: a class Account whose rules (a fee, an overdraft, a number of withdrawals) the task gives,
put to hidden tests (programs).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import random
import re

from training.kinds._common import _fill
from training.kinds._programs import module_check, program, raises

KIND = "h_prog_bank"
FAMILY = "programs"
HARD = True
ORDER = 500


class _Account:
    """The reference: what the task's rules say, with its numbers."""
    def __init__(self, fee, limit, most, balance=0):
        self.fee, self.limit, self.most, self.b, self.n = fee, limit, most, balance, 0

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError
        self.b += amount
        return self.b

    def withdraw(self, amount):
        if amount <= 0 or self.n >= self.most or self.b - amount - self.fee < -self.limit:
            raise ValueError
        self.b -= amount + self.fee
        self.n += 1
        return self.b

    def balance(self):
        return self.b


def _call(acc, op, v):
    try:
        return getattr(acc, op)(v)
    except ValueError:
        return raises()


def _moves(r, n):
    return [(r.choice(["deposit", "withdraw", "withdraw"]), r.choice([0, -5, r.randrange(1, 60), r.randrange(10, 300), r.randrange(10, 300)])) for _ in range(n)]


def h_prog_bank(r):
    fee, limit, most = r.choice([0, 1, 2, 3, 5]), r.choice([0, 25, 50, 100, 200]), r.randrange(2, 6)
    start = r.randrange(0, 300)
    moves = _moves(r, r.randrange(4, 8))
    acc = _Account(fee, limit, most, start)
    for op, v in moves:
        _call(acc, op, v)
    want = acc.balance()
    seed = r.random()

    def draw():
        h = random.Random(f"hidden:{seed}")
        out = []
        for _ in range(30):
            b = h.randrange(0, 300)
            ref, steps = _Account(fee, limit, most, b), [["balance", [], b]]
            for op, v in _moves(h, h.randrange(3, 12)):
                steps.append([op, [v], _call(ref, op, v)])
            steps.append(["balance", [], ref.balance()])
            out.append({"new": ["Account", [b]], "steps": steps})
        for _ in range(5):  # a rich account: only the number of withdrawals refuses
            b = h.randrange(5000, 9000)
            ref = _Account(fee, limit, most, b)
            steps = [["withdraw", [v], _call(ref, "withdraw", v)] for v in (h.randrange(1, 40) for _ in range(most + 2))]
            out.append({"new": ["Account", [b]], "steps": steps + [["balance", [], ref.balance()]]})
        out.append({"new": ["Account", []], "steps": [["balance", [], 0], ["deposit", [7], 7]]})
        return out
    told = ", ".join(f"{op}({v})" for op, v in moves)
    return (FAMILY, "a class with rules, with hidden tests",
            "Write a Python module and save it as bank.py. It holds a class Account. Account(balance=0) opens an account with that "
            "many dollars (whole numbers only). It has three methods. 1) deposit(amount) adds the amount and returns the new balance; "
            "an amount that is not above 0 raises ValueError. 2) withdraw(amount) takes the amount and a fee of "
            f"{fee} dollars for every withdrawal and returns the new balance; it raises ValueError and changes nothing when the "
            f"amount is not above 0, when the account has already made {most} withdrawals, or when the balance would fall below "
            f"-{limit} (an overdraft of {limit} dollars is allowed). A refused withdrawal does not count. 3) balance() returns the "
            f"balance. Test the class yourself before you finish. Then tell me the balance of Account({start}) after {told}, "
            "in that order, each that raises ValueError skipped.", module_check("bank", draw, [want]))


SOURCE = '''FEE, OVERDRAFT, MOST = __FEE__, __LIMIT__, __MOST__


class Account:
    def __init__(self, balance=0):
        self.money = balance
        self.withdrawals = 0

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("the amount must be above 0")
        self.money += amount
        return self.money

    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("the amount must be above 0")
        if self.withdrawals >= MOST:
            raise ValueError("no withdrawals left")
        if self.money - amount - FEE < -OVERDRAFT:
            raise ValueError("over the overdraft")
        self.money -= amount + FEE
        self.withdrawals += 1
        return self.money

    def balance(self):
        return self.money'''


def bank(task):
    m = re.search(r"a fee of (\d+) dollars.*?already made (\d+) withdrawals.*?below -(\d+).*?the balance of Account\((\d+)\) after (.+?), in that order", task, re.S)
    if not m or "save it as bank.py" not in task:
        return None
    fee, most, limit, start = map(int, m.groups()[:4])
    moves = [(op, int(v)) for op, v in re.findall(r"(deposit|withdraw)\((-?\d+)\)", m.group(5))]
    tests = ["a = Account(10)", "assert a.deposit(5) == 15", "try:\n        a.deposit(0)\n        raise AssertionError('0 taken')\n    except ValueError:\n        pass",
             f"a = Account({start})", f"for op, v in {moves!r}:\n        try:\n            getattr(a, op)(v)\n        except ValueError:\n            pass"]
    return program("bank", _fill(SOURCE, fee=fee, limit=limit, most=most), tests, ["print(a.balance())"])


make = h_prog_bank
lesson = bank
