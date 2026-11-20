"""The diagnostics must preserve the original worker's bytes separately from published work."""
import hashlib
import json
import os

import pytest

from training.member_evidence import capture, collect


def worker(home, seat, files, hashes=None, directory=None):
    directory = directory or ("work" if seat == 1 else f"member{seat}")
    work = home / directory
    work.mkdir(parents=True)
    for name, data in files.items():
        (work / name).write_bytes(data)
    if hashes is None:
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    receipt = {"work": str(work), "delivery": {"byte_hashes": hashes}, "answer": "irrelevant"}
    (home / f"member{seat}.json").write_text(json.dumps(receipt))
    return work


def test_collect_archives_requested_files_by_seat(tmp_path):
    root = tmp_path / "exam"
    home = root / "sitting" / "job" / "members"
    home.mkdir(parents=True)
    (home / "TASK.md").write_text("Save card.txt and marks.json.")
    first = worker(home, 1, {"card.txt": b"first", "spare.py": b"internal"})
    worker(home, 2, {"marks.json": b"false"}, directory="member2-retry-xyz")
    (home / "REPORT.md").write_text("Withheld.")
    (home.parent / "exam.json").write_text('{"ok": false}')
    out = root / "worker-evidence"

    assert collect(root, out) == 1
    evidence = out / "sitting" / "job"
    manifest = json.loads((evidence / "manifest.json").read_text())
    first_files, second_files = [seat["files"] for seat in manifest["seats"]]
    assert set(first_files) == set(second_files) == {"card.txt", "marks.json"}
    assert first_files["marks.json"] == second_files["card.txt"] == {"status": "missing"}
    for files, name, expected in ((first_files, "card.txt", b"first"), (second_files, "marks.json", b"false")):
        record = files[name]
        assert record["matched_submission_hash"]
        assert (evidence / record["path"]).read_bytes() == expected
        assert record["sha256"] == hashlib.sha256(expected).hexdigest()
    assert not list(out.rglob("spare.py"))
    assert (home / "REPORT.md").read_text() == "Withheld."
    assert (home.parent / "exam.json").read_text() == '{"ok": false}'
    (first / "card.txt").write_text("later")
    with pytest.raises(FileExistsError):
        collect(root, out)
    assert (evidence / first_files["card.txt"]["path"]).read_bytes() == b"first"


def test_changed_files_and_other_workers_paths_are_excluded(tmp_path):
    home = tmp_path / "g" / "job" / "members"
    home.mkdir(parents=True)
    (home / "TASK.md").write_text("Save card.txt.")
    first = worker(home, 1, {"card.txt": b"original"})
    (first / "card.txt").write_bytes(b"overwritten")
    second = worker(home, 2, {})
    (second / "card.txt").symlink_to(first / "card.txt")
    (home / "member3.json").write_text(json.dumps({"work": str(first)}))
    (home / "member4.json").write_text("interrupted receipt")
    out = tmp_path / "evidence"
    assert collect(tmp_path, out) == 1
    manifest = json.loads((out / "g/job/manifest.json").read_text())
    assert [s["files"]["card.txt"]["status"] for s in manifest["seats"]] == [
        "changed since submission", "unreadable or not a regular file", "no worker directory", "no worker directory"
    ]
    assert not list(out.rglob("card.txt"))


def test_capture_ignores_text_only_and_skips_damaged_siblings(tmp_path, capsys):
    out = tmp_path / "evidence"
    for name, contents in (("text", b"Say hello."), ("damaged", b"\xff"), ("file", b"Save card.txt.")):
        home = tmp_path / "g" / name / "members"
        home.mkdir(parents=True)
        (home / "TASK.md").write_bytes(contents)
    assert collect(tmp_path, out) == 1
    assert "damaged" in capsys.readouterr().err
    assert list((out / "g").iterdir()) == [out / "g/file"]
    existing = tmp_path / "already"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        capture("Save card.txt.", [], existing)
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "other")
    with pytest.raises(FileExistsError):
        collect(tmp_path, dangling)


def test_run_with_fewer_workers_excludes_receipts_from_previous_attempt(tmp_path):
    home = tmp_path / "g/job/members"
    home.mkdir(parents=True)
    worker(home, 3, {"card.txt": b"from a prior attempt"})
    receipt = home / "member3.json"
    task = home / "TASK.md"
    task.write_text("Save card.txt.")
    # Use explicit times so this regression is independent of the filesystem clock resolution.
    start = task.stat().st_mtime_ns
    os.utime(receipt, ns=(start - 1_000_000_000, start - 1_000_000_000))
    worker(home, 1, {"card.txt": b"current"})
    out = tmp_path / "evidence"
    assert collect(tmp_path, out) == 1
    manifest = json.loads((out / "g/job/manifest.json").read_text())
    assert [seat["seat"] for seat in manifest["seats"]] == [1]


def test_current_roster_limits_seats_even_with_equal_timestamps(tmp_path):
    home = tmp_path / "g/job/members"
    home.mkdir(parents=True)
    task = home / "TASK.md"
    task.write_text("Save card.txt.")
    worker(home, 1, {"card.txt": b"current"})
    worker(home, 2, {"card.txt": b"previous"})
    (home / "members.json").write_text(json.dumps({"who": ["first"]}))
    moment = task.stat().st_mtime_ns
    for path in home.glob("*.json"):
        os.utime(path, ns=(moment, moment))
    out = tmp_path / "evidence"
    assert collect(tmp_path, out) == 1
    manifest = json.loads((out / "g/job/manifest.json").read_text())
    assert [seat["seat"] for seat in manifest["seats"]] == [1]
