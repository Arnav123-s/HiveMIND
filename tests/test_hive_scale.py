import hashlib
from concurrent.futures import ThreadPoolExecutor
from itertools import product

import numpy as np
import pytest

from training.experiments.hive_scale import Readings
from training.experiments.hive_scale_archive import Archive, Workers
from training.experiments.hive_scale_cells import BYTES, Cell, draw_cell, forward, inverse, learn, regrow
from training.experiments.hive_scale_certify import certify, replay
from training.experiments.hive_scale_regions import route
from training.experiments.hive_scale_router import Directory, Index, discover, fixed_scans, verified


@pytest.fixture
def bank(tmp_path):
    rng = np.random.default_rng(83)
    members = []
    for _ in range(8):
        child, receipt = learn(draw_cell(rng), rng.permutation(BYTES))
        members.append((child.archive(), receipt))
    archive = Archive.create(tmp_path / "bank", members, region_size=4)
    directory = Directory(archive, np.array([29, 63, 153], np.uint8))
    return archive, directory, members


def test_cell_fits_replays_and_inverts_every_code():
    rng = np.random.default_rng(198)
    parent = draw_cell(rng)
    child, receipt = learn(parent, rng.permutation(BYTES))
    packed = child.archive()
    assert len(packed) == 16 and len(receipt) < 64
    assert regrow(receipt, hashlib.sha256(packed).digest()) == packed
    output = Cell.restore(packed).neural(BYTES)
    assert np.array_equal(output, parent.neural(BYTES))
    assert np.array_equal(inverse(child.tables(), output), BYTES)
    with pytest.raises(ValueError):
        regrow(receipt[:-1], hashlib.sha256(packed).digest())


def test_joins_match_brute_force_on_arbitrary_midpoints(bank):
    _, d, _ = bank
    for length, program in ((2, (5, 2)), (4, (6, 3, 1, 5))):
        xs = d.anchors if length == 4 else np.array([7, 84, 119], np.uint8)
        target = d.predict(program, xs)
        brute = {p for p in product(range(d.size), repeat=length) if np.array_equal(d.predict(p, xs), target)}
        assert set(d.candidates(xs, target, length, "linear")) == brute
        assert set(d.candidates(xs, target, length, "pairs")) == brute
    collision = Index(np.zeros((4, 3), np.uint8))
    assert collision.join(np.zeros(3, np.uint8), cap=3) is None
    assert len(collision.join(np.zeros(3, np.uint8), cap=4)) == 4
    assert verified(d, [program, program], xs, target) == (program, "ok")


def test_shared_reading_and_wrong_region_fallback(bank):
    archive, d, _ = bank
    p = (0, 3, 7, 5)
    mid = d.predict(p[:2], BYTES)
    gold = d.predict(p[2:], mid)
    task = Readings(4, d.anchors, np.array([4, 37, 201], np.uint8), mid, gold)
    with pytest.raises(ValueError):
        task.observe(np.array([223], np.uint8), True)
    plan, why, _ = discover(d, task, "checkpoint", {})
    assert why == "ok" and plan == p and (task.end_bytes, task.mid_bytes) == (6, 6)
    regions = [Directory(archive, d.anchors, range(i, i + 4)) for i in (0, 4)]
    assert route(d, regions, (1, 1), task, "region_only")[0] is None
    assert route(d, regions, (1, 1), task, "fallback") == (p, 1)
    worker = Workers(archive, d.groups)
    assert np.array_equal(worker.execute(plan, BYTES), gold) and worker.peak == 2
    for depth, scan in fixed_scans(8).items():
        assert len(scan) == min(8 ** depth, 256)


def test_recovery_handles_lost_region_corrupt_replica_and_concurrent_repairs(bank, tmp_path):
    archive, d, members = bank
    (archive.root / "region-0.bin").unlink()
    assert Workers(archive, d.groups).execute((0,), BYTES) is None
    with ThreadPoolExecutor(max_workers=3) as pool:
        assert list(pool.map(archive.repair, [0, 0, 0])) == [members[0][0]] * 3
    assert archive.read(0) == members[0][0]
    (archive.root / "teaching.bin").write_bytes(b"")
    assert Workers(archive, d.groups, heal=True).take(1) is None
    assert not (archive.root / "restored" / "1").exists()
    doubles = Archive.create(tmp_path / "twins", members * 2, region_size=8)
    index = Directory(doubles, d.anchors)
    assert index.groups == [[i, i + 8] for i in range(8)]
    path = doubles.root / "region-0.bin"
    data = bytearray(path.read_bytes())
    data[0] ^= 1
    path.write_bytes(data)
    worker = Workers(doubles, index.groups)
    assert np.array_equal(worker.execute((0,), BYTES), d.predict((0,), BYTES))
    assert worker.unavailable == 1 and worker.repairs == 0


def test_disjoint_witnesses_recover_exception_and_bind_revision_and_members(bank):
    archive, d, _ = bank
    p = (2, 1, 3, 7)
    mid = d.predict(p[:2], BYTES)
    expected = d.predict(p[2:], mid)
    expected[[0, 3]] = expected[[3, 0]]
    reads = []
    def middle(x):
        reads.extend(x.tolist())
        return mid[x]
    record = certify(d, 4, None, "unit7/v2", lambda x: expected[x], middle)
    assert len(bytes.fromhex(record["edits"])) == 4 and reads == list(range(9))
    # Local member positions may change on restart. The recipe identifies members by fingerprint.
    reordered = Directory(archive, d.anchors, reversed(range(8)))
    assert np.array_equal(replay(record, reordered, "unit7/v2", BYTES), expected)
    with pytest.raises(ValueError, match="revision"):
        replay(record, d, "unit7/v3", BYTES)
    with pytest.raises(KeyError):
        replay(record, Directory(archive, d.anchors, range(2)), "unit7/v2", BYTES)


def test_operation_memory_updates_and_retries_a_single_revision(tmp_path):
    from training.experiments.hive_scale_work_orders import exercise
    scores = exercise(tmp_path, 8)["counts"]
    assert scores["typed-known"]["correct_outcomes"] == 12
    assert scores["typed-new_word"]["writes"] == 0
    assert scores["typed-after_teaching"]["correct_outcomes"] == 4
    assert scores["typed-after_unsupported"]["writes"] == 0


def test_damaged_repair_copy_can_fall_back_to_healthy_primary(bank):
    archive, _, members = bank
    (archive.root / "restored" / "0").write_bytes(b"incomplete")
    assert archive.read(0) == members[0][0]


def test_birth_school_values_completed_pairs_and_preserves_unqualified_members():
    from collections import Counter
    from training.experiments.hive_scale_births import choose, colony, fixture
    demand = Counter({(1, 2): 6, (1, 3): 6, (4, 5): 10})
    assert choose("frequency", {0}, demand, {}, None) == [1, 4]
    assert choose("pairs", {0}, demand, {}, None) == (4, 5)
    world = fixture(1553)
    frequency, pairs = (colony(1553, world, p) for p in ("frequency", "pairs"))
    assert frequency["teaching_readings"] == pairs["teaching_readings"] == 672
    assert [r["deaths"] for r in frequency["epochs"]] == [r["deaths"] for r in pairs["epochs"]]
    assert pairs["completed"] > frequency["completed"]
    assert any(epoch["unqualified_living"] for epoch in pairs["epochs"])


def test_functional_twins_keep_both_fingerprints_across_a_directory_reorder(tmp_path):
    cell = Cell(np.zeros((8, 4), np.int8), np.full(8, -2, np.int8))
    twin = Cell(cell.weights.copy(), cell.thresholds.copy())
    twin.weights[0, 0] = 1  # Both neurons still fire on every nibble at threshold -2.
    assert cell.archive() != twin.archive() and np.array_equal(cell.neural(BYTES), twin.neural(BYTES))
    a = Archive.create(tmp_path / "twins", [(m.archive(), b"") for m in (cell, twin)])
    original = Directory(a, [1, 2, 3])
    reordered = Directory(a, [1, 2, 3], [1, 0])
    assert original.size == reordered.size == 1
    r = {"version": "v1", "members": original.digests * 2, "edits": ""}
    assert np.array_equal(replay(r, reordered, "v1", BYTES), original.predict((0, 0), BYTES))
