"""What the kinds of task share: the checks that read numbers out of an answer, a few lists more than one kind draws
from, and the beginnings of the lessons' programs that more than one kind's lesson starts with.

A kind's own constants stay in its own file (training/kinds/<kind>.py); only what two kinds or more use is here.
"""
import json
import re

from training import hive_bench as B


# ---- checks ----------------------------------------------------------------------------------------------------------
def _nums(text):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", re.sub(r"(?<=\d),(?=\d{3}\b)", "", text))]


def says(x, tol=0.006):
    """The answer states the number x (1,150 and 1150.00 are the same number)."""
    def check(run, report):
        got = _nums(B._body(report))
        return any(abs(g - x) <= tol for g in got), f"wants {x:g}; the answer's numbers: {got[:8]}"
    return check


def _line_says(label, x, tol=0.1):
    """The answer's line that begins with the label states the number x."""
    def check(run, report):
        got = [g for ln in B._body(report).splitlines() if re.match(rf"\W*{label}\b", ln.strip(), re.I) for g in _nums(ln)]
        return any(abs(g - x) <= tol for g in got), f"wants {label}: {x:g}; that line's numbers: {got[:4]}"
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


# ---- the hard kinds' checks -----------------------------------------------------------------------------------------
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


# ---- lists more than one kind draws from ----------------------------------------------------------------------------
NAMES = ["Mira", "Tomas", "Aiko", "Ravi", "Lena", "Omar", "Nadia", "Jonas"]


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


CAPITALS = {"Australia": "Canberra", "Canada": "Ottawa", "Brazil": "Brasília", "Turkey": "Ankara", "Switzerland": "Bern", "New Zealand": "Wellington",
            "Morocco": "Rabat", "Vietnam": "Hanoi", "Kenya": "Nairobi", "Peru": "Lima", "Norway": "Oslo", "Egypt": "Cairo", "Portugal": "Lisbon",
            "Argentina": "Buenos Aires", "Thailand": "Bangkok", "Poland": "Warsaw", "Hungary": "Budapest", "Chile": "Santiago", "Finland": "Helsinki"}


HARD_NAMES = ["Mira", "Tomas", "Aiko", "Ravi", "Lena", "Omar", "Nadia", "Jonas", "Ines", "Pavel", "Sofia", "Kofi"]  # the hard kinds' names (more of them)


HARD_PACKAGES = ["requests", "numpy", "pandas", "flask", "django", "pytest", "rich", "httpx", "pydantic", "click", "tqdm", "scipy", "pillow", "jinja2",
            "sqlalchemy", "attrs", "black", "ruff", "mypy", "fastapi", "uvicorn", "aiohttp", "boto3", "celery", "lxml", "markdown", "networkx", "sympy"]


# ---- the lessons' programs: what several begin with ------------------------------------------------------------------
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


CATEGORY = HEAD + '''
# a category is reached from the site's first page, by the link whose text is its name
site = "https://books.toscrape.com/"
link = next(a for a in page(site).select(".side_categories a") if a.text.strip() == __CATEGORY__)
url = urljoin(site, link["href"])
'''


PYPI = '''import requests
from datetime import date

headers = {"User-Agent": "hive/1.0"}


def latest(package):
    """The latest version on PyPI and the date it was released."""
    data = requests.get(f"https://pypi.org/pypi/{package}/json", headers=headers, timeout=30).json()
    version = data["info"]["version"]
    return version, data["releases"][version][0]["upload_time"][:10]
'''


DATE = r"(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})"
