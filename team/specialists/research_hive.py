"""The research hive: a question too big for one look-up is worked by many small specialists at once.

    decomposer (4B member)     the question -> 2 to 4 sub-questions that together answer it
    per sub-question:
      planner (4B member)      sources and short queries (the researcher's planner)
      relevance cells          one call per search result: is it about the sub-question? (result_relevant)
      reader + condenser       the pages of the kept results, cut to the lines that matter
      extractor (4B member)    claims with exact quotes (the researcher's extractor)
    gap finder cells           does any claim answer the sub-question? (answers_q) -> one more search for each gap
    cross-check cells          two sources on the same point: agree, conflict or unrelated? (claims_agree)
The verifier then checks every claim against its quote, as for any research step. A cell takes its job only where
it measured at least as well as what did the job before (cells/wins.json); otherwise the code fallback runs.
Returns the researcher's result shape, so the verifier and writer need nothing new.
"""
import json
import re

from .. import llm
from ..cells import use
from . import researcher

BROAD = re.compile(r"\b(research|investigate|overview|survey|state of the art|landscape|in depth|in-depth|deep dive|"
                   r"pros and cons|advantages and disadvantages|compare|comparison|explain (how|why)|how does|why does|"
                   r"what is known|everything about|end[- ]to[- ]end)\b", re.I)
DECOMPOSE = """You lead research for Arnav's team. Split the QUESTION into 2 to 4 sub-questions that together answer it.
Each sub-question must be answerable by one search (a fact, a definition, a comparison point, a date, a number).
Keep his names and terms exactly. Reply with JSON only: {"questions": ["...", "..."]}"""
STOP = set("the a an of to in on for and or is are was what which who how why does do with about from by its it this "
           "that be as at me my".split())


def broad(task):
    """A research question for the hive, not a single look-up: research words, or several questions at once."""
    return bool(BROAD.search(task or "")) or (task or "").count("?") >= 2


def words(t):
    return {w for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if w not in STOP and len(w) > 2}


def relevant(q, results, board=None):
    """Is each search result about the sub-question? The result_relevant cell, one question per result, all at once
    on the cell pool; else word overlap (half the sub-question's content words in the result)."""
    texts = [f"{r.get('title', '')} | {str(r.get('snippet', ''))[:200]}" for r in results]
    if use.on("result_relevant"):
        return [a == "yes" for a in use.ask_all("result_relevant", [f"QUESTION: {q}\nRESULT: {t}" for t in texts], board)]
    w = words(q)
    return [not w or len(w & words(t)) / len(w) >= 0.5 for t in texts]


def answered(facts, board=None):
    """For each fact: does it answer its own sub-question? The answers_q cell (all at once), else any fact counts."""
    if not facts:
        return []
    if use.on("answers_q"):
        return [a == "yes" for a in use.ask_all("answers_q", [f"QUESTION: {f['question']}\nFACT: {f['claim']}"
                                                              for f in facts], board)]
    return [True] * len(facts)


def conflicts(facts, board=None, limit=24):
    """Pairs of claims from different sources that give different values for the same thing (claims_agree cell, all
    pairs at once); nothing without the cell."""
    if not use.on("claims_agree"):
        return []
    pairs = [(a, b) for i, a in enumerate(facts) for b in facts[i + 1:]
             if a.get("url") != b.get("url") and words(a["claim"]) & words(b["claim"])][:limit]
    said = use.ask_all("claims_agree", [f"A: {a['claim']}\nB: {b['claim']}" for a, b in pairs], board)
    return [p for p, v in zip(pairs, said) if v == "conflict"]


def decompose(task, board):
    data, _ = llm.chat_json("researcher", [{"role": "system", "content": DECOMPOSE},
                                           {"role": "user", "content": f"QUESTION: {task}"}], max_new_tokens=250)
    qs = [str(q).strip() for q in (data or {}).get("questions", []) if str(q).strip()] if isinstance(data, dict) else []
    qs = list(dict.fromkeys(qs))[:4]
    board.log("research_hive", "decompose", " | ".join(qs) or "no sub-questions: the question as one")
    return qs or [task]


def one(q, board, step_id, context="", note=""):
    """Plan, search, filter, read and extract for one sub-question. Returns (facts, items, corpus, notes)."""
    plan, _ = llm.chat_json("researcher", researcher.plan_messages(q + (f"\n{note}" if note else ""), context),
                            max_new_tokens=300)
    if not isinstance(plan, dict) or not plan.get("searches"):
        src = use.ask("pick_source", q[:300], board) if use.on("pick_source") else "web"
        plan = {"searches": [{"source": src, "q": q[:80]}]}
    blocks, corpus, notes = researcher.gather(plan, board, step_id, q, keep=lambda res: relevant(q, res, board),
                                              read_top=1)
    if not blocks:
        return [], [], corpus, notes
    data, raw = llm.chat_json("researcher", researcher.extract_messages(q, "\n\n".join(blocks)[:9000]), max_new_tokens=900)
    if not isinstance(data, dict):
        return [], [], corpus, notes
    facts = [researcher.with_value(f) for f in data.get("facts") or [] if isinstance(f, dict) and f.get("claim")]
    for f in facts:
        f["question"] = q
    items = [str(i) for i in (data.get("items") or []) if str(i).strip()]
    return facts, items, corpus, notes


def run(task, context, board, step_id):
    qs = decompose(task, board)
    facts, items, corpus, notes = [], [], {}, []
    for q in qs:
        f, it, c, n = one(q, board, step_id, context)
        if not any(answered(f, board)):  # a gap: one more search, told the first found nothing
            board.log("research_hive", "gap", f"not answered yet: {q}")
            f2, it2, c2, n2 = one(q, board, step_id, context, note="An earlier search found nothing that answers this: "
                                                                   "use other sources or other words.")
            f, it, n = f + f2, it + it2, n + n2
            c = {**c, **c2}
        facts += f
        items += it
        corpus.update(c)
        notes += n
    ok = answered(facts, board)
    open_qs = [q for q in qs if not any(a for x, a in zip(facts, ok) if x.get("question") == q)]
    clash = conflicts(facts, board)
    for a, b in clash:
        board.log("research_hive", "conflict", f"{a['claim'][:80]} [{a.get('url')}] vs {b['claim'][:80]} [{b.get('url')}]")
    lines = []
    for q in qs:
        got = [x for x in facts if x.get("question") == q]
        lines.append(f"{q}\n" + ("\n".join(f"- {x['claim']}" for x in got[:5]) if got else "- (nothing found)"))
    if clash:
        lines.append("Sources disagree:\n" + "\n".join(f"- {a['claim']} ({a.get('url')}) / {b['claim']} ({b.get('url')})"
                                                       for a, b in clash))
    if open_qs:
        lines.append("Not answered by any source read: " + "; ".join(open_qs))
    board.log("research_hive", "done", json.dumps({"sub_questions": len(qs), "facts": len(facts), "open": len(open_qs),
                                                   "conflicts": len(clash)}))
    return {"summary": "\n\n".join(lines)[:3000], "items": list(dict.fromkeys(items)), "facts": facts,
            "corpus": corpus, "notes": notes, "sub_questions": qs, "open_questions": open_qs}
