"""H1: general fixes for what held-out kinds showed (g51 held-out exam, g48 taught hard kinds)."""
import subprocess
import sys

from team import solo

TWO = ("Look at the latest versions of the packages flask and sqlalchemy on PyPI. Which was released more recently, and how "
       "many days lie between? Answer in two lines: 'later: NAME' and 'days: N'.")
INI = "What is the value of 'retries', and how many keys? Answer in two lines: 'value: ', 'keys: '."


def test_int_of_a_word_from_a_column_says_the_column_holds_text():
    err = "Traceback...\nValueError: invalid literal for int() with base 10: 'Lima'"
    code = "import csv\nrows = list(csv.DictReader(open('people.csv')))\nint(rows[0]['city'])"
    assert "text from a column, not a number" in solo.number_hint(code, err)
    assert "text_as_number" in solo.hints_in(solo.number_hint(code, err))
    assert "text from a column" in solo.number_hint(code, "ValueError: could not convert string to float: 'north'")
    assert not solo.number_hint(code, "ValueError: invalid literal for int() with base 10: '3.5'")
    assert not solo.number_hint("print(int('x'))", err)


def test_a_value_overwritten_by_the_same_call_again_is_named():
    code = "def latest(p):\n    return 1, 2\nversion, released = latest('a')\nversion, released = latest('b')\nprint(version)"
    assert solo.overwritten(code) == ["released", "version"]
    ok = "v = 1\nv = v + 1\nprint(v)\na = f(1)\nb = f(2)\nfor a in x:\n    pass"
    assert solo.overwritten(ok) == []
    assert solo.overwrite_hint(ok) == ""


def test_the_named_line_with_a_version_or_nothing_after_its_label_is_asked_again():
    assert "number (2.1.9) where the name goes" in solo.form(TWO, "later: 2.1.9\ndays: 3")
    assert solo.form(TWO, "later: flask\ndays: 3") == ""
    assert "has no value after 'value:'" in solo.form(INI, "value: N/A\nkeys: 4")
    assert solo.form(INI, "value: 6\nkeys: 4") == ""
