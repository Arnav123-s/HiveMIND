"""scripts/capped_run.sh (the trainer's memory cap and low priority on the runner) and the guard's cgroup ceiling."""
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import yaml

from training import grow

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capped_run.sh"
MB, GB = 2**20, 2**30


def _limits(total):
    return subprocess.run(["bash", str(SCRIPT), "--limits", str(total)], capture_output=True, text=True).stdout.split()


def test_limits_leave_the_runner_agent_1200_mb_and_high_is_512_below_max():
    assert _limits(15990) == ["14278", "14790"]  # a 16 GB runner: free -m says about 15990
    assert _limits(7500) == ["5788", "6300"]


def test_a_small_or_unreadable_total_gets_no_cap():
    assert _limits(2999) == ["none"] and _limits("") == ["none"] and _limits("abc") == ["none"]


def test_the_trainers_measured_peak_fits_under_the_cap_on_a_16gb_runner():
    high, mx = map(int, _limits(15990))
    assert 12.68 * 1024 < high < mx  # the whole cgroup's measured peak, 12.52-12.68 GiB (measurement.md), is under High


def _bare_path(tmp_path):
    """A PATH with the tools the script needs but no systemd-run, sudo or ionice."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for tool in ("bash", "free", "awk", "nice", "timeout", "sh", "true", "false", "env", "id", "sleep"):
        found = subprocess.run(["bash", "-c", f"command -v {tool}"], capture_output=True, text=True).stdout.strip()
        if found:
            (bin_ / tool).symlink_to(found)
    return str(bin_)


def _run(tmp_path, *args, path=None):
    env = dict(os.environ, PATH=path or _bare_path(tmp_path))
    return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env)


def test_without_systemd_run_the_command_runs_plain_and_its_status_passes(tmp_path):
    p = _run(tmp_path, "--", "bash", "-c", "echo hello; exit 7")
    assert p.returncode == 7 and "hello" in p.stdout and "no memory cap" in p.stderr


def test_without_systemd_run_a_timeout_ends_the_command(tmp_path):
    assert _run(tmp_path, "--timeout", "1", "--", "sleep", "30").returncode == 124


def test_a_failed_scope_probe_falls_back_to_the_plain_command(tmp_path):
    path = _bare_path(tmp_path)
    for tool in ("sudo", "systemd-run"):  # present, but the scope cannot start
        (Path(path) / tool).write_text("#!/bin/bash\nexit 1\n")
        (Path(path) / tool).chmod(0o755)
    p = _run(tmp_path, "--", "bash", "-c", "echo ran; exit 3", path=path)
    assert p.returncode == 3 and "ran" in p.stdout and "without the cap" in p.stderr


def test_the_train_step_runs_through_the_cap_inside_the_outer_timeout():
    flow = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())
    step = next(s for s in flow["jobs"]["train"]["steps"] if s.get("name") == "Grow the cell")["run"]
    assert "scripts/capped_run.sh --timeout" in step and "-- python training/grow.py train" in step


def _fake_cgroup(tmp_path, **files):
    root = tmp_path / "cgroup"
    leaf = root / "w"
    leaf.mkdir(parents=True)
    for name, text in files.items():
        (leaf / name.replace("_", ".")).write_text(text)
    member = tmp_path / "membership"
    member.write_text("0::/w\n")
    return root, member, leaf


def test_guard_limits_read_max_and_high_and_treat_max_as_none(tmp_path):
    root, member, leaf = _fake_cgroup(tmp_path, memory_max=str(14790 * MB), memory_high=str(14278 * MB))
    assert grow._cgroup_limits(root, member) == [(leaf / "memory.current", 14790 * MB), (leaf / "memory.current", 14278 * MB)]
    root, member, _ = _fake_cgroup(tmp_path / "b", memory_max="max\n", memory_high="max\n")
    assert grow._cgroup_limits(root, member) == []


def test_guard_limits_with_a_missing_file_or_membership(tmp_path):
    root, member, leaf = _fake_cgroup(tmp_path, memory_high=str(8 * GB))
    assert grow._cgroup_limits(root, member) == [(leaf / "memory.current", 8 * GB)]  # no memory.max: only High counts
    assert grow._cgroup_limits(root, tmp_path / "nothing") == []


def test_the_guards_ceiling_is_the_lower_of_host_and_cgroup(tmp_path):
    root, member, leaf = _fake_cgroup(tmp_path, memory_max=str(10 * GB), memory_high=str(9 * GB))
    (leaf / "memory.current").write_text(str(6 * GB))
    limits = grow._cgroup_limits(root, member)
    host = lambda avail: SimpleNamespace(virtual_memory=lambda: SimpleNamespace(available=avail))
    assert grow._available(host(12 * GB), limits) == 3 * GB  # the cap (High 9 - used 6) is under the host's 12
    assert grow._available(host(2 * GB), limits) == 2 * GB  # the host is under the cap
