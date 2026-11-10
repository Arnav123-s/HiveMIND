"""Score a version of the browser's weight edit on its held-out cases, as the hive runs it (llama.cpp).

    python training/eval_browser.py <lora name in adapters_gguf/> [--live]
Single-step cases (the next action on a real page): CASES (from the first training) and SKILL_CASES (skills added
later); --live also runs whole tasks (LIVE). Writes training/reports/browser/eval_<lora>.json.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
lora = sys.argv[1]
os.environ["AGENT_TEAM_ROSTER"] = json.dumps({"browser": f"fast+{lora}"})
from team import llm  # noqa: E402
from team.board import Board  # noqa: E402
from team.guard import Guard  # noqa: E402
from team.specialists import browser_agent, verifier  # noqa: E402
from team.tools.browser import Browser  # noqa: E402
from training.evals.browser_cases import CASES, LIVE, SKILL_CASES  # noqa: E402


def score(case, elements, page_text, action):
    exp = case["expect"]
    if not isinstance(action, dict):
        return 0.0
    a = action.get("action")
    if "click_text" in exp:
        ok = {e["id"] for e in elements.values() if re.search(exp["click_text"], e["text"])}
        return float(a == "click" and str(action.get("id")).isdigit() and int(action["id"]) in ok)
    if "done_evidence" in exp:
        ev = str(action.get("evidence", ""))
        return float(a == "done" and verifier.quote_in(ev, page_text) and
                     bool(re.search(exp["done_evidence"], ev + " " + str(action.get("answer", "")))))
    if "done_parts" in exp:  # several items, each copied from the page
        ev = str(action.get("evidence", ""))
        parts = [p for p in re.split(r"\s*(?:\.\.\.|…|\n)\s*", ev) if len(p.strip()) >= 8]
        return float(a == "done" and verifier.quote_in(ev, page_text) and len(parts) >= exp["done_parts"])
    if "type_search" in exp:
        el = elements.get(int(action["id"])) if str(action.get("id", "")).isdigit() else None
        return float(a == "type" and bool(el) and el.get("tag") == "input" and bool(str(action.get("text", "")).strip()))
    if "fail" in exp:
        return float(a == "fail")
    if "goto_host" in exp:
        return float(a == "goto" and exp["goto_host"] in str(action.get("url", "")))
    return 0.0


def single(cases):
    out = {}
    b = Browser()
    try:
        for c in cases:
            try:
                b.goto(c["url"]) if c["url"] != "about:blank" else b.page.goto("about:blank")
                obs = b.observe(c["goal"])
                text = b.text(20000)
                action, raw = llm.chat_json("browser", browser_agent.turn_messages(c["goal"], obs, c.get("history", [])),
                                            max_new_tokens=200)
                out[c["name"]] = {"score": score(c, b.elements, text, action), "action": action if isinstance(action, dict) else raw}
            except Exception as e:  # noqa: BLE001 - a page that did not load is a failed case, with the reason
                out[c["name"]] = {"score": 0.0, "error": str(e)[:200]}
            print(f"{out[c['name']]['score']:.0f} {c['name']}: {str(out[c['name']].get('action') or out[c['name']].get('error'))[:150]}", flush=True)
    finally:
        b.close()
    return out


def live(cases):
    out = {}
    for c in cases:
        board = Board(Path(tempfile.mkdtemp(prefix="browser_live_")), echo=False)
        res = browser_agent.run(c["goal"], "", board, "live", Guard(board, "never"), start_url=c["url"])
        text = f"{res.get('summary', '')} {res.get('evidence', '')}"
        out[c["name"]] = {"score": float(bool(re.search(c["answer"], text)) and not res.get("failed")),
                          "answer": (res.get("summary") or res.get("failed") or "")[:200]}
        print(f"{out[c['name']]['score']:.0f} {c['name']}: {out[c['name']]['answer'][:150]}", flush=True)
    return out


if __name__ == "__main__":
    res = {"lora": lora, "cases": single(CASES), "skill_cases": single(SKILL_CASES)}
    if "--live" in sys.argv:
        res["live"] = live(LIVE)
    for k in ("cases", "skill_cases", "live"):
        if k in res:
            res[f"{k}_score"] = round(sum(v["score"] for v in res[k].values()) / len(res[k]), 3)
    print({k: v for k, v in res.items() if k.endswith("_score")})
    d = ROOT / "training" / "reports" / "browser"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"eval_{lora}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
