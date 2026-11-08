"""Write the README's cells section from the measured reports (between the cells markers)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "training" / "reports" / "cells"
sys.path.insert(0, str(ROOT))


def j(name):
    p = R / name
    return json.loads(p.read_text()) if p.exists() else None


def variants():
    out = {}
    for d in sorted((ROOT / "cells" / "variants").glob("*")):
        v = {p.parent.name: json.loads(p.read_text()) for p in d.glob("*/result.json")}
        if v:
            out[d.name] = v
    return out


def edit_table():
    """Every skill: test score (edited parameters) of each candidate edit; * = the one dev picked."""
    reg = json.loads((ROOT / "cells" / "registry.json").read_text()) if (ROOT / "cells" / "registry.json").exists() else {}
    cols = ["pick", "thin", "all_r2", "random", "all_r8"]
    rows, best = [], {c: 0 for c in cols}
    for skill, v in variants().items():
        if skill == "gate" or skill.startswith("_"):
            continue
        cells = []
        top = max((r["test"] for k, r in v.items() if k != "base"), default=0)
        for c in cols:
            k = next((k for k in v if k.startswith(c)), None)
            if not k:
                cells.append("-")
                continue
            r = v[k]
            mark = "*" if reg.get(skill, {}).get("variant") == k else ""
            best[c] += r["test"] >= top - 1e-9
            cells.append(f"{r['test']:.3f}{mark} ({r['trainable_params'] / 1e3:.0f}K)")
        rows.append(f"| {skill} | {v.get('base', {}).get('test', 0):.3f} | " + " | ".join(cells) + " |")
    return rows, best


HOOKS = [
    ("engine", "broken JSON from any member, after the code rules fail (`team/llm.py`)", ["json_repair"]),
    ("coordinator", "the instruction checklist from your order (`team/specialists/coordinator.py`)", ["split_orders"]),
    ("coordinator", "a plan step names an unknown specialist", ["route_step"]),
    ("researcher", "no usable search plan, or a search names an unknown source (`team/specialists/researcher.py`)",
     ["pick_source"]),
    ("verifier", "does the quote state the claim (`team/specialists/verifier.py`)", ["claim_support"]),
    ("verifier", "a cited quote is in no source the team read: which source sentence states the claim", ["quote_pick"]),
    ("guard", "the second reading of your order: five one-kind order cells (`team/guard.py`)",
     [f"orders_{k}" for k in ("spend", "delete", "send", "login", "signup")]),
    ("guard", "family check: the rule OR the cell", ["family_topic"]),
    ("hive loop", "after a failed attempt: retry, reroute now, or stop (`team/hive.py`)", ["next_move"]),
]


def hooks():
    p = ROOT / "cells" / "wins.json"
    w = json.loads(p.read_text()) if p.exists() else {}
    out = []
    for part, what, cells in HOOKS:
        on = all(w.get(c, {}).get("use") for c in cells)
        if on:
            state = "**on**"
        elif cells[0].startswith("orders_") and "_orders_organizer" in w:
            o = w["_orders_organizer"]
            state = (f"off: with the parser, the cells read {o['cells']['both']['exact']} exact vs the order reader "
                     f"member's {o['order_reader_member']['both']['exact']}")
        else:
            c = w.get(cells[0], {})
            state = (f"off: cell {c.get('cell', 0):.3f} vs {c.get('incumbent_name')} {c.get('incumbent'):.3f}"
                     if c.get("incumbent") is not None else "off: not measured")
        out.append(f"- {part}: {what} -> `{'`, `'.join(cells) if len(cells) < 3 else 'orders_*'}`: {state}")
    return out


def main():
    summary = (R / "SUMMARY.md").read_text().split("\n", 2)[2] if (R / "SUMMARY.md").exists() else "(not measured yet)"
    fac = j("factory_licence_open.json")
    cut = j("cut22.json")
    reg = json.loads((ROOT / "cells" / "registry.json").read_text()) if (ROOT / "cells" / "registry.json").exists() else {}
    total_params = sum(c["trainable_params"] for c in reg.values())
    total_bytes = sum(c.get("gguf_bytes", 0) for c in reg.values())
    out = ["<!-- cells:start -->", "## Cells: one tiny model per smallest skill (`team/cells/`, `training/cells*.py`)", "",
           "Every smallest job in the hive is its own specialist, a **cell**. A cell is trained for one micro-skill only "
           "(is a purchase ordered? which specialist takes this step? does this quote state this claim? retry, reroute or "
           "give up?) and is allowed to be bad at everything else: other cells cover that. All cells share **one** frozen "
           "SmolLM2-135M (144 MB at 8-bit) in RAM; each cell owns only a small weight delta, hot-swapped per call in "
           "llama.cpp. A label cell answers through a grammar that only allows its labels.", "",
           f"**{len(reg)} cells**, {total_params / 1e6:.1f}M edited parameters in total, {total_bytes / 1e6:.0f} MB of deltas "
           "on one 144 MB base.", "",
           "### Measured: each cell against what does that job today", "",
           "Test inputs use other words, frames and sites than training. The winner per skill is chosen on a dev split "
           "built from **held-out training words** (a dev split with the training words scored 1.0 for every variant and "
           "could not pick a winner). `takes the job` = the cell scored at least as well as the incumbent, so the hive "
           "now hands it that job (`cells/wins.json`, `team/cells/use.py`).", "", summary, "",
           "### Finding which part of the model does what (the locator)", "",
           "Until a trained locator cell exists, I acted as the locator. For each skill, `training/cells.py probe` maps "
           "where the skill lives in the base: (1) |W x dL/dW| per module, the first-order loss change if that module "
           "moved; (2) a knockout per layer, the loss when one layer's attention or MLP output is removed. I read the maps "
           "and wrote my rules down so they are explicit and testable (`training/cells_view.py`, every pick logged with "
           "its reason in `training/reports/cells/locator_log.jsonl`, the future locator cell's training data):", "",
           "- **R1 read**: q and v in the band of layers most sensitive per parameter (layers ~9-17 for every skill: "
           "the value projections there are where the input is read)",
           "- **R2 unblock**: o of layers whose attention knockout LOWERS the loss, down of layers whose MLP knockout "
           "lowers it: these push toward the base's default answer",
           "- **R3 bottleneck**: down of middle layers whose MLP knockout raises the loss by >= 1.0",
           "- **R5**: R2 only from layer 3 up; **R6**: the last two layers' MLPs always (they write the answer out)", "",
           "What the measurements taught the locator (route_step and orders_spend were the tuning skills; the rules "
           "were then frozen and applied to the other skills):", "",
           "- My first rules (without R6) lost to a **random** choice of the same number of modules (route_step 0.941 vs "
           "0.915 random, next_move 0.847 vs 0.893). Adding the output MLPs (R6) moved route_step to 0.966-0.992.",
           "- More rank on the same modules did nothing (rank 32: 0.941). On route_step, editing only the MLPs of every "
           "layer scored 1.000 and attention only 0.958: routing by meaning lives in the MLPs (word -> category "
           "memories); attention mostly moves information.",
           "- **Breadth beats concentration.** On the skills the rules were not tuned on, the locator's concentrated "
           "pick won only pick_source; a random pick of the same size beat it on claim_support and quote_pick; "
           "rank 2 on every module, or the pick plus rank 2 everywhere else (`thin`), won the rest. A skill is not "
           "stored in one small set of modules: a small change in every module edits it best.",
           "- Rank 8 everywhere (2.4M edited parameters) never beat rank 2 everywhere (0.6M): 4x the size for nothing.",
           "- So each skill trains the candidates below from its maps and **dev** picks (dev = held-out training words; "
           "test is never used to choose). Where dev and test disagree it is reported, not fixed by peeking at test "
           "(next_move: dev picked MLP-only rank 2, 0.880 on test, while `thin` scored 0.973).", "",
           "Every skill, every candidate edit (test score, edited parameters; * = the edit dev chose and the hive runs):", "",
           "| skill | base | locator pick (r8) | pick r8 + r2 elsewhere | r2 everywhere | random K (r8) | r8 everywhere |",
           "|---|---|---|---|---|---|---|",
           *edit_table()[0], ""]
    if cut:
        out += ["### Architecture edit: a smaller base by removing layers", "",
                f"The knockout maps show some layers barely matter to any probed skill. `training/cells_cut.py` removed "
                f"the {len(cut['dropped'])} least important ({cut['dropped']}) -> a {cut['layers']}-layer base "
                f"({cut['params_m']:.0f}M params, {cut['gguf_mb']:.0f} MB). Cells retrained on it:", "",
                "| skill | 30 layers | 22 layers | ms/call 30 | ms/call 22 |", "|---|---|---|---|---|",
                *[f"| {r['skill']} | {r['full']:.3f} | {r['cut']:.3f} | {r['ms_full']:.0f} | {r['ms_cut']:.0f} |" for r in cut["rows"]], "",
                cut["verdict"], ""]
    if fac:
        out += ["### Cloning: a new skill gets a cell by copying the nearest one and editing the copy", "",
                "`training/cells_factory.py <skill>`: the parent finder runs every registered cell on the new skill's dev "
                "inputs; the one already closest is cloned (its weight deltas copied into the new cell), then the clone is "
                "trained on the new skill only. The control trains the same modules from zero for the same steps.", "",
                f"New skill `{fac['skill']}` (is a licence free for any use?): nearest cell **{fac['parent']}**. "
                f"After {fac['steps']} steps: clone dev {fac['clone']['dev']:.3f} / test {fac['clone']['test']:.3f}, "
                f"from zero dev {fac['scratch']['dev']:.3f} / test {fac['scratch']['test']:.3f}.", ""]
    gate = reg.get("gate")
    page = j("organizer_pick_element.json")
    one = reg.get("pick_element", {})
    out += ["### Organizers and the gate", "",
            "- **gate**: a cell that routes any input to the group of cells that reads it (order, step, failure, claim, "
            "sentences, page, json, licence), like the gate of a mixture of experts (`team/cells/skills.py` GROUPS)"
            + (f": {gate['test_runtime']:.3f} on test inputs from every cell's test split." if gate and "test_runtime" in gate
               else "."),
            "- **organizers** run a group: the order organizer asks the five one-kind order cells (spend, delete, "
            "send, login, signup) and returns the set that said yes (`team/cells/use.py`).",
            "- **a skill too big for one cell is split again**: one cell reading a whole list of page elements and "
            "copying the right id (pick_element) " + (f"scored {one.get('test_runtime', one.get('test_torch', 0)):.3f}. " if one else "was weak. ")
            + "The smaller skill inside it, `element_match` (does THIS one element reach the goal? yes/no), is its own "
            "cell; the page organizer asks it about every element and acts on the most likely yes"
            + (f": **{page['test']:.3f}** on the same test pages ({page['ms_per_input']:.0f} ms per page)." if page else "."), "",
            "### Where cells work in the hive (switched on only where they won)", "",
            *hooks(),             "", "Turn every cell off with `AGENT_TEAM_CELLS=0`.", "",
            "Commands: `python training/cells_pipeline.py <skill>` (probe, locator pick, candidates, promote); "
            "`python training/cells_factory.py <new_skill>`; `python training/cells_incumbents.py <skill>`; "
            "`python training/cells_compare.py`.", "<!-- cells:end -->"]
    text = "\n".join(out)
    readme = (ROOT / "README.md").read_text()
    if "<!-- cells:start -->" in readme:
        a, rest = readme.split("<!-- cells:start -->", 1)
        readme = a + text + rest.split("<!-- cells:end -->", 1)[1]
    else:
        readme = readme.replace("## Dreaming:", text + "\n\n## Dreaming:", 1)
    (ROOT / "README.md").write_text(readme)
    print(text[:500])


if __name__ == "__main__":
    main()
