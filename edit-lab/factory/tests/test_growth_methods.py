"""Growth methods-arms tests (2026-11-11, the Fable-methods
upgrade). Run from ~/workspace/edit-lab:
    python3 -m unittest factory.tests.test_growth_methods -v

Covers the cycle-3 candidate machinery in factory/growth.py:
the dev split (Fable selection discipline), the weight-blend
shapes behind the breadth/concentrated edit pair, and an
end-to-end smoke of attempt_birth with the methods arms on one
real target at tiny budgets — with the models directory
redirected to a temp copy, so a smoke birth cannot touch the
serving registry, config, or models. The gate itself is guarded
by asserting the recorded parent/child numbers obey it either
way the smoke lands.
"""
import hashlib
import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from factory import growth, name_intent  # noqa: E402
from factory.growth_cycle import cap_intent, replay_set  # noqa: E402
from factory.lineage import LineageLog  # noqa: E402

REAL_MODELS_DIR = growth.MODELS_DIR


def _config_hash():
    return hashlib.sha256(
        (REAL_MODELS_DIR / "composer_config.json")
        .read_bytes()).hexdigest()


def _models_listing():
    return sorted(p.name for p in REAL_MODELS_DIR.glob("*.json"))


class TestDevSplit(unittest.TestCase):
    def test_deterministic_stratified_disjoint(self):
        items = ([{"text": f"a{i}", "label": "x"} for i in range(50)]
                 + [{"text": f"b{i}", "label": "y"}
                    for i in range(30)])
        fit1, dev1 = growth._dev_split(items, seed=7)
        fit2, dev2 = growth._dev_split(items, seed=7)
        self.assertEqual([e["text"] for e in fit1],
                         [e["text"] for e in fit2])
        self.assertEqual([e["text"] for e in dev1],
                         [e["text"] for e in dev2])
        fit_t = {e["text"] for e in fit1}
        dev_t = {e["text"] for e in dev1}
        self.assertFalse(fit_t & dev_t)
        self.assertEqual(fit_t | dev_t, {e["text"] for e in items})
        # both classes represented in dev (stratified)
        self.assertEqual({e["label"] for e in dev1}, {"x", "y"})
        self.assertEqual(len(dev1), 16)  # 20% of 50 + 20% of 30

    def test_tiny_class_contributes_no_dev(self):
        items = ([{"text": f"a{i}", "label": "x"} for i in range(40)]
                 + [{"text": "only", "label": "rare"}])
        fit, dev = growth._dev_split(items, seed=3)
        self.assertTrue(all(e["label"] == "x" for e in dev))
        self.assertEqual(len(fit) + len(dev), 41)


class TestBlendWeights(unittest.TestCase):
    BASE = {"w": {"f1": {"a": 1.0, "b": 2.0}}, "b": {"a": 0.5}}
    MOVED = {"w": {"f1": {"a": 3.0, "b": 2.0}, "f2": {"a": 1.0}},
             "b": {"a": 1.5}}

    def test_thin_moves_every_tensor_by_alpha(self):
        out = growth._blend_weights(self.BASE, self.MOVED, 0.5)
        self.assertAlmostEqual(out["w"]["f1"]["a"], 2.0)
        self.assertAlmostEqual(out["b"]["a"], 1.0)
        # a feature only in `moved` enters at alpha * value
        self.assertAlmostEqual(out["w"]["f2"]["a"], 0.5)

    def test_concentrated_moves_only_the_named_tensor(self):
        out = growth._blend_weights(self.BASE, self.MOVED, 1.0,
                                    tensors={"b"})
        self.assertEqual(out["w"], self.BASE["w"])
        self.assertAlmostEqual(out["b"]["a"], 1.5)

    def test_tensor_deltas_pick_the_largest_mover(self):
        d = growth._tensor_deltas(self.BASE, self.MOVED)
        self.assertAlmostEqual(d["w"], 3.0)   # |3-1| + |2-2| + |1-0|
        self.assertAlmostEqual(d["b"], 1.0)
        self.assertEqual(max(d, key=d.get), "w")


class TestLegacyUntouched(unittest.TestCase):
    def test_methods_defaults_to_none(self):
        sig = inspect.signature(growth.attempt_birth)
        self.assertIsNone(sig.parameters["methods"].default)

    def test_no_methods_no_methods_key(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            models = tmp / "models"
            models.mkdir()
            (models / "composer_config.json").write_text(
                (REAL_MODELS_DIR / "composer_config.json")
                .read_text())
            old = growth.MODELS_DIR
            growth.MODELS_DIR = models
            try:
                out = growth.attempt_birth(
                    "wrong-operator", "expression", tmp / "run",
                    LineageLog(tmp / "lineage.jsonl"), "test-legacy",
                    arms=())
            finally:
                growth.MODELS_DIR = old
            self.assertNotIn("methods", out)
            self.assertFalse(out["born"])


class TestMethodsArmsSmoke(unittest.TestCase):
    def test_attempt_birth_with_methods_tiny_budget(self):
        if not (name_intent.DATA_DIR
                / "name_intent_train.json").exists():
            name_intent.build_datasets()
        intent_train = name_intent.load_train()
        intent_held = name_intent.load_held()
        extra = cap_intent(intent_train, "wrong-operator",
                           "expression", seed=99)
        before_hash = _config_hash()
        before_listing = _models_listing()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            models = tmp / "models"
            models.mkdir()
            (models / "composer_config.json").write_text(
                (REAL_MODELS_DIR / "composer_config.json")
                .read_text())
            old = growth.MODELS_DIR
            growth.MODELS_DIR = models
            try:
                out = growth.attempt_birth(
                    "wrong-operator", "expression", tmp / "run",
                    LineageLog(tmp / "lineage.jsonl"), "test-methods",
                    extra_train=extra, extra_held=intent_held,
                    arms=(), init_train_extra=replay_set(),
                    failure_weight=True,
                    methods={"seed": 99, "probe_epochs": 25,
                             "full_epochs": 90,
                             "breadth_probe_epochs": 50,
                             "repair_epochs": 40})
            finally:
                growth.MODELS_DIR = old
        # provenance recorded, all three arms
        self.assertIn("methods", out)
        mp = out["methods"]
        hh = mp["headtohead"]
        self.assertEqual(len(hh["recipes"]), 3)
        self.assertTrue(all("dev_acc" in r or "blocked" in r
                            for r in hh["recipes"]))
        self.assertIn(hh["winner"],
                      {"scratch-text-h4", "init-lr03", "init-lr10"})
        win_row = [r for r in hh["recipes"]
                   if r["id"] == hh["winner"]][0]
        self.assertEqual(hh["winner_dev_acc"], win_row["dev_acc"])
        self.assertIn("indicted_tensor", mp["breadth"])
        self.assertIsNotNone(mp["dream_first"].get("kept_n"))
        # candidates from every arm reached the judge
        arms = [r["arm"] for r in out["attempts"]]
        self.assertIn(f"recipe:{hh['winner']}", arms)
        self.assertIn("breadth", arms)
        self.assertIn("concentrated", arms)
        self.assertIn("dream-first", arms)
        for r in out["attempts"]:
            if "slice_heldout_acc" in r:
                self.assertIn("intent_heldout_acc", r)
        # the gate's arithmetic holds whichever way it landed
        if out["born"]:
            self.assertGreater(out["child_slice_heldout_acc"],
                               out["parent_slice_heldout_acc"])
            self.assertGreater(out["child_intent_heldout_acc"],
                               out["parent_intent_heldout_acc"])
        else:
            self.assertIn("gate failed", out["rejection"])
        # serving state untouched: the smoke wrote only to tmp
        self.assertEqual(_config_hash(), before_hash)
        self.assertEqual(_models_listing(), before_listing)
        rec = json.loads((REAL_MODELS_DIR / "composer_config.json")
                         .read_text())
        self.assertIsInstance(rec, dict)


if __name__ == "__main__":
    unittest.main()
