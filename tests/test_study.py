"""The pick of what a cell trains on next (training/grow.py Study), without a model: passes go where the error is."""
import random
from collections import Counter

from training import grow


def run(study, losses, n):
    """n passes, each subject answering with its fixed loss; the subjects picked, in order."""
    got = []
    for _ in range(n):
        p = study.pick()
        if p is None:
            break
        s, row = p
        got.append((s, row))
        study.learned(s, losses.get(s, 0.1))
    return got


def subjects(**sizes):
    out, k = {}, 0
    for s, n in sizes.items():
        out[s] = list(range(k, k + n))
        k += n
    return out


def test_high_loss_subject_gets_most_passes():
    study = grow.Study(subjects(hard=50, easy1=50, easy2=50), rng=random.Random(1))
    got = Counter(s for s, _ in run(study, {"hard": 1.5, "easy1": 0.05, "easy2": 0.05}, 120))
    assert got["hard"] > 0.8 * 120
    assert got["easy1"] >= 1 and got["easy2"] >= 1


def test_every_subject_met_in_the_first_sweep():
    sizes = {f"s{j}": 3 for j in range(40)}
    study = grow.Study(subjects(**sizes), rng=random.Random(2))
    first = [s for s, _ in run(study, {"s0": 2.0}, 40)]
    assert sorted(first) == sorted(sizes)  # one each, before any subject is met twice


def test_no_row_more_than_four_times_and_then_it_ends():
    study = grow.Study(subjects(a=3, b=5, c=1), rng=random.Random(3))
    got = run(study, {"a": 3.0}, 10_000)
    rows = Counter(r for _, r in got)
    assert len(got) == 4 * 9 and set(rows.values()) == {4}
    assert study.pick() is None


def test_rows_of_a_subject_cycle_before_repeating():
    study = grow.Study({"a": [0, 1, 2, 3, 4]}, rng=random.Random(4))
    got = [r for _, r in run(study, {}, 10)]
    assert sorted(got[:5]) == [0, 1, 2, 3, 4] and sorted(got[5:]) == [0, 1, 2, 3, 4]


def test_read_and_judged_keep_their_share():
    study = grow.Study(subjects(read=200, judged=200, hard=300, easy=300), rng=random.Random(5))
    got = Counter(s for s, _ in run(study, {"read": 5.0, "judged": 0.0, "hard": 1.0, "easy": 0.05}, 500))
    assert 13 <= got["read"] <= 17 and 13 <= got["judged"] <= 17  # 3% each, whatever their loss


def test_own_organ_weighs_three_times():
    study = grow.Study(subjects(mine=2000, other=2000), own={"mine"}, rng=random.Random(6))
    got = Counter(s for s, _ in run(study, {"mine": 0.2, "other": 0.2}, 2000))
    assert 2.4 < got["mine"] / got["other"] < 3.7


def test_loss_is_mean_of_last_three_and_table():
    study = grow.Study({"a": [0, 1, 2, 3]}, rng=random.Random(7))
    for loss in (0.9, 0.6, 0.3, 0.0):
        study.pick()
        study.learned("a", loss)
    assert abs(study.loss("a") - 0.3) < 1e-9
    assert study.table() == [{"subject": "a", "rows": 4, "passes": 4, "loss_first": 0.9, "loss_last": 0.3}]


def test_learning_rate_share():
    assert grow.lr_share(0.0) < 0.05 and abs(grow.lr_share(0.025) - 0.5) < 1e-9
    assert abs(grow.lr_share(0.05) - 1.0) < 1e-9 and abs(grow.lr_share(1.0) - 0.05) < 1e-9
    assert grow.lr_share(0.5) > grow.lr_share(0.9)


def test_subject_names():
    row = {"kind": "a sum in words", "type": "fix", "task": "x"}
    assert grow.subject(row) == "a sum in words · fix"
    assert grow.subject(row, new=True) == "a sum in words · fix · new"


def test_done_rows_are_one_subject_and_own_is_a_weight_not_a_split():
    """g35code: 104 subjects, 40 of them rows of type done at a loss of about 0.001 (102 of 444 passes); the own organ
    split every kind in two. Done rows are one subject (two with the new ones) and own weighs by its share."""
    rows = [{"kind": k, "type": t} for k in ("sums", "dates", "files", "logs") for t in ("first", "done", "fix")]
    names = {grow.subject(r, new) for r in rows for new in (False, True)}
    assert len(names) == 4 * 2 * 2 + 2 and {"done", "done · new"} <= names
    study = grow.Study({"half": list(range(10)), "none": list(range(10, 20)), "all": list(range(20, 30))},
                       own={"half": 0.5, "all": 1.0}, rng=random.Random(8), weight=3)
    assert (study.odds("none"), study.odds("half"), study.odds("all")) == (1.0, 2.0, 3.0)
    assert grow.Study({"a": [0]}, own={"a"}, weight=3).odds("a") == 3.0  # a set: wholly own, as before


def test_the_flow_runs_a_generation_on_more_runners_with_the_same_work():
    """Agent C's speed piece: a stage lasts as long as its slowest runner, so 12 practice runners of 8 tasks (and 8 dream runners of 3)
    in place of 6 of 16 (4), and the pulse on 8 runners of 8 tasks in place of 4 of 16: 64 tasks still."""
    from pathlib import Path
    flow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "grow.yml").read_text()
    assert "shard: ${{ fromJSON(inputs.shards || '[1,2,3,4,5,6,7,8,9,10,11,12]') }}" in flow
    assert '--tasks "${{ inputs.tasks || \'8\' }}"' in flow and 'DREAMS="${{ inputs.dreams || \'3\' }}"' in flow
    assert "exam.py sit --level mixed --tasks 8 --seed" in flow
    assert 12 * 8 == 6 * 16 and 8 * 8 == 4 * 16


WALK, LOG, EASY = "walk a site over several pages · first · new", "a log read and counted into a file · first · new", "a sum in words · first"


def learning(study, start, per_round=0.85, n=10_000):
    """n passes in which a subject's loss falls by `per_round` for each round of its rows met (a subject not in `start`
    answers 0.05 and learns nothing). The passes each subject had when its loss first fell under the goal."""
    met, under = Counter(), {}
    for _ in range(n):
        p = study.pick()
        if p is None:
            break
        s = p[0]
        met[s] += 1
        study.learned(s, start.get(s, 0.05) * per_round ** (met[s] / study.rows[s]))
        if study.loss(s) < study.GOAL and s not in under:
            under[s] = study.passes[s]
    return under


def test_new_hard_subject_is_studied_past_four_meetings_until_under_goal():
    """Generation 35: lesson rows met 4 times at the most, the new hard subjects ended at a loss of 0.4 to 1.6. A new
    hard subject (1.6 at first, x0.85 for each round of its rows: about 11 rounds to fall under 0.3) keeps its passes
    past 4 meetings a row until its loss is under 0.3; then it gets no more than any other (4 meetings a row)."""
    subs = subjects(**{WALK: 4, EASY: 40})
    before = grow.Study(subs, rng=random.Random(11))
    learning(before, {WALK: 1.6}, n=400)
    assert before.passes[WALK] == 4 * 4 and before.loss(WALK) > 0.5  # the old rule: 4 meetings a row, never learned
    study = grow.Study(subs, rng=random.Random(11), hard={WALK}, web={WALK})
    under = learning(study, {WALK: 1.6}, n=400)
    assert study.loss(WALK) < 0.3 and 4 * 4 < under[WALK] == study.passes[WALK] <= 32 * 4
    assert study.passes[EASY] >= 40  # every easy row met at least once while it was studied


def test_new_hard_subject_never_learned_stops_at_32_meetings_a_row():
    study = grow.Study(subjects(**{WALK: 3, EASY: 10}), rng=random.Random(12), hard={WALK})
    got = Counter(run(study, {WALK: 2.0, EASY: 0.05}, 10_000))
    assert got[(WALK, 0)] == 32 and study.passes[WALK] == 32 * 3 and study.passes[EASY] == 4 * 10
    assert study.pick() is None and study.size == 32 * 3 + 4 * 10


def test_web_kinds_come_first():
    """The new web subjects are met first in the first sweep, then the other new hard ones, then the rest; while both
    are above 0.3 a web subject gets about three times the passes of another hard one."""
    subs = subjects(**{EASY: 30, LOG: 30, WALK: 30, "done · new": 30})
    hard, web = grow.new_hard(subs)
    assert (hard, web) == ({WALK, LOG}, {WALK})
    study = grow.Study(subs, rng=random.Random(13), hard=hard, web=web)
    got = [s for s, _ in run(study, {WALK: 1.5, LOG: 1.5, EASY: 0.05, "done · new": 0.01}, 300)]
    assert got[:2] == [WALK, LOG]
    assert 2.2 < Counter(got)[WALK] / Counter(got)[LOG] < 4.0


def test_easy_subjects_still_get_passes_while_hard_ones_are_studied():
    """FIRST (3 in 4) of the passes go to new hard subjects not learned yet; the rest are picked among the others by
    the odds, so what is known is still rehearsed."""
    subs = subjects(**{WALK: 40, LOG: 40, EASY: 100, "a thing to know · first": 100})
    study = grow.Study(subs, rng=random.Random(14), hard={WALK, LOG}, web={WALK})
    got = Counter(s for s, _ in run(study, {WALK: 2.0, LOG: 2.0}, 1000))
    easy = got[EASY] + got["a thing to know · first"]
    assert 0.2 * 1000 < easy < 0.3 * 1000 and got[EASY] > 50 and got["a thing to know · first"] > 50


def test_hard_kinds_are_read_from_the_hard_exam():
    kinds = grow.hard_kinds()
    assert len(kinds) == 13 and set(grow.WEB) <= kinds
    assert {"a fact read and a date sum on it", "a fact from a site and a date sum on it", "a module of two functions, with hidden tests"} <= kinds
    rows = [{"kind": k, "type": t} for k in ("walk a site over several pages", "a sum in words") for t in ("first", "fix", "done")]
    names = {grow.subject(r, new) for r in rows for new in (False, True)}
    walk = {"walk a site over several pages · first · new", "walk a site over several pages · fix · new"}
    assert grow.new_hard(names) == (walk, walk)
