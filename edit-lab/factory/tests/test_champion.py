"""Champion-recipe tests (2026-11-12, Fable-study Build 1).
Run from ~/workspace/edit-lab:
    python3 -m unittest factory.tests.test_champion -v

Covers factory/champion.py (the persistent one-gene-mutated
recipe record: validation, mutation discipline, crown rule,
record IO), the crown application helper in growth_cycle.py
(kept-birth + positive dev margin only — never on an unborn or
rolled-back challenger), and an end-to-end smoke of
attempt_birth with the champion arm switched on at tiny budgets,
with the models directory redirected to a temp copy and the
champion record path redirected to a temp file, so the smoke
cannot touch serving state or the real champion record.
"""
import hashlib
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from factory import champion, growth, name_intent  # noqa: E402
from factory import growth_cycle  # noqa: E402
from factory.growth_cycle import cap_intent, replay_set  # noqa: E402
from factory.lineage import LineageLog  # noqa: E402

REAL_MODELS_DIR = growth.MODELS_DIR


class TestValidate(unittest.TestCase):
    def test_seed_recipe_is_valid(self):
        self.assertEqual(
            champion.validate_recipe(dict(champion.SEED_RECIPE)),
            champion.SEED_RECIPE)

    def test_unknown_gene_rejected(self):
        bad = dict(champion.SEED_RECIPE)
        bad["dropout"] = 0.5
        with self.assertRaises(ValueError):
            champion.validate_recipe(bad)

    def test_disallowed_value_rejected(self):
        bad = dict(champion.SEED_RECIPE)
        bad["lr_scale"] = 3.0
        with self.assertRaises(ValueError):
            champion.validate_recipe(bad)


class TestMutate(unittest.TestCase):
    def test_exactly_one_gene_changes(self):
        rng = random.Random(1234)
        for _ in range(40):
            mutant, mut = champion.mutate(champion.SEED_RECIPE,
                                          rng)
            diff = [g for g in champion.GENES
                    if mutant[g] != champion.SEED_RECIPE[g]]
            self.assertEqual(diff, [mut["gene"]])
            self.assertEqual(mut["from"],
                             champion.SEED_RECIPE[mut["gene"]])
            self.assertEqual(mut["to"], mutant[mut["gene"]])
            self.assertIn(mut["to"], champion.GENES[mut["gene"]])
            champion.validate_recipe(mutant)

    def test_deterministic_in_rng(self):
        m1, mut1 = champion.mutate(champion.SEED_RECIPE,
                                   random.Random(7))
        m2, mut2 = champion.mutate(champion.SEED_RECIPE,
                                   random.Random(7))
        self.assertEqual(m1, m2)
        self.assertEqual(mut1, mut2)

    def test_mutation_reaches_multiple_genes(self):
        rng = random.Random(2026)
        genes = {champion.mutate(champion.SEED_RECIPE, rng)[1]
                 ["gene"] for _ in range(60)}
        self.assertGreaterEqual(len(genes), 3)


class TestRecordIO(unittest.TestCase):
    def test_load_missing_returns_seed_without_writing(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "champion_recipe.json"
            rec = champion.load_record(p)
            self.assertEqual(rec["version"], 1)
            self.assertEqual(rec["recipe"], champion.SEED_RECIPE)
            self.assertFalse(p.exists())

    def test_ensure_writes_seed_then_loads_it(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "champion_recipe.json"
            rec = champion.ensure_record(p)
            self.assertTrue(p.exists())
            self.assertEqual(champion.load_record(p), rec)

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "champion_recipe.json"
            rec = champion.seed_record()
            rec["recipe"] = dict(champion.SEED_RECIPE,
                                 epochs=300)
            champion.save_record(rec, p)
            self.assertEqual(champion.load_record(p)["recipe"]
                             ["epochs"], 300)


class TestTrainKwargs(unittest.TestCase):
    def test_parent_recipe_uses_init_diet(self):
        parent = object()
        kw, diet = champion.train_kwargs(champion.SEED_RECIPE,
                                         parent)
        self.assertEqual(diet, "init")
        self.assertIs(kw["init_from"], parent)
        self.assertEqual(kw["lr_scale"], 1.0)
        self.assertEqual(kw["epochs"], 800)

    def test_scratch_recipe_uses_child_diet(self):
        recipe = dict(champion.SEED_RECIPE,
                      init_source="scratch", fmode="code",
                      hidden=8)
        kw, diet = champion.train_kwargs(recipe, object())
        self.assertEqual(diet, "child")
        self.assertEqual(kw["fmode"], "code")
        self.assertEqual(kw["hidden"], 8)
        self.assertNotIn("init_from", kw)


class TestCrownRule(unittest.TestCase):
    def test_truth_table(self):
        self.assertTrue(champion.should_crown(
            mutant_born=True, dev_margin=0.01))
        self.assertFalse(champion.should_crown(
            mutant_born=False, dev_margin=0.01))
        self.assertFalse(champion.should_crown(
            mutant_born=True, dev_margin=0.0))
        self.assertFalse(champion.should_crown(
            mutant_born=True, dev_margin=-0.05))
        self.assertFalse(champion.should_crown(
            mutant_born=True, dev_margin=None))

    def test_crown_bumps_version_and_records_history(self):
        rec = champion.seed_record()
        mutant = dict(champion.SEED_RECIPE, epochs=300)
        out = champion.crown(
            rec, cycle_id="cycle-999", target="wrong-operator/"
            "expression", mutant_recipe=mutant,
            mutation={"gene": "epochs", "from": 800, "to": 300},
            dev_margin=0.02, champ_dev_acc=0.80,
            mutant_dev_acc=0.82)
        self.assertEqual(out["version"], 2)
        self.assertEqual(out["recipe"], mutant)
        self.assertEqual(out["stats"]["crowns"], 1)
        self.assertEqual(out["history"][-1]["event"], "crowned")
        self.assertEqual(out["history"][-1]["mutation"]["gene"],
                         "epochs")
        # the input record is untouched (crown is pure)
        self.assertEqual(rec["version"], 1)
        self.assertEqual(rec["recipe"], champion.SEED_RECIPE)


def _fake_attempt(born, margin, mutant_born=True):
    return {"born": born, "cls": "wrong-operator",
            "slice": "expression",
            "methods": {"champion": {
                "mutation": {"gene": "epochs", "from": 800,
                             "to": 300},
                "mutant_recipe": dict(champion.SEED_RECIPE,
                                      epochs=300),
                "dev_margin": margin,
                "champ_dev_acc": 0.80,
                "mutant_dev_acc": 0.82,
                "mutant_born": mutant_born}}}


class TestCrownApplication(unittest.TestCase):
    """growth_cycle._apply_champion_crowns is only ever called
    from the births-kept branch; these tests pin its own guards
    as well (unborn attempts are skipped even if handed in)."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.rec_path = Path(self._td.name) / "champion_recipe.json"
        self._old = champion.RECORD_PATH
        champion.RECORD_PATH = self.rec_path

    def tearDown(self):
        champion.RECORD_PATH = self._old
        self._td.cleanup()

    def test_kept_mutant_birth_crowns(self):
        applied = growth_cycle._apply_champion_crowns(
            "cycle-999", [_fake_attempt(True, 0.02)])
        self.assertEqual(len(applied), 1)
        rec = champion.load_record(self.rec_path)
        self.assertEqual(rec["version"], 2)
        self.assertEqual(rec["recipe"]["epochs"], 300)

    def test_unborn_attempt_never_crowns(self):
        applied = growth_cycle._apply_champion_crowns(
            "cycle-999", [_fake_attempt(False, 0.02)])
        self.assertEqual(applied, [])
        self.assertEqual(
            champion.load_record(self.rec_path)["version"], 1)

    def test_nonpositive_margin_never_crowns(self):
        applied = growth_cycle._apply_champion_crowns(
            "cycle-999", [_fake_attempt(True, -0.01)])
        self.assertEqual(applied, [])
        self.assertEqual(
            champion.load_record(self.rec_path)["version"], 1)

    def test_champion_base_birth_does_not_crown(self):
        applied = growth_cycle._apply_champion_crowns(
            "cycle-999",
            [_fake_attempt(True, 0.02, mutant_born=False)])
        self.assertEqual(applied, [])


class TestChampionArmSmoke(unittest.TestCase):
    def test_attempt_birth_with_champion_tiny_budget(self):
        if not (name_intent.DATA_DIR
                / "name_intent_train.json").exists():
            name_intent.build_datasets()
        intent_train = name_intent.load_train()
        intent_held = name_intent.load_held()
        extra = cap_intent(intent_train, "wrong-operator",
                           "expression", seed=99)
        real_rec = champion.RECORD_PATH
        real_rec_hash = (hashlib.sha256(real_rec.read_bytes())
                         .hexdigest() if real_rec.exists()
                         else None)
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            models = tmp / "models"
            models.mkdir()
            (models / "composer_config.json").write_text(
                (REAL_MODELS_DIR / "composer_config.json")
                .read_text())
            old_models = growth.MODELS_DIR
            old_rec = champion.RECORD_PATH
            growth.MODELS_DIR = models
            champion.RECORD_PATH = tmp / "champion_recipe.json"
            try:
                out = growth.attempt_birth(
                    "wrong-operator", "expression", tmp / "run",
                    LineageLog(tmp / "lineage.jsonl"),
                    "test-champion",
                    extra_train=extra, extra_held=intent_held,
                    arms=(), init_train_extra=replay_set(),
                    failure_weight=True,
                    methods={"seed": 99, "probe_epochs": 25,
                             "full_epochs": 90,
                             "breadth_probe_epochs": 50,
                             "repair_epochs": 40,
                             "champion": True})
            finally:
                growth.MODELS_DIR = old_models
                champion.RECORD_PATH = old_rec
            # the arm ran and recorded its experiment
            cp = out["methods"]["champion"]
            self.assertNotIn("skipped", cp)
            self.assertIn(cp["mutation"]["gene"], champion.GENES)
            diff = [g for g in champion.GENES
                    if cp["mutant_recipe"][g]
                    != cp["recipe"][g]]
            self.assertEqual(diff, [cp["mutation"]["gene"]])
            arms = [r["arm"] for r in out["attempts"]]
            self.assertIn("champion", arms)
            self.assertIn("champion-mutant", arms)
            if "dev_margin" in cp:
                self.assertAlmostEqual(
                    cp["dev_margin"],
                    round(cp["mutant_dev_acc"]
                          - cp["champ_dev_acc"], 4), places=6)
            # crown bookkeeping stamped either way it landed
            self.assertIn("mutant_born", cp)
            if out["born"]:
                self.assertEqual(
                    cp["mutant_born"],
                    out["winning_arm"] == "champion-mutant")
                self.assertGreater(
                    out["child_slice_heldout_acc"],
                    out["parent_slice_heldout_acc"])
                self.assertGreater(
                    out["child_intent_heldout_acc"],
                    out["parent_intent_heldout_acc"])
            else:
                self.assertFalse(cp["mutant_born"])
            # the arm itself never writes the champion record —
            # crowns are the cycle runner's job, after
            # verification. The temp record was never created.
            self.assertFalse(
                (tmp / "champion_recipe.json").exists())
        # and the real record (if any) is byte-identical
        if real_rec_hash is not None:
            self.assertEqual(
                hashlib.sha256(real_rec.read_bytes()).hexdigest(),
                real_rec_hash)


if __name__ == "__main__":
    unittest.main()
