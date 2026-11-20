"""Run frozen entrants on grade-free observations. This process never imports any exam checker."""
import argparse
import gzip
import json
from pathlib import Path
import sys
import time

from audit import HERE, digest

ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from training.experiments.verified_growth.composer import learner, solver
from training.experiments.verified_growth.file_relay import relay
from training.experiments.fieldwork.guest import Guest


def frozen_sources():
    required = {
        solver: "23eaba4bbca3e96663f8b2e5335b7ed6428da6c0e0c33ccd3d675c213038fb68",
        learner: "dc0e6951376d7379a185e4b498082c478c2f2063ff570d753b339f0c843036ab",
        relay: "63a3e2ba9216b5f8d5854c8a628675ed0e81abf98cc92d6d5f5b67aef0658bb1",
    }
    for module, expected in required.items():
        assert digest(Path(module.__file__).read_bytes()) == expected, module.__file__
    return {m.__name__: sha for m, sha in required.items()}


def select(sdk):
    sources = frozen_sources()
    packed = gzip.decompress((HERE / "observations.json.gz").read_bytes())
    assert digest(packed) == "17118747aa857ea15845d2b0a4ed674d4cd2e207c85ab5d7d8b5dd2163d06540"
    records = json.loads(packed)
    guest = Guest(sdk)
    responses = {}
    for key, row in sorted(records.items()):
        assert digest(row["request"].encode()) == key
        answer = solver.run_files(row["request"], row["files"], mode="learned")
        item = {"table": answer, "relay": {}}
        for gen, observed in sorted(row["arms"].items()):
            # The entrant is handed only that sitting's source and report.
            item["relay"][gen] = relay.propose(row["request"], row["files"], observed["programs"],
                                                observed["visible_report"], guest=guest)
        responses[key] = item
    return {"sources": sources, "raw_inputs_sha256": digest(packed), "decisions": responses}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = select(args.sdk)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("Wrote", len(result["decisions"]), "paired submissions in", round(time.monotonic()-started, 2), "s")
    for name in ("table", "g51", "g52"):
        picked = [v["table"] if name == "table" else v["relay"][name] for v in result["decisions"].values()]
        print(name, sum(v["status"] == "answered" for v in picked), "offered")
