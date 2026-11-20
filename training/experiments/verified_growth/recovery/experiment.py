"""Compare an uninterrupted training slice to genuine process deaths and fresh restarts."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import torch

from training.experiments.verified_growth.recovery import checkpoint


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def check_equal(first, second):
    if isinstance(first, torch.Tensor):
        return type(second) is type(first) and first.dtype == second.dtype and torch.equal(first, second)
    if isinstance(first, dict):
        return list(first) == list(second) and all(check_equal(first[k], second[k]) for k in first)
    if isinstance(first, (list, tuple)):
        return type(first) is type(second) and len(first) == len(second) and all(check_equal(a, b) for a, b in zip(first, second))
    return type(first) is type(second) and first == second


def load(path):
    return torch.load(path, map_location="cpu", weights_only=True)


def execute(work, name, retain=None, crash=False, restore=False):
    host = work / name
    host.mkdir()
    final = host / "result.pt"
    command = [sys.executable, "-m", "training.experiments.verified_growth.recovery.slice", "--out", str(final)]
    if retain:
        command.extend(["--store", str(retain)])
    if crash:
        command.extend(["--fail-row", "95"])
    if restore:
        command.append("--resume")
    # A new temporary working directory per process and intentionally different hash seeds.
    env = os.environ | {"PYTHONPATH": str(ROOT), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                        "HIVE_DEQ": "torch", "PYTHONHASHSEED": str(391 if restore else 42)}
    proc = subprocess.run(command, env=env, cwd=host, capture_output=True, text=True, timeout=120)
    if proc.returncode != (75 if crash else 0):
        raise RuntimeError(f"{name}: {proc.returncode} {proc.stderr[-2000:]}")
    receipt = json.loads(proc.stdout.splitlines()[-1])
    if crash:
        if final.exists():
            raise AssertionError("failed runner produced a final model")
        shutil.rmtree(host)
    return receipt, final


def compare():
    with tempfile.TemporaryDirectory(prefix="hive-recovery-") as scratch:
        root = Path(scratch)
        store = root / "retain"
        reference, ref_file = execute(root, "uninterrupted")
        failed, _ = execute(root, "lost-without-store", crash=True)
        restarted, restart_file = execute(root, "restart-from-zero")
        saved, _ = execute(root, "lost-with-store", retain=store, crash=True)
        ref_state = load(ref_file)
        identity = ref_state["identity"]
        retained = sorted(store.glob("step-*.pt"))
        # Try to restore a still-valid snapshot with the wrong input identity.
        try:
            checkpoint.latest(store, identity | {"data": "different-shard"})
            raise AssertionError("accepted another shard")
        except ValueError as exc:
            wrong_identity = str(exc)
        # A partial temp and truncated newest published object must preserve the previous valid checkpoint.
        corrupt = root / "damaged"
        shutil.copytree(store, corrupt)
        (corrupt / ".pending-interrupted").write_bytes(b"incomplete")
        newest = corrupt / retained[-1].name
        newest.write_bytes(newest.read_bytes()[:1000])
        fallback = checkpoint.latest(corrupt, identity)["step"]
        fallback_run, fallback_file = execute(root, "restore-earlier", retain=corrupt, restore=True)
        # Negative control: same weights, row cursor, exact picker and RNG; intentionally reset AdamW moments.
        reset = root / "reset-moments"
        reset.mkdir()
        altered = checkpoint.latest(store, identity)
        altered["optimizer"]["state"].clear()
        checkpoint.publish(reset, altered)
        _, no_moments_file = execute(root, "restore-without-moments", retain=reset, restore=True)
        resumed, resume_file = execute(root, "restore-best", retain=store, restore=True)
        compares = {}
        for name, path in (("from_zero", restart_file), ("resume", resume_file), ("resume_fallback", fallback_file)):
            other = load(path)
            compares[name] = {key: check_equal(value, other[key]) for key, value in ref_state.items()}
            assert all(compares[name].values()), compares[name]
        costs = {"uninterrupted": reference["rows_executed"],
                 "restart_from_zero": failed["rows_executed"] + restarted["rows_executed"],
                 "resume": saved["rows_executed"] + resumed["rows_executed"],
                 "resume_after_corruption": saved["rows_executed"] + fallback_run["rows_executed"]}
        assert (len(retained), resumed["initial_step"], fallback) == (4, 20, 15)
        assert costs == {"uninterrupted": 128, "restart_from_zero": 223, "resume": 143, "resume_after_corruption": 163}
        no_moments = load(no_moments_file)
        missing_moments_equal = check_equal(no_moments["parameters"], ref_state["parameters"])
        assert not missing_moments_equal
        return {"slice": identity, "protocol_sha256": checkpoint.digest(HERE / "protocol.md"),
                "torch": str(torch.__version__), "worker_processes": 7, "weights_match_after_resetting_adam_moments": missing_moments_equal, "rows_executed_including_lost_work": costs,
                "bitwise_state_equality": compares, "wrong_identity_rejection": wrong_identity,
                "fallback_to_step_after_truncation": fallback, "first_loss": ref_state["history"][0][2],
                "last_loss": ref_state["history"][-1][2], "row_loss_sequence_sha256":
                sha256(json.dumps(ref_state["history"], separators=(",", ":")).encode()).hexdigest(),
                "runs": {"uninterrupted": reference, "lost_without_store": failed, "restart_from_zero": restarted,
                         "lost_with_store": saved, "resume": resumed, "resume_after_corruption": fallback_run}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = compare()
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["rows_executed_including_lost_work"]))
