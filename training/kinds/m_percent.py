"""The kind m_percent: a price that rises or falls by a percentage (at a higher level, several times) (maths).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training.kinds._common import says

KIND = "m_percent"
FAMILY = "maths"
HARD = False
ORDER = 10
LESSON_ORDER = 10
LEVELED = True


THINGS = ["laptop", "bicycle", "camera", "sofa", "guitar", "printer", "tent", "watch"]


def m_percent(r):
    p, q, up = r.randrange(120, 1900, 20), r.choice([5, 10, 12, 15, 20, 25, 30, 35]), r.random() < 0.5
    x = p * (1 + q / 100) if up else p * (1 - q / 100)
    text = f"A {r.choice(THINGS)} costs {p} dollars and the price {'rises' if up else 'falls'} by {q}%. "
    for _ in range(getattr(r, "level", 0)):  # harder: the price changes again, each time on the price before
        q, up = r.choice([5, 10, 12, 15, 20, 25]), r.random() < 0.5
        x = x * (1 + q / 100) if up else x * (1 - q / 100)
        text += f"Then it {'rises' if up else 'falls'} by {q}%. "
    return "maths", "a sum in words", text + "What is the new price?", says(round(x, 2))


def percent(task):
    m = re.search(r"costs (\d+) dollars and the price (rises|falls) by (\d+)%\.", task)
    if not m:
        return None
    steps = [(m.group(2), int(m.group(3)))] + [(a, int(b)) for a, b in re.findall(r"Then it (rises|falls) by (\d+)%\.", task)]
    lines = [f"price = {int(m.group(1))}"]
    for way, q in steps:
        lines.append(f"price = price * (1 {'+' if way == 'rises' else '-'} {q} / 100)  # {way} by {q}%")
    return "\n".join(lines) + '\nprint(f"new price: {price:.2f}")\n'


make = m_percent
lesson = percent
