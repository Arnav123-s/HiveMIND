"""agent-team command line.

    python -m team "your task"            give the team one task (default)
    python -m team "task" --approve never --until-done 2   unattended: follow-up rounds until nothing is left undone
    python -m team api [--port 8766]      OpenAI/Anthropic-compatible API + jobs (any SDK or chat app can use the swarm)
    python -m team chat                   talk to it like an assistant
    python -m team web                    chat-style page at http://127.0.0.1:8765
    python -m team serve [--port 8766]    always on: API + chat page + inbox + schedule, dreaming when idle
    python -m team install [--dry-run]    start the always-on agent with the device (uninstall: stop and remove it)
    python -m team add "task"             drop a task into the inbox for `serve`
    python -m team dream [--no-train] [--rehearse N]   replay past runs, learn lessons, retrain weights
    python -m team remember "fact"        add to your profile (how you like things done)
    python -m team grow [--min 200]       grow new cells from the hive's own logged decisions (team/cells/learn.py)
    python -m team project "goal"         a long project: milestones in their own workspace, resumable (team/project.py)
    python -m team projects               every project and how far it got
    python -m team stop                   KILL SWITCH: stop every running task now (also Ctrl+C, web Stop, inbox/STOP)
    python -m team smiths [cycle ROLE|gaps|tests]   the smith swarm: ledger, one improvement cycle, gaps, field tests
    python -m team evolve ROLE [--variants 3] [--generations 1]   evolve a specialist's prompt (gated)
    python -m team life [--min 200] [--no-train]   one turn of the hive's life: notice new small jobs in its own calls,
                                          grow a cell for each, check the working ones, retire the bad (team/life.py)
    python -m team org                    the hive as an organisation: teams, members, cells, who holds each job
"""
import argparse
import json
import sys

COMMANDS = {"chat", "serve", "add", "dream", "remember", "web", "evolve", "stop", "smiths", "api", "grow", "install",
            "uninstall", "project", "projects", "life", "org"}


def main():
    if len(sys.argv) > 1 and sys.argv[1] in COMMANDS:
        cmd, rest = sys.argv[1], sys.argv[2:]
        if cmd == "chat":
            from .chat import main as chat
            return chat()
        if cmd == "life":
            from . import life
            return life.main(rest)
        if cmd == "org":
            from . import org
            return org.main()
        if cmd == "smiths":
            from . import smiths
            if rest and rest[0] == "cycle":
                return smiths.cycle(rest[1] if len(rest) > 1 else "verifier")
            if rest and rest[0] == "tests":
                return print("field tests written:", smiths.write_field_tests())
            if rest and rest[0] == "gaps":
                return print("\n".join(smiths.spot_gaps()))
            for s in sorted(smiths.ledger().values(), key=lambda x: (x["job"], -smiths.rate(x))):
                print(f"{s['job']:<15} {s['id']:<22} wins {s['wins']}/{s['trials']}  {'RETIRED ' if s.get('retired') else ''}{s['strategy'][:70]}")
            return None
        if cmd == "stop":
            from . import stop
            return print("stop flag set:", stop.request("terminal: python -m team stop"),
                         "- every running task halts now")
        if cmd == "evolve":
            from .evolve import evolve
            role = rest[0] if rest else "verifier"
            opt = lambda k, d: type(d)(rest[rest.index(k) + 1]) if k in rest else d  # noqa: E731
            return evolve(role, variants=opt("--variants", 3), generations=opt("--generations", 1),
                          prompt_name=opt("--prompt", "") or None)
        if cmd == "api":
            ap = argparse.ArgumentParser(prog="python -m team api")
            ap.add_argument("--port", type=int, default=8766)
            ap.add_argument("--host", default="127.0.0.1")
            ap.add_argument("--until-done", type=int, default=0, help="follow-up rounds for anything left undone")
            ap.add_argument("--workers", type=int, default=1, help="jobs at once (they share the loaded models)")
            o = ap.parse_args(rest)
            from .api import main as api
            return api(o.port, o.host, o.until_done, workers=o.workers)
        if cmd == "web":
            from .web import main as web
            return web(int(rest[0]) if rest else 8765)
        if cmd == "serve":
            from .serve import serve
            return serve(port=int(rest[rest.index("--port") + 1]) if "--port" in rest else 8766)
        if cmd == "projects":
            from .project import status_text
            return print(status_text())
        if cmd == "project":
            from . import project, sdk
            sw = sdk.Swarm(approve="never")
            if rest and rest[0] == "--resume":
                ps = project.open_projects() if len(rest) == 1 else [project.Project.load(rest[1])]
                for p in ps:
                    print(p.run(sw))
                return 0
            p = project.Project.start(" ".join(rest))
            print(project.started_text(p))
            return print(p.run(sw))
        if cmd == "install":
            from .service import install
            return install(dry_run="--dry-run" in rest)
        if cmd == "uninstall":
            from .service import uninstall
            return uninstall()
        if cmd == "add":
            from .serve import add
            return print("queued:", add(" ".join(rest)))
        if cmd == "dream":
            from .dream import dream
            n = int(rest[rest.index("--rehearse") + 1]) if "--rehearse" in rest else 2
            return dream(train="--no-train" not in rest, rehearse_n=n)
        if cmd == "grow":  # CPU-heavy training: its own process, like the other trainers
            import subprocess
            from . import config
            return subprocess.run([sys.executable, str(config.ROOT / "training" / "cells_grow.py"), *rest]).returncode
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
    ap.add_argument("--until-done", type=int, default=0, metavar="N",
                    help="up to N follow-up rounds for instructions or steps left undone (runs as a job in runs/)")
    a = ap.parse_args()
    task = open(a.file).read() if a.file else a.task
    if not task:
        ap.error("give a task")
    import signal

    from . import stop
    from .hive import Hive

    def on_ctrl_c(sig, frame):  # first Ctrl+C: kill switch (clean stop + record); second: exit at once
        if stop.requested():
            raise SystemExit(130)
        stop.request("terminal: Ctrl+C")
        print("\n*** stopping every specialist now (Ctrl+C again to exit immediately)", flush=True)

    signal.signal(signal.SIGINT, on_ctrl_c)
    if a.until_done:
        from .sdk import Swarm
        job = Swarm(approve=a.approve).submit(task, until_done=a.until_done, allow_login=a.allow_login)
        job.wait()  # the board prints each event as it happens
        print("\n" + "=" * 70 + "\n" + job.report[:6000])
        print(f"\nJob folder: {job.dir} ({len(job.rounds)} round(s)); still undone: {job.unmet or 'nothing'}")
        if job.pending_approvals:
            print("Waiting on you:", json.dumps(job.pending_approvals, indent=1))
        return None
    out = Hive(task, a.run_dir, a.approve, a.allow_login).run()
    print("\n" + "=" * 70 + "\n" + (out["report"] or "")[:6000])
    print("\nRun folder:", out["dir"])
    if out["pending_approvals"]:
        print("Waiting on you:", json.dumps(out["pending_approvals"], indent=1))


if __name__ == "__main__":
    main()
