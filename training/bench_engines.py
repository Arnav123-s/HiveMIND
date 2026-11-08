"""Measure RAM and speed of each engine/model on this machine (same prompt, greedy)."""
import json
import os
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
which = sys.argv[1]
os.environ["AGENT_TEAM_ENGINE"] = "hf" if which == "hf" else "gguf"
if which == "gguf8b":
    os.environ["AGENT_TEAM_BRAIN"] = "brain8b"
from team import llm  # noqa: E402

msgs = [{"role": "system", "content": "You are a careful assistant."},
        {"role": "user", "content": "Explain in about 150 words why the sky is blue, then list three related facts."}]
spec = sys.argv[2] if len(sys.argv) > 2 else "verifier"
proc = psutil.Process()
rss0 = proc.memory_info().rss
t0 = time.time()
llm.chat(spec, [{"role": "user", "content": "hi"}], max_new_tokens=4)  # load
load = time.time() - t0
llm.STATS.update(calls=0, tokens_out=0, seconds=0.0)
t0 = time.time()
out = llm.chat(spec, msgs, max_new_tokens=200, adapter=False)
dt = time.time() - t0
def smaps():
    d = {}
    for line in open("/proc/self/smaps_rollup"):
        k, _, v = line.partition(":")
        if v.strip().endswith("kB"):
            d[k.strip()] = int(v.split()[0]) / 1e6
    return d


sm = smaps()
res = {"engine": which, "specialist": spec, "load_s": round(load, 1), "gen_s": round(dt, 1),
       "tokens": llm.STATS["tokens_out"], "tok_per_s": round(llm.STATS["tokens_out"] / dt, 1),
       "rss_gb": round(proc.memory_info().rss / 1e9, 2), "rss_added_gb": round((proc.memory_info().rss - rss0) / 1e9, 2),
       "anon_gb": round(sm.get("Anonymous", 0), 2), "file_backed_gb": round(sm.get("Rss", 0) - sm.get("Anonymous", 0), 2)}
print(json.dumps(res))
with open(ROOT / "training" / "reports" / "engines.jsonl", "a") as f:
    f.write(json.dumps(res) + "\n")
