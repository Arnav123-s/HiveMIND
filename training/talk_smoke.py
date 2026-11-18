"""The body talking: three fixed plain messages sent every generation through the door a person uses.

    python training/talk_smoke.py sit --arm after [--out talk_smoke.json] [--per 240] [--minutes 12]
                                    the three messages, one after the other in one conversation, each through
                                    `python -m team.talk --thread thread.json --out reply.md` (as the workflow
                                    "Talk to the hive" runs it); each held to --per seconds, all to --minutes
    python training/talk_smoke.py write GEN FOLDER [--out docs/reads/talk_smoke.md] [--record generations.jsonl]
                                    the page of what the body said: the sitting of the body the record kept
                                    (after when kept, before when dropped), from FOLDER/talk-smoke-<arm>/

The gate sits it (.github/workflows/grow.yml) on the first seat of before and of after, where the hive is installed
already: installing it in the record job would add a quarter of an hour there. The record job writes the page after
the record is committed, so a person can see the body actually talking. Neither ever fails or holds up the line: a
message that takes too long is said so on the page, and a page that cannot be written leaves the old one.
No check is made: the talk exam (training/talk_exam.py) scores; this only shows.
"""
import datetime
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RECORD = ROOT / "training" / "reports" / "generations.jsonl"
PAGE = ROOT / "docs" / "reads" / "talk_smoke.md"
# a fact, a follow-up that needs the turn before it, and the time (the hive is told the date and time: team/talk.TALK)
MESSAGES = ("What is the capital of Australia?",
            "And roughly how many people live in that city?",
            "What time is it?")
ARMS = ("before", "after")
MOST = 3000  # the most characters of one reply on the page


def _reply_text(md):
    """The reply as team/talk.py wrote it, less its footer (the line of how it was answered)."""
    return "\n".join(ln for ln in md.splitlines() if not ln.strip().startswith("<sub>")).strip()


def _run(cmd, timeout, **kw):
    from training import exam
    return exam.run_task(cmd, timeout, **kw)  # ends every program the reply started when it runs out of time


def sit(arm, out, per=240, minutes=12, run=None, log=print):
    """Each message in turn, the conversation so far with it; writes out (json) after every message."""
    run = run or _run
    turns, history, t00 = [], [], time.time()
    home = Path(tempfile.mkdtemp(prefix="talk-smoke-"))

    def save():
        Path(out).write_text(json.dumps({"arm": arm, "when": time.strftime("%Y-%m-%d %H:%M"), "members": os.environ.get("HIVE_MEMBERS", ""),
                                         "turns": turns}, indent=1) + "\n")
    for i, message in enumerate(MESSAGES):
        left = 60 * minutes - (time.time() - t00)
        cap = min(per, left)
        t0 = time.time()
        text, note = "", ""
        if cap <= 5:
            note = "not sent: the sitting's time was up"
        else:
            thread, reply = home / f"thread{i}.json", home / f"reply{i}.md"
            thread.write_text(json.dumps({"name": "the owner", "messages": history + [{"role": "user", "content": message}]}))
            code, err = run([sys.executable, "-m", "team.talk", "--thread", str(thread), "--out", str(reply), "--run-dir", str(home / f"run{i}")],
                            cap, cwd=ROOT)
            text = _reply_text(reply.read_text()) if reply.exists() else ""
            if code is None:
                note = f"no reply within {cap:.0f} s"
            elif code != 0 or not text:
                note = f"no reply (exit {code}: {err.strip().splitlines()[-1][:200] if err and err.strip() else ''})"
        turns.append({"message": message, "reply": text, "seconds": round(time.time() - t0), "note": note})
        history += [{"role": "user", "content": message}, {"role": "assistant", "content": text or "(no reply)"}]
        log(f"{arm} {i + 1}: {message!r} -> {text[:100]!r} {note}", flush=True)
        save()
    save()
    return turns


def _verdict(gen, record):
    try:
        lines = [json.loads(ln) for ln in Path(record).read_text().splitlines() if ln.strip().startswith("{")]
    except (OSError, ValueError):
        return None
    line = next((r for r in reversed(lines) if isinstance(r, dict) and r.get("generation") == gen), None)
    return None if line is None else bool(line.get("kept"))


def _sitting(folder, arm):
    """One arm's sitting, as this file wrote it: only the messages it sends, and replies cut to MOST characters."""
    for f in sorted(Path(folder).glob(f"talk-smoke-{arm}/*.json")):
        if f.stat().st_size > 200_000:
            continue
        try:
            d = json.loads(f.read_text())
        except ValueError:
            continue
        turns = []
        for t in (d.get("turns") or [])[:len(MESSAGES)] if isinstance(d, dict) else []:
            if not isinstance(t, dict) or t.get("message") not in MESSAGES:
                continue
            s = t.get("seconds")
            turns.append({"message": t["message"], "reply": str(t.get("reply") or "")[:MOST],
                          "seconds": s if isinstance(s, int) and 0 <= s < 100000 else None, "note": str(t.get("note") or "")[:240]})
        if turns:
            return turns
    return None


def _block(text):
    """A reply as plain text on the page: fenced, so nothing in it is read as the page's own markup."""
    text = re.sub(r"~{3,}", "~~", text.replace("\r", ""))
    return ["~~~text", text, "~~~"]


def page(gen, folder, record=RECORD):
    kept = _verdict(gen, record)
    first = "after" if kept is not False else "before"
    order = [first] + [a for a in ARMS if a != first]
    arm, turns = next(((a, t) for a in order if (t := _sitting(folder, a))), (None, None))
    out = [f"# The body talking, after {gen}", "",
           "Three fixed plain messages, sent every generation through the door a person uses (`team/talk.py`, as the "
           "workflow \"Talk to the hive\" runs it), in one conversation: a fact, a follow-up that needs the turn before, "
           "and the time. Nothing here is scored (the talk exam is); it shows the body actually talking. Written by the "
           "record job (`training/talk_smoke.py`) and overwritten every generation.", ""]
    if not turns:
        return "\n".join(out + [f"Not sat this generation: no sitting of the body came from {gen}'s gate.", ""])
    who = {"after": "the body with this generation's children", "before": "the body as it was before this generation"}[arm]
    why = ("it was kept" if kept else "they were dropped" if kept is False else "the record says neither") if arm == first else \
        f"the sitting of the {first} arm did not come"
    out += [f"Who answered: {who} ({why}). Recorded {datetime.date.today().isoformat()}.", ""]
    for i, t in enumerate(turns, 1):
        out += [f"## {i}. You: {t['message']}", ""]
        took = f" ({t['seconds']} s)" if t["seconds"] is not None else ""
        if t["reply"]:
            out += [f"The hive{took}:", ""] + _block(t["reply"]) + [""]
        else:
            out += [f"The hive did not reply{took}: {t['note'] or 'nothing came back'}.", ""]
    return "\n".join(out)


def write(gen, folder, out=PAGE, record=RECORD):
    text = page(gen, folder, record)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(text)
    print(f"{out}: written for {gen}")
    return 0


def main(argv):
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else d  # noqa: E731
    if argv[:1] == ["sit"] and opt("--arm") in ARMS:
        sit(opt("--arm"), opt("--out", "talk_smoke.json"), float(opt("--per", 240)), float(opt("--minutes", 12)))
        return 0
    if argv[:1] == ["write"] and len(argv) >= 3 and re.fullmatch(r"g\d{1,6}", argv[1]):
        return write(argv[1], argv[2], opt("--out", PAGE), opt("--record", RECORD))
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
