"""The kind m_csv: a page of books.toscrape.com scraped to a CSV file (websites).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import CATEGORY, _fill

KIND = "m_csv"
FAMILY = "websites"
HARD = False
ORDER = 110
LESSON_ORDER = 140
NETWORK = True


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


make = m_csv
lesson = csv_page
