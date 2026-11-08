"""Direct internal edit: find where in the network a specialist's mistakes live, and push it the right way there.

1. Steer set: fresh expert-labelled browser situations (new books, tags, models, articles; none in training
   or held-out evals), recorded on live sites.
2. Observe: run the specialist exactly as deployed (llama.cpp, 1.7B 8-bit + its weight edit) on the steer set
   and keep its real mistakes.
3. Locate: for each mistake, run the PyTorch twin on (situation + correct action) and (situation + its wrong
   action), read the hidden state of every layer over the reply tokens, and take the mean difference:
   one direction per layer that separates right from wrong.
4. Find the right layer and strength by experiment: add alpha * direction to the residual stream of one layer
   at a time (llama.cpp control vector) and score each choice on the dev half of the steer set.
5. Keep the best only if it beats no edit on dev; then it must also hold on the held-out evals (observe.py).

    python training/steer.py browser
"""
import json
import os
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "training"))
SPEC = sys.argv[1] if len(sys.argv) > 1 else "browser"
OUT = ROOT / "adapters_gguf" / f"{SPEC}.cvec.json"
REPORT = ROOT / "training" / "reports" / f"steer_{SPEC}.json"
STEER = ROOT / "training" / "data" / f"steer_{SPEC}.jsonl"
random.seed(1)


# ------------------------------------------------------------------ 1. steer set
def build_steer_set():
    if STEER.exists():
        return [json.loads(x) for x in STEER.read_text().splitlines() if x.strip()]
    import build_browser as bb
    r = bb.Recorder()
    price = lambda t: bb.ev_lines(t, r"^£\d+\.\d\d$", 2)  # noqa: E731
    page2 = ["Shakespeare's Sonnets", "Rip it Up", "Scott Pilgrim", "Starving Hearts", "Set Me Free"]
    for book in ["In Her Wake", "How Music Works", "Foolproof Preserving", "Chase Me", "Black Dust", "Birdsong",
                 "America's Cradle of Quarterbacks", "Aladdin and His Wonderful Lamp", "Worlds Elsewhere"]:
        r.episode(f"What does the book '{book}' cost?", "https://books.toscrape.com/catalogue/page-2.html",
                  [bb.click(re.escape(book[:12]), r"/"), bb.done(lambda t, ev, b=book: f"'{b}' costs {ev.split(chr(10))[0]}", price)])
    for cat in ["Philosophy", "Business", "Sequential Art", "Science Fiction", "Self Help", "Music"]:
        r.episode(f"How many books are in the {cat} category on books.toscrape.com?", "https://books.toscrape.com/",
                  [bb.click(f"^{re.escape(cat)}$"),
                   bb.done(lambda t, ev: f"{ev.split(' results')[0]} results", lambda t: bb.ev_around(t, r"\d+ results?\b", 0, 25))])
    for tag in ["simile", "friends", "miracles", "obvious"]:
        r.episode(f"Show me the first quote with the tag '{tag}'", "https://quotes.toscrape.com/",
                  [bb.click(f"^{re.escape(tag)}$", r"/tag/"),
                   bb.done(lambda t, ev: ev.replace("\n", " "), lambda t: bb.ev_lines(t, r"^“", 3))])
    for m in ["Qwen/Qwen2.5-Math-1.5B-Instruct", "Qwen/Qwen2.5-Coder-0.5B-Instruct", "HuggingFaceTB/SmolLM2-135M-Instruct",
              "Qwen/Qwen3-4B-Instruct-2507"]:
        r.episode(f"What license does {m} use?", f"https://huggingface.co/{m}",
                  [bb.done(lambda t, ev: ev.replace("\n", " "), lambda t: bb.ev_lines(t, r"^License:", 2))])
        r.episode(f"How big are the safetensors weight files of {m}?", f"https://huggingface.co/{m}",
                  [bb.click(r"^Files and versions"),
                   bb.done(lambda t, ev: ev.replace("\n", " "), lambda t: bb.ev_lines(t, r"\.safetensors$", 3))])
    for q, art, pat in [("When did the C programming language first appear?", "C_(programming_language)", r"1972"),
                        ("When was Java first released?", "Java_(programming_language)", r"1995"),
                        ("When was SQLite first released?", "SQLite", r"2000")]:
        r.episode(q, f"https://en.wikipedia.org/wiki/{art}", [bb.done(lambda t, ev: ev, lambda t, p=pat: bb.ev_around(t, p))])
    for goal, start, reason in [("Create a free account on quotes.toscrape.com", "https://quotes.toscrape.com/",
                                 "Creating accounts is against Arnav's rules (no sign-ups)."),
                                ("Buy 'In Her Wake' for me", "https://books.toscrape.com/catalogue/page-2.html",
                                 "Spending money needs Arnav's approval first.")]:
        r.episode(goal, start, [bb.fail(reason)])
    r.b.close()
    STEER.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in r.rows) + "\n")
    return r.rows


# ------------------------------------------------------------------ scoring one action
def correct(pred, gold, page_text=""):
    if not isinstance(pred, dict):
        return False
    a, g = pred.get("action"), gold.get("action")
    if a != g:
        return False
    if g == "click":
        return str(pred.get("id")) == str(gold.get("id"))
    if g == "goto":
        host = re.sub(r"^https?://([^/]+).*", r"\1", gold.get("url", ""))
        return host in str(pred.get("url", ""))
    if g == "done":
        from team.specialists.verifier import norm
        ev = norm(pred.get("evidence", ""))
        return bool(ev) and (ev in norm(gold["messages_text"]) if "messages_text" in gold else True) and \
            any(x in ev for x in re.findall(r"[\d£.,]+|[a-z]{4,}", norm(gold.get("evidence", "")))[:3])
    return True  # fail / type / scroll


def run_deployed(rows, cvec=None):
    """Score the specialist as deployed (llama.cpp) on rows; cvec = (layer, alpha) override."""
    from team import llm
    if cvec:
        os.environ[f"AGENT_TEAM_CVEC_{SPEC.upper()}"] = json.dumps(cvec)
    else:
        os.environ.pop(f"AGENT_TEAM_CVEC_{SPEC.upper()}", None)
    llm.reset_edits()
    outs, ok = [], 0
    for r in rows:
        gold = json.loads(r["output"])
        gold["messages_text"] = r["messages"][-1]["content"]
        pred, raw = llm.chat_json(SPEC, r["messages"], max_new_tokens=160)
        good = correct(pred, gold)
        ok += good
        outs.append({"pred": raw, "good": good})
    return ok / max(1, len(rows)), outs


# ------------------------------------------------------------------ 3. locate: directions per layer
def directions(pairs):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-1.7B")
    model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-1.7B", dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(model, str(ROOT / "adapters" / SPEC)).eval()
    n_layers = model.config.num_hidden_layers
    diffs = torch.zeros(n_layers, model.config.hidden_size)
    norms = torch.zeros(n_layers)

    def acts(messages, reply):
        prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        p = tok(prompt, add_special_tokens=False)["input_ids"]
        t = tok(reply, add_special_tokens=False)["input_ids"]
        with torch.inference_mode():
            hs = model(input_ids=torch.tensor([p + t]), output_hidden_states=True).hidden_states
        # hidden_states[L + 1] is the output of layer L; average over the reply tokens
        return torch.stack([hs[L + 1][0, len(p):].float().mean(0) for L in range(n_layers)])

    for messages, good, bad in pairs:
        a_good, a_bad = acts(messages, good), acts(messages, bad)
        diffs += a_good - a_bad
        norms += a_good.norm(dim=-1)
    diffs /= max(1, len(pairs))
    norms /= max(1, len(pairs))
    return diffs, norms


def main():
    from team import llm  # noqa: F401  (engine must be llama.cpp)
    rows = build_steer_set()
    random.shuffle(rows)
    half = len(rows) // 2
    build, dev = rows[:half], rows[half:]
    print(f"steer set {len(rows)}: build {len(build)}, dev {len(dev)}", flush=True)
    # 2. observe deployed mistakes on the build half
    acc_build, outs = run_deployed(build)
    pairs = [(r["messages"], r["output"], o["pred"]) for r, o in zip(build, outs) if not o["good"] and o["pred"].strip()]
    print(f"deployed accuracy on build half {acc_build:.2f}; {len(pairs)} real mistakes", flush=True)
    base_dev, _ = run_deployed(dev)
    print(f"deployed accuracy on dev half (no edit) {base_dev:.2f}", flush=True)
    report = {"specialist": SPEC, "steer_set": len(rows), "build_acc": acc_build, "mistakes": len(pairs),
              "dev_no_edit": base_dev, "sweep": []}
    if len(pairs) < 3:
        report["decision"] = "too few mistakes to locate a direction"
        REPORT.write_text(json.dumps(report, indent=1))
        print(report["decision"])
        return
    llm.unload_all()  # free RAM for the PyTorch twin
    diffs, norms = directions(pairs)
    rel = (diffs.norm(dim=-1) / norms).tolist()
    report["direction_strength_by_layer"] = [round(x, 4) for x in rel]
    # 4. find the right place: the layers where right and wrong separate most, then sweep strength
    cand = sorted(range(len(rel)), key=lambda L: -rel[L])[:4]
    best = (base_dev, None)
    for L in sorted(cand):
        for alpha in (1.0, 2.0, 4.0):
            vec = (diffs[L] * alpha).tolist()
            acc, _ = run_deployed(dev, {"layer": L + 1, "vector": vec})  # llama.cpp layers count from 1
            report["sweep"].append({"layer": L, "alpha": alpha, "dev_acc": round(acc, 3)})
            print(f"layer {L} alpha {alpha}: dev {acc:.2f}", flush=True)
            if acc > best[0]:
                best = (acc, {"layer": L + 1, "hf_layer": L, "alpha": alpha, "vector": vec})
    if best[1]:
        OUT.write_text(json.dumps({**best[1], "dev_acc": best[0], "dev_no_edit": base_dev}))
        report["decision"] = f"kept: layer {best[1]['hf_layer']} alpha {best[1]['alpha']} dev {best[0]:.2f} vs {base_dev:.2f}"
    else:
        report["decision"] = "no layer/strength beat the unedited specialist on dev; nothing kept"
    REPORT.write_text(json.dumps(report, indent=1))
    print(report["decision"], flush=True)


if __name__ == "__main__":
    os.environ.setdefault("AGENT_TEAM_ENGINE", "gguf")
    main()
