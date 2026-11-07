"""Fills README's training section from measured files only (training_meta.json, reports/*.json, weights_*.md)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "training" / "reports"


def score_table(tags, labels):
    reps = {t: json.loads((R / f"{t}.json").read_text()) for t in tags if (R / f"{t}.json").exists()}
    suites = []
    for r in reps.values():
        for s in r["scores"]:
            if s not in suites:
                suites.append(s)
    head = "| eval (held out) | cases | " + " | ".join(labels[t] for t in reps) + " |"
    lines = [head, "|---|---|" + "---|" * len(reps)]
    for s in suites:
        n = next((r["scores"][s]["n"] for r in reps.values() if s in r["scores"]), "")
        cells = [f"{r['scores'][s]['mean']:.2f}" if s in r["scores"] else "-" for r in reps.values()]
        lines.append(f"| {s} | {n} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def meta_table():
    lines = ["| specialist | examples | layers edited | matrices | rank | epochs | loss start → end | CPU time | kept? |",
             "|---|---|---|---|---|---|---|---|---|"]
    kept = json.loads((R / "kept.json").read_text()) if (R / "kept.json").exists() else {}
    for spec in ["coordinator", "researcher", "browser", "verifier", "writer"]:
        for base in (ROOT / "adapters", ROOT / "adapters" / ".rejected"):
            p = base / spec / "training_meta.json"
            if p.exists():
                m = json.loads(p.read_text())
                lines.append(f"| {spec} | {m['examples']} | {m['layers'][0]}-{m['layers'][-1]} | "
                             f"{len(m['modules'])} kinds × {len(m['layers'])} layers | {m['rank']} | {m['epochs']} | "
                             f"{m['loss_first']:.2f} → {m['loss_last']:.2f} | {m['seconds'] // 60} min | "
                             f"{kept.get(spec, '?')} |")
                break
    return "\n".join(lines)


def main(tags, labels):
    return "\n\n".join([
        "**Observe.** Each specialist was run on held-out cases with automatic scoring "
        "(`training/observe.py`, cases in `training/evals/`, none of them in the training data). "
        "Per-case outputs are in `training/reports/<tag>.json`.",
        "**Fix the design where the design was the problem.** What the failures showed, and what changed:\n"
        "- browser invented URLs and missed targets buried in page chrome → it now sees the page lines that "
        "match its goal, and the 40 elements most relevant to the goal (rare goal words weigh more)\n"
        "- coder guessed HTML classes and JSON keys blind, imported unrelated packages → it now gets a real "
        "preview of every URL/file in its task and is told when a file it should have made is missing\n"
        "- small models kept generating after the answer → decoding stops when the JSON object or code block closes\n"
        "- Hugging Face search matched descriptive words against model names → the tool strips them\n"
        "- the coordinator sometimes said \"for each\" without fanning out → the plan is repaired",
        "**Edit the weights.** For each Qwen3 specialist I wrote training data aimed at its failures "
        "(`training/build_*.py`): hand-written plans for the coordinator; expert runs recorded on live sites "
        "for the browser; live Hugging Face / PyPI / Hacker News / arXiv / quotes pages for the researcher; "
        "true and perturbed claims for the verifier. Then `training/train_lora.py` trained a rank-r weight delta "
        "W' = W + (α/r)·B·A restricted to the top 14 transformer layers and the 7 projection matrices "
        "in each, on CPU. Loss is computed on the specialist's reply only.",
        meta_table(),
        "Exactly which tensors changed and by how much (‖ΔW‖/‖W‖ per layer and module, effective rank): "
        "`training/reports/weights_<specialist>.md`.",
        "**Measure again, keep only what helps.** Same held-out cases, same scoring:",
        score_table(tags, labels),
        "An edit is kept only if its specialist scores at least as well as without it; otherwise the base "
        "weights are used and the edit is moved to `adapters/.rejected/`.",
    ])


if __name__ == "__main__":
    tags = sys.argv[1:] or ["base", "base_tools", "trained"]
    labels = {"base": "base model, first design", "base_tools": "base model, improved design",
              "trained": "edited weights, improved design"}
    text = main(tags, labels)
    readme = ROOT / "README.md"
    s = readme.read_text()
    start = s.index("## How the specialists were improved") + len("## How the specialists were improved")
    end = s.index("## Dreaming")
    s = s[:start] + "\n\n" + text + "\n\n" + s[end:]
    readme.write_text(s)
    print(text)
