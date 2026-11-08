"""Does the cut base (layers removed) still make good cells, and how much faster is it?

    python training/cells_cut_eval.py route_step next_move claim_support orders_spend
Same edit type on both bases (rank 2 on every module), same data, same steps; speed measured in llama.cpp.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import skills as S  # noqa: E402
from training import cells as C  # noqa: E402


def speed(base_gguf, tok_dir, skill, xs):
    from llama_cpp import Llama
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(tok_dir)
    llm = Llama(model_path=str(base_gguf), n_ctx=1024, n_threads=4, n_batch=512, verbose=False)
    t0 = time.time()
    for x in xs:
        msgs = [{"role": "system", "content": S.SKILLS[skill]["instr"]}, {"role": "user", "content": x}]
        llm.reset()
        llm.create_completion(tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True), max_tokens=3,
                              temperature=0.0)
    llm.close()
    return (time.time() - t0) / len(xs) * 1000


if __name__ == "__main__":
    cfg = json.loads((C.CELLS / "bases" / "smol135-cut22" / "config.json").read_text())
    rows = []
    for skill in sys.argv[1:]:
        full = json.loads((C.CELLS / "variants" / skill / "all_r2" / "result.json").read_text())
        n = cfg["num_hidden_layers"]
        every = [f"{i}:{m}" for i in range(n) for m in C.MODS]
        steps = full["steps"]
        cut = C.train(skill, "cut22", every, rank=2, steps=steps, tag="cut22_all_r2", save=False)
        _, _, te = C.data(skill)
        xs = [x for x, _ in te[:40]]
        rows.append({"skill": skill, "full": full["test"], "cut": cut["test"],
                     "ms_full": speed(C.CELLS / "gguf" / "smol135.gguf", C.BASES["smol135"], skill, xs),
                     "ms_cut": speed(C.CELLS / "gguf" / "cut22.gguf", C.BASES["cut22"], skill, xs),
                     "params_full": full["trainable_params"], "params_cut": cut["trainable_params"]})
        print(rows[-1], flush=True)
    d_full = sum(r["full"] for r in rows) / len(rows)
    d_cut = sum(r["cut"] for r in rows) / len(rows)
    sp = sum(r["ms_full"] for r in rows) / sum(r["ms_cut"] for r in rows)
    verdict = (f"Average test {d_full:.3f} (30 layers) vs {d_cut:.3f} (22 layers); the cut base is {sp:.2f}x faster per "
               f"call. " + ("The cut base keeps the skills: cells can use it." if d_cut >= d_full - 0.01 else
                            "The cut base loses accuracy: cells stay on the full base."))
    gguf_mb = (C.CELLS / "gguf" / "cut22.gguf").stat().st_size / 1e6
    out = {"layers": n, "dropped": [25, 26, 7, 9, 22, 5, 4, 21], "params_m": 0, "gguf_mb": gguf_mb, "rows": rows,
           "verdict": verdict, "speedup": sp}
    from transformers import AutoModelForCausalLM
    out["params_m"] = sum(p.numel() for p in AutoModelForCausalLM.from_pretrained(C.BASES["cut22"]).parameters()) / 1e6
    (C.REPORTS / "cut22.json").write_text(json.dumps(out, indent=1))
    print(verdict)
