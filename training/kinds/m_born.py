"""The kind m_born: an author's date of birth on quotes.toscrape.com (websites).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import FIND_AUTHOR, _fill

KIND = "m_born"
FAMILY = "websites"
HARD = False
ORDER = 100
LESSON_ORDER = 130
NETWORK = True


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


def born(task):
    m = re.search(r"go to (.+?)'s author page", task)
    return m and _fill(FIND_AUTHOR + 'print("born:", born)\n', name=m.group(1))


make = m_born
lesson = born
