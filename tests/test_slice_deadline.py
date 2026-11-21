"""S1 (hours), part A: a train slice stops at its budget and a stuck one is ended soon after it (g51: 17 of 20 slices
stopped at 170 minutes, one ran 220 and failed, and the train span grew 46 minutes for it). A fake clock, no model."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
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


@pytest.mark.parametrize("profile,minutes", [("auto", 170), ("85", 85), ("110", 110), ("170", 170)])
def test_the_train_step_and_job_have_time_limits_just_past_the_budget(tmp_path, profile, minutes):
    plan = FLOW["jobs"]["plan"]
    budget = next(s for s in plan["steps"] if s.get("id") == "budget")
    out = tmp_path / "output"
    env = dict(os.environ, PROFILE=profile, CHUNK_TOKENS="64", GITHUB_OUTPUT=str(out), GITHUB_STEP_SUMMARY=str(tmp_path / "summary"))
    subprocess.run(["bash", "-e", "-c", budget["run"]], env=env, check=True)
    limits = {k: int(v) for k, v in (line.split("=") for line in out.read_text().splitlines())}
    assert limits.pop("chunk_tokens") == (0 if profile == "auto" else 64)
    assert limits == {"minutes": minutes, "step_timeout": minutes + 30, "job_timeout": minutes + 55}
    assert budget["env"]["PROFILE"] == "${{ inputs.train_minutes || 'auto' }}"
    assert budget["env"]["CHUNK_TOKENS"] == "${{ vars.HIVE_CHUNK_CE || '0' }}"
    assert plan["outputs"]["chunk_tokens"] == "${{ steps.budget.outputs.chunk_tokens }}"
    assert all(plan["outputs"][f"train_{k}"] == "${{ steps.budget.outputs." + k + " }}" for k in limits)
    job = FLOW["jobs"]["train"]
    step = next(s for s in job["steps"] if s.get("name") == "Grow the cell")
    assert step["env"]["HIVE_TRAIN_MIN"] == "${{ needs.plan.outputs.train_minutes }}"
    assert step["env"]["HIVE_CHUNK_CE"] == "${{ needs.plan.outputs.chunk_tokens }}"
    assert step["timeout-minutes"] == "${{ fromJSON(needs.plan.outputs.train_step_timeout) }}"
    assert job["timeout-minutes"] == "${{ fromJSON(needs.plan.outputs.train_job_timeout) }}"
    assert 'timeout -k 60 $(( (MIN + 25) * 60 ))' in step["run"]
    up = job["steps"][-1]
    assert up["uses"].startswith("actions/upload-artifact") and "!cancelled()" in up["if"]  # what a slice kept is uploaded


def test_invalid_chunk_size_fails_before_creating_cpu_slices(tmp_path):
    budget = next(s for s in FLOW["jobs"]["plan"]["steps"] if s.get("id") == "budget")
    out = tmp_path / "output"
    env = dict(os.environ, PROFILE="85", CHUNK_TOKENS="-1", GITHUB_OUTPUT=str(out), GITHUB_STEP_SUMMARY=str(tmp_path / "summary"))
    p = subprocess.run(["bash", "-e", "-c", budget["run"]], env=env, capture_output=True, text=True)
    assert p.returncode != 0 and "HIVE_CHUNK_CE" in p.stdout and not out.exists()


def test_gguf_seconds_fake_clock():
    born, m = 1000.0, 170
    end = born + m * 60
    assert grow.gguf_seconds(end, born, m) == 900  # on time: the usual 15 minutes
    assert grow.gguf_seconds(end + 600, born, m) == 600  # a late row ended at +10 minutes: 10 minutes of the 20 left
    assert grow.gguf_seconds(end + 1100, born, m) == 180  # 100 s of wall left: 3 minutes always
    assert grow.gguf_seconds(end + 9999, born, m) == 180
    assert grow.gguf_seconds(end + 9999, born, 0) == 900  # no budget: the old rule
    worst = max(end + 600 + 600, end + 1100 + 180) - born  # row +10, then GGUF held to the wall or 3 minutes after
    assert worst / 60 <= 195



def test_measure_until_caps_the_ungated_measuring_phases():
    from training.grow import measure_until
    assert measure_until(1000.0, 0, 0.12) == 0.0
    assert measure_until(1000.0, 170, 0.12) == 1000.0 + 170 * 60 * 0.12  # 20.4 minutes, not g59's 57 and 35
    assert measure_until(1000.0, 1, 0.12) == 1000.0 + 120.0  # a short trial keeps its floor


def test_measuring_with_a_fake_clock_ends_inside_the_budget():
    """g59 timeline on a fake clock: the read measure (one row a minute) and the kept-back first measure (one row a
    minute) stop at their 12%, so training starts by 41 minutes and the loop's own check then ends it at the budget."""
    from training.grow import measure_until
    born, minutes, t = 0.0, 170, 0.0
    until = measure_until(t, minutes, 0.12)
    while t <= until:
        t += 60
    read_end = t
    until = measure_until(t, minutes, 0.12)
    while t <= until:
        t += 60
    spare = t - read_end
    assert t <= 45 * 60 and spare <= 21 * 60
    assert born + minutes * 60 - spare - t > 100 * 60  # most of the 170 minutes is left for training
