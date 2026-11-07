"""agent-team command line.

    python -m team "your task"            give the team one task (default)
    python -m team chat                   talk to it like an assistant
    python -m team web                    chat-style page at http://127.0.0.1:8765
    python -m team serve                  always on: inbox + schedule + dreaming when idle
    python -m team add "task"             drop a task into the inbox for `serve`
    python -m team dream [--no-train] [--rehearse N]   replay past runs, learn lessons, retrain weights
    python -m team remember "fact"        add to your profile (how you like things done)
"""
import argparse
import json
import sys

COMMANDS = {"chat", "serve", "add", "dream", "remember", "web"}


def main():
    if len(sys.argv) > 1 and sys.argv[1] in COMMANDS:
        cmd, rest = sys.argv[1], sys.argv[2:]
        if cmd == "chat":
            from .chat import main as chat
            return chat()
        if cmd == "web":
            from .web import main as web
            return web(int(rest[0]) if rest else 8765)
        if cmd == "serve":
            from .serve import serve
            return serve()
        if cmd == "add":
            from .serve import add
            return print("queued:", add(" ".join(rest)))
        if cmd == "dream":
            from .dream import dream
            n = int(rest[rest.index("--rehearse") + 1]) if "--rehearse" in rest else 2
            return dream(train="--no-train" not in rest, rehearse_n=n)
        if cmd == "remember":
            from . import memory
            memory.remember(" ".join(rest))
            return print("saved to", memory.PROFILE)
    ap = argparse.ArgumentParser(prog="python -m team", description="Give the agent team one task.")
    ap.add_argument("task", nargs="?", help="the task, in plain words (or use --file)")
    ap.add_argument("--file", help="read the task from a file")
    ap.add_argument("--approve", choices=["ask", "never"], default="ask",
                    help="ask: stop and ask on the terminal before spending/deleting/sending (default); "
                         "never: refuse those actions and list them for you at the end")
    ap.add_argument("--allow-login", action="append", default=[], metavar="SITE",
                    help="let the browser log in to SITE with your vault credentials for this task only")
    ap.add_argument("--run-dir", help="where to keep this run's board, files and report")
    a = ap.parse_args()
    task = open(a.file).read() if a.file else a.task
    if not task:
        ap.error("give a task")
    from .hive import Hive
    out = Hive(task, a.run_dir, a.approve, a.allow_login).run()
    print("\n" + "=" * 70 + "\n" + (out["report"] or "")[:6000])
    print("\nRun folder:", out["dir"])
    if out["pending_approvals"]:
        print("Waiting on you:", json.dumps(out["pending_approvals"], indent=1))


if __name__ == "__main__":
    main()
