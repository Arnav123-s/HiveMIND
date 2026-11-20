"""Exercise local bank publication across independent writers, interrupted writes and legacy records."""

import json
import multiprocessing
import os
import stat
from concurrent.futures import ProcessPoolExecutor

import pytest

from training.experiments.fieldwork import work as fw


def member(source, description="Double the measurement"):
    return dict(task="adjust", description=description, source=source,
                digest=fw.fingerprint(source), public=2, validation=3, parents=[])


def test_concurrent_processes_retain_each_qualified_source_and_contract_once(tmp_path):
    bank = tmp_path / "new" / "bank"
    rows = [member("first"), member("second"), member("first", "Scale the measurement")]
    with ProcessPoolExecutor(3, mp_context=multiprocessing.get_context("spawn")) as writers:
        tasks = [writers.submit(fw.admit, bank, row) for row in rows * 4]
        for task in tasks:
            task.result(timeout=30)
    assert sorted(fw.load_bank(bank), key=lambda row: (row["source"], row["description"])) == [rows[0], rows[2], rows[1]]
    assert len(list(bank.iterdir())) == len(rows)


def abandon_publication(bank, row, after_link):
    link = os.link

    def terminate(source, target):
        if after_link:
            link(source, target)
        # Simulate loss of the whole process. Context managers cannot clean up.
        os._exit(73)

    os.link = terminate
    fw.admit(bank, row)


@pytest.mark.parametrize("after_link", [False, True])
def test_killed_publisher_leaves_only_complete_visible_records_and_can_retry(tmp_path, after_link):
    old, new = member("first"), member("second")
    fw.admit(tmp_path, old)
    writer = multiprocessing.get_context("spawn").Process(target=abandon_publication,
                                                         args=(tmp_path, new, after_link))
    writer.start()
    writer.join(30)
    assert writer.exitcode == 73
    assert {r["source"] for r in fw.load_bank(tmp_path)} == ({"first", "second"} if after_link else {"first"})
    # A different admission must not truncate an inode already linked by the dead writer.
    third = member("third")
    fw.admit(tmp_path, third)
    fw.admit(tmp_path, new)
    assert {r["source"] for r in fw.load_bank(tmp_path)} == {"first", "second", "third"}
    assert len(list(tmp_path.iterdir())) == 3


def test_incomplete_or_colliding_names_never_receive_credit_or_get_overwritten(tmp_path):
    first, second = member("same", "First"), member("same", "Second")
    fw.admit(tmp_path, first)
    legacy = tmp_path / (first["digest"] + ".json")
    legacy_bytes = legacy.read_bytes()
    other = tmp_path / (second["digest"] + "-" + fw.contract_id(second) + ".json")
    other.write_bytes(b"{")
    with pytest.raises(FileExistsError, match="occupied"):
        fw.admit(tmp_path, second)
    assert legacy.read_bytes() == legacy_bytes and other.read_bytes() == b"{"
    assert fw.load_bank(tmp_path) == [first]
    with pytest.raises(ValueError, match="checked record"):
        fw.admit(tmp_path, dict(second, digest=fw.fingerprint("different")))
    assert len(list(tmp_path.iterdir())) == 2


def test_legacy_alias_is_neither_published_twice_nor_counted_twice(tmp_path):
    row = member("v1")
    scoped = tmp_path / (row["digest"] + "-" + fw.contract_id(row) + ".json")
    scoped.write_text(json.dumps(row))
    fw.admit(tmp_path, dict(row, validation=999))
    assert list(tmp_path.iterdir()) == [scoped] and fw.load_bank(tmp_path) == [row]
    # Existing directories can contain both layouts from before deduplication.
    legacy = dict(row, validation=2)
    (tmp_path / (row["digest"] + ".json")).write_text(json.dumps(legacy))
    assert fw.load_bank(tmp_path) == [legacy]


@pytest.mark.parametrize("fail_at", ["file", "directory_after_link"])
def test_sync_failure_is_reported_and_retry_is_idempotent(tmp_path, monkeypatch, fail_at):
    row = member("method")
    real_sync, real_link = os.fsync, os.link
    linked = False

    def record_link(source, target):
        nonlocal linked
        real_link(source, target)
        linked = True

    def interrupt(fd):
        regular = stat.S_ISREG(os.fstat(fd).st_mode)
        if (regular and fail_at == "file") or (not regular and linked and fail_at == "directory_after_link"):
            raise OSError("disk sync failed")
        real_sync(fd)

    with monkeypatch.context() as m:
        m.setattr(os, "fsync", interrupt)
        m.setattr(os, "link", record_link)
        with pytest.raises(OSError, match="disk sync failed"):
            fw.admit(tmp_path, row)
    fw.admit(tmp_path, row)
    assert fw.load_bank(tmp_path) == [row] and len(list(tmp_path.iterdir())) == 1
