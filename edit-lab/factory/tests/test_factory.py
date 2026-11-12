"""Phase A unit tests (stdlib unittest). Run from ~/workspace/edit-lab:
    python3 -m unittest factory.tests.test_factory -v
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from factory import stages  # noqa: E402
from factory.contracts import (Action, Diagnosis, Indictment,  # noqa: E402
                               InterventionPlan, Mode, Subject, WinGate)
from factory.host import Governor, GovernorConfig, HostProfile  # noqa: E402
from factory.loop import FactoryLoop  # noqa: E402
from factory.state import CycleState, StateStore  # noqa: E402


def _profile(**kw) -> HostProfile:
    base = dict(probed_at="t", os="test", python="3", cpu_count=4,
                loadavg_1m=0.1, load_per_cpu=0.025, mem_total_bytes=1,
                mem_available_bytes=1, cgroup_mem_limit_bytes=None,
                disk_free_bytes=1, disk_total_bytes=2, uptime_seconds=100.0,
                gpu_present=False, gpu_evidence="none", thermal_celsius=None,
                thermal_source=None, on_battery=False)
    base.update(kw)
    return HostProfile(**base).derive()


class TestGovernor(unittest.TestCase):
    def test_owner_busy_backs_off(self):
        d = Governor().decide(_profile(load_per_cpu=2.0))
        self.assertTrue(d.backoff)
        self.assertEqual(d.cause, "owner_busy")
        self.assertFalse(d.allow_heavy)

    def test_hot_backs_off(self):
        d = Governor().decide(_profile(thermal_celsius=95.0))
        self.assertTrue(d.backoff)
        self.assertEqual(d.cause, "hot")

    def test_heavy_needs_opt_in(self):
        d = Governor().decide(_profile(), heavy_opt_in=False)
        self.assertFalse(d.allow_heavy)
        self.assertTrue(d.allow_light)

    def test_chunk_ceiling_formula(self):
        p = _profile()
        self.assertEqual(p.chunk_ceiling_minutes, 20)  # 120/6, capped at 20


class TestVerifyGateFailClosed(unittest.TestCase):
    def _subject(self):
        return Subject(subject_id="s", kind="tier0_specialist", niche="review",
                       heldout_score=0.9, fresh_score=0.5, fresh_bar=0.75)

    def test_weight_edit_without_map_blocked(self):
        subj = self._subject()
        ind = Indictment("s", indictable=True, target_units=["w"], method="m",
                         rationale="r", weight_edit_justified=False)
        plan = InterventionPlan("s", Action.WEIGHT_EDIT, steps=["flip"],
                                estimated_cost="test",
                                win_gate=WinGate("m", 0.9, "reg", "proto"))
        v = stages.verify(subj, plan, ind)
        self.assertEqual(v.verdict, "BLOCKED")

    def test_gateless_plan_blocked(self):
        subj = self._subject()
        ind = Indictment("s", indictable=True, target_units=["cov"], method="m",
                         rationale="r")
        plan = InterventionPlan("s", Action.TRAIN_DATA_WIDEN, steps=["x"],
                                estimated_cost="test", win_gate=None)
        v = stages.verify(subj, plan, ind)
        self.assertEqual(v.verdict, "BLOCKED")

    def test_complete_plan_shadow_passes_unmeasured(self):
        subj = self._subject()
        diag = stages.diagnose(subj)
        ind = stages.indict(subj, diag)
        plan = stages.edit_train(subj, diag, ind)
        v = stages.verify(subj, plan, ind)
        self.assertEqual(v.verdict, "SHADOW_PASS")
        self.assertFalse(v.measured)
        self.assertFalse(plan.executed)


class TestDiagnoseFailClosed(unittest.TestCase):
    def test_no_evidence_no_advance(self):
        subj = Subject(subject_id="ghost", kind="tier0_specialist", niche="x")
        diag = stages.diagnose(subj)
        self.assertFalse(diag.has_evidence)
        ind = stages.indict(subj, diag)
        self.assertFalse(ind.indictable)


class TestStateResume(unittest.TestCase):
    def test_save_load_skip(self):
        with tempfile.TemporaryDirectory() as td:
            store = StateStore(Path(td))
            st = CycleState(cycle_id="c1", mode="dry_run")
            st.record("subj", "diagnose", {"summary": "ok"})
            store.save(st)
            loaded = store.load()
            self.assertTrue(loaded.is_stage_done("subj", "diagnose"))
            self.assertEqual(loaded.stages_done("subj"), ["diagnose"])


class TestLoopModeGate(unittest.TestCase):
    def test_real_mode_constructs_in_phase_b(self):
        # Phase B: REAL is legal; what it may DO is gated per-plan at
        # verify (executors exist only for Tier-0 TRAIN_DATA_WIDEN).
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            import factory.loop as loop_mod
            saved = loop_mod.FACTORY_DIR
            try:
                loop_mod.FACTORY_DIR = Path(td)
                lp = FactoryLoop(lab_root=Path("."), cycle_id="x", mode=Mode.REAL)
                self.assertEqual(lp.mode, Mode.REAL)
            finally:
                loop_mod.FACTORY_DIR = saved

    def test_real_cycle_tier1_subject_holds_never_executes(self):
        # The coordinator (Tier-1, contest closed) in REAL mode: NO_OP
        # plan -> HOLD, nothing executed.
        import tempfile
        import factory.loop as loop_mod
        subj = Subject(subject_id="tier1-x", kind="tier1_adapter",
                       niche="coordinator", fresh_score=0.95, fresh_bar=0.93,
                       failing_cases=[{"failed_checks": ["size"], "score": 0.5}])
        with tempfile.TemporaryDirectory() as td:
            saved = loop_mod.FACTORY_DIR
            try:
                loop_mod.FACTORY_DIR = Path(td)
                lp = FactoryLoop(lab_root=Path("."), cycle_id="rt", mode=Mode.REAL)
                rep = lp.run_cycle([subj])
            finally:
                loop_mod.FACTORY_DIR = saved
        entry = rep["subjects"]["tier1-x"]
        self.assertEqual(entry["verify"]["verdict"], "HOLD")
        self.assertNotIn("execution", entry)


class TestMeasuredVerify(unittest.TestCase):
    def _mk_outcome(self, **kw):
        base = {"subject_id": "s", "supported": True, "executed": True,
                "incumbent": {"heldout": {"acc": 0.9, "n": 10},
                              "battery_reference": {"acc": 0.5}},
                "train_n_original": 10, "train_n_widened": 20,
                "filter": {"hard_items_kept": 5, "easy_items_kept": 3},
                "contamination": {"widen": {"dropped": 0},
                                  "screen": {"dropped": 0},
                                  "confirm": {"dropped": 0}},
                "verdict_basis": "confirm fresh 0.80 vs gate 0.75",
                "win": True, "threshold": 0.75,
                "finalist": {"hidden": 0, "params": 10, "screen_acc": 0.9,
                             "screen_n": 10, "confirm_acc": 0.8,
                             "confirm_n": 10},
                "adopted_file": "coding/swarm/models/s-v2.json"}
        base.update(kw)
        return base

    def test_win_is_measured(self):
        from factory import executors
        subj = Subject(subject_id="s", kind="tier0_specialist", niche="review")
        v = executors.verify_measured(subj, None, self._mk_outcome())
        self.assertEqual(v.verdict, "WIN")
        self.assertTrue(v.measured)

    def test_revert_is_measured_not_shadow(self):
        from factory import executors
        subj = Subject(subject_id="s", kind="tier0_specialist", niche="review")
        v = executors.verify_measured(subj, None, self._mk_outcome(win=False))
        self.assertEqual(v.verdict, "REVERT")
        self.assertTrue(v.measured)

    def test_unsupported_subject_blocks_unmeasured(self):
        from factory import executors
        subj = Subject(subject_id="s", kind="tier0_specialist", niche="review")
        v = executors.verify_measured(
            subj, None, {"subject_id": "s", "supported": False,
                         "executed": False,
                         "block_reason": "no Phase B executor"})
        self.assertEqual(v.verdict, "BLOCKED")
        self.assertFalse(v.measured)


if __name__ == "__main__":
    unittest.main()
