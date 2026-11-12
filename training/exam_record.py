"""One line in the record of the hive's exams, from the files of a sitting that ran somewhere else.

    python3 training/exam_record.py <folder with the sitting's <seed>.json>
The sitting ran in a job where the hive wrote and ran code of its own; this runs in the job that may write to the
repository. So nothing of the sitting is trusted but numbers and names this file knows: the line is built here, from
whole numbers within their bounds and the field names of the exam. Needs nothing but Python."""
import json
import re
import sys
from pathlib import Path

RECORD = Path(__file__).resolve().parent / "reports" / "exams.jsonl"
FIELDS = ("maths", "dates", "units", "given data", "code", "live facts", "websites", "instructions", "knowledge", "languages", "writing",
          "understanding")


def _int(x, most):
    return x if isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= most else None


def line(summary):
    """The record's line from a sitting's summary, or None if it is not one."""
    if not isinstance(summary, dict):
        return None
    seed, passed, tasks, minutes = (_int(summary.get(k), m) for k, m in (("seed", 10 ** 6), ("passed", 64), ("tasks", 64), ("minutes", 600)))
    if None in (seed, passed, tasks, minutes) or passed > tasks:
        return None
    by = {}
    for k, v in (summary.get("by_field") or {}).items() if isinstance(summary.get("by_field"), dict) else []:
        if k in FIELDS and isinstance(v, list) and len(v) == 2 and _int(v[0], 64) is not None and _int(v[1], 64) is not None and v[0] <= v[1]:
            by[k] = [v[0], v[1]]
    when, code = str(summary.get("when", "")), str(summary.get("code", ""))
    return {"seed": seed, "when": when if re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d", when) else "", "passed": passed, "tasks": tasks,
            "by_field": by, "minutes": minutes, "code": code if re.fullmatch(r"[0-9a-f]{4,12}", code) else "",
            "memory": "its own" if summary.get("memory") == "its own" else "none"}


def main(argv):
    done = {json.loads(ln).get("seed") for ln in RECORD.read_text().splitlines() if ln.strip()} if RECORD.exists() else set()
    added = 0
    for f in sorted(Path(argv[0]).glob("*.json")):
        if f.stat().st_size > 2_000_000:
            continue
        try:
            new = line(json.loads(f.read_text()).get("summary"))
        except (ValueError, AttributeError):
            new = None
        if new and new["seed"] not in done:
            with open(RECORD, "a") as out:
                out.write(json.dumps(new) + "\n")
            done.add(new["seed"])
            added += 1
    print(f"{added} sitting(s) added to the record")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
