"""Replay member programs at the public handoff, where only the delivered files count."""
import json
import os

import pytest

from team import deliverables, solo


RAIN = ("A rain gauge recorded 7 mm on Monday, 11 mm on Tuesday, and 3 mm on Wednesday. "
        "Create a CSV file named rainfall.csv with columns day,mm and rows in the order Wednesday, Monday, Tuesday. "
        "Tell me the total rainfall in millimetres.")
GOOD = "day,mm\nWednesday,3\nMonday,7\nTuesday,11\n"


def write(name, body, answer="21"):
    return f"open({name!r}, 'w').write({body!r})\nprint({answer!r})"


def run(home, task, replies, monkeypatch):
    calls = iter(replies)
    def chat(*args, **kwargs):
        reply = next(calls)
        return reply if reply == "DONE" else f"```python\n{reply}\n```"
    monkeypatch.setattr(solo.llm, "chat", chat)
    monkeypatch.setattr(solo.ternary, "seating", lambda task: ["coder"])
    result = solo.first(task, home, members=2)
    assert next(calls, None) is None
    return result


def test_selects_valid_rain_file_with_same_stdout_and_no_extra_turn(tmp_path, monkeypatch):
    bad = GOOD.replace("Wednesday,3", "Wednesday,3,7")
    out = run(tmp_path, RAIN, [write("rainfall.csv", bad), "DONE", write("rainfall.csv", GOOD), "DONE"], monkeypatch)
    assert out["agreed"] and out["tries"] == 2
    assert out["requested_files"] == out["files"] == ["rainfall.csv"]
    assert (tmp_path / "work" / "rainfall.csv").read_text() == GOOD
    decision = json.loads((tmp_path / "members" / "members.json").read_text())
    assert decision["printed_agreeing"] == [1, 2]
    assert decision["agreeing"] == [2] and decision["selected_member"] == 2
    assert "matching structured data" not in out["report"]


def test_file_conflict_calls_third_and_does_not_train_on_dissenter(tmp_path, monkeypatch):
    a, b = write("counts.json", '{"north":1,"south":3}'), write("counts.json", '{"north":2,"south":2}')
    c = write("counts.json", '{ "south": 2.0, "north": 2e0 }')
    out = run(tmp_path, "Write counts.json. Print the total.", [a, "DONE", b, "DONE", c, "DONE"], monkeypatch)
    assert out["agreed"] and out["tries"] == 3 and "matching structured data" in out["report"]
    assert json.loads((tmp_path / "work" / "counts.json").read_text()) == {"north": 2, "south": 2}
    assert json.loads((tmp_path / "members" / "members.json").read_text())["agreeing"] == [2, 3]


def test_bad_files_do_not_confirm_and_reused_run_cannot_republish(tmp_path, monkeypatch):
    task, good = "Write totals.json and tell me the total.", write("totals.json", '{"x":21}')
    run(tmp_path, task, [good, "DONE"] * 2, monkeypatch)
    out = run(tmp_path, task, ["print(21)", "DONE"] * 3, monkeypatch)
    assert not out["agreed"] and out["files"] == [] and out["requested_files"] == ["totals.json"]
    assert "missing" in out["report"]
    assert (tmp_path / "REPORT.md").read_text() == out["report"]


def test_failed_retry_cannot_overwrite_last_good_turn(tmp_path, monkeypatch):
    good = write("result.txt", "correct")
    changed = "open('result.txt','w').write('corrupt')\nraise ValueError('incomplete')"
    out = run(tmp_path, "Save result.txt and print the total.", [good, changed, "DONE", good, "DONE"], monkeypatch)
    assert out["agreed"] and (tmp_path / "work" / "result.txt").read_text() == "correct"


@pytest.mark.parametrize("task,names", [
    ("Read bills.csv and print its sum.", []),
    ("Write a summary of bills.csv.", []),
    ("Do not save ignored.csv. Print the result.", []),
    ("Write a summary of bills.csv into summary.json.", ["summary.json"]),
    ("Convert bills.csv to bills.json.", ["bills.json"]),
    ("Save a copy of bills.csv as preview.txt.", ["preview.txt"]),
    ("Create a.csv and b.json.", ["a.csv", "b.json"]),
    ('Save the report as "November totals.csv" and `day.2.json`.', ["November totals.csv", "day.2.json"]),
    ("Write a brief.\n\n(This continues a conversation. Last time: Save earlier.csv.)", []),
])
def test_input_output_names(task, names):
    assert deliverables.wanted(task) == names


def test_csv_rules_reject_ragged_rows_and_explicit_wrong_header_but_allow_quoted_cells(tmp_path):
    csv = tmp_path / "test.csv"
    task = "Save test.csv with columns note,value sorted by value."
    csv.write_text('note,value\n"multiple\nlines and a,comma",2\n')
    assert not deliverables.inspect(task, tmp_path, [csv.name])["issues"]
    csv.write_text("value,note\n2,sample\n")
    assert "header" in deliverables.inspect(task, tmp_path, [csv.name])["issues"][csv.name]
    assert not deliverables.inspect("Save test.csv using the same columns as before.", tmp_path, [csv.name])["issues"]
    csv.write_text("value,note\n2,sample,extra\n")
    assert "3 columns" in deliverables.inspect(task.replace("note,value", "value,note"), tmp_path, [csv.name])["issues"][csv.name]


def test_json_and_links(tmp_path):
    path = tmp_path / "test.json"
    def check():
        return deliverables.inspect("Write test.json", tmp_path, [path.name])
    for content in ['{"n":NaN}', '{"n":1,"n":2}', '{"n":1,']:
        path.write_text(content)
        assert check()["issues"]
    path.write_text('{"n":1.00000000000000001}')
    first = check()
    assert not first["issues"]
    path.write_text('{"n":1.00000000000000002}')
    assert first["content"] != check()["content"]
    path.unlink()
    target = tmp_path / "elsewhere"
    target.write_text('{"x":1}')
    path.symlink_to(target)
    assert check()["issues"]
    with pytest.raises(ValueError):
        deliverables.copy_files(tmp_path, [path.name], tmp_path / "out")
    path.unlink()
    if hasattr(os, "mkfifo"):
        os.mkfifo(path)
        assert check()["issues"]

def test_explicit_empty_text_file(tmp_path):
    (tmp_path / "blank.txt").touch()
    assert not deliverables.inspect("Create an empty blank.txt.", tmp_path, ["blank.txt"])["issues"]
    assert deliverables.inspect("Create blank.txt with the answer.", tmp_path, ["blank.txt"])["issues"]

def test_header_only_table_depends_on_the_request(tmp_path):
    name = "books.csv"
    (tmp_path / name).write_text("title,price\n")
    def issue(task):
        return deliverables.inspect(task, tmp_path, [name])["issues"]
    assert issue("Fetch the three books and create books.csv with columns title,price.")
    assert not issue("Filter this list to books below $1. Save books.csv with columns title,price.")
    assert not issue("Save a header-only books.csv with columns title,price.")
    assert not issue("Save books.csv without a header, exactly 1 data rows.")


def test_copy_failure_restores_previous_files(tmp_path, monkeypatch):
    from pathlib import Path
    src, dest = tmp_path / "source", tmp_path / "destination"
    src.mkdir()
    dest.mkdir()
    for folder, value in ((src, "new"), (dest, "old")):
        for name in ("a.txt", "b.txt"):
            (folder / name).write_text(value)
    replace = Path.replace
    def fail_second(self, target):
        if self.name == "b.txt" and self.parent.parent == dest and self.parent.name != ".previous":
            raise OSError("simulated publish error")
        return replace(self, target)
    monkeypatch.setattr(Path, "replace", fail_second)
    with pytest.raises(OSError):
        deliverables.copy_files(src, ["a.txt", "b.txt"], dest)
    assert [p.read_text() for p in sorted(dest.iterdir())] == ["old", "old"]


def test_simultaneous_default_run_names_are_distinct(tmp_path, monkeypatch):
    monkeypatch.setattr(solo.config, "RUNS", tmp_path)
    assert solo._home(None) != solo._home(None)

def test_failed_publication_is_recorded_as_unconfirmed(tmp_path, monkeypatch):
    # A directory occupies the requested destination. Preserve it and surface the
    # failed handoff both to the caller and to the later learner.
    (tmp_path / "work" / "result.txt").mkdir(parents=True)
    good = write("result.txt", "correct")
    out = run(tmp_path, "Save result.txt.", [good, "DONE"] * 2, monkeypatch)
    assert not out["agreed"] and not out["files"]
    assert (tmp_path / "work" / "result.txt").is_dir()
    decision = json.loads((tmp_path / "members" / "members.json").read_text())
    assert not decision["agreed"] and not decision["agreeing"] and decision["delivery_error"]


def test_order_helper_preserves_rows_and_records_raw_provenance(tmp_path, monkeypatch):
    task = "Save weights.tsv with columns item,mass sorted by mass descending. Print the total."
    raw = 'item\tmass\r\nlight\t-1\r\n"two\tA"\t+02.00\r\nempty\t0\r\n"two\nB"\t2e0\r\n'
    expected = 'item\tmass\r\n"two\tA"\t+02.00\r\n"two\nB"\t2e0\r\nempty\t0\r\nlight\t-1\r\n'
    calls = []
    monkeypatch.setattr(solo, "keep", lambda *args: calls.append(args))
    job = run(tmp_path, task, [write("weights.tsv", raw), "DONE"] * 2, monkeypatch)
    assert job["agreed"] and job["tries"] == 2 and not calls
    assert job["file_repairs"] == [{"name": "weights.tsv", "column": "mass", "direction": "descending"}]
    assert "The hive sorted weights.tsv" in job["report"]
    # Cell strings, duplicate numeric values, tie order and every record are preserved.
    import csv
    import io
    with (tmp_path / "work" / "weights.tsv").open(newline="") as file:
        assert list(csv.reader(file, delimiter="\t")) == list(csv.reader(io.StringIO(expected, newline=""), delimiter="\t"))
    for folder in ("member2", "work"):
        assert (tmp_path / "members" / folder / "weights.tsv").read_bytes() == raw.encode()
    decision = json.loads((tmp_path / "members" / "members.json").read_text())
    assert decision["agreeing"] == [] and decision["printed_agreeing"] == [1, 2]
    assert decision["file_repairs"] == job["file_repairs"]


def test_existing_ordered_member_wins_over_a_repair(tmp_path, monkeypatch):
    task = "Create readings.csv with columns label,depth. Sort by depth ascending."
    original = 'label,depth\np,8\nq,-1\n'
    ordered = 'label,depth\nq,-1\np,8\n'
    job = run(tmp_path, task, [write("readings.csv", original), "DONE", write("readings.csv", ordered), "DONE"], monkeypatch)
    assert job["agreed"] and job["tries"] == 2 and job["file_repairs"] == []
    decision = json.loads((tmp_path / "members" / "members.json").read_text())
    assert decision["selected_member"] == 2 and decision["agreeing"] == [2]
    assert (tmp_path / "work" / "readings.csv").read_text() == ordered


def test_wrong_order_without_a_second_valid_table_cannot_be_repaired(tmp_path, monkeypatch):
    task = "Create rooms.csv with columns room,capacity sorted by capacity ascending."
    one = write("rooms.csv", "room,capacity\nA,8\nB,3\n")
    broken = write("rooms.csv", "room,capacity\nC,4,2\n")
    job = run(tmp_path, task, [one, "DONE", broken, "DONE", "print(21)", "DONE"], monkeypatch)
    assert not job["agreed"] and job["file_repairs"] == [] and not job["files"]


@pytest.mark.parametrize("instruction", [
    "Save book.csv sorted by price descending, then by id ascending.",
    "Save book.csv sorted by price descending. Break ties by id.",
    "Save book.csv sorted by price descending. The bytes must match the reference.",
    "The input is sorted by price descending. Save book.csv.",
    "Save book.csv from an input sorted by price descending.",
    "Save book.csv and totals.tsv sorted by price descending.",
    "Save book.csv sorted by price.",
    "Create book.csv but do not sort by price descending.",
    "Create book.csv and compare it to samples sorted by price descending.",
    "If requested later, create book.csv sorted by price descending.",
])
def test_ambiguous_or_byte_sensitive_sort_is_left_alone(tmp_path, instruction):
    (tmp_path / "book.csv").write_text("id,price\nA,1\nB,3\n")
    assert deliverables.inspect(instruction, tmp_path, ["book.csv"])["sorts"] == {}


def test_nonnumeric_column_is_not_a_numeric_sort(tmp_path):
    name = "cities.csv"
    (tmp_path / name).write_text("city,elevation\nKyoto,30 m\nLima,150 m\n")
    checked = deliverables.inspect("Save cities.csv sorted by elevation descending.", tmp_path, [name])
    assert not checked["issues"] and not checked["sorts"]

@pytest.mark.parametrize(("phrase", "direction"), [
    ("Put the highest points first.", "descending"),
    ("List the rows with the lowest points first.", "ascending"),
])
def test_single_matching_extreme_column(tmp_path, phrase, direction):
    name = "scores.csv"
    (tmp_path / name).write_text("name,points\nA,1\nB,3\n")
    checked = deliverables.inspect(f"Create {name} with columns name,points. {phrase}", tmp_path, [name])
    assert checked["sorts"][name]["direction"] == direction

def test_sort_applies_after_filtered_rows_are_assigned_to_output(tmp_path):
    name = "fees.csv"
    (tmp_path / name).write_text("town,fee\nA,30\nB,22\n")
    task = f"Create {name} with columns town,fee. Include towns charging at least 20 in the output table, sorted by fee ascending."
    checked = deliverables.inspect(task, tmp_path, [name])
    assert deliverables.repairs(checked) == [{"name": name, "column": "fee", "direction": "ascending"}]
