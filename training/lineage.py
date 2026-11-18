"""Plan children and active places for the hive. The paired exam in training/grow_record.py decides whether
a generation joins the active body.

    python3 training/lineage.py plan <generation> <dna> [organs as a JSON list]    the children to grow, as JSON
    python3 training/lineage.py members <dna> [few]                                who works for the body (for HIVE_MEMBERS); few: the trunk and each organ's newest cell
    python3 training/lineage.py trunk <generation> <dna> <child that grew> ...     which cells this generation's trunk is the average of
    python3 training/lineage.py studied <dna> <folder>                             the training steps of every cell record in the folder (<dna>.<cell>.json), kept in cells/studied.json

A child starts from its parent's weight edit. Training can mix it with the shared trunk and uses checked work,
including right answers, contrasts with wrong answers and corrected failures. Later training can change an
answer the parent got right. The released parent edit can be run again.

It grows the way Fibonacci's rabbits do: a cell born in the last generation is young and has no child yet; every
other cell has one child each generation. Per organ: 1, 2, 3, 5, 8, ... (in a generation where every cell is
young, they all count as grown, so the line never stands still). Two limits are the runners', not the idea's: at
most MOST_CHILDREN children a generation (each trains on its own runner, for hours) and at most MOST_CELLS cells in
the body (each is loaded beside the DNA in the same server). When the body is full, the oldest cells whose line
goes on in a descendant give up their place. The limit applies to the active roster. Retention of a particular
skill is measurable by comparing what the two versions actually deliver on matching jobs.

Only names are read here, from files this repository wrote; it needs nothing but Python.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BODY = ROOT / "cells" / "body.json"
STUDIED = ROOT / "cells" / "studied.json"
ORGANS = ("sources", "code", "data", "words")
MOST_CHILDREN = 8
MOST_CELLS = 24
CELL = r"g\d{1,6}(?:sources|code|data|words)\d{0,2}"
TRUNK = r"g\d{1,6}trunk"  # the body's shared edit of a generation (training/merge.py)


def organ_of(cell):
    """'g24code2' -> 'code'."""
    m = re.fullmatch(r"g\d{1,6}(sources|code|data|words)\d{0,2}", cell)
    return m.group(1) if m else ""


def born(cell):
    m = re.match(r"g(\d+)", cell)
    return int(m.group(1)) if m else 0


def studied(dna, path=None):
    """{cell: the training steps it made when it was grown} for this DNA (cells/studied.json), {} where none is kept.

    One number is counted, and only between cells born in the same generation. g38 (2026-11-17): one runner trained a
    row in 9.9 seconds and another in 50.3, so of three code children taught the same lessons one made 375 steps,
    one 206 and one 67. Their loss on "walk a site over several pages" ended at 0.001, 0.003 and 0.58, and at the
    pulse the second passed that kind 5 of 5 and the third 0 of 5. By name the third sat before them and would have
    been the first parent of the next children; the first never sat one task."""
    try:
        d = json.loads((STUDIED if path is None else Path(path)).read_text())
        return {c: n for c, n in (d.get(dna) or {}).items() if isinstance(n, (int, float))} if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def keep_studied(dna, folder, path=None):
    """Read the steps of every cell record in the folder (<dna>.<cell>.json, as a generation's jobs name them, or
    <dna>+<cell>.json) into cells/studied.json. Returns what was added."""
    path = STUDIED if path is None else Path(path)
    try:
        all_ = json.loads(path.read_text())
    except (OSError, ValueError):
        all_ = {}
    new = {}
    for f in sorted(Path(folder).glob(f"{dna}[.+]*.json")):
        cell = f.stem[len(dna) + 1:]
        try:
            steps = json.loads(f.read_text()).get("steps")
        except (OSError, ValueError, AttributeError):
            continue
        if re.fullmatch(CELL, cell) and isinstance(steps, (int, float)) and steps > 0:
            new[cell] = int(steps)
    if new:
        all_[dna] = dict(sorted({**(all_.get(dna) or {}), **new}.items()))
        path.write_text(json.dumps(all_, indent=1) + "\n")
    return new


def line_of(cell, parents):
    """The cell and every ancestor of it, by the body's record of whose child each cell is."""
    out, c = [], cell
    while c and c not in out:
        out.append(c)
        c = parents.get(c, "")
    return out


def plan(gen, dna, body=None, organs=None, steps=None):
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
        steps = studied(dna) if steps is None else steps
        for o in organs or ORGANS:
            mine = sorted((c for c in cells if organ_of(c) == o), key=lambda c: (born(c), steps.get(c, 0)))
            child(o, mine[-1] if mine else "")
        return out
    # an organ the body has no cell of (its first cell's runner died, 2026-11-15: sources) gets a first cell now
    for o in ORGANS:
        if not any(organ_of(c) == o for c in cells):
            child(o, "")
    gen_body = body.get("generation", 0)
    grown = [c for c in cells if born(c) < gen_body] or cells  # all young: they all count as grown
    # past the runners' limit, the organs take turns, the newest parents first (they hold the most), and of one
    # generation the one that studied more (studied()): its children start from the most that was learned
    steps = studied(dna) if steps is None else steps
    by_organ = {o: sorted((c for c in grown if organ_of(c) == o), key=lambda c: (-born(c), -steps.get(c, 0), c)) for o in ORGANS}
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


def leaves(cells, parents):
    """The cells no other cell of the body descends from: the newest of every line. The trunk is their average."""
    has_child = {parents.get(c) for c in cells}
    return [c for c in cells if c not in has_child]


def members(dna, body=None, few=False, steps=None):
    """The names of who works for the body of this DNA, the trunk first: [] when it has no cell yet.
    few: the trunk and the newest cell of each organ, which is everyone a single task can seat (practice and the
    pulse load the whole body; answering one message does not need to)."""
    body = json.loads(BODY.read_text()) if body is None else body
    if body.get("dna") != dna:
        return []
    cells = [c for c in body.get("cells", []) if re.fullmatch(CELL, str(c))]
    if few:
        steps = studied(dna) if steps is None else steps
        newest = lambda o: min((c for c in cells if organ_of(c) == o), key=lambda c: (-born(c), -steps.get(c, 0), c))  # noqa: E731
        cells = [newest(o) for o in ORGANS if any(organ_of(c) == o for c in cells)]
    trunk = body.get("trunk")
    return ([trunk] if cells and isinstance(trunk, str) and re.fullmatch(TRUNK, trunk) else []) + cells


def trunk_of(gen, dna, grown, body=None):
    """What this generation's trunk is made of: {"name", "of": every leaf of the body as it will be, "older": the
    leaves born before this generation (their weights are in the release)}. grown: the children that did grow."""
    body = json.loads(BODY.read_text()) if body is None else body
    same = body.get("dna") == dna
    before = [c for c in body.get("cells", []) if re.fullmatch(CELL, str(c))] if same else []
    kids = [c for c in plan(gen, dna, body) if c["name"] in grown]
    parents = dict({c: p for c, p in (body.get("parents") or {}).items() if isinstance(p, str)} if same else {}, **{c["name"]: c["parent"] for c in kids if c["parent"]})
    cells, _ = grown_body(before, [c["name"] for c in kids], parents)
    of = leaves(cells, {c: p for c, p in parents.items() if c in cells})
    return {"name": f"{gen}trunk", "of": of, "older": [c for c in of if c not in grown]}


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["plan"] and len(a) >= 3 and re.fullmatch(r"g\d{1,6}", a[1]):
        organs = [o for o in json.loads(a[3]) if o in ORGANS] if len(a) > 3 and a[3].strip() else None
        print(json.dumps(plan(a[1], a[2], organs=organs)))
    elif a[:1] == ["members"] and len(a) >= 2 and re.fullmatch(r"t\d{1,3}", a[1]):
        # who works for the body, for HIVE_MEMBERS: "t80+g25trunk,t80+g25code,..."; the DNA alone when it has no cell
        print(",".join(f"{a[1]}+{c}" for c in members(a[1], few=a[2:3] == ["few"])) or a[1])
    elif a[:1] == ["trunk"] and len(a) >= 3 and re.fullmatch(r"g\d{1,6}", a[1]):
        print(json.dumps(trunk_of(a[1], a[2], [c for c in a[3:] if re.fullmatch(CELL, c)])))
    elif a[:1] == ["studied"] and len(a) >= 3 and re.fullmatch(r"t\d{1,3}", a[1]):
        print(json.dumps(keep_studied(a[1], a[2])))
    else:
        print(__doc__)
