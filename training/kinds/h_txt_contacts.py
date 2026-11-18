"""The kind h_txt_contacts: the email addresses and phone numbers in a messy message, found and listed (hard: text).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import _fill, _says, HARD_NAMES as NAMES

KIND = "h_txt_contacts"
FAMILY = "hard: text"
HARD = True
ORDER = 400

DOMAINS = ["example.org", "mail.example.com", "shop.example.net", "uni.example.edu"]
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
FILLER = ["Thanks again for last week.", "The order #{n} shipped on 2026-0{m}-1{d}.", "Room {n} is free after 3 pm.",
          "Bring the {n} forms, please!", "See you soon;", "Ask at the front desk (open 9-17)."]


def _phone(r, digits):
    a, b, c = digits[:3], digits[3:6], digits[6:]
    return r.choice([f"{a}-{b}-{c}", f"({a}) {b}-{c}", f"{a}.{b}.{c}", f"({a}){b}-{c}"])


def h_txt_contacts(r):
    who = r.sample(NAMES, r.randrange(4, 7))
    emails = sorted({f"{w.lower()}{r.choice(['', '.', '_'])}{r.choice('abkmrt')}{r.choice(['', str(r.randrange(2, 99))])}@{r.choice(DOMAINS)}"
                     for w in who})
    phones = sorted({f"{r.randrange(200, 999)}{r.randrange(200, 999)}{r.randrange(1000, 9999)}" for _ in range(r.randrange(3, 6))})
    bits = []
    for e in emails + r.sample(emails, 2):  # two of them written twice, in other letters
        e = e if r.random() < 0.5 else r.choice([e.upper(), e.capitalize(), e.split("@")[0] + "@" + e.split("@")[1].upper()])
        bits.append(r.choice(["Write to {} for the forms.", "Contact: {}.", "cc {}", "or mail <{}>,", "({}) wrote back."]).format(e))
    for p in phones + r.sample(phones, 1):  # one number written twice, maybe another way
        bits.append(r.choice(["Call {} after noon.", "Phone: {},", "tel. {}", "Ring {} if late!"]).format(_phone(r, p)))
    for f in r.sample(FILLER, 4):
        bits.append(f.format(n=r.randrange(10000, 99999), m=r.randrange(1, 10), d=r.randrange(0, 10)))
    r.shuffle(bits)
    text = " ".join(bits)

    def check(run, report):
        body = B._body(report)
        got = [ln.strip().strip("-*` ").lower() for ln in body.splitlines() if EMAIL.fullmatch(ln.strip().strip("-*` "))]
        ok = got == emails and any(re.match(r"\W*phones\W", ln.strip(), re.I) and _says(ln, len(phones), 0.1) for ln in body.splitlines())
        return ok, f"wants {len(emails)} emails {emails} in order and phones: {len(phones)}; got {got}"
    return ("hard: text", "emails and phones found in a messy message", "Here is a message:\n" + text + "\nList every distinct email "
            "address in it, in lower case, sorted, one per line and nothing else on the line (two addresses that differ only in "
            "capital letters are the same). Then write a line 'phones: ' with the number of distinct phone numbers in it (two are "
            "the same when their digits are the same, however they are written).", check)


def contacts(task):
    m = re.search(r"Here is a message:\n(.*?)\nList every distinct email", task, re.S)
    if not m:
        return None
    return _fill(r'''import re
t = __TEXT__
for e in sorted({e.lower() for e in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", t)}):
    print(e)
print("phones:", len({re.sub(r"\D", "", p) for p in re.findall(r"(?<!\d)\(?\d{3}\)?[ .-]?\d{3}[.-]\d{4}(?!\d)", t)}))
''', text=m.group(1))


make = h_txt_contacts
lesson = contacts
