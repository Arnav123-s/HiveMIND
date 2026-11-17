"""The kind m_units: a unit conversion (degrees, miles, pounds) (units).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training.kinds._common import says

KIND = "m_units"
FAMILY = "units"
HARD = False
ORDER = 40
LESSON_ORDER = 150


def m_units(r):
    kind = r.choice(["f", "c", "km", "kg"])
    if kind == "f":
        v = r.choice([14, 41, 59, 68, 77, 86, 95, 104, 113])
        return "units", "a unit conversion", f"What is {v} degrees Fahrenheit in Celsius? One decimal place.", says(round((v - 32) * 5 / 9, 1), 0.051)
    if kind == "c":
        v = r.choice([-10, 5, 12, 18, 23, 31, 37, 42])
        return "units", "a unit conversion", f"What is {v} degrees Celsius in Fahrenheit? One decimal place.", says(round(v * 9 / 5 + 32, 1), 0.051)
    if kind == "km":
        v = r.randrange(12, 480)
        return "units", "a unit conversion", f"How many miles are {v} kilometres? One decimal place.", says(round(v / 1.609344, 1), 0.11)
    v = r.randrange(8, 140)
    return "units", "a unit conversion", f"How many pounds are {v} kilograms? One decimal place.", says(round(v * 2.2046226, 1), 0.11)


def units(task):
    for pat, expr, unit in ((r"What is (-?\d+) degrees Fahrenheit in Celsius", "(v - 32) * 5 / 9", "degrees Celsius"),
                            (r"What is (-?\d+) degrees Celsius in Fahrenheit", "v * 9 / 5 + 32", "degrees Fahrenheit"),
                            (r"How many miles are (\d+) kilometres", "v / 1.609344", "miles"),
                            (r"How many pounds are (\d+) kilograms", "v * 2.2046226", "pounds")):
        m = re.search(pat, task)
        if m:
            return f"v = {int(m.group(1))}\nprint(f\"{{{expr}:.1f}} {unit}\")\n"
    return None


make = m_units
lesson = units
