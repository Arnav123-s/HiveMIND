"""The kind m_know: a thing to know (a capital, an element, a prime, a divisor, a rectangle) (knowledge).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import CAPITALS, _fill, _nums, every, says

KIND = "m_know"
FAMILY = "knowledge"
HARD = False
ORDER = 130
LESSON_ORDER = 120
COPIES = 2


ELEMENTS = {"sodium": ("Na", 11), "potassium": ("K", 19), "iron": ("Fe", 26), "gold": ("Au", 79), "silver": ("Ag", 47), "tungsten": ("W", 74),
            "lead": ("Pb", 82), "mercury": ("Hg", 80), "tin": ("Sn", 50), "copper": ("Cu", 29), "helium": ("He", 2), "neon": ("Ne", 10)}


def m_know(r):
    kind = r.choice(["capital", "element", "number", "gcd", "area"])
    if kind == "capital":
        c = r.choice(sorted(CAPITALS))
        want = CAPITALS[c]
        return "knowledge", "a thing to know", f"What is the capital of {c}?", B.has(any_of=(want, want.replace("í", "i")))
    if kind == "element":
        e = r.choice(sorted(ELEMENTS))
        sym, num = ELEMENTS[e]

        def check(run, report):
            body = B._body(report)
            ok = bool(re.search(rf"(?<![A-Za-z]){sym}(?![a-z])", body)) and num in [int(x) for x in _nums(body) if x == int(x)]
            return ok, f"symbol {sym} and atomic number {num} in the answer: {ok}"
        return "knowledge", "a thing to know", f"What are the chemical symbol and the atomic number of {e}?", check
    if kind == "number":
        n = r.choice([91, 97, 101, 111, 119, 127, 133, 143, 149, 151])
        prime = all(n % d for d in range(2, int(n ** 0.5) + 1))

        def check(run, report):
            low = B._body(report).lower()
            says_not = bool(re.search(r"\bnot (a )?prime|isn't (a )?prime|\bno\b|composite", low))
            return says_not != prime, f"{n} is {'prime' if prime else 'not prime'}; the answer says {'not prime' if says_not else 'prime'}"
        return "knowledge", "a thing to know", f"Is {n} a prime number? Answer yes or no, and if no, give a divisor.", check
    if kind == "gcd":
        import math
        g = r.choice([6, 8, 12, 14, 15, 18])
        a, b = g * r.choice([3, 5, 7, 11]), g * r.choice([4, 8, 13, 16])
        return "knowledge", "a thing to know", f"What is the greatest common divisor of {a} and {b}?", says(math.gcd(a, b), 0.1)
    w, h = r.randrange(3, 30), r.randrange(3, 30)
    return "knowledge", "a thing to know", f"A rectangle is {w} metres wide and {h} metres long. What are its area and its perimeter?", every(says(w * h, 0.1), says(2 * (w + h), 0.1))


def know(task):
    """What does not change and is known needs no source: it is written into the program and printed. (The talk test
    of 2026-11-15: asked for the capital of Australia, all three members fetched it from addresses they made up.)"""
    m = re.search(r"What is the capital of (.+?)\?", task)
    if m and m.group(1) in CAPITALS:
        return _fill('''# a capital city does not change and is known: no source is needed
capital = __CAPITAL__
print(capital)
''', capital=CAPITALS[m.group(1)])
    m = re.search(r"chemical symbol and the atomic number of (\w+)\?", task)
    if m and m.group(1) in ELEMENTS:
        sym, num = ELEMENTS[m.group(1)]
        return _fill('''# an element's symbol and number do not change and are known: no source is needed
print("symbol:", __SYM__)
print("atomic number:", __NUM__)
''', sym=sym, num=num)
    m = re.search(r"Is (\d+) a prime number\?", task)
    if m:
        return _fill('''n = __N__
divisor = next((d for d in range(2, int(n ** 0.5) + 1) if n % d == 0), None)
print("yes" if divisor is None else f"no, it is divisible by {divisor}")
''', n=int(m.group(1)))
    m = re.search(r"greatest common divisor of (\d+) and (\d+)", task)
    if m:
        return f"import math\n\nprint(math.gcd({int(m.group(1))}, {int(m.group(2))}))\n"
    m = re.search(r"A rectangle is (\d+) metres wide and (\d+) metres long", task)
    if m:
        return _fill('''width, length = __W__, __L__
print("area:", width * length, "square metres")
print("perimeter:", 2 * (width + length), "metres")
''', w=int(m.group(1)), l=int(m.group(2)))
    return None


make = m_know
lesson = know
