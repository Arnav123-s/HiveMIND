"""The kind m_fix: a small program to mend (code).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training.kinds._common import says

KIND = "m_fix"
FAMILY = "code"
HARD = False
ORDER = 70
LESSON_ORDER = 60


def m_fix(r):
    nums = r.sample(range(2, 40), 4)
    kind = r.choice(["average", "largest", "product"])
    if kind == "average":
        return ("code", "mend a program", "This Python code should print the average of the numbers but prints their total. Fix it and tell me "
                f"the output:\nnums = {nums}\nprint(sum(nums))", says(sum(nums) / len(nums), 0.006))
    if kind == "largest":
        return ("code", "mend a program", "This Python code should print the largest number but prints the smallest. Fix it and tell me the "
                f"output:\nnums = {nums}\nprint(min(nums))", says(max(nums), 0.1))
    a, b = nums[:2]
    return ("code", "mend a program", "This Python code should print the product of the two numbers but prints their sum. Fix it and tell me "
            f"the output:\na, b = {a}, {b}\nprint(a + b)", says(a * b, 0.1))


def mend(task):
    m = re.search(r"Fix it and tell me the output:\n(.+)$", task, re.S)
    if not m:
        return None
    given = m.group(1).strip()
    for asked, wrong, right in (("print the average", "print(sum(nums))", "print(sum(nums) / len(nums))  # the average, not the total"),
                                ("print the largest", "print(min(nums))", "print(max(nums))  # the largest, not the smallest"),
                                ("print the product", "print(a + b)", "print(a * b)  # the product, not the sum")):
        if asked in task and wrong in given:
            return given.replace(wrong, right) + "\n"
    return None


make = m_fix
lesson = mend
