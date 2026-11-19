"""Rebuild a preregistered corrective candidate from its public native training states and scores."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from training import domain_engram

CORRECTION_MARGIN = 8.0


def build(states, out, spellings):
    x, labels = states["features"], states["gold_tokens"]
    ids, gold = np.unique(labels, return_inverse=True)
    # Scores use the larger native logit across the accepted surface forms of each label.
    scores = states["class_scores"]
    best_competitor = states["other_best"]
    own = scores[np.arange(len(gold)), gold]
    targets = -0.5 * np.maximum(0.0, scores - own[:, None])
    targets[np.arange(len(gold)), gold] = np.maximum(0.0, CORRECTION_MARGIN + best_competitor - own)
    canonical, a, b, result = domain_engram.fit(x, labels, target_scores=targets)
    assert np.array_equal(ids, canonical)
    surface_ids, rows = [], []
    for i, word_id in enumerate(canonical):
        for surface_id in spellings[str(word_id)]:
            surface_ids.append(surface_id)
            rows.append(b[i])
    domain_engram.write_adapter(out, np.asarray(surface_ids), a, np.asarray(rows), 151669)
    result["sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", type=Path, help="water-v2 or timing-v2 report directory")
    parser.add_argument("--out", type=Path, required=True, help="new GGUF candidate file")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out already exists")
    with np.load(args.study / "training-states.npz") as states:
        spellings = json.loads((args.study / "spellings.json").read_text())
        print(json.dumps(build(states, args.out, spellings), indent=2))


if __name__ == "__main__":
    main()
