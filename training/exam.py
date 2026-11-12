"""A fresh exam for the working hive, made by code and checked by code.

Every sitting has new tasks of the same kinds: sums, dates, units, small tables, programs to write and to mend,
facts read live from a source, a website to operate, a file to make, instructions to follow to the letter, things to
know, sentences to translate, a text to sum up. The tasks are drawn from a seed (by default the day), every answer is
checked in code against a value worked out here or read live from the source, nobody wrote them to suit the hive and
no fix was ever tried on them. So the pass rate of a sitting is an honest number, and sat again and again it shows
whether the hive is getting better, field by field, with nobody there to see.

    python training/exam.py show [--seed N]            the tasks of a sitting, without running them
    python training/exam.py sit [--seed N] [--tasks 16] [--only FIELD ...] [--empty-memory]
                                                       sit it: every task goes through the whole hive
                                                       (python -m team, risky actions never). Writes
                                                       training/reports/exams/<seed>.json and .md and one line
                                                       in training/reports/exams.jsonl
    python training/exam.py practice [--tasks 16] [--members 2]
                                                       fresh tasks that are never an exam's, done by the members
                                                       (team/solo.py) with the hive's real memory: a program two
                                                       members agreed on and the task's check confirmed stays in
                                                       the hive's library, for the next task like it
The hive sits the exam with what it has learned (a copy of its memory, so a sitting cannot change it);
--empty-memory: with none.
"""
import datetime
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from training import hive_bench as B  # noqa: E402

OUT = ROOT / "training" / "reports" / "exams"
RECORD = ROOT / "training" / "reports" / "exams.jsonl"
RUNS = ROOT / "runs" / "exam"


# ---- checks ----------------------------------------------------------------------------------------------------------
def _nums(text):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", re.sub(r"(?<=\d),(?=\d{3}\b)", "", text))]


def says(x, tol=0.006):
    """The answer states the number x (1,150 and 1150.00 are the same number)."""
    def check(run, report):
        got = _nums(B._body(report))
        return any(abs(g - x) <= tol for g in got), f"wants {x:g}; the answer's numbers: {got[:8]}"
    return check


def every(*checks):
    def check(run, report):
        res = [c(run, report) for c in checks]
        return all(ok for ok, _ in res), "; ".join(why for _, why in res)
    return check


def _json_in(text):
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except ValueError:
        return None


# ---- the makers: each gives (field, kind, task, check) from a random source ------------------------------------------
THINGS = ["laptop", "bicycle", "camera", "sofa", "guitar", "printer", "tent", "watch"]
NAMES = ["Mira", "Tomas", "Aiko", "Ravi", "Lena", "Omar", "Nadia", "Jonas"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def m_percent(r):
    p, q, up = r.randrange(120, 1900, 20), r.choice([5, 10, 12, 15, 20, 25, 30, 35]), r.random() < 0.5
    x = round(p * (1 + q / 100) if up else p * (1 - q / 100), 2)
    return ("maths", "a sum in words", f"A {r.choice(THINGS)} costs {p} dollars and the price {'rises' if up else 'falls'} by {q}%. "
            "What is the new price?", says(x))


def m_days(r):
    a = datetime.date(r.choice([2026, 2027, 2028]), r.randrange(1, 13), r.randrange(1, 28))
    b = a + datetime.timedelta(days=r.randrange(20, 200))
    f = lambda d: f"{d.day} {MONTHS[d.month - 1]} {d.year}"  # noqa: E731
    return "dates", "days between two dates", f"How many days are there from {f(a)} to {f(b)}?", says((b - a).days, 0.1)


def m_weekday(r):
    d = datetime.date(r.choice([2026, 2027, 2028]), r.randrange(1, 13), r.randrange(1, 28))
    return ("dates", "the weekday of a date", f"What day of the week is {d.day} {MONTHS[d.month - 1]} {d.year}?",
            B.has(d.strftime("%A")))


def m_units(r):
    kind = r.choice(["f", "c", "km", "kg"])
    if kind == "f":
        v = r.choice([14, 41, 59, 68, 77, 86, 95, 104, 113])
        return "units", "a unit conversion", f"What is {v} degrees Fahrenheit in Celsius? One decimal place.", says(round((v - 32) * 5 / 9, 1), 0.051)
    if kind == "c":
        v = r.choice([-10, 5, 12, 18, 23, 31, 37, 42])
        return "units", "a unit conversion", f"What is {v} degrees Celsius in Fahrenheit? One decimal place.", says(round(v * 9 / 5 + 32, 1), 0.051)
    if kind == "km":
        v = r.randrange(12, 480)
        return "units", "a unit conversion", f"How many miles are {v} kilometres? One decimal place.", says(round(v / 1.609344, 1), 0.11)
    v = r.randrange(8, 140)
    return "units", "a unit conversion", f"How many pounds are {v} kilograms? One decimal place.", says(round(v * 2.2046226, 1), 0.11)


def m_table(r):
    what, unit = r.choice([("water use", "litres"), ("steps walked", "steps"), ("bread sold", "loaves"), ("emails sent", "emails")])
    days = DAYS[:r.choice([4, 5])]
    vals = r.sample(range(40, 400, 5), len(days))
    least = r.random() < 0.5
    pick = days[vals.index(min(vals) if least else max(vals))]
    full = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday"}[pick]
    avg = round(sum(vals) / len(vals), 2)
    return ("given data", "reason over a small table", f"Daily {what} in {unit}: " + ", ".join(f"{d} {v}" for d, v in zip(days, vals))
            + f". Which day had the {'least' if least else 'most'}, and what was the daily average?",
            every(B.has(any_of=(pick, full)), says(avg, 0.051)))


def m_code(r):
    word = r.choice(["imagination", "encyclopedia", "watermelon", "architecture", "photosynthesis", "refrigerator", "university"])
    n = r.randrange(10_000, 9_999_999)
    sent = r.choice(["the quick brown fox jumps over the lazy dog", "a journey of a thousand miles begins with a single step",
                     "all that glitters is not gold", "to be or not to be that is the question"])
    kind = r.choice(["vowels", "digits", "long", "evens"])
    if kind == "vowels":
        return ("code", "write and run a program", f"Write a Python function that counts the vowels in a word and tell me how many vowels "
                f"'{word}' has.", says(sum(c in "aeiou" for c in word), 0.1))
    if kind == "digits":
        return ("code", "write and run a program", f"Write a Python function that adds up the digits of a number and tell me the result for {n}.",
                says(sum(map(int, str(n))), 0.1))
    if kind == "long":
        return ("code", "write and run a program", "Write a Python function that counts the words with more than four letters in a sentence and "
                f"tell me the count for '{sent}'.", says(sum(len(w) > 4 for w in sent.split()), 0.1))
    k = r.randrange(30, 90)
    return ("code", "write and run a program", f"Write Python code that adds up all the even numbers from 1 to {k} and tell me the total.",
            says(sum(i for i in range(1, k + 1) if i % 2 == 0), 0.1))


def m_fix(r):
    nums = r.sample(range(2, 40), 4)
    kind = r.choice(["average", "largest", "product"])
    if kind == "average":
        return ("code", "mend a program", "This Python code should print the average of the numbers but prints their total. Fix it and tell me "
                f"the output:\nnums = {nums}\nprint(sum(nums))", says(sum(nums) / len(nums), 0.006))
    if kind == "largest":
        return ("code", "mend a program", "This Python code should print the largest number but prints the smallest. Fix it and tell me the "
                f"output:\nnums = {nums}\nprint(min(nums))", says(max(nums), 0.1))
    a, b = nums[:2]
    return ("code", "mend a program", "This Python code should print the product of the two numbers but prints their sum. Fix it and tell me "
            f"the output:\na, b = {a}, {b}\nprint(a + b)", says(a * b, 0.1))


PACKAGES = ["requests", "numpy", "pandas", "flask", "django", "pytest", "rich", "httpx", "pydantic", "click", "tqdm", "scipy", "pillow", "jinja2"]
MODELS = ["google-bert/bert-base-uncased", "FacebookAI/roberta-base", "distilbert/distilbert-base-uncased", "openai-community/gpt2",
          "sentence-transformers/all-MiniLM-L6-v2", "google-t5/t5-small", "FacebookAI/xlm-roberta-base", "microsoft/deberta-v3-base"]


def m_pypi(r):
    pkg = r.choice(PACKAGES)

    def check(run, report):
        import requests
        v = requests.get(f"https://pypi.org/pypi/{pkg}/json", timeout=30).json()["info"]["version"]
        return v in B._body(report), f"latest {pkg} {v} in the answer"
    return "live facts", "a fact read from a source", f"Tell me the current version of {pkg} on PyPI.", check


def m_licence(r):
    model = r.choice(MODELS)

    def check(run, report):
        lic = str((B._hf(model).get("cardData") or {}).get("license", "")).lower()
        words = re.findall(r"[a-z]+|\d+(?:\.\d+)?", lic)
        body = B._body(report).lower()
        return bool(words) and all(w in body for w in words), f"licence {lic} in the answer"
    return "live facts", "a fact read from a source", f"Under which licence is {model} published on Hugging Face?", check


AUTHORS = {"Albert Einstein": "Albert-Einstein", "Jane Austen": "Jane-Austen", "Marilyn Monroe": "Marilyn-Monroe", "Mark Twain": "Mark-Twain",
           "Eleanor Roosevelt": "Eleanor-Roosevelt", "Steve Martin": "Steve-Martin", "Harper Lee": "Harper-Lee", "George Eliot": "George-Eliot",
           "Bob Marley": "Bob-Marley", "Elie Wiesel": "Elie-Wiesel"}


def m_born(r):
    name = r.choice(sorted(AUTHORS))

    def check(run, report):
        from bs4 import BeautifulSoup
        born = BeautifulSoup(B._get(f"https://quotes.toscrape.com/author/{AUTHORS[name]}/"), "html.parser").select_one(".author-born-date").text.strip()
        month, day, year = born.replace(",", "").split()
        body = B._body(report)
        ok = year in body and str(int(day)) in body and month[:3].lower() in body.lower()
        return ok, f"born {born}: in the answer {ok}"
    return "websites", "operate a website", f"Open quotes.toscrape.com, go to {name}'s author page and give me the date of birth.", check


CATEGORIES = ["Travel", "Mystery", "Classics", "Philosophy", "Romance", "Poetry", "Science", "Music", "Business", "Biography", "Horror", "History"]


def m_csv(r):
    cat = r.choice(CATEGORIES)

    def check(run, report):
        cs = B.files(run, ".csv")
        if not cs:
            return False, "no CSV made"
        prices = [p.text.strip().lstrip("£Â") for p in B._category(cat).select("article.product_pod .price_color")]
        text = cs[0].read_text(errors="ignore")
        got = [p for p in prices if p in text]
        return len(got) >= len(prices) - 1, f"CSV has {len(got)}/{len(prices)} prices of the {cat} page"
    return ("websites", "scrape a page to a file", f"Make a CSV with the title and price of each book listed on the first page of the {cat} "
            "category on books.toscrape.com.", check)


LISTS = {"fruits": None, "European capital cities": None, "programming languages": None, "colours": None, "musical instruments": None}
OPPOSITES = {"hot": "cold", "early": "late", "empty": "full", "heavy": "light", "ancient": "modern", "generous": ("stingy", "selfish", "mean", "greedy")}


def m_follow(r):
    kind = r.choice(["list", "one word", "capitals", "json", "sentences"])
    if kind == "list":
        n, what = r.randrange(3, 7), r.choice(sorted(LISTS))

        def check(run, report):
            items = re.findall(r"^\s*\d+[.)]\s+\S", B._body(report), re.M)
            return len(items) == n, f"{len(items)} numbered items, {n} asked"
        return "instructions", "follow a form to the letter", f"Give me exactly {n} {what} as a numbered list and nothing else.", check
    if kind == "one word":
        word = r.choice(sorted(OPPOSITES))
        want = OPPOSITES[word] if isinstance(OPPOSITES[word], tuple) else (OPPOSITES[word],)

        def check(run, report):
            body = B._body(report).strip().strip(".!\"'*` ").lower()
            return body in want, f"the answer is {body[:40]!r}; one word of {want} was asked"
        return "instructions", "follow a form to the letter", f"Answer with one word and nothing else: what is the opposite of '{word}'?", check
    if kind == "capitals":
        word = r.choice(["harbour", "lantern", "meadow", "compass", "orchard", "thunder"])

        def check(run, report):
            body = B._body(report).strip().strip(".!\"'*` ")
            return body == word.upper(), f"the answer is {body[:40]!r}; {word.upper()!r} was asked"
        return "instructions", "follow a form to the letter", f"Write the word '{word}' in capital letters and nothing else.", check
    if kind == "json":
        name, age, city = r.choice(NAMES), r.randrange(19, 80), r.choice(["Lisbon", "Oslo", "Kyoto", "Lima", "Cairo", "Perth"])

        def check(run, report):
            got = _json_in(B._body(report))
            ok = isinstance(got, dict) and got.get("name") == name and str(got.get("age")) == str(age) and got.get("city") == city and len(got) == 3
            return ok, f"the answer's JSON: {str(got)[:80]}"
        return ("instructions", "follow a form to the letter", f"Give me a JSON object with exactly the keys name, age and city for {name}, who is "
                f"{age} years old and lives in {city}. Only the JSON, nothing else.", check)
    topic, word = r.choice([("why the sky is blue", "scatter"), ("why the sea is salty", "salt"), ("why leaves fall in autumn", ("light", "cold", "chlorophyll", "water")),
                            ("why the moon has phases", ("sun", "orbit"))])
    words = word if isinstance(word, tuple) else (word,)

    def check(run, report):
        body = B._body(report)
        n = len(B._sentences(body))
        return n == 2 and any(w in body.lower() for w in words), f"{n} sentences (two asked); speaks of {words}: {any(w in body.lower() for w in words)}"
    return "instructions", "follow a form to the letter", f"Explain {topic} in exactly two sentences.", check


CAPITALS = {"Australia": "Canberra", "Canada": "Ottawa", "Brazil": "Brasília", "Turkey": "Ankara", "Switzerland": "Bern", "New Zealand": "Wellington",
            "Morocco": "Rabat", "Vietnam": "Hanoi", "Kenya": "Nairobi", "Peru": "Lima", "Norway": "Oslo", "Egypt": "Cairo", "Portugal": "Lisbon",
            "Argentina": "Buenos Aires", "Thailand": "Bangkok", "Poland": "Warsaw", "Hungary": "Budapest", "Chile": "Santiago", "Finland": "Helsinki"}
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


TONGUES = {"German": ({"library": "bibliothek", "bakery": ("bäckerei", "backerei"), "museum": "museum", "pharmacy": "apotheke"},
                      {"seven": ("sieben", "7"), "nine": ("neun", "9"), "ten": ("zehn", "10")}, {"Mondays": "montag", "Sundays": "sonntag", "Fridays": "freitag"}),
           "French": ({"library": ("bibliothèque", "bibliotheque"), "bakery": "boulangerie", "museum": ("musée", "musee"), "pharmacy": "pharmacie"},
                      {"seven": ("sept", "7"), "nine": ("neuf", "9"), "ten": ("dix", "10")}, {"Mondays": "lundi", "Sundays": "dimanche", "Fridays": "vendredi"}),
           "Spanish": ({"library": "biblioteca", "bakery": ("panadería", "panaderia"), "museum": "museo", "pharmacy": "farmacia"},
                       {"seven": ("siete", "7"), "nine": ("nueve", "9"), "ten": ("diez", "10")}, {"Mondays": "lunes", "Sundays": "domingo", "Fridays": "viernes"}),
           "Italian": ({"library": "biblioteca", "bakery": ("panetteria", "panificio", "forno"), "museum": "museo", "pharmacy": "farmacia"},
                       {"seven": ("sette", "7"), "nine": ("nove", "9"), "ten": ("dieci", "10")}, {"Mondays": ("lunedì", "lunedi"), "Sundays": "domenic", "Fridays": ("venerdì", "venerdi")})}


def m_translate(r):
    lang = r.choice(sorted(TONGUES))
    places, hours, days = TONGUES[lang]
    place, hour, day = r.choice(sorted(places)), r.choice(sorted(hours)), r.choice(sorted(days))
    verb = r.choice(["opens", "closes"])
    tup = lambda v: v if isinstance(v, tuple) else (v,)  # noqa: E731

    def check(run, report):
        low = B._body(report).lower()
        hits = [any(w in low for w in tup(v)) for v in (places[place], hours[hour], days[day])]
        return all(hits) and place not in low, f"place, hour and day in {lang}: {hits}; the English word left in: {place in low}"
    return "languages", "translate a sentence", f"Translate into {lang}: 'The {place} {verb} at {hour} on {day}.'", check


def m_summary(r):
    who, what = r.choice(NAMES), r.choice(["bridge", "library", "swimming pool", "market hall"])
    year, months, cost = r.randrange(1921, 1989), r.randrange(4, 15), r.choice(["2.6", "3.4", "4.8", "5.1"])
    street = r.choice(["Elm Street", "Mill Lane", "Harbour Road", "Station Street"])
    text = (f"The Ridgeway {what}, built in {year}, was closed in March for repairs after inspectors found cracks in two support beams. "
            f"The city expects the work to take {months} months and cost {cost} million dollars. Until it reopens, visitors are sent to the "
            f"{street} entrance, says the city engineer {who} Hartmann.")

    def check(run, report):
        body = B._body(report)
        n = len(B._sentences(body))
        ok = n == 1 and what.split()[-1] in body.lower() and any(w in body.lower() for w in ("repair", "closed", "close", "crack"))
        return ok, f"{n} sentence(s); names the {what} and the closing or the repairs: {ok}"
    return "writing", "sum up a text", f"Give me a one-sentence summary of this: {text}", check


def m_steps(r):
    a, b = r.randrange(12, 60), r.randrange(3, 12)
    word = r.choice(["lantern", "harvest", "pocket", "window", "garden"])
    c = CAPITALS[(country := r.choice(sorted(CAPITALS)))]

    def check(run, report):
        body = B._body(report)
        parts = re.split(r"(?m)^\s*\**([ABC])[).:\*]", body)
        got = {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}
        ok = (set(got) == {"A", "B", "C"} and any(abs(x - a * b) < 0.1 for x in _nums(got["A"])) and word[::-1] in got["B"].lower()
              and (c.lower() in got["C"].lower() or c.replace("í", "i").lower() in got["C"].lower()))
        return ok, f"three labelled answers {sorted(got)}; each right: {ok}"
    return ("understanding", "several orders in one message", f"Do these three things and label the answers A, B and C, each on its own line: "
            f"first multiply {a} by {b}; then write the word '{word}' backwards; then name the capital of {country}.", check)


MAKERS = [m_percent, m_days, m_weekday, m_units, m_table, m_code, m_fix, m_pypi, m_licence, m_born, m_csv, m_follow, m_follow, m_know, m_know,
          m_translate, m_summary, m_steps]


def exam(seed, n=16, only=()):
    """The tasks of one sitting: [(id, field, kind, task, check)]. The same seed gives the same exam."""
    r = random.Random(seed)
    makers = [m for m in MAKERS]
    r.shuffle(makers)
    out = []
    for i, make in enumerate(makers):
        for again in range(8):  # the same task twice in one sitting tells nothing: drawn again
            field, kind, task, check = make(random.Random(f"{seed}:{make.__name__}:{i}:{again}"))
            if task not in [t[3] for t in out]:
                break
        if only and field not in only:
            continue
        out.append((f"e{seed}_{len(out):02d}", field, kind, task, check))
        if len(out) >= n:
            break
    return out


# ---- sitting it ------------------------------------------------------------------------------------------------------
def _memory(empty):
    """Where the hive's memory is for a sitting: a copy of what it has learned (lessons, policy, profile), so a
    sitting cannot change it; or nothing."""
    home = Path(tempfile.mkdtemp(prefix="exam-memory-"))
    if not empty:
        from team import memory
        for name in ("lessons.jsonl", "policy.json", "profile.md", "solved.jsonl"):
            if (memory.HOME / name).exists():
                shutil.copyfile(memory.HOME / name, home / name)
    return home


def sit_one(tag, tid, task, check, memory_home, timeout=2400):
    run = RUNS / tag / tid
    if (run / "exam.json").exists():
        return json.loads((run / "exam.json").read_text())
    run.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-m", "team", task, "--approve", "never", "--run-dir", str(run)], cwd=ROOT,
                           env=dict(os.environ, AGENT_TEAM_HOME=str(memory_home)), capture_output=True, text=True, timeout=timeout)
        note = "" if p.returncode == 0 else f"exit {p.returncode}: {p.stderr.strip().splitlines()[-1][:200] if p.stderr.strip() else ''}"
    except subprocess.TimeoutExpired:
        note = f"timed out after {timeout} s"
    report = (run / "REPORT.md").read_text() if (run / "REPORT.md").exists() else ""
    try:
        ok, why = check(run, report)
    except Exception as e:  # noqa: BLE001 - a check that cannot be made is a failed task, with the reason
        ok, why = False, f"check failed: {type(e).__name__}: {e}"
    res = {"id": tid, "ok": bool(ok), "why": why, "seconds": round(time.time() - t0), "note": note, "answer": B._body(report)[:400]}
    (run / "exam.json").write_text(json.dumps(res, indent=1))
    return res


def sit(seed, n=16, only=(), empty_memory=False, log=print):
    tag, home, rows, t0 = f"exam_{seed}", _memory(empty_memory), [], time.time()
    for tid, field, kind, task, check in exam(seed, n, only):
        r = sit_one(tag, tid, task, check, home) | {"field": field, "kind": kind, "task": task}
        rows.append(r)
        log(f"{'PASS' if r['ok'] else 'FAIL'} {tid} [{field}: {kind}] {r['seconds']}s - {r['why']} {r['note']}", flush=True)
    by = {}
    for r in rows:
        p, m = by.get(r["field"], (0, 0))
        by[r["field"]] = (p + r["ok"], m + 1)
    try:
        code = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        code = ""
    line = {"seed": seed, "when": time.strftime("%Y-%m-%d %H:%M"), "passed": sum(r["ok"] for r in rows), "tasks": len(rows),
            "by_field": {k: list(v) for k, v in sorted(by.items())}, "minutes": round((time.time() - t0) / 60), "code": code,
            "memory": "none" if empty_memory else "its own"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{seed}.json").write_text(json.dumps({"summary": line, "tasks": rows}, indent=1))
    md = [f"# The hive's exam {seed}", "", f"{line['passed']} of {line['tasks']} tasks passed in {line['minutes']} minutes "
          f"(code {code}, memory: {line['memory']}).", "", "| field | kind | pass | time | the check |", "|---|---|---|---|---|"]
    md += [f"| {r['field']} | {r['kind']} | {'✅' if r['ok'] else '❌'} | {r['seconds']} s | {r['why']} {r['note']} |" for r in rows]
    (OUT / f"{seed}.md").write_text("\n".join(md) + "\n")
    with open(RECORD, "a") as f:
        f.write(json.dumps(line) + "\n")
    return line


def practice(seed, n=16, only=(), members=2, log=print):
    """Practice: fresh tasks that are never an exam's (their seeds start at ten million), done by the members with the
    hive's real memory, so what two members agree on stays in its library (team/solo.py); then each task's own check
    says whether that program was right, and a wrong one is taken out again. Nothing is written to the exam's record."""
    from team import memory, solo
    tag, rows = f"practice_{seed}", []
    os.environ["AGENT_TEAM_SOLO"] = str(members)
    had = len(solo.solved())
    for tid, field, kind, task, check in exam(seed, n, only):
        r = sit_one(tag, tid, task, check, memory.HOME)
        solo.judge(task, r["ok"])
        rows.append(r)
        log(f"{'RIGHT' if r['ok'] else 'not right'} {tid} [{field}: {kind}] {r['seconds']}s", flush=True)
    now = solo.solved()
    return {"practice": seed, "tasks": len(rows), "right": sum(r["ok"] for r in rows), "library_before": had, "library_now": len(now),
            "confirmed_in_library": sum(bool(x.get("checked")) for x in now)}


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    seed = opt("--seed", (datetime.date.today() - datetime.date(2026, 1, 1)).days)
    only = tuple(argv[argv.index("--only") + 1:]) if "--only" in argv else ()
    only = tuple(a for a in only if not a.startswith("--"))
    cmd = argv[0] if argv else ""
    if cmd == "show":
        for tid, field, kind, task, _ in exam(seed, opt("--tasks", 16), only):
            print(f"{tid} [{field}: {kind}]\n    {task}\n")
    elif cmd == "practice":
        print(json.dumps(practice(opt("--seed", 10_000_000 + int(time.time() // 3600)), opt("--tasks", 16), only, opt("--members", 2))))
    elif cmd == "sit":
        print(json.dumps(sit(seed, opt("--tasks", 16), only, "--empty-memory" in argv)))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
