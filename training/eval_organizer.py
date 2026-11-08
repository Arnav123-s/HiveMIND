"""The page organizer (element_match cell on every element) on the browser's held-out click cases, live pages.

    python training/eval_organizer.py
Where the right next action is a click: does the organizer's top element match? Compared with the browser model's
own score on the same cases (training/reports/browser/eval_<lora>.json). Writes training/reports/browser/organizer.json.
"""
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import runtime  # noqa: E402
from team.tools.browser import Browser  # noqa: E402
from training.evals.browser_cases import CASES, SKILL_CASES  # noqa: E402

out = {}
b = Browser()
try:
    for c in [c for c in CASES + SKILL_CASES if "click_text" in c["expect"]]:
        b.goto(c["url"])
        obs = b.observe(c["goal"])
        lines = [ln for ln in obs["elements"].split("\n") if re.match(r"\[\d+\]", ln.strip())]
        t = time.time()
        pick = runtime.pick_element(f"GOAL: {c['goal']}\nELEMENTS:\n" + "\n".join(lines))
        el = b.elements.get(int(pick)) if pick.isdigit() else None
        ok = bool(el and re.search(c["expect"]["click_text"], el["text"]))
        out[c["name"]] = {"ok": ok, "picked": el["text"][:60] if el else None, "elements": len(lines),
                          "seconds": round(time.time() - t, 2)}
        print(f"{'OK ' if ok else 'BAD'} {c['name']}: picked {out[c['name']]['picked']!r} of {len(lines)} in {out[c['name']]['seconds']}s", flush=True)
finally:
    b.close()
    runtime.unload()
d = ROOT / "training" / "reports" / "browser"
d.mkdir(parents=True, exist_ok=True)
(d / "organizer.json").write_text(json.dumps(out, indent=1))
print(f"organizer: {sum(v['ok'] for v in out.values())}/{len(out)}")
