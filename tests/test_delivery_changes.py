"""The generation record compares the same individual final deliveries across exam arms."""
import json

from training import grow_record, reads


KIND = "a sum in words"


def row(index, ok, seed=123, **updates):
    return {"id": f"e{seed}_{index:02}", "task": f"private prompt {index}", "kind": KIND, "ok": ok} | updates


def sitting(folder, arm, slot, rows, *, seed=123, code="7654321", total=None, passed=None):
    d = folder / f"gate-{arm}-{slot}"
    d.mkdir(parents=True, exist_ok=True)
    data = {"summary": {"seed": seed, "code": code, "tasks": len(rows) if total is None else total,
                        "passed": sum(r.get("ok") is True for r in rows) if passed is None else passed, "minutes": 1},
            "tasks": rows}
    (d / "exam_mixed.json").write_text(json.dumps(data))


def test_real_record_and_read_include_identified_gains_and_losses(tmp_path, monkeypatch):
    gate, got = tmp_path / "gate", tmp_path / "got"
    sitting(gate, "before", 1, [row(0, False), row(1, True), row(2, False), row(3, True)])
    sitting(gate, "after", 1, [row(3, True), row(2, False), row(1, False), row(0, True)])
    got.mkdir()
    cell = "t80.g8code"
    (got / (cell + ".gguf")).write_bytes(b"fixture")
    (got / (cell + ".json")).write_text('{"rows":2,"seconds":30}')
    body, record = tmp_path / "body.json", tmp_path / "record.jsonl"
    body.write_text('{"dna":"t80","generation":7,"cells":["g7code"]}')
    monkeypatch.setattr(grow_record, "BODY", body)
    monkeypatch.setattr(grow_record, "STRENGTHS", tmp_path / "strengths.json")
    monkeypatch.setattr(grow_record, "RECORD", record)
    grow_record.gate([str(gate), str(got), "g8", "--dna", "t80", "--grow"])
    line = json.loads(record.read_text())
    audit = line["paired"]["deliveries"]
    assert audit["sat"] == {"before": 4, "after": 4} and audit["comparable"] == 4
    assert audit["counts"] == {"both_pass": 1, "both_fail": 1, "gained": 1, "lost": 1}
    assert audit["changed"] == {"gained": [{"id": "e123_00", "kind": KIND}], "lost": [{"id": "e123_01", "kind": KIND}]}
    report = "\n".join(reads.delivery_changes_table(line))
    assert "4 matched" in report and "e123_01" in report and "e123_00" in report
    assert "private prompt" not in json.dumps(audit) + report


def test_excludes_ambiguous_ids_mismatches_incomplete_rows_and_unpaired_seats(tmp_path):
    before = [row(i, True) for i in range(8)]
    after = [row(0, False), row(1, True), row(1, False), row(2, True, task="different"),
             row(3, True, kind="the weekday of a date"), row(4, 1),
             row(5, True, id="../bad"), row(6, False, task=""), row(7, True, kind=[])]
    sitting(tmp_path, "before", 1, before)
    sitting(tmp_path, "after", 1, after)
    # Code absent or different, summary seed error, an internal contradiction, or a seat only on one side.
    for slot, old, new in [(2, None, None), (3, "1234567", "1234568"), (4, "1234567", "1234567"),
                           (5, "1234567", "1234567")]:
        seed = 200 + slot
        sitting(tmp_path, "before", slot, [row(0, True, seed)], seed=seed, code=old)
        sitting(tmp_path, "after", slot, [row(0, False, seed)], seed=seed + (slot == 4), code=new,
                passed=1 if slot == 5 else 0)
    sitting(tmp_path, "before", 6, [row(0, True, 300)], seed=300)
    sitting(tmp_path, "after", 7, [row(0, True, 300)], seed=300)
    # An older summary has no individual trial details at all.
    sitting(tmp_path, "after", 8, [], total=4, passed=2)
    audit = grow_record.delivery_changes(tmp_path)
    assert audit["sat"] == {"before": 13, "after": 18}
    assert audit["comparable"] == 1 and audit["counts"]["lost"] == 1
    assert audit["changed"]["lost"] == [{"id": "e123_00", "kind": KIND}]
    assert "not recorded" in "\n".join(reads.delivery_changes_table({"paired": {}}))
