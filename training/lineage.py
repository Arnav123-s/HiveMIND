"""How the body multiplies (Arnav, 2026-11-14): cells are not replaced, they have children, and the body keeps
growing. No gate decides it and no ledger of who was right on what steers it: the body grows every generation.

    python3 training/lineage.py plan <generation> <dna> [organs as a JSON list]    the children to grow, as JSON

A child starts as an exact copy of its parent's weight edit (training/grow.py --parent) and is trained further on
all the hive's checked work: its right answers, its right-against-wrong pairs and its corrected failures. So each
child is a degree away from its parent: it keeps what the parent learned, mistakes and corrections included, and
goes on from there.

It grows the way Fibonacci's rabbits do: a cell born in the last generation is young and has no child yet; every
other cell has one child each generation. Per organ: 1, 2, 3, 5, 8, ... (in a generation where every cell is
young, they all count as grown, so the line never stands still). Two limits are the runners', not the idea's: at
most MOST_CHILDREN children a generation (each trains on its own runner, for hours) and at most MOST_CELLS cells in
the body (each is loaded beside the DNA in the same server). When the body is full, the oldest cells whose line
goes on in a descendant give up their place: a child holds what its parent learned, so nothing is lost.

Only names are read here, from files this repository wrote; it needs nothing but Python.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BODY = ROOT / "cells" / "body.json"
ORGANS = ("sources", "code", "data", "words")
MOST_CHILDREN = 8
MOST_CELLS = 24
CELL = r"g\d{1,6}(?:sources|code|data|words)\d{0,2}"


def organ_of(cell):
    """'g24code2' -> 'code'."""
    m = re.fullmatch(r"g\d{1,6}(sources|code|data|words)\d{0,2}", cell)
    return m.group(1) if m else ""


def born(cell):
    m = re.match(r"g(\d+)", cell)
    return int(m.group(1)) if m else 0


def line_of(cell, parents):
    """The cell and every ancestor of it, by the body's record of whose child each cell is."""
    out, c = [], cell
    while c and c not in out:
        out.append(c)
        c = parents.get(c, "")
    return out


def plan(gen, dna, body=None, organs=None):
    """The children to grow this generation: [{"name", "suffix", "organ", "parent"}] (parent "" for a first cell).

    organs given: one child for each organ named, from the body's newest cell of that organ (the old way, kept for
    trials that compare ways of training). A new DNA, or a body with no cells: one first cell for each organ."""
    body = json.loads(BODY.read_text()) if body is None else body
    cells = [c for c in body.get("cells", []) if re.fullmatch(CELL, str(c))] if body.get("dna") == dna else []
    out = []

    def child(o, parent):
        n = sum(c["organ"] == o for c in out)
        name = f"{gen}{o}{n + 1 if n else ''}"
        out.append({"name": name, "suffix": name[len(gen):], "organ": o, "parent": parent})

    if organs or not cells:
        for o in organs or ORGANS:
            mine = sorted((c for c in cells if organ_of(c) == o), key=born)
            child(o, mine[-1] if mine else "")
        return out
    gen_body = body.get("generation", 0)
    grown = [c for c in cells if born(c) < gen_body] or cells  # all young: they all count as grown
    # past the runners' limit, the organs take turns, the newest parents first (they hold the most)
    by_organ = {o: sorted((c for c in grown if organ_of(c) == o), key=lambda c: (-born(c), c)) for o in ORGANS}
    while len(out) < MOST_CHILDREN and any(by_organ.values()):
        for o in ORGANS:
            if by_organ[o] and len(out) < MOST_CHILDREN:
                child(o, by_organ[o].pop(0))
    return out


def grown_body(before, children, parents=None, most=MOST_CELLS):
    """The body after a generation: the cells before and their children. Over `most`, the oldest cells whose line
    goes on in a descendant in the body give up their place first. Returns (cells, retired)."""
    cells = list(dict.fromkeys(list(before) + list(children)))
    parents = parents or {}
    retired = []
    while len(cells) > most:
        carried = {a for c in cells for a in line_of(c, parents)[1:]}
        can_go = [c for c in cells if c in carried and c not in children] or [c for c in cells if c not in children] or cells
        oldest = min(can_go, key=lambda c: (born(c), c))
        cells.remove(oldest)
        retired.append(oldest)
    return cells, retired


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["plan"] and len(a) >= 3 and re.fullmatch(r"g\d{1,6}", a[1]):
        organs = [o for o in json.loads(a[3]) if o in ORGANS] if len(a) > 3 and a[3].strip() else None
        print(json.dumps(plan(a[1], a[2], organs=organs)))
    else:
        print(__doc__)
