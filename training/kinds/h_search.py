"""The kind h_search: a search for a number with given properties (hard: search).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import _fill, _says

KIND = "h_search"
FAMILY = "hard: search"
HARD = True
ORDER = 110
LESSON_ORDER = 220
LEVELED = True


def h_search(r):
    kind = r.choice(["digits", "palins", "nth", "change"])
    lv = getattr(r, "level", 0)  # harder: the same search over a larger range
    if kind == "digits":
        n, d, s = r.randrange(1000, 90000) * 10 ** min(lv, 3), r.choice([7, 11, 13, 17]), r.randrange(12, 26)
        x = next(i for i in range(n + 1, 10**11) if i % d == 0 and sum(map(int, str(i))) == s)
        return ("hard: search", "a number with given properties", f"Find the smallest whole number greater than {n} that is divisible by {d} and "
                f"whose digits add up to {s}.", lambda run, report: (_says(B._body(report), x, 0.1), f"wants {x}"))
    if kind == "palins":
        a, k = r.randrange(100, 5000), r.choice([3, 7, 11, 13])
        b = a + r.randrange(20000, 90000) * 4 ** min(lv, 3)
        x = sum(1 for i in range(a, b + 1) if str(i) == str(i)[::-1] and i % k == 0)
        return ("hard: search", "a number with given properties", f"How many whole numbers from {a} to {b} (both included) read the same "
                f"backwards as forwards and are divisible by {k}?", lambda run, report: (_says(B._body(report), x, 0.1), f"wants {x}"))
    if kind == "nth":
        n = r.randrange(300, 3000) * (1 + lv)
        ps, i = [], 1
        while len(ps) < n:
            i += 1
            if all(i % p for p in ps if p * p <= i):
                ps.append(i)
        x, tot = ps[-1], sum(map(int, str(ps[-1])))
        return ("hard: search", "a number with given properties", f"What is prime number {n} (counting 2 as the first), and what do its digits add up to?",
                lambda run, report: (_says(B._body(report), x, 0.1) and _says(B._body(report), tot, 0.1), f"wants {x} and {tot}"))
    coins, amount = sorted(r.sample([1, 2, 5, 10, 20, 25, 50], 4)), r.randrange(60, 300) * (1 + lv)
    if 1 not in coins:
        coins[0] = 1
    ways = [1] + [0] * amount
    for c in coins:
        for v in range(c, amount + 1):
            ways[v] += ways[v - c]
    x = ways[amount]
    return ("hard: search", "a number with given properties", f"In how many different ways can {amount} cents be paid with coins of {', '.join(map(str, coins))} "
            "cents (any number of each, order does not matter)?", lambda run, report: (_says(B._body(report), x, 0.1), f"wants {x}"))


def search(task):
    m = re.search(r"smallest whole number greater than (\d+) that is divisible by (\d+) and whose digits add up to (\d+)", task)
    if m:
        return _fill('''n, d, total = __N__, __D__, __T__
x = (n // d + 1) * d  # the first multiple of d above n; then every next one
while sum(int(c) for c in str(x)) != total:
    x += d
print(x)
''', n=int(m.group(1)), d=int(m.group(2)), t=int(m.group(3)))
    m = re.search(r"from (\d+) to (\d+) \(both included\) read the same backwards as forwards and are divisible by (\d+)", task)
    if m:
        return _fill('''a, b, k = __A__, __B__, __K__
print(sum(1 for i in range(a, b + 1) if i % k == 0 and str(i) == str(i)[::-1]))
''', a=int(m.group(1)), b=int(m.group(2)), k=int(m.group(3)))
    m = re.search(r"What is prime number (\d+) \(counting 2 as the first\)", task)
    if m:
        return _fill('''n = __N__
size = 1000
while True:  # a sieve, larger until it holds n primes
    sieve = [True] * size
    sieve[0] = sieve[1] = False
    for i in range(2, int(size ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = [False] * len(sieve[i * i::i])
    primes = [i for i, p in enumerate(sieve) if p]
    if len(primes) >= n:
        break
    size *= 2
p = primes[n - 1]
print("prime:", p)
print("digit sum:", sum(int(c) for c in str(p)))
''', n=int(m.group(1)))
    m = re.search(r"In how many different ways can (\d+) cents be paid with coins of ([\d, ]+) cents", task)
    if m:
        return _fill('''amount, coins = __AMOUNT__, __COINS__
ways = [1] + [0] * amount  # ways[v]: how many ways to pay v with the coins seen so far
for c in coins:
    for v in range(c, amount + 1):
        ways[v] += ways[v - c]
print(ways[amount])
''', amount=int(m.group(1)), coins=[int(c) for c in m.group(2).split(",")])
    return None


make = h_search
lesson = search
