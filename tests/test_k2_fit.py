"""K2/T4: the lessons of the taught kinds of the families tables, text and programs make rows a runner that trains in 32
bits takes (lessons.LIMIT, 508 pieces), on 40 seeds, and are right by their own check on every one.

Some kinds cannot fit without changing what the exam draws: the task asks for a module that must hold its own data and
a scenario copied from the task. (A text on one line is data the runtime saves as a file: contacts, words and sentences
read it from there, so it is in the row once, and cut to its first and last words where the row is still long.) They are listed in TOO_LONG with the shortest
their rows could be, and are held to the length they have now, so that they do not grow.
"""
from concurrent.futures import ThreadPoolExecutor

import pytest

from training import kinds as K
from training import lessons

FAMILIES = ("hard: tables", "hard: text", "programs")
SEEDS = range(40)
# the longest row of each kind that does not fit, on these 40 seeds (counted with the DNA's tokenizer), and why
TOO_LONG = {
    "h_prog_bank": (609, "the task is 223 pieces: 139 are left for the class, its saving and the moves asked"),
    "h_prog_lru": (672, "the task is 252 pieces: 101 are left for the class, its saving and the calls asked (65); +16 for the line naming the rule of a put"),
    "h_prog_calc": (662, "the task is 257 pieces: 102 are left for a parser of three levels and its saving"),
    "h_prog_machine": (636, "the task is 267 pieces with its table: 97 are left for the table (70) and the module"),
    "h_prog_schedule": (615, "the task is 234 pieces: 107 are left for the module and the plan asked (60)"),
}


def taught():
    return sorted(k for k in lessons.SOLVERS if K.get(k).FAMILY in FAMILIES)


def _longest(maker):
    def one(seed):
        les = lessons.lesson(maker, seed)
        return seed, les["ok"], les["why"], max((lessons.row_pieces(r) for r in lessons.rows(les, today="2026-01-01 (Thursday)")), default=0)
    with ThreadPoolExecutor(8) as pool:
        return list(pool.map(one, SEEDS))


def test_the_families_have_their_taught_kinds():
    names = taught()
    assert len(names) == 18 and set(TOO_LONG) <= set(names)
    assert all(not K.get(k).HELD_OUT for k in names)


@pytest.mark.parametrize("maker", taught())
def test_lesson_rows_fit_and_are_right_on_40_seeds(maker):
    if lessons._tokenizer() is None:
        pytest.skip("the DNA's tokenizer is not at hand: pieces counted by the rule are only within a sixth")
    got = _longest(maker)
    wrong = [(s, why) for s, ok, why, _ in got if not ok]
    assert not wrong, wrong[:3]
    longest = max(n for *_, n in got)
    bound = TOO_LONG.get(maker, (lessons.LIMIT, ""))[0]
    assert longest <= bound, [(s, n) for s, *_, n in got if n > bound]
