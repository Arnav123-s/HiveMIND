"""Replay the join against official held rows. The scheduler never sees task text or grades."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from .halves import join


def verify(directory):
    done, partial, row_count = 0, 0, 0
    for path in sorted(directory.glob("held-*.zip")):
        with ZipFile(path) as z:
            name, = z.namelist()
            doc = json.loads(z.read(name))
        summary, tasks = doc["summary"], doc["tasks"]
        seat = summary["seat"]
        expected = (30 - seat)//8 + 1
        group = directory.name + "-" + path.stem
        with TemporaryDirectory() as tmp:
            parts = Path(tmp)
            boundary = (expected+1)//2
            for half, rows in enumerate((tasks[:boundary], tasks[boundary:]),1):
                header = dict(summary, group=group, half=half, started=0, ended=1, tasks=len(rows),
                              passed=sum(r["ok"] for r in rows))
                (parts/f"part-{half}-seat-{seat}.json").write_text(json.dumps(dict(summary=header,tasks=rows)))
            if len(tasks) != expected:
                try:
                    join(parts, parts/"out", seat, 8, 3, group)
                except ValueError:
                    partial += 1
                else:
                    raise AssertionError("incomplete historical seat was accepted")
                continue
            joined = join(parts, parts/"out", seat, 8, 3, group)
            assert joined["passed"] == summary["passed"] and joined["tasks"] == summary["tasks"]
            assert json.loads((parts/"out"/f"held_{seat}.json").read_text())["tasks"] == tasks
            done += 1
            row_count += len(tasks)
    return dict(complete=done, partial=partial, rows_preserved=row_count)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archives", type=Path)
    args = p.parse_args()
    print(json.dumps({g:verify(args.archives/g) for g in ("g53","g54","g55","g56")}, indent=2))
