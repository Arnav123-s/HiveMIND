"""The kind h_join: a join over two small tables given in the task (hard: given data).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import _fill, _says, HARD_NAMES as NAMES

KIND = "h_join"
FAMILY = "hard: given data"
HARD = True
ORDER = 80
LESSON_ORDER = 90
LEVELED = True


ITEMS = ["pen", "notebook", "lamp", "mug", "chair", "desk", "clock", "bag"]


def h_join(r):
    items = r.sample(ITEMS, 4)
    price = {i: r.randrange(3, 60) + r.choice([0, 0.5, 0.25]) for i in items}
    who = r.sample(NAMES, 4)
    orders = [(r.choice(who), r.choice(items), r.randrange(1, 9)) for _ in range(r.randrange(12, 19) + 6 * getattr(r, "level", 0))]  # harder: more orders
    spent = {w: round(sum(q * price[i] for x, i, q in orders if x == w), 2) for w in who}
    best = max(spent, key=spent.get)
    while sorted(spent.values())[-1] == sorted(spent.values())[-2]:  # a tie has no single answer: one more order breaks it
        orders.append((best, items[0], 1))
        spent = {w: round(sum(q * price[i] for x, i, q in orders if x == w), 2) for w in who}
    item = r.choice(items)
    sold = sum(q for _, i, q in orders if i == item)
    total = round(sum(spent.values()), 2)

    def check(run, report):
        body = B._body(report)
        ok = best.lower() in body.lower() and _says(body, spent[best]) and _says(body, total) and _says(body, sold, 0.1)
        return ok, f"{best} spent most ({spent[best]}), total {total}, {sold} of {item}; all in the answer: {ok}"
    return ("hard: given data", "a join over two small tables", "Prices in dollars: " + ", ".join(f"{i} {price[i]:g}" for i in items)
            + ". Orders (customer, item, quantity): " + "; ".join(f"{w}, {i}, {q}" for w, i, q in orders)
            + f". Which customer spent the most and how much, what is the total revenue of all orders, and how many units of '{item}' "
            "were sold? Answer in four lines: 'customer: ', 'spent: ', 'revenue: ', 'units: '.", check)


def join(task):
    m = re.search(r"Prices in dollars: (.+?)\. Orders \(customer, item, quantity\): (.+?)\. Which customer spent the most.+units of '(\w+)' were sold", task, re.S)
    if not m:
        return None
    # the two tables are copied in as the task writes them, and split there: as many pieces as the task's own text
    # (T4: as lists of tuples they took 300 pieces, and every row of the kind was over a 32-bit runner's limit)
    return _fill('''price = dict(p.split() for p in __PRICES__.split(", "))
spent, units = {}, 0
for order in __ORDERS__.split("; "):
    who, item, n = order.split(", ")
    spent[who] = spent.get(who, 0) + int(n) * float(price[item])
    units += int(n) * (item == __ITEM__)
best = max(spent, key=spent.get)
print("customer:", best)
print("spent:", round(spent[best], 2))
print("revenue:", round(sum(spent.values()), 2))
print("units:", units)
''', prices=m.group(1), orders=m.group(2), item=m.group(3))


make = h_join
lesson = join
