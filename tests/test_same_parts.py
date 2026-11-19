"""Agreement on a compound task ("PART A ... PART B") reads each part, so the inline form ('PART B: Monday') and the
line-by-line form agree. g48's c10004810_03: 'PART B\\nMonday' against 'PART B\\nPART B: Monday' was no agreement."""
from team import parts, solo

TASK = parts.join(["What day of the week is 27 April 2026?", "Reverse 'window'."])


def test_a_heading_repeated_with_its_answer_inline_agrees_with_the_line_by_line_form():
    a = "PART A\nA: 102\nB: wodniw\nPART B\nMonday"
    b = "PART A\nA: 102\nB: wodniw\nPART B\nPART B: Monday"
    assert solo.same(a, b, TASK) and solo.same(b, a, TASK)
    assert solo.same("PART A: 31 days\nPART B: Jan", "PART A\n31\nPART B\nJan", TASK)
    assert solo.same("PART A\nlamp: 7\nPART A\nwas: 6\nPART B\n7", "PART A\nlamp: 7\nwas: 6\nPART B: 7", TASK)


def test_a_different_part_still_does_not_agree():
    a = "PART A\nA: 102\nPART B\nMonday"
    assert not solo.same(a, "PART A\nA: 102\nPART B\nPART B: Wednesday", TASK)
    assert not solo.same(a, "PART A: 103\nPART B: Monday", TASK)
    assert not solo.same(a, "PART A: 102\nPART B: Monday\nPART B: Friday", TASK)


def test_the_exam_still_reads_the_first_piece_under_a_heading():
    assert parts.of_answer("PART B\nPART B: Monday")["B"] == ""
    assert parts.of_answer("PART B\nPART B: Monday", merge=True)["B"] == "Monday"
