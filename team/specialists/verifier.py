"""Verifier: every result is checked before the team relies on it.

Hard checks run first (quote really is in the source, code really exited 0,
files really exist); the verifier model then judges what code cannot.
"""
import re
from pathlib import Path

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
    sizes = [float(m.group(1))] if m else []
    # quantized repos report packed parameter counts; the size in the model's name is the real one
    first = evidence.split("|")[0]
    sizes += [float(x) for x in re.findall(r"[-_](\d+(?:\.\d+)?)[bB](?![a-zA-Z])", first)]
    if limit and sizes and max(sizes) >= float(limit.group(2)):
        return f"{max(sizes)}B is not under {limit.group(2)}B"
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


def describe_file(path):
    """What a saved file holds, checked in code: an image's format and size in pixels, a text file's first lines."""
    name = path.name
    if not path.exists() or path.stat().st_size == 0:
        return f"EMPTY: {name} has no content"
    kb = path.stat().st_size / 1024
    if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf"):
        if path.suffix.lower() in (".svg", ".pdf"):
            return f"{name}: a {path.suffix[1:].upper()} file of {kb:.0f} KB"
        try:
            from PIL import Image
            with Image.open(path) as im:
                w, h = im.size
                colours = len(set(im.convert("RGB").resize((64, 64)).getdata()))
            if colours < 3:
                return f"BROKEN: {name} is a blank image ({w}x{h} pixels, one colour)"
            return f"{name}: a valid {im.format} image, {w}x{h} pixels, {kb:.0f} KB (a drawn picture, not blank)"
        except Exception as e:  # noqa: BLE001
            return f"BROKEN: {name} is not a readable image ({type(e).__name__})"
    try:
        head = path.read_text(errors="replace")[:600]
    except Exception:  # noqa: BLE001
        return f"{name}: {kb:.0f} KB"
    return f"{name} ({kb:.1f} KB), first lines:\n{head}"


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
    from ..cells import use
    if use.on("claim_support"):  # one small cell trained only on "does this quote state this claim"
        v = use.ask("claim_support", f"CLAIM: {claim}\nQUOTE: {quote}")
        return v == "SUPPORTED", f"claim_support cell: {v}"
    from ..cells import learn
    text = f"CLAIM: {claim}\nQUOTE: {quote}"
    v = learn.decide("learned_claim", text)  # a cell grown from the verifier's own decisions, when it is sure
    if v:
        return v == "SUPPORTED", f"learned_claim cell: {v}"
    data, raw = llm.chat_json("verifier", fact_messages(claim, quote), max_new_tokens=100)
    v = str((data or {}).get("verdict", "")).upper() if isinstance(data, dict) else ""
    learn.record("learned_claim", text, v)  # the hive learns from its own work (memory/decisions/)
    return v == "SUPPORTED", str((data or {}).get("reason", raw[:100]) if isinstance(data, dict) else raw[:100])


def _rescue_quote(claim, corpus, board):
    """The cited quote is in no source: the quote_pick cell chooses which source sentence states the claim, from the
    six that share the most words with it. Returns (exact sentence, its url) or None."""
    from ..cells import use
    if not use.on("quote_pick") or not corpus:
        return None
    words = set(re.findall(r"[a-z0-9.\-]{3,}", claim.lower()))
    cands, seen = [], set()
    for u, t in corpus.items():
        for s in re.split(r"(?<=[.!?])\s+|\n", t):
            s = s.strip(" -\t")
            if 15 <= len(s) <= 300 and s not in seen:
                seen.add(s)
                ov = len(words & set(re.findall(r"[a-z0-9.\-]{3,}", s.lower())))
                if ov >= 2:
                    cands.append((ov, s, u))
    cands = sorted(cands, key=lambda c: -c[0])[:6]
    if not cands:
        return None
    x = f"CLAIM: {claim}\nSENTENCES:\n" + "\n".join(f"{i + 1}. {s}" for i, (_, s, _) in enumerate(cands))
    a = use.ask("quote_pick", x, board)
    if a.isdigit() and 1 <= int(a) <= len(cands):
        return cands[int(a) - 1][1], cands[int(a) - 1][2]
    return None


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
            if not quote_in(quote, corpus.get(url, "")) or not url.startswith("http"):
                # cited the wrong source, or a search listing: credit the page that really contains the quote
                url = (next((u for u, t in corpus.items() if u.startswith("http") and quote_in(quote, t)), None)
                       or next((u for u, t in corpus.items() if quote_in(quote, t)), None) or url)
            if not quote_in(quote, corpus.get(url, "") or all_text):
                found = _rescue_quote(claim, corpus, board)
                if not found:
                    board.add_fact(sid, claim, url, quote, "rejected", "quote not found in any source the team read")
                    continue
                quote, url = found  # the exact sentence of a source the team read; the claim is still checked below
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
            from ..cells import learn
            item_text = f"TASK: {step['task']}\nITEM: {it}\nSOURCE LINE: {ev}"
            said = learn.decide("learned_item", item_text)  # a cell grown from the juror's own decisions, when sure
            if said:
                data = {"meets": said == "yes", "why": "learned_item cell"}
            else:
                data, _ = llm.chat_json("juror_brain", [
                    {"role": "system", "content": "Decide if ONE item meets every requirement of the task, using only its "
                     "source line. Size and gating were already checked in code and passed: do not judge them again "
                     "('gated False' means NOT gated). Judge only the other requirements (e.g. license, type). "
                     'Reply with JSON only: {"meets": true} or {"meets": false, "why": "..."}'},
                    {"role": "user", "content": item_text}], max_new_tokens=80)
                if isinstance(data, dict) and isinstance(data.get("meets"), bool):
                    learn.record("learned_item", item_text, "yes" if data["meets"] else "no")
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
        shown = [describe_file(workdir / f) for f in result.get("files", [])]
        empty = [d for d in shown if d.startswith("EMPTY") or d.startswith("BROKEN")]
        if empty:
            return "FAIL", "; ".join(empty)[:300]
        # the jury sees the files, not only what the program printed: a saved chart was rejected because "the
        # evidence shows the number of downloads, not the file"
        # the jury sees the program as well as what it printed: shown only "30", it could not tell that the fixed loop
        # sums the even numbers to 10 and rejected a right fix as "insufficient evidence"
        code = ""
        if result.get("code_path") and Path(result["code_path"]).exists():
            code = Path(result["code_path"]).read_text(errors="replace")[:2500]
        return judge(check, "Program ran (exit 0)." + (f" Files saved: {', '.join(result['files'])}" if result.get("files") else ""),
                     (f"PROGRAM:\n{code}\n\n" if code else "") + "OUTPUT:\n" + (result.get("summary", "") or "(nothing)")
                     + ("\n\nFILES SAVED (checked in code):\n" + "\n".join(shown) if shown else ""))

    if agent == "calculator":
        if result.get("failed"):
            return "FAIL", result["failed"]
        if result.get("returncode") != 0:
            return "FAIL", f"program exited {result.get('returncode')}: {result.get('stderr', '')[-300:]}"
        if not re.search(r"\d", result.get("summary", "")):
            return "FAIL", "the program printed no number"
        # one check, not a jury: the arithmetic is Python's; only "does it compute what was asked" needs a model
        return _judge_one("verifier", check + " (Does the PROGRAM compute exactly what the task asks, with its numbers?)",
                          f"Program ran (exit 0). Output: {result.get('summary', '')[:500]}", result.get("code", ""))

    if agent == "writer":
        body = result.get("summary", "").split("\n## ")[0].strip()
        if not body:  # a two-line summary or a translated sentence is short and right: only empty is wrong
            return "FAIL", "report is empty"
        return "PASS", "report written from verified results"

    return "FAIL", f"unknown agent {agent}"
