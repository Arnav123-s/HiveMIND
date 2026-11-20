"""Apply the independently frozen inline-file transport without importing the official exam or labels."""
import argparse
import gzip
import json
from pathlib import Path
import sys

from audit import HERE, digest

sys.path.insert(0, str(HERE.parents[3]))
from training.experiments.verified_growth.composer import solver
from training.experiments.verified_growth.inline import ingress


def select(bridge_sha256):
    assert digest(Path(ingress.__file__).read_bytes()) == bridge_sha256
    planner_sha = digest(Path(solver.__file__).read_bytes())
    assert planner_sha == "23eaba4bbca3e96663f8b2e5335b7ed6428da6c0e0c33ccd3d675c213038fb68"
    packed = gzip.decompress((HERE / "observations.json.gz").read_bytes())
    assert digest(packed) == "17118747aa857ea15845d2b0a4ed674d4cd2e207c85ab5d7d8b5dd2163d06540"
    rows = {}
    for key, case in sorted(json.loads(packed).items()):
        req, files = case["request"], case["files"]
        assert digest(req.encode()) == key and not files
        parsed = ingress.extract(req, files)
        bare = solver.run_files(req, files, mode="rules")
        bridged = ingress.solve_message(req, files, mode="rules")
        rows[key] = {"rules": bare, "bridged_rules": bridged, "bound": parsed is not None}
        if parsed:
            rows[key]["input_file_sha256"] = {f: digest(v.encode()) for f, v in parsed[1].items()}
            rows[key]["remaining_prompt_sha256"] = digest(parsed[0].encode())
    return {"bridge_sha256": bridge_sha256, "planner_sha256": planner_sha,
            "raw_inputs_sha256": digest(packed), "records": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = select(args.bridge_sha256)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
