"""Held-out accuracy of the two order detectors and of the rule that combines them.
The dangerous error is a FALSE APPROVAL: treating a sentence as an order when Arnav did not give one."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AGENT_TEAM_ENGINE", "gguf")
from team import llm, prompts  # noqa: E402
from team.guard import parse_orders  # noqa: E402

KINDS = {"spend", "delete", "send", "login", "signup"}
cases = json.loads((ROOT / "training" / "evals" / "orders_heldout.json").read_text())
tag = sys.argv[1] if len(sys.argv) > 1 else "eval"
use_edit = "--base" not in sys.argv


def model_orders(text):
    data, _ = llm.chat_json("order_reader", [{"role": "system", "content": prompts.ORDER_READER},
                                             {"role": "user", "content": text}], max_new_tokens=40, adapter=use_edit)
    return {k for k in (data or {}).get("orders", []) if k in KINDS} if isinstance(data, dict) else set()


res = {"regex": [0, 0, 0], "model": [0, 0, 0], "both": [0, 0, 0]}  # exact, false approvals, missed orders
for c in cases:
    gold = set(c["orders"])
    rx = set(parse_orders(c["text"])) & KINDS
    md = model_orders(c["text"])
    for name, pred in (("regex", rx), ("model", md), ("both", rx & md)):
        res[name][0] += pred == gold
        res[name][1] += len(pred - gold)
        res[name][2] += len(gold - pred)
out = {name: {"exact": round(v[0] / len(cases), 3), "false_approvals": v[1], "missed_orders": v[2]} for name, v in res.items()}
out["cases"] = len(cases)
out["model_edit"] = use_edit
print(json.dumps(out, indent=1))
(ROOT / "training" / "reports" / f"orders_{tag}.json").write_text(json.dumps(out, indent=1))
