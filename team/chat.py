"""Talk to the team like an assistant. Anything that needs the web, a browser
or code goes to the whole hive; small talk and "remember ..." are handled here.

    python -m team chat
"""
import re

from . import llm, memory
from .hive import Hive

ROUTER = """Decide how to handle Arnav's message.
Reply with JSON only: {"route":"task"} if it needs looking things up, a website, code, files or any fact that must be correct;
{"route":"chat"} if it is small talk, thanks, or a question about the conversation itself."""

CHAT = """You are Arnav's assistant, the voice of a team of AI specialists. Be short and direct.
If he asks for facts you have not verified, say the team can look it up (he can just ask it as a task)."""


def route(msg):
    if re.match(r"^\s*(remember|note that)\b", msg, re.I):
        return "remember"
    data, _ = llm.chat_json("coordinator", [{"role": "system", "content": ROUTER}, {"role": "user", "content": msg}],
                            max_new_tokens=20, adapter=False)
    return (data or {}).get("route", "task") if isinstance(data, dict) else "task"


def main(approve="ask"):
    history = []
    print("agent-team chat. Type a task or a question; 'exit' to quit.")
    while True:
        try:
            msg = input("\nyou> ").strip()
        except EOFError:
            break
        if not msg:
            continue
        if msg.lower() in ("exit", "quit"):
            break
        r = route(msg)
        if r == "remember":
            memory.remember(re.sub(r"^\s*(remember( that)?|note that)\s*", "", msg, flags=re.I))
            print("team> Saved to your profile.")
            continue
        if r == "task":
            out = Hive(msg, approve=approve).run()
            print("\nteam> " + (out["report"] or "(no report)") + f"\n\n(run folder: {out['dir']})")
            history += [{"role": "user", "content": msg}, {"role": "assistant", "content": out["report"][:1500]}]
            continue
        prof = memory.profile()
        sysmsg = CHAT + (f"\nArnav's preferences:\n{prof}" if prof else "")
        reply = llm.chat("writer", [{"role": "system", "content": sysmsg}] + history[-8:] + [{"role": "user", "content": msg}],
                         max_new_tokens=300, adapter=False)
        history += [{"role": "user", "content": msg}, {"role": "assistant", "content": reply}]
        print("team> " + reply)
