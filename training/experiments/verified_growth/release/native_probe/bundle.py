"""Join sealed outputs to the independent grader's maker seeds after inference has ended."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build(path):
    raw = json.loads(path.read_bytes())
    assert "end_utc" in raw and all(r["state"] != "started" for r in raw["calls"])
    requests = json.loads((HERE / "requests.json").read_bytes())
    keys = json.loads((HERE / "draw-manifest.json").read_bytes())["selected"]
    assert raw["requests_sha256"] == sha256((HERE / "requests.json").read_bytes()).hexdigest()
    replies = {row["id"]: row.get("raw", "") for row in raw["calls"]}
    assert len(replies) == len(raw["calls"])
    grade_inputs = []
    for question in requests:
        ident = question["id"]
        meta = keys[ident]
        assert sha256(question["task"].strip().encode()).hexdigest() == meta["prompt_sha256"]
        grade_inputs.append({"id": ident, "task": question["task"], "raw": replies.get(ident, ""),
                             "maker": meta["maker"], "seed": meta["seed"]})
    return {"receipts_sha256": sha256(path.read_bytes()).hexdigest(), "rows": grade_inputs}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--receipts", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.write_text(json.dumps(build(args.receipts), indent=2, ensure_ascii=False) + "\n")
