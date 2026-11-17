"""The kind h_prog_wrap: text wrapped to a width and justified, with the task's own rules for a word too long and for
where the extra spaces go, two functions put to hidden tests (programs).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed. It is
held out: never practised or taught. `solution` writes a right program for a task of it, used only by the tests
(tests/test_k2c.py) to prove the check passes a right module and fails a wrong one.
"""
import random
import re

from training.kinds._common import _fill
from training.kinds._programs import module_check, program

KIND = "h_prog_wrap"
FAMILY = "programs"
HARD = True
ORDER = 570
HELD_OUT = True

LONG = {"cut": "it is cut into pieces of exactly width characters (the last piece may be shorter), each piece then wrapped as a word",
        "keep": "it stands on a line of its own, uncut, longer than the width"}
EXTRA = {"left": "the gaps on the left get one more space than those on the right",
         "right": "the gaps on the right get one more space than those on the left"}
WORDS = ["a", "an", "the", "river", "stone", "amber", "cloud", "ember", "field", "grain", "harbor", "island", "juniper",
         "lantern", "meadow", "north", "orchard", "pebble", "quiet", "remarkable", "sea", "to", "of", "extraordinarily", "unbelievable"]


def _wrap(text, width, long):
    words = []
    for w in text.split():
        if len(w) > width and long == "cut":
            words += [w[i:i + width] for i in range(0, len(w), width)]
        else:
            words.append(w)
    lines = []
    for w in words:
        if lines and len(lines[-1]) + 1 + len(w) <= width:
            lines[-1] += " " + w
        else:
            lines.append(w)
    return lines


def _justify(text, width, long, extra):
    lines = _wrap(text, width, long)
    out = []
    for ln in lines[:-1]:
        ws = ln.split(" ")
        if len(ws) == 1:
            out.append(ln.ljust(width))
            continue
        gaps, spare = len(ws) - 1, width - sum(map(len, ws))
        sizes = [spare // gaps + (1 if i < spare % gaps else 0) for i in range(gaps)]
        if extra == "right":
            sizes = sizes[::-1]
        out.append("".join(w + " " * s for w, s in zip(ws, sizes + [0])))
    return out + lines[-1:]


def _text(r, n=None):
    return " ".join(r.choice(WORDS) for _ in range(n or r.randrange(1, 16)))


def h_prog_wrap(r):
    long, extra = r.choice(sorted(LONG)), r.choice(sorted(EXTRA))
    width = r.randrange(10, 21)
    ask = _text(r, r.randrange(8, 14))
    want = [_wrap(ask, width, long), _justify(ask, width, long, extra)]
    seed = r.random()

    def draw():
        h = random.Random(f"hidden:{seed}")
        steps = []
        for _ in range(30):
            t, w = _text(h), h.randrange(6, 25)
            steps += [["wrap", [t, w], _wrap(t, w, long)], ["justify", [t, w], _justify(t, w, long, extra)]]
        return [{"new": None, "steps": steps}]
    return (FAMILY, "text wrapped and justified, with hidden tests",
            "Write a Python module and save it as wrap.py. It has two functions. 1) wrap(text, width) splits the text into words at "
            "white space and returns the list of lines: each line takes as many of the next words as fit in width characters with "
            f"one space between them. When a word alone is longer than the width, {LONG[long]}. 2) justify(text, width) returns the "
            "lines of wrap(text, width) with every line but the last made exactly width characters long by widening the gaps between "
            f"its words as evenly as can be; when the gaps cannot all be the same, {EXTRA[extra]}. A line of one word is filled with "
            "spaces on its right; a line already longer than the width is left as it is; the last line is left as wrap made it. Test "
            "both yourself before you finish. Then tell me, on two lines, the value of wrap(text, width) and of justify(text, width) "
            f"for text = {ask!r} and width = {width}.", module_check("wrap", draw, want))


SOURCE = '''CUT = __CUT__  # a word longer than the width is cut into pieces
EXTRA_LEFT = __LEFT__  # the extra spaces go to the gaps on the left


def wrap(text, width):
    words = []
    for w in text.split():
        if len(w) > width and CUT:
            words += [w[i:i + width] for i in range(0, len(w), width)]
        else:
            words.append(w)
    lines = []
    for w in words:
        if lines and len(lines[-1]) + 1 + len(w) <= width:
            lines[-1] += " " + w
        else:
            lines.append(w)
    return lines


def justify(text, width):
    lines = wrap(text, width)
    out = []
    for line in lines[:-1]:
        words = line.split(" ")
        if len(words) == 1:
            out.append(line.ljust(width))
            continue
        gaps = len(words) - 1
        spare = width - sum(len(w) for w in words)
        sizes = [spare // gaps + (1 if i < spare % gaps else 0) for i in range(gaps)]
        if not EXTRA_LEFT:
            sizes.reverse()
        out.append("".join(w + " " * s for w, s in zip(words, sizes + [0])))
    return out + lines[-1:]'''


def solution(task):
    m = re.search(r"longer than the width, it (is cut|stands).*?the gaps on the (left|right) get one more.*?for text = (.+) and width = (\d+)\.\s*$", task, re.S)
    if not m or "wrap.py" not in task:
        return None
    tests = ["assert wrap('a bb ccc', 4) == ['a bb', 'ccc']"]
    prints = [f"text, width = {m.group(3)}, {m.group(4)}", "print(wrap(text, width))", "print(justify(text, width))"]
    return program("wrap", _fill(SOURCE, cut=m.group(1) == "is cut", left=m.group(2) == "left"), tests, prints)


make = h_prog_wrap
lesson = None
