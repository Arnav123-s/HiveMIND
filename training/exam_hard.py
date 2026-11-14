"""The harder kinds of the hive's exam: work of several steps, still made by code and checked by code.

The first exam (training/exam.py) asks for one sum, one date, one fact. By 2026-11-13 the hive passed 14 to 16 of
its 16 tasks, so it could no longer show whether a change made the hive better. These kinds take several steps
each and their space of tasks is large (the numbers, tables, sites and specifications are drawn afresh):

    walk a site over several pages and count        two facts from two sources, combined
    a module of two functions, with hidden tests    a file given in the task, edited to a specification
    a join over two small tables                    a log read and counted into a file
    a search for a number with given properties     a simulation followed step by step
    several facts fetched and laid out as a file    a fact from a site and a date sum on it

Every check is computed here or read live from the source at the moment of checking. `python training/exam.py
show --level hard --seed N` prints a sitting; `sit --level hard` sits it.
"""
import csv
import datetime
import importlib.util
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from training import hive_bench as B  # noqa: E402

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
NAMES = ["Mira", "Tomas", "Aiko", "Ravi", "Lena", "Omar", "Nadia", "Jonas", "Ines", "Pavel", "Sofia", "Kofi"]
PACKAGES = ["requests", "numpy", "pandas", "flask", "django", "pytest", "rich", "httpx", "pydantic", "click", "tqdm", "scipy", "pillow", "jinja2",
            "sqlalchemy", "attrs", "black", "ruff", "mypy", "fastapi", "uvicorn", "aiohttp", "boto3", "celery", "lxml", "markdown", "networkx", "sympy"]


def _nums(text):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", re.sub(r"(?<=\d),(?=\d{3}\b)", "", text))]


def _says(body, x, tol=0.006):
    return any(abs(g - x) <= tol for g in _nums(body))


def _file(run, name):
    """The file the task asked for, by its exact name, wherever under the run's work folder it was saved."""
    got = [p for p in (run / "work").rglob(name) if p.is_file()] if (run / "work").exists() else []
    return got[0] if got else None


def _pypi(pkg):
    import requests
    d = requests.get(f"https://pypi.org/pypi/{pkg}/json", timeout=30).json()
    v = d["info"]["version"]
    return v, d["releases"][v][0]["upload_time"][:10]


# ---- a site walked over several pages --------------------------------------------------------------------------------
BIG = ["Sequential Art", "Nonfiction", "Fiction", "Young Adult", "Fantasy", "Romance", "Mystery", "Food and Drink", "Childrens",
       "Historical Fiction", "Add a comment"]


def _all_books(cat):
    """[(title, price)] of every book of a category, over all its pages."""
    from bs4 import BeautifulSoup
    home = BeautifulSoup(B._get("https://books.toscrape.com/"), "html.parser")
    url = "https://books.toscrape.com/" + next(a["href"] for a in home.select(".side_categories a") if a.text.strip() == cat)
    out = []
    while url:
        page = BeautifulSoup(B._get(url), "html.parser")
        for a in page.select("article.product_pod"):
            out.append((a.h3.a["title"], float(re.sub(r"[^\d.]", "", a.select_one(".price_color").text))))
        nxt = page.select_one("li.next a")
        url = url.rsplit("/", 1)[0] + "/" + nxt["href"] if nxt else None
    return out


def h_walk(r):
    cat, top = r.choice(BIG), r.random() < 0.5

    def check(run, report):
        books = _all_books(cat)
        price = (max if top else min)(p for _, p in books)
        body = B._body(report)
        ok = _says(body, len(books), 0.1) and _says(body, price)
        return ok, f"{cat}: {len(books)} books, the {'highest' if top else 'lowest'} price {price}; both in the answer: {ok}"
    return ("hard: websites", "walk a site over several pages", f"On books.toscrape.com the category '{cat}' runs over several pages. How many "
            f"books does it list in total, over all its pages, and what is the price of the {'most expensive' if top else 'cheapest'} one?", check)


def h_quotes(r):
    k = r.randrange(2, 6)

    def check(run, report):
        from bs4 import BeautifulSoup
        f = _file(run, "authors.json")
        if not f:
            return False, "no authors.json saved"
        want = {}
        for i in range(1, k + 1):
            for q in BeautifulSoup(B._get(f"https://quotes.toscrape.com/page/{i}/"), "html.parser").select(".quote .author"):
                want[q.text.strip()] = want.get(q.text.strip(), 0) + 1
        try:
            got = json.loads(f.read_text())
        except ValueError:
            return False, "authors.json is not JSON"
        return got == want, f"authors.json has {len(got) if isinstance(got, dict) else 0} authors, {len(want)} wanted; the same: {got == want}"
    return ("hard: websites", "walk a site and count into a file", f"Go through the first {k} pages of quotes.toscrape.com and save a file "
            "authors.json: one JSON object that maps each author's name to the number of that author's quotes on those pages. Then tell me "
            "which author has the most quotes there.", check)


# ---- two facts from two sources, combined ----------------------------------------------------------------------------
def h_two(r):
    a, b = r.sample(PACKAGES, 2)

    def check(run, report):
        (_, da), (_, db) = _pypi(a), _pypi(b)
        days = abs((datetime.date.fromisoformat(da) - datetime.date.fromisoformat(db)).days)
        later = a if da >= db else b
        body = B._body(report)
        m = re.search(r"later\W+([\w.-]+)", body.lower())
        named = da == db or bool(m and m.group(1).strip(".") == later)
        ok = named and any(abs(g - days) <= 1 for g in _nums(body))
        return ok, f"{a} {da}, {b} {db}: {later} is later by {days} days; in the answer: {ok}"
    return ("hard: live facts", "two facts from two sources, combined", f"Look at the latest versions of the packages {a} and {b} on PyPI. "
            "Which of the two was released more recently, and how many days lie between the two release dates? Answer in two lines: "
            "'later: NAME' and 'days: N'.", check)


def h_since(r):
    pkg = r.choice(PACKAGES)

    def check(run, report):
        v, d = _pypi(pkg)
        days = (datetime.date.today() - datetime.date.fromisoformat(d)).days
        body = B._body(report)
        ok = v in body and any(abs(g - days) <= 1 for g in _nums(body))
        return ok, f"{pkg} {v} of {d}, {days} days ago; version and days in the answer: {ok}"
    return ("hard: live facts", "a fact read and a date sum on it", f"What is the latest version of {pkg} on PyPI, on which date was it released, "
            "and how many days ago was that?", check)


AUTHORS = {"Albert Einstein": "Albert-Einstein", "Jane Austen": "Jane-Austen", "Marilyn Monroe": "Marilyn-Monroe", "Mark Twain": "Mark-Twain",
           "Eleanor Roosevelt": "Eleanor-Roosevelt", "Steve Martin": "Steve-Martin", "Harper Lee": "Harper-Lee", "George Eliot": "George-Eliot",
           "Bob Marley": "Bob-Marley", "Elie Wiesel": "Elie-Wiesel", "Mother Teresa": "Mother-Teresa", "Dr. Seuss": "Dr-Seuss",
           "Thomas A. Edison": "Thomas-A-Edison", "Friedrich Nietzsche": "Friedrich-Nietzsche", "Ernest Hemingway": "Ernest-Hemingway"}


def h_age(r):
    name = r.choice(sorted(AUTHORS))
    on = datetime.date(r.randrange(1990, 2031), r.randrange(1, 13), r.randrange(1, 28))

    def check(run, report):
        from bs4 import BeautifulSoup
        born = BeautifulSoup(B._get(f"https://quotes.toscrape.com/author/{AUTHORS[name]}/"), "html.parser").select_one(".author-born-date").text.strip()
        d = datetime.datetime.strptime(born, "%B %d, %Y").date()
        days = (on - d).days
        ok = _says(B._body(report), days, 0.1)
        return ok, f"born {born}; {days} days to {on}; in the answer: {ok}"
    return ("hard: websites", "a fact from a site and a date sum on it", f"Open quotes.toscrape.com, find {name}'s author page and read the date "
            f"of birth there. How many days lie between that date and {on.day} {MONTHS[on.month - 1]} {on.year}?", check)


def h_table(r):
    pk = sorted(r.sample(PACKAGES, r.choice([3, 4])))

    def check(run, report):
        f = _file(run, "versions.md")
        if not f:
            return False, "no versions.md saved"
        rows = [x for x in f.read_text().splitlines() if x.strip().startswith("|") and not re.fullmatch(r"[|\s:-]+", x.strip())]
        cells = [[c.strip() for c in x.strip().strip("|").split("|")] for x in rows][1:]
        want = [[p, *_pypi(p)] for p in pk]
        ok = len(cells) == len(want) and all(len(c) >= 3 and c[0].lower() == w[0] and c[1] == w[1] and w[2] in c[2] for c, w in zip(cells, want))
        return ok, f"versions.md has {len(cells)} rows; the {len(want)} packages in order with version and date: {ok}"
    return ("hard: plans", "several facts fetched and laid out as a file", f"Save a file versions.md holding a Markdown table with the columns "
            f"package, version, released: one row for each of the PyPI packages {', '.join(pk)}, sorted by package name, with its latest "
            "version and that version's release date as YYYY-MM-DD. Then tell me which of them was released most recently.", check)


# ---- a module of two functions, with hidden tests --------------------------------------------------------------------
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


# name: (module, [(function, what it must do, reference, how to draw its arguments)])
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


# ---- data given in the task ------------------------------------------------------------------------------------------
ITEMS = ["pen", "notebook", "lamp", "mug", "chair", "desk", "clock", "bag"]


def h_join(r):
    items = r.sample(ITEMS, 4)
    price = {i: r.randrange(3, 60) + r.choice([0, 0.5, 0.25]) for i in items}
    who = r.sample(NAMES, 4)
    orders = [(r.choice(who), r.choice(items), r.randrange(1, 9)) for _ in range(r.randrange(12, 19))]
    spent = {w: round(sum(q * price[i] for x, i, q in orders if x == w), 2) for w in who}
    best = max(spent, key=spent.get)
    while sorted(spent.values())[-1] == sorted(spent.values())[-2]:  # a tie has no single answer: one more order breaks it
        orders.append((best, items[0], 1))
        spent = {w: round(sum(q * price[i] for x, i, q in orders if x == w), 2) for w in who}
    item = r.choice(items)
    sold = sum(q for _, i, q in orders if i == item)
    total = round(sum(spent.values()), 2)

    def check(run, report):
        body = B._body(report)
        ok = best.lower() in body.lower() and _says(body, spent[best]) and _says(body, total) and _says(body, sold, 0.1)
        return ok, f"{best} spent most ({spent[best]}), total {total}, {sold} of {item}; all in the answer: {ok}"
    return ("hard: given data", "a join over two small tables", "Prices in dollars: " + ", ".join(f"{i} {price[i]:g}" for i in items)
            + ". Orders (customer, item, quantity): " + "; ".join(f"{w}, {i}, {q}" for w, i, q in orders)
            + f". Which customer spent the most and how much, what is the total revenue of all orders, and how many units of '{item}' "
            "were sold? Answer in four lines: 'customer: ', 'spent: ', 'revenue: ', 'units: '.", check)


CITIES = ["Lisbon", "Oslo", "Kyoto", "Lima", "Cairo", "Perth", "Quito", "Riga"]


def h_edit(r):
    rows = [(n, r.randrange(17, 70), r.choice(CITIES[:4])) for n in r.sample(NAMES, r.randrange(8, 12))]
    least = r.randrange(25, 45)
    text = "name,age,city\n" + "\n".join(f"{n},{a},{c}" for n, a, c in rows)
    want = [[n, str(a), c, n[0] + c[0]] for n, a, c in sorted((x for x in rows if x[1] >= least), key=lambda x: (x[2], x[0]))]

    def check(run, report):
        f = _file(run, "people.csv")
        if not f:
            return False, "no people.csv saved"
        got = [[c.strip() for c in row] for row in csv.reader(io.StringIO(f.read_text())) if any(c.strip() for c in row)]
        head = bool(got) and [c.lower() for c in got[0]] == ["name", "age", "city", "code"]
        ok = head and got[1:] == want and _says(B._body(report), len(want), 0.1)
        return ok, f"people.csv: heading right {head}, {len(got) - 1 if got else 0} rows against {len(want)} wanted, the same and counted in the answer: {ok}"
    return ("hard: files", "a file given in the task, edited to a specification", "Here is a CSV file:\n" + text + f"\nMake a new file people.csv from "
            f"it: keep only the people aged {least} or more, sort them by city and then by name, and add a fourth column 'code' holding the "
            "first letter of the name followed by the first letter of the city. Keep the heading line. Then tell me how many people are in "
            "the new file.", check)


SERVICES = ["auth", "billing", "search", "mail", "storage"]


def h_log(r):
    day = datetime.date(2026, r.randrange(1, 13), r.randrange(1, 28))
    lines = []
    for _ in range(r.randrange(16, 24)):
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


# ---- searching and simulating ----------------------------------------------------------------------------------------
def h_search(r):
    kind = r.choice(["digits", "palins", "nth", "change"])
    if kind == "digits":
        n, d, s = r.randrange(1000, 90000), r.choice([7, 11, 13, 17]), r.randrange(12, 26)
        x = next(i for i in range(n + 1, 10**7) if i % d == 0 and sum(map(int, str(i))) == s)
        return ("hard: search", "a number with given properties", f"Find the smallest whole number greater than {n} that is divisible by {d} and "
                f"whose digits add up to {s}.", lambda run, report: (_says(B._body(report), x, 0.1), f"wants {x}"))
    if kind == "palins":
        a, k = r.randrange(100, 5000), r.choice([3, 7, 11, 13])
        b = a + r.randrange(20000, 90000)
        x = sum(1 for i in range(a, b + 1) if str(i) == str(i)[::-1] and i % k == 0)
        return ("hard: search", "a number with given properties", f"How many whole numbers from {a} to {b} (both included) read the same "
                f"backwards as forwards and are divisible by {k}?", lambda run, report: (_says(B._body(report), x, 0.1), f"wants {x}"))
    if kind == "nth":
        n = r.randrange(300, 3000)
        ps, i = [], 1
        while len(ps) < n:
            i += 1
            if all(i % p for p in ps if p * p <= i):
                ps.append(i)
        x, tot = ps[-1], sum(map(int, str(ps[-1])))
        return ("hard: search", "a number with given properties", f"What is prime number {n} (counting 2 as the first), and what do its digits add up to?",
                lambda run, report: (_says(B._body(report), x, 0.1) and _says(B._body(report), tot, 0.1), f"wants {x} and {tot}"))
    coins, amount = sorted(r.sample([1, 2, 5, 10, 20, 25, 50], 4)), r.randrange(60, 300)
    if 1 not in coins:
        coins[0] = 1
    ways = [1] + [0] * amount
    for c in coins:
        for v in range(c, amount + 1):
            ways[v] += ways[v - c]
    x = ways[amount]
    return ("hard: search", "a number with given properties", f"In how many different ways can {amount} cents be paid with coins of {', '.join(map(str, coins))} "
            "cents (any number of each, order does not matter)?", lambda run, report: (_says(B._body(report), x, 0.1), f"wants {x}"))


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


MAKERS = [h_walk, h_quotes, h_two, h_since, h_age, h_table, h_module, h_module, h_join, h_edit, h_log, h_search, h_sim]
# Kinds the hive never practises on (training/practice draws from the others): what it scores on these is what it
# learned that carries over to work it has not seen, not what it learned by heart.
HELD_OUT = {"h_quotes", "h_two", "h_edit", "h_sim"}
