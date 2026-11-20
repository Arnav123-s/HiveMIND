"""Use the pinned t80 server to select typed operations from a user's request."""
from urllib.request import Request, urlopen
import json
import time


INSTRUCTION = """Choose two operations for the user's table request. Reply with their two letters.
First letter: C = count records, S = sum a numeric column.
Second letter: P = one total, G = a mapping per group, H = return the group name with greatest result, L = return the group name with least result.
Choose X if these operations cannot answer the question. A category restriction is handled separately."""
GRAMMAR = 'root ::= ("C" | "S") ("P" | "G" | "H" | "L") | "X"'


def post(url, path, body):
    req = Request(url.rstrip("/") + path, data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=150) as response:
        return json.load(response)


def select(url, request, columns):
    messages = [{"role": "system", "content": INSTRUCTION},
                {"role": "user", "content": "Columns: " + ", ".join(columns) + "\n" + request}]
    template = post(url, "/apply-template", {
        "messages": messages, "chat_template_kwargs": {"enable_thinking": False},
    })
    start = time.monotonic()
    result = post(url, "/completion", {"prompt": template["prompt"], "grammar": GRAMMAR,
                  "temperature": 0, "seed": 1901, "n_predict": 5, "cache_prompt": True, "stream": False})
    return {"code": result["content"].strip(), "seconds": round(time.monotonic() - start, 3),
            "timings": result.get("timings"), "stop": result.get("stop_type")}
