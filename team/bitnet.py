"""The published 2.4B BitNet (microsoft/bitnet-b1.58-2B-4T) as a member of the hive, on Microsoft's own runtime.

The runtime (github.com/microsoft/BitNet, built with `python setup_env.py -md models/BitNet-b1.58-2B-4T -q i2_s`)
serves the model over HTTP:

    build/bin/llama-server -m models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf -t 4 -c 4096 --special --port 8089

HIVE_BITNET_URL says where it listens (http://127.0.0.1:8089) and HIVE_BITNET_MEMBERS which members it is
("2": the second member of team/solo.py; "2,3"; "all"). A member that is another model shares less with the first
than the same model asked twice, which is what agreement between members is worth.

The model answers only in its own chat format, written out here ("User: ...<|eot_id|>Assistant: "). Asked any other
way it repeats itself without end, which is what was first taken for a broken build (2026-11-12). The server must
run with --special: the end of a turn is then printed as <|eot_id|> and the reply is cut there.
"""
import json
import os
import urllib.request

END = "<|eot_id|>"


def url():
    return os.environ.get("HIVE_BITNET_URL", "").rstrip("/")


def is_member(n):
    who = os.environ.get("HIVE_BITNET_MEMBERS", "").strip()
    return bool(url()) and (who == "all" or str(n) in [w.strip() for w in who.split(",")])


def prompt(messages):
    return "".join(f"{m['role'].capitalize()}: {m['content']}{END}" for m in messages) + "Assistant: "


def chat(messages, max_new_tokens=512, temperature=0.0, window=4096):
    messages = list(messages)
    while len(messages) > 3 and len(prompt(messages)) > (window - max_new_tokens - 100) * 3:  # about 3 characters a piece
        del messages[2:4]  # the oldest program and what it printed go first; the orders and the task stay
    body = {"prompt": prompt(messages), "n_predict": max_new_tokens, "temperature": temperature,
            "stop": [END, "\nUser:", "<|end_of_text|>"], "cache_prompt": True}
    req = urllib.request.Request(url() + "/completion", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        text = json.load(r).get("content", "")
    return text.split(END)[0].strip()
