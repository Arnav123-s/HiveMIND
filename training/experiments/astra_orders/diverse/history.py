"""Verify the runtime wording index against the original G55 six-request resemblance measurements."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from team import familiarity, memory
from training.experiments.astra_orders import prepare


def verify(rows):
    inputs = json.loads((prepare.HERE / "inputs.json").read_text())
    prompts = {r["id"]:r["task"] for r in json.loads((prepare.HERE / "panel.json").read_text())}
    with tempfile.TemporaryDirectory() as tmp:
        index = Path(tmp) / "index"
        count = familiarity.build(rows, index, inputs["training_rows_sha256"])
        os.environ["HIVE_FAMILIAR_TASKS"] = str(index)
        corpus = familiarity.indexed_tasks()
        result = []
        assert len(corpus) == count == inputs["history_count"]
        for row in inputs["rows"]:
            mine = memory.words(prompts[row["id"]])
            best = max(len(mine & other) / max(1, len(mine | other)) for other in corpus)
            assert round(best, 6) == row["jaccard"]
            found = familiarity.familiar(prompts[row["id"]])
            assert found == (row["gate"] == "short")
            result.append({"id":row["id"], "nearest_jaccard": round(best, 6), "familiar":found})
        return {"checked_tasks":count, "rows_sha256":inputs["training_rows_sha256"],
                "index_sha256":hashlib.sha256(index.read_bytes()).hexdigest(), "panel":result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("rows", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.write_text(json.dumps(verify(args.rows), indent=2) + "\n")
