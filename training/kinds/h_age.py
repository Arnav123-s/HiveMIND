"""The kind h_age: a date of birth read from a site and a date sum on it (hard: websites).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import datetime
import re

from training import hive_bench as B
from training.kinds._common import FIND_AUTHOR, MONTHS, _fill, _says

KIND = "h_age"
FAMILY = "hard: websites"
HARD = True
ORDER = 50
LESSON_ORDER = 180
NETWORK = True


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


make = h_age
lesson = age
