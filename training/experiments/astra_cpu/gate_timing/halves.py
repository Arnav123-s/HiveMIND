"""Optional held-seat runner for an isolated two-runner trial. The grow workflow does not invoke it."""
import argparse
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from training import exam


def join(folder, out, seat, seats, per, group):
    expected = exam.held_share(exam.held_exam(per), seat, seats)
    boundary = (len(expected)+1)//2
    rows, summaries = [], []
    for half, reference in ((1, expected[:boundary]), (2, expected[boundary:])):
        doc = json.loads((folder / f"part-{half}-seat-{seat}.json").read_text())
        summary, tasks = doc["summary"], doc["tasks"]
        fields = dict(exam="held", memory="none", group=group, seat=seat, seats=seats, per=per, half=half)
        if any(summary.get(k) != v for k,v in fields.items()):
            raise ValueError("held halves have different settings or run identities")
        if (not isinstance(tasks, list) or len(tasks) != len(reference)
                or summary.get("tasks") != len(tasks) or not isinstance(summary.get("members"), str)
                or not all(isinstance(summary.get(k), (float,int)) and math.isfinite(summary[k])
                           for k in ("started","ended")) or summary["ended"] < summary["started"]):
            raise ValueError("incomplete held half")
        for task, (tid, field, kind, question, check) in zip(tasks, reference):
            if (task.get("id"), task.get("field"), task.get("kind"), task.get("task"), task.get("maker")) != (
                    tid, field, kind, question, getattr(check,"maker","")) or type(task.get("ok")) is not bool:
                raise ValueError("held half does not contain the expected graded tasks in order")
        if summary.get("passed") != sum(r["ok"] for r in tasks):
            raise ValueError("held half grade summary disagrees with rows")
        rows.extend(tasks)
        summaries.append(summary)
    if summaries[0]["members"] != summaries[1]["members"]:
        raise ValueError("held halves used different workers")
    seconds = max(r["ended"] for r in summaries) - min(r["started"] for r in summaries)
    summary = dict(exam="held", seat=seat, seats=seats, per=per, passed=sum(r["ok"] for r in rows),
                   tasks=len(rows), minutes=round(seconds/60), memory="none", members=summaries[0]["members"])
    out.mkdir(parents=True, exist_ok=True)
    destination = out / f"held_{seat}.json"
    encoded = json.dumps(dict(summary=summary,tasks=rows), indent=1)
    with NamedTemporaryFile(dir=out, mode="w") as stage:
        stage.write(encoded)
        stage.flush()
        try:
            os.link(stage.name, destination)
        except FileExistsError:
            if destination.read_text() != encoded:
                raise ValueError("a different joined grade already exists")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["sit","join"])
    p.add_argument("--half", type=int, choices=[1,2])
    p.add_argument("--seat", required=True, type=int, choices=range(1,9))
    p.add_argument("--group", required=True, help="same unique generation, run attempt and arm on both runners")
    p.add_argument("--parts-dir", required=True, type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    if args.action == "sit":
        if args.half is None:
            p.error("sit requires --half")
        exam.sit_held(args.seat, 8, 3, out=args.parts_dir, seconds=900, half=args.half, group=args.group)
    elif args.out is None:
        p.error("join requires --out")
    else:
        print(json.dumps(join(args.parts_dir, args.out, args.seat, 8, 3, args.group)))


if __name__ == "__main__":
    main()
