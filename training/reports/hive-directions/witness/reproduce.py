"""Verify each selected source, then run it only through the repository WebAssembly guest."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[3]))
from training.experiments.fieldwork.guest import Guest


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_archive(path, manifest):
    if path.stat().st_size != manifest["archive_bytes"] or digest(path.read_bytes()) != manifest["archive_sha256"]:
        raise ValueError("Archive does not match GitHub's artifact digest")
    with zipfile.ZipFile(path) as z:
        for row in [*manifest["candidates"], manifest["task_file"]]:
            if z.read(row["archive_entry"]) != (ROOT / row["local"]).read_bytes():
                raise ValueError(f"Different bytes in {row['local']}")
        for row in manifest["candidates"]:
            member, entry = row["member"], Path(row["archive_entry"])
            pattern = re.escape(entry.parent.as_posix()) + rf"/member{member}_(\d+)\.py"
            turns = [int(m[1]) for name in z.namelist() if (m := re.fullmatch(pattern, name))]
            if entry.name != f"member{member}_{max(turns)}.py":
                raise ValueError(f"Not the last recorded attempt of member {member}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True, help="directory with WASI python.wasm and lib/")
    parser.add_argument("--archive", type=Path, help="optional full original gate-work-after-3.zip to authenticate the extracted bytes")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "manifest.json").read_text())
    if args.archive:
        verify_archive(args.archive, manifest)
    spec = json.loads((ROOT / "probes.json").read_text())
    inputs = [{"operation": case["operation"], "text": case["text"]} for case in spec["inputs"]]
    guest = Guest(args.sdk)
    wrapper = "\ndef solve(probe):\n    return tokens(probe['text']) if probe['operation'] == 'tokens' else evaluate(probe['text'])\n"
    results = []
    for row in manifest["candidates"]:
        raw = (ROOT / row["local"]).read_bytes()
        if digest(raw) != row["sha256"]:
            raise ValueError(f"Source hash mismatch: {row['local']}")
        actual, fuel, seconds = guest.run(raw.decode() + wrapper, inputs, fuel=4_000_000_000)
        passed = [obs.get("value") == case["expected"] for obs, case in zip(actual, spec["inputs"], strict=True)]
        results.append({"member": row["member"], "passed": passed, "actual": actual, "fuel": fuel, "seconds": seconds})
    winners = [r["member"] for r in results if all(r["passed"])]
    print(json.dumps({"candidates": results, "selected": winners[0] if len(winners) == 1 else None}, indent=2))


if __name__ == "__main__":
    main()
