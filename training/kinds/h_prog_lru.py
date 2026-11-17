"""The kind h_prog_lru: a cache of a given size that forgets what was used longest ago, with the task's own rules of
what counts as a use, put to hidden tests (programs).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import random
import re

from training.kinds._common import _fill
from training.kinds._programs import module_check, program

KIND = "h_prog_lru"
FAMILY = "programs"
HARD = True
ORDER = 520

MISSING = [-1, None, 0, "missing"]


class _Cache:
    def __init__(self, size, get_uses, put_uses, missing):
        self.size, self.get_uses, self.put_uses, self.missing, self.d = size, get_uses, put_uses, missing, {}

    def get(self, k):
        if k not in self.d:
            return self.missing
        if self.get_uses:
            self.d[k] = self.d.pop(k)
        return self.d[k]

    def put(self, k, v):
        if k in self.d and not self.put_uses:
            self.d[k] = v
            return None
        self.d.pop(k, None)
        self.d[k] = v
        if len(self.d) > self.size:
            self.d.pop(next(iter(self.d)))
        return None

    def keys(self):
        return list(self.d)


def _ops(r, n):
    keys = "abcdefg"[:r.randrange(3, 8)]
    return [("put", [r.choice(keys), r.randrange(100)]) if r.random() < 0.55 else ("get", [r.choice(keys)]) for _ in range(n)]


def _says(word, yes):
    return "does" if yes else "does not"


def h_prog_lru(r):
    size, get_uses, put_uses, missing = r.randrange(2, 5), r.random() < 0.5, r.random() < 0.5, r.choice(MISSING)
    ask = _ops(r, r.randrange(5, 9))
    ref = _Cache(size, get_uses, put_uses, missing)
    for op, args in ask:
        getattr(ref, op)(*args)
    want = ref.keys()
    seed = r.random()

    def draw():
        h = random.Random(f"hidden:{seed}")
        out = []
        for _ in range(30):
            n = h.randrange(1, 5)
            c, steps = _Cache(n, get_uses, put_uses, missing), []
            for op, args in _ops(h, h.randrange(3, 16)):
                steps.append([op, args, getattr(c, op)(*args)])
                if h.random() < 0.3:
                    steps.append(["keys", [], c.keys()])
            steps.append(["keys", [], c.keys()])
            out.append({"new": ["LRUCache", [n]], "steps": steps})
        return out
    calls = "; ".join(f"{op}({', '.join(map(repr, a))})" for op, a in ask)
    return (FAMILY, "a cache that forgets the least recently used, with hidden tests",
            f"Write a Python module and save it as lru.py. It holds a class LRUCache. LRUCache(capacity) is a cache that holds at most "
            f"capacity keys. It has three methods. 1) get(key) returns the value kept for the key, or {missing!r} when the cache does "
            f"not hold it. 2) put(key, value) keeps the value for the key and returns None; when that makes more keys than the "
            f"capacity, the key used longest ago is forgotten. 3) keys() returns the list of keys it holds, from the one used longest "
            f"ago to the one used last. Putting a new key is a use of it. Getting a key the cache holds {_says('get', get_uses)} count as "
            f"a use. Putting a key the cache already holds changes its value and {_says('put', put_uses)} count as a use. Test the "
            f"class yourself before you finish. Then tell me the value of keys() of an LRUCache({size}) after these calls, in order: "
            f"{calls}.", module_check("lru", draw, [want]))


SOURCE = '''MISSING = __MISSING__
GET_IS_USE, PUT_IS_USE = __GET__, __PUT__


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.kept = {}  # a dict keeps its keys in the order they went in: the first is the one used longest ago

    def get(self, key):
        if key not in self.kept:
            return MISSING
        if GET_IS_USE:
            self.kept[key] = self.kept.pop(key)
        return self.kept[key]

    def put(self, key, value):
        if key in self.kept and not PUT_IS_USE:
            self.kept[key] = value
            return None
        self.kept.pop(key, None)
        self.kept[key] = value
        if len(self.kept) > self.capacity:
            del self.kept[next(iter(self.kept))]
        return None

    def keys(self):
        return list(self.kept)'''


def lru(task):
    m = re.search(r"kept for the key, or (.+?) when the cache does not hold it.*?Getting a key the cache holds (does|does not) count.*?"
                  r"and (does|does not) count as a use.*?keys\(\) of an LRUCache\((\d+)\) after these calls, in order: (.+)\.\s*$", task, re.S)
    if not m or "lru.py" not in task:
        return None
    missing, get_uses, put_uses, size, calls = m.groups()
    tests = ["c = LRUCache(1)", "c.put('x', 1)", "c.put('y', 2)", f"assert c.keys() == ['y'] and c.get('x') == {missing}",
             f"c = LRUCache({size})", *calls.split("; ")]
    tests = tests[:5] + [f"c.{call}" for call in tests[5:]]
    return program("lru", _fill(SOURCE, get=get_uses == "does", put=put_uses == "does").replace("__MISSING__", missing), tests, ["print(c.keys())"])


make = h_prog_lru
lesson = lru
