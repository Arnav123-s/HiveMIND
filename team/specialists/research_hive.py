"""The research hive: a question too big for one look-up is worked by many small specialists at once.

    decomposer (4B member)     the question -> 2 to 4 sub-questions that together answer it
    per sub-question:
      planner (4B member)      sources and short queries (the researcher's planner)
      relevance cells          one call per search result: is it about the sub-question? (result_relevant)
      reader + condenser       the pages of the kept results, cut to the lines that matter
      extractor (4B member)    claims with exact quotes (the researcher's extractor)
    or, for a sub-question answered by an experiment or by math:
      coder (7B member)        a program that tests, measures, simulates or derives it; its RESULT lines are claims
                               whose evidence is the program's own output
    gap finder cells           does any claim answer the sub-question? (answers_q) -> one more search for each gap
    cross-check cells          two sources on the same point: agree, conflict or unrelated? (claims_agree)
The verifier then checks every claim against its quote, as for any research step. A cell takes its job only where
it measured at least as well as what did the job before (cells/wins.json); otherwise the code fallback runs.
Returns the researcher's result shape, so the verifier and writer need nothing new.
"""
import json
import re
from pathlib import Path

from .. import llm
from ..cells import use
from . import researcher

BROAD = re.compile(r"\b(research|investigate|overview|survey|state of the art|landscape|in depth|in-depth|deep dive|"
                   r"pros and cons|advantages and disadvantages|compare|comparison|explain (how|why)|how does|why does|"
                   r"what is known|everything about|end[- ]to[- ]end|experiment\w*|test whether|measure whether|simulat\w+|"
                   r"prove|derive|hypothes\w+|scientific\w*)\b", re.I)
DECOMPOSE = """You lead research for Arnav's team. Split the QUESTION into 2 to 4 sub-questions that together answer it,
and say how each is answered:
- "read": from sources (papers, articles, docs): a fact, a definition, what is known, a comparison point
- "experiment": by running a program on this computer: timing or testing code, an algorithm, a simulation from
  numbers he gave, analysing data he gave. Never for the physical world (batteries, telescopes, the body, the
  climate): what is known about it is "read" from studies
- "math": by computing or deriving: an exact calculation, a formula, a proof check, solving equations
Each sub-question asks about the subject itself, never about what Arnav asked. Keep his names and terms exactly.
Reply with JSON only:
{"questions": [{"q": "...", "how": "read"}, {"q": "...", "how": "experiment"}]}"""
EXPERIMENT = """Answer this research sub-question by running a program, not from memory:
{q}
Write one complete Python program that does the experiment or the computation (numpy, sympy, pandas, networkx and
matplotlib are available; use a fixed random seed). Print the method in one line starting 'METHOD: ', then every
result it measured or derived on its own line starting 'RESULT: ' (what was measured = the value, with units)."""
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
    w, names = words(q), subjects(q)
    # a result that names what the question is about counts: "Compare the speed of SQLite and DuckDB for analytics on
    # a laptop" has six content words, so Wikipedia's SQLite article (one of them) was dropped with every other result
    return [not w or bool(names & words(t)) or len(w & words(t)) / len(w) >= 0.5 for t in texts]


def subjects(q):
    """The names in a question (SQLite, DuckDB, GPT-2, Webb): capitalised words after its first, or words with digits
    or inner capitals."""
    toks = re.findall(r"[A-Za-z][\w.+-]*", q or "")
    out = {t for i, t in enumerate(toks) if (i > 0 and t[0].isupper()) or re.search(r"\d|[a-z][A-Z]", t)}
    return {t.lower().strip(".") for t in out} - STOP - {"arnav", "i"}


def answered(facts, board=None):
    """For each fact: does it answer its own sub-question? The answers_q cell (all at once), else any fact counts."""
    if not facts:
        return []
    if use.on("answers_q"):
        yes = [a == "yes" for a in use.ask_all("answers_q", [f"QUESTION: {f['question']}\nFACT: {f['claim']}"
                                                             for f in facts], board)]
        if len(facts) >= 4 and len(set(yes)) == 1:
            # the same answer for every fact of a batch is how this cell fails on real text: it said "no" to all 11
            # facts of the battery question, "SEI growth ... is a degradation mechanism" against "How do lithium-ion
            # batteries degrade?" among them (it scored 0.933 on its synthetic test set). The researcher checks it.
            member = member_answers(facts)
            if member is not None:
                if board is not None:
                    board.log("research_hive", "second-opinion", f"answers_q said {'yes' if yes[0] else 'no'} to all "
                                                                 f"{len(facts)} facts; the researcher: {sum(member)} yes")
                return member
        return yes
    return [True] * len(facts)


ANSWERS = """For each numbered FACT, say whether it answers its QUESTION, fully or in part: a cause, a mechanism, a
value or a finding the question asks about counts; a fact about something else does not.
Reply with JSON only: {"answers": ["yes", "no", ...]}, one entry per fact, in order."""


def member_answers(facts):
    """The researcher's own yes/no for each fact (one call for the batch), or None if its reply cannot be read."""
    body = "\n".join(f"{i + 1}. QUESTION: {f['question']}\n   FACT: {f['claim']}" for i, f in enumerate(facts[:24]))
    data, _ = llm.chat_json("researcher", [{"role": "system", "content": ANSWERS},
                                           {"role": "user", "content": body}], max_new_tokens=220)
    a = data.get("answers") if isinstance(data, dict) else None
    if not isinstance(a, list) or len(a) < min(len(facts), 24):
        return None
    out = [str(x).strip().lower().startswith("y") for x in a[:len(facts)]]
    return out + [False] * (len(facts) - len(out))


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
    """[(sub-question, how)], how = read | experiment | math."""
    data, _ = llm.chat_json("researcher", [{"role": "system", "content": DECOMPOSE},
                                           {"role": "user", "content": f"QUESTION: {task}"}], max_new_tokens=350)
    raw = (data or {}).get("questions", []) if isinstance(data, dict) else []
    qs, seen = [], set()
    for x in raw:
        q, how = (x.get("q"), x.get("how")) if isinstance(x, dict) else (x, "read")
        q = str(q or "").strip()
        if q and q not in seen:
            seen.add(q)
            qs.append((q, how if how in ("read", "experiment", "math") else "read"))
    qs = qs[:4]
    if not RUNNABLE.search(task):
        # checked in code: the 4B called "What factors slow the degradation of lithium-ion batteries?" an experiment
        # although the prompt says never for the physical world; a program would invent a battery model, and its
        # printed numbers would count as verified results
        moved = [q for q, h in qs if h != "read"]
        qs = [(q, "read") for q, _ in qs]
        if moved:
            board.log("research_hive", "read", f"nothing in his question can be run here; read from studies: {moved[0][:80]}")
    board.log("research_hive", "decompose", " | ".join(f"[{h}] {q}" for q, h in qs) or "no sub-questions: the question as one")
    return qs or [(task, "read")]


# a question a program on this computer can answer: he asks for a test, a measurement or a computation, or it is about
# code, algorithms, maths or data he gave
RUNNABLE = re.compile(r"\b(experiment\w*|test whether|measur\w*|benchmark\w*|simulat\w*|run (?:a|an|the|it)|time (?:it|them)|"
                      r"faster|slower|algorithm\w*|code|program\w*|python|function|sort\w*|dataset|data he gave|prove|"
                      r"derive|calculat\w*|comput\w*|equation\w*|formula\w*|probabilit\w*|\d+\s*(?:%|x|times))\b", re.I)


def experiment(q, board, step_id, guard, work):
    """A sub-question answered by a program the coder writes and runs. Its RESULT lines become claims whose quote is
    the program's own output (the verifier checks each against that output; the jury sees the program)."""
    from . import coder
    res = coder.run(EXPERIMENT.format(q=q), "", board, f"{step_id}_exp{abs(hash(q)) % 1000}", guard, work)
    out = res.get("summary", "") if res.get("returncode") == 0 else ""
    src = f"experiment:{Path(res.get('code_path', 'program.py')).name}"
    code = Path(res["code_path"]).read_text(errors="replace")[:4000] if res.get("code_path") and \
        Path(res["code_path"]).exists() else ""
    facts = [{"claim": ln.split("RESULT:", 1)[1].strip(), "quote": ln.strip(), "url": src, "question": q}
             for ln in out.splitlines() if ln.strip().startswith("RESULT:") and ln.split("RESULT:", 1)[1].strip()]
    method = next((ln.split("METHOD:", 1)[1].strip() for ln in out.splitlines() if ln.strip().startswith("METHOD:")), "")
    board.log("research_hive", "experiment", f"{q[:80]}: {len(facts)} result(s)"
              + (f"; method: {method[:120]}" if method else "") + ("" if res.get("returncode") == 0 else " (program failed)"))
    corpus = {src: out + (f"\n\nPROGRAM:\n{code}" if code else "")} if out else {}
    notes = [] if out else [f"experiment for '{q[:80]}' failed: {str(res.get('stderr', ''))[-200:]}"]
    return facts, ([f"Method ({q[:60]}): {method}"] if method else []), corpus, notes


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


WRAPPER = re.compile(r"^.{0,80}?\bwhat Arnav asked:\s*", re.I | re.S)


def run(task, context, board, step_id, guard=None, work=None):
    # the question itself, not the step's wrapper: handed "Find, with quotes from sources, what Arnav asked: Research how
    # ...", the decomposer made "What did Arnav ask about lithium-ion battery degradation?" a sub-question, and the
    # relevance filter then rejected every Wikipedia result against it
    task = WRAPPER.sub("", task or "", count=1)
    plan = decompose(task, board)
    qs = [q for q, _ in plan]
    facts, items, corpus, notes = [], [], {}, []
    for q, how in plan:
        if how in ("experiment", "math") and guard is not None and work is not None:
            f, it, c, n = experiment(q, board, step_id, guard, work)
            facts, items, notes = facts + f, items + it, notes + n
            corpus.update(c)
            continue
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
