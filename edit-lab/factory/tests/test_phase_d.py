"""Phase D tests: the final-product build — sealed bug held-out,
niche dream generators + executor discipline, the shared registry
+ serve-time audit, the Tier-3 contract stub, and the scheduler
daemon. Stdlib unittest, system python3, run from the lab root:

    python3 -m unittest factory.tests.test_phase_d -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).parent.parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "coding"))

from factory import audit as audit_mod  # noqa: E402
from factory import daemon as daemon_mod  # noqa: E402
from factory import dream_gen_niches as GN  # noqa: E402
from factory import registry as registry_mod  # noqa: E402
from factory import serve as serve_mod  # noqa: E402
from factory import tier3 as T3  # noqa: E402
from factory.bug_heldout_v2 import load_sealed  # noqa: E402
from factory.scheduler import CycleQueue  # noqa: E402


class TestSealedSet(unittest.TestCase):
    def test_seal_verifies_and_shape(self):
        rec = load_sealed()   # raises if the seal is broken
        items = rec["items"]
        self.assertEqual(len(items), 36)
        labels = {it["label"] for it in items}
        self.assertIn("clean", labels)
        self.assertGreaterEqual(len(labels), 5)
        for it in items:
            self.assertEqual(set(it.keys()), {"text", "label"})

    def test_baseline_recorded(self):
        base = json.loads(
            (LAB / "results" / "bug_heldout_v2_baseline.json").read_text())
        self.assertEqual(base["n"], 36)
        self.assertIn("composed_acc", base)
        self.assertIn("per_class_recall", base)


class TestNicheGenerators(unittest.TestCase):
    POOLS = {"train": GN.contract_gen_pool,
             "screen": GN.contract_gen_screen_pool,
             "confirm": GN.contract_gen_confirm_pool}
    COMMIT_POOLS = {"train": GN.commit_gen_pool,
                    "screen": GN.commit_gen_screen_pool,
                    "confirm": GN.commit_gen_confirm_pool}

    def test_contract_signatures_proved(self):
        # every generated item's label must equal its class's
        # EXECUTED signature — the generator's core promise
        for pool, gen in self.POOLS.items():
            items, _stats = gen({1: 3, 2: 3, 3: 3}, 7, f"t-{pool}")
            self.assertTrue(items)
            for it in items:
                self.assertEqual(
                    GN.contract_signature(it["text"]),
                    GN._CLASS_SIGNATURE[it["label"]],
                    f"{pool}: {it['text'][:60]}")

    def test_contract_pools_are_structurally_disjoint(self):
        def codes(gen):
            items, _ = gen({1: 4, 2: 4, 3: 4}, 7, "t")
            return {it["text"] for it in items}
        tr = codes(self.POOLS["train"])
        sc = codes(self.POOLS["screen"])
        cf = codes(self.POOLS["confirm"])
        self.assertFalse(tr & sc)
        self.assertFalse(tr & cf)
        self.assertFalse(sc & cf)

    def test_commit_labels_pass_the_checker(self):
        for pool, gen in self.COMMIT_POOLS.items():
            items, _stats = gen({1: 3, 2: 3, 3: 3}, 7, f"t-{pool}")
            self.assertTrue(items)
            for it in items:
                self.assertIsNone(
                    GN.verify_commit_item(it["text"], it["label"]),
                    f"{pool}: {it['text'][:60]}")

    def test_two_views_exist(self):
        items, _ = GN.contract_gen_pool({2: 4}, 7, "t")
        views = [it for it in items if it.get("view") == 2]
        self.assertTrue(views)
        for v in views:   # second views are signature-verified too
            self.assertEqual(GN.contract_signature(v["text"]),
                             GN._CLASS_SIGNATURE[v["label"]])


class TestRegistryAndServe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = registry_mod.load_registry()

    def test_book_shape(self):
        self.assertEqual(len(self.reg["specialists"]), 5)
        comp = self.reg["compositions"]["bug-pattern-composed"]
        self.assertGreaterEqual(len(comp["members"]), 10)
        base = comp["evidence"]["fresh_sealed_baseline"]
        self.assertIsNotNone(base)
        self.assertEqual(base["n"], 36)
        self.assertIn("synthv1-r4-coordinator", self.reg["tier1"])

    def test_serving_versions(self):
        s = self.reg["specialists"]
        # assembly 2026-11-10 (Arnav's ruling): the BitNet
        # scale-arm single took the secret-line default — battery
        # tie 0.8333 >= 0.8333 AND held-out tie 1.0 >= 1.0 under
        # the standing serving rule; the founder ternary pack is
        # the registered substrate alternate (held-out 0.9385 <
        # 1.0 keeps it off the default)
        self.assertEqual(s["secret-line-model"]["serving"]["name"],
                         "secret-line-model-v3")
        self.assertEqual(
            s["secret-line-model"]["serving"]["substrate"], "ternary")
        self.assertEqual(
            [x["name"] for x in s["secret-line-model"]["substrates"]],
            ["secret-line-model-ternary"])
        self.assertEqual(s["commit-type-model"]["serving"]["name"],
                         "commit-type-model-v2")
        # the standing serving rule (created by the v3 case):
        # v2 promoted on its battery slice (0.9167 >= v1's
        # 0.5833); v3 (0.4167 < 0.9167) is SHADOW — adopted and
        # audited, never served, not even a fallback
        c = s["contract-judgment-model"]
        self.assertEqual(c["serving"]["name"],
                         "contract-judgment-model-v2")
        self.assertIn("promotion", c["serving"])
        self.assertEqual([f["name"] for f in c["fallbacks"]],
                         ["contract-judgment-model"])
        self.assertEqual([sh["name"] for sh in c["shadow"]],
                         ["contract-judgment-model-v3"])
        self.assertIn("standing serving rule",
                      c["shadow"][0]["shadow_reason"])
        # gap-move and error-class also serve their assembly
        # adoptions (ternary singles: battery 1.0 > 0.8 / 1.0 =
        # 1.0, held-out 0.9444 > 0.9333 / 0.9833 > 0.9583)
        self.assertEqual(s["gap-move-model"]["serving"]["name"],
                         "gap-move-model-v3")
        self.assertEqual(s["gap-move-model"]["shadow"], [])
        self.assertEqual(s["error-class-model"]["serving"]["name"],
                         "error-class-model-v2")
        self.assertEqual(
            s["error-class-model"]["serving"]["substrate"], "ternary")

    def test_rule_enforced_by_audit(self):
        # the shipped book obeys the rule
        self.assertEqual(audit_mod.verify_rule(self.reg), [])
        # a book that serves the shadow artifact by hand fails
        reg = json.loads(json.dumps(self.reg))
        c = reg["specialists"]["contract-judgment-model"]
        v3 = c["shadow"][0]
        v2 = c["serving"]
        v3 = dict(v3, role="serving")
        del v3["shadow_reason"]
        c["serving"] = v3
        c["fallbacks"] = [dict(v2, role="fallback")]
        c["shadow"] = []
        failures = audit_mod.verify_rule(reg)
        self.assertTrue(failures)
        self.assertIn("standing serving rule",
                      failures[0]["failure"] + str(failures[0]))
        # ...and the serving path refuses to load such a book
        with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False) as fh:
            json.dump(reg, fh)
            tmp = Path(fh.name)
        try:
            with self.assertRaises(serve_mod.ServingRefused):
                serve_mod.ServingHive.load(registry_path=tmp)
        finally:
            tmp.unlink()

    def test_ternary_registered_not_default(self):
        subs = self.reg["specialists"]["secret-line-model"]["substrates"]
        self.assertEqual(len(subs), 1)
        self.assertFalse(subs[0]["niche_default"])
        self.assertEqual(
            self.reg["specialists"]["secret-line-model"]
            ["substrate_default"], "fp")

    def test_file_audit_clean(self):
        self.assertEqual(audit_mod.verify_files(self.reg), [])

    def test_audit_fails_closed_on_tamper(self):
        reg = json.loads(json.dumps(self.reg))
        reg["specialists"]["gap-move-model"]["serving"]["sha256"] = \
            "0" * 64
        failures = audit_mod.verify_files(reg)
        self.assertTrue(failures)
        with self.assertRaises(serve_mod.ServingRefused):
            # load() audits the REAL book; simulate by pointing the
            # loader at a tampered copy
            import factory.registry as R
            with tempfile.NamedTemporaryFile(
                    "w", suffix=".json", delete=False) as fh:
                json.dump(reg, fh)
                tmp = Path(fh.name)
            try:
                serve_mod.ServingHive.load(registry_path=tmp)
            finally:
                tmp.unlink()

    def test_serve_classify_and_provenance(self):
        hive = serve_mod.ServingHive.load()
        out = hive.serve({"kind": "classify", "job": "commit-type-model",
                          "text": "fix crash when the cart is empty"})
        self.assertTrue(out["ok"])
        self.assertEqual(out["output"], "fix")
        self.assertIn("provenance", out)
        self.assertEqual(out["provenance"]["artifact"],
                         "commit-type-model-v2")
        bug = hive.serve({"kind": "bug-pattern",
                          "code": "def f(xs):\n    return xs[len(xs)]"})
        self.assertEqual(bug["output"], "off-by-one")
        coord = hive.serve({"kind": "coordinate", "text": "plan"})
        self.assertFalse(coord["ok"])
        self.assertEqual(coord["gap"], "tier1-backend-required")
        unknown = hive.serve({"kind": "classify", "job": "nope",
                               "text": "x"})
        self.assertFalse(unknown["ok"])


class TestTier3Contract(unittest.TestCase):
    def test_never_delegate_refused(self):
        gw = T3.Tier3Gateway()
        for kind in ("gate_verdict", "adoption_decision", "weight_edit",
                     "sealed_set_contents", "spend_or_send"):
            with self.assertRaises(T3.Tier3Refused):
                gw.propose(T3.Tier3Request(
                    kind=kind, subject_id="s", payload={},
                    rationale="r"))

    def test_unknown_kind_and_missing_rationale_refused(self):
        gw = T3.Tier3Gateway()
        with self.assertRaises(T3.Tier3Refused):
            gw.propose(T3.Tier3Request(
                kind="write_the_report", subject_id="s", payload={},
                rationale="r"))
        with self.assertRaises(T3.Tier3Refused):
            gw.propose(T3.Tier3Request(
                kind="cluster_failures", subject_id="s", payload={},
                rationale=""))

    def test_valid_request_fails_closed_unconfigured(self):
        with tempfile.TemporaryDirectory() as td:
            sink = Path(td) / "audit.jsonl"
            gw = T3.Tier3Gateway(audit_sink=sink)
            with self.assertRaises(T3.Tier3NotConfigured):
                gw.propose(T3.Tier3Request(
                    kind="cluster_failures", subject_id="s",
                    payload={"x": 1},
                    rationale="no checker decides semantic grouping"))
            lines = sink.read_text().strip().splitlines()
            events = [json.loads(ln)["event"] for ln in lines]
            self.assertIn("tier3_request", events)
            self.assertIn("tier3_not_configured", events)

    def test_budget_caps_enforced(self):
        gw = T3.Tier3Gateway(caps=T3.BudgetCaps(
            max_input_tokens_per_call=100))
        with self.assertRaises(T3.Tier3Refused):
            gw.propose(T3.Tier3Request(
                kind="draft_suite", subject_id="s", payload={},
                rationale="r", est_input_tokens=101))
        gw2 = T3.Tier3Gateway(caps=T3.BudgetCaps(max_calls_per_cycle=0))
        with self.assertRaises(T3.Tier3Refused):
            gw2.propose(T3.Tier3Request(
                kind="draft_suite", subject_id="s", payload={},
                rationale="r"))


class TestDaemon(unittest.TestCase):
    def test_dry_run_cycle_consumed_and_reported(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            queue = CycleQueue(path=td / "queue.json")
            queue.enqueue({"cycle_id": "test-daemon-001",
                           "mode": "dry_run",
                           "subjects": ["secret-line-model"]})
            d = daemon_mod.FactoryDaemon(
                queue=queue, history_path=td / "history.jsonl",
                reports_dir=td / "reports")
            # pin the governor: this test measures queue mechanics,
            # not host politeness (a loaded host may legitimately
            # hold — that path has its own coverage in Phase A/C)
            from factory.host import GovernorDecision
            d.governor = type("G", (), {"decide": staticmethod(
                lambda profile, heavy_opt_in=False: GovernorDecision(
                    allow_light=True, allow_heavy=False, backoff=False,
                    cause=None, duty_cycle={}))})()
            summary = d.run(max_cycles=1, max_idle_polls=0)
            self.assertEqual(summary["processed"], 1)
            self.assertEqual(len(queue), 0)
            hist = (td / "history.jsonl").read_text().strip().splitlines()
            self.assertEqual(json.loads(hist[-1])["event"], "processed")
            self.assertTrue((td / "reports" / "factory-report.json")
                            .exists())
            self.assertTrue((td / "reports" / "factory-report.md")
                            .exists())

    def test_empty_queue_is_a_noop(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            d = daemon_mod.FactoryDaemon(
                queue=CycleQueue(path=td / "q.json"),
                history_path=td / "h.jsonl", reports_dir=td / "r")
            summary = d.run(max_cycles=1, max_idle_polls=0)
            self.assertEqual(summary["processed"], 0)


if __name__ == "__main__":
    unittest.main()
