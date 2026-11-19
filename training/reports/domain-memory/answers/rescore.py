"""Grade the saved, user-visible replies with the separate frozen keys. No model required."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

from grade import extract, numeric_content

HERE = Path(__file__).resolve().parent


def rescore(path):
    keys = json.loads((HERE / "keys.json").read_text())
    panel = {task["id"]: task["stratum"] for task in json.loads((HERE / "panel.json").read_text())}
    counts = defaultdict(Counter)
    seen = defaultdict(set)
    for row in json.loads(path.read_text())["rows"]:
        arm, ident = row["arm"], row["id"]
        if ident in seen[arm]:
            raise ValueError(f"Duplicate {arm}/{ident}")
        seen[arm].add(ident)
        key, phase = keys[ident], panel[ident]
        visible = row["text"] or ""
        strict = extract(visible, key["format"])
        content = numeric_content(visible) if strict is None and key["format"] == "integer" else strict
        delivered = row["error"] is None and (not row["worked"] or row["agreed"] is True)
        correct = delivered and strict == key["answer"]
        content_correct = delivered and content == key["answer"]
        if (correct, content_correct) != (row["correct"], row["content_correct"]):
            raise ValueError(f"Disagreement grading {arm}/{ident}")
        counts[arm][phase + "_strict"] += correct
        counts[arm][phase + "_content"] += content_correct
        counts[arm][phase + "_total"] += 1
    if not seen or any(ids != set(panel) for ids in seen.values()):
        raise ValueError("At least one arm has incomplete coverage")
    return counts


if __name__ == "__main__":
    result_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results.json"
    print(json.dumps(rescore(result_path), indent=2))
