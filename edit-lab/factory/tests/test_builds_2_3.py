"""Tests for Fable-study Builds 2 + 3 (2026-11-12) — Muse's work,
Muse's side. Run from ~/workspace/edit-lab:
    python3 -m unittest factory.tests.test_builds_2_3 -v

Covers factory/learned_say.py (seat grouping, the combination and
verdict rules, the dev fit improving on its own cache, the
adopted-only serving state), the say branch of
swarm/composers.class_margins, the serve decision log
(factory/serve.py), and the recorded-history miners
(factory/spawn_mining.py). Everything runs on synthetic caches or
the lab's recorded files — no training, no sealed judging.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "coding"))

from factory import learned_say as S  # noqa: E402
from factory import serve as serve_mod  # noqa: E402
from swarm import composers as C  # noqa: E402

MEMBERS = [
    "bug-missing-return-assigns-model", "bug-missing-return-model",
    "bug-mutable-default-model",
    "bug-off-by-one-harvest-model", "bug-off-by-one-index-model",
    "bug-off-by-one-model", "bug-off-by-one-range-model",
    "bug-swapped-operands-harvest-model", "bug-swapped-operands-model",
    "bug-swapped-operands-named-model",
    "bug-swapped-operands-plain-model",
    "bug-wrong-operator-accumulator-model",
    "bug-wrong-operator-expression-model",
    "bug-wrong-operator-harvest-model", "bug-wrong-operator-model",
    "bug-wrong-operator-named-model"]


class TestSeatsAndCombine(unittest.TestCase):
    def test_seats_group_all_members(self):
        seats = S.seats_of(MEMBERS)
        self.assertEqual({c: len(v) for c, v in seats.items()}, {
            "off-by-one": 4, "wrong-operator": 5,
            "swapped-operands": 4, "mutable-default": 1,
            "missing-return": 2})

    def test_combine_uniform_is_mean(self):
        row = {"off-by-one": {"a": 1.0, "b": 3.0}}
        self.assertEqual(S.combine(row, None)["off-by-one"], 2.0)

    def test_combine_weights_and_fallback(self):
        row = {"off-by-one": {"a": 1.0, "b": 3.0}}
        w = {"off-by-one": {"a": 3.0, "b": 1.0}}
        self.assertAlmostEqual(S.combine(row, w)["off-by-one"], 1.5)
        # a seat missing from the weights takes the mean weight
        row2 = {"off-by-one": {"a": 1.0, "b": 3.0, "c": 5.0}}
        got = S.combine(row2, w)["off-by-one"]
        self.assertAlmostEqual(got, (3 * 1 + 1 * 3 + 2 * 5) / 6)

    def test_verdict_form(self):
        self.assertEqual(S.verdict({"off-by-one": -1.0}, {}), "clean")
        self.assertEqual(S.verdict({"off-by-one": 0.5}, {}),
                         "off-by-one")
        self.assertEqual(
            S.verdict({"off-by-one": 0.5}, {"off-by-one": 0.6}),
            "clean")


class TestFit(unittest.TestCase):
    def _cache(self):
        # seat "good" always fires on its class and stays quiet
        # elsewhere; seat "bad" does the opposite
        cache = []
        for i in range(30):
            cache.append({"margins": {
                "off-by-one": {"bug-off-by-one-model": 2.0,
                               "bug-off-by-one-range-model": -2.0}},
                "label": "off-by-one"})
            cache.append({"margins": {
                "off-by-one": {"bug-off-by-one-model": -2.0,
                               "bug-off-by-one-range-model": 2.0}},
                "label": "clean"})
        return cache

    def test_fit_prefers_the_good_seat(self):
        seats = {"off-by-one": ["bug-off-by-one-model",
                                "bug-off-by-one-range-model"]}
        say = S.fit_on_cache(self._cache(), seats, {})
        w = say["weights"]["off-by-one"]
        self.assertGreater(w["bug-off-by-one-model"],
                           w["bug-off-by-one-range-model"])
        self.assertGreaterEqual(say["fit"]["dev_acc_say"],
                                say["fit"]["dev_acc_uniform"])
        self.assertEqual(say["fit"]["dev_acc_say"], 1.0)

    def test_single_seat_class_keeps_full_share(self):
        seats = {"mutable-default": ["bug-mutable-default-model"]}
        cache = [{"margins": {"mutable-default":
                              {"bug-mutable-default-model": 1.0}},
                  "label": "mutable-default"}]
        say = S.fit_on_cache(cache, seats, {})
        self.assertEqual(
            say["weights"]["mutable-default"]
            ["bug-mutable-default-model"], 1.0)


class TestSayState(unittest.TestCase):
    def test_shadow_never_serves_adopted_does(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "learned_say.json"
            old = S.STATE_PATH
            S.STATE_PATH = path
            try:
                say = {"weights": {}, "thresholds": {}}
                S.write_state("shadow", say, {})
                self.assertIsNone(S.load_serving_say())
                S.write_state("adopted", say, {})
                self.assertEqual(S.load_serving_say(), say)
                path.write_text("{corrupt")
                self.assertIsNone(S.load_serving_say())
            finally:
                S.STATE_PATH = old


class TestComposerSayBranch(unittest.TestCase):
    def test_class_margins_honor_say_weights(self):
        margins = {"bug-off-by-one-model": 0.0,
                   "bug-off-by-one-range-model": 4.0}
        orig = C._model_margin
        C._model_margin = lambda m, code, cls: margins[m.name]
        try:
            class M:
                def __init__(self, name):
                    self.name = name
            reg = {n: M(n) for n in margins}
            cfg = {"say": {"weights": {"off-by-one": {
                "bug-off-by-one-model": 1.0,
                "bug-off-by-one-range-model": 0.0}}}}
            out = C.class_margins(reg, "code", cfg)
            self.assertEqual(out["off-by-one"], 0.0)
            cfg2 = {"say": {"weights": {"off-by-one": {
                "bug-off-by-one-model": 0.0,
                "bug-off-by-one-range-model": 1.0}}}}
            out2 = C.class_margins(reg, "code", cfg2)
            self.assertEqual(out2["off-by-one"], 4.0)
        finally:
            C._model_margin = orig


class TestServeLog(unittest.TestCase):
    def test_append_writes_json_lines(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "serve_log.jsonl"
            old = os.environ.get("FACTORY_SERVE_LOG")
            os.environ["FACTORY_SERVE_LOG"] = str(log)
            try:
                serve_mod._append_serve_log(
                    {"kind": "classify", "job": "gap-move-model",
                     "text": "ship it"},
                    {"ok": True, "output": "wait-for-backend",
                     "provenance": {"artifact": "gap-move-model-v2"}})
                serve_mod._append_serve_log(
                    {"kind": "bug-pattern", "code": "def f(): pass"},
                    {"ok": True, "output": "clean",
                     "provenance": {"composition":
                                    "bug-pattern-composed",
                                    "mechanism": "verified",
                                    "verification_fired": True,
                                    "composer_verdict": "clean"}})
            finally:
                if old is None:
                    os.environ.pop("FACTORY_SERVE_LOG", None)
                else:
                    os.environ["FACTORY_SERVE_LOG"] = old
            rows = [json.loads(x) for x in
                    log.read_text().splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["artifact"], "gap-move-model-v2")
            self.assertEqual(rows[1]["mechanism"], "verified")
            self.assertEqual(rows[1]["composer_verdict"], "clean")


class TestMining(unittest.TestCase):
    def test_sealed_trajectory_shape(self):
        from factory import spawn_mining as M
        traj = M.mine_sealed_trajectory()
        self.assertGreaterEqual(traj["measurements"], 10)
        self.assertIn("swapped-operands", traj["per_class"])
        self.assertEqual(
            traj["per_class"]["swapped-operands"]["max"], 0.0)

    def test_growth_targets_show_the_standing_attacks(self):
        from factory import spawn_mining as M
        gt = M.mine_growth_targets()
        self.assertEqual(
            gt["target_frequency"].get("wrong-operator/expression"),
            6)


if __name__ == "__main__":
    unittest.main()
