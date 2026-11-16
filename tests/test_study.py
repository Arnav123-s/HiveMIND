"""A cell studies where its error is: the passes of its training go to the subjects it gets most wrong."""
from pathlib import Path

from training import grow

ROOT = Path(__file__).resolve().parents[1]


def _run(plan, loss_of, passes):
    """Study `passes` rows; loss_of(subject, times met) is the loss the cell has on a subject. Returns the rows met."""
    met = []
    for _ in range(passes):
        nxt = plan.next()
        if nxt is None:
            break
        key, idx = nxt
        plan.saw(key, loss_of(key, plan.met[key]))
        met.append((key, idx))
    return met


def test_a_row_belongs_to_its_kind_its_type_and_whether_it_is_new():
    assert grow.subject_of({"kind": "walk a site", "type": "first"}) == "walk a site / first"
    assert grow.subject_of({"kind": "walk a site", "type": "fix"}, new=True) == "walk a site / fix / new"
    assert grow.subject_of({"type": "first"}) == "other work / first"
    # the word DONE after a right output is the same thing to learn in every kind: one subject
    assert grow.subject_of({"kind": "walk a site", "type": "done"}) == grow.subject_of({"kind": "a sum", "type": "done"})


def test_the_passes_go_to_the_subject_the_cell_gets_wrong():
    groups = {f"kind {i} / first": list(range(i * 10, i * 10 + 10)) for i in range(10)}
    groups["a hard kind / first / new"] = list(range(100, 106))
    plan = grow.Study(groups, seed=1)
    # the known kinds stand at 0.04; the hard kind starts at 1.2 and falls a little each time it is met
    met = _run(plan, lambda k, n: max(0.3, 1.2 - 0.05 * n) if k.startswith("a hard") else 0.04, 120)
    hard = sum(k.startswith("a hard") for k, _ in met)
    # 6 rows of 106 (6%) get more than a tenth of the passes: its rows are few and no row is met more than MOST times
    assert hard == 6 * grow.Study.MOST
    assert {k for k, _ in met} == set(groups)  # every subject is met: what is known is still gone over
    rec = plan.record()
    assert list(rec)[0] == "a hard kind / first / new" and rec["a hard kind / first / new"]["first"] == 1.2
    assert rec["kind 3 / first"]["rows"] == 10 and rec["kind 3 / first"]["last"] == 0.04


def test_what_is_new_is_met_first():
    groups = {f"kind {i} / first": [i] for i in range(30)} | {f"new work {i} / first / new": [100 + i] for i in range(10)}
    early = []
    for seed in range(20):
        plan = grow.Study(groups, seed=seed)
        met = _run(plan, lambda k, n: 0.5, 10)
        early.append(sum(k.endswith(" / new") for k, _ in met))
    # ten subjects of forty, counted as unknown where the others count as nearly known: most of the first ten rows
    assert sum(early) / len(early) >= 6


def test_no_row_is_met_more_than_most_times_and_the_plan_ends_when_all_are():
    plan = grow.Study({"a / first": [0, 1], "b / first": [2]}, seed=0)
    met = _run(plan, lambda k, n: 1.0, 100)
    assert len(met) == 3 * grow.Study.MOST and plan.next() is None
    assert all(sum(i == j for _, i in met) == grow.Study.MOST for j in (0, 1, 2))


def test_raw_text_keeps_a_fixed_share_whatever_its_loss():
    groups = {"a kind / first": list(range(200)), grow.RAW: list(range(200, 260))}
    plan = grow.Study(groups, fixed={grow.RAW: 0.06}, seed=3)
    met = _run(plan, lambda k, n: 3.0 if k == grow.RAW else 0.04, 400)  # raw text is never foreseen: its loss stays high
    raw = sum(k == grow.RAW for k, _ in met)
    assert 10 <= raw <= 45  # about 6% of 400, not the 98% its loss would take


def test_a_cell_meets_its_own_organs_work_more_often_at_the_same_loss():
    groups = {"its own / first": list(range(100)), "another organ's / first": list(range(100, 200))}
    plan = grow.Study(groups, boost={"its own / first": 3.0}, seed=5)
    met = _run(plan, lambda k, n: 0.5, 200)
    own = sum(k == "its own / first" for k, _ in met)
    assert 130 <= own <= 170  # three parts in four


def test_the_same_seed_gives_the_same_study():
    groups = {f"kind {i} / first": list(range(i * 5, i * 5 + 5)) for i in range(6)}
    a = _run(grow.Study(groups, seed="g40code"), lambda k, n: 0.2 + 0.1 * len(k) % 0.7, 60)
    b = _run(grow.Study(groups, seed="g40code"), lambda k, n: 0.2 + 0.1 * len(k) % 0.7, 60)
    assert a == b and a != _run(grow.Study(groups, seed="g40data"), lambda k, n: 0.2 + 0.1 * len(k) % 0.7, 60)


def test_a_trial_can_grow_cells_the_old_way_beside_the_new():
    text = (ROOT / ".github" / "workflows" / "grow.yml").read_text()
    assert "no-checkpoint|even|" in text  # versus: --even
    src = (ROOT / "training" / "grow.py").read_text()
    assert 'study="even" if "--even" in argv else "error"' in src


def test_a_childs_record_adds_up_what_its_slices_studied():
    from training import merge
    a = {"walk a site / first / new": {"rows": 2, "passes": 8, "first": 1.2, "last": 0.4}, "a sum / first": {"rows": 30, "passes": 3, "first": 0.04, "last": 0.04}}
    b = {"walk a site / first / new": {"rows": 1, "passes": 4, "first": 1.0, "last": 0.6}}
    got = merge.subjects([a, b, None])
    assert list(got) == ["walk a site / first / new", "a sum / first"]  # the most studied first
    assert got["walk a site / first / new"] == {"rows": 3, "passes": 12, "first": 1.1, "last": 0.5}
    assert got["a sum / first"]["passes"] == 3 and merge.subjects([None, {}]) == {}
