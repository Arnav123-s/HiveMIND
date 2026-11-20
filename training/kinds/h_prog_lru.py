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


SOURCE = """class LRUCache:
    def __init__(s, capacity):
        s.c, s.d = capacity, {}

    def get(s, k):
__GET__        return s.d.get(k, __MISSING__)

    def put(s, k, v):
__PUT__        s.d[k] = v
        if len(s.d) > s.c:
            del s.d[next(iter(s.d))]

    def keys(s):
        return list(s.d)"""


def lru(task):
    m = re.search(r"kept for the key, or (.+?) when the cache does not hold it.*?Getting a key the cache holds (does|does not) count.*?"
                  r"and (does|does not) count as a use.*?keys\(\) of an LRUCache\((\d+)\) after these calls, in order: (.+)\.\s*$", task, re.S)
    if not m or "lru.py" not in task:
        return None
    missing, get_uses, put_uses, size, calls = m.groups()
    # a dict keeps its keys in the order they went in: a use takes the key out and puts it back last
    src = (SOURCE.replace("__MISSING__", missing)
           .replace("__GET__", "        if k in s.d:\n            s.d[k] = s.d.pop(k)\n" if get_uses == "does" else "")
           .replace("__PUT__", "        # put on a held key = a use: pop it first\n"
                                    "        s.d.pop(k, None)\n" if put_uses == "does" else
                                    "        # put on a held key keeps its place\n"))
    tests = ["t = LRUCache(1)", "t.put('x', 1)", "t.put('y', 2)", "assert t.keys() == ['y']", f"c = LRUCache({size})", "c." + calls.replace("; ", "; c.")]
    return program("lru", src, tests, ["print(c.keys())"])


def shows(task):
    """Whether the task asks about the detail members get wrong: a key put again after it was put (does that move it to
    the last place? the task says). A lesson on a task that does not ask it is drawn again (training/lessons.fitting)."""
    m = re.search(r"in order: (.+)\.\s*$", task, re.S)
    seen = set()
    for call in (m.group(1).split("; ") if m else []):
        k = re.match(r"put\((.+?),", call)
        if k and k.group(1) in seen:
            return True
        if k:
            seen.add(k.group(1))
    return False


make = h_prog_lru
lesson = lru
