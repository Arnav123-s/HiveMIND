"""The small reader: sources read in small parts, one small job per call.

The researcher on the 4B reads up to 9000 characters in one call and writes summary, items and facts together. A
1.7B does not hold that job (training/reports/hive_bench/small_only_notes.md). Cut up, it does much of it
(training/reports/chunk_read.json):
  1. the sources are cut at line ends into parts of PART characters, each under the header of its source
  2. each part is read in its own call: only the facts the task needs, each with an exact quote
  3. the source of a fact is filled in by code from the part it was read in, not by the model
  4. a last short call writes the summary and the list the task asks for, from the facts alone
Used by the researcher when AGENT_TEAM_SMALL=1 (team/config.py).
"""
import re

from .. import llm

PART = 1800
# No example value stands in this instruction. It used to say ("X has 0.135B parameters"): asked for download counts,
# with "downloads 3597908" in front of it, the 1.7B returned parameter counts, once the example's own 0.135B for a
# model that has 2.032B; asked for a licence and a parameter count it returned the parameter count alone.
EXTRACT = """You read ONE PART of a source for Arnav's team and pull out the facts the TASK asks for.
Reply with JSON only: {"facts":[{"claim":"...","quote":"..."}]}
- First read the TASK: which things does it ask for (a licence, a number of downloads, a date, a price, a name)? \
Take a fact for each of those things that this part states, and not other values that stand next to them.
- claim: one full sentence that names the thing and gives the value this part states for it, never a bare label.
- quote: the words copied exactly, character for character, from the part. Never invent or reword a quote.
- At most 4 facts. {"facts":[]} if this part states nothing the task asks for."""
COMPOSE = """You answer Arnav's TASK from the FACTS his team found. Use only the facts.
Reply with JSON only: {"summary":"2-4 sentences answering the task","items":["..."]}
- items: the list the task asks for (names, ids, titles), best first; [] if the task asks for no list.
- If the facts do not answer the task, say so in summary."""


def chunks(sources, size=PART):
    """Cut at line ends; every part starts with the header of the source its lines come from."""
    out, cur, head = [], "", ""
    for line in sources.split("\n"):
        if line.startswith("### Source:"):
            head = line
        while len(line) > size:  # one very long line: cut it at a space
            cut = line.rfind(" ", 0, size)
            cut = cut if cut > size // 2 else size
            out.append((head + "\n" if head and not line.startswith("###") else "") + line[:cut])
            line = line[cut:]
        if cur and len(cur) + len(line) + 1 > size:
            out.append(cur)
            cur = head + "\n" if head and line != head else ""
        cur += line + "\n"
    if cur.strip():
        out.append(cur)
    return [c for c in out if c.strip() and c.strip() != head]


def source_of(part, quote):
    """The url a quote was read at: the link on its own line of a search listing, else the part's source."""
    for line in part.split("\n"):
        if quote and quote[:60] in line:
            m = re.search(r"\|\s*(https?://\S+)\s*\|", line)
            if m:
                return m.group(1)
    m = re.search(r"^### Source:\s*(\S+)", part, re.M)
    return m.group(1) if m else ""


def _norm(s):
    return re.sub(r"\s+", " ", str(s).lower()).strip()


def read(task_head, sources, member="researcher", size=PART):
    """Facts from every part: [{"claim", "quote", "url"}], each quote once."""
    facts = []
    for part in chunks(sources, size):
        data, _ = llm.chat_json(member, [{"role": "system", "content": EXTRACT},
                                         {"role": "user", "content": f"{task_head}\n\nPART:\n{part}"}],
                                max_new_tokens=500, adapter=False)
        for f in (data.get("facts") if isinstance(data, dict) else None) or []:
            if not (isinstance(f, dict) and f.get("claim") and f.get("quote")):
                continue
            if any(_norm(f["quote"]) == _norm(g["quote"]) and _norm(f["claim"]) == _norm(g["claim"]) for g in facts):
                continue
            facts.append({"claim": str(f["claim"]), "quote": str(f["quote"]), "url": source_of(part, str(f["quote"]))})
    return facts


def compose(task_head, facts, member="researcher"):
    """Summary and items from the facts alone (a short input: the model never sees the pages again)."""
    if not facts:
        return "The sources read do not answer the task.", []
    listing = "\n".join(f"- {f['claim']} (source: {f['url']})" for f in facts[:24])
    data, raw = llm.chat_json(member, [{"role": "system", "content": COMPOSE},
                                       {"role": "user", "content": f"{task_head}\n\nFACTS:\n{listing}"}],
                              max_new_tokens=400, adapter=False)
    if not isinstance(data, dict):
        return raw[:500], []
    return str(data.get("summary", "")), [str(i) for i in (data.get("items") or []) if str(i).strip()]
