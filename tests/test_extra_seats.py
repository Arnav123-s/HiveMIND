"""R1: a right member is not lost. g48's gate: 5 of 11 failed hard tasks had one member right while the other two
crashed; no two agreed and nothing was delivered. Extra seats (at most two) go to a task with a lone or disagreeing
answer and a crashed member; delivery still needs two in agreement."""
from team import solo, ternary

TASK = "Add 2 and 3 and tell me the sum."


def _hive(monkeypatch, answers):
    left, seats = list(answers), []

    def member(task, n, board, guard, work, temperature, who="coder", also=()):
        seats.append((n, temperature))
        a = left.pop(0) if left else ""
        return {"answer": a, "program": "", "turns": 1, "who": who, "messages": [], "hints": [], "temperature": temperature, "also": []}
    monkeypatch.setattr(solo, "member", member)
    monkeypatch.setattr(ternary, "seating", lambda t, kind=None: ["a", "b", "c"])
    return seats


def test_a_crash_beside_a_lone_answer_gets_an_extra_seat_and_two_agree(tmp_path, monkeypatch):
    seats = _hive(monkeypatch, ["", "sum: 5", "", "sum: 5"])
    out = solo.run(TASK, tmp_path / "a", "never", members=2)
    assert out["agreed"] and out["tries"] == 4 and [n for n, _ in seats] == [1, 2, 3, 4]
    assert seats[3][1] > 0.7  # a new temperature


def test_extra_seats_are_at_most_two_and_a_lone_answer_is_never_delivered(tmp_path, monkeypatch):
    seats = _hive(monkeypatch, ["", "sum: 5", "", "", ""])
    out = solo.run(TASK, tmp_path / "b", "never", members=2)
    assert not out["agreed"] and len(seats) == 5 and out["report"].startswith("Not confirmed")


def test_no_extra_seat_when_nobody_crashed(tmp_path, monkeypatch):
    seats = _hive(monkeypatch, ["sum: 5", "sum: 6", "sum: 7"])
    out = solo.run(TASK, tmp_path / "c", "never", members=2)
    assert not out["agreed"] and len(seats) == 3


def test_no_extra_seat_when_every_member_crashed(tmp_path, monkeypatch):
    seats = _hive(monkeypatch, ["", "", ""])
    solo.run(TASK, tmp_path / "d", "never", members=2)
    assert len(seats) == 3


def test_agreement_in_the_first_seats_costs_nothing_more(tmp_path, monkeypatch):
    seats = _hive(monkeypatch, ["sum: 5", "sum: 5"])
    assert solo.run(TASK, tmp_path / "e", "never", members=2)["agreed"] and len(seats) == 2
