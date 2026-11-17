"""The kind m_table: a small table of a week: the least or most, the average (at a higher level, more) (given data).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import _fill, _line_says, every, says

KIND = "m_table"
FAMILY = "given data"
HARD = False
ORDER = 50
LESSON_ORDER = 40
LEVELED = True


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def m_table(r):
    lv = getattr(r, "level", 0)
    what, unit = r.choice([("water use", "litres"), ("steps walked", "steps"), ("bread sold", "loaves"), ("emails sent", "emails")])
    days = DAYS[:r.choice([6, 7] if lv else [4, 5])]
    vals = r.sample(range(40, 400, 5), len(days))
    least = r.random() < 0.5
    pick = days[vals.index(min(vals) if least else max(vals))]
    full = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday"}[pick]
    avg = round(sum(vals) / len(vals), 2)
    task = f"Daily {what} in {unit}: " + ", ".join(f"{d} {v}" for d, v in zip(days, vals)) + f". Which day had the {'least' if least else 'most'}, and what was the daily average?"
    if not lv:
        return "given data", "reason over a small table", task, every(B.has(any_of=(pick, full)), says(avg, 0.051))
    # harder: a longer table and two more things asked of it
    over = sum(v > avg for v in vals)
    return ("given data", "reason over a small table", task[:-1] + ", what is the total, and on how many days was it above the average? "
            "Answer in four lines: 'day: ', 'average: ', 'total: ', 'above: '.",
            every(B.has(any_of=(pick, full)), says(avg, 0.051), says(sum(vals), 0.1), _line_says("above", over)))


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


make = m_table
lesson = small_table
