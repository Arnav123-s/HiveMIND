"""Phase C unit tests (stdlib unittest). Run from ~/workspace/edit-lab:
    python3 -m unittest factory.tests.test_phase_c -v

Covers the dream generator's execution checker, the thermostat, the
slice quota, the ternary substrate (quantize / QAT / flip map), the
scheduler (lock + queue), v2-aware intake, and the dream plan shape.
The measured end-to-end evidence lives in the run directories
(dream-phaseC-002, phaseC-ternary-002, phaseC-growth-001); these
tests guard the mechanisms, not the numbers.
"""
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from factory import dream, dream_gen as G, scheduler, ternary  # noqa: E402
from factory.contracts import Action, Subject  # noqa: E402
from factory import stages  # noqa: E402


class TestDreamGenChecker(unittest.TestCase):
    def test_real_mutation_verifies(self):
        fam = {"band": 1, "family": "t",
               "correct": "def f(a, b):\n    return a - b",
               "mutations": {"swapped-operands":
                             "def f(a, b):\n    return b - a"},
               "probes": [(7, 3), (5, 5)], "repeat_probe": None}
        v = G.verify_family(fam)
        self.assertIsNone(v["correct"])
        self.assertIsNone(v["swapped-operands"])

    def test_unobservable_mutation_is_dropped(self):
        # addition commutes: the "swap" changes nothing observable
        fam = {"band": 1, "family": "t",
               "correct": "def f(a, b):\n    return a + b",
               "mutations": {"swapped-operands":
                             "def f(a, b):\n    return b + a"},
               "probes": [(7, 3)], "repeat_probe": None}
        v = G.verify_family(fam)
        self.assertIsNotNone(v["swapped-operands"])

    def test_broken_correct_code_drops_family(self):
        fam = {"band": 1, "family": "t",
               "correct": "def f(a):\n    return a[5]",
               "mutations": {}, "probes": [([1],)], "repeat_probe": None}
        v = G.verify_family(fam)
        self.assertIsNotNone(v["correct"])

    def test_renamed_view_behaves_identically(self):
        code = "def tally(xs):\n    s = 0\n    for x in xs:\n" \
               "        s += x\n    return s"
        view = G.renamed_view(code)
        self.assertIsNotNone(view)
        self.assertNotEqual(view, code)
        probes = [([1, 2, 3],), ([7],)]
        self.assertEqual(G._signature(code, probes),
                         G._signature(view, probes))

    def test_pool_items_carry_two_views(self):
        items, stats = G.gen_pool({1: 6}, seed=5, group_prefix="t")
        self.assertTrue(items)
        views = {i.get("view", 1) for i in items}
        self.assertIn(2, views)


class TestThermostat(unittest.TestCase):
    def _stats(self, recalls):
        return {b: {"acc": None, "recall": r, "n_pos": 10}
                for b, r in recalls.items()}

    def test_mastery_steps_up(self):
        th = dream.Thermostat()
        e = th.measure("s", "c", self._stats({1: 0.95, 2: 0.5, 3: 0.2}))
        self.assertEqual(e["edge_band"], 2)
        self.assertEqual(e["mastered"], [1])

    def test_unmastered_first_band_is_edge(self):
        th = dream.Thermostat()
        e = th.measure("s", "c", self._stats({1: 0.4, 2: 0.99, 3: 0.99}))
        self.assertEqual(e["edge_band"], 1)

    def test_all_mastered_edge_is_top(self):
        th = dream.Thermostat()
        e = th.measure("s", "c", self._stats({1: 1.0, 2: 1.0, 3: 1.0}))
        self.assertEqual(e["edge_band"], 3)
        self.assertEqual(e["mastered"], [1, 2, 3])


class TestSliceQuota(unittest.TestCase):
    def test_dominant_slice_is_capped(self):
        items = []
        for i in range(10):   # range-slice positives dominate
            items.append({"text": f"def f{i}(n):\n    for i in range(n):"
                                  f"\n        pass",
                          "label": "off-by-one", "group": f"g{i}"})
        for i in range(2):    # index-slice positives
            items.append({"text": f"def h{i}(xs):\n    return xs[0]",
                          "label": "off-by-one", "group": f"h{i}"})
        kept, dropped = dream.slice_quota(items, cap_share=0.5)
        kept_pos = [k for k in kept if k["label"] == "off-by-one"]
        self.assertLessEqual(len(kept_pos), 6 + 2)
        self.assertTrue(dropped)


class TestTernary(unittest.TestCase):
    def _toy(self):
        train = ([{"text": "red round fruit", "label": "apple"}] * 6
                 + [{"text": "yellow long fruit", "label": "banana"}] * 6
                 + [{"text": "red round berry", "label": "apple"}] * 4
                 + [{"text": "yellow long berry", "label": "banana"}] * 4)
        return train

    def test_qat_learns_toy(self):
        from swarm import factory as F
        train = self._toy()
        pack, feats = ternary.train_qat(train, ["apple", "banana"], 0,
                                        fmode="text", epochs=200)
        tmpl = F.TinyNet("toy", "test", "toy job", ["apple", "banana"],
                         feats, 0, "text")
        q = ternary.materialize(tmpl, pack)
        right = sum(1 for ex in train
                    if q.run({"text": ex["text"]})["output"] == ex["label"])
        self.assertGreaterEqual(right / len(train), 0.9)

    def test_quantize_materialize_close_to_fp(self):
        from swarm import factory as F
        train = self._toy()
        task = {"name": "toy", "niche": "test", "job": "toy",
                "classes": ["apple", "banana"], "train": train,
                "heldout": train}
        fp = F.train_candidate(task, fmode="text", hidden=0, epochs=200,
                               train=train)
        pack = ternary.quantize(fp, train)
        q = ternary.materialize(fp, pack)
        foot = ternary.packed_footprint(pack, fp)
        self.assertGreater(foot["ternary_weights"], 0)
        self.assertLess(foot["packed_bytes"], 4 * foot["ternary_weights"])
        base, entries = ternary.flip_map(fp, pack, train[:8])
        self.assertTrue(entries)
        self.assertTrue(all(-1 <= e["from"] <= 1 for e in entries))


class TestScheduler(unittest.TestCase):
    def test_lock_contention_and_stale_break(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "heavy.lock"
            a = scheduler.HeavyLegLock(p, stale_seconds=3600)
            r1 = a.acquire("owner-a")
            self.assertTrue(r1["acquired"])
            b = scheduler.HeavyLegLock(p, stale_seconds=3600)
            r2 = b.acquire("owner-b")
            self.assertFalse(r2["acquired"])
            self.assertEqual(r2["holder"]["owner"], "owner-a")
            a.release()
            r3 = b.acquire("owner-b")
            self.assertTrue(r3["acquired"])
            b.release()
            # stale lock may be broken, and says so
            c = scheduler.HeavyLegLock(p, stale_seconds=0)
            c.acquire("owner-c")
            old = time.time() - 100
            import os
            os.utime(p, (old, old))
            d = scheduler.HeavyLegLock(p, stale_seconds=10)
            r4 = d.acquire("owner-d")
            self.assertTrue(r4["acquired"])
            self.assertTrue(r4["broke_stale"])
            d.release()

    def test_queue_fifo_persists(self):
        with tempfile.TemporaryDirectory() as td:
            q = scheduler.CycleQueue(Path(td) / "queue.json")
            self.assertEqual(len(q), 0)
            q.enqueue({"cycle_id": "c1", "mode": "real"})
            q.enqueue({"cycle_id": "c2", "mode": "real"})
            q2 = scheduler.CycleQueue(Path(td) / "queue.json")
            self.assertEqual(q2.peek()["cycle_id"], "c1")
            self.assertEqual(q2.pop()["cycle_id"], "c1")
            self.assertEqual(q2.pop()["cycle_id"], "c2")
            self.assertIsNone(q2.pop())


class TestThermalAdapter(unittest.TestCase):
    def test_fresh_jsonl_log_reads_latest(self):
        from factory import thermal
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "tempwatch.log"
            p.write_text('{"temp_c": 61.5}\n{"temp_c": 72.25}\n')
            v, src = thermal.read_tempwatch(p)
            self.assertEqual(v, 72.25)
            self.assertIn("tempwatch", src)

    def test_stale_log_is_not_a_sensor(self):
        import os
        from factory import thermal
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "tempwatch.log"
            p.write_text('{"temp_c": 55}\n')
            old = time.time() - 3600
            os.utime(p, (old, old))
            v, _ = thermal.read_tempwatch(p)
            self.assertIsNone(v)


class TestIntakeAndPlanShape(unittest.TestCase):
    def test_subjects_diagnose_v2(self):
        from factory.subjects import load_coding_subjects
        subs = {s.subject_id: s
                for s in load_coding_subjects(Path("."))}
        contract = subs["contract-judgment-model"]
        # Phase D update: intake follows the HIGHEST adopted
        # version — the dream cycle adopted v3 after this test was
        # written for v2 (the generalization is the point of the
        # intake; serving is a separate registry decision)
        self.assertTrue(contract.artifact_path.endswith("-v3.json"))
        self.assertEqual(contract.heldout_score, 1.0)
        self.assertEqual(contract.metadata.get("supersedes"),
                         "contract-judgment-model-v2")

    def test_bug_plan_is_dream_train_with_gate(self):
        from factory.subjects import load_coding_subjects
        subs = {s.subject_id: s
                for s in load_coding_subjects(Path("."))}
        bug = subs["bug-pattern-composed"]
        diag = stages.diagnose(bug)
        ind = stages.indict(bug, diag)
        plan = stages.edit_train(bug, diag, ind)
        self.assertEqual(plan.action, Action.DREAM_TRAIN)
        self.assertIsNotNone(plan.win_gate)
        self.assertEqual(plan.win_gate.threshold, 0.8)
        v = stages.verify(bug, plan, ind)
        self.assertEqual(v.verdict, "SHADOW_PASS")
        self.assertFalse(v.measured)


if __name__ == "__main__":
    unittest.main()
