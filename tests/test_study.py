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
    assert 48 <= got["read"] <= 52 and 48 <= got["judged"] <= 52  # 10% each, whatever their loss


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
    assert grow.subject(row, new=True, own=True) == "a sum in words · fix · new · own"
