"""Researcher: picks live sources, reads them, returns facts with exact quotes."""
import json
import re

from .. import llm, prompts
from ..tools import web


def plan_messages(task, context):
    user = f"Task: {task}"
    if context:
        user += f"\n\nWhat the team already found:\n{context}"
    return [{"role": "system", "content": prompts.RESEARCHER_PLAN}, {"role": "user", "content": user}]


def extract_messages(task, sources_text):
    return [{"role": "system", "content": prompts.RESEARCHER_EXTRACT},
            {"role": "user", "content": f"Task: {task}\n\nSOURCES:\n{sources_text}"}]


def gather(plan, board, step_id, task=""):
    """Run the searches and URL reads. Returns (blocks, corpus{url: text}, notes)."""
    blocks, corpus, notes = [], {}, []
    for s in (plan.get("searches") or [])[:4]:
        if not isinstance(s, dict):
            continue
        src, q = str(s.get("source", "")).lower(), str(s.get("q", "")).strip()
        if src == "url":
            plan.setdefault("urls", []).append(q)
            continue
        kw = {}
        if src == "huggingface" and re.search(r"text.generation|chat|instruct|llm|language model|assistant", task, re.I):
            kw = {"pipeline_tag": "text-generation", "limit": 20}
        try:
            res = web.search(src, q, **kw)
        except Exception as e:  # noqa: BLE001 - report every failure to the board
            notes.append(f"{src} search '{q}' failed: {e}")
            board.log("researcher", "tool-fail", notes[-1])
            continue
        board.log("researcher", "search", f"{src}: '{q}' -> {len(res)} results")
        lines = [f"- {r['title']} | {r['url']} | {r['snippet']}" for r in res]
        url = res[0].get("source_url") if res and res[0].get("source_url") else f"search:{src}:{q}"
        text = "\n".join(lines)
        corpus[url] = text
        blocks.append(f"### Source: {url}\n{text}")
    for u in (plan.get("urls") or [])[:3]:
        if not isinstance(u, str) or not u.startswith("http"):
            continue
        try:
            page = web.read_url(u, max_chars=5000)
        except Exception as e:  # noqa: BLE001
            notes.append(f"read {u} failed: {e}")
            board.log("researcher", "tool-fail", notes[-1])
            continue
        board.log("researcher", "read", f"{u} ({len(page['text'])} chars)")
        corpus[u] = page["text"]
        blocks.append(f"### Source: {u}\nTitle: {page['title']}\n{page['text']}")
    return blocks, corpus, notes


def run(task, context, board, step_id):
    plan, raw = llm.chat_json("researcher", plan_messages(task, context), max_new_tokens=300)
    if not isinstance(plan, dict):
        plan = {"searches": [{"source": "web", "q": task[:80]}]}
    plan.setdefault("searches", [])
    urls_in_task = re.findall(r"https?://[^\s)\"']+", task)
    plan["urls"] = list(dict.fromkeys((plan.get("urls") or []) + urls_in_task))
    board.log("researcher", "plan", json.dumps(plan)[:300])
    blocks, corpus, notes = gather(plan, board, step_id, task)
    if not blocks:
        return {"summary": "No source could be read. " + "; ".join(notes), "items": [], "facts": [],
                "corpus": {}, "notes": notes}
    text = "\n\n".join(blocks)[:9000]
    data, raw = llm.chat_json("researcher", extract_messages(task, text), max_new_tokens=900)
    if not isinstance(data, dict):
        data = {"summary": raw[:500], "items": [], "facts": []}
    facts = [f for f in data.get("facts") or [] if isinstance(f, dict) and f.get("claim")]
    items = [str(i) for i in (data.get("items") or []) if str(i).strip()]
    return {"summary": str(data.get("summary", "")), "items": items, "facts": facts,
            "corpus": corpus, "notes": notes}
