"""Data of several lines in a task (a grid, a markdown table) is offered to the members as a file, with a line in the
orders saying so. g48's practice: h10004803_01 (a grid) and h10004802_02 (a markdown table) had it retyped by hand."""
from team import solo
from team.tools.sandbox import give, given, note

GRID = ("Write a Python module and save it as grid.py. regions(grid) returns how many regions there are. Then tell me, "
        "on two lines, regions(grid) of this grid:\n@.@.@\n@@@..\n..@.@\n@...@")
TABLE = ("Here is a markdown table:\n| Name | Score |\n|---|---:|\n| Mira | 56.6 |\n| Ines | 49.1 |\n"
         "Save it as table.csv: the header row first, then the data rows. Then tell me how many data rows the table has.")


def test_a_grid_and_a_table_are_saved_as_a_file_and_the_member_is_told(tmp_path):
    for task, text in ((GRID, "@.@.@\n@@@..\n..@.@\n@...@\n"), (TABLE, "| Name | Score |\n|---|---:|\n| Mira | 56.6 |\n| Ines | 49.1 |\n")):
        d = tmp_path / str(len(task))
        said = note(give(task, d, skip=solo.wanted(task)))
        assert (d / "task_data.txt").read_text() == text
        assert "task_data.txt" in said and "Do not type the data out again" in said
    assert not (tmp_path / str(len(GRID)) / "grid.py").exists()  # the file asked for is not made for the member


def test_one_line_or_no_data_gets_no_note_and_a_named_file_keeps_its_name(tmp_path):
    assert note(give("What is 2 + 2?", tmp_path / "a")) == ""
    assert note(give("Here is a text:\nthe quick brown fox.\nCount the words.", tmp_path / "b")) == ""
    task = "Here is the file scores.csv:\na,b\n1,2\n3,4\n5,6\nSum the column b."
    d = tmp_path / "c"
    said = note(give(task, d))
    assert (d / "scores.csv").exists() and "scores.csv (5 lines, CSV text" in said and not (d / "task_data.txt").exists()


def test_the_member_is_shown_the_note_with_its_task(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(solo.llm, "chat", lambda who, msgs, **k: seen.append(msgs[1]["content"]) or "DONE")
    board = solo.Board(tmp_path)
    solo.member(TABLE, 1, board, solo.Guard(board, "never", goal=TABLE, use_model=False), tmp_path / "w", 0.0)
    assert seen and seen[0].startswith("TASK: Here is a markdown table") and "saved for you as a file" in seen[0]
    assert (tmp_path / "w" / "task_data.txt").is_file()
