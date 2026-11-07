"""Verifier: every result is checked before the team relies on it.

Hard checks run first (quote really is in the source, code really exited 0,
files really exist); the verifier model then judges what code cannot.
"""
import re

from .. import llm, prompts


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


def judge_messages(check, work, evidence):
    return [{"role": "system", "content": prompts.VERIFIER},
            {"role": "user", "content": f"CHECK: {check}\n\nWORK: {work}\n\nEVIDENCE:\n{evidence}"}]


def fact_messages(claim, quote):
    return [{"role": "system", "content": prompts.VERIFIER_FACT},
            {"role": "user", "content": f"CLAIM: {claim}\nQUOTE: {quote}"}]


def judge(check, work, evidence):
    data, raw = llm.chat_json("verifier", judge_messages(check, work, evidence[:5000]), max_new_tokens=120)
    if not isinstance(data, dict):
        return "FAIL", f"verifier gave no verdict: {raw[:100]}"
    v = str(data.get("verdict", "")).upper()
    return ("PASS" if v == "PASS" else "FAIL"), str(data.get("reason", ""))[:300]


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
            src = corpus.get(url) or all_text
            if not quote_in(quote, src):
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
        if result.get("items") and not items_ok:
            return "FAIL", "listed items do not appear in any source"
        result["items"] = items_ok or result.get("items", [])
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
