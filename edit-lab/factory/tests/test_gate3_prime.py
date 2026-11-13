# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.
"""Gate 3′ tests (2026-11-12, from the E-007 retro-check —
factory/reports/e007-retrocheck-2026-11-12.md).
Run from ~/workspace/edit-lab:
    python3 -m unittest factory.tests.test_gate3_prime -v

The retro-check refuted the raw-composer gate E-007 proposed:
cycles 6 and 7 regressed serving entirely inside the
waking-dream refresh (clean recall fell; raw composed totals
never moved). Gate 3′ judges the full serving path on the
say_dev pool, per child, pre-adoption.

The centrepiece test SIMULATES the demonstrated failure: a
birth whose waking refresh drops clean recall by exactly 1 dev
item at a FLAT served total (the cycle-7 signature). It drives
the real run_cycle3 with training stubbed and the serving-path
scorecard scripted, and proves:
  * adoption is BLOCKED for that child (born=False, Gate 3′
    record + lineage event),
  * serving state is byte-untouched for it — the incumbent
    model file is back byte-for-byte, its composer routing is
    gone, waking-dream/results.json and registry.json were
    never written, and the cycle did NOT roll back (no
    growth_rollback event, rolled_back=False): a Gate 3′
    rejection involves no rollback path,
  * the cycle's OTHER target is gated independently and its
    clean birth is kept,
  * the blocked child's bytes were still snapshotted into the
    run dir (gate3/<child>.json) for future retro-checks.
Pure-verdict tests pin the thresholds: any total fall blocks;
a >=1-item clean fall blocks at flat AND at rising totals;
identical scorecards keep the birth."""
import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from factory import champion as champion_mod  # noqa: E402
from factory import dream as dream_mod  # noqa: E402
from factory import growth_cycle as gc  # noqa: E402
from factory import name_intent as name_intent_mod  # noqa: E402
from factory.lineage import LineageLog  # noqa: E402
import factory.registry as registry_mod  # noqa: E402

EXPR = "bug-wrong-operator-expression-model"
INDEX = "bug-off-by-one-index-model"
EXPR_BYTES = json.dumps({"name": EXPR, "w": [1, 2, 3]}).encode()
INDEX_BYTES = json.dumps({"name": INDEX, "w": [4, 5]}).encode()
CFG_BYTES = json.dumps({"strengths": {}}).encode()


def _card(served_right, clean_right, n=216, clean_n=70):
    return {"n": n,
            "served_acc": round(served_right / n, 4),
            "served_right": served_right,
            "served_per_class_recall":
                {"clean": round(clean_right / clean_n, 4)},
            "served_per_class":
                {"clean": {"n": clean_n, "right": clean_right}},
            "raw_acc": 0.5, "raw_right": n // 2,
            "raw_per_class_recall": {"clean": 0.5},
            "raw_per_class":
                {"clean": {"n": clean_n, "right": clean_n // 2}}}


def _flat_battery(run_dir, tag):
    return {
        "bug-pattern-composed-sealed-v2": {
            "score": 0.8611, "status": "completed", "detail": ""},
        "classify-secret-line": {
            "score": 1.0, "status": "completed", "detail": ""},
    }


class TestGate3Verdict(unittest.TestCase):
    """The threshold law, in exact item counts."""

    def test_total_fall_blocks(self):
        self.assertIsNotNone(gc._gate3_verdict(_card(170, 56),
                                               _card(173, 56)))

    def test_clean_fall_at_flat_total_blocks(self):
        self.assertIsNotNone(gc._gate3_verdict(_card(173, 55),
                                               _card(173, 56)))

    def test_clean_fall_at_rising_total_blocks(self):
        # A compensated clean loss is the cycle-6/7 signature;
        # a rise elsewhere does not launder it.
        self.assertIsNotNone(gc._gate3_verdict(_card(180, 55),
                                               _card(173, 56)))

    def test_identical_scorecards_keep(self):
        self.assertIsNone(gc._gate3_verdict(_card(173, 56),
                                            _card(173, 56)))

    def test_clean_rise_and_total_rise_keeps(self):
        self.assertIsNone(gc._gate3_verdict(_card(180, 60),
                                            _card(173, 56)))


class _Gate3Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.models = root / "models"
        self.models.mkdir()
        (self.models / f"{EXPR}.json").write_bytes(EXPR_BYTES)
        (self.models / f"{INDEX}.json").write_bytes(INDEX_BYTES)
        (self.models / "composer_config.json").write_bytes(CFG_BYTES)
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
        self.run_dir = root / "run"
        self.run_dir.mkdir()

        stack = ExitStack()
        self.addCleanup(stack.close)
        self.addCleanup(self.tmp.cleanup)
        p = stack.enter_context
        p(mock.patch.object(gc, "MODELS_DIR", self.models))
        p(mock.patch.object(gc, "LAB_ROOT", self.lab))
        p(mock.patch.object(gc, "FACTORY_DIR", self.factory_dir))
        p(mock.patch.object(gc, "GROWTH_DIR", self.growth_dir))
        p(mock.patch.object(gc, "_gate3_dev_items", lambda: []))
        p(mock.patch.object(gc, "_gate3_registry",
                            lambda child_name, child_bytes: {}))
        p(mock.patch.object(dream_mod, "load_bug_registry",
                            lambda: {}))

    def _script_scorecards(self, cards):
        """Scripted serving-path measurements. The gate measures
        the child first, then the parent, once per target — the
        queue order is part of the gate's contract."""
        queue = list(cards)
        calls = []

        def fake(reg, config, items):
            calls.append(1)
            return queue.pop(0)

        self._scorecard_calls = calls
        return mock.patch.object(gc, "_gate3_scorecard", fake)

    def _install_fake_child(self, child_name):
        """What attempt_birth does on a dual-gate pass: write the
        child model file + route its slice in composer_config."""
        (self.models / f"{child_name}.json").write_bytes(
            b"child-bytes-" + child_name.encode())
        cfg = json.loads(
            (self.models / "composer_config.json").read_text())
        cls, slice_name = child_name[4:-6].rsplit("-", 1)
        cfg.setdefault("strengths", {}).setdefault(
            cls, {})[slice_name] = "slice"
        (self.models / "composer_config.json").write_text(
            json.dumps(cfg))


class TestGate3PrimeDirect(_Gate3Base):
    """The gate itself, driven directly with scripted cards."""

    def _run_gate(self, child_name, cards):
        pre = gc._gate3_pre_state(child_name)
        self._install_fake_child(child_name)
        out = {"cls": "wrong-operator", "slice": "expression",
               "child": child_name, "born": True}
        lineage = LineageLog(self.run_dir / "lineage.jsonl")
        with self._script_scorecards(cards):
            return gc._gate3_prime(out, pre, self.run_dir, lineage,
                                   "growth-cycle-999")

    def test_clean_drop_one_item_flat_total_blocks(self):
        out = self._run_gate(EXPR, [_card(173, 55), _card(173, 56)])
        self.assertFalse(out["born"])
        self.assertEqual(out["gate3_prime"]["verdict"], "blocked")
        self.assertIn("clean recall fell by 1 item",
                      out["gate3_prime"]["reason"])
        # Serving state byte-untouched.
        self.assertEqual((self.models / f"{EXPR}.json").read_bytes(),
                         EXPR_BYTES)
        self.assertEqual(
            (self.models / "composer_config.json").read_bytes(),
            CFG_BYTES)
        self.assertEqual(
            (self.lab / "waking-dream" / "results.json")
            .read_bytes(), b"wd")
        # Bookkeeping: child bytes snapshotted pre-adoption.
        snap = self.run_dir / "gate3" / f"{EXPR}.json"
        self.assertEqual(snap.read_bytes(),
                         b"child-bytes-" + EXPR.encode())
        self.assertEqual(
            out["gate3_prime"]["child_snapshot_sha256"],
            hashlib.sha256(
                b"child-bytes-" + EXPR.encode()).hexdigest())

    def test_total_fall_blocks(self):
        out = self._run_gate(EXPR, [_card(170, 56), _card(173, 56)])
        self.assertFalse(out["born"])
        self.assertIn("total fell", out["gate3_prime"]["reason"])
        self.assertEqual((self.models / f"{EXPR}.json").read_bytes(),
                         EXPR_BYTES)

    def test_better_child_kept_and_left_installed(self):
        out = self._run_gate(EXPR, [_card(180, 60), _card(173, 56)])
        self.assertTrue(out["born"])
        self.assertEqual(out["gate3_prime"]["verdict"], "kept")
        self.assertEqual((self.models / f"{EXPR}.json").read_bytes(),
                         b"child-bytes-" + EXPR.encode())


class TestGate3InCycle3(_Gate3Base):
    """The required simulation, end to end through run_cycle3:
    target 1's refresh drops clean recall by 1 item at a flat
    total; target 2's birth is clean. Target 1 is blocked with
    serving state byte-untouched and NO rollback; target 2 is
    gated independently and kept."""
    CYCLE_ID = "growth-cycle-996"

    def setUp(self):
        super().setUp()
        stack = ExitStack()
        self.addCleanup(stack.close)
        p = stack.enter_context
        p(mock.patch.object(registry_mod, "write_registry",
                            lambda: None))
        p(mock.patch.object(
            registry_mod, "load_registry",
            lambda: {"compositions": {"bug-pattern-composed": {
                "evidence": {"fresh_sealed_baseline": {"acc": 0.5}}}}}))
        p(mock.patch.object(champion_mod, "ensure_record",
                            lambda: {"version": 1, "recipe": {}}))
        p(mock.patch.object(champion_mod, "load_record",
                            lambda: {"version": 1}))
        p(mock.patch.object(name_intent_mod, "DATA_DIR", self.nidata))
        p(mock.patch.object(name_intent_mod, "load_train", lambda: []))
        p(mock.patch.object(name_intent_mod, "load_held", lambda: []))
        p(mock.patch.object(gc, "harvest_failures", lambda items: {}))
        p(mock.patch.object(gc, "learned_say_experiment", lambda: {}))
        p(mock.patch.object(gc, "replay_set", lambda: []))
        p(mock.patch.object(gc, "cap_intent", lambda *a, **k: []))
        p(mock.patch.object(gc, "measure_served_battery",
                            _flat_battery))
        p(mock.patch.object(
            gc, "_sealed_judge",
            lambda cycle_id, previous_acc=None: {
                "composed_acc": 0.5, "per_class_recall": {}}))
        p(mock.patch.object(gc, "_refresh_waking_dream_results",
                            lambda cycle_id: {}))
        p(mock.patch.object(gc, "_full_audit",
                            lambda: {"ok": True, "failures": []}))
        p(mock.patch.object(gc, "write_report", lambda cycle: None))

    def _fake_birth(self, cls, slice_name, *a, **k):
        child = f"bug-{cls}-{slice_name}-model"
        self._install_fake_child(child)
        return {"born": True, "child": child, "cls": cls,
                "slice": slice_name, "rejection": None}

    def test_refresh_clean_drop_blocks_one_target_keeps_other(self):
        # Gate order per target: child card, then parent card.
        # wrong-operator/expression: total FLAT (173 -> 173),
        # clean 56 -> 55 (-1 item): the cycle-7 signature.
        # off-by-one/index: total and clean both rise: clean.
        cards = [_card(173, 55), _card(173, 56),
                 _card(180, 60), _card(173, 56)]
        with mock.patch.object(gc.growth, "attempt_birth",
                               self._fake_birth), \
                self._script_scorecards(cards):
            cycle = gc.run_cycle3(self.CYCLE_ID)
        self.assertEqual(len(self._scorecard_calls), 4)
        attempts = {a["child"]: a for a in cycle["attempts"]}
        expr, index = attempts[EXPR], attempts[INDEX]
        # Target 1 blocked by Gate 3′ after passing the dual gate.
        self.assertFalse(expr["born"])
        self.assertEqual(expr["gate3_prime"]["verdict"], "blocked")
        self.assertIn("clean recall fell by 1 item",
                      expr["gate3_prime"]["reason"])
        self.assertIn("Gate 3′", expr["rejection"])
        # Target 2 gated independently, kept.
        self.assertTrue(index["born"])
        self.assertEqual(index["gate3_prime"]["verdict"], "kept")
        # Serving state: target 1 byte-untouched...
        self.assertEqual((self.models / f"{EXPR}.json").read_bytes(),
                         EXPR_BYTES)
        cfg = json.loads(
            (self.models / "composer_config.json").read_text())
        self.assertNotIn("wrong-operator",
                         cfg.get("strengths", {}))
        # ...target 2's kept birth is exactly what remains.
        self.assertEqual((self.models / f"{INDEX}.json").read_bytes(),
                         b"child-bytes-" + INDEX.encode())
        self.assertEqual(
            cfg["strengths"]["off-by-one"]["index"], "slice")
        self.assertEqual(
            (self.lab / "waking-dream" / "results.json")
            .read_bytes(), b"wd")
        self.assertEqual(
            (self.factory_dir / "registry.json").read_bytes(), b"{}")
        # No rollback was involved anywhere.
        self.assertFalse(cycle["rolled_back"])
        events = [json.loads(ln) for ln in
                  (self.factory_dir / "runs" / self.CYCLE_ID
                   / "lineage.jsonl").read_text().splitlines()]
        kinds = [e.get("kind") for e in events]
        self.assertNotIn("growth_rollback", kinds)
        blocked = [e for e in events
                   if e.get("kind") == "gate3_prime_blocked"]
        kept = [e for e in events
                if e.get("kind") == "gate3_prime_kept"]
        self.assertEqual([e["child"] for e in blocked], [EXPR])
        self.assertEqual([e["child"] for e in kept], [INDEX])
        # Bookkeeping: BOTH children's bytes were snapshotted
        # pre-adoption (the blocked one included).
        for name in (EXPR, INDEX):
            snap = (self.factory_dir / "runs" / self.CYCLE_ID
                    / "gate3" / f"{name}.json")
            self.assertEqual(snap.read_bytes(),
                             b"child-bytes-" + name.encode())


if __name__ == "__main__":
    unittest.main()
