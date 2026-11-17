"""The kind h_prog_grid: the regions of a grid (a flood fill), joined by sides or also by corners as the task says,
three functions put to hidden tests (programs).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import random
import re

from training.kinds._common import _fill
from training.kinds._programs import module_check, program

KIND = "h_prog_grid"
FAMILY = "programs"
HARD = True
ORDER = 550

JOINS = {4: "by a side only (up, down, left, right)", 8: "by a side or by a corner (the 8 cells around it)"}


def _sizes(grid, land, join):
    seen, out = set(), []
    steps = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (join == 8 or not (a and b))]
    for y, row in enumerate(grid):
        for x, c in enumerate(row):
            if c != land or (y, x) in seen:
                continue
            seen.add((y, x))
            todo, n = [(y, x)], 0
            while todo:
                cy, cx = todo.pop()
                n += 1
                for a, b in steps:
                    ny, nx = cy + a, cx + b
                    if 0 <= ny < len(grid) and 0 <= nx < len(grid[ny]) and grid[ny][nx] == land and (ny, nx) not in seen:
                        seen.add((ny, nx))
                        todo.append((ny, nx))
            out.append(n)
    return sorted(out, reverse=True)


def _grid(r, land, h=None, w=None):
    h, w = h or r.randrange(1, 8), w or r.randrange(1, 9)
    p = r.choice([0.3, 0.45, 0.6])
    return ["".join(land if r.random() < p else "." for _ in range(w)) for _ in range(h)]


def h_prog_grid(r):
    land, join = r.choice("#XO@"), r.choice([4, 8])
    ask = _grid(r, land, r.randrange(4, 7), r.randrange(5, 9))
    sizes = _sizes(ask, land, join)
    want = [len(sizes), sizes[0] if sizes else 0]
    seed = r.random()

    def draw():
        h = random.Random(f"hidden:{seed}")
        steps = []
        for _ in range(30):
            g = _grid(h, land)
            s = _sizes(g, land, join)
            steps += [["regions", [g], len(s)], ["largest", [g], s[0] if s else 0], ["sizes", [g], s]]
        steps += [["regions", [[]], 0], ["largest", [["..."]], 0]]
        return [{"new": None, "steps": steps}]
    rows = "\n".join(ask)
    return (FAMILY, "the regions of a grid, with hidden tests",
            f"Write a Python module and save it as grid.py. A grid is a list of strings, one a row; '{land}' is land and every other "
            f"character is water. Two land cells are in the same region when they touch {JOINS[join]}, or are joined through other land "
            "cells that do. The module has three functions. 1) regions(grid) returns how many regions of land there are. 2) largest(grid) "
            "returns the number of cells of the largest region (0 when there is no land). 3) sizes(grid) returns the list of the "
            "regions' sizes, largest first. Test them yourself before you finish. Then tell me, on two lines, regions(grid) and "
            f"largest(grid) of this grid:\n{rows}\n", module_check("grid", draw, want))


SOURCE = '''LAND = __LAND__
AROUND = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (__CORNERS__ or not (a and b))]


def sizes(grid):
    seen, out = set(), []
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell != LAND or (y, x) in seen:
                continue
            seen.add((y, x))
            todo, n = [(y, x)], 0
            while todo:
                cy, cx = todo.pop()
                n += 1
                for a, b in AROUND:
                    ny, nx = cy + a, cx + b
                    if 0 <= ny < len(grid) and 0 <= nx < len(grid[ny]) and grid[ny][nx] == LAND and (ny, nx) not in seen:
                        seen.add((ny, nx))
                        todo.append((ny, nx))
            out.append(n)
    return sorted(out, reverse=True)


def regions(grid):
    return len(sizes(grid))


def largest(grid):
    return max(sizes(grid), default=0)'''


def grid(task):
    m = re.search(r"'(.)' is land.*?when they touch by a side (only|or by a corner).*?of this grid:\n(.+?)\n?$", task, re.S)
    if not m or "grid.py" not in task:
        return None
    land, how, rows = m.groups()
    rows = rows.strip().splitlines()
    tests = ["assert regions([]) == 0 and largest(['..']) == 0"]
    return program("grid", _fill(SOURCE, land=land, corners=how != "only"), tests, [f"g = {rows!r}", "print(regions(g))", "print(largest(g))"])


make = h_prog_grid
lesson = grid
