"""A child grown on several runners at once: each on its own slice of the rows, the slices' edits averaged into it."""
import json
from pathlib import Path

import numpy as np
import pytest

from training import grow, merge

ROOT = Path(__file__).resolve().parents[1]


def _rows(n):
    return [{"messages": [{"role": "system", "content": "s"}, {"role": "user", "content": f"TASK {i}"}], "output": f"print({i})"} for i in range(n)]


def test_every_row_is_in_exactly_one_slice_whatever_the_order():
    rows = _rows(300)
    parts = [grow.slice_rows(rows, k, 3) for k in range(3)]
    assert sum(len(p) for p in parts) == 300 and all(60 < len(p) < 140 for p in parts)
    seen = [r["output"] for p in parts for r in p]
    assert sorted(seen) == sorted(r["output"] for r in rows)  # none twice, none left out
    assert grow.slice_rows(list(reversed(rows)), 1, 3) == list(reversed(parts[1]))  # the same rows, in any order
    with pytest.raises(ValueError):
        grow.slice_rows(rows, 3, 3)


def test_the_slices_edits_are_averaged_into_one_child_of_the_childs_rank(tmp_path):
    rng = np.random.default_rng(0)
    start = {f"model.layers.{i}.self_attn.q_proj": (rng.normal(size=(4, 32)).astype(np.float32), rng.normal(size=(24, 4)).astype(np.float32)) for i in (5, 6)}
    files = []
    for k in range(3):  # each slice: the same start, moved a little its own way
        e = {m: (a + 0.01 * rng.normal(size=a.shape).astype(np.float32), b + 0.01 * rng.normal(size=b.shape).astype(np.float32)) for m, (a, b) in start.items()}
        f = tmp_path / f"s{k}" / "t80.g29code.safetensors"
        f.parent.mkdir()
        merge.save(e, f)
        f.with_suffix(".json").write_text(json.dumps({"steps": 10 + k, "used": 100, "rows": 300, "read": 40, "seconds": 900 + k, "leans": "code"}))
        files.append(e)
    joined, kept = merge.merge(files, None, 4)
    for m in start:  # the average of the products, cut to rank 4: close to each slice's (they share their start)
        want = sum(b @ a for a, b in (e[m] for e in files)) / 3
        got = joined[m][1] @ joined[m][0]
        assert np.abs(got - want).max() < 0.05 * np.abs(want).max()
    import subprocess
    import sys
    out = subprocess.run([sys.executable, "training/merge.py", "join", str(tmp_path / "work")] + [str(tmp_path / f"s{k}" / "t80.g29code.safetensors") for k in range(3)] + ["--rank", "4"],
                         cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    said = json.loads(out.stdout.strip().splitlines()[-1])
    assert said["slices"] == 3 and said["steps"] == 33 and said["used"] == 300  # the slices' work added up
    cfg = json.loads((tmp_path / "work" / "adapter_config.json").read_text())
    assert cfg["r"] == 4 and cfg["lora_alpha"] == 8 and (tmp_path / "work" / "adapter_model.safetensors").exists()


def test_the_workflow_grows_each_child_on_its_slices_and_joins_them_before_the_trunk():
    import yaml
    flow = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())
    jobs = flow["jobs"]
    assert "slice" in jobs["train"]["strategy"]["matrix"]  # {child, shard, n}: each child its own number of slices
    up = next(s for s in jobs["train"]["steps"] if s.get("uses", "").startswith("actions/upload-artifact"))
    assert up["with"]["name"].startswith("part-") and up["with"]["if-no-files-found"] == "ignore"
    assert jobs["join"]["needs"] == ["plan", "train"]
    joined = next(s for s in jobs["join"]["steps"] if s.get("uses", "").startswith("actions/upload-artifact"))
    assert joined["with"]["name"] == "${{ matrix.variant }}-${{ matrix.child.suffix }}"  # the name merge, gate and record read
    for later in ("merge", "gate", "record"):
        assert "join" in jobs[later]["needs"]
    text = (ROOT / ".github" / "workflows" / "grow.yml").read_text()
    assert "vars.HIVE_SHARDS || '3'" in text and 'SLICE="--shard $SHARD/$N"' in text


def test_a_row_too_long_loses_the_middle_of_an_earlier_program_never_its_answer():
    program = "```python\n" + "\n".join(f"x{i} = {i}" for i in range(100)) + "\nprint(x99)\n```"
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "TASK: t"}, {"role": "assistant", "content": program},
            {"role": "user", "content": "ERROR: NameError"}]
    short = grow.shorten(msgs, 0.3)
    text = short[2]["content"]
    assert text.startswith("```python\nx0 = 0") and "print(x99)" in text and "lines of this program left out" in text
    assert text.count("\n") < 40 and short[3] == msgs[3] and msgs[2]["content"] == program  # the original is left as it was
    assert grow.shorten(msgs[:2], 0.3) is not None and grow.shorten(msgs[:2], 0.3) == msgs[:2]  # no earlier program: nothing cut


def test_what_is_new_this_generation_is_in_every_slice_and_old_rows_in_one():
    src = (ROOT / "training" / "grow.py").read_text()
    # the rule as train() applies it: new rows (this generation's, and mended mistakes) to every slice, the rest shared out
    rows = _rows(90)
    for r in rows[:9]:
        r["gen"] = "g40"
    rows[9]["type"] = "mend"
    new = lambda r: r.get("gen") == "g40" or r.get("type") == "mend"  # noqa: E731
    parts = [[r for r in rows if new(r)] + grow.slice_rows([r for r in rows if not new(r)], k, 3) for k in range(3)]
    assert all(sum(new(r) for r in p) == 10 for p in parts)                      # every slice studies all that is new
    assert sum(sum(not new(r) for r in p) for p in parts) == 80                  # an old row is in one slice only
    assert 'fresh_rows + slice_rows([r for r in rows if not ((gen and r.get("gen") == gen) or r.get("type") == "mend")], k, n)' in src


def test_a_16_bit_slice_keeps_a_gigabyte_more_spare_than_before():
    """g38 lost 7 of 24 slices to memory; the 16-bit slices that lived stood at 14.6-14.7 of 15.6 GB."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "training" / "grow.py").read_text()
    assert "spare = 2.5 + (1.0 if half else 0.0)" in src and "ternary_base.held_gb() - spare)" in src
    # the 8B: 14 trained layers, hidden size 4096, 46 values a piece; a 16-bit runner of 15.6 GB, 8.1 GB held
    fits = lambda spare, bytes_: int((15.6 - 8.1 - spare) * 2**30 / (14 * 4096 * bytes_ * 46))
    assert fits(2.5, 2) > 950 and 750 < fits(3.5, 2) < 900 and fits(2.5, 4) == fits(2.5 + 0.0, 4)
