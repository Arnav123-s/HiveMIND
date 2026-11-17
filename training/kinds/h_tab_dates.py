"""The kind h_tab_dates: the rows of a CSV given in the task, its dates written in several forms, kept within a range
of dates and saved with one form (hard: tables).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
it has no lesson: it is held out, never practised or taught, so what the hive scores on it is what carries over.
"""
import datetime

from training import hive_bench as B
from training.kinds._common import _says
from training.kinds import _tab

KIND = "h_tab_dates"
FAMILY = "hard: tables"
HARD = True
ORDER = 370
HELD_OUT = True

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# (file, the key column, its prefix, the column summed)
THEMES = [("payments.csv", "id", "P", "amount"), ("shipments.csv", "ref", "S", "weight"), ("bookings.csv", "code", "B", "guests")]


def _written(d, form):
    return [d.isoformat(), f"{d.day:02d}/{d.month:02d}/{d.year}", f"{d.day} {MON[d.month - 1]} {d.year}"][form]


def h_tab_dates(r):
    name, key, prefix, col = r.choice(THEMES)
    out = r.choice(["in_range.csv", "window.csv", "selected.csv"])
    start = datetime.date(2026, r.randrange(1, 9), r.randrange(1, 29))
    span = r.randrange(60, 120)
    lo = start + datetime.timedelta(days=r.randrange(10, 30))
    hi = lo + datetime.timedelta(days=r.randrange(20, 45))
    data = []
    for i in r.sample(range(100, 1000), r.randrange(12, 19)):
        d = start + datetime.timedelta(days=r.randrange(span))
        data.append((f"{prefix}{i}", d, r.choice([0, 1, 2]), r.randrange(1, 500) if col != "guests" else r.randrange(1, 9)))
    data += [(f"{prefix}{1000 + j}", d, r.choice([1, 2]), r.randrange(1, 9)) for j, d in enumerate((lo, hi))]  # the ends are kept
    r.shuffle(data)
    kept = [x for x in data if lo <= x[1] <= hi]
    total = sum(x[3] for x in kept)
    want = [[k, d.isoformat(), str(v)] for k, d, _, v in kept]
    text = f"{key},date,{col}\n" + "\n".join(f"{k},{_written(d, f)},{v}" for k, d, f, v in data)

    def check(run, report):
        got = _tab.rows(run, out)
        if got is None:
            return False, f"no {out} saved"
        ok = (_tab.head(got, [key, "date", col]) and len(got) == len(want) + 1
              and all(len(g) == 3 and g[:2] == w[:2] and _tab.near(g[2], int(w[2]), 0.01) for g, w in zip(got[1:], want))
              and _says(B._body(report), total, 0.1))
        return ok, f"{out}: {len(got) - 1} rows against {len(want)} kept, total {col} {total} in the answer: {ok}"
    return ("hard: tables", "rows kept within a range of dates written in several forms", _tab.given(name, text,
            f"Its dates are written in three forms: YYYY-MM-DD, DD/MM/YYYY (the day first) and D Mon YYYY. Save a file {out} with the "
            f"columns {key},date,{col}, keeping in the order of the file only the rows dated from {lo.isoformat()} to {hi.isoformat()}, "
            f"both days included, with every date written as YYYY-MM-DD. Then tell me the total {col} of the rows kept."), check)


make = h_tab_dates
lesson = None
