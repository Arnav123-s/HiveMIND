"""How often does the birth gate keep a newborn that adds nothing? The old gate and the new one, on the same newborns.

    HIVE_BODY=<name> python training/experiments/gate_aa.py [out.json]      (HIVE_BODY unset: the first body)

A newborn that adds nothing is made for every living cell of the body: an exact copy of that cell, set down on the
same territory. It knows nothing the body does not know already, and among the cells awake it takes the place of
the fourth nearest, so what it is truly worth is nothing or a little less. Whatever gain it shows is luck, or the
say of a member counted twice.

Each copy is judged twice, as body.turn judges a newborn:
- the gate as it was until 2026-11-12: its gain over the 60 nearest gate passages must exceed 0.004;
- the gate as it is now (body.judge_local): over the passages it wakes on among the body.NEARBY nearest, its gain
  must exceed body.LOCAL and body.SURE standard errors.
The same is done on report passages, which decide nothing in the hive: a second, independent set of the same kind.
Nothing of the hive is changed: the copies live in this process only.
"""
import json
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from training import body as B  # noqa: E402
from training import scratch as T  # noqa: E402


class WithCopy(B.Body):
    """The body with one more cell: a copy of cell `of`, on the same territory."""

    def __init__(self, of):
        super().__init__()
        self.of, self.new = of, self.terr["centre"].shape[0]
        self.terr = dict(self.terr, centre=torch.cat([self.terr["centre"], self.terr["centre"][of][None]]))
        self.alive = self.alive + [self.new]

    def cell(self, k):
        return super().cell(self.of if k == self.new else k)


def main(argv):
    data = B._data()
    alive = B.Body().alive
    rows = []
    for part in ("gate", "report"):
        pool = B._held(data, part, 10 ** 9)
        for of in alive:
            b = WithCopy(of)
            near = b.near(data, pool)[:, b.new]
            order = near.topk(min(B.NEARBY, len(pool))).indices.tolist()
            local = [pool[i] for i in order]
            f1, s1, _ = b.read(data, local, without=(b.new,))
            f2, s2, w2 = b.read(data, local)
            before, after, wakes = B.fit_loss(f1, s1), B.fit_loss(f2, s2), (w2 == b.new).any(1)
            old_gain = (before[:60] - after[:60]).mean().item()  # the 60 nearest come first in the order of nearness
            new_kept, why = B.judge_local(before[wakes], after[wakes], wakes.float().mean().item())
            rows.append({"copy_of": of, "on": part, "old_gate_gain": round(old_gain, 4), "old_gate_keeps": old_gain > 0.004 and bool(wakes[:60].any()),
                         "new_gate_keeps": new_kept, "new_gate_says": why})
    res = {"body": T.BODY or "first", "copies": len(alive)}
    for part in ("gate", "report"):
        got = [r for r in rows if r["on"] == part]
        res[part] = {"old_gate_kept": sum(r["old_gate_keeps"] for r in got), "new_gate_kept": sum(r["new_gate_keeps"] for r in got), "of": len(got),
                     "mean_gain_of_a_copy": round(sum(r["old_gate_gain"] for r in got) / len(got), 4)}
    res["each"] = rows
    print(json.dumps({k: v for k, v in res.items() if k != "each"}, indent=1))
    for r in rows:
        print(r)
    if argv:
        Path(argv[0]).write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
