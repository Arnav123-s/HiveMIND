"""Writer: assembles the finished deliverable from verified results only."""
import re

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
    # the deliverable is built from everything the team verified, not only the steps the plan wired in
    top = [s["id"] for s in board.steps() if s["agent"] != "writer" and "[" not in s["id"] and not s["id"].endswith("r")]
    results_text = board.context_for(list(dict.fromkeys(top + list(needs or []))), max_chars=7000)
    dropped = re.findall(r"Dropped by the team's checks \(do not use\): ([^\n]+)", results_text)
    if dropped:
        task = f"{task}\nNever include these, they failed the checks: {'; '.join(dropped)}"
    msgs = messages(goal, task, results_text, sources)
    text = llm.chat("writer", msgs, max_new_tokens=1200)
    # the critic checks every claim against the verified results; the writer fixes what it flags (one round)
    todo = "\n".join(f"- {i}" for i in getattr(board, "checklist", []))
    data, _ = llm.chat_json("critic", [{"role": "system", "content": prompts.CRITIC},
                                       {"role": "user", "content": f"INSTRUCTIONS:\n{todo}\n\nVERIFIED RESULTS:\n{results_text}"
                                                                   f"\n\nREPORT:\n{text}"}],
                            max_new_tokens=700)
    checklist = [c for c in (data or {}).get("checklist", []) if isinstance(c, dict)] if isinstance(data, dict) else []
    unordered = [str(x) for x in (data or {}).get("unordered", [])] if isinstance(data, dict) else []
    flagged = [str(x) for x in (data or {}).get("unsupported", [])] if isinstance(data, dict) else []
    honest = re.compile(r"could not|couldn't|not (be )?(confirmed|determined|verified|found)|unable|unknown|no data", re.I)
    flagged = [f for f in flagged if not honest.search(f)]  # saying what is unknown is never an unsupported claim
    if flagged:
        board.log("critic", "flag", f"{len(flagged)} unsupported claim(s): " + " | ".join(f[:80] for f in flagged[:3]))
        text = llm.chat("writer", msgs + [{"role": "assistant", "content": text},
                                          {"role": "user", "content": "These sentences are not supported by the verified "
                                           "results. Remove or correct them and return the whole report:\n- "
                                           + "\n- ".join(flagged[:10])}], max_new_tokens=1200)
    else:
        board.log("critic", "ok", "every claim matches the verified results")
    if checklist:
        done = sum(bool(c.get("done")) for c in checklist)
        board.log("critic", "checklist", f"{done}/{len(checklist)} of your instructions done")
        text += "\n\n## Your instructions\n" + "\n".join(
            f"- {'✅' if c.get('done') else '❌'} {c.get('instruction', '')}" + ("" if c.get("done") else f" - {c.get('why', '')}")
            for c in checklist)
    if unordered:
        board.log("critic", "unordered", " | ".join(unordered)[:300])
        text += "\n\n## Done without your order (flagged)\n" + "\n".join(f"- {u}" for u in unordered)
    failed = [s for s in board.steps() if s["agent"] != "writer" and s.get("verdict") not in ("PASS", "REROUTED", None)]
    if failed:
        text += "\n\n## Not confirmed by the team\n" + "\n".join(
            f"- {s['id']} ({s['agent']}): {s['task'][:150]} - {s.get('feedback') or s.get('verdict')}" for s in failed)
    if sources:
        text += "\n\n## Sources\n" + "\n".join(f"[{i + 1}] {u}" for i, u in enumerate(sources))
    return {"summary": text, "sources": sources}
