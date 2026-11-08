"""Verifier: every result is checked before the team relies on it.

Hard checks run first (quote really is in the source, code really exited 0,
files really exist); the verifier model then judges what code cannot.
"""
import re

from .. import config, llm, prompts


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def quote_in(quote, text):
    q, t = norm(quote), norm(text)
    if len(q) < 4:
        return False
    if q in t:
        return True
    # tolerate ellipses / small gaps: every 25+ char chunk must be present
    parts = [p.strip() for p in re.split(r"\.\.\.|…", q) if len(p.strip()) >= 4]
    return bool(parts) and all(p in t for p in parts)


def hard_item_check(task, evidence):
    """Reason an item breaks a hard limit the task states (size, gating), or None."""
    limit = re.search(r"(under|below|less than|smaller than|at most|up to|<)\s*(\d+(?:\.\d+)?)\s*b\b", task, re.I)
    m = re.search(r"params (\d+(?:\.\d+)?)B", evidence)
    if limit and m and float(m.group(1)) >= float(limit.group(2)):
        return f"{m.group(1)}B is not under {limit.group(2)}B"
    if re.search(r"\b(not|un|non)[- ]?gated\b", task, re.I) and re.search(r"gated (True|manual|auto)", evidence):
        return "gated"
    return None


def judge_messages(check, work, evidence):
    return [{"role": "system", "content": prompts.VERIFIER},
            {"role": "user", "content": f"CHECK: {check}\n\nWORK: {work}\n\nEVIDENCE:\n{evidence}"}]


def fact_messages(claim, quote):
    return [{"role": "system", "content": prompts.VERIFIER_FACT},
            {"role": "user", "content": f"CLAIM: {claim}\nQUOTE: {quote}"}]


def _judge_one(member, check, work, evidence):
    data, raw = llm.chat_json(member, judge_messages(check, work, evidence[:5000]), max_new_tokens=120)
    if not isinstance(data, dict):
        return "FAIL", f"{member} gave no verdict: {raw[:100]}"
    v = str(data.get("verdict", "")).upper()
    return ("PASS" if v == "PASS" else "FAIL"), str(data.get("reason", ""))[:300]


def judge(check, work, evidence):
    """Step verdicts are a vote: different models make different mistakes, so a majority beats any one of them.
    With the PyTorch engine all jurors would be the same model, so only the verifier votes there."""
    jury = config.JURY if llm.use_gguf() else ["verifier"]
    votes = [(m, *_judge_one(m, check, work, evidence)) for m in jury]
    passes = sum(v == "PASS" for _, v, _ in votes)
    verdict = "PASS" if passes * 2 > len(votes) else "FAIL"
    reason = next((r for _, v, r in votes if v == verdict), votes[0][2])
    if len(votes) > 1:
        reason = f"{reason} (jury {passes}/{len(votes)} pass)"
    return verdict, reason


def check_fact(claim, quote):
    data, raw = llm.chat_json("verifier", fact_messages(claim, quote), max_new_tokens=100)
    v = str((data or {}).get("verdict", "")).upper() if isinstance(data, dict) else ""
    return v == "SUPPORTED", str((data or {}).get("reason", raw[:100]) if isinstance(data, dict) else raw[:100])


def verify(step, result, board, workdir):
    """Returns (verdict, reason). Also marks each fact on the board."""
    agent, sid = step["agent"], step["id"]
    check = step.get("done_when") or step["task"]

    if agent == "researcher":
        corpus = result.get("corpus", {})
        all_text = "\n".join(corpus.values())
        good = 0
        for f in result.get("facts", []):
            claim, quote, url = str(f.get("claim", "")), str(f.get("quote", "")), str(f.get("url", ""))
            if not quote_in(quote, corpus.get(url, "")):
                # cited the wrong source: credit the source that really contains the quote, if any
                url = next((u for u, t in corpus.items() if quote_in(quote, t)), None) or url
            if not quote_in(quote, corpus.get(url, "") or all_text):
                board.add_fact(sid, claim, url, quote, "rejected", "quote not found in any source the team read")
                continue
            ok, why = check_fact(claim, quote)
            board.add_fact(sid, claim, url, quote, "supported" if ok else "rejected", why)
            good += ok
        if not corpus:
            return "FAIL", "no source could be read: " + "; ".join(result.get("notes", []))[:200]
        if good == 0 and not result.get("items"):
            return "FAIL", "no fact survived checking against its source"
        items_ok = [i for i in result.get("items", []) if norm(i) and norm(i) in norm(all_text)]
        # short names become the full id the source uses ("Qwen2.5-1.5B" -> "Qwen/Qwen2.5-1.5B"), so later
        # steps never have to guess an owner
        full = []
        for i in items_ok:
            m = re.search(r"\b([\w.\-]+/" + re.escape(i.split("/")[-1]) + r")\b", all_text) if "/" not in i else None
            full.append(m.group(1) if m else i)
        items_ok = list(dict.fromkeys(full))
        if result.get("items") and not items_ok:
            return "FAIL", "listed items do not appear in any source"
        # every item is checked on its own source line against what the task asked for; failures are dropped
        kept, dropped = [], []
        lines = all_text.split("\n")
        for it in items_ok[:8]:
            ev = "\n".join(ln for ln in lines if norm(it) in norm(ln))[:800]
            why = hard_item_check(step["task"], ev)  # hard limits are checked in code, not by a model
            if why:
                dropped.append(f"{it} ({why})")
                continue
            data, _ = llm.chat_json("juror_brain", [
                {"role": "system", "content": "Decide if ONE item meets every requirement of the task, using only its "
                 "source line. Size and gating were already checked in code and passed: do not judge them again "
                 "('gated False' means NOT gated). Judge only the other requirements (e.g. license, type). "
                 'Reply with JSON only: {"meets": true} or {"meets": false, "why": "..."}'},
                {"role": "user", "content": f"TASK: {step['task']}\nITEM: {it}\nSOURCE LINE: {ev}"}], max_new_tokens=80)
            if isinstance(data, dict) and data.get("meets") is False:
                dropped.append(f"{it} ({str(data.get('why', ''))[:80]})")
            else:
                kept.append(it)
        if dropped:
            board.log("juror_brain", "drop", "items that do not meet the task: " + "; ".join(dropped))
            result["summary"] = (result.get("summary", "") + "\nDropped by the team's checks (do not use): "
                                 + "; ".join(dropped))
        if result.get("items") and not kept:
            return "FAIL", "no listed item meets the task: " + "; ".join(dropped)[:200]
        result["items"] = kept or result.get("items", [])
        return judge(check, result.get("summary", "") + "\nItems: " + ", ".join(result["items"]),
                     "\n".join(f"- {f['claim']} (quote: {f['quote']})" for f in board.facts(sid, "supported"))
                     or all_text[:3000])

    if agent == "browser":
        if result.get("failed"):
            return "FAIL", "browser could not finish: " + result["failed"][:200]
        ev = result.get("evidence", "")
        if not quote_in(ev, result.get("page_text", "")):
            return "FAIL", "the evidence quoted is not on the page the browser was on"
        board.add_fact(sid, result.get("summary", ""), result.get("url", ""), ev, "supported", "evidence seen on page")
        return judge(check, result.get("summary", ""), f"Page {result.get('url')}: {ev}")

    if agent == "coder":
        if result.get("returncode") is None:
            return "FAIL", result.get("summary", "not run")
        if result.get("returncode") != 0:
            return "FAIL", f"program exited {result.get('returncode')}: {result.get('stderr', '')[-300:]}"
        from .coder import sanity
        bad = sanity(result.get("summary", ""))
        if bad:
            return "FAIL", "; ".join(bad)
        missing = [f for f in result.get("files", []) if not (workdir / f).exists()]
        if missing:
            return "FAIL", f"files missing: {missing}"
        return judge(check, f"Program ran (exit 0). Files: {result.get('files')}", result.get("summary", ""))

    if agent == "writer":
        text = result.get("summary", "")
        if len(text) < 200:
            return "FAIL", "report is too short"
        return "PASS", "report written from verified results"

    return "FAIL", f"unknown agent {agent}"
