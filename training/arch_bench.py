"""Engine architecture: does 8-bit attention memory, or prompt-lookup decoding, make the hive faster and smaller
without changing what it writes?

    python training/arch_bench.py
Real prompts the hive sent in the development bench run (runs/bench/new2: a researcher extraction, a critic, a writer,
a verifier, the coder), replayed with greedy decoding under three engine settings, each in a fresh process:
  base          the engine as it runs today: KV cache in 8-bit with flash attention, llama.cpp's repacked weights
  kv16          the KV cache in 16-bit
  base+lu       plus prompt-lookup decoding: next tokens guessed from text already in the prompt (a quote, a claim,
                code being fixed) and checked in one pass; no extra model, no RAM
  norepack      without llama.cpp's extra repacked copy of the weights (the 4B: 6.1 -> 3.6 GB resident)
  norepack+lu   both
Measured per call: seconds, generated tokens per second, whether the output is word for word the base output; per
setting: the process's peak resident memory. A setting is worth switching on only if every output is unchanged (or
only differs where the base output itself was cut off) and it is faster or smaller.
Writes training/reports/arch_bench.json.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "training" / "reports" / "arch_bench.json"
PICK = [("explain", "researcher"), ("explain", "critic"), ("chart", "writer"), ("lookup", "verifier"), ("fib", "coder")]


def decision(out):
    """What a reply decides: a JSON reply's verdict/route/ok/meets and the keys it fills; else its numbers."""
    import re
    from team.llm import parse_json
    d = parse_json(out or "")
    if isinstance(d, dict):
        return tuple(sorted((k, str(v)[:40]) for k, v in d.items() if k in ("verdict", "route", "ok", "meets", "answer")
                            or not isinstance(v, (str, list, dict))))
    return tuple(re.findall(r"\d[\d.,]*", out or ""))[:20]


def calls():
    out = []
    for task, role in PICK:
        p = ROOT / "runs" / "bench" / "new2" / task / "calls.jsonl"
        if not p.exists():
            continue
        rows = [json.loads(ln) for ln in p.read_text().splitlines()]
        rows = [r for r in rows if r.get("specialist") == role and r.get("output")]
        if rows:
            r = max(rows, key=lambda r: len(json.dumps(r["messages"])))  # the longest prompt of that role
            out.append({"task": task, "role": role, "messages": r["messages"], "expected_len": len(r["output"])})
    return out


def one(setting):
    os.environ["AGENT_TEAM_KV"] = "f16" if "kv16" in setting else "q8"
    os.environ["AGENT_TEAM_LOOKUP"] = "1" if "lu" in setting else "0"
    os.environ["AGENT_TEAM_REPACK"] = "0" if "norepack" in setting else "1"
    from team import llm
    res = []
    for c in calls():
        t = time.time()
        out = llm.chat(c["role"], c["messages"], max_new_tokens=700)
        sec = time.time() - t
        model, tok = llm._gguf_model(c["role"], True)
        n = len(tok.encode(out))
        res.append({"task": c["task"], "role": c["role"], "seconds": round(sec, 1), "tokens": n,
                    "tok_per_s": round(n / sec, 2) if sec else None, "output": out})
    hwm = next(int(ln.split()[1]) for ln in open("/proc/self/status") if ln.startswith("VmHWM")) / 1e6
    print(json.dumps({"setting": setting, "peak_rss_gb": round(hwm, 2), "calls": res}))
    llm.unload_all()


def main():
    got = {}
    for s in (sys.argv[1:] or ("base", "kv16", "base+lu", "norepack", "norepack+lu", "norepack+kv16")):
        p = subprocess.run([sys.executable, __file__, "one", s], capture_output=True, text=True, cwd=ROOT)
        line = [ln for ln in p.stdout.splitlines() if ln.startswith("{")]
        if not line:
            print(f"{s} failed:\n{p.stderr[-1500:]}")
            continue
        got[s] = json.loads(line[-1])
    ref = got.get("base") or (json.loads(OUT.read_text())["raw"].get("base", {}) if OUT.exists() else {})
    base = {(c["task"], c["role"]): c["output"] for c in ref.get("calls", [])}  # a saved base run when not re-run
    summary = {}
    for s, r in got.items():
        same = [c["output"] == base.get((c["task"], c["role"])) for c in r["calls"]]
        decided = [decision(c["output"]) == decision(base.get((c["task"], c["role"]), "")) for c in r["calls"]]
        summary[s] = {"peak_rss_gb": r["peak_rss_gb"], "seconds": round(sum(c["seconds"] for c in r["calls"]), 1),
                      "same_output": f"{sum(same)}/{len(same)}", "same_decision": f"{sum(decided)}/{len(decided)}",
                      "per_call": [{k: c[k] for k in ("task", "role", "seconds", "tok_per_s")} for c in r["calls"]]}
        print(f"{s}: {summary[s]['seconds']} s for {len(same)} calls, peak {r['peak_rss_gb']} GB, "
              f"same output as base {summary[s]['same_output']}, same decision {summary[s]['same_decision']}", flush=True)
    OUT.write_text(json.dumps({"summary": summary, "raw": got}, indent=1))


if __name__ == "__main__":
    if sys.argv[1:2] == ["one"]:
        one(sys.argv[2])
    elif sys.argv[1:2] == ["only"]:  # some settings, merged into the saved report: python arch_bench.py only base x y
        sys.argv = sys.argv[1:]
        prev = json.loads(OUT.read_text()) if OUT.exists() else {"summary": {}, "raw": {}}
        main()
        new = json.loads(OUT.read_text())
        OUT.write_text(json.dumps({"summary": {**prev["summary"], **new["summary"]}, "raw": {**prev["raw"], **new["raw"]}},
                                  indent=1))
    else:
        main()
