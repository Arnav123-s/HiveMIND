"""Retrain order cells with questions in their data, and keep the new one only if it is better.

    python training/cells_questions.py orders_delete [orders_spend ...]
Same recipe as each cell's winner (cells/adapters/<skill>/result.json: modules, rank, steps), with a quarter of the
training examples being questions ("How do I delete X?" = no order, "Can you delete X?" = an order). Old and new are
scored on the unchanged test set and on held-out questions (other words and frames). The new one is promoted only if
it is at least as good on the test set and better on the questions. Report: training/reports/cells/questions.json.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from training import cells as C  # noqa: E402
from team.cells import skills as S  # noqa: E402


def q_rows(kind):
    return [(t, "yes" if kind in k else "no") for t, k in S._orders_q_rows("test")]


def score(skill, model, tok):
    kind = skill.split("_", 1)[1]
    _, _, te = C.data(skill)
    return {"test": C.accuracy(model, tok, skill, te)[0], "questions": C.accuracy(model, tok, skill, q_rows(kind))[0]}


def old_scores(skill, base):
    from peft import PeftModel
    tok, model = C.load(base)
    model = PeftModel.from_pretrained(model, str(C.CELLS / "adapters" / skill)).eval()
    return score(skill, model, tok)


if __name__ == "__main__":
    out_file = C.REPORTS / "questions.json"
    report = json.loads(out_file.read_text()) if out_file.exists() else {}
    for skill in sys.argv[1:]:
        kind = skill.split("_", 1)[1]
        win = json.loads((C.CELLS / "adapters" / skill / "result.json").read_text())
        old = old_scores(skill, win["base"])
        S.SKILLS[skill]["gen"] = S._orders_gen_q(kind)
        C._DATA.pop(skill, None)
        res = C.train(skill, win["base"], win["modules"], rank=win["rank"], alpha=win["alpha"], steps=win["steps"],
                      lr=win["lr"], thin=win.get("thin"), tag=f"{win['tag']}_questions")
        from peft import PeftModel
        tok, model = C.load(win["base"])
        vdir = C.CELLS / "variants" / skill / res["tag"]
        model = PeftModel.from_pretrained(model, str(vdir)).eval()
        new = score(skill, model, tok)
        better = new["test"] >= old["test"] and new["questions"] > old["questions"]
        report[skill] = {"old": old, "new": new, "promoted": better, "recipe": res["tag"],
                         "rule": "new test >= old test and new questions > old questions"}
        print(f"{skill}: old {old} new {new} -> {'PROMOTED' if better else 'kept the old one'}", flush=True)
        if better:  # same recipe, so the registry keeps its modules and rank; llama.cpp file and timing are redone
            import time
            from team.cells import runtime
            from training.cells_promote import retime, to_gguf
            dst = C.CELLS / "adapters" / skill
            for f in ("adapter_model.safetensors", "adapter_config.json"):
                shutil.copy(vdir / f, dst / f)
            (dst / "result.json").write_text(json.dumps(dict(res, questions=new["questions"]), indent=1))
            to_gguf(dst, skill, win["base"])
            runtime.update_registry(skill, {"variant": res["tag"], "dev": res["dev"], "test_torch": res["test"],
                                            "questions_torch": new["questions"],
                                            "promoted": time.strftime("%Y-%m-%d %H:%M")})
            retime(skill)
        out_file.write_text(json.dumps(report, indent=1))
