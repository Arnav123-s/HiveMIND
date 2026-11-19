"""Talk with the hive: a question, a conversation or a task, through one door.

    python -m team.talk                       a conversation in the terminal
    python -m team.talk "one message"         one reply
    python -m team.talk --thread thread.json --out reply.md
                                              one reply to a conversation kept elsewhere (the workflow "Talk to the
                                              hive" keeps it in a GitHub issue): {"name": ..., "messages": [{"role":
                                              "user" | "assistant", "content": ...}, ...]}, the last one the user's

Every message is first put to the body's own model as one question: can this be answered as it stands, or does it
have to be worked out? It says one word.

  talk    greetings, an explanation, advice, an opinion, something written, a thing that does not change and is
          simply known: the model answers at once, with the conversation so far.
  work    anything that has to be worked out or looked up to be right (a sum, a date, data to go through, a fact that
          changes, a web page, a file, a program): the message goes, in the user's own words, to the body, which does
          it the way it does every task (team/solo.py): its trunk and cells each write and run programs, and an
          answer counts when two of them agree. The result comes back into the conversation and is said in plain
          words, with the checked values as the programs printed them.

A checked method from the local fieldwork bank can answer a matching request before the body starts. HIVE_BANK
can select another bank. When its saved versions disagree, or the message lacks its inputs, the reply says so.

So nothing that can be computed or read from a source is answered from memory, and small talk does not wait for
programs. The one who talks is the body's DNA with no cell's edit switched on: conversation is what the DNA knows
already, and the cells are grown for the work. (The first form let the talker hand a task over by writing it out
after the word WORK. On the first real conversation it wrote its own answer there, and the body spent five minutes
"working on" a sentence. The decision is one word now, and the task is always the user's own message.)
"""
import datetime
from contextlib import redirect_stdout
from decimal import Decimal, InvalidOperation
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

from . import config, ternary

TALK = """You are HiveMIND: a hive of small neural nets with ternary weights that work as one body, on plain CPUs. You are talking with {name}. Now it is {today}.
Answer directly and in plain words, as briefly as the message allows. Be honest: if you do not know, say so. Do not make up facts, figures, links or sources."""
DECIDE = """Decide how a message has to be answered. Reply with one word, TALK or WORK.
TALK: greetings and talk, an explanation, advice, an opinion, something to write (a letter, a poem, a summary of a text that is given), a translation, and facts that do not change (a capital city, a definition, how something works).
WORK: anything to calculate or count, dates and time spans, data to go through (a table, a list, a log, a file), a fact that changes or must be exact today (a version, a price, a release date, a score, news), a web page or website to read, a file to make, a program to write and run.
"hi there" -> TALK
"why is the sky blue?" -> TALK
"what is 17.5% of 2340?" -> WORK
"what is the capital of Peru?" -> TALK
"how many days until 1 March 2027?" -> WORK
"write a haiku about rain" -> TALK
"which is the newest version of numpy?" -> WORK
"write a function that reverses a list and show that it works" -> WORK
"thanks, that helps" -> TALK
"here are my expenses: rent 900, food 320, bus 64. what share is rent?" -> WORK"""
SMALL = re.compile(r"^\W*(hi|hello|hey|thanks|thank you|thx|cheers|ok|okay|cool|great|nice|perfect|good (morning|evening|night)|bye|see you)\b[\w\s!.,:)]{0,24}$", re.I)
RESULT = """RESULT OF THE HIVE'S WORK ({how}):
{report}
{files}
Now reply to {name}. Give the answer in plain words with every value exactly as the result has it; do not change, round or add any value. {then}"""
# what must be worked out even when the talker answered from memory: a small net is often wrong on these
MUST = re.compile(r"https?://|\bwww\.|\d\s*[-+*/^%]\s*\d|\b\d+(?:\.\d+)?\s*%|\b(?:latest|newest|current)\s+(?:version|release|price)\b|\bhow many days\b|"
                  r"\b(?:calculate|compute)\b|\b\w+\.(?:csv|json|py|md|txt|xlsx)\b|\b(?:scrape|download)\b", re.I)
LONG = int(os.environ.get("HIVE_TALK_LONG", 900))  # the most pieces of one reply
KEEP = int(os.environ.get("HIVE_TALK_KEEP", 9000))  # how many characters of the conversation the talker is shown
SINGLE_INTEGER = re.compile(r"\b(?:(?:as|with)\s+(?:a\s+)?single integer|(?:only|just)\s+(?:the|an?|one)\s+integer)\b", re.I)


def speaker():
    """Who talks: the DNA of the body on this machine (None when the ternary runtime or the body is not here)."""
    who = [w for w in ternary.roster() if w != "coder"]
    return ternary.split(who[0])[0] if who else None


def _shown(history):
    """The end of the conversation that fits: whole messages, the newest kept."""
    out, used = [], 0
    for m in reversed(list(history)):
        text = str(m.get("content", ""))
        if used and used + len(text) > KEEP:
            break
        out.append({"role": "assistant" if m.get("role") == "assistant" else "user", "content": text[-KEEP:]})
        used += len(text)
    out.reverse()
    while out and out[0]["role"] != "user":  # a conversation as the model reads it begins with the user
        out.pop(0)
    return out


def decide(base, message, before=""):
    """'talk' or 'work' for a message. Code decides what it can tell by itself; the body's model says one word for
    the rest (before: the hive's last reply, which a short follow-up refers to)."""
    if MUST.search(message):
        return "work"
    if SMALL.match(message):
        return "talk"
    said = ternary.chat(base, [{"role": "system", "content": DECIDE},
                               {"role": "user", "content": (f'(Just before, the user was told: "{before[:400]}")\n' if before else "") + f'"{message[:1500]}" ->'}],
                        max_new_tokens=4, temperature=0.0)
    return "work" if "WORK" in said.upper() else "talk"


_VALUE = re.compile(r"(?<![\w.])v?\d+(?:\.\d+){2,}(?:[a-z]+\d*)?|"
                    r"(?<![\w.])[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?", re.I)


def _values(text):
    # Preserve versions and decimal precision when a conversational rewrite restates a result.
    values = set()
    for token in _VALUE.findall(text):
        try:
            values.add(Decimal(token.replace(",", "")))
        except InvalidOperation:
            values.add(token.lower().lstrip("v"))
    return values


def route(base, message, history=()):
    """How reply() takes a message: ('talk' or 'work', the conversation as the talker is shown it)."""
    convo = _shown(list(history) + [{"role": "user", "content": message}])
    last = next((m["content"] for m in reversed(convo[:-1]) if m["role"] == "assistant"), "")
    return decide(base, message, last), convo


def saved_reply(message, log=None, *, local_only=False):
    """Run a matching saved method and format its result for the ordinary chat interface."""
    from . import saved

    started = time.time()
    if saved.bank_path() is None:
        return None
    kept = saved.answer(message, log=log, local_only=local_only)
    if kept is None:
        return None
    if log:
        log(f"saved method {kept['task']}: {kept['status']}")
    return {"text": kept["text"], "worked": True, "agreed": kept["status"] == "answered",
            "task": message, "dir": "", "files": [], "saved": kept, "seconds": round(time.time() - started)}


def reply(message, history=(), name="the user", run_dir=None, log=None, base=None, now=None):
    """The hive's reply to the latest message: {"text", "worked", "agreed", "task", "dir", "seconds"}.
    history: the earlier messages, oldest first ({"role", "content"}). base: who talks (default: the body's DNA).
    now: the date and time the hive is told it is (default: the clock; the talk exam gives its own)."""
    t0 = time.time()
    kept = saved_reply(message, log, local_only=True)
    if kept and not kept["saved"].get("fallback_to_members"):
        return kept
    base = base or speaker()
    if not base:
        if kept:
            return kept
        raise RuntimeError("the hive's body is not on this machine: bash scripts/cloud_setup.sh (or python -m team.ternary install, then python training/grow.py fetch)")
    say = log or (lambda *a: None)
    today = (now or datetime.datetime.now()).strftime("%Y-%m-%d (%A), %H:%M")
    system = {"role": "system", "content": TALK.format(name=name, today=today)}
    way, convo = route(base, message, history)
    if way == "talk":
        text = ternary.chat(base, [system] + convo, max_new_tokens=LONG, temperature=0.0).strip()
        return {"text": text, "worked": False, "agreed": None, "task": "", "dir": "", "files": [], "seconds": round(time.time() - t0)}
    # the task is the user's own message; what it refers to in the conversation goes with it
    before = "\n".join(f"{'User' if m['role'] == 'user' else 'HiveMIND'}: {m['content'][:700]}" for m in convo[:-1][-4:])
    task = f"{message}\n\n(This continues a conversation. What was said before, for what the task refers to:\n{before})" if before else message
    if now:  # a time given from outside is not the machine's clock: the programs are told it
        # g45's talk exam: told it was 2028-02-27, the members' programs read the machine's clock and answered from 2026
        task += f"\n\n(It is now {today}. Take this as today's date and the time now; do not read the computer's clock.)"
    say(f"the hive works on it: {task[:300]}")
    from . import solo
    if run_dir is None:
        config.RUNS.mkdir(parents=True, exist_ok=True)
        run_dir = tempfile.mkdtemp(dir=config.RUNS, prefix=time.strftime("talk-%Y%m%d-%H%M%S-"))
    home = Path(run_dir)
    out = solo.first(task, home, "never", members=int(os.environ.get("AGENT_TEAM_SOLO", "2") or 2))
    answer = out["report"].split("\n## ")[0].strip()
    made = out.get("files", []) if out["agreed"] else []
    exact = out["agreed"] and SINGLE_INTEGER.search(message) and re.fullmatch(r"[+-]?\d+", answer)
    if out.get("requested_files") or exact:
        # A file request already has a plain report and a publication decision. A second
        # model rewriting that decision can invent a successful delivery or change a value.
        final = answer if out["agreed"] else out["report"].strip()
        if made and not exact:
            final += "\n\nFiles saved: " + ", ".join(made)
        return {"text": final, "worked": True, "agreed": bool(out["agreed"]), "task": task, "dir": str(home),
                "files": made, "file_repairs": out.get("file_repairs", []), "seconds": round(time.time() - t0)}
    if out["agreed"]:
        how, then = "checked: its members worked it out independently with programs and two of them agreed", "Then say in one short sentence that the hive's members worked it out with programs and two agreed."
    else:
        how, then = "NOT confirmed: its members did not agree", "Say plainly that the hive could not confirm an answer, and what each member found."
        answer = out["report"].strip()
    files = f"Files it made: {', '.join(made)}\n" if made else ""
    final = ternary.chat(base, [system] + convo + [{"role": "assistant", "content": "That has to be worked out. The hive is doing it with programs."},
                                                   {"role": "user", "content": RESULT.format(how=how, report=answer[:3500], files=files, name=name, then=then)}],
                         max_new_tokens=LONG, temperature=0.0).strip()
    if not final:
        final = answer
    # the values are the programs', never the talker's: where its wording lost or changed one, the checked output is shown as it is
    if out["agreed"]:
        expected, said = _values(answer), _values(final)
        if expected - said or said - expected - _values(task):
            final = answer
    if made and not all(f in final for f in made):
        final += "\n\nFiles made: " + ", ".join(made)
    return {"text": final, "worked": True, "agreed": bool(out["agreed"]), "task": task, "dir": str(home),
            "files": made, "seconds": round(time.time() - t0)}


def file_paths(out):
    """The published files in a reply, for terminal users and the hosted download."""
    return [Path(out["dir"]) / "work" / name for name in out.get("files", [])]


def repair_notes(out):
    return [f"The hive sorted {r['name']} by {r['column']} ({r['direction']}) before delivery."
            for r in out.get("file_repairs", [])]


def local_text(out):
    details = repair_notes(out) + [str(p.absolute()) for p in file_paths(out)]
    return out["text"] + ("\n\n" + "\n".join(details) if details else "")


def print_one(message, **options):
    """Keep progress and file locations on stderr so stdout can be used as the answer."""
    with redirect_stdout(sys.stderr):
        out = reply(message, **options)
    print(out["text"])
    for note in repair_notes(out):
        print(note, file=sys.stderr)
    for path in file_paths(out):
        print(path.absolute(), file=sys.stderr)
    return int("saved" in out and not out["agreed"])


def main(argv):
    opt = lambda k, d: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else d  # noqa: E731
    name = opt("--name", os.environ.get("HIVE_USER", "the user"))
    if "--thread" in argv:
        thread = json.loads(Path(opt("--thread", "")).read_text())
        msgs = [m for m in thread.get("messages", []) if isinstance(m, dict) and str(m.get("content", "")).strip()]
        if not msgs or msgs[-1].get("role") == "assistant":
            print("nothing to answer: the last message is not the user's")
            return 0
        message = str(msgs[-1]["content"])
        if "--saved-only" in argv:
            from . import saved
            if saved.bank_path() is None:
                return 3  # Continue to the ordinary model.
            class NeedsRuntime(Exception):
                pass
            class UnavailableGuest:
                def run(self, *args, **kwargs):
                    raise NeedsRuntime
            # Matching and input validation use the standard saved-method path. An
            # unavailable guest is only asked to run if a real computation matches.
            started = time.monotonic()
            try:
                kept = saved.answer(message, runner=saved.guest() or UnavailableGuest())
            except NeedsRuntime:
                return 4  # Install the optional guest and retry with its interpreter.
            if kept is None:
                return 3
            out = dict(text=kept["text"], saved=kept, seconds=round(time.monotonic() - started))
        else:
            out = reply(message, msgs[:-1], str(thread.get("name") or name), opt("--run-dir", None),
                        log=lambda *a: print(*a, flush=True))
        if out.get("saved"):
            foot = f"\n\n<sub>Saved method · {out['saved']['status']} · {out['seconds']} s</sub>"
        else:
            foot = (f"\n\n<sub>{'Worked out by programs; two members agreed' if out['agreed'] else 'Worked on by programs; not confirmed'} · {out['seconds']} s</sub>"
                    if out["worked"] else f"\n\n<sub>Answered directly · {out['seconds']} s</sub>")
        notes = repair_notes(out)
        response = out["text"].strip() + ("\n\n" + "\n".join(notes) if notes else "")
        Path(opt("--out", "reply.md")).write_text(response + foot + "\n")
        if "--export-files" in argv:
            from . import deliverables
            export = Path(opt("--export-files", "delivery"))
            export.mkdir(parents=True, exist_ok=False)
            if out.get("files"):
                deliverables.copy_files(Path(out["dir"]) / "work", out["files"], export)
        print(out["text"])
        return 0
    words = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in ("--name", "--run-dir", "--out", "--export-files"))]
    if words:
        return print_one(" ".join(words), name=name, run_dir=opt("--run-dir", None), log=lambda *a: print(*a, flush=True))
    return conversation(name=name, base=speaker())


def conversation(first=None, *, name="the user", base=None, methods=(), remote=None):
    """Keep ordinary conversation or, on a model-free machine, serve its available local methods."""
    if not base:
        from . import saved
        methods = methods or saved.available()
        if not methods:
            print("the hive's body is not on this machine: bash scripts/cloud_setup.sh")
            return 1
        print("Saved methods: " + ", ".join(methods) + '. Type "Run NAME with JSON" to use one; type "exit" to leave.')
    else:
        print("HiveMIND. Say anything, or give it a task; 'exit' ends the conversation.")
    history = []
    msg = first
    while True:
        if msg is None:
            try:
                msg = input("\nyou> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
        if msg.lower() in ("exit", "quit", "/exit", "/quit", ":q", "bye"):
            break
        if msg:
            if base:
                out = reply(msg, history, name, base=base, log=lambda *a: print("  [" + " ".join(map(str, a)) + "]", flush=True))
            else:
                out = saved_reply(msg, local_only=remote is None)
            if out is not None:
                text = local_text(out)
                print("\nhive> " + text)
            elif remote:
                text = remote(msg, [(m["role"], m["content"]) for m in history])
            else:
                text = "No saved method fits this request. For other tasks, install the hive's body with bash scripts/cloud_setup.sh."
                print("\nhive> " + text)
            history += [{"role": "user", "content": msg}, {"role": "assistant", "content": text}]
        msg = None
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
