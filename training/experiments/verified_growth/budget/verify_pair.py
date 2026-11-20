"""Verify the two real trainer receipts and the GGUFs emitted by the paired run."""
import argparse
from hashlib import file_digest, sha256
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent


def verify(results, scratch):
    source = json.loads((HERE / "environment.json").read_text())
    root = HERE.parents[3]
    for relative, expected in source["source_sha256"].items():
        if sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"source changed: {relative}")
    arms = {}
    for arm, fit_rows in (("half", 4), ("full", 8)):
        data = results["arms"][arm]
        receipt = data["result"]
        meta = receipt["meta"]
        assert meta["used"] == meta["passes"] == fit_rows
        assert meta["steps"] == fit_rows // 4 and meta["layers"] == [22, 35]
        assert meta["rank"] == 16 and meta["int8_base"] and not meta["gpu"]
        assert len(meta["kept_back"]) == 2
        if scratch:
            output = scratch / arm / "exports/t80+budgetstudy.gguf"
            with output.open("rb") as f:
                magic, version, count = struct.unpack("<4sIQ", f.read(16))
                f.seek(0)
                digest = file_digest(f, "sha256").hexdigest()
            if magic != b"GGUF" or version < 2 or count != 2 * 7 * 14 or digest != receipt["adapter_sha256"]:
                raise ValueError(f"incorrect {arm} export")
        arms[arm] = {k: v["before"] for k, v in meta["kept_back"].items()}
    assert arms["half"] == arms["full"], "initial held-out losses must be identical"
    assert results["arms"]["half"]["result"]["adapter_sha256"] != results["arms"]["full"]["result"]["adapter_sha256"]
    print("Whole-model trainer settings and paired held-back losses checked.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results", type=Path, default=HERE / "paired-results.json")
    p.add_argument("--scratch", type=Path, help="also verify the exported adapters and their tensor counts")
    args = p.parse_args()
    verify(json.loads(args.results.read_text()), args.scratch)
