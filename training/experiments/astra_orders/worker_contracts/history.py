"""Count which genuine G55 after-body prompts can exercise the public checks, before reading grades."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from training import exam
from team.deliverables import wanted
from team.public_examples import module_examples, required_gets
from training.experiments.astra_orders.generate import save


def summarize(folder):
    manifest = json.loads((folder / "index.json").read_bytes())
    expected = {r["name"]: r["digest"].removeprefix("sha256:") for r in manifest["archives"]}
    digest = {}
    rows = []
    for ix in range(1, 9):
        filename = f"gate-after-{ix}"
        archive = folder / (filename + ".zip")
        digest[filename] = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest[filename] != expected[filename]:
            raise ValueError(str(archive))
        with ZipFile(archive) as z:
            data = json.loads(z.read(z.namelist()[0]))
        for row in data["tasks"]:
            task = row["task"]
            eligible = bool(module_examples(task, wanted(task)) or required_gets(task))
            rows.append((row["id"], eligible, row["ok"]))
    if len({r[0] for r in rows}) != len(rows):
        raise ValueError("duplicate job IDs")
    fixed = exam.held_exam()
    fixed_scope = {"requests": len(fixed),
                   "explicit_examples_or_urls": sum(bool(module_examples(task, wanted(task)) or required_gets(task))
                                                    for _, _, _, task, _ in fixed)}
    return {"empty_memory_fixed_exam": fixed_scope, "public_workflow_run": manifest["run"], "digests": digest,
            "counts": {status: dict(Counter("eligible" if e else "inapplicable"
                                             for _, e, ok in rows if ok == expected_ok))
                       for status, expected_ok in (("passed", True), ("failed", False))}}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archives", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    save(args.out, summarize(args.archives))
