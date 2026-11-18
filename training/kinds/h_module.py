"""The kind h_module: a module of two functions, with hidden tests (hard: code).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

from training import hive_bench as B
from training.kinds._common import _file

KIND = "h_module"
FAMILY = "hard: code"
HARD = True
ORDER = 70
LESSON_ORDER = 200
COPIES = 2


def _roman(n):
    out = ""
    for v, s in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out, n = out + s, n - v
    return out


def _rle(s):
    out, i = "", 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out, i = out + f"{s[i]}{j - i}", j
    return out


def _merge(xs):
    out = []
    for a, b in sorted(map(tuple, xs)):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _base(n, b):
    d = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        out, n = d[n % b] + out, n // b
        if not n:
            return out


def _balanced(s):
    st, pair = [], {")": "(", "]": "[", "}": "{"}
    for c in s:
        if c in "([{":
            st.append(c)
        elif c in pair and (not st or st.pop() != pair[c]):
            return False
    return not st


def _caesar(t, k):
    sh = lambda c, a: chr((ord(c) - a + k) % 26 + a)  # noqa: E731
    return "".join(sh(c, 97) if c.islower() else sh(c, 65) if c.isupper() else c for c in t)


def _factors(n):
    out, d = [], 2
    while d * d <= n:
        while n % d == 0:
            out, n = out + [d], n // d
        d += 1
    return out + ([n] if n > 1 else [])


def _spiral(m):
    m, out = [list(x) for x in m], []
    while m:
        out += m.pop(0)
        m = [list(x) for x in zip(*m)][::-1]
    return out


def _dur(s):
    return sum(int(n) * {"h": 3600, "m": 60, "s": 1}[u] for n, u in re.findall(r"(\d+)([hms])", s))


def _fmt(n):
    h, m, s = n // 3600, n % 3600 // 60, n % 60
    return "".join(f"{v}{u}" for v, u in ((h, "h"), (m, "m"), (s, "s")) if v) or "0s"


def _words(r, n):
    return [r.choice(["river", "stone", "amber", "cloud", "ember", "field", "grain", "harbor", "island", "juniper"]) for _ in range(n)]


def _letters(r, n, abc="abc"):
    return "".join(r.choice(abc) * r.randrange(1, 4) for _ in range(n))


SPECS = {
    "roman": ("roman", [("to_roman", "to_roman(n) returns the Roman numeral of an integer from 1 to 3999 as a string (to_roman(1994) is 'MCMXCIV')",
                         _roman, lambda r: (r.randrange(1, 4000),)),
                        ("from_roman", "from_roman(s) returns the integer of a Roman numeral (from_roman('XLII') is 42)",
                         lambda s: next(i for i in range(1, 4000) if _roman(i) == s), lambda r: (_roman(r.randrange(1, 4000)),))]),
    "rle": ("rle", [("encode", "encode(s) returns the run-length encoding of a string of letters: each run as the letter followed by the "
                     "length of the run (encode('aaabcc') is 'a3b1c2')", _rle, lambda r: (_letters(r, r.randrange(1, 7)),)),
                    ("decode", "decode(s) reverses it (decode('a3b1c2') is 'aaabcc'; a run may be longer than 9)",
                     lambda s: "".join(c * int(n) for c, n in re.findall(r"([a-z])(\d+)", s)),
                     lambda r: ("".join(f"{c}{r.randrange(1, 15)}" for c in r.sample("abcdefg", r.randrange(1, 5))),))]),
    "intervals": ("intervals", [("merge", "merge(xs) takes a list of [start, end] pairs of integers in any order and returns the list of merged "
                                 "pairs, sorted by start; pairs that overlap or touch are merged (merge([[5, 8], [1, 3], [2, 4]]) is [[1, 4], [5, 8]]; "
                                 "[1, 2] and [2, 3] become [1, 3])",
                                 _merge, lambda r: ([sorted(r.sample(range(40), 2)) for _ in range(r.randrange(1, 7))],)),
                                ("covered", "covered(xs) returns how many integers lie inside at least one of the pairs, ends included "
                                 "(covered([[1, 3], [2, 4]]) is 4)", lambda xs: len({i for a, b in xs for i in range(a, b + 1)}),
                                 lambda r: ([sorted(r.sample(range(40), 2)) for _ in range(r.randrange(1, 7))],))]),
    "bases": ("bases", [("to_base", "to_base(n, b) returns the non-negative integer n written in base b (2 to 36) with the digits 0-9 and "
                         "a-z in lower case (to_base(255, 16) is 'ff')", _base, lambda r: (r.randrange(0, 100000), r.randrange(2, 37))),
                        ("from_base", "from_base(s, b) returns the integer of such a string (from_base('ff', 16) is 255)",
                         lambda s, b: int(s, b), lambda r: (_base(r.randrange(0, 100000), (b := r.randrange(2, 37))), b))]),
    "brackets": ("brackets", [("balanced", "balanced(s) returns True when every bracket of the kinds () [] {} in the string is closed in the "
                               "right order, other characters ignored (balanced('a(b[c]{d})') is True, balanced('(]') is False)", _balanced,
                               lambda r: ("".join(r.choice("()[]{}ab") for _ in range(r.randrange(0, 9))) if r.random() < 0.5 else
                                          "".join(r.choice(["()", "[]", "{}", "([])", "{a}", "(", "]"]) for _ in range(r.randrange(1, 5))),)),
                              ("depth", "depth(s) returns the deepest nesting of round brackets in a string whose round brackets are balanced "
                               "(depth('(a(b)(c(d)))') is 3, depth('abc') is 0)",
                               lambda s: max([0] + [s[:i + 1].count("(") - s[:i + 1].count(")") for i in range(len(s))]),
                               lambda r: ("".join(r.choice(["(a)", "((b))", "c", "(((d)))", "()", "(e(f))"]) for _ in range(r.randrange(1, 5))),))]),
    "cipher": ("cipher", [("shift", "shift(text, k) returns the text with every letter moved k places along the alphabet, wrapping round, "
                           "upper and lower case kept, everything else unchanged (shift('Hello, World!', 3) is 'Khoor, Zruog!')", _caesar,
                           lambda r: (" ".join(_words(r, 3)).title() + r.choice("!?."), r.randrange(1, 60))),
                          ("unshift", "unshift(text, k) reverses it", lambda t, k: _caesar(t, -k),
                           lambda r: (" ".join(_words(r, 3)).title() + r.choice("!?."), r.randrange(1, 60)))]),
    "factors": ("factors", [("prime_factors", "prime_factors(n) returns the prime factors of an integer above 1 as a list in rising order, "
                             "each as often as it divides (prime_factors(360) is [2, 2, 2, 3, 3, 5])", _factors, lambda r: (r.randrange(2, 200000),)),
                            ("divisors", "divisors(n) returns how many positive divisors n has (divisors(360) is 24)",
                             lambda n: sum(n % i == 0 for i in range(1, n + 1)), lambda r: (r.randrange(2, 20000),))]),
    "spiral": ("spiral", [("spiral", "spiral(m) takes a matrix as a list of rows and returns its values as one list, read clockwise from the "
                           "top left inwards (spiral([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) is [1, 2, 3, 6, 9, 8, 7, 4, 5])", _spiral,
                           lambda r: ([[r.randrange(100) for _ in range(w)] for _ in range(r.randrange(1, 5))] if (w := r.randrange(1, 5)) else [],)),
                          ("rotate", "rotate(m) returns the matrix turned a quarter clockwise (rotate([[1, 2], [3, 4]]) is [[3, 1], [4, 2]])",
                           lambda m: [list(x) for x in zip(*m[::-1])],
                           lambda r: ([[r.randrange(100) for _ in range(w)] for _ in range(r.randrange(1, 5))] if (w := r.randrange(1, 5)) else [],))]),
    "durations": ("durations", [("to_seconds", "to_seconds(s) returns the seconds of a duration written with the units h, m and s, any of "
                                 "them left out (to_seconds('1h30m15s') is 5415, to_seconds('45m') is 2700)", _dur,
                                 lambda r: (_fmt(r.randrange(1, 90000)),)),
                                ("to_text", "to_text(n) writes a number of seconds that way, leaving out units that are zero "
                                 "(to_text(5415) is '1h30m15s', to_text(3600) is '1h', to_text(0) is '0s')", _fmt, lambda r: (r.choice([0, 3600, 60, r.randrange(1, 90000)]),))]),
    "anagrams": ("anagrams", [("groups", "groups(words) takes a list of lower-case words and returns the groups of words that are anagrams of "
                               "each other: a list of lists, each group sorted, the groups sorted by their first word; a word with no anagram is a "
                               "group of one (groups(['tea', 'bat', 'eat', 'tab', 'sun']) is [['bat', 'tab'], ['eat', 'tea'], ['sun']])",
                               lambda ws: sorted(sorted(g) for g in {tuple(sorted(w)): [x for x in ws if sorted(x) == sorted(w)] for w in ws}.values()),
                               lambda r: (r.sample(["tea", "eat", "ate", "bat", "tab", "sun", "nus", "listen", "silent", "enlist", "stone", "notes", "onset", "arc", "car", "dog"], r.randrange(2, 9)),)),
                              ("is_anagram", "is_anagram(a, b) returns True when the two strings use the same letters as often, case and "
                               "spaces ignored (is_anagram('Dormitory', 'dirty room') is True)",
                               lambda a, b: sorted(a.replace(" ", "").lower()) == sorted(b.replace(" ", "").lower()),
                               lambda r: r.choice([("Dormitory", "dirty room"), ("Listen", "Silent"), ("apple", "papel"), ("apple", "apply"), ("a b", "ba"), ("abc", "abcc")]))]),
}


def _load(path):
    spec = importlib.util.spec_from_file_location(f"hive_exam_{abs(hash(str(path)))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hidden(path, fns, seed, n=25, timeout=20):
    """Run the hidden tests in a process of their own (a module that loops for ever must not hang the exam).
    Returns (ok, why). The tests are drawn here from a seed the task never showed."""
    import random
    import subprocess
    r = random.Random(f"hidden:{seed}")
    cases = [(name, args, ref(*args)) for name, _, ref, draw in fns for args in (draw(r) for _ in range(n))]
    prog = ("import importlib.util, json, sys\n"
            "spec = importlib.util.spec_from_file_location('m', sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "bad = []\n"
            "for name, args, want in json.loads(sys.stdin.read()):\n"
            "    try:\n        got = json.loads(json.dumps(getattr(m, name)(*args)))\n    except Exception as e:\n        got = f'{type(e).__name__}: {e}'\n"
            "    if got != want:\n        bad.append([name, args, want, got])\n"
            "print(json.dumps([len(bad), bad[:1]], default=str))\n")
    try:
        p = subprocess.run([sys.executable, "-I", "-c", prog, str(path)], input=json.dumps(cases), capture_output=True, text=True, timeout=timeout, cwd=str(Path(path).parent))
        bad, first = json.loads(p.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError, IndexError) as e:
        return False, f"the hidden tests could not run: {type(e).__name__}"
    return bad == 0, f"{len(cases) - bad} of {len(cases)} hidden tests pass" + (f"; first failure {str(first[0])[:160]}" if bad else "")


def h_module(r):
    key = r.choice(sorted(SPECS))
    mod, fns = SPECS[key]
    ask = [(name, draw(r)) for name, _, _, draw in fns]
    want = [ref(*args) for (name, _, ref, _), (_, args) in zip(fns, ask)]
    call = [f"{name}({', '.join(map(repr, args))})" for name, args in ask]
    seed = r.random()

    def check(run, report):
        f = _file(run, f"{mod}.py")
        if not f:
            return False, f"no {mod}.py saved"
        ok, why = _hidden(f, fns, seed)
        body = B._body(report)
        told = all(str(w) in body or repr(w) in body or json.dumps(w) in body for w in want)
        return ok and told, f"{why}; the values asked for ({want}) in the answer: {told}"
    return ("hard: code", "a module of two functions, with hidden tests", f"Write a Python module and save it as {mod}.py. It has two functions. "
            + " ".join(f"{i}) {what}." for i, (_, what, _, _) in enumerate(fns, 1))
            + f" Test both yourself before you finish. Then tell me, each on its own line, the value of {call[0]} and of {call[1]}.", check)


MODULES = {
    "roman": ("", '''def to_roman(n):
    out = ""
    for v, s in zip((1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1), "M CM D CD C XC L XL X IX V IV I".split()):
        while n >= v:
            out += s
            n -= v
    return out


def from_roman(s):
    v = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    return sum(-v[c] if v[c] < v.get(d, 0) else v[c] for c, d in zip(s, s[1:] + " "))
''', ["assert all(from_roman(to_roman(n)) == n for n in range(1, 4000))"]),
    "rle": ("", '''def encode(s):
    out, i = "", 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out += f"{s[i]}{j - i}"
        i = j
    return out


def decode(s):
    import re
    return "".join(c * int(n) for c, n in re.findall(r"([a-z])(\\d+)", s))
''', ["assert decode(encode('aaabcc')) == 'aaabcc'"]),
    "intervals": ("", '''def merge(xs):
    out = []
    for a, b in sorted(xs):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def covered(xs):
    return sum(b - a + 1 for a, b in merge(xs))
''', ["assert covered([[1, 3], [2, 4]]) == 4"]),
    "bases": ("", '''def to_base(n, b):
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        out = digits[n % b] + out
        n //= b
        if not n:
            return out


def from_base(s, b):
    return int(s, b)
''', ["assert from_base(to_base(255, 16), 16) == 255"]),
    "brackets": ("", '''def balanced(s):
    stack, pairs = [], {")": "(", "]": "[", "}": "{"}
    for c in s:
        if c in "([{":
            stack.append(c)
        elif c in pairs and (not stack or stack.pop() != pairs[c]):
            return False
    return not stack


def depth(s):
    deepest = now = 0
    for c in s:
        if c == "(":
            now += 1
            deepest = max(deepest, now)
        elif c == ")":
            now -= 1
    return deepest
''', ["assert balanced('(]') is False", "assert depth('(a(b)(c(d)))') == 3"]),
    "cipher": ("", '''def shift(text, k):
    out = ""
    for c in text:
        if c.islower():
            out += chr((ord(c) - 97 + k) % 26 + 97)
        elif c.isupper():
            out += chr((ord(c) - 65 + k) % 26 + 65)
        else:
            out += c
    return out


def unshift(text, k):
    return shift(text, -k)
''', ["assert unshift(shift('Hello, World!', 3), 3) == 'Hello, World!'"]),
    "factors": ("", '''def prime_factors(n):
    out, d = [], 2
    while d * d <= n:
        while n % d == 0:
            out.append(d)
            n //= d
        d += 1
    if n > 1:
        out.append(n)
    return out


def divisors(n):
    count = 1
    for p in set(prime_factors(n)):
        count *= prime_factors(n).count(p) + 1
    return count
''', ["assert divisors(360) == 24"]),
    "spiral": ("", '''def spiral(m):
    m, out = [list(row) for row in m], []
    while m:
        out += m.pop(0)
        m = [list(col) for col in zip(*m)][::-1]
    return out


def rotate(m):
    return [list(col) for col in zip(*m[::-1])]
''', ["assert spiral([[1, 2], [4, 3]]) == [1, 2, 3, 4]", "assert rotate([[1, 2], [3, 4]]) == [[3, 1], [4, 2]]"]),
    "durations": ("", '''def to_seconds(s):
    import re
    return sum(int(n) * {"h": 3600, "m": 60, "s": 1}[u] for n, u in re.findall(r"(\\d+)([hms])", s))


def to_text(n):
    h, m, s = n // 3600, n % 3600 // 60, n % 60
    return "".join(f"{v}{u}" for v, u in ((h, "h"), (m, "m"), (s, "s")) if v) or "0s"
''', ["assert to_seconds(to_text(5415)) == 5415"]),
    "anagrams": ("", '''def groups(words):
    by = {}
    for w in words:
        by.setdefault("".join(sorted(w)), []).append(w)
    return sorted(sorted(g) for g in by.values())


def is_anagram(a, b):
    return sorted(a.replace(" ", "").lower()) == sorted(b.replace(" ", "").lower())
''', ["assert is_anagram('Dormitory', 'dirty room')"]),
}


def module(task):
    m = re.search(r"save it as (\w+)\.py", task)
    asked = re.search(r"the value of (.+) and of (.+)\.\s*$", task, re.S)
    if not (m and asked and m.group(1) in MODULES):
        return None
    name = m.group(1)
    _, functions, tests = MODULES[name]
    # The program is the module: its functions, then what runs only when it is run itself (never when it is
    # imported): it saves itself under the module's name, tests the functions and prints what is asked. No code is
    # written inside a string (members that did broke their own quotes), and nothing is said twice: T4, a row of a
    # module must fit 508 pieces with the task beside it (with inspect.getsource and comments, 1 in 3 did not).
    body = [f"shutil.copy(__file__, {name + '.py'!r})", *tests, f"print({asked.group(1).strip()})", f"print({asked.group(2).strip()})"]
    return functions + '\n\nif __name__ == "__main__":\n    import shutil\n\n' + "".join(f"    {ln}\n" for ln in body)


make = h_module
lesson = module
