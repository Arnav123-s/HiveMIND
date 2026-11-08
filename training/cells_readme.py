"""Write the README's cells section from the measured reports (between the cells markers)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "training" / "reports" / "cells"
sys.path.insert(0, str(ROOT))


def ms(x):
    return "-" if x is None else f"{x:.0f}"


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


def breadth_line():
    """Where the locator's concentrated pick stands against the broad edits, from the measured variants."""
    won, tied, lost, rnd = [], [], [], []
    for skill, v in variants().items():
        if "pick" not in v or skill == "gate":
            continue
        others = [r["test"] for k, r in v.items() if k not in ("base", "pick") and not k.startswith("random")]
        if not others:
            continue
        top = max(others)
        p = v["pick"]["test"]
        (won if p > top + 1e-9 else tied if abs(p - top) < 1e-9 else lost).append(skill)
        r = next((r for k, r in v.items() if k.startswith("random")), None)
        if r and r["test"] > p:
            rnd.append(f"{skill} {r['test']:.3f} vs {p:.3f}")
    return (f"- **Breadth beats concentration.** Across {len(won) + len(tied) + len(lost)} skills, the locator's "
            f"concentrated pick (~0.2-0.4M edited parameters) was the best edit on {len(won)} "
            f"({', '.join(won) or 'none'}), tied on {len(tied)} ({', '.join(tied) or 'none'}) and lost on {len(lost)} to "
            f"rank 2 on every module or the pick plus rank 2 everywhere else (`thin`). A random pick of the same size "
            f"beat it where that control ran ({'; '.join(rnd) or 'none'}). A skill is not stored in one small set of "
            "modules: a small change in every module edits it best.")


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
        pick = reg.get(skill, {}).get("variant")
        pk = f"{pick} {v[pick]['test']:.3f}" if pick in v else (pick or "-")  # what dev picked, also outside the columns
        rows.append(f"| {skill} | {v.get('base', {}).get('test', 0):.3f} | " + " | ".join(cells) + f" | {pk} |")
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
    ("hive", "triage: the cheapest way through the hive for the whole task; when sure, a template plan replaces the 4B "
     "coordinator and plan reviewer (`team/specialists/coordinator.py`)", ["task_kind"]),
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


def not_on(reg):
    p = ROOT / "cells" / "wins.json"
    w = json.loads(p.read_text()) if p.exists() else {}
    if not w:
        return []
    out = ["Measured, but not switched on (or with a cost):", "",
           "- checklist (`split_orders`): on a real order the cell respelled a model id ('Smol LM2') and left out "
           "'Do not log in or pay': its training orders had no ids and no negations. The coordinator now keeps the span "
           "of your own words closest to each line and adds any sentence of the order that no line covers, as written "
           "(`team/specialists/coordinator.py`); on the test split that scores 0.927 vs 0.913 for the raw cell.",
           "- JSON repair (`json_repair`): the cell turns ANY text into JSON ('no json here' -> {\"no\": null}); it never "
           "saw text without JSON. The hook now runs only on text that holds a broken object, rejects a repair whose "
           "keys are not in the text, and is asked before the code rules settle for a list inside a broken object (they "
           "returned [1, 2] for a whole object). As used: 1.000 on the test split; the code rules alone 0.493."]
    f = w.get("family_topic", {})
    if "rule_or_cell" in f:
        out.append(f"- family check: the rule OR the cell scores {f['rule_or_cell']} vs the rule alone {f['incumbent']} on "
                   "test. The cell catches family steps the rule misses ('Plan a trip with the kids', 'Choose a school "
                   "for our son') and wrongly flags as many ('Family Guy' trivia, 'brother-in-arms' quotes); a wrongly "
                   "flagged step is dropped and listed in the report. Kept on because your family rule is strict. "
                   "No confidence threshold helps: dev is perfect at every threshold and test has 9-10 false blocks at "
                   "every one (`training/reports/cells/thresholds_and_cascade.md`). The writer's step is judged by the "
                   "rule alone.")
    tk = w.get("task_kind", {})
    if tk.get("thresholds"):
        out.append(f"- triage (`task_kind`): served test 0.913. A shortcut needs the cell's confidence to reach its "
                   f"kind's threshold, chosen on dev ({', '.join(f'{k} {v}' for k, v in tk['thresholds'].items())}): "
                   f"it is taken for {tk['shortcut_share_test']:.0%} of test tasks and is right on {tk['cell']}. What "
                   "it still gets wrong: a lookup it confidently calls a writing task (the writer then answers from its "
                   "own knowledge and the critic marks it; an until-done round re-plans with the coordinator).")
    out.append("- cell -> member cascade (the cell answers when sure, unsure cases go up): on every cell measured, the "
               "threshold chosen on dev sent nothing up, so the cascade equals the cell; none is wired "
               "(`training/reports/cells/thresholds_and_cascade.md`).")
    for k, who in (("claim_support", "verifier"), ("licence_open", "juror")):
        c = w.get(k, {})
        if c and not c.get("use") and c.get("incumbent") is not None:
            out.append(f"- `{k}`: cell {c['cell']:.3f} vs the {who} member {c['incumbent']:.3f}: the bigger member keeps "
                       "the job. The 135M cell lacks the world knowledge the test needs (e.g. that ISC is a permissive "
                       "licence)." if k == "licence_open" else
                       f"- `{k}`: cell {c['cell']:.3f} vs the {who} member {c['incumbent']:.3f}: the bigger member keeps "
                       "the job.")
    pe = w.get("pick_element", {})
    if pe:
        live = j("../browser/organizer.json")
        live_s = (f" On the browser's held-out click cases on live pages it picked the right element in "
                  f"{sum(v['ok'] for v in live.values())}/{len(live)}; the browser member got 7/8 of the same cases "
                  "(`training/reports/browser/`), so the browser keeps choosing its own clicks." if live else "")
        out.append(f"- page organizer (`element_match` per element): {pe.get('organizer')} on the test pages vs the browser "
                   f"member's {pe.get('incumbent')}, asked exactly as the hive asks it.{live_s}")
    if "gate" in reg:
        out.append(f"- `gate`: routes {reg['gate'].get('test_runtime', 0):.3f} of test inputs to the right group. The hive "
                   "calls each cell at a fixed hook, so nothing needs routing yet; the gate is ready for inputs that "
                   "arrive without one.")
    if "orders_any" in reg:
        out.append("- `orders_any`: made by the factory to test cloning; not wired, the five one-kind order cells "
                   "already read every order.")
    return out + [""]


def main():
    summary = (R / "SUMMARY.md").read_text().split("\n", 2)[2] if (R / "SUMMARY.md").exists() else "(not measured yet)"
    summary = summary.replace("\n## ", "\n#### ")
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
           breadth_line(),
           "- Rank 8 everywhere (2.4M edited parameters) beat rank 2 everywhere (0.6M) once in four skills "
           "(orders_spend 0.984 vs 0.967, one test sentence) and lost on the other three: 4x the size, no gain.",
           "- So each skill trains the candidates below from its maps and **dev** picks (dev = held-out training words; "
           "test is never used to choose). Where dev and test disagree it is reported, not fixed by peeking at test "
           "(next_move: dev picked MLP-only rank 2, 0.880 on test, while `thin` scored 0.973).", "",
           "Every skill, every candidate edit (test score, edited parameters; * = the edit dev chose and the hive runs):", "",
           "| skill | base | locator pick (r8) | pick r8 + r2 elsewhere | r2 everywhere | random K (r8) | r8 everywhere | served (dev pick) |",
           "|---|---|---|---|---|---|---|---|",
           *edit_table()[0], ""]
    if cut:
        out += ["### Architecture edit: a smaller base by removing layers", "",
                f"The knockout maps show some layers barely matter to any probed skill. `training/cells_cut.py` removed "
                f"the {len(cut['dropped'])} least important ({cut['dropped']}) -> a {cut['layers']}-layer base "
                f"({cut['params_m']:.0f}M params, {cut['gguf_mb']:.0f} MB). Cells retrained on it:", "",
                "| skill | 30 layers | 22 layers | ms/call 30 | ms/call 22 |", "|---|---|---|---|---|",
                *[f"| {r['skill']} | {r['full']:.3f} | {r['cut']:.3f} | {ms(r['ms_full'])} | {ms(r['ms_cut'])} |" for r in cut["rows"]], "",
                cut["verdict"] + (" " + cut["source"] if cut.get("source") else ""), ""]
    facs = [f for f in (j("factory_orders_any.json"), fac) if f]
    if facs:
        what = {"orders_any": "does the sentence order ANY risky action?",
                "licence_open": "is a licence free for any use, including commercial?"}
        out += ["### Cloning: a new skill gets a cell by copying the nearest one and editing the copy", "",
                "`training/cells_factory.py <skill>`: the parent finder runs every registered cell on the new skill's dev "
                "inputs; the one that already answers it best (ties: the lowest dev loss) is cloned, its weight deltas "
                "copied into the new cell, and the clone is trained on the new skill only. The control trains the same "
                "modules from zero for the same steps. Dev picks which one becomes the cell.", "",
                "| new skill | nearest cell | clone dev / test | from zero dev / test | steps |", "|---|---|---|---|---|",
                *[f"| {f['skill']} ({what.get(f['skill'], '')}) | {f['parent']} | {f['clone']['dev']:.3f} / "
                  f"{f['clone']['test']:.3f} | {f['scratch']['dev']:.3f} / {f['scratch']['test']:.3f} | {f['steps']} |"
                  for f in facs], ""]
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
            *hooks(), "", *not_on(reg),             "### End-to-end: one real task with cells on (`training/reports/cells/hive_check/`)", "",
            "> Find the licence and the parameter count of HuggingFaceTB/SmolLM2-135M-Instruct on Hugging Face and give me "
            "a two-line summary. Do not log in or pay.", "",
            "- run 1: correct answer (Apache-2.0, 0.135B; jury 3/3). The order cells read 'Do not log in or pay' as no "
            "order (right). The checklist cell respelled the model id and left out 'Do not log in or pay' -> fixed "
            "(lines keep your words; uncovered sentences are added).",
            "- run 2, the final code: same correct answer; the checklist has all 4 instructions in your words, 4/4 done. "
            "This time the coordinator also planned a browser and a coder step; when they failed, the `next_move` cell "
            "stopped the browser step after 1 attempt (page not reachable), retried the coder after a crash, and stopped "
            "it after a second failure, instead of always using all 3 attempts.",
            "- the other hooks (JSON repair, routing rescue, source pick, quote rescue) only fire when something breaks; "
            "nothing they cover broke in these two runs, so they are exercised by their tests and test splits only.", "",
            "Turn every cell off with `AGENT_TEAM_CELLS=0`.", "",
            "Commands: `python training/cells_build.py` (after a clone: rebuild the base and the cells for llama.cpp); "
            "`python training/cells_pipeline.py <skill>` (probe, locator pick, candidates, promote); "
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
