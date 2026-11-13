# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.
"""Status-surface tests (2026-11-12, product stream).
Run from ~/workspace/edit-lab:
    python3 -m unittest factory.tests.test_status -v

factory/status.py assembles the hive's status ONLY from the
factory's records (registry, newest battery measurement, growth
records, newest recorded full audit) plus the live serve-time
gate (verify_files + verify_rule — the checks ServingHive.load
fails closed on). These tests build a miniature lab in a temp
dir — real artifact files whose sha256 the fixture registry
records, so the gate runs for real — and pin:

  * the battery overall is the mean of the newest battery
    record's section scores (growth_cycle.py's formula);
  * the newest audit record wins across cycle and repair records;
  * a missing registry / battery / growth / audit record raises
    StatusUnavailable (fail-closed, clear message);
  * a tampered artifact flips serving to REFUSED in the report
    instead of raising;
  * a last cycle that exists only as a run dir still reports its
    outcome: regressed battery, alert, and the repair that
    restored it.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import factory.registry as registry_mod  # noqa: E402
from factory import status as status_mod  # noqa: E402


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, doc) -> bytes:
    raw = (doc if isinstance(doc, bytes)
           else json.dumps(doc).encode())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


class _StatusBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.lab = root
        fac = root / "factory"
        art = fac / "artifacts"
        art.mkdir(parents=True)

        def entry(name, substrate="fp", held=1.0, battery=0.9):
            raw = _write(art / f"{name}.json",
                         {"name": name, "adopted": True})
            return {"name": name, "role": "serving",
                    "path": f"factory/artifacts/{name}.json",
                    "sha256": _sha(raw), "substrate": substrate,
                    "heldout_acc": held, "battery_acc": battery}

        members = []
        for mname in ("bug-a-model", "bug-b-model"):
            raw = _write(art / f"{mname}.json",
                         {"name": mname, "adopted": True})
            members.append({"name": mname, "role": "member",
                            "path": f"factory/artifacts/{mname}.json",
                            "sha256": _sha(raw)})
        wd_raw = _write(art / "wd.py", b"# waking dream fixture\n")
        jobs = ["secret-line-model", "error-class-model",
                "commit-type-model", "contract-judgment-model",
                "gap-move-model"]
        reg = {
            "registry_version": 1,
            "specialists": {
                job: {"niche": "testing",
                      "serving": entry(f"{job}-v2"),
                      "fallbacks": [], "shadow": [],
                      "substrate_default": "fp"}
                for job in jobs},
            "compositions": {"bug-pattern-composed": {
                "name": "bug-pattern-composed", "niche": "debugging",
                "members": members,
                "serving_layer": {
                    "name": "waking-dream",
                    "path": "factory/artifacts/wd.py",
                    "sha256": _sha(wd_raw), "sealed_acc": 0.8611},
                "evidence": {"fresh_sealed_baseline": {"acc": 0.5}}}},
            "tier1": {},
        }
        _write(fac / "registry.json", reg)
        _write(fac / "battery_evidence.json", {"artifacts": {}})

        # Newest battery measurement (mean of sections = 0.75).
        _write(fac / "runs" / "run-a" / "battery_after.json", {
            "battery": "whole-hive acceptance (final product)",
            "started": "2026-11-13 01:00 UTC",
            "results": {
                "classify-secret-line": {"score": 0.5,
                                         "status": "completed"},
                "tiny-hive-ops": {"score": 1.0,
                                  "status": "completed"}}})
        # One recorded growth cycle with a clean full audit.
        _write(root / "growth" / "growth-cycle-001.json", {
            "cycle_id": "growth-cycle-001",
            "date": "2026-11-12 00:00 UTC", "rolled_back": False,
            "battery_overall_before": 0.9,
            "battery_overall_after": 0.91,
            "attempts": [{"child": "bug-a2-model", "born": True},
                         {"child": "bug-b2-model", "born": False}],
            "audit": {"ok": True, "failures": []}})
        # A NEWER audit rides in a repair record.
        _write(fac / "runs" / "repair-z" / "repair-result.json", {
            "repair_id": "repair-z", "date": "2026-11-13 02:00 UTC",
            "battery_overall_after": 0.95,
            "audit": {"ok": True, "failures": []}})

        patcher = mock.patch.object(
            registry_mod, "BATTERY_EVIDENCE_PATH",
            fac / "battery_evidence.json")
        patcher.start()
        self.addCleanup(patcher.stop)

    def collect(self):
        return status_mod.collect_status(self.lab)


class TestCollectStatus(_StatusBase):
    def test_happy_path_reads_the_records(self):
        st = self.collect()
        self.assertTrue(st["serving"]["healthy"])
        self.assertEqual(st["serving"]["failures"], [])
        self.assertEqual(st["battery"]["overall"], 0.75)
        self.assertEqual(st["battery"]["source"], "run-a")
        self.assertEqual(st["battery"]["sections"], 2)
        niches = {n["short"]: n for n in st["niches"]}
        self.assertEqual(
            sorted(niches),
            ["bug", "commit", "contract", "error", "gap", "secret"])
        self.assertEqual(niches["secret"]["serving"],
                         "secret-line-model-v2")
        self.assertEqual(niches["bug"]["members"], 2)
        self.assertEqual(niches["bug"]["sealed_acc"], 0.8611)
        self.assertEqual(niches["bug"]["raw_composed_acc"], 0.5)
        self.assertEqual(st["growth"]["count"], 1)
        last = st["growth"]["last"]
        self.assertEqual(last["cycle_id"], "growth-cycle-001")
        self.assertEqual(last["battery_before"], 0.9)
        self.assertEqual(last["battery_after"], 0.91)
        self.assertEqual(last["births"], ["bug-a2-model"])
        self.assertFalse(last["rolled_back"])
        self.assertTrue(last["audit_ok"])

    def test_newest_audit_record_wins(self):
        st = self.collect()
        self.assertEqual(st["audit"]["source"], "repair-z")
        self.assertTrue(st["audit"]["ok"])
        self.assertEqual(st["audit"]["failures"], 0)

    def test_render_mentions_every_surface(self):
        text = status_mod.render(self.collect())
        for needle in ("HIVE STATUS", "HEALTHY", "0.75",
                       "secret", "bug-pattern-composed",
                       "growth-cycle-001", "repair-z"):
            self.assertIn(needle, text)


class TestFailClosed(_StatusBase):
    def test_missing_registry(self):
        (self.lab / "factory" / "registry.json").unlink()
        with self.assertRaises(status_mod.StatusUnavailable) as cm:
            self.collect()
        self.assertIn("registry", str(cm.exception))

    def test_missing_battery(self):
        (self.lab / "factory" / "runs" / "run-a"
         / "battery_after.json").unlink()
        with self.assertRaises(status_mod.StatusUnavailable) as cm:
            self.collect()
        self.assertIn("battery", str(cm.exception))

    def test_missing_growth_records(self):
        (self.lab / "growth" / "growth-cycle-001.json").unlink()
        with self.assertRaises(status_mod.StatusUnavailable) as cm:
            self.collect()
        self.assertIn("growth", str(cm.exception))

    def test_missing_audit_record(self):
        (self.lab / "growth" / "growth-cycle-001.json").unlink()
        _write(self.lab / "growth" / "growth-cycle-001.json", {
            "cycle_id": "growth-cycle-001",
            "date": "2026-11-12 00:00 UTC", "rolled_back": False,
            "battery_overall_before": 0.9,
            "battery_overall_after": 0.91, "attempts": []})
        (self.lab / "factory" / "runs" / "repair-z"
         / "repair-result.json").unlink()
        with self.assertRaises(status_mod.StatusUnavailable) as cm:
            self.collect()
        self.assertIn("audit", str(cm.exception))


class TestServingGate(_StatusBase):
    def test_tampered_artifact_reports_refused_not_raises(self):
        victim = (self.lab / "factory" / "artifacts"
                  / "secret-line-model-v2.json")
        victim.write_bytes(b'{"name": "tampered"}')
        st = self.collect()
        self.assertFalse(st["serving"]["healthy"])
        self.assertTrue(st["serving"]["failures"])
        text = status_mod.render(st)
        self.assertIn("REFUSED", text)


class TestRunDirOnlyCycle(_StatusBase):
    def test_last_cycle_from_run_dir_with_repair(self):
        run = self.lab / "factory" / "runs" / "growth-cycle-002"
        _write(run / "battery_before.json", {
            "started": "2026-11-12 20:00 UTC",
            "results": {"a": {"score": 0.9, "status": "completed"}}})
        _write(run / "battery_after.json", {
            "started": "2026-11-12 20:30 UTC",
            "results": {"a": {"score": 0.8, "status": "completed"}}})
        (run / "births" / "wrong-operator-expression").mkdir(
            parents=True)
        _write(self.lab / "growth" / "ALERT-growth-cycle-002.md",
               b"# alert\n")
        _write(self.lab / "factory" / "runs" / "repair-cycle002-fix"
               / "repair-result.json", {
                   "repair_id": "repair-cycle002-fix",
                   "date": "2026-11-12 21:00 UTC",
                   "battery_overall_after": 0.9,
                   "audit": {"ok": True, "failures": []}})
        st = self.collect()
        self.assertEqual(st["growth"]["count"], 2)
        last = st["growth"]["last"]
        self.assertEqual(last["cycle_id"], "growth-cycle-002")
        self.assertEqual(last["battery_before"], 0.9)
        self.assertEqual(last["battery_after"], 0.8)
        self.assertTrue(last["alert"])
        self.assertEqual(last["repair"]["repair_id"],
                         "repair-cycle002-fix")
        self.assertEqual(last["repair"]["battery_overall_after"], 0.9)
        text = status_mod.render(st)
        self.assertIn("repaired by repair-cycle002-fix", text)


if __name__ == "__main__":
    unittest.main()
