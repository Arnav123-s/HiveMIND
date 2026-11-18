"""The kind h_walk: a category of books.toscrape.com walked over all its pages (hard: websites).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import CATEGORY, _fill, _says

KIND = "h_walk"
FAMILY = "hard: websites"
HARD = True
ORDER = 10
LESSON_ORDER = 160
NETWORK = True


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


make = h_walk
lesson = walk
