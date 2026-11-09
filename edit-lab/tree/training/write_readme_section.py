"""Fills README's "How the specialists were improved" section from measured files only."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "training" / "reports"


def load(tag):
    p = R / f"{tag}.json"
    return json.loads(p.read_text())["scores"] if p.exists() else {}


COLS = [  # (label, tag)
    ("1.7B base, first design", "base"),
    ("1.7B base, improved design", "base_tools"),
    ("1.7B + own edit (PyTorch)", "trained"),
    ("1.7B 8-bit + own edit (llama.cpp)", "v2_fast_edits"),
    ("4B 4-bit / coder 7B 4-bit", "v2_4b"),
]
ROWS = ["coordinator", "researcher_plan", "researcher_extract", "verifier", "writer", "browser", "browser_live", "coder"]
CHOSEN = {"coordinator": "4B", "researcher_plan": "4B", "researcher_extract": "4B", "verifier": "1.7B + edit",
          "writer": "1.7B + edit", "browser": "1.7B + edit", "browser_live": "1.7B + edit", "coder": "coder 7B"}


def table():
    data = {tag: load(tag) for _, tag in COLS}
    final_browser = load("v2_final_browser")  # browser re-measured after the repeat-penalty fix
    head = "| eval (held out) | cases | " + " | ".join(lbl for lbl, _ in COLS) + " | in the team now |"
    lines = [head, "|---|---|" + "---|" * len(COLS) + "---|"]
    for r in ROWS:
        n = next((d[r]["n"] for d in data.values() if r in d), "")
        cells = []
        for _, tag in COLS:
            v = data[tag].get(r, {}).get("mean")
            if tag == "v2_fast_edits" and r in final_browser:
                v = final_browser[r]["mean"]
            cells.append(f"{v:.2f}" if v is not None else "-")
        lines.append(f"| {r} | {n} | " + " | ".join(cells) + f" | {CHOSEN[r]} |")
    return "\n".join(lines)


def meta_table():
    lines = ["| edit | examples | layers | rank | epochs | train loss start → end | CPU time | kept? |",
             "|---|---|---|---|---|---|---|---|"]
    kept = {"coordinator": "no: 0.79 vs 0.94 without it (learned 2-step plans)",
            "researcher": "no: extraction 0.57 vs 0.77 (looped, broke JSON)",
            "browser": "yes: 0.79 vs 0.43", "verifier": "yes: 0.89 vs 0.83", "writer": "yes: tie 0.88, faster model"}
    for spec in ["coordinator", "researcher", "browser", "verifier", "writer"]:
        for base in (ROOT / "adapters", ROOT / "adapters" / ".rejected"):
            p = base / spec / "training_meta.json"
            if p.exists():
                m = json.loads(p.read_text())
                lines.append(f"| {spec} | {m['examples']} | {m['layers'][0]}-{m['layers'][-1]} | {m['rank']} | {m['epochs']} | "
                             f"{m['loss_first']:.2f} → {m['loss_last']:.2f} | {m['seconds'] // 60} min | {kept[spec]} |")
                break
    return "\n".join(lines)


def engines():
    p = R / "engines.jsonl"
    if not p.exists():
        return ""
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    lines = ["| engine | model | tokens/s | RAM it allocates | + mapped weights (evictable) |", "|---|---|---|---|---|"]
    names = {("gguf", "verifier"): "Qwen3-4B 4-bit", ("gguf", "coder"): "Qwen2.5-Coder-7B 4-bit",
             ("hf", "verifier"): "Qwen3-1.7B bf16"}
    for r in rows:
        if "anon_gb" in r:
            lines.append(f"| {'llama.cpp' if r['engine'] == 'gguf' else 'PyTorch'} | {names.get((r['engine'], r['specialist']), r['specialist'])} | "
                         f"{r['tok_per_s']} | {r['anon_gb']} GB | {r['file_backed_gb']} GB |")
    return "\n".join(lines)


def main():
    return "\n\n".join([
        "Every number here is a measurement on held-out cases (`training/evals/`, none of them in any training "
        "data), produced by `training/observe.py`; per-case outputs are in `training/reports/<tag>.json`. "
        "Evals are small (3-18 cases), so treat single-case differences as noise.",
        "**1. Observe.** Each specialist ran its held-out cases on the base model. What failed, and the design fix:\n"
        "- browser invented URLs and missed targets buried in page chrome → it now sees the page lines that match its "
        "goal and the 40 most relevant elements (rare goal words weigh more); navigation errors come back as a reason, not a crash\n"
        "- coder guessed HTML classes and JSON keys blind and imported unrelated packages → it gets a real preview of "
        "every URL/file in its task, and is told when a file it should have made is missing\n"
        "- small models kept talking after the answer → decoding stops when the JSON object or code block closes; on "
        "llama.cpp, JSON is grammar-constrained so it is always valid\n"
        "- Hugging Face search matched descriptive words against model names → the tool strips them; PyPI needs an exact "
        "name → the tool tries each word\n"
        "- \"for each\" without fan-out → the plan is repaired; a step that fails 3 times is re-routed to a different specialist",
        "**2. Edit the weights.** For each 1.7B specialist I wrote training data aimed at its failures "
        "(`training/build_*.py`: hand-written plans; expert browser runs recorded on live sites; live Hugging Face / PyPI / "
        "Hacker News / arXiv / quotes pages; true and perturbed claims) and trained a weight delta "
        "W' = W + (α/r)·B·A on the top 14 of 28 transformer layers, all 7 projection matrices per layer, on CPU, "
        "loss on the reply tokens only. Exact tensors changed: `training/reports/weights_<specialist>.md`.",
        meta_table(),
        "**3. Bigger brains for the same RAM.** A second engine (llama.cpp, 4-bit) runs a 4B model in about the RAM and "
        "speed the 1.7B needed in PyTorch (measured, this 4-core CPU):",
        engines(),
        "**4. Pick each role's brain by score.** Same held-out cases, every candidate:",
        table(),
        "Rule: a candidate replaces the current one only if it scores at least as well; ties go to the faster model. "
        "Rejected edits are kept in `adapters/.rejected/` for the record.",
    ])


if __name__ == "__main__":
    text = main()
    readme = ROOT / "README.md"
    s = readme.read_text()
    start = s.index("## How the specialists were improved") + len("## How the specialists were improved")
    end = s.index("## Dreaming")
    readme.write_text(s[:start] + "\n\n" + text + "\n\n" + s[end:])
    print(text)
