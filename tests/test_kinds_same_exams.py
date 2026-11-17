"""K1: the kinds moved to training/kinds/ give the same exams as before, seed for seed.

tests/data/exams_golden.json was written by snapshot() below from the code as it was before the kinds were moved
(one file for the easy makers, one for the hard ones). Every task, its id, field, kind, the seed and level its check
remembers, and the values the check holds (what it wants) are compared, byte for byte. No network: the one maker that
asks a site while it makes its task (the open web) is answered by a stand-in for requests.get.

Kinds added later (K2) change what a seed draws, so the comparison is made over the kinds the fixture names, in their
own order: the old kinds keep their exams whatever is added beside them.

    python tests/test_kinds_same_exams.py      writes the fixture again (only when a change of the exams is meant)
"""
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
GOLDEN = ROOT / "tests" / "data" / "exams_golden.json"

BASIC_SEEDS = list(range(9001, 9009))
GATE_SEEDS = [20000000 + 42 * 10 + s for s in range(1, 5)]  # grow.yml's gate: 20000000 + run * 10 + seed, --level mixed --tasks 8
PRACTICE_SEEDS = [10000000 + 42 * 100 + s for s in range(1, 3)]  # grow.yml's practice: 10000000 + run * 100 + runner
LEVELS = {"m_percent": 2, "m_table": 1, "h_join": 1, "h_log": 2, "h_search": 1, "compound": 3}
WEIGHTS = {"a sum in words": 0.9, "a join over two small tables": 0.6, "operate a website": 0.05}


class _Answer:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def _offline_get(url, *a, **k):
    """requests.get without the network: the query service is 'busy' (so the open web falls back to a known item, drawn
    by the seed) and an item's data is a label made from its id."""
    if "query.wikidata.org" in url:
        raise ConnectionError("offline")
    if "Special:EntityData/" in url:
        qid = url.rsplit("/", 1)[1].split(".")[0]
        return _Answer({"entities": {qid: {"labels": {"en": {"value": f"Item {qid}"}}, "claims": {}}}})
    raise ConnectionError(f"offline: {url}")


def _plain(x, depth=0):
    """What a check holds, as JSON: numbers, words, lists, and for a function the values of its closure by name."""
    if depth > 6:
        return "..."
    if x is None or isinstance(x, (bool, int, str)):
        return x
    if isinstance(x, float):
        return repr(x)
    if isinstance(x, (list, tuple)):
        return [_plain(v, depth + 1) for v in x]
    if isinstance(x, set):
        return sorted(repr(v) for v in x)
    if isinstance(x, dict):
        return {str(k): _plain(v, depth + 1) for k, v in x.items()}
    if isinstance(x, (datetime.date, datetime.time)):
        return x.isoformat()
    if callable(x) and hasattr(x, "__code__"):
        cells = dict(zip(x.__code__.co_freevars, x.__closure__ or ()))
        return {"fn": x.__qualname__.rsplit(".", 1)[-1] if "<locals>" not in x.__qualname__ else x.__qualname__,
                "holds": {k: _plain(c.cell_contents, depth + 1) for k, c in sorted(cells.items()) if k != "r"}}
    return type(x).__name__


def _task(t):
    tid, field, kind, task, check = t
    return {"id": tid, "field": field, "kind": kind, "task": task, "maker": getattr(check, "maker", ""),
            "rseed": getattr(check, "rseed", ""), "level": getattr(check, "level", 0),
            "parts": getattr(check, "parts", None), "check": _plain(check)}


def snapshot():
    import requests

    from training import exam, exam_hard, lessons
    real = requests.get
    requests.get = _offline_get
    try:
        out = {"easy_makers": [m.__name__ for m in exam.MAKERS], "hard_makers": [m.__name__ for m in exam_hard.MAKERS],
               "leveled": list(exam.LEVELED), "held_out": sorted(exam_hard.HELD_OUT), "solvers": list(lessons.SOLVERS), "exams": {}}
        ex = out["exams"]
        for s in BASIC_SEEDS:
            ex[f"basic:{s}"] = [_task(t) for t in exam.exam(s, 16)]
            ex[f"hard:{s}"] = [_task(t) for t in exam.exam(s, 16, level="hard")]
        for s in GATE_SEEDS:
            ex[f"mixed:{s}"] = [_task(t) for t in exam.exam(s, 8, level="mixed")]
        for s in PRACTICE_SEEDS:
            ex[f"ladder:{s}"] = [_task(t) for t in exam.exam(s, 8, (), "ladder", without=exam_hard.HELD_OUT, levels=LEVELS)]
            ex[f"ladder-edge:{s}"] = [_task(t) for t in exam.exam(s, 8, (), "ladder", without=exam_hard.HELD_OUT, weights=WEIGHTS, levels=LEVELS)]
            ex[f"edge:{s}"] = [_task(t) for t in exam.exam(s, 8, (), "edge", without=exam_hard.HELD_OUT, weights=WEIGHTS)]
        # what a generation's lessons draw: one task of every taught kind, and tasks of several parts from those kinds
        pool = [lessons._maker(m) for m in lessons.SOLVERS]
        ex["lessons:g42"] = [_task((m,) + tuple(exam.remake(m, f"lesson:42:{m}:0", LEVELS.get(m, 0)))) for m in lessons.SOLVERS]
        ex["lessons:g42:several"] = [_task((i,) + tuple(exam.compound(f"lesson:42:several:{i}", 3, pool, LEVELS))) for i in range(4)]
        # every maker made again from a seed, at a level
        ex["remake"] = [_task((m,) + tuple(exam.remake(m, f"remake:{m}", 2))) for m in dict.fromkeys(out["easy_makers"] + out["hard_makers"])]
    finally:
        requests.get = real
    return out


def _dump(d):
    return json.dumps(d, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def test_the_same_seeds_give_the_same_exams_as_before_the_kinds_were_moved(monkeypatch):
    from training import exam, exam_hard, kinds
    want = json.loads(GOLDEN.read_text())
    # the old kinds, in their old order, are the registry's: whatever is added beside them comes after or between
    names = [k.KIND for k in kinds.ALL]
    for key in ("easy_makers", "hard_makers"):
        old = list(dict.fromkeys(want[key]))
        assert [n for n in names if n in old] == old
    # only the kinds the fixture knows are sat (new kinds would change what a seed draws, and that is meant)
    monkeypatch.setattr(exam, "MAKERS", [kinds.get(n).make for n in want["easy_makers"]])
    monkeypatch.setattr(exam_hard, "MAKERS", [kinds.get(n).make for n in want["hard_makers"]])
    monkeypatch.setattr(exam_hard, "HELD_OUT", exam_hard.HELD_OUT & set(want["held_out"]))  # a new kind held out is not sat here either
    from training import lessons
    monkeypatch.setattr(lessons, "SOLVERS", {n: lessons.SOLVERS[n] for n in want["solvers"]})
    got = snapshot()
    assert _dump(got) == GOLDEN.read_text()


def test_the_registry_lists_the_kinds_as_the_exam_did():
    from training import exam, exam_hard, kinds, lessons
    want = json.loads(GOLDEN.read_text())
    easy = [m.__name__ for m in exam.MAKERS]
    hard = [m.__name__ for m in exam_hard.MAKERS]
    assert [n for n in easy if n in want["easy_makers"]] == want["easy_makers"]
    assert [n for n in hard if n in want["hard_makers"]] == want["hard_makers"]
    assert [n for n in lessons.SOLVERS if n in want["solvers"]] == want["solvers"]
    assert [n for n in exam.LEVELED if n in want["leveled"]] == want["leveled"]
    assert set(want["held_out"]) <= set(exam_hard.HELD_OUT)
    assert len({k.KIND for k in kinds.ALL}) == len(kinds.ALL)


if __name__ == "__main__":
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(_dump(snapshot()))
    print(f"written {GOLDEN}")
