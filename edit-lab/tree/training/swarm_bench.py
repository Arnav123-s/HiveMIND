"""How big a swarm fits in the RAM budget? Runs every member of a large swarm in turn on the shared bases and
records the process's peak memory. Members = role prompt + base model + optional weight edit (+ internal edit)."""
import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("AGENT_TEAM_ENGINE", "gguf")
from team import config, llm  # noqa: E402

PROMPTS = {"careful": "You are careful and exact.", "brief": "Answer in as few words as possible.",
           "teacher": "Explain like a patient teacher.", "skeptic": "Question every claim before accepting it."}
members = []
for edit in ("browser", "verifier", "writer", None):  # members on the shared 1.7B
    for style in PROMPTS:
        members.append((f"fast+{edit}" if edit else "fast", style))
for style in PROMPTS:  # members on the 4B brain
    members.append((config.BRAIN, style))
for style in ("careful", "brief"):  # members on the coder
    members.append(("coder7b", style))

peak = {"anon": 0.0, "system_used": 0.0}


def sample():
    base = None
    while not done.is_set():
        anon = sum(int(ln.split()[1]) for ln in open("/proc/self/smaps_rollup") if ln.startswith("Anonymous")) / 1e6
        used = [int(x) for x in os.popen("free -m").read().split("\n")[1].split()[1:3]][1] / 1e3
        base = used if base is None else base
        peak["anon"] = max(peak["anon"], anon)
        peak["system_used"] = max(peak["system_used"], used - base0)
        time.sleep(0.5)


base0 = [int(x) for x in os.popen("free -m").read().split("\n")[1].split()[1:3]][1] / 1e3
done = threading.Event()
threading.Thread(target=sample, daemon=True).start()
t0 = time.time()
for i, (spec, style) in enumerate(members):
    role = f"m{i}"
    config.GGUF_ROSTER[role] = spec
    llm.chat(role, [{"role": "system", "content": PROMPTS[style]}, {"role": "user", "content": "Say ready."}], max_new_tokens=6)
done.set()
time.sleep(0.6)
res = {"members": len(members), "distinct_base_models": 3, "ram_budget_gb": config.RAM_GB, "kv_8bit": config.KV_8BIT,
       "max_resident_models": config.GGUF_MAX_LOADED, "peak_process_alloc_gb": round(peak["anon"], 2),
       "peak_system_used_gb": round(peak["system_used"], 2), "seconds": round(time.time() - t0)}
print(json.dumps(res))
(ROOT / "training" / "reports" / "swarm_bench.json").write_text(json.dumps(res, indent=1))
