"""Cell vs incumbent on the same test inputs; decides which jobs each cell takes (cells/wins.json).

A cell takes a job when its llama.cpp test score is at least the incumbent's. Writes the summary table
training/reports/cells/SUMMARY.md.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import runtime, skills as S  # noqa: E402
from team.guard import parse_orders  # noqa: E402

R = ROOT / "training" / "reports" / "cells"
KINDS = ("spend", "delete", "send", "login", "signup")


def orders_organizer():
    """The five order cells together, as the guard uses them: exact set, false approvals, missed orders;
    alone and combined with the parser (both must agree)."""
    cases = json.loads((ROOT / "training" / "evals" / "orders_heldout.json").read_text())
    res = {"cells": [0, 0, 0], "both": [0, 0, 0]}
    for c in cases:
        gold = set(c["orders"])
        cell = runtime.orders(c["text"])
        both = cell & (set(parse_orders(c["text"])) & set(KINDS))
        for k, got in (("cells", cell), ("both", both)):
            res[k][0] += got == gold
            res[k][1] += len(got - gold)
            res[k][2] += len(gold - got)
    n = len(cases)
    return {k: {"exact": round(v[0] / n, 3), "false_approvals": v[1], "missed_orders": v[2]} for k, v in res.items()} | {"n": n}


def family_as_used():
    """The guard asks the rule OR the family cell (the cell only adds blocks): that pair against the rule alone."""
    from team import guard
    from training.cells import data
    _, _, te = data("family_topic")
    pred = ["yes" if guard.FAMILY.search(x) or runtime.run("family_topic", x) == "yes" else "no" for x, _ in te]
    return round(sum(S.score("family_topic", p, y) for p, (_, y) in zip(pred, te)) / len(te), 4)


def page_organizer():
    """pick_element done by the smaller element_match cell, asked once per element (runtime.pick_element)."""
    from training.cells import data
    _, _, te = data("pick_element")
    runtime.unload()
    t0 = time.time()
    acc = sum(S.score("pick_element", runtime.pick_element(x), y) for x, y in te) / len(te)
    return {"test": round(acc, 4), "ms_per_input": round((time.time() - t0) / len(te) * 1000, 1), "n": len(te)}


if __name__ == "__main__":
    reg = runtime.registry()
    wins, rows = {}, []
    for skill, c in reg.items():
        inc_p = R / f"incumbent_{skill}.json"
        inc = json.loads(inc_p.read_text()) if inc_p.exists() else None
        use = inc is not None and c["test_runtime"] >= inc["test"]
        wins[skill] = {"use": use, "cell": c["test_runtime"], "incumbent": inc and inc["test"],
                       "incumbent_name": inc and inc["incumbent"]}
        v = c["variants"]
        rows.append((skill, c, inc, use, v))
    if "family_topic" in wins and wins["family_topic"]["incumbent"] is not None:
        both = family_as_used()
        wins["family_topic"].update(rule_or_cell=both, use=both >= wins["family_topic"]["incumbent"])
    page = None
    if "element_match" in reg:  # the page organizer competes for pick_element's job against the one-shot cell
        page = page_organizer()
        (R / "organizer_pick_element.json").write_text(json.dumps(page, indent=1))
        inc_p = R / "incumbent_pick_element.json"
        inc = json.loads(inc_p.read_text()) if inc_p.exists() else None
        one = reg.get("pick_element", {}).get("test_runtime", -1)
        best, via = (page["test"], "organizer") if page["test"] > one else (one, "cell")
        use_p = inc is not None and best >= inc["test"]
        wins["pick_element"] = {"use": use_p, "cell": best, "via": via, "one_shot_cell": one if one >= 0 else None,
                                "organizer": page["test"], "incumbent": inc and inc["test"],
                                "incumbent_name": inc and inc["incumbent"]}
        wins["element_match"] = {"use": use_p and via == "organizer", "cell": reg["element_match"]["test_runtime"],
                                 "incumbent": None, "incumbent_name": "member of the pick_element organizer"}
    org = None
    if all(f"orders_{k}" in reg for k in KINDS):
        org = orders_organizer()
        old = json.loads((ROOT / "training" / "reports" / "orders_edited.json").read_text())
        ok = org["both"]["false_approvals"] == 0 and org["both"]["exact"] >= old["both"]["exact"]
        for k in KINDS:  # the order cells replace the order reader only as a group, judged as the guard uses them
            wins[f"orders_{k}"]["use"] = ok
        wins["_orders_organizer"] = {"cells": org, "order_reader_member": {"model": old["model"], "both": old["both"]}, "use": ok}
    old_w = json.loads((runtime.CELLS / "wins.json").read_text()) if (runtime.CELLS / "wins.json").exists() else {}
    wins.update({k: v for k, v in old_w.items() if isinstance(v, dict) and v.get("learned")})  # grown cells keep theirs
    from training.cells_triage_threshold import wins_entry
    if wins_entry():  # the triage cell is judged by its shortcut's precision (training/cells_triage_threshold.py)
        wins["task_kind"] = wins_entry()
    (runtime.CELLS / "wins.json").write_text(json.dumps(wins, indent=1))
    lines = ["# Cells: measured", "",
             "Each cell = SmolLM2-135M (shared, frozen) + its own weight delta. Scores are on the TEST split (other "
             "words, frames, sites than training). Variant columns are the PyTorch test scores of each candidate edit; "
             "the winner is chosen on dev. `cell` = the winner served by llama.cpp. The five orders_* cells take the "
             "job only together, judged as the guard uses them (the organizer table below), so one of them can lose "
             "alone and still say yes here.", "",
             "| skill | hive part | base | locator pick (r8) | pick r8 + r2 elsewhere | r2 everywhere | random K (r8) | r8 everywhere | winner | params changed | cell (llama.cpp) | ms/call | incumbent | incumbent score | ms/call | takes the job |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for skill, c, inc, use, v in rows:
        def g(prefix):
            k = next((k for k in v if k.startswith(prefix)), None)
            return f"{v[k]['test']:.2f} ({v[k]['params'] / 1e3:.0f}K)" if k else "-"
        lines.append(f"| {skill} | {c['part']} | {v.get('base', {}).get('test', 0):.2f} | {g('pick')} | {g('thin')} | "
                     f"{g('all_r2')} | {g('random')} | {g('all_r8')} | {c['variant']} | {c['trainable_params']:,} | {c['test_runtime']:.2f} | "
                     f"{c['ms_per_call']:.0f} | {inc['incumbent'] if inc else '-'} | {inc['test'] if inc else '-'} | "
                     f"{inc['ms_per_call'] if inc else '-'} | {'yes' if wins[skill]['use'] else 'no'} |")
    if "rule_or_cell" in wins.get("family_topic", {}):
        w = wins["family_topic"]
        lines += ["", f"family_topic as the guard uses it (the rule OR the cell; the cell only adds blocks): "
                      f"{w['rule_or_cell']} vs the rule alone {w['incumbent']} -> {'on' if w['use'] else 'off'}."]
    if page:
        w = wins["pick_element"]
        lines += ["", "## pick_element split into a smaller cell plus an organizer", "",
                  "`element_match` answers one question per element (does this element reach the goal?); the organizer "
                  "asks it about every element on the page and acts on the most likely yes (`runtime.pick_element`).", "",
                  "| reader | test (exact id) | ms per page |", "|---|---|---|",
                  f"| one cell reads the whole list (pick_element) | {w['one_shot_cell'] if w['one_shot_cell'] is not None else '-'} | "
                  f"{reg.get('pick_element', {}).get('ms_per_call', '-')} |",
                  f"| organizer over element_match | {page['test']} | {page['ms_per_input']} |",
                  f"| incumbent ({w['incumbent_name'] or '-'}) | {w['incumbent'] if w['incumbent'] is not None else '-'} | - |"]
    if org:
        lines += ["", "## The five order cells as one organizer (as the guard uses them, 63 held-out tasks)", "",
                  "| reader | exact | false approvals | missed orders |", "|---|---|---|---|",
                  f"| order cells alone | {org['cells']['exact']} | {org['cells']['false_approvals']} | {org['cells']['missed_orders']} |",
                  f"| parser AND order cells | {org['both']['exact']} | {org['both']['false_approvals']} | {org['both']['missed_orders']} |"]
        old = wins["_orders_organizer"]["order_reader_member"]
        lines += [f"| order reader member (Qwen3-1.7B + edit) alone | {old['model']['exact']} | {old['model']['false_approvals']} | {old['model']['missed_orders']} |",
                  f"| parser AND order reader member | {old['both']['exact']} | {old['both']['false_approvals']} | {old['both']['missed_orders']} |"]
    (R / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
