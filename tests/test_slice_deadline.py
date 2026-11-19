"""S1 (hours), part A: a train slice stops at its budget and a stuck one is ended soon after it (g51: 17 of 20 slices
stopped at 170 minutes, one ran 220 and failed, and the train span grew 46 minutes for it). A fake clock, no model."""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training import grow  # noqa: E402

FLOW = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())


def test_a_row_may_take_25_minutes_while_the_time_lasts_and_10_once_it_is_up():
    born, minutes = 1000.0, 170
    assert grow.row_limit(born + 60, born, minutes, 1500) == 1500
    assert grow.row_limit(born + 170 * 60, born, minutes, 1500) == 1500  # exactly at the budget: not yet late
    assert grow.row_limit(born + 170 * 60 + 1, born, minutes, 1500) == 600
    assert grow.row_limit(born + 999 * 60, born, minutes, 1500) == 600
    assert grow.row_limit(born + 999 * 60, born, 0, 1500) == 1500  # no budget (tests, whole runs by rows): the old rule
    assert grow.row_limit(born + 999 * 60, born, minutes, 300) == 300  # never longer than the row limit itself


def test_the_lessons_second_measure_stops_at_the_deadline(monkeypatch):
    import torch

    class Model:
        training = False

        def eval(self):
            pass

        def train(self):
            pass

        def __call__(self, input_ids, logits_to_keep):
            clock[0] += 100.0  # each row takes 100 s
            return type("O", (), {"logits": torch.zeros(1, logits_to_keep, 5)})()

    clock = [0.0]
    monkeypatch.setattr(grow.time, "time", lambda: clock[0])
    import contextlib
    items = [("k", (torch.zeros(1, 4, dtype=torch.long), 2)) for _ in range(10)]
    full = grow.kept_loss(Model(), items, "cpu", contextlib.nullcontext)
    assert len(full["k"]) == 10
    clock[0] = 0.0
    cut = grow.kept_loss(Model(), items, "cpu", contextlib.nullcontext, until=350.0)
    assert len(cut["k"]) == 4  # rows begun at 0, 100, 200, 300 s; none after 350


def test_the_train_step_and_job_have_time_limits_just_past_the_budget():
    job = FLOW["jobs"]["train"]
    step = next(s for s in job["steps"] if s.get("name") == "Grow the cell")
    assert "MIN=170" in step["run"]
    assert 170 < step["timeout-minutes"] <= 170 + 15  # the budget and 15 minutes for the last row, the measure and the GGUF
    assert job["timeout-minutes"] <= 200 and job["timeout-minutes"] > step["timeout-minutes"]  # setup, step, upload
    up = job["steps"][-1]
    assert up["uses"].startswith("actions/upload-artifact") and "!cancelled()" in up["if"]  # what a slice kept is uploaded
