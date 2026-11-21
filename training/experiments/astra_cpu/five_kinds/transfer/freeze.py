"""Draw one independently seeded ordinary question per selected maker and seal its exact messages."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from team import solo
from team.tools.sandbox import give, note
from training import exam

HERE = Path(__file__).resolve().parent
FAMILIES = ("bank", "calc", "lru", "machine", "schedule")


def build(archive):
    seen = {" ".join(json.loads(line)["task"].casefold().split()) for line in archive.read_text().splitlines()}
    result = []
    for name in FAMILIES:
        maker = "h_prog_" + name
        seed = f"astra-independent-transfer-v1-20261121/{maker}/0"
        _, _, task, _ = exam.remake(maker, seed, 0)
        assert " ".join(task.casefold().split()) not in seen, "collision with cumulative G56 archive"
        with tempfile.TemporaryDirectory() as tmp:
            provided = give(task, Path(tmp), skip=solo.wanted(task))
            user = "TASK: " + task + note(provided)
        result.append({"name": name, "maker": maker, "seed": seed, "level": 0, "task": task,
                       "messages": [{"role": "system", "content": solo.orders("t80+cell", "2026-11-21 (Saturday)")},
                                    {"role": "user", "content": user}]})
    return {"g56_rows_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "rows": result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(build(args.archive), indent=2, ensure_ascii=False) + "\n")
