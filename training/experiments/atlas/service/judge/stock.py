"""Read a single request with the production, local-only classifier and saved methods."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from team import talk

result = talk.local_reply(sys.argv[1], local_only=True)
if result is None:
    print(json.dumps({"status": "abstained", "value": None, "unit": None, "route": "stock_local"}))
elif result.get("saved", {}).get("status") == "answered":
    saved = result["saved"]
    unit = "cents" if saved["task"] == "depot_shipping_fee" else "unspecified"
    print(json.dumps({"status": "answered", "value": saved["value"], "unit": unit,
                      "route": saved["task"], "text": result["text"]}))
elif result.get("saved"):
    print(json.dumps({"status": "abstained", "route": "stock_" + result["saved"]["status"], "value": None,
                      "unit": None, "text": result["text"]}))
else:
    print(json.dumps({"status": "other_local_reply", "value": None, "unit": None, "text": result.get("text")}))
