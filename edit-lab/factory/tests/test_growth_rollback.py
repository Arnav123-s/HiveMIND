# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.
"""Rollback model-file regression tests (cycle-006 repair, 2026-11-12).
Run from ~/workspace/edit-lab:
    python3 -m unittest factory.tests.test_growth_rollback -v

The bug: a growth birth OVERWRITES the incumbent serving model
file of the same name (children reuse names every cycle), and
rollback used to unlink the child file outright — so a rolled-back
cycle deleted the serving specialists instead of restoring them
(cycle 006: bug-wrong-operator-expression-model and
bug-off-by-one-index-model lost; served battery 0.941 -> degraded,
post-rollback audit FAILED).

These tests simulate an adoption + rollback with pre-existing
serving model files, with the models dir and lab root redirected
to a temp tree, and assert the originals come back byte-for-byte
while a genuinely new child file is removed."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from factory import growth_cycle  # noqa: E402
from factory.lineage import LineageLog  # noqa: E402
import factory.registry as registry_mod  # noqa: E402

EXPR = "bug-wrong-operator-expression-model"
INDEX = "bug-off-by-one-index-model"
NEW_CHILD = "bug-swapped-operands-plain-model"


class TestRollbackRestoresModels(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.models = root / "models"
        self.models.mkdir()
        self.lab = root / "lab"
        (self.lab / "waking-dream").mkdir(parents=True)
        (self.lab / "results").mkdir(parents=True)
        self._orig_models_dir = growth_cycle.MODELS_DIR
        self._orig_lab_root = growth_cycle.LAB_ROOT
        self._orig_write_registry = registry_mod.write_registry
        growth_cycle.MODELS_DIR = self.models
        growth_cycle.LAB_ROOT = self.lab
        registry_mod.write_registry = lambda: None
        self.addCleanup(self._restore)

    def _restore(self):
        growth_cycle.MODELS_DIR = self._orig_models_dir
        growth_cycle.LAB_ROOT = self._orig_lab_root
        registry_mod.write_registry = self._orig_write_registry
        self.tmp.cleanup()

    def test_rollback_restores_overwritten_incumbents(self):
        expr_bytes = json.dumps({"name": EXPR, "w": [1, 2, 3]}).encode()
        index_bytes = json.dumps({"name": INDEX, "w": [4, 5]}).encode()
        (self.models / f"{EXPR}.json").write_bytes(expr_bytes)
        (self.models / f"{INDEX}.json").write_bytes(index_bytes)
        (self.models / "composer_config.json").write_bytes(b"cfg-before")

        names = [EXPR, INDEX, NEW_CHILD]
        snaps = growth_cycle._snapshot_model_files(names)
        self.assertEqual(snaps[EXPR], expr_bytes)
        self.assertEqual(snaps[INDEX], index_bytes)
        self.assertIsNone(snaps[NEW_CHILD])

        # Simulate adoption: births overwrite both incumbents and
        # write one genuinely new child file; config changes too.
        (self.models / f"{EXPR}.json").write_bytes(b"new-expr")
        (self.models / f"{INDEX}.json").write_bytes(b"new-index")
        (self.models / f"{NEW_CHILD}.json").write_bytes(b"new-child")
        (self.models / "composer_config.json").write_bytes(b"cfg-after")

        lineage = LineageLog(Path(self.tmp.name) / "lineage.jsonl")
        snapshots = {"composer_config": b"cfg-before",
                     "waking_dream_results": b"wd-before"}
        born = [{"child": EXPR}, {"child": INDEX},
                {"child": NEW_CHILD}]
        growth_cycle._rollback(born, snapshots, "growth-cycle-test",
                               lineage, "test reason",
                               model_snapshots=snaps)

        # Incumbents back byte-for-byte; the new child is gone;
        # config restored.
        self.assertEqual(
            (self.models / f"{EXPR}.json").read_bytes(), expr_bytes)
        self.assertEqual(
            (self.models / f"{INDEX}.json").read_bytes(), index_bytes)
        self.assertFalse((self.models / f"{NEW_CHILD}.json").exists())
        self.assertEqual(
            (self.models / "composer_config.json").read_bytes(),
            b"cfg-before")
        events = [json.loads(ln) for ln in
                  (Path(self.tmp.name) / "lineage.jsonl")
                  .read_text().splitlines()]
        rb = [e for e in events if e.get("kind") == "growth_rollback"]
        self.assertEqual(len(rb), 1)
        self.assertEqual(sorted(rb[0]["restored"]), [INDEX, EXPR])
        self.assertEqual(rb[0]["removed"], [NEW_CHILD])

    def test_legacy_call_without_snapshots_still_unlinks(self):
        (self.models / f"{EXPR}.json").write_bytes(b"child")
        (self.models / "composer_config.json").write_bytes(b"cfg")
        lineage = LineageLog(Path(self.tmp.name) / "lineage.jsonl")
        snapshots = {"composer_config": b"cfg",
                     "waking_dream_results": b"wd"}
        growth_cycle._rollback([{"child": EXPR}], snapshots,
                               "growth-cycle-test", lineage, "legacy")
        self.assertFalse((self.models / f"{EXPR}.json").exists())


if __name__ == "__main__":
    unittest.main()
