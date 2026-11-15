"""Several tasks given in one message, and their answers read back apart.

The body's lessons grow harder by putting tasks together (training/exam.compound): a program that must do two or
three different things at once cannot be one remembered answer, it has to be built from what each part needs. Such
a message names its parts PART A, PART B, ... and asks for the answers under the same headings. This file reads
both sides apart: the parts of the task, and the answer's piece for each part. Needs nothing but Python.
"""
import re

LETTERS = "ABCDEFGH"
HEAD = ("Do these {n} things in one program. Print the answers under the headings {heads}: each heading alone on its own line, "
        "and that part's answer on the lines below it, exactly as the part asks for it.")
_TASK = re.compile(r"(?m)^PART ([A-H]): ")
_ANSWER = re.compile(r"(?mi)^[ \t]*[#*_`]*[ \t]*PART[ \t]+([A-H])\b[ \t]*[*_`]*[ \t]*[:.\-]?[ \t]*[*_`]*[ \t]*")


def join(tasks):
    """One message from several tasks."""
    heads = ", ".join(f"'PART {LETTERS[i]}'" for i in range(len(tasks)))
    return HEAD.format(n=len(tasks), heads=heads) + "\n\n" + "\n\n".join(f"PART {LETTERS[i]}: {t}" for i, t in enumerate(tasks))


def of_task(task):
    """{letter: that part's task} of a message made by join(), or {} for any other task."""
    if not task.startswith(HEAD.split("{")[0]):
        return {}
    hits = list(_TASK.finditer(task))
    return {m.group(1): task[m.end():(hits[i + 1].start() if i + 1 < len(hits) else len(task))].strip() for i, m in enumerate(hits)}


def of_answer(answer):
    """{letter: the answer's piece under that heading}. A heading may stand alone on its line or be followed by the
    answer on the same line ('PART A: 42'); the first piece under a heading counts."""
    hits = list(_ANSWER.finditer(answer or ""))
    out = {}
    for i, m in enumerate(hits):
        out.setdefault(m.group(1).upper(), answer[m.end():(hits[i + 1].start() if i + 1 < len(hits) else len(answer))].strip())
    return out
