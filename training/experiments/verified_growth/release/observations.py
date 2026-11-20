"""Extract anonymous, grade-free inputs that were actually available at each point in an exam."""
import argparse
import gzip
import json
from pathlib import Path
import re
from zipfile import ZipFile

from audit import HERE, PULSE, digest


def materialize(archives):
    records = {}
    for src in json.loads((PULSE / "artifacts.json").read_text()):
        if src["generation"] not in ("g51", "g52") or "-after-" not in src["name"]:
            continue
        path = archives / (str(src["id"]) + ".zip")
        assert digest(path.read_bytes()) == src["sha256"]
        generation = src["generation"]
        with ZipFile(path) as z:
            for name in z.namelist():
                if not re.fullmatch(r"exam_held_\d+/x_[^/]+/members/TASK.md", name):
                    continue
                task = z.read(name).decode().strip()
                key = digest(task.encode())
                rec = records.setdefault(key, {"request": task, "files": {}, "arms": {}})
                members = name.removesuffix("TASK.md")
                report_name = members.removesuffix("members/") + "REPORT.md"
                report = z.read(report_name).decode() if report_name in z.namelist() else ""
                sources = []
                for filename in sorted(z.namelist()):
                    if not filename.startswith(members):
                        continue
                    relative = filename.removeprefix(members)
                    if re.fullmatch(r"(?:work|member\d+)/member\d+_\d+\.py", relative):
                        sources.append([relative, z.read(filename).decode()])
                assert generation not in rec["arms"]
                rec["arms"][generation] = {"programs": sources, "visible_report": report,
                                           "artifact_id": src["id"]}
    assert len(records) == 30 and all(set(r["arms"]) == {"g51", "g52"} for r in records.values())
    return records


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archives", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    rows = materialize(args.archives)
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    args.out.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    print(len(rows), "anonymous questions", digest(raw))
