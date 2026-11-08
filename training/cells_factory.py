"""Factory: a new skill gets its own cell by cloning the nearest existing cell and editing the clone's weights.

    python training/cells_factory.py <new_skill> [--steps 60]

1. parent finder: every registered cell (and the bare base) answers the new skill's dev inputs; the one that
   already does best is the nearest neuron
2. cloner: a new cell starts as an exact copy of that parent's weight edits, on the parent's modules
3. specialiser: the clone's edits are trained on the new skill only
4. control: the same modules trained from zero for the same steps, to measure what cloning bought
5. gatekeeper: cells_promote picks the winner on dev and registers it; the gate is then retrained with it
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import runtime, skills as S  # noqa: E402
from training import cells as C  # noqa: E402


def find_parent(skill, base="smol135"):
    from peft import PeftModel
    reg = runtime.registry()
    tok, model = C.load(base)
    _, dv, _ = C.data(skill)
    scores = {"base": C.accuracy(model, tok, skill, dv)[0]}
    names = [k for k, v in reg.items() if v["base"] == base and k != skill and k != "gate"]
    if names:
        pm = PeftModel.from_pretrained(model, str(C.CELLS / "adapters" / names[0]), adapter_name=names[0])
        for n in names[1:]:
            pm.load_adapter(str(C.CELLS / "adapters" / n), adapter_name=n)
        pm.eval()
        for n in names:
            pm.set_adapter(n)
            scores[n] = C.accuracy(pm, tok, skill, dv)[0]
    best = max(scores, key=lambda k: (scores[k], k == "base"))
    print(f"{skill}: nearest cells on dev: " + ", ".join(f"{k} {v:.2f}" for k, v in sorted(scores.items(), key=lambda kv: -kv[1])[:6]))
    return best, scores


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("skill")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--base", default="smol135")
    a = ap.parse_args()
    parent, scores = find_parent(a.skill, a.base)
    C.eval_base(a.skill, a.base)
    reg = runtime.registry()
    if parent == "base":  # no cell is closer than the bare base: clone the strongest cell overall instead
        parent = max((k for k in reg if k != "gate"), key=lambda k: scores.get(k, 0))
    keys = reg[parent]["modules"]
    thin = reg[parent].get("thin")
    clone = C.train(a.skill, a.base, keys, rank=reg[parent]["rank"], steps=a.steps, tag=f"clone_{parent}",
                    parent=str(C.CELLS / "adapters" / parent), thin=thin)
    scratch = C.train(a.skill, a.base, keys, rank=reg[parent]["rank"], steps=a.steps, tag="scratch", thin=thin)
    out = {"skill": a.skill, "parent": parent, "parent_scores_dev": scores, "steps": a.steps,
           "clone": {k: clone[k] for k in ("dev", "test", "trainable_params", "copied_tensors")},
           "scratch": {k: scratch[k] for k in ("dev", "test", "trainable_params")}}
    (C.REPORTS / f"factory_{a.skill}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
