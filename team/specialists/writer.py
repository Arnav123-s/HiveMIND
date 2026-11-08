"""Writer: assembles the finished deliverable from verified results only."""
import re
from pathlib import Path

from .. import llm, memory, prompts


def messages(goal, task, results_text, sources):
    src = "\n".join(f"[{i + 1}] {u}" for i, u in enumerate(sources)) or "(none)"
    prof = memory.profile()
    if prof:
        task = f"{task}\nArnav's preferences:\n{prof}"
    return [{"role": "system", "content": prompts.WRITER},
            {"role": "user", "content": f"ARNAV'S TASK: {goal}\nYOUR STEP: {task}\n\nVERIFIED RESULTS:\n{results_text}"
                                        f"\n\nSOURCES:\n{src}"}]


NUM = re.compile(r"(?<![\w/.-])\d+(?:[.,]\d+)*(?:\s*/\s*\d+)?")


def _plain(x):
    """Without spaces or thousands separators: 3,905,849 and 3 905 849 are 3905849."""
    return re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", x).replace(" ", "")


def ground_numbers(text, verified):
    """Every number in the report must appear in the verified results; lines with unverified numbers are struck."""
    ok, struck = [], []
    plain = _plain(verified)  # "3,905,849" in the report is the "3905849" a source gave
    for line in text.split("\n"):
        nums = [n for n in NUM.findall(line) if not re.fullmatch(r"\d", n)]  # [1]-style citations / single digits
        if line.startswith("##") or line.lstrip().startswith("[") or all(_plain(n) in plain for n in nums):
            ok.append(line)
        else:
            struck.append(line.strip())
    return "\n".join(ok), struck


WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_N = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"


def _n(m):
    g = m.group(1)
    return int(g) if g.isdigit() else WORDS[g]


def ordered_format(instructions):
    """The layout Arnav ordered in his own words ("a two-line summary", "in 3 sentences", "no table"): (one line for the
    writer, number of lines or None). The writer's edit learned reports that lead with an answer and a table; told
    "give me a two-line summary" it still wrote a table, told "exactly 2 lines of plain text" it wrote 2 lines."""
    text = " ".join(instructions).lower()
    out, lines = [], None
    # only a layout for the deliverable: "fix the two lines of code" is not one
    kind = r" (?:summary|answer|report|reply|overview|description|explanation|version)\b"
    m = re.search(_N + r"[- ]lines?" + kind, text) or re.search(r"\b(?:in|within|as) " + _N + r" lines?\b", text)
    if m:
        lines = _n(m)
        out.append(f"exactly {lines} line{'s' if lines != 1 else ''} of plain text, no table, no headings, no other sections")
    m = re.search(_N + r"[- ]sentences?" + kind, text) or re.search(r"\b(?:in|within|as) " + _N + r" sentences?\b", text)
    if m:
        out.append(f"exactly {_n(m)} sentence{'s' if _n(m) != 1 else ''}, no table, no headings")
    m = re.search(_N + r" bullet(?: point)?s?\b", text)
    if m:
        out.append(f"exactly {_n(m)} bullet points")
    m = re.search(r"\b(?:in|under|at most|max(?:imum)?|no more than) " + _N + r" words\b", text)
    if m:
        out.append(f"at most {_n(m)} words")
    if re.search(r"\bno tables?\b|\bwithout (?:a )?tables?\b", text):
        out.append("no table")
    elif re.search(r"\btable\b", text) and lines is None:
        out.append("include a table")
    return "; ".join(out), lines


def body_lines(text):
    return [ln for ln in text.split("\n") if ln.strip()]


EMPTY_NOT_CONFIRMED = re.compile(r"^\s*(?:#+\s*)?\**not confirmed\**[.:]?\**\s*$", re.I)


def drop_empty_sections(text):
    """A "Not confirmed" heading with nothing under it (the writer adds one even when everything was confirmed)."""
    lines = text.split("\n")
    out = []
    for i, ln in enumerate(lines):
        if EMPTY_NOT_CONFIRMED.match(ln):
            rest = [x for x in lines[i + 1:] if x.strip()]
            if not rest or rest[0].lstrip().startswith("#"):
                continue
        out.append(ln)
    return "\n".join(out).strip()


HONEST = re.compile(r"could not|couldn't|not (be )?(confirmed|determined|verified|found|accessible|available)"
                    r"|inaccessible|unavailable|unable|unknown|no data", re.I)


def critique(todo, results_text, text):
    """The critic's reading of a report: (checklist, unordered, unsupported sentences)."""
    data, _ = llm.chat_json("critic", [{"role": "system", "content": prompts.CRITIC},
                                       {"role": "user", "content": f"INSTRUCTIONS:\n{todo}\n\nVERIFIED RESULTS:\n{results_text}"
                                                                   f"\n\nREPORT:\n{text}"}],
                            max_new_tokens=700)
    if not isinstance(data, dict):
        return [], [], []
    checklist = [c for c in data.get("checklist", []) if isinstance(c, dict)]
    unordered = [str(x) for x in data.get("unordered", [])]
    flagged = [str(x) for x in data.get("unsupported", [])]
    return checklist, unordered, [f for f in flagged if not HONEST.search(f)]  # saying what is unknown is never unsupported


def run(goal, task, board, needs):
    facts = [f for f in board.facts(status="supported")]
    sources = list(dict.fromkeys(f["url"] for f in facts if f["url"].startswith("http")))
    # the deliverable is built from everything the team verified, not only the steps the plan wired in
    top = [s["id"] for s in board.steps() if s["agent"] != "writer" and "[" not in s["id"] and not s["id"].endswith("r")]
    results_text = board.context_for(list(dict.fromkeys(top + list(needs or []))), max_chars=7000)
    if not top and not needs:  # nothing to look up: translate, rewrite, summarise or fix his text, draft a message
        results_text = f"(No research was needed: Arnav's own words are the source for this task.)\n{goal}"
        ctx = getattr(board, "context", "")
        if ctx:  # "make it shorter": the text to work on is in the conversation
            results_text += f"\n\nEarlier in this conversation:\n{ctx[:4000]}"
    if nothing_verified(goal, board, facts):
        # every step that looked something up failed, and his own words hold nothing to work from: a writer here
        # listed the papers the verifier had rejected and gave each one today's date
        board.log("writer", "nothing-verified", "no step was verified: reporting that, with no answer")
        checklist = [{"instruction": i, "done": False, "why": "not confirmed by the team"}
                     for i in (getattr(board, "checklist", None) or [goal])]
        return finish(NOTHING_VERIFIED, board, results_text, sources, checklist, [], [], [])
    dropped = re.findall(r"Dropped by the team's checks \(do not use\): ([^\n]+)", results_text)
    if dropped:
        task = f"{task}\nNever include these, they failed the checks: {'; '.join(dropped)}"
    fmt, n_lines = ordered_format(getattr(board, "checklist", None) or [goal])
    if fmt:
        task = f"{task}\nFORMAT Arnav ordered: {fmt}. This overrides the usual layout."
        board.log("writer", "format", fmt)
    msgs = messages(goal, task, results_text, sources)
    text = drop_empty_sections(llm.chat("writer", msgs, max_new_tokens=1200))
    if n_lines and len(body_lines(text)) != n_lines:  # checked in code: one more try, told what was wrong
        board.log("writer", "format", f"wrote {len(body_lines(text))} lines, {n_lines} ordered: asking again")
        text = llm.chat("writer", msgs + [{"role": "assistant", "content": text},
                                          {"role": "user", "content": f"That is {len(body_lines(text))} lines. Write it as "
                                           f"exactly {n_lines} lines of plain text, nothing else."}], max_new_tokens=400)
    # the critic checks every claim against the verified results and every instruction of Arnav's; the writer fixes
    # what it flags or finds missing (one round), and the critic checks the fixed report, so the ticks are about it
    todo = "\n".join(f"- {i}" for i in getattr(board, "checklist", []))
    checklist, unordered, flagged = critique(todo, results_text, text)
    missed = [c for c in checklist if not c.get("done")]
    fixes = []
    if flagged:
        board.log("critic", "flag", f"{len(flagged)} unsupported claim(s): " + " | ".join(f[:80] for f in flagged[:3]))
        fixes.append("These sentences are not supported by the verified results. Remove or correct them:\n- "
                     + "\n- ".join(flagged[:10]))
    if missed:
        board.log("critic", "missed", f"{len(missed)} of your instructions not met: "
                  + " | ".join(str(c.get("instruction", ""))[:80] for c in missed[:3]))
        # only his words: a small writer given the critic's reason copies the reason into the report
        fixes.append("Arnav asked for these and your report does not do them yet:\n- "
                     + "\n- ".join(str(c.get("instruction", "")) for c in missed[:10])
                     + "\nRewrite the report so it does each of them, using only the verified results. If the verified "
                       "results are not enough for one, write one line saying what is missing.")
    if fixes:
        text = llm.chat("writer", msgs + [{"role": "assistant", "content": text},
                                          {"role": "user", "content": "\n\n".join(fixes) + "\n\nReturn only the whole "
                                                                      "corrected report."}],
                        max_new_tokens=1200)
        again, unordered2, flagged = critique(todo, results_text, text)
        if again:  # no answer from the critic: keep the first ticks (they can only under-claim what was done)
            checklist, unordered = again, unordered2
        if flagged:
            board.log("critic", "flag", f"{len(flagged)} unsupported claim(s) after the fix: " + " | ".join(f[:80] for f in flagged[:3]))
        missed = [c for c in checklist if not c.get("done")]
        if flagged or missed:
            # escalate: the small writer could not fix it (it translated "Friday" as "mercredi" twice); a bigger
            # member rewrites once, the critic checks again, and the version with fewer problems is kept
            board.log("editor", "escalate", f"{len(flagged)} unsupported, {len(missed)} not done after the writer's fix")
            asks = (["These sentences are not supported by the verified results or are wrong:\n- " + "\n- ".join(flagged[:10])]
                    if flagged else []) + (["Arnav asked for these and the report does not do them yet:\n- "
                                            + "\n- ".join(str(c.get("instruction", "")) for c in missed[:10])] if missed else [])
            text2 = llm.chat("editor", msgs + [{"role": "assistant", "content": text},
                                               {"role": "user", "content": "\n\n".join(asks) + "\n\nReturn only the whole "
                                                                           "corrected report."}], max_new_tokens=1200)
            c2, u2, f2 = critique(todo, results_text, text2)
            if c2 and len(f2) + sum(not c.get("done") for c in c2) < len(flagged) + len(missed):
                board.log("editor", "kept", "the editor's version has fewer problems")
                text, checklist, unordered, flagged = text2, c2, u2, f2
            else:
                board.log("editor", "dropped", "the editor's version was not better")
    else:
        board.log("critic", "ok", "every claim matches the verified results")
    return finish(text, board, results_text, sources, checklist, unordered, flagged, fixes)


NOTHING_VERIFIED = ("The team could not confirm an answer to this, so none is given: every step that looked it up was "
                    "rejected by the checks. What was tried and why it failed is listed below.")


def nothing_verified(goal, board, facts):
    """Every step that ran before the writer failed, no fact was verified, and the task hands over no text."""
    from ..guard import split_material
    ran = [s for s in board.steps() if s["agent"] != "writer" and s.get("verdict")]
    return bool(ran) and not facts and not split_material(goal)[1] \
        and all(s["verdict"] not in ("PASS", "REROUTED") for s in ran)


def finish(text, board, results_text, sources, checklist, unordered, flagged, fixes):
    """The report's checked tail: numbers grounded, flags, the checklist, what failed, the sources."""
    saved = [Path(a["path"]) for a in board.artifacts() if a.get("kind") == "file"]
    text = fix_images(drop_empty_sections(text), saved)
    text, struck = ground_numbers(text, results_text + "\n" + "\n".join(sources))
    if struck:
        board.log("critic", "strike", f"{len(struck)} line(s) with numbers not in the verified results removed")
        text += "\n\n## Removed: numbers the team could not verify\n" + "\n".join(f"- {x[:160]}" for x in struck)
    if fixes and flagged:
        text += "\n\n## Not backed by the verified results (flagged by the critic)\n" + "\n".join(f"- {x[:160]}" for x in flagged)
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
    if saved:
        text += "\n\n## Files\n" + "\n".join(f"- work/{p.name}" for p in dict.fromkeys(saved))
    if sources:
        text += "\n\n## Sources\n" + "\n".join(f"[{i + 1}] {u}" for i, u in enumerate(sources))
    return {"summary": text, "sources": sources}


IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]*)\)")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


def fix_images(text, saved):
    """An image in the report shows a file the team saved, or nothing: the writer linked a chart to a Hugging Face
    API page. A link to a saved file is kept (as work/<name>); any other image link points to the saved image (if
    there is exactly one) or is removed."""
    images = [p for p in saved if p.suffix.lower() in IMAGE_EXT]

    def one(m):
        target = Path(m.group(2).split("?")[0]).name
        if any(p.name == target for p in images):
            return f"![{m.group(1)}](work/{target})"
        return f"![{m.group(1)}](work/{images[0].name})" if len(images) == 1 else ""
    return IMG.sub(one, text)
