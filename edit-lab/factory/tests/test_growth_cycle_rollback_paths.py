# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.
"""Rollback-path regression tests for the cycle runner functions
(cycle-007 repair, 2026-11-12).
Run from ~/workspace/edit-lab:
    python3 -m unittest factory.tests.test_growth_cycle_rollback_paths -v

The bug: the cycle-006 repair added the pre-cycle model-file
snapshot (_snapshot_model_files) to run_cycle only. run_cycle2
and run_cycle3 passed model_snapshots=... to _rollback without
ever taking the snapshot, so any rollback in those paths died
with `NameError: name 'model_snapshots' is not defined` BEFORE
restoring anything — cycle 007's two regressed births stayed
serving (battery 0.941 -> 0.9375, sealed bug-pattern 0.8611 ->
0.8333) with the rollback unexecuted.

These tests drive the real run_cycle2 / run_cycle3 functions
with the heavy pieces stubbed (training, battery, judge, audit):
a birth overwrites both incumbent model files, the served
battery then regresses, and the cycle's own rollback must
restore the incumbents byte-for-byte from the snapshot the
cycle itself took (and persisted under snapshots/models/).
On the pre-fix code both tests raise the NameError."""
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from factory import champion as champion_mod  # noqa: E402
from factory import growth_cycle as gc  # noqa: E402
from factory import name_intent as name_intent_mod  # noqa: E402
import factory.registry as registry_mod  # noqa: E402

EXPR = "bug-wrong-operator-expression-model"
INDEX = "bug-off-by-one-index-model"
EXPR_BYTES = json.dumps({"name": EXPR, "w": [1, 2, 3]}).encode()
INDEX_BYTES = json.dumps({"name": INDEX, "w": [4, 5]}).encode()


def _battery(run_dir, tag):
    sealed = 0.8611 if tag == "before" else 0.8333
    return {
        "bug-pattern-composed-sealed-v2": {
            "score": sealed, "status": "completed", "detail": ""},
        "classify-secret-line": {
            "score": 1.0, "status": "completed", "detail": ""},
    }


class _CycleRollbackPathBase(unittest.TestCase):
    CYCLE_ID = "growth-cycle-997"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.models = root / "models"
        self.models.mkdir()
        (self.models / f"{EXPR}.json").write_bytes(EXPR_BYTES)
        (self.models / f"{INDEX}.json").write_bytes(INDEX_BYTES)
        (self.models / "composer_config.json").write_bytes(b"cfg")
        self.lab = root / "lab"
        (self.lab / "waking-dream").mkdir(parents=True)
        (self.lab / "waking-dream" / "results.json").write_bytes(b"wd")
        (self.lab / "results").mkdir(parents=True)
        self.factory_dir = root / "factory"
        self.factory_dir.mkdir()
        (self.factory_dir / "registry.json").write_bytes(b"{}")
        self.growth_dir = root / "growth"
        self.growth_dir.mkdir()
        self.nidata = root / "nidata"
        self.nidata.mkdir()
        (self.nidata / "name_intent_train.json").write_text("[]")

        stack = ExitStack()
        self.addCleanup(stack.close)
        self.addCleanup(self.tmp.cleanup)
        p = stack.enter_context
        p(mock.patch.object(gc, "MODELS_DIR", self.models))
        p(mock.patch.object(gc, "LAB_ROOT", self.lab))
        p(mock.patch.object(gc, "FACTORY_DIR", self.factory_dir))
        p(mock.patch.object(gc, "GROWTH_DIR", self.growth_dir))
        p(mock.patch.object(registry_mod, "write_registry",
                            lambda: None))
        p(mock.patch.object(
            registry_mod, "load_registry",
            lambda: {"compositions": {"bug-pattern-composed": {
                "evidence": {"fresh_sealed_baseline": {"acc": 0.5}}}}}))
        p(mock.patch.object(champion_mod, "ensure_record",
                            lambda: {"version": 1, "recipe": {}}))
        p(mock.patch.object(name_intent_mod, "DATA_DIR", self.nidata))
        p(mock.patch.object(name_intent_mod, "load_train", lambda: []))
        p(mock.patch.object(name_intent_mod, "load_held", lambda: []))
        p(mock.patch.object(gc, "harvest_failures", lambda items: {}))
        p(mock.patch.object(gc, "learned_say_experiment", lambda: {}))
        p(mock.patch.object(
            gc, "learned_say_experiment_v2",
            lambda: {"composed_acc": {"routed": 0.5, "mean": 0.5,
                                      "learned": 0.4}}))
        p(mock.patch.object(gc, "replay_set", lambda: []))
        p(mock.patch.object(gc, "cap_intent", lambda *a, **k: []))
        p(mock.patch.object(gc, "measure_served_battery", _battery))
        p(mock.patch.object(
            gc, "_sealed_judge",
            lambda cycle_id, previous_acc=None: {
                "composed_acc": 0.5, "per_class_recall": {}}))
        # Gate 3′ (2026-11-12) is a serving-verification piece
        # like the judge/refresh above and is stubbed neutral
        # here — this file's subject is the rollback path. The
        # gate's own suite (incl. an in-cycle3 simulation) is
        # factory/tests/test_gate3_prime.py.
        p(mock.patch.object(
            gc, "_gate3_prime",
            lambda out, pre, run_dir, lineage, cycle_id: out))
        p(mock.patch.object(gc, "_refresh_waking_dream_results",
                            lambda cycle_id: {}))
        p(mock.patch.object(gc, "_full_audit",
                            lambda: {"ok": True, "failures": []}))
        p(mock.patch.object(gc, "write_report", lambda cycle: None))

    def _fake_birth(self, cls, slice_name):
        child = f"bug-{cls}-{slice_name}-model"
        (gc.MODELS_DIR / f"{child}.json").write_bytes(
            b"child-bytes-" + child.encode())
        return {"born": True, "child": child, "rejection": None}

    def _assert_restored(self, cycle):
        self.assertTrue(cycle["rolled_back"])
        # Incumbents back byte-for-byte.
        self.assertEqual((self.models / f"{EXPR}.json").read_bytes(),
                         EXPR_BYTES)
        self.assertEqual((self.models / f"{INDEX}.json").read_bytes(),
                         INDEX_BYTES)
        # The cycle itself took and persisted the model snapshot.
        snap_models = (self.factory_dir / "runs" / self.CYCLE_ID
                       / "snapshots" / "models")
        self.assertEqual((snap_models / f"{EXPR}.json").read_bytes(),
                         EXPR_BYTES)
        self.assertEqual((snap_models / f"{INDEX}.json").read_bytes(),
                         INDEX_BYTES)
        # The rollback lineage event names both as restored.
        events = [json.loads(ln) for ln in
                  (self.factory_dir / "runs" / self.CYCLE_ID
                   / "lineage.jsonl").read_text().splitlines()]
        rb = [e for e in events if e.get("kind") == "growth_rollback"]
        self.assertEqual(len(rb), 1)
        self.assertEqual(sorted(rb[0]["restored"]),
                         sorted([EXPR, INDEX]))
        self.assertEqual(rb[0]["removed"], [])


class TestRunCycle3RollbackPath(_CycleRollbackPathBase):
    CYCLE_ID = "growth-cycle-997"

    def test_cycle3_rollback_restores_models(self):
        with mock.patch.object(
                gc.growth, "attempt_birth",
                lambda cls, slice_name, *a, **k:
                    self._fake_birth(cls, slice_name)):
            cycle = gc.run_cycle3(self.CYCLE_ID)
        self._assert_restored(cycle)


class TestRunCycle2RollbackPath(_CycleRollbackPathBase):
    CYCLE_ID = "growth-cycle-998"

    def test_cycle2_rollback_restores_models(self):
        with mock.patch.object(
                gc, "_attempt_target_cycle2",
                lambda cls, slice_name, *a, **k:
                    self._fake_birth(cls, slice_name)):
            cycle = gc.run_cycle2(self.CYCLE_ID)
        self._assert_restored(cycle)


if __name__ == "__main__":
    unittest.main()
