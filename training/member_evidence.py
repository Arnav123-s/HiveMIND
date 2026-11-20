"""Archive requested worker files after an exam, outside the graded work directory."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile

from team.deliverables import regular, wanted


# each_member in training/exam.py already excludes larger files when constructing its grading copy.
MAX_FILE_BYTES = 5_000_000


def capture(task, members, destination):
    """Preserve each seat's own bytes in a new evidence directory; this makes no delivery decision."""
    destination = Path(destination)
    names = wanted(task)
    if not names:
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"purpose": "ungraded worker evidence", "task_sha256": sha256(task.encode()).hexdigest(),
                "requested": names, "seats": []}
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        snapshot = Path(temporary) / "snapshot"
        snapshot.mkdir()
        seen = set()
        for member in members:
            seat = member["seat"]
            if type(seat) is not int or seat < 1 or seat in seen:
                raise ValueError("expected distinct positive seat numbers")
            seen.add(seat)
            files = {}
            submitted = member.get("byte_hashes", {})
            work = member.get("work")
            for name in names:
                if work is None:
                    files[name] = {"status": "no worker directory"}
                    continue
                try:
                    with regular(Path(work) / name) as original:
                        contents = original.read(MAX_FILE_BYTES + 1)
                except FileNotFoundError:
                    files[name] = {"status": "missing"}
                    continue
                except (OSError, ValueError):
                    files[name] = {"status": "unreadable or not a regular file"}
                    continue
                if len(contents) > MAX_FILE_BYTES:
                    files[name] = {"status": "too large"}
                    continue
                digest = sha256(contents).hexdigest()
                if name in submitted and submitted[name] != digest:
                    files[name] = {"status": "changed since submission",
                                   "recorded_sha256": submitted[name], "observed_sha256": digest}
                    continue
                relative = Path(f"seat-{seat}") / "artifacts" / name
                target = snapshot / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(contents)
                files[name] = {"status": "archived", "sha256": digest, "bytes": len(contents),
                               "path": relative.as_posix(), "matched_submission_hash": name in submitted}
            manifest["seats"].append({"seat": seat, "files": files})
        (snapshot / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        # Immutable snapshots prevent a rerun with different work from overwriting the original evidence.
        snapshot.rename(destination)
    return manifest


def recorded_members(home):
    """Read only the seat and the file provenance, ignoring answers and grade records."""
    for path in sorted(home.glob("member*.json")):
        number = re.fullmatch(r"member([1-9][0-9]*)", path.stem)
        if not number:
            continue
        seat = int(number[1])
        try:
            with regular(path) as file:
                row = json.load(file)
        except (OSError, ValueError):
            row = {}
        if not isinstance(row, dict):
            row = {}
        work = None
        if isinstance(row.get("work"), str) and row["work"]:
            candidate = Path(row["work"])
            normal = "work" if seat == 1 else f"member{seat}"
            owned = candidate.name == normal or re.fullmatch(rf"member{seat}-(?:retry-)?[\w-]+", candidate.name)
            if owned and candidate.parent.resolve() == home.resolve() and not candidate.is_symlink():
                work = candidate
        delivery = row.get("delivery")
        hashes = delivery.get("byte_hashes") if isinstance(delivery, dict) else None
        yield {"seat": seat, "work": work, "byte_hashes": hashes if isinstance(hashes, dict) else {}}


def collect(root, out):
    root = Path(root).resolve()
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError(f"choose a new evidence directory: {out}")
    tasks = sorted(root.glob("*/*/members/TASK.md"))
    if not tasks:
        return 0
    count = 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as temporary:
        snapshot = Path(temporary) / "capture"
        snapshot.mkdir()
        for path in tasks:
            home = path.parent
            if home.resolve() != home:
                continue
            with regular(path) as file:
                task = file.read().decode()
            result = capture(task, recorded_members(home), snapshot / home.parent.relative_to(root))
            if result is not None:
                count += 1
        if count:
            snapshot.rename(out)
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(f"Captured ungraded worker evidence for {collect(args.root, args.out)} tasks.")
