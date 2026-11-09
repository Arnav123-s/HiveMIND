"""Talk to the hive like to an assistant: one prompt, then a normal conversation. It decides the rest.

Every message is one of:
- stop     ("stop", "cancel that"): the kill switch, every running job halts
- remember ("remember that ...", "from now on ..."): saved to your profile; every report follows it
- talk     (thanks, hello, a question the conversation or the team's last answer already answers): answered at once
            by a small member, no job
- work     (anything to look up, a website, code, files, a calculation, writing, a fact that must be right): a hive
            job with the conversation as context, running until nothing is left undone
The first message of a conversation is work unless it is only a greeting. When unsure, it is work: doing the job
is never wrong, answering from memory can be.
"""
import os
import re

from . import llm, memory


def on():
    """Conversation routing (AGENT_TEAM_CONVERSE=0: every message is a job, as before)."""
    return os.environ.get("AGENT_TEAM_CONVERSE", "1") != "0"

STOP = re.compile(r"^\s*(please\s+)?(stop|halt|cancel|abort|kill)(\s+(it|that|this|everything|now|all|the (job|task|work)))*"
                  r"\s*(now|please)?[\s.!]*$", re.I)
REMEMBER = re.compile(r"^\s*(please\s+)?(remember( that)?|note that|from now on|always)\b", re.I)
SMALL = re.compile(r"^\s*(hi|hello|hey|thanks|thank you|thx|cheers|ok|okay|cool|great|nice|perfect|good (morning|evening|"
                   r"night)|bye|see you)\b[\s!.,:)]*(hive(mind)?)?[\s!.,:)]*$", re.I)
ROUTER = """Decide how to handle Arnav's LATEST message in this conversation with his team of AI specialists.
Reply with JSON only:
{"route":"work"} if it asks for something to be done or found: looking something up, a website, code, files, a
calculation, something written, or any fact that must be correct and is not already in the conversation;
{"route":"talk"} if it is small talk, thanks, or a question that the conversation (including the team's last answer)
already answers."""
TALK = """You are HiveMIND, Arnav's personal agent: a hive of AI specialists working as one. Answer his message in a
few short sentences, using only the conversation and the team's last answer. Never invent facts: if the answer is not
there, say the team can find it and that he only has to ask."""


def route(msg, history=()):
    """'stop', 'remember', 'talk' or 'work' for the latest message (history: earlier (role, text) turns)."""
    if STOP.match(msg):
        return "stop"
    if REMEMBER.match(msg):
        return "remember"
    if SMALL.match(msg):
        return "talk"
    if not history:  # the opening prompt is the job
        return "work"
    convo = "\n".join(f"{'Arnav' if r == 'user' else 'Team'}: {t[:600]}" for r, t in list(history)[-6:])
    data, _ = llm.chat_json("coordinator", [{"role": "system", "content": ROUTER},
                                            {"role": "user", "content": f"{convo}\n\nLATEST: {msg}"}],
                            max_new_tokens=20, adapter=False)
    r = (data or {}).get("route") if isinstance(data, dict) else None
    return "talk" if r == "talk" else "work"


def talk(msg, history=()):
    prof = memory.profile()
    msgs = [{"role": "system", "content": TALK + (f"\nHis preferences:\n{prof}" if prof else "")}]
    msgs += [{"role": "user" if r == "user" else "assistant", "content": t[:2000]} for r, t in list(history)[-8:]]
    return llm.chat("writer", msgs + [{"role": "user", "content": msg}], max_new_tokens=300, adapter=False).strip()


def remember(msg):
    fact = re.sub(r"^\s*(please\s+)?(remember( that)?|note that)\s*", "", msg, flags=re.I).strip()
    memory.remember(fact)
    return f"Saved to your profile: {fact}"


def context(history):
    """Earlier turns as context for a job: what was said and found, never orders."""
    return "\n".join(f"{'Arnav' if r == 'user' else 'Team'}: {t[:1500]}" for r, t in list(history)[-8:])


class Reply:
    """A direct answer, shaped like a finished job for the API's answer formats."""

    def __init__(self, text, kind="talk"):
        import secrets
        self.id, self.report, self.kind = f"talk-{secrets.token_hex(4)}", text, kind
        self.error, self.unmet, self.files, self.status, self.rounds, self.pending_approvals = "", [], [], "done", [], []

    def wait(self, timeout=None):
        return self

    def events(self, follow=False, poll=0.5, heartbeat=None):
        return iter(())


def handle(msg, history, submit):
    """One message of the conversation. submit(task, context) starts a job. Returns a Reply or the job."""
    from . import stop
    r = route(msg, history)
    if r == "stop":
        stop.request("conversation: " + msg[:60])
        return Reply("Stopping every running job now. What each one finished is kept in its run folder.", "stop")
    if r == "remember":
        return Reply(remember(msg), "remember")
    if r == "talk":
        return Reply(talk(msg, history))
    return submit(msg, context(history))
