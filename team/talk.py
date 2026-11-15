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

So nothing that can be computed or read from a source is answered from memory, and small talk does not wait for
programs. The one who talks is the body's DNA with no cell's edit switched on: conversation is what the DNA knows
already, and the cells are grown for the work. (The first form let the talker hand a task over by writing it out
after the word WORK. On the first real conversation it wrote its own answer there, and the body spent five minutes
"working on" a sentence. The decision is one word now, and the task is always the user's own message.)
"""
import json
import os
import re
import sys
import time
from pathlib import Path

from . import config, ternary

TALK = """You are HiveMIND: a hive of small neural nets with ternary weights that work as one body, on plain CPUs. You are talking with {name}. Today is {today}.
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


def _numbers(text, task=""):
    from . import solo
    return {round(x, 2) for x in solo.key(text, task)}


def reply(message, history=(), name="the user", run_dir=None, log=None):
    """The hive's reply to the latest message: {"text", "worked", "agreed", "task", "dir", "seconds"}.
    history: the earlier messages, oldest first ({"role", "content"})."""
    t0 = time.time()
    base = speaker()
    if not base:
        raise RuntimeError("the hive's body is not on this machine: bash scripts/cloud_setup.sh (or python -m team.ternary install, then python training/grow.py fetch)")
    say = log or (lambda *a: None)
    system = {"role": "system", "content": TALK.format(name=name, today=time.strftime("%Y-%m-%d (%A)"))}
    convo = _shown(list(history) + [{"role": "user", "content": message}])
    last = next((m["content"] for m in reversed(convo[:-1]) if m["role"] == "assistant"), "")
    if decide(base, message, last) == "talk":
        text = ternary.chat(base, [system] + convo, max_new_tokens=LONG, temperature=0.0).strip()
        return {"text": text, "worked": False, "agreed": None, "task": "", "dir": "", "seconds": round(time.time() - t0)}
    # the task is the user's own message; what it refers to in the conversation goes with it
    before = "\n".join(f"{'User' if m['role'] == 'user' else 'HiveMIND'}: {m['content'][:700]}" for m in convo[:-1][-4:])
    task = f"{message}\n\n(This continues a conversation. What was said before, for what the task refers to:\n{before})" if before else message
    say(f"the hive works on it: {task[:300]}")
    from . import solo
    home = Path(run_dir or config.RUNS / time.strftime("talk-%Y%m%d-%H%M%S"))
    out = solo.first(task, home, "never", members=int(os.environ.get("AGENT_TEAM_SOLO", "2") or 2))
    answer = out["report"].split("\n## ")[0].strip()
    made = sorted(p.name for p in (home / "work").iterdir() if p.is_file() and not p.name.startswith(".")) if (home / "work").is_dir() else []
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
    if out["agreed"] and not _numbers(answer, task) <= _numbers(final, task):
        final += "\n\nThe checked result, as the programs printed it:\n```\n" + answer[:3000] + "\n```"
    if made and not all(f in final for f in made):
        final += "\n\nFiles made: " + ", ".join(made)
    return {"text": final, "worked": True, "agreed": bool(out["agreed"]), "task": task, "dir": str(home), "seconds": round(time.time() - t0)}


def main(argv):
    opt = lambda k, d: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else d  # noqa: E731
    name = opt("--name", os.environ.get("HIVE_USER", "the user"))
    if "--thread" in argv:
        thread = json.loads(Path(opt("--thread", "")).read_text())
        msgs = [m for m in thread.get("messages", []) if isinstance(m, dict) and str(m.get("content", "")).strip()]
        if not msgs or msgs[-1].get("role") == "assistant":
            print("nothing to answer: the last message is not the user's")
            return 0
        out = reply(str(msgs[-1]["content"]), msgs[:-1], str(thread.get("name") or name), opt("--run-dir", None), log=lambda *a: print(*a, flush=True))
        foot = (f"\n\n<sub>{'Worked out by programs; two members agreed' if out['agreed'] else 'Worked on by programs; not confirmed'} · {out['seconds']} s</sub>"
                if out["worked"] else f"\n\n<sub>Answered directly · {out['seconds']} s</sub>")
        Path(opt("--out", "reply.md")).write_text(out["text"].strip() + foot + "\n")
        print(out["text"])
        return 0
    words = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in ("--name", "--run-dir", "--out"))]
    if words:
        out = reply(" ".join(words), (), name, opt("--run-dir", None), log=lambda *a: print("[" + " ".join(map(str, a)) + "]", file=sys.stderr, flush=True))
        print(out["text"])
        return 0
    if not speaker():
        print("the hive's body is not on this machine: bash scripts/cloud_setup.sh")
        return 1
    print("HiveMIND. Say anything, or give it a task; 'exit' ends the conversation.")
    history = []
    while True:
        try:
            msg = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not msg:
            continue
        if msg.lower() in ("exit", "quit", "bye"):
            break
        out = reply(msg, history, name, log=lambda *a: print("  [" + " ".join(map(str, a)) + "]", flush=True))
        print("\nhive> " + out["text"])
        history += [{"role": "user", "content": msg}, {"role": "assistant", "content": out["text"]}]
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
