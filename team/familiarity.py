"""Compare a request with task wording from checked memory or a frozen pre-exam training corpus."""
import argparse
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path


def build(rows, output, expected=None):
    """Project an existing verified training artifact to request texts. No model messages, programs or grades."""
    digest = hashlib.sha256()
    tasks = set()
    with rows.open("rb") as source:
        for line in source:
            digest.update(line)
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("type") == "first" and row.get("checked") is not False and isinstance(row.get("task"), str) and row["task"]:
                tasks.add(row["task"])
    if expected is not None and digest.hexdigest() != expected:
        raise ValueError("training artifact does not match the requested digest")
    if not tasks:
        raise ValueError("training artifact has no checked first-program task rows")
    data = {"version": 1, "rows_sha256": digest.hexdigest(), "tasks": sorted(tasks)}
    output.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return len(tasks)


@lru_cache(maxsize=2)
def _load(path, version):
    from . import memory
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or set(data) != {"version", "rows_sha256", "tasks"} or data["version"] != 1
            or not isinstance(data["rows_sha256"], str) or len(data["rows_sha256"]) != 64
            or not isinstance(data["tasks"], list) or not all(isinstance(task, str) for task in data["tasks"])):
        raise ValueError("invalid checked task index")
    return tuple(frozenset(memory.words(task)) for task in data["tasks"])


def indexed_tasks():
    path = os.environ.get("HIVE_FAMILIAR_TASKS")
    if not path:
        return ()
    path = Path(path).resolve()
    # Reading a designated but missing or malformed index must fail the trial, rather than silently changing the arm.
    stat = path.stat()
    return _load(path, (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns))


def familiar(task):
    from . import memory, solo
    mine = memory.words(task)
    def matches(prior):
        return len(mine & prior) >= 0.30 * max(1, len(mine | prior))
    if any(matches(prior) for prior in indexed_tasks()):
        return True
    return any(matches(memory.words(row.get("task", ""))) for row in solo.solved() if row.get("checked") is True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rows-sha256")
    args = parser.parse_args()
    print(f"{build(args.rows, args.output, args.rows_sha256)} distinct checked task texts")
