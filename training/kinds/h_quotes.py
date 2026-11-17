"""The kind h_quotes: the first pages of quotes.toscrape.com walked and counted into a file (hard: websites).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
it has no lesson: the hive is never shown it done.
"""
import json

from training import hive_bench as B
from training.kinds._common import _file

KIND = "h_quotes"
FAMILY = "hard: websites"
HARD = True
ORDER = 20
HELD_OUT = True
NETWORK = True


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


make = h_quotes
lesson = None
