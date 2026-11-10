"""Can small models do the 4B's biggest job, reading sources and pulling out the facts, if the reading is cut up?

    python training/chunk_read.py [--runs runs/drill runs/life] [--max 30] [--chunk 1800]
The researcher (Qwen3-4B) reads up to 9000 characters of sources in one call; in the logs that one call is the
largest share of the hive's model time. Here the same real inputs (every logged extract call) are read again by the
1.7B alone: the sources are cut at line ends into chunks of --chunk characters, each chunk is read in its own call
with an instruction for that one small job, and the facts are put together. Both sides then pass the hive's own checks: the quote must
be in the source word for word, and the verifier must find that it supports the claim.

Measured per input: checked facts from each side, how many of the 4B's checked facts the small reading also found
(same quoted passage), and model seconds. Nothing is trained here. The verifier's checks of these real extracted facts
are logged (runs/chunk_read/calls.jsonl) like any other work of its: they are decisions of its fact-check job.
Writes training/reports/chunk_read.json and .md.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team import llm, prompts  # noqa: E402
from team.specialists import verifier  # noqa: E402

SMALL = "juror_fast"  # the plain Qwen3-1.7B, no weight edit
from team.specialists.reader import EXTRACT as CHUNK_EXTRACT  # noqa: E402 - the hive's small reader's own instruction


def extract_calls(dirs, limit):
    seen, out = set(), []
    for d in dirs:
        for f in sorted(Path(d).rglob("calls.jsonl")):
            for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    c = json.loads(ln)
                except ValueError:
                    continue
                m = c.get("messages") or []
                if c.get("specialist") != "researcher" or len(m) != 2 or m[0]["content"] != prompts.RESEARCHER_EXTRACT:
                    continue
                user = m[1]["content"]
                if user in seen or "\n\nSOURCES:\n" not in user:
                    continue
                seen.add(user)
                out.append({"user": user, "output": c["output"], "seconds": c.get("seconds") or 0.0, "run": str(f.parent)})
    return out[:limit]


from team.specialists.reader import chunks  # noqa: E402 - the same cutting the hive's small reader uses


def facts_of(data):
    fs = data.get("facts") if isinstance(data, dict) else None
    return [f for f in fs or [] if isinstance(f, dict) and f.get("claim") and f.get("quote")]


def checked(facts, sources):
    """The hive's own checks: quote word for word in the sources, then the verifier on claim against quote."""
    out, secs = [], 0.0
    for f in facts:
        claim, quote = str(f["claim"]), str(f["quote"])
        if not verifier.quote_in(quote, sources):
            continue
        t0 = time.time()
        ok, _ = verifier.check_fact(claim, quote)
        secs += time.time() - t0
        if ok:
            out.append({"claim": claim, "quote": quote})
    return out, secs


def same_passage(a, b):
    na, nb = verifier.norm(a), verifier.norm(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    wa, wb = set(na.split()), set(nb.split())
    return len(wa & wb) >= 0.6 * min(len(wa), len(wb))


def small_read(task_head, sources, size):
    facts, secs, n = [], 0.0, 0
    for ch in chunks(sources, size):
        t0 = time.time()
        data, _ = llm.chat_json(SMALL, [{"role": "system", "content": CHUNK_EXTRACT},
                                        {"role": "user", "content": f"{task_head}\n\nPART:\n{ch}"}],
                                max_new_tokens=500, adapter=False)
        secs += time.time() - t0
        n += 1
        for f in facts_of(data):
            if not any(same_passage(f["quote"], g["quote"]) and verifier.norm(f["claim"]) == verifier.norm(g["claim"])
                       for g in facts):
                facts.append(f)
    return facts, secs, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", default=[str(ROOT / "runs" / "drill"), str(ROOT / "runs" / "life")])
    ap.add_argument("--max", type=int, default=30)
    ap.add_argument("--chunk", type=int, default=1800)
    a = ap.parse_args()
    import os
    os.environ["AGENT_TEAM_SPAWN"] = "0"  # the verifier itself checks both sides: no cell answers for it here
    rows = []
    log = ROOT / "runs" / "chunk_read"
    log.mkdir(parents=True, exist_ok=True)

    def record(specialist, messages, output, **info):
        if specialist == "verifier":  # its checks of real extracted facts are real decisions of that job
            with open(log / "calls.jsonl", "a") as f:
                f.write(json.dumps({"step": "check", "specialist": specialist, "messages": messages, "output": output,
                                    **info}, ensure_ascii=False) + "\n")
    llm.set_recorder(record)
    for i, c in enumerate(extract_calls(a.runs, a.max)):
        task_head, sources = c["user"].split("\n\nSOURCES:\n", 1)
        big = facts_of(llm.parse_json(c["output"]))
        big_ok, _ = checked(big, sources)
        small, secs, n = small_read(task_head, sources, a.chunk)
        small_ok, _ = checked(small, sources)
        found = sum(any(same_passage(b["quote"], s["quote"]) for s in small_ok) for b in big_ok)
        rows.append({"task": task_head.split("Task:", 1)[-1].strip()[:120], "chars": len(sources), "chunks": n,
                     "big_facts": len(big), "big_checked": len(big_ok), "big_seconds": round(c["seconds"], 1),
                     "small_facts": len(small), "small_checked": len(small_ok), "small_seconds": round(secs, 1),
                     "big_checked_also_found": found, "small_only": [s["claim"][:120] for s in small_ok if not any(
                         same_passage(b["quote"], s["quote"]) for b in big_ok)][:6],
                     "missed": [b["claim"][:120] for b in big_ok if not any(same_passage(b["quote"], s["quote"])
                                                                           for s in small_ok)][:6]})
        r = rows[-1]
        print(f"{i:02d} {r['chars']:5d} chars {n} chunks | 4B {r['big_checked']} checked facts {r['big_seconds']:5.0f}s | "
              f"1.7B {r['small_checked']} checked {r['small_seconds']:5.0f}s | found {found}/{r['big_checked']} of the 4B's | "
              f"{r['task'][:50]}", flush=True)
        tot = {k: sum(x[k] for x in rows) for k in ("big_checked", "small_checked", "big_checked_also_found",
                                                    "big_seconds", "small_seconds", "big_facts", "small_facts")}
        with_big = [x for x in rows if x["big_checked"]]
        summary = {"inputs": len(rows), "chunk_chars": a.chunk, **tot,
                   "inputs_where_small_found_every_4b_fact": sum(x["big_checked_also_found"] == x["big_checked"] for x in with_big),
                   "inputs_where_4b_had_checked_facts": len(with_big),
                   "inputs_where_small_found_none_but_4b_did": sum(x["small_checked"] == 0 for x in with_big),
                   "inputs_where_only_small_had_checked_facts": sum(x["small_checked"] > 0 and not x["big_checked"] for x in rows)}
        out = ROOT / "training" / "reports"
        (out / "chunk_read.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
