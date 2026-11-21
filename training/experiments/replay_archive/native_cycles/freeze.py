"""Freeze actual archived training rows and verify each replay actor's numbered program."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from zipfile import ZipFile

from team import solo
from team.tools.sandbox import give, note
from training import exam, grow, kinds, self_replay

HERE = Path(__file__).resolve().parent
FAMILIES = ("h_txt_names", "h_txt_mdcsv", "h_tab_fill")
OLD = ("m_percent", "m_weekday")
REPLAY = ((10005502, 14626582627, "2f6f73f14cc527adcb74af4acbdecbdd5f5205be2c7789bc76159e1505e42b6b"),
          (10005503, 14626203707, "9178bfb877caa461ad41994ed8d4c853debb98a397d4faa29551dd43683e585a"),
          (10005509, 14626639676, "e6f9e2dd94fd919125061cf7c971741e2d837b3cd1360ba4b565f45743937041"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def row_id(row):
    return digest(json.dumps(row, sort_keys=True).encode())


def freeze(archives, proofs):
    previous, current = ([json.loads(l) for l in (archives / f"g{n}-rows.jsonl").read_text().splitlines()] for n in (55, 56))
    body = json.loads((HERE.parents[3] / "cells/body.json").read_text())
    assert body["generation"] == 55 and body["trunk"] == "g55trunk"
    norm = self_replay.question
    prior = {norm(r["task"]) for r in previous}
    seen = {norm(r["task"]) for r in current}
    held = {norm(t) for tasks in grow.kept_back(current).values() for t in tasks}
    fresh = [r for r in current if r.get("gen") == "g56"]
    eligible = self_replay.select(previous, body, "t80", "g56", held | {norm(r["task"]) for r in fresh})
    stages, inputs, details = [], [], []
    for family, (seed, artifact, sha) in zip(FAMILIES, REPLAY):
        candidates = [r for r in fresh if r.get("type") == "first" and r.get("who") == "lesson" and r.get("lesson") == family
                      and norm(r["task"]) not in prior | held]
        chosen = sorted(candidates, key=row_id)[:2]
        assert len({norm(r["task"]) for r in chosen}) == 2
        rows = [previous[i] for i in eligible if previous[i].get("seed") == seed and previous[i].get("gen") == "g55"
                and previous[i]["type"] == "first"]
        assert len(rows) == 1
        row = rows[0]
        path = proofs / f"g55-retention-work-{seed % 100}.zip"
        assert digest(path.read_bytes()) == sha
        with ZipFile(path) as z:
            prompts = [p for p in z.namelist() if p.endswith("/members/TASK.md") and z.read(p).decode().strip() == row["task"].strip()]
            assert len(prompts) == 1
            base = prompts[0].removesuffix("members/TASK.md")
            grades = json.loads(z.read(base + "exam.json"))["members"]
            member = row["member"]
            assert [x for x in grades if x["member"] == member] == [{"who": row["who"], "ok": True, "member": member}]
            program = z.read(base + f"members/member{member}/member{member}_1.py").decode().strip()
            assert row["output"].strip() == f"```python\n{program}\n```"
        stages.append(dict(family=family, fresh=[row_id(r) for r in chosen], replay=row_id(row)))
        details.append(dict(artifact=artifact, sha256=sha, task_grade=base + "exam.json", actor=row["who"],
                            member=member, seed=seed, source_sha256=digest(program.encode()), ok=True))
        inputs.append(chosen + [row])
    panel = []
    for family in (*OLD, *FAMILIES):
        assert family not in kinds.HELD_OUT
        seed = f"post-astra/native-retention/v1/{family}"
        _, _, task, _ = exam.remake(family, seed, 0)
        assert norm(task) not in seen | prior
        with tempfile.TemporaryDirectory() as tmp:
            files = give(task, Path(tmp), skip=solo.wanted(task))
            user = "TASK: " + task + note(files)
        panel.append(dict(name=family, seed=seed, task=task, messages=[
            {"role": "system", "content": solo.SHORT.format(today="2026-11-21 (Saturday)")}, {"role": "user", "content": user}]))
    return inputs, dict(rows=panel), dict(stages=stages, proof=details, sources={
        f"g{n}": digest((archives / f"g{n}-rows.jsonl").read_bytes()) for n in (55, 56)})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("archives", "proofs", "scratch"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    rows, panel, manifest = freeze(args.archives, args.proofs)
    args.scratch.mkdir(exist_ok=True, parents=True)
    for i, stage in enumerate(rows, 1):
        (args.scratch / f"rows-{i}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in stage))
    for name, obj in (("panel", panel), ("manifest", manifest)):
        (HERE / (name + ".json")).write_text(json.dumps(obj, indent=2) + "\n")
