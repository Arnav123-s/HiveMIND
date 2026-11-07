"""Writer: assembles the finished deliverable from verified results only."""
from .. import llm, memory, prompts


def messages(goal, task, results_text, sources):
    src = "\n".join(f"[{i + 1}] {u}" for i, u in enumerate(sources)) or "(none)"
    prof = memory.profile()
    if prof:
        task = f"{task}\nArnav's preferences:\n{prof}"
    return [{"role": "system", "content": prompts.WRITER},
            {"role": "user", "content": f"ARNAV'S TASK: {goal}\nYOUR STEP: {task}\n\nVERIFIED RESULTS:\n{results_text}"
                                        f"\n\nSOURCES:\n{src}"}]


def run(goal, task, board, needs):
    facts = [f for f in board.facts(status="supported")]
    sources = list(dict.fromkeys(f["url"] for f in facts if f["url"].startswith("http")))
    results_text = board.context_for(needs or [s["id"] for s in board.steps() if s["agent"] != "writer"],
                                     max_chars=7000)
    text = llm.chat("writer", messages(goal, task, results_text, sources), max_new_tokens=1200)
    failed = [s for s in board.steps() if s["agent"] != "writer" and s.get("verdict") not in ("PASS", None)]
    if failed:
        text += "\n\n## Not confirmed by the team\n" + "\n".join(
            f"- {s['id']} ({s['agent']}): {s['task'][:150]} - {s.get('feedback') or s.get('verdict')}" for s in failed)
    if sources:
        text += "\n\n## Sources\n" + "\n".join(f"[{i + 1}] {u}" for i, u in enumerate(sources))
    return {"summary": text, "sources": sources}
