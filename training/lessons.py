"""Lessons: right programs for the kinds of task the hive cannot do yet, checked before they are taught.

    python training/lessons.py --seed S [--per-kind 1] [--several 4] [--failures failures.jsonl] [--most-failures 12] [--own-rows rows.jsonl ...] [--record generations.jsonl --dna t80] [--out rows.jsonl]
    python training/lessons.py --show MAKER [--seed S] [--level L]      one lesson: its task, its program, what it printed

Why (from first principles): the hive learns only from programs that its own checks confirmed. On a kind of task it
never gets right (reading a website, walking a site over pages, saving a file, writing a module) it has nothing to
learn from, so practising that kind more teaches nothing: in generation 27 such kinds stood at 0 of 2 or 0 of 3 for
generation after generation. A child learns a new skill from someone showing it once, done right. These are those
showings: for each kind, a program written the way a careful member would write it (fetch the site's first page,
follow its links, never make an address up; copy given data into the program; save a module from functions the
program has tested), made for a fresh task of that kind with fresh values every generation.

Nothing is taught unless it is right: every lesson's program is run in the hive's own runtime (team/tools/sandbox)
and put to the task's own check, the same one the exam uses. A lesson whose program fails its check (a site that
changed, a service down) is dropped, never taught.

Two kinds of rows come out, in the same form as the hive's own (training/grow.rows_of):
  first, done   the task and the right program; the program's output and DONE
  fix           where the hive got this very task wrong before (failures.jsonl from practice): its own wrong program
                and what it printed, then the right program. The task is made again from the same seed and level.

The kinds held out of practice (exam_hard.HELD_OUT) are never taught: they measure whether what is learned carries
over to work never shown.
"""
import json
import re
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HEAD = '''import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

headers = {"User-Agent": "hive/1.0"}


def page(url):
    return BeautifulSoup(requests.get(url, headers=headers, timeout=30).content, "html.parser")
'''


def _fill(src, **values):
    """A program from its template: each __NAME__ replaced by the value written as Python (repr)."""
    for k, v in values.items():
        src = src.replace(f"__{k.upper()}__", repr(v))
    return src.strip() + "\n"


# ---- websites ---------------------------------------------------------------------------------------------------------
FIND_AUTHOR = HEAD + '''
# an author's own page is linked from their quotes: walk the site's pages from the first until a quote by them shows it
name = __NAME__
url, about = "https://quotes.toscrape.com/", None
while url and not about:
    p = page(url)
    for quote in p.select("div.quote"):
        if quote.select_one("small.author").text.strip() == name:
            about = urljoin(url, quote.select_one("a[href*='/author/']")["href"])
            break
    nxt = p.select_one("li.next a")
    url = urljoin(url, nxt["href"]) if nxt else None
born = page(about).select_one(".author-born-date").text.strip()
'''


def born(task):
    m = re.search(r"go to (.+?)'s author page", task)
    return m and _fill(FIND_AUTHOR + 'print("born:", born)\n', name=m.group(1))


def age(task):
    m = re.search(r"find (.+?)'s author page", task)
    on = re.search(r"between that date and (\d{1,2}) (\w+) (\d{4})", task)
    if not (m and on):
        return None
    return _fill(FIND_AUTHOR + '''
from datetime import datetime
birthday = datetime.strptime(born, "%B %d, %Y").date()
day = datetime.strptime(__ON__, "%d %B %Y").date()
print("born:", born)
print("days:", abs((day - birthday).days))
''', name=m.group(1), on=" ".join(on.groups()))


CATEGORY = HEAD + '''
# a category is reached from the site's first page, by the link whose text is its name
site = "https://books.toscrape.com/"
link = next(a for a in page(site).select(".side_categories a") if a.text.strip() == __CATEGORY__)
url = urljoin(site, link["href"])
'''


def csv_page(task):
    m = re.search(r"first page of the (.+?) category on books\.toscrape\.com", task)
    return m and _fill(CATEGORY + '''
import csv
import re

books = page(url).select("article.product_pod")
with open("books.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["title", "price"])
    for b in books:
        w.writerow([b.h3.a["title"], re.sub(r"[^0-9.]", "", b.select_one(".price_color").text)])
print(f"books.csv saved: {len(books)} books")
''', category=m.group(1))


def walk(task):
    m = re.search(r"the category '(.+?)' runs over several pages", task)
    if not m:
        return None
    which, pick = ("most expensive", "max") if "most expensive" in task else ("cheapest", "min")
    return _fill(CATEGORY + f'''
import re

# the category goes on over several pages: follow its "next" link until there is none
prices = []
while url:
    p = page(url)
    prices += [float(re.sub(r"[^0-9.]", "", b.select_one(".price_color").text)) for b in p.select("article.product_pod")]
    nxt = p.select_one("li.next a")
    url = urljoin(url, nxt["href"]) if nxt else None
print("books:", len(prices))
print("{which}:", f"{{{pick}(prices):.2f}}")
''', category=m.group(1))


# ---- live facts -------------------------------------------------------------------------------------------------------
PYPI = '''import requests
from datetime import date

headers = {"User-Agent": "hive/1.0"}


def latest(package):
    """The latest version on PyPI and the date it was released."""
    data = requests.get(f"https://pypi.org/pypi/{package}/json", headers=headers, timeout=30).json()
    version = data["info"]["version"]
    return version, data["releases"][version][0]["upload_time"][:10]
'''


def since(task):
    m = re.search(r"latest version of (\S+) on PyPI", task)
    return m and _fill(PYPI + '''
version, released = latest(__PACKAGE__)
print("version:", version)
print("released:", released)
print("days ago:", (date.today() - date.fromisoformat(released)).days)
''', package=m.group(1))


def table(task):
    m = re.search(r"PyPI packages (.+?), sorted by package name", task)
    if not m:
        return None
    return _fill(PYPI + '''
rows = sorted((p, *latest(p)) for p in __PACKAGES__)
with open("versions.md", "w") as f:
    f.write("| package | version | released |\\n|---|---|---|\\n")
    for p, v, d in rows:
        f.write(f"| {p} | {v} | {d} |\\n")
newest = max(rows, key=lambda r: r[2])
print("versions.md saved")
print("released most recently:", newest[0], newest[2])
''', packages=[p.strip() for p in m.group(1).split(",")])


WIKIDATA = {  # what is asked -> (the property, its units in the unit asked for)
    "population": ("P1082", {"Q199": 1.0}),
    "height above sea level": ("P2044", {"Q11573": 1.0, "Q3710": 0.3048}),
    "length of the river": ("P2043", {"Q828224": 1.0, "Q11573": 0.001, "Q253276": 1.609344}),
}


def wikidata(task):
    m = re.search(r"Wikidata item (Q\d+)", task)
    what = next((k for k in WIKIDATA if k in task), None)
    if not (m and what):
        return None
    prop, units = WIKIDATA[what]
    return _fill('''import requests

qid, prop = __QID__, __PROP__
units = __UNITS__  # the unit's item on Wikidata -> how many of the unit asked for it is
data = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json", headers={"User-Agent": "hive/1.0"}, timeout=30).json()
claims = data["entities"][qid]["claims"][prop]
best = [c for c in claims if c["rank"] == "preferred"] or [c for c in claims if c["rank"] == "normal"]
value = best[0]["mainsnak"]["datavalue"]["value"]
unit = value.get("unit", "").rsplit("/", 1)[-1]
print(round(float(value["amount"]) * units.get(unit, 1.0), 2))
''', qid=m.group(1), prop=prop, units=units)


# ---- given data and computing -----------------------------------------------------------------------------------------
LOG_COUNT = '''errors, hours = {}, {}
for line in __LINES__:
    day, clock, level, rest = line.split(" ", 3)
    if level == "ERROR":
        service = rest.split(":")[0]
        errors[service] = errors.get(service, 0) + 1
        hours[int(clock[:2])] = hours.get(int(clock[:2]), 0) + 1
with open("errors.json", "w") as f:
    json.dump(errors, f)
print("errors.json saved:", errors)
print("hour:", max(hours, key=hours.get))
'''


def log(task, copy=False):
    """The log is data the task gives: the runtime saves it as a file (team/tools/sandbox.give), so the program reads
    log.txt and stays short whatever the log's length. (T4: the program that copied the log in was about 1300 pieces,
    left out of training on every runner that trains in 32 bits.) copy: the log copied into the program instead, for a
    task of several parts whose first block of data is another part's, which log.txt would then hold."""
    m = re.search(r"Here is a log:\n(.*?)\nSave a file errors\.json", task, re.S)
    if not m:
        return None
    if copy:
        return 'import json\n\nlog = """' + m.group(1) + '"""\n' + LOG_COUNT.replace("__LINES__", "log.splitlines()")
    return "import json\n\n" + LOG_COUNT.replace("__LINES__", 'open("log.txt")')


def units(task):
    for pat, expr, unit in ((r"What is (-?\d+) degrees Fahrenheit in Celsius", "(v - 32) * 5 / 9", "degrees Celsius"),
                            (r"What is (-?\d+) degrees Celsius in Fahrenheit", "v * 9 / 5 + 32", "degrees Fahrenheit"),
                            (r"How many miles are (\d+) kilometres", "v / 1.609344", "miles"),
                            (r"How many pounds are (\d+) kilograms", "v * 2.2046226", "pounds")):
        m = re.search(pat, task)
        if m:
            return f"v = {int(m.group(1))}\nprint(f\"{{{expr}:.1f}} {unit}\")\n"
    return None


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


def know(task):
    """What does not change and is known needs no source: it is written into the program and printed. (The talk test
    of 2026-11-15: asked for the capital of Australia, all three members fetched it from addresses they made up.)"""
    from training import exam
    m = re.search(r"What is the capital of (.+?)\?", task)
    if m and m.group(1) in exam.CAPITALS:
        return _fill('''# a capital city does not change and is known: no source is needed
capital = __CAPITAL__
print(capital)
''', capital=exam.CAPITALS[m.group(1)])
    m = re.search(r"chemical symbol and the atomic number of (\w+)\?", task)
    if m and m.group(1) in exam.ELEMENTS:
        sym, num = exam.ELEMENTS[m.group(1)]
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


# ---- everyday kinds: every value computed by the program, never typed --------------------------------------------------
# Seen in generation 28's practice: 'pocket' backwards typed as 'etok' (two members agreed on it), 'lantern' in capitals
# typed as 'LANCERN', 680 dollars less 15% typed as 528, and code to be fixed run as it was. A value that can be
# computed is computed: 'pocket'[::-1], 'lantern'.upper(), 680 * (1 - 15 / 100).
def percent(task):
    m = re.search(r"costs (\d+) dollars and the price (rises|falls) by (\d+)%\.", task)
    if not m:
        return None
    steps = [(m.group(2), int(m.group(3)))] + [(a, int(b)) for a, b in re.findall(r"Then it (rises|falls) by (\d+)%\.", task)]
    lines = [f"price = {int(m.group(1))}"]
    for way, q in steps:
        lines.append(f"price = price * (1 {'+' if way == 'rises' else '-'} {q} / 100)  # {way} by {q}%")
    return "\n".join(lines) + '\nprint(f"new price: {price:.2f}")\n'


DATE = r"(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})"


def days(task):
    m = re.search(rf"from {DATE} to {DATE}", task)
    return m and _fill('''from datetime import datetime

start = datetime.strptime(__A__, "%d %B %Y").date()
end = datetime.strptime(__B__, "%d %B %Y").date()
print("days:", (end - start).days)
''', a=" ".join(m.group(1, 2, 3)), b=" ".join(m.group(4, 5, 6)))


def weekday(task):
    m = re.search(rf"What day of the week is {DATE}", task)
    return m and _fill('''from datetime import datetime

print(datetime.strptime(__D__, "%d %B %Y").strftime("%A"))
''', d=" ".join(m.groups()))


def small_table(task):
    m = re.search(r"Daily (.+?) in (\w+): (.+?)\. Which day had the (least|most)", task)
    if not m:
        return None
    data = {d: int(v) for d, v in re.findall(r"(\w{3}) (\d+)", m.group(3))}
    pick = "min" if m.group(4) == "least" else "max"
    src = _fill('''values = __DATA__
average = sum(values.values()) / len(values)
''', data=data) + f"day = {pick}(values, key=values.get)\n"
    if "Answer in four lines" in task:
        return src + '''print("day:", day)
print("average:", round(average, 2))
print("total:", sum(values.values()))
print("above:", sum(v > average for v in values.values()))
'''
    return src + '''print("day:", day)
print("average:", round(average, 2))
'''


def code(task):
    m = re.search(r"how many vowels '(\w+)' has", task)
    if m:
        return _fill('''def vowels(word):
    return sum(c in "aeiou" for c in word.lower())


print(vowels(__W__))
''', w=m.group(1))
    m = re.search(r"adds up the digits of a number and tell me the result for (\d+)", task)
    if m:
        return f"def digit_sum(n):\n    return sum(int(c) for c in str(n))\n\n\nprint(digit_sum({int(m.group(1))}))\n"
    m = re.search(r"more than four letters in a sentence and tell me the count for '(.+?)'", task)
    if m:
        return _fill('''def long_words(sentence):
    return sum(len(w) > 4 for w in sentence.split())


print(long_words(__S__))
''', s=m.group(1))
    m = re.search(r"adds up all the even numbers from 1 to (\d+)", task)
    if m:
        return f"print(sum(i for i in range(1, {int(m.group(1))} + 1) if i % 2 == 0))\n"
    return None


def mend(task):
    m = re.search(r"Fix it and tell me the output:\n(.+)$", task, re.S)
    if not m:
        return None
    given = m.group(1).strip()
    for asked, wrong, right in (("print the average", "print(sum(nums))", "print(sum(nums) / len(nums))  # the average, not the total"),
                                ("print the largest", "print(min(nums))", "print(max(nums))  # the largest, not the smallest"),
                                ("print the product", "print(a + b)", "print(a * b)  # the product, not the sum")):
        if asked in task and wrong in given:
            return given.replace(wrong, right) + "\n"
    return None


LIST_ITEMS = {"fruits": ["apple", "banana", "orange", "mango", "pear", "cherry", "grape"],
              "European capital cities": ["Paris", "Berlin", "Madrid", "Rome", "Lisbon", "Vienna", "Oslo"],
              "programming languages": ["Python", "Java", "C", "Rust", "Go", "JavaScript", "Ruby"],
              "colours": ["red", "blue", "green", "yellow", "purple", "orange", "black"],
              "musical instruments": ["piano", "violin", "guitar", "flute", "drum", "trumpet", "cello"]}
TWO_SENTENCES = {
    "why the sky is blue": "Sunlight is scattered by the molecules of the air, and blue light is scattered much more than red light because its waves are shorter. So blue light reaches our eyes from every part of the sky.",
    "why the sea is salty": "Rain wears down rocks on land, and rivers carry the salt from them into the sea. When sea water evaporates the salt stays behind, so over millions of years the sea has become salty.",
    "why leaves fall in autumn": "In autumn the days grow shorter and colder, so trees stop making chlorophyll and their leaves lose their green colour. The tree then seals each leaf off to save water through the winter, and the leaf falls.",
    "why the moon has phases": "The moon does not shine by itself but reflects light from the sun, so only the half that faces the sun is lit. As the moon travels along its orbit around the earth, we see more or less of that lit half, and these are its phases.",
}


def form(task):
    from training import exam
    m = re.search(r"Give me exactly (\d+) (.+?) as a numbered list and nothing else", task)
    if m and m.group(2) in LIST_ITEMS:
        return _fill('''# well known, and nothing to compute: written into the program
items = __ITEMS__
for i, item in enumerate(items[:__N__], 1):
    print(f"{i}. {item}")
''', items=LIST_ITEMS[m.group(2)], n=int(m.group(1)))
    m = re.search(r"what is the opposite of '(\w+)'\?", task)
    if m and m.group(1) in exam.OPPOSITES:
        word = exam.OPPOSITES[m.group(1)]
        return _fill("# one word and nothing else\nprint(__W__)\n", w=word[0] if isinstance(word, tuple) else word)
    m = re.search(r"Write the word '(\w+)' in capital letters and nothing else", task)
    if m:
        return _fill("print(__W__.upper())\n", w=m.group(1))
    m = re.search(r"keys name, age and city for (\w+), who is (\d+) years old and lives in (\w+)\. Only the JSON", task)
    if m:
        return _fill('''import json

print(json.dumps({"name": __NAME__, "age": __AGE__, "city": __CITY__}))
''', name=m.group(1), age=int(m.group(2)), city=m.group(3))
    m = re.search(r"Explain (.+?) in exactly two sentences", task)
    if m and m.group(1) in TWO_SENTENCES:
        return _fill("# something only I can write: the text is put in a string and printed\nprint(__T__)\n", t=TWO_SENTENCES[m.group(1)])
    return None


def orders(task):
    from training import exam
    m = re.search(r"first multiply (\d+) by (\d+); then write the word '(\w+)' backwards; then name the capital of (.+?)\.$", task.strip())
    if not (m and m.group(4) in exam.CAPITALS):
        return None
    return _fill('''print("A:", __A__ * __B__)
print("B:", __W__[::-1])
print("C:", __C__)  # a capital city is known: no source
''', a=int(m.group(1)), b=int(m.group(2)), w=m.group(3), c=exam.CAPITALS[m.group(4)])


def join(task):
    m = re.search(r"Prices in dollars: (.+?)\. Orders \(customer, item, quantity\): (.+?)\. Which customer spent the most.+units of '(\w+)' were sold", task, re.S)
    if not m:
        return None
    # the two tables are copied in as the task writes them, and split there: as many pieces as the task's own text
    # (T4: as lists of tuples they took 300 pieces, and every row of the kind was over a 32-bit runner's limit)
    return _fill('''price = dict(p.split() for p in __PRICES__.split(", "))
spent, units = {}, 0
for order in __ORDERS__.split("; "):
    who, item, n = order.split(", ")
    spent[who] = spent.get(who, 0) + int(n) * float(price[item])
    units += int(n) * (item == __ITEM__)
best = max(spent, key=spent.get)
print("customer:", best)
print("spent:", round(spent[best], 2))
print("revenue:", round(sum(spent.values()), 2))
print("units:", units)
''', prices=m.group(1), orders=m.group(2), item=m.group(3))


def pypi_version(task):
    m = re.search(r"current version of (\S+) on PyPI", task)
    return m and _fill(PYPI + '''
print("version:", latest(__P__)[0])
''', p=m.group(1))


def licence(task):
    m = re.search(r"Under which licence is (\S+) published on Hugging Face", task)
    return m and _fill('''import requests

data = requests.get(f"https://huggingface.co/api/models/{__M__}", headers={"User-Agent": "hive/1.0"}, timeout=30).json()
print("licence:", data["cardData"]["license"])
''', m=m.group(1))


# ---- a module of two functions ------------------------------------------------------------------------------------------
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


# the makers taught, and how each one's program is written. The held-out kinds are never here.
SOLVERS = {"m_percent": percent, "m_days": days, "m_weekday": weekday, "m_table": small_table, "m_code": code, "m_fix": mend,
           "m_follow": form, "m_steps": orders, "h_join": join, "m_pypi": pypi_version, "m_licence": licence,
           "m_know": know, "m_born": born, "m_csv": csv_page, "m_units": units, "h_walk": walk, "h_since": since, "h_age": age, "h_table": table,
           "h_module": module, "h_log": log, "h_search": search, "h_web": wikidata}


def _maker(name):
    from training import exam, exam_hard
    return getattr(exam, name, None) or getattr(exam_hard, name)


def program_for(task, check):
    """The right program for a task, or None where a part has no lesson. A task of several parts (team/parts.py) gets
    its parts' programs one after another, each printing its answers under its own heading."""
    from team import parts as P
    pieces = P.of_task(task)
    if getattr(check, "maker", "") != "compound" or not pieces:
        return SOLVERS[check.maker](task) if check.maker in SOLVERS else None
    from team.tools.sandbox import given
    blocks = given(task)
    out = []
    for (letter, text), part in zip(sorted(pieces.items()), check.parts):
        if part[0] == "h_log":  # log.txt holds the task's first block of data: the log, or another part's
            mine = given(text)
            prog = log(text, copy=not (mine and blocks and blocks[0]["text"] == mine[0]["text"]))
        else:
            prog = SOLVERS[part[0]](text) if part[0] in SOLVERS else None
        if not prog:
            return None
        out.append(f"# ---- PART {letter}: each part is done by itself and printed under its own heading\n"
                   f"print({'PART ' + letter!r})\n" + prog.strip() + "\n")
    return "\n\n".join(out)


def lesson(maker, rseed, level=0, parts=None, timeout=300):
    """One lesson: the task made again from its maker (or its parts), its program, and whether the task's own check
    says it is right. {"maker", "rseed", "level", "parts", "task", "kind", "program", "answer", "ok", "why"}."""
    from training import exam
    from team.tools.sandbox import give, run_python
    made = exam.remake(maker, rseed, level, parts)
    if not made:
        return {"maker": maker, "rseed": rseed, "level": level, "parts": parts, "task": "", "kind": "", "ok": False, "why": "the task cannot be made again"}
    field, kind, task, check = made
    out = {"maker": maker, "rseed": rseed, "level": level, "parts": parts, "task": task, "kind": kind, "program": "", "answer": "", "ok": False, "why": ""}
    program = program_for(task, check)
    if not program:
        out["why"] = "no program for this form of the task"
        return out
    out["program"] = program
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        # the task's data saved where its program can open it, as the runtime does for a member (team/solo.member)
        give(task, work, skip=_wanted(task))
        res = run_python(program, work, name="lesson.py", timeout=timeout)
        out["answer"] = res["stdout"].strip()
        if res["returncode"] != 0 or not out["answer"]:
            out["why"] = f"the program failed: {(res['stderr'].strip().splitlines() or ['no output'])[-1][:200]}"
            return out
        (work / "lesson.py").unlink(missing_ok=True)
        try:
            ok, why = check(Path(tmp), out["answer"])
        except Exception as e:  # noqa: BLE001 - a check that cannot be made: not taught
            ok, why = False, f"check failed: {type(e).__name__}: {e}"
    out["ok"], out["why"] = bool(ok), why
    return out


def _const(name):
    """A constant of the members' own code (team/solo.py), read from its source: the orders a taught member works under
    and what it is asked after a program ran. Read, not imported, so that lessons need no model library."""
    import ast
    tree = ast.parse((ROOT / "team" / "solo.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


LIMIT = 508  # the longest row (in the DNA's pieces) a runner that trains in 32 bits takes (training/grow.train, fits)
_PIECE = re.compile(r"\d| ?[A-Za-z]{1,7}|\n| {2,}|[^\w\s]{1,2}")
_TOK = []


def _tokenizer():
    """The DNA's own tokenizer (the 1.7B's; the members share it), from the local Hugging Face cache or fetched (one
    small file); None where neither can be had, and pieces() then counts by a rule."""
    if not _TOK:
        try:
            from huggingface_hub import hf_hub_download, try_to_load_from_cache
            from tokenizers import Tokenizer
            from training import grow
            path = try_to_load_from_cache(grow.UNPACKED["t17"], "tokenizer.json")
            path = path if isinstance(path, str) else hf_hub_download(grow.UNPACKED["t17"], "tokenizer.json")
            _TOK.append(Tokenizer.from_file(path))
        except Exception:  # noqa: BLE001 - no library, no cache and no network: counted by the rule
            _TOK.append(None)
    return _TOK[0]


def pieces(text):
    """How many of the DNA's pieces a text is: by its tokenizer, or with none at hand by a rule that comes within
    about a sixth of it (every digit, short word, line end, indent and pair of signs one piece)."""
    tok = _tokenizer()
    return len(tok.encode(text or "", add_special_tokens=False).ids) if tok else len(_PIECE.findall(text or ""))


def row_pieces(row):
    """How many pieces a training row is with its chat template, as training/grow.train's encode counts it."""
    return 9 + sum(pieces(m["content"]) + 5 for m in row["messages"]) + pieces(row["output"])


def lean(task, program, head=3, tail=2):
    """The task as a lesson's rows show it. A block of data the task gives (team/tools/sandbox.given) that the program
    does not copy in, because it reads the file the runtime saves, keeps only its first and last lines and a line
    that says how many are left out between: what is taught is the program, which never needs the rest. A log of 16
    to 34 lines is 400 to 850 pieces by itself, more than a row may hold on a runner that trains in 32 bits (T4)."""
    from team.tools.sandbox import given
    for b in given(task):
        lines = b["text"].splitlines()
        if len(lines) > head + tail + 2 and not any(ln.strip() in program for ln in lines if len(ln.strip()) > 12):
            cut = lines[:head] + [f"... ({len(lines) - head - tail} more lines like these) ..."] + lines[-tail:]
            task = task.replace(b["text"], "\n".join(cut), 1)
    return task


def _wanted(task):
    """The files the TASK asks to be saved (team/solo.wanted), with the pattern read from the members' source."""
    import ast
    tree = ast.parse((ROOT / "team" / "solo.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "FILE" for t in node.targets):
            pattern = re.compile(ast.literal_eval(node.value.args[0]), re.I)
            return list(dict.fromkeys(m.group(1) for m in pattern.finditer(task)))
    raise KeyError("FILE")


def rows(les, wrong=None, today=None):
    """Training rows of a lesson that its check passed, in the hive's own form (training/grow.rows_of). wrong: a
    failure record of the hive for this very task ({"program", "printed"}): a fix row is added from its program."""
    if not les.get("ok"):
        return []
    from training import grow
    short, more = _const("SHORT"), _const("MORE")
    head = [{"role": "system", "content": short.format(today=today or time.strftime("%Y-%m-%d (%A)"))},
            {"role": "user", "content": f"TASK: {lean(les['task'], les['program'])}"}]
    fenced = f"```python\n{les['program'].strip()}\n```"
    base = {"task": les["task"], "kind": les["kind"], "seed": les["rseed"], "who": "lesson", "member": 0, "lesson": les["maker"]}  # noqa: E501
    out = [base | {"type": "first", "messages": head, "output": fenced},
           base | {"type": "done", "messages": head + [{"role": "assistant", "content": fenced},
                                                         {"role": "user", "content": f"OUTPUT:\n{les['answer'][-1800:]}\n\n{more}"}], "output": "DONE"}]
    if wrong and wrong.get("program") and wrong["program"].strip() != les["program"].strip():
        printed, lines = wrong.get("printed") or "(it printed nothing)", wrong["program"].strip().splitlines()
        # what is taught is the right program; the wrong one and what it printed are context. Over LIMIT, they are
        # cut (the middle of the program, the start of what it printed) more than training/grow.shorten would (T4)
        for keep, tail in ((len(lines), 1200), (6, 300), (3, 120), (0, 60)):
            cut = f"# ... ({len(lines) - keep} lines of this program left out) ..."
            shown = lines if len(lines) <= keep + 1 else lines[:keep - keep // 3] + [cut] + lines[len(lines) - keep // 3:] if keep else [cut]
            row = base | {"type": "fix", "messages": head + [{"role": "assistant", "content": "```python\n" + "\n".join(shown) + "\n```"},
                                                             {"role": "user", "content": grow.MEND.format(shown=f"OUTPUT:\n{printed[-tail:]}")}], "output": fenced}
            if row_pieces(row) <= LIMIT:
                break
        out.append(row)
    return out


OWN = 3  # a kind with this many right programs of the hive's own is the hive's to learn: it gets no more lessons


def own_counts(*row_files):
    """{kind: how many right programs the hive found itself} (rows of type "first" that no lesson wrote), from the
    rows gathered so far: practice, dreams, the trunk's and the cells' own work."""
    count = {}
    for f in row_files:
        for ln in Path(f).read_text().splitlines() if f and Path(f).exists() else []:
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("type") == "first" and r.get("who") != "lesson":
                count[r.get("kind", "")] = count.get(r.get("kind", ""), 0) + 1
    return count


def pulse_counts(record, dna, last=3):
    """{kind: [passed, sat]} over the last `last` pulses of this DNA's body (training/reports/generations.jsonl)."""
    lines = []
    for ln in Path(record).read_text().splitlines() if record and Path(record).exists() else []:
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        kinds = d.get("arms", {}).get("after", {}).get("kinds") if isinstance(d, dict) else None
        if d.get("dna", "t17") == dna and isinstance(kinds, dict) and kinds:
            lines.append(kinds)
    out = {}
    for kinds in lines[-last:]:
        for k, v in kinds.items():
            if isinstance(v, list) and len(v) == 2:
                a = out.setdefault(k, [0, 0])
                a[0], a[1] = a[0] + v[0], a[1] + v[1]
    return out


def reason(why):
    """Why a lesson was not taught, in a few words: "timed out", "site refused" (the site answered with an error or
    not at all), "program failed" (it stopped with an error or printed nothing), "not made" (the task could not be made
    again), or "check failed" (it ran and printed, and the task's own check said no)."""
    w = (why or "").lower()
    if "timeout" in w or "timed out" in w:
        return "timed out"
    if any(x in w for x in ("connectionerror", "connection refused", "connection reset", "max retries", "httperror",
                            "too many requests", "forbidden", "service unavailable", "bad gateway", "nameresolution",
                            "name or service not known", "remotedisconnected", "sslerror", "is a web page (html), not json")) \
            or re.search(r"\b(403|429|5\d\d) (client|server) error", w):
        return "site refused"
    if w.startswith("check failed: jsondecodeerror"):  # the check read the site, and the site sent no JSON
        return "site refused"
    if w.startswith(("could not be made", "the task cannot be made", "no program")):
        return "not made"
    if w.startswith("the program failed"):
        return "program failed"
    return "check failed"


def by_kind_line(by_kind, failed):
    """The printed line: right of made for every kind, worst first, the main reason of its failures beside it."""
    parts = []
    for k, (r, n) in sorted(by_kind.items(), key=lambda kv: (kv[1][0] / max(kv[1][1], 1), kv[0])):
        why = failed.get(k) or {}
        main = max(why, key=why.get) if why else ""
        parts.append(f"{k} {r}/{n}" + (f" ({main})" if main else ""))
    return "lessons by kind: " + (", ".join(parts) or "none made")


def fitting(maker, rseed, level=0, parts=None, fresh=True, tries=8):
    """A lesson whose rows (first and done) fit LIMIT pieces. A fresh lesson (no task the hive got wrong) whose task
    drew values so long that they do not (a module asked of two 4 by 4 matrices: they are in the task and again in the
    program) is drawn again, with the seed and a number, up to `tries` times; the shortest right one is kept when none
    fits, for the runners that take longer rows (a join's always: its tables are in the task and in the program). A
    task the hive got wrong is its own and is never drawn again; nor is a task of several parts (its parts' seeds)."""
    best, n_best = None, None
    for j in range(tries if fresh and maker != "compound" else 1):
        try:
            les = lesson(maker, rseed if j == 0 else f"{rseed}:{j}", level, parts)
        except Exception as e:  # noqa: BLE001 - a task that cannot be made (a site down): no lesson
            les = {"maker": maker, "ok": False, "why": f"could not be made: {type(e).__name__}: {str(e)[:120]}"}
        if not les.get("ok"):
            if best is None and j == 0:
                return les  # a lesson that is not right (a site down) is not drawn again: its failure is counted
            continue
        n = max(row_pieces(r) for r in rows(les, today="2026-01-01 (Thursday)"))  # its first and its done row
        if n <= LIMIT:
            return les
        if best is None or n < n_best:
            best, n_best = les, n
    return best


def teach(seed, per_kind=1, failures=None, most_failures=12, out=None, log=print, levels=None, minutes=0, several=4, own=None, pulse=None):
    """A generation's lessons: per_kind fresh tasks of every taught kind, at the body's levels, `several` fresh tasks of
    several parts, and the most recent tasks the hive got wrong (of the taught kinds), each made again and shown done
    right. Rows appended to out.
    own: {kind: right programs the hive found itself} (own_counts). Lessons only start a kind: one where the hive has
    OWN of its own gets none, so its practice and its dreams carry it from there, as they do every kind it can learn
    from its own work.
    pulse: {kind: [passed, sat]} of the body's last pulses (pulse_counts). A kind the body still fails more often than
    not is taught whatever it has of its own: generation 34 had 25 right programs of modules and passed 0 of 6, and
    with rows from every confirmed member a kind has 3 of its own long before the body passes it.
    Returns {"lessons" (planned, the kinds left to the hive among them), "made", "right", "rows", "dropped": [why],
    "left_to_the_hive": [kind], "by_kind": {kind: [right, made]},
    "failed_by_kind": {kind: {reason: n}}} (reason() gives the words), and logs the by-kind line last."""
    from training import grow
    levels = grow.body_levels() if levels is None else levels
    t0 = time.time()
    from training import exam
    plan = [(m, f"lesson:{seed}:{m}:{i}", levels.get(m, 0), None, None) for i in range(per_kind) for m in SOLVERS]
    # tasks of several parts, as practice gives them (half of it): as many parts as the body's level says
    pool = [_maker(m) for m in SOLVERS]
    k = max(2, int(levels.get("compound", 2) or 2))
    for i in range(several):
        rseed = f"lesson:{seed}:several:{i}"
        try:
            plan.append(("compound", rseed, k, exam.compound(rseed, k, pool, levels)[3].parts, None))
        except Exception as e:  # noqa: BLE001 - a part that cannot be made now (a site that does not answer): one lesson fewer
            log(f"lesson of several parts {i}: could not be made: {type(e).__name__}", flush=True)
    seen = set()
    for ln in reversed(Path(failures).read_text().splitlines() if failures and Path(failures).exists() else []):
        try:
            f = json.loads(ln)
        except ValueError:
            continue
        key = (f.get("maker"), f.get("rseed"), f.get("level", 0))
        taught = f.get("maker") in SOLVERS or (f.get("maker") == "compound" and f.get("parts") and all(p[0] in SOLVERS for p in f["parts"]))
        if taught and key not in seen and len(seen) < most_failures:
            seen.add(key)
            plan.append((f["maker"], f["rseed"], f.get("level", 0), f.get("parts"), f))
    made, right, dropped, left = [], 0, [], set()
    by_kind, failed = {}, {}
    for maker, rseed, level, parts, wrong in plan:
        if minutes and time.time() - t0 > minutes * 60:
            dropped.append("out of time")
            break
        if own is not None:
            try:
                made_now = exam.remake(maker, rseed, level, parts)
            except Exception:  # noqa: BLE001 - made below again, where the failure is said
                made_now = None
            p, n = (pulse or {}).get(made_now[1], [0, 0]) if made_now else (0, 0)
            if made_now and own.get(made_now[1], 0) >= OWN and not (n and 2 * p < n):
                left.add(made_now[1])
                continue
        les = fitting(maker, rseed, level, parts, fresh=wrong is None)
        new = rows(les, wrong)
        right += bool(les.get("ok"))
        made += new
        kind = les.get("kind") or ("several parts" if maker == "compound" else maker)
        tally = by_kind.setdefault(kind, [0, 0])
        tally[0], tally[1] = tally[0] + bool(les.get("ok")), tally[1] + 1
        if not les.get("ok"):
            why = failed.setdefault(kind, {})
            r = reason(les.get("why", ""))
            why[r] = why.get(r, 0) + 1
            dropped.append(f"{maker}: {les.get('why', '')[:160]}")
        log(f"lesson {maker} {'(a task got wrong before) ' if wrong else ''}{'right' if les.get('ok') else 'NOT taught'}: {les.get('why', '')[:150]}", flush=True)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        with open(out, "a") as f:
            for r in made:
                f.write(json.dumps(r) + "\n")
    if left:
        log(f"left to the hive (it has {OWN} or more right programs of its own): {', '.join(sorted(left))}", flush=True)
    log(by_kind_line(by_kind, failed), flush=True)
    return {"lessons": len(plan), "made": sum(n for _, n in by_kind.values()), "right": right, "rows": len(made), "dropped": dropped,
            "left_to_the_hive": sorted(left), "seconds": round(time.time() - t0), "by_kind": by_kind, "failed_by_kind": failed}


def main(argv):
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else d  # noqa: E731
    if "--show" in argv:
        les = lesson(opt("--show"), opt("--seed", "show"), int(opt("--level", 0)))
        print(les["task"], "\n\n" + les["program"], "\n" + les["answer"], "\n\nright:", les["ok"], "-", les["why"])
        return 0 if les["ok"] else 1
    owned = [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "--own-rows"]
    res = teach(opt("--seed", time.strftime("%Y%m%d%H")), int(opt("--per-kind", 1)), opt("--failures"), int(opt("--most-failures", 12)),
                opt("--out", "lessons.jsonl"), minutes=float(opt("--minutes", 0)), several=int(opt("--several", 4)),
                own=own_counts(*owned) if owned else None, pulse=pulse_counts(opt("--record"), opt("--dna", "t80")) if opt("--record") else None)
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
