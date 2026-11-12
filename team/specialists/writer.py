"""Writer: assembles the finished deliverable from verified results only."""
import re
from pathlib import Path

from .. import llm, memory, prompts


def messages(goal, task, results_text, sources):
    src = "\n".join(f"[{i + 1}] {u}" for i, u in enumerate(sources)) or "(none)"
    prof = memory.profile()
    if prof:
        task = f"{task}\nArnav's preferences:\n{prof}"
    if results_text.startswith(OWN_TEXT):  # his text is the material: do what he says to it
        return [{"role": "system", "content": prompts.WRITER_TEXT},
                {"role": "user", "content": f"ARNAV'S ORDER AND HIS TEXT: {goal}\nYOUR STEP: {task}"
                                            + results_text[len(OWN_TEXT):].replace(goal, "", 1).rstrip()}]
    return [{"role": "system", "content": prompts.WRITER},
            {"role": "user", "content": f"ARNAV'S TASK: {goal}\nYOUR STEP: {task}\n\nVERIFIED RESULTS:\n{results_text}"
                                        f"\n\nSOURCES:\n{src}"}]


OWN_TEXT = "(No research was needed: Arnav's own words are the source for this task.)"


NUM = re.compile(r"(?<![\w/.-])\d+(?:[.,]\d+)*(?:\s*/\s*\d+)?")


def _plain(x):
    """Without spaces or thousands separators: 3,905,849 and 3 905 849 are 3905849."""
    return re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", x).replace(" ", "")


def _value(x):
    try:
        return float(_plain(x))
    except ValueError:
        return None


def ground_numbers(text, verified):
    """Every number in the report must appear in the verified results; lines with unverified numbers are struck.
    A number counts by its value too: '$161.00' is the calculator's 161.0 (held-out set 2: the right discount was
    struck because the strings differed)."""
    ok, struck = [], []
    plain = _plain(verified)  # "3,905,849" in the report is the "3905849" a source gave
    values = {v for v in (_value(n) for n in NUM.findall(verified)) if v is not None}
    for line in text.split("\n"):
        nums = [n for n in NUM.findall(line) if not re.fullmatch(r"\d", n)]  # [1]-style citations / single digits
        if line.startswith("##") or line.lstrip().startswith("[") or all(
                _plain(n) in plain or _value(n) in values for n in nums):
            ok.append(line)
        else:
            struck.append(line.strip())
    return "\n".join(ok), struck


WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_N = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"


def _n(m):
    g = m.group(1)
    return int(g) if g.isdigit() else WORDS[g]


def order_words(instruction):
    """His order without the text he handed over: "the apples that was on the table" asked for no table."""
    from ..guard import split_material
    order = split_material(instruction)[0]
    return re.sub(r"'[^']{2,}'|\"[^\"]{2,}\"|“[^”]{2,}”|‘[^’]{2,}’|\(the text he gave\)", " ", order)


def ordered_format(instructions):
    """The layout Arnav ordered in his own words ("a two-line summary", "in 3 sentences", "no table"): (one line for the
    writer, number of lines or None). The writer's edit learned reports that lead with an answer and a table; told
    "give me a two-line summary" it still wrote a table, told "exactly 2 lines of plain text" it wrote 2 lines."""
    text = " ".join(order_words(i) for i in instructions).lower()
    out, lines = [], None
    # only a layout for the deliverable: "fix the two lines of code" is not one
    kind = (r" (?:summary|answer|report|reply|overview|description|explanation|version|email|e-mail|message|letter|note|"
            r"paragraph|response|introduction|intro|bio|post|update|reminder|announcement|story|poem)\b")
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
    m = re.search(r"\bonly (?:the |a |an |one )?((?:corrected|fixed|new|final|translated|rewritten|polite|short|shorter)\s+)?"
                  r"(sentence|word|number|answer|text|name|line|email|message|code|list|translation|version)\b", text)
    if m:
        what = (m.group(1) or "") + m.group(2)
        out.append(f"only the {what} itself: nothing before or after it, no heading, no label, no table, no notes")
        if m.group(2) in ("sentence", "word", "number", "name", "line", "translation") and lines is None:
            lines = 1
    m = re.search(r"\b(?:write|draft|compose|send|prepare)\b[^.?!]*?\b(email|e-mail|message|letter|note|reply|poem|post|tweet|"
                  r"announcement|invitation|reminder)\b", text)
    if m and not re.search(r"\btable\b", text):
        # a draft is the text he will send: the writer added a "Details" list and a table repeating the email
        out.append(f"only the {m.group(1)} itself, written out as it would be sent: no table, no notes, no second copy")
    if re.search(r"\bno tables?\b|\bwithout (?:a )?tables?\b", text):
        out.append("no table")
    elif re.search(r"\btable\b", text) and lines is None:
        out.append("include a table")
    return "; ".join(out), lines


def ordered_sentences(instructions):
    """The number of sentences Arnav ordered ("in two sentences", "a three-sentence message"), or None."""
    m = re.search(_N + r"[- ]sentences?\b", " ".join(order_words(i) for i in instructions).lower())
    return _n(m) if m else None


def sentence_count(text):
    body = re.sub(r"\s+", " ", (text or "").split("\n## ")[0]).strip()
    return len([x for x in re.split(r"(?<=[.!?])\s+", body) if re.search(r"\w", x)])


def dedupe_paragraphs(text):
    """A paragraph or line given twice, word for word, once (held-out set 3: the queue explanation came twice, so
    'in two sentences' became four)."""
    out, seen = [], set()
    for para in (text or "").split("\n\n"):
        key = re.sub(r"\s+", " ", para).strip().lower()
        if key and key in seen and not key.startswith("|"):
            continue
        seen.add(key)
        out.append(para)
    lines, prev = [], None
    for ln in "\n\n".join(out).split("\n"):
        if ln.strip() and ln.strip() == prev and not ln.lstrip().startswith("|"):
            continue
        lines.append(ln)
        prev = ln.strip() or prev
    return "\n".join(lines)


def body_lines(text):
    return [ln for ln in text.split("\n") if ln.strip()]


EMPTY_NOT_CONFIRMED = re.compile(r"^\s*(?:#+\s*)?\**not confirmed\**[.:]?\**\s*$", re.I)


def drop_empty_sections(text):
    """A "Not confirmed" heading with nothing under it (the writer adds one even when everything was confirmed), and a
    sources block that only says there are none."""
    # a bare "Not confirmed." sentence that says nothing (the writer ends an answer with it)
    text = re.sub(r"(?m)(?<=[.!?])[ \t]+Not confirmed\.?[ \t]*$|^[ \t]*Not confirmed\.?[ \t]*$", "", text)
    # a sources block that only says there are none (copied from the prompt's "SOURCES: (none)")
    text = re.sub(r"(?im)^\s*(?:\*\*|#+\s*)?sources:?(?:\*\*)?:?\s*\n?\s*\(?none\)?\.?\s*$", "", text)
    lines = text.split("\n")
    out = []
    for i, ln in enumerate(lines):
        if EMPTY_NOT_CONFIRMED.match(ln):
            rest = [x for x in lines[i + 1:] if x.strip()]
            if not rest or rest[0].lstrip().startswith("#"):
                continue
        out.append(ln)
    return "\n".join(out).strip()


SELF_TALK = re.compile(r"^\W*(?:wait\b|hmm+\b|let me\b|let's (?:re)?(?:calculate|check|compute|think|verify|try|see)\b|"
                       r"actually,? (?:no|wait)\b|oops\b|on second thought|i (?:think|need to|will now|made a mistake)\b|"
                       r"this is (?:not|in)correct\b)", re.I)
LABEL_ONLY = re.compile(r"^\s*(?:\*\*[^*]{1,60}:?\*\*:?|#+\s*[^#]{1,60})\s*$")


def drop_self_talk(text):
    """A model thinking aloud is no deliverable: the 1.7B writer looped "**Wait, this is not correct.** Let's
    recalculate." under "Correct Calculation:" headings (the dev set, days, on the final frozen copy). Lines of it go,
    then bold labels and headings left with nothing under them (the report's own "## " sections stay)."""
    lines = [ln for ln in (text or "").split("\n") if not SELF_TALK.search(ln.strip())]
    out = []
    for i, ln in enumerate(lines):
        if LABEL_ONLY.match(ln) and not ln.lstrip().startswith("## "):
            nxt = next((x for x in lines[i + 1:] if x.strip()), "")
            if not nxt or LABEL_ONLY.match(nxt):
                continue
        out.append(ln)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


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
    # a complaint must point at the report: the sentence it flags has to be in it. (With the 1.7B as critic, the flag
    # was the reply format's own placeholder, "exact sentence"; the writer "corrected" a right one-sentence summary
    # into his three sentences again.) The same rule as for facts: no quote, no claim.
    here = _flat(text)
    flagged = [f for f in flagged if len(_flat(f)) >= 12 and _flat(f) in here]
    return checklist, unordered, [f for f in flagged if not HONEST.search(f)]  # saying what is unknown is never unsupported


def _flat(t):
    return re.sub(r"[^a-z0-9]+", " ", str(t).lower()).strip()


def _words(t):
    return set(re.findall(r"[a-z0-9]+", str(t).lower())) - {"the", "a", "an", "of", "to", "and", "in", "on", "for", "me"}


def align_checklist(checklist, instructions):
    """His instructions, as written, each with the critic's verdict on it. The critic added "Provide a table with
    dates, days of the week, and notes" to a one-question task and ticked it: an item matching none of his
    instructions is dropped; an instruction the critic did not check stays not done."""
    if not instructions or not checklist:
        return checklist, []
    out, used = [], set()
    for ins in instructions:
        w = _words(ins)
        best, score = None, 0.0
        for i, c in enumerate(checklist):
            if i in used:
                continue
            cw = _words(c.get("instruction", ""))
            sc = len(w & cw) / max(1, len(w | cw))
            if sc > score:
                best, score = i, sc
        if best is not None and score >= 0.34:
            used.add(best)
            out.append({**checklist[best], "instruction": ins})
        else:
            out.append({"instruction": ins, "done": False, "why": "the critic did not check it"})
    extra = [str(c.get("instruction", "")) for i, c in enumerate(checklist) if i not in used]
    return out, extra


MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
          "december"]
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE_RX = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{_MON},?\s+(\d{{4}})\b|\b{_MON}\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b|"
                     r"\b(\d{4})-(\d{2})-(\d{2})\b", re.I)
DAY_RX = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)


def _date(m):
    import datetime
    g = m.groups()
    try:
        if g[0]:
            return datetime.date(int(g[2]), [x[:3] for x in MONTHS].index(g[1][:3].lower()) + 1, int(g[0]))
        if g[3]:
            return datetime.date(int(g[5]), [x[:3] for x in MONTHS].index(g[3][:3].lower()) + 1, int(g[4]))
        return datetime.date(int(g[6]), int(g[7]), int(g[8]))
    except ValueError:
        return None


def check_weekdays(text):
    """A line that puts a weekday with a date gets the calendar's weekday (a report called 15 January 2026 a Monday; it
    was a Thursday). Pairs in the order they appear when a line has as many dates as weekdays. The calendar is exact,
    so a wrong day is corrected, not struck: striking it left a held-out answer as the bare '6'. Returns (text with
    the days corrected, the lines as they were)."""
    out, wrong = [], []
    for line in text.split("\n"):
        dates = [d for d in (_date(m) for m in DATE_RX.finditer(line)) if d]
        days = list(DAY_RX.finditer(line))
        if line.startswith("##") or not dates or not days or len(dates) != len(days):
            out.append(line)
            continue
        if all(DAYS[d.weekday()] == w.group(1).lower() for d, w in zip(dates, days)):
            out.append(line)
            continue
        wrong.append(line.strip())
        fixed, last = [], 0
        for d, w in zip(dates, days):
            right = DAYS[d.weekday()]
            fixed += [line[last:w.start()], right.capitalize() if w.group(1)[0].isupper() else right]
            last = w.end()
        out.append("".join(fixed) + line[last:])
    return "\n".join(out), wrong


def run(goal, task, board, needs):
    facts = [f for f in board.facts(status="supported")]
    sources = list(dict.fromkeys(f["url"] for f in facts if f["url"].startswith("http")))
    # the deliverable is built from everything the team verified, not only the steps the plan wired in
    top = [s["id"] for s in board.steps() if s["agent"] != "writer" and "[" not in s["id"] and not s["id"].endswith("r")]
    results_text = board.context_for(list(dict.fromkeys(top + list(needs or []))), max_chars=7000)
    if not top and not needs:  # nothing to look up: translate, rewrite, summarise or fix his text, draft a message
        results_text = f"{OWN_TEXT}\n{goal}"
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
    role = translator_role(goal, results_text)
    if role != "writer":
        board.log("writer", "translate", f"a translation: written by the {role} (training/reports/translator.json)")
    text = dedupe_paragraphs(drop_empty_sections(llm.chat(role, msgs, max_new_tokens=1200)))
    n_sent = ordered_sentences(getattr(board, "checklist", None) or [goal])
    text = keep_sentences(text, n_sent, role, msgs, board)
    if n_lines and len(body_lines(text)) != n_lines:  # checked in code: one more try, told what was wrong
        board.log("writer", "format", f"wrote {len(body_lines(text))} lines, {n_lines} ordered: asking again")
        text = llm.chat(role, msgs + [{"role": "assistant", "content": text},
                                          {"role": "user", "content": f"That is {len(body_lines(text))} lines. Write it as "
                                           f"exactly {n_lines} lines of plain text, nothing else."}], max_new_tokens=400)
    # the critic checks every claim against the verified results and every instruction of Arnav's; the writer fixes
    # what it flags or finds missing (one round), and the critic checks the fixed report, so the ticks are about it
    todo = "\n".join(f"- {i}" for i in getattr(board, "checklist", []))
    checklist, unordered, flagged = critique(todo, results_text, text)
    if sources:  # a report built from sources: sentences from memory are flagged in code too
        loose = [x for x in ungrounded(text, results_text + "\n" + goal) if x not in flagged]
        if loose:
            board.log("critic", "ungrounded", f"{len(loose)} sentence(s) share few words with the verified results: "
                      + " | ".join(x[:70] for x in loose[:3]))
            flagged = flagged + loose[:10]
    checklist = mark_echo(goal, text, checklist, board)
    open_qs = open_questions(board)
    checklist = mark_open(checklist, open_qs, board)
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
        text = llm.chat(role, msgs + [{"role": "assistant", "content": text},
                                          {"role": "user", "content": "\n\n".join(fixes) + "\n\nReturn only the whole "
                                                                      "corrected report."}],
                        max_new_tokens=1200)
        again, unordered2, flagged = critique(todo, results_text, text)
        if again:  # no answer from the critic: keep the first ticks (they can only under-claim what was done)
            checklist, unordered = again, unordered2
        checklist = mark_open(mark_echo(goal, text, checklist, board), open_qs)
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
            c2 = mark_echo(goal, text2, c2, board) if c2 else c2
            if c2 and len(f2) + sum(not c.get("done") for c in c2) < len(flagged) + len(missed):
                board.log("editor", "kept", "the editor's version has fewer problems")
                text, checklist, unordered, flagged = text2, c2, u2, f2
            else:
                board.log("editor", "dropped", "the editor's version was not better")
    else:
        board.log("critic", "ok", "every claim matches the verified results")
    if fixes:
        text = keep_sentences(dedupe_paragraphs(text), n_sent, role, msgs, board)
    if fixes and n_lines and len(body_lines(text)) != n_lines:  # a fix can break the layout he ordered: checked again
        board.log("writer", "format", f"after the fix: {len(body_lines(text))} lines, {n_lines} ordered: asking again")
        text = llm.chat(role, msgs + [{"role": "assistant", "content": text},
                                          {"role": "user", "content": f"That is {len(body_lines(text))} lines. Write it as "
                                           f"exactly {n_lines} lines of plain text, nothing else."}], max_new_tokens=400)
    if open_qs[1] and "not answered by any source" not in text.lower():
        text += "\n\n## Not answered by any source the team read\n" + "\n".join(f"- {q}" for q in open_qs[1])
    return finish(text, board, results_text, sources, checklist, unordered, flagged, fixes)


NOTHING_VERIFIED = ("The team could not confirm an answer to this, so none is given: every step that looked it up was "
                    "rejected by the checks. What was tried and why it failed is listed below.")


TRANSFORM = re.compile(r"\b(translate|rewrite|rephrase|paraphrase|reword|summari[sz]e|shorten|correct|fix|polish|"
                       r"simplify)\b", re.I)


REWORD = {"rewrite", "rephrase", "paraphrase", "reword", "polish", "simplify"}


def echoed(goal, text):
    """Checked in code: the report repeats the text he gave instead of doing what he ordered to it. (A held-out run:
    'Translate into Spanish: ...' came back as the English sentence, and the critic ticked it done.) Translating:
    most of the report's words are copied from his message; any other change: the report is his text word for word."""
    m = TRANSFORM.search(goal or "")
    body = (text or "").split("\n## ")[0]
    # the same sentence three times is still his sentence ("Send me the file now." x3 passed as a rewrite)
    sents = list(dict.fromkeys(" ".join(re.findall(r"\w+", x.lower())) for x in re.split(r"(?<=[.!?])\s+|\n+", body)))
    body = " ".join(x for x in sents if x)
    words = [w for w in body.split() if len(w) >= 3]
    if not m or len(words) < 3:
        return False
    have = re.findall(r"\w+", goal.lower())
    verb = m.group(1).lower()
    if verb == "translate":
        return sum(w in have for w in words) / len(words) >= 0.8
    if verb in REWORD:  # a rewrite with no word of its own has not rewritten anything
        return all(w in have for w in words)
    return body in " ".join(have[have.index(verb) + 1:])


def mark_echo(goal, text, checklist, board):
    """The critic's ticks, with the ordered change marked not done when the report only repeats his text."""
    if not echoed(goal, text):
        return checklist
    board.log("critic", "echo", "the report repeats his text instead of doing what he ordered to it")
    hit = [c for c in checklist if TRANSFORM.search(str(c.get("instruction", "")))] or checklist
    return [dict(c, done=False, why="the report repeats his text unchanged") if c in hit else c for c in checklist]


def _stems(t):
    return {w[:4] for w in re.findall(r"[a-z]{4,}", (t or "").lower())} - {"what", "whic", "wher", "ther", "abou", "from",
                                                                          "with", "does", "that", "this", "have"}


def ungrounded(text, verified, min_stems=6, share=0.3):
    """Sentences of a report built from sources that make a substantial claim (6+ content words) sharing under 30% of
    their words with the verified results: written from the model's memory. (The single researcher's battery report
    gave four paragraphs on battery management systems and material quality from one verified claim about modelling,
    said it was 'based on the verified results', and the critic flagged nothing.)"""
    have = _stems(verified)
    out = []
    for block in (text or "").split("\n## ")[0].split("\n"):
        for sent in re.split(r"(?<=[.!?])\s+", block.strip(" |*-#")):
            mine = _stems(sent)
            if len(mine) >= min_stems and len(mine & have) / len(mine) < share:
                out.append(sent.strip())
    return out


def keep_sentences(text, n, role, msgs, board):
    """Checked in code: the number of sentences he ordered. One more try, told the count; the version closer to it
    is kept."""
    if not n or sentence_count(text) == n:
        return text
    have = sentence_count(text)
    board.log("writer", "format", f"wrote {have} sentences, {n} ordered: asking again")
    again = dedupe_paragraphs(llm.chat(role, msgs + [{"role": "assistant", "content": text},
                                                     {"role": "user", "content": f"That is {have} sentences. Write it as "
                                                      f"exactly {n} sentence{'s' if n != 1 else ''}, nothing else."}],
                                       max_new_tokens=600))
    return again if abs(sentence_count(again) - n) < abs(have - n) else text


def translator_role(goal, results_text):
    """Who writes a translation of his text, by measurement (training/translator.py, 120 held-out professional
    translations, chrF): the 4B editor 51.6, a translation edit of the 1.7B 48.4, the writer (1.7B + its edit) 46.7;
    the 4B is better than the edit by 3.2 (95% CI +0.7 to +5.6) at 4.9 s against 3.0 s a sentence."""
    from .. import config
    if results_text.startswith(OWN_TEXT) and re.search(r"\btranslat\w*\b", goal or "", re.I):
        return config.TRANSLATE_ROLE
    return "writer"


def open_questions(board):
    """(every sub-question the research hive worked on, those no source answered), from its passed steps."""
    every, out = [], []
    for st in board.steps():
        res = st.get("result") or {}
        if isinstance(res, dict) and st.get("verdict") == "PASS":
            every += [q[0] if isinstance(q, (list, tuple)) else q for q in res.get("sub_questions") or []]
            out += [q for q in res.get("open_questions") or [] if q not in out]
    return list(dict.fromkeys(every + out)), out


def mark_open(checklist, questions, board=None):
    """An instruction whose closest sub-question no source answered is not done, whatever the critic ticked (the
    battery report answered 'what slows the degradation' with factors that drive it, after the research hive had found
    nothing that answers it, and the critic ticked it). questions = (all sub-questions, the open ones)."""
    every, open_qs = questions
    if not open_qs:
        return checklist
    out = []
    for c in checklist:
        mine = _stems(c.get("instruction", ""))
        score = {q: len(mine & _stems(q)) / len(mine) for q in every} if mine else {}
        best = max(score, key=score.get) if score else None
        if best in open_qs and score[best] >= 0.5 and c.get("done"):
            c = dict(c, done=False, why=f"no source the team read answers it ({best[:80]})")
            if board is not None:
                board.log("critic", "open", f"not done: {c.get('instruction', '')[:80]} (no source answered: {best[:80]})")
        out.append(c)
    return out


def nothing_verified(goal, board, facts):
    """Every step that ran before the writer failed, and the task hands over no text. (A failed step's facts do not
    count: a researcher step that failed had still checked some facts one by one, and the writer then wrote a report
    of empty step headings.)"""
    from ..guard import split_material
    ran = [s for s in board.steps() if s["agent"] != "writer" and s.get("verdict")]
    passed = {s["id"] for s in ran if s["verdict"] in ("PASS", "REROUTED")}
    return bool(ran) and not passed and not split_material(goal)[1] \
        and not [f for f in facts if f.get("step") in passed]


UNCHECKED = "the critic did not check it"
ONE = """You check one thing for Arnav. Was his INSTRUCTION done, according to the VERIFIED RESULTS and the REPORT?
It is done only if the report holds what the instruction asks for and the verified results back it.
Reply with JSON only: {"done": true, "why": "short"}"""


def ask_again(checklist, board, results_text, text):
    """An instruction the critic did not check is put to it once more, alone. (Asked about three instructions at
    once, the critic checked the plan's steps instead; none matched, and a report whose every step had passed was
    handed over as "0/3 of your instructions done".) Only where every step of the team passed: where one failed, an
    unchecked instruction stays not done."""
    steps = [s for s in board.steps() if s["agent"] != "writer" and s.get("verdict")]
    if not steps or any(s["verdict"] not in ("PASS", "REROUTED") for s in steps):
        return checklist
    out = []
    for c in checklist:
        if not c.get("done") and c.get("why") == UNCHECKED:
            data, _ = llm.chat_json("critic", [{"role": "system", "content": ONE},
                                               {"role": "user", "content": f"INSTRUCTION:\n{c.get('instruction', '')}\n\nVERIFIED RESULTS:\n"
                                                                           f"{results_text[:5000]}\n\nREPORT:\n{text[:4000]}"}],
                                    max_new_tokens=120)
            if isinstance(data, dict) and isinstance(data.get("done"), bool):
                c = {**c, "done": data["done"], "why": str(data.get("why") or "")[:200]}
                board.log("critic", "asked-again", f"{'done' if c['done'] else 'not done'}: {c.get('instruction', '')[:80]}")
        out.append(c)
    return out


def finish(text, board, results_text, sources, checklist, unordered, flagged, fixes):
    """The report's checked tail: numbers grounded, flags, the checklist, what failed, the sources."""
    saved = [Path(a["path"]) for a in board.artifacts() if a.get("kind") == "file"]
    text = fix_images(drop_empty_sections(drop_self_talk(dedupe_paragraphs(text))), saved)
    text, bad_days = check_weekdays(text)
    if bad_days:
        board.log("critic", "weekday", f"{len(bad_days)} line(s) with a date on the wrong day of the week corrected")
    checklist, invented = align_checklist(checklist, list(getattr(board, "checklist", None) or []))
    if invented:
        board.log("critic", "invented", "checklist items that are not his instructions, dropped: " + " | ".join(invented)[:300])
    checklist = ask_again(checklist, board, results_text, text)
    text, struck = ground_numbers(text, results_text + "\n" + "\n".join(sources))
    if struck:
        board.log("critic", "strike", f"{len(struck)} line(s) with numbers not in the verified results removed")
        text += "\n\n## Removed: numbers the team could not verify\n" + "\n".join(f"- {x[:160]}" for x in struck)
    if bad_days:
        text += ("\n\n## Corrected: the day of the week (from the calendar); the report had\n"
                 + "\n".join(f"- {x[:160]}" for x in bad_days))
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
