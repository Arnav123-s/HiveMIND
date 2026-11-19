"""Score the separate final production repeat against the frozen baseline and v1 rows."""
import argparse
import json
from pathlib import Path

from grade import grade

HERE = Path(__file__).resolve().parent
KNOWN = {"venue-seats": "integral formatting", "detector-recall": "integral formatting and delivery",
         "cache-straddle": "checked cache-line count"}


def compare(prior, current, ids, measure):
    outcomes = {"gain": [], "loss": [], "both": [], "neither": []}
    for ident in ids:
        before, after = prior[ident][measure], current[ident][measure]
        if before:
            outcomes["both" if after else "loss"].append(ident)
        else:
            outcomes["gain" if after else "neither"].append(ident)
    return outcomes


def finalize(output_directory):
    result = grade(output_directory, ["final_system"])
    current = {r["id"]: r for r in result["rows"]}
    frozen = json.loads((HERE / "results.json").read_text())
    result["previously_diagnosed"] = KNOWN
    result["compared_against"] = {}
    groups = {"all": list(current), "known_cases": list(KNOWN),
              "other_practical": [i for i, r in current.items() if r["stratum"] == "primary" and i not in KNOWN],
              "retention": [i for i, r in current.items() if r["stratum"] == "retention"]}
    for arm in ("baseline", "integrated"):
        prior = {r["id"]: r for r in frozen["rows"] if r["arm"] == arm}
        result["compared_against"][arm] = {
            name: {metric: compare(prior, current, ids, metric) for metric in ("correct", "content_correct")}
            for name, ids in groups.items()
        }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.write_text(json.dumps(finalize(args.root), indent=2, ensure_ascii=False) + "\n")
