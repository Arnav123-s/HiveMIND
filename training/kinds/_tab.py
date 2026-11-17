"""What the kinds of the family "tables and data files" (h_tab_*) share: their data given as a named file in the task,
and the reading of a CSV the hive saved. Not a kind (its name begins with "_")."""
import csv
import io

from training.kinds._common import _file


def given(name, text, ask):
    """A task that gives a file: the runtime saves the block under its name (team/tools/sandbox.give), so a program
    opens it by that name. A blank line ends the block before the ask."""
    return f"Here is the file {name}:\n{text}\n\n{ask}"


def rows(run, name):
    """The rows of a CSV the hive saved, each cell stripped, blank rows left out; None if it saved none."""
    f = _file(run, name)
    if not f:
        return None
    return [[c.strip() for c in row] for row in csv.reader(io.StringIO(f.read_text())) if any(c.strip() for c in row)]


def near(cell, x, tol=0.006):
    """The cell holds the number x."""
    try:
        return abs(float(cell) - x) <= tol
    except (TypeError, ValueError):
        return False


def head(got, want):
    """The CSV's heading is the one asked for (case and spaces aside)."""
    return bool(got) and [c.lower() for c in got[0]] == [w.lower() for w in want]
