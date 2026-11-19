"""Replay the G48 training submission and evaluate a separate exhaustive small-domain panel in WASI."""
import argparse
import hashlib
import itertools
import json
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from team.config import fieldwork_sdk_path
from training.experiments.fieldwork import practice_import, work
from training.experiments.fieldwork.guest import Guest

SEED = 6084116933787393751
TASK = Path("practice_10004810/h10004810_02")
FILES = [TASK / "exam.json", TASK / "members/TASK.md", TASK / "members/work/member1_1.py"]


def doubled_lattice(intervals):
    # On a half-unit grid, separated integer endpoints leave a missing half-step.
    points = sorted({p for lo, hi in intervals for p in range(2 * lo, 2 * hi + 1)})
    out = []
    for p in points:
        if out and p == out[-1][1] + 1:
            out[-1][1] = p
        else:
            out.append([p, p])
    return [[lo // 2, hi // 2] for lo, hi in out]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, default=fieldwork_sdk_path())
    args = parser.parse_args()
    manifest = json.loads((HERE / "manifest.json").read_bytes())
    artifact = HERE / "training-record.zip"
    if hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest["record_zip_sha256"]:
        raise ValueError("record hash mismatch")
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(artifact) as z:
        tmp = Path(tmp)
        for name in FILES:
            raw = z.read(name.as_posix())
            if hashlib.sha256(raw).hexdigest() != manifest["members"][name.as_posix()]:
                raise ValueError("submission member hash mismatch")
            path = tmp / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        guest = Guest(args.sdk)
        receipt = practice_import.import_practice(tmp / TASK, tmp / "bank", guest, seed=SEED)
        if receipt["status"] != "qualified":
            raise ValueError(f"program did not qualify: {receipt}")
        program, = work.load_bank(tmp / "bank")
        previously_seen = {json.dumps(row["input"]) for row in practice_import.probes(SEED)}
        previously_seen.update(json.dumps(row) for row, _ in practice_import.PUBLIC)
        endpoints = [-2, 0, 1, 4]
        intervals = list(itertools.combinations_with_replacement(endpoints, 2))
        panel = []
        for size in range(4):
            for pairs in itertools.product(intervals, repeat=size):
                if json.dumps(pairs) not in previously_seen:
                    panel.append({"input": pairs, "output": doubled_lattice(pairs)})
        passed, _ = work.check(guest, program["source"], panel, explain=False)
        receipt["separate_exhaustive_panel"] = {"passed": passed, "total": len(panel)}
        print(json.dumps(receipt, indent=2))
        return 0 if passed == len(panel) else 1


if __name__ == "__main__":
    raise SystemExit(main())
