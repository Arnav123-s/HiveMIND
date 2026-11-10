"""Researcher: picks live sources, reads them, returns facts with exact quotes."""
import json
import re
import time

from .. import config, llm, prompts
from ..cells import use
from ..tools import web


SITE = web.SITE
NEWEST = re.compile(r"\b(newest|latest|most recent|recent(ly)?|this (week|month|year)|today|yesterday|last (week|month))\b",
                    re.I)


def today():
    return time.strftime("%Y-%m-%d (%A)")


def plan_messages(task, context):
    user = f"Today is {today()}.\nTask: {task}"
    if context:
        user += f"\n\nWhat the team already found:\n{context}"
    return [{"role": "system", "content": prompts.RESEARCHER_PLAN}, {"role": "user", "content": user}]

_WHERE = re.compile(r"\b(arxiv|openalex|hacker ?news)\b", re.I)


def topic(q):
    """The subject of a search in a source the hive sorts itself. Words that say how to sort ("newest") or where to
    look ("arXiv") are not in the papers: the 1.7B planner searched arXiv for "mixture of experts newest", no paper
    has all four words, and the any-word search sorted by date returned six unrelated papers of that day."""
    t = " ".join(_WHERE.sub(" ", NEWEST.sub(" ", q)).split())
    return t if len(t) > 2 else q


def extract_messages(task, sources_text):
    return [{"role": "system", "content": prompts.RESEARCHER_EXTRACT},
            {"role": "user", "content": f"Today is {today()}.\nTask: {task}\n\nSOURCES:\n{sources_text}"}]


def gather(plan, board, step_id, task="", keep=None, read_top=0):
    """Run the searches and URL reads. Returns (blocks, corpus{url: text}, notes).
    keep(results) -> [bool] drops search results that are not about the task (the research hive's relevance filter,
    asked about every result of a search at once);
    read_top: also read that many of the first kept results' pages."""
    blocks, corpus, notes = [], {}, []
    for s in (plan.get("searches") or [])[:4]:
        if not isinstance(s, dict):
            continue
        src, q = str(s.get("source", "")).lower(), str(s.get("q", "")).strip()
        if src == "url":
            plan.setdefault("urls", []).append(q)
            continue
        if src not in web.SOURCES and use.on("pick_source"):  # unknown source: the pick_source cell chooses one
            src = use.ask("pick_source", q or task[:200], board)
        kw = {}
        if src == "huggingface" and re.search(r"text.generation|chat|instruct|llm|language model|assistant", task, re.I):
            kw = {"pipeline_tag": "text-generation", "limit": 20}
        if src in ("arxiv", "hn", "openalex") and (NEWEST.search(f"{task} {q}") or s.get("sort") == "newest"):
            kw["newest"] = True  # "the newest papers" sorted by relevance gave papers from two years earlier
        if src in ("arxiv", "hn", "openalex"):
            q = topic(q)
        try:
            res = web.search(src, q, **kw)
        except Exception as e:  # noqa: BLE001 - report every failure to the board
            notes.append(f"{src} search '{q}' failed: {e}")
            board.log("researcher", "tool-fail", notes[-1])
            continue
        board.log("researcher", "search", f"{src}: '{q}' -> {len(res)} results")
        if keep is not None and res:
            kept = [r for r, ok in zip(res, keep(res)) if ok]
            if len(kept) < len(res):
                board.log("researcher", "filter", f"{src}: kept {len(kept)} of {len(res)} results as about the question")
            res = kept
        if read_top:
            plan.setdefault("urls", [])
            for r in [r for r in res if str(r.get("url", "")).startswith("http")][:read_top]:
                if r["url"] not in plan["urls"]:
                    plan["urls"].append(r["url"])
        ids = re.findall(r"\b[\w.\-]+/[\w.\-]+\b", q) if src == "huggingface" else []
        for mid in ids[:2]:  # an exact model id: also get that model's own facts (license, files, sizes)
            try:
                det = web.search("hf_model", mid)
                res = res + det
                board.log("researcher", "search", f"hf_model: {mid} -> {len(det)} facts")
            except Exception as e:  # noqa: BLE001
                notes.append(f"hf_model {mid} failed: {e}")
        if src == "wikipedia" and res and res[0].get("url", "").startswith("http"):
            # a search lists 250-character snippets; what a thing is, is in the article (an explanation of a
            # concept found only snippets from model and paper listings)
            plan.setdefault("urls", [])
            if res[0]["url"] not in plan["urls"]:
                plan["urls"].insert(0, res[0]["url"])
        lines = [f"- {r['title']} | {r['url']} | {r['snippet']}" for r in res]
        url = res[0].get("source_url") if res and res[0].get("source_url") else f"search:{src}:{q}"
        text = "\n".join(lines)
        for r, line in zip(res, lines):  # each result is also its own source, so a quote is credited to its page
            if str(r.get("url", "")).startswith("http"):
                corpus.setdefault(r["url"], line[2:])
        corpus[url] = text
        blocks.append(f"### Source: {url}\n{text}")
    for u in (plan.get("urls") or [])[:3]:
        if not isinstance(u, str) or not u.startswith("http"):
            continue
        try:
            page = web.read_url(u, max_chars=30000)
        except Exception as e:  # noqa: BLE001
            notes.append(f"read {u} failed: {e}")
            board.log("researcher", "tool-fail", notes[-1])
            continue
        board.log("researcher", "read", f"{u} ({len(page['text'])} chars)")
        corpus[u] = page["text"]
        short = condense(task, page["title"] or u, page["text"], board)
        blocks.append(f"### Source: {u}\nTitle: {page['title']}\n{short}")
    return blocks, corpus, notes


def condense(task, title, text, board, limit=3000):
    """Long source -> the lines that matter, chosen by the condenser. Extractive, so quotes stay exact."""
    if len(text) <= limit:
        return text
    lines = [ln for ln in text.split("\n") if ln.strip()][:400]
    from ..cells import learn
    said = learn.decide_all("learned_line", [f"TASK: {task[:300]}\nLINE: {ln[:300]}" for ln in lines])
    if lines and sum(x is not None for x in said) >= 0.9 * len(lines):
        # a cell grown from the condenser's own choices, asked about every line at once on the cell pool
        keep = [i for i, x in enumerate(said) if x == "keep"]
        board.log("cell:learned_line", "condense", f"{title[:60]}: kept {len(keep)} of {len(lines)} lines")
        if keep:
            out, size = [], 0
            for i in keep:  # whole lines, up to twice the budget
                if size + len(lines[i]) > limit * 2 and out:
                    break
                out.append(lines[i])
                size += len(lines[i]) + 1
            return "\n".join(out)
    numbered = "\n".join(f"{i}: {ln[:300]}" for i, ln in enumerate(lines))[:14000]
    data, _ = llm.chat_json("condenser", [{"role": "system", "content": prompts.CONDENSER},
                                          {"role": "user", "content": f"TASK: {task}\nSOURCE: {title}\n\n{numbered}"}],
                            max_new_tokens=200)
    keep = [int(i) for i in (data or {}).get("keep", []) if str(i).isdigit() and int(i) < len(lines)] \
        if isinstance(data, dict) else []
    if not keep or len(keep) > 60:  # the condenser failed to choose: fall back to goal-matching lines
        from ..tools.browser import focus_text
        board.log("condenser", "fallback", f"{title[:60]}: kept goal-matching lines")
        return focus_text(text, task, head=600, budget=limit)
    board.log("condenser", "condense", f"{title[:60]}: kept {len(keep)} of {len(lines)} lines")
    shown = len(numbered.split("\n"))  # the lines the condenser saw: its choices are logged to grow learned_line
    kept = set(keep)
    import random
    dropped = [i for i in range(shown) if i not in kept]
    for i in sorted(kept) + random.Random(len(lines)).sample(dropped, min(len(dropped), 3 * max(1, len(kept)))):
        learn.record("learned_line", f"TASK: {task[:300]}\nLINE: {lines[i][:300]}", "keep" if i in kept else "drop")
    return "\n".join(lines[i] for i in sorted(set(keep)))


_VALUE = re.compile(r"(?<![\w./-])\d[\d,.]*\d|(?<![\w./-])\d(?![\w/-])")  # a number standing alone, not part of a name


def with_value(fact):
    """A bare label ("parameter count") states nothing the checker can match to its quote ("params 0.135B"), so it was
    rejected while the number still reached the report through the summary. Such a claim takes its quote's words.
    So does a claim that names a quantity and leaves the number out ("Number of downloads for Qwen/Qwen3-1.7B on
    Hugging Face", quote "downloads 3597908": the small composer then wrote that the model had 0 downloads)."""
    claim, quote = str(fact.get("claim", "")).strip(), str(fact.get("quote", "")).strip()
    if not quote or quote.lower() in claim.lower():
        return fact
    label = not re.search(r"\d", claim) and len(claim.split()) <= 4
    no_number = not _VALUE.search(claim) and bool(_VALUE.search(quote))
    if label or no_number:
        fact["claim"] = f"{claim.rstrip('.')}: {quote[:200]}"
    return fact


def run(task, context, board, step_id):
    plan, raw = llm.chat_json("researcher", plan_messages(task, context), max_new_tokens=300)
    if not isinstance(plan, dict):  # no usable plan: the pick_source cell chooses where to search (else the web)
        src = use.ask("pick_source", task[:300], board) if use.on("pick_source") else "web"
        plan = {"searches": [{"source": src, "q": task[:80]}]}
    plan.setdefault("searches", [])
    urls_in_task = re.findall(r"https?://[^\s)\"']+", task)
    # a site named without a link ("on books.toscrape.com"): read it, do not search the web for it (the web search was
    # blocked by a bot check, and the site itself was never read)
    urls_in_task += [f"https://{d}/" for d in SITE.findall(task) if not any(d in u for u in urls_in_task)]
    plan["urls"] = list(dict.fromkeys((plan.get("urls") or []) + urls_in_task))
    board.log("researcher", "plan", json.dumps(plan)[:300])
    blocks, corpus, notes = gather(plan, board, step_id, task)
    if not blocks:
        return {"summary": "No source could be read. " + "; ".join(notes), "items": [], "facts": [],
                "corpus": {}, "notes": notes}
    text = "\n\n".join(blocks)[:9000]
    if config.SMALL:  # no 4B: the sources are read in small parts, one small job per call (reader.py)
        from . import reader
        head = f"Today is {today()}.\nTask: {task}"
        facts = [with_value(f) for f in reader.read(head, text)]
        summary, items = reader.compose(head, facts)
        board.log("researcher", "read", f"small reader: {len(facts)} facts from {len(reader.chunks(text))} parts")
        return {"summary": summary, "items": items, "facts": facts, "corpus": corpus, "notes": notes}
    data, raw = llm.chat_json("researcher", extract_messages(task, text), max_new_tokens=900)
    if not isinstance(data, dict):
        data = {"summary": raw[:500], "items": [], "facts": []}
    facts = [with_value(f) for f in data.get("facts") or [] if isinstance(f, dict) and f.get("claim")]
    items = [str(i) for i in (data.get("items") or []) if str(i).strip()]
    return {"summary": str(data.get("summary", "")), "items": items, "facts": facts,
            "corpus": corpus, "notes": notes}
