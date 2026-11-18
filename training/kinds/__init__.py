"""The kinds of task of the hive's exam and lessons, one file each (docs/KINDS.md says how to add one).

Every module here whose name does not begin with "_" is a kind. It holds:

    KIND          its name, the same as its maker's (the exam draws a task with a seed made from this name)
    FAMILY        the field its tasks are counted under ("maths", "hard: websites" ...)
    HARD          True for a kind of several steps (training/exam_hard.py's sitting), False for the first exam's
    ORDER         where it stands among the kinds of its exam: the exam shuffles them with its seed, so the order is
                  part of what a seed draws, and it must not hang on file names. A new kind takes a number after the
                  last one (tests/test_kinds_same_exams.py: the old kinds keep their order and their tasks)
    make(r)       its maker: (field, kind, task, check) from a random.Random r (r.level: how hard, for a LEVELED kind);
                  check(run, report) -> (ok, why), the task's own check, made with the task
    lesson        lesson(task) -> the right program for a task of it, or None (no lesson: never shown done)
    sample()      optional: a task of it made without the network (the default draws one with make)

and may say:

    COPIES = 2         drawn twice as often in its exam (two places in the list)
    LEVELED = True     its own difficulty can be raised (r.level)
    HELD_OUT = True    never practised or taught: what the hive scores on it is what carries over
    NETWORK = True     its check or its lesson reads a site
    GIVEN_FILE = True  its lesson reads the task's data from the file the runtime saves (lesson(task, copy=True)
                       copies it into the program instead)
    LESSON_ORDER       where its lesson stands among the lessons (the order a generation's lessons are drawn in)

The modules are found by pkgutil, so two agents adding two kinds never edit the same file.
"""
import ast
import importlib
import pkgutil
import random
from functools import cache
from pathlib import Path

DEFAULTS = {"COPIES": 1, "LEVELED": False, "HELD_OUT": False, "NETWORK": False, "GIVEN_FILE": False, "lesson": None}


def _load():
    found = []
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda i: i.name):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{__name__}.{info.name}")
        for name in ("KIND", "FAMILY", "HARD", "ORDER", "make"):
            if not hasattr(mod, name):
                raise ImportError(f"training/kinds/{info.name}.py has no {name} (docs/KINDS.md)")
        for name, value in DEFAULTS.items():
            if not hasattr(mod, name):
                setattr(mod, name, value)
        if not hasattr(mod, "LESSON_ORDER"):
            mod.LESSON_ORDER = 10000 + (1000 if mod.HARD else 0) + mod.ORDER  # after every lesson there was before
        if mod.make.__name__ != mod.KIND:
            raise ImportError(f"training/kinds/{info.name}.py: its maker is called {mod.make.__name__}, its KIND {mod.KIND}: "
                              "the exam seeds a task by the maker's name, so the two must be the same")
        found.append(mod)
    found.sort(key=lambda m: (m.HARD, m.ORDER, m.KIND))
    names = [m.KIND for m in found]
    if len(set(names)) != len(names):
        raise ImportError(f"two kinds share a name: {sorted(n for n in names if names.count(n) > 1)}")
    places = [(m.HARD, m.ORDER) for m in found]
    if len(set(places)) != len(places):
        raise ImportError(f"two kinds share an ORDER: {sorted(m.KIND for m in found if places.count((m.HARD, m.ORDER)) > 1)}")
    return found


ALL = _load()
BY_NAME = {m.KIND: m for m in ALL}
EASY_KINDS = [m for m in ALL if not m.HARD]
HARD_KINDS = [m for m in ALL if m.HARD]
# the kinds whose own difficulty can be raised, the first exam's first; the kinds never practised or taught
LEVELED = tuple(m.KIND for m in ALL if m.LEVELED)
HELD_OUT = {m.KIND for m in ALL if m.HELD_OUT}
# the lessons: kind -> lesson(task), in the order a generation draws them; the held-out kinds are never here
SOLVERS = {m.KIND: m.lesson for m in sorted(ALL, key=lambda m: (m.LESSON_ORDER, m.KIND)) if m.lesson and not m.HELD_OUT}


def makers(hard=False):
    """The makers of one exam, in the order its seed shuffles them, a kind with COPIES as often as that."""
    return [m.make for m in (HARD_KINDS if hard else EASY_KINDS) for _ in range(m.COPIES)]


def get(name):
    """The kind of this name (its module); KeyError for a kind there is not."""
    return BY_NAME[name]


def find(name):
    """The kind of this name, or None."""
    return BY_NAME.get(name)


def sample(name):
    """(field, kind, task, check) of one task of the kind, made without the network."""
    mod = get(name)
    if hasattr(mod, "sample"):
        return mod.sample()
    r = random.Random(f"sample:{name}")
    r.level = 0
    return mod.make(r)


def written(name):
    """The kinds of task (the second of the four things its maker returns) a kind's maker writes out, read from its
    source, without calling it (some makers reach the network before they return), in the order they stand."""
    mod = get(name)
    out = []
    for fn in ast.parse(Path(mod.__file__).read_text()).body:
        if isinstance(fn, ast.FunctionDef) and fn.name == mod.KIND:
            for node in ast.walk(fn):
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple) and len(node.value.elts) == 4:
                    field, kind = node.value.elts[:2]
                    is_field = ((isinstance(field, ast.Constant) and field.value == mod.FAMILY)
                                or (isinstance(field, ast.Name) and field.id == "FAMILY"))
                    if is_field and isinstance(kind, ast.Constant) and isinstance(kind.value, str) and kind.value not in out:
                        out.append(kind.value)
    return out


@cache
def hard_groups():
    """The labels written to exam records, grouped by the maker's teaching policy."""
    groups = {}
    for mod in HARD_KINDS:
        if mod.HELD_OUT or mod.KIND in SOLVERS:
            for label in written(mod.KIND):
                groups[label] = "unpractised" if mod.HELD_OUT else "taught"
    return groups


def hard_scores(arm):
    """(Taught, held out) as [passed, sat]. Preserve the original split for new records.
    Older complete per-kind rolls can be recounted. The oldest records have only a held-out total.
    """
    held = arm.get("unpractised") or [0, 0]
    if "taught" in arm:
        return arm["taught"], held
    counts = arm.get("kinds") or {}
    if not counts or sum(v[1] for v in counts.values()) != arm.get("tasks"):
        return [0, 0], held
    totals = {"taught": [0, 0], "unpractised": [0, 0]}
    groups = hard_groups()
    for label, (passed, sat) in counts.items():
        group = groups.get(label)
        if group:
            totals[group][0] += passed
            totals[group][1] += sat
    return totals["taught"], totals["unpractised"]
