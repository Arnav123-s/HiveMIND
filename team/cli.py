"""hive: give the swarm a prompt, the way you would give one to a coding assistant, and it does the job.

    hive "find the three cheapest Mystery books on books.toscrape.com and save them to a CSV"
    hive                                  a session: prompt after prompt, follow-ups keep the conversation
    hive --rounds 0 "..."                 one round only (default: up to 2 follow-up rounds until nothing is left undone)
    hive --unattended "..."               never stop to ask: risky actions you did not order are refused and listed

The prompt is the order, word for word. What it orders (buy, delete, send, log in, sign up) is approved by the order
itself; anything risky it does not order stops and asks you (or, unattended, is refused and listed at the end).
Each prompt runs as a job (runs/<job>/): you see the hive work, then the answer, the files it made and the run folder.
Ctrl+C is the kill switch: every specialist stops now; Ctrl+C again exits.
In a session, earlier prompts and answers are context for the next prompt, never orders.
Session commands: /stop (kill switch), /jobs (recent jobs), /remember <fact> (your profile), /exit.
"""
import argparse
import signal
import sys
import time

SHOW = {"assign", "triage", "plan", "pass", "fail", "give-up", "reroute", "retry", "decompose", "gap", "conflict", "drop",
        "format", "escalate", "kept", "nothing-verified", "same-error", "error-kind", "examples", "finished", "round",
        "approval", "refused", "stopped"}


def line(e):
    """One event as a short progress line."""
    t = time.strftime("%H:%M:%S", time.localtime(e.get("ts", time.time())))
    return f"  {t}  {e.get('agent', ''):<14} {e.get('kind', ''):<9} {str(e.get('msg', ''))[:150]}"


def run_prompt(swarm, prompt, rounds=2, context="", out=print):
    """One prompt as a job: progress while it works, then the answer, files and run folder. Returns the job."""
    job = swarm.submit(prompt, until_done=rounds, context=context)
    out(f"hive: job {job.id} ({'up to ' + str(rounds + 1) + ' rounds' if rounds else 'one round'})")
    for e in job.events(follow=True, poll=0.5):
        if e.get("kind") in SHOW or e.get("agent", "").startswith("cell:task_kind"):
            out(line(e))
    job.wait()
    out("\n" + (job.report or "(no report)").strip())
    if job.files:
        out("\nFiles:\n" + "\n".join(f"  {f}" for f in job.files))
    if job.unmet:
        out(f"\nStill not done after {len(job.rounds)} round(s): " + "; ".join(job.unmet[:5]))
    if job.pending_approvals:
        out("\nNeeds your approval (not done): " + "; ".join(str(p) for p in job.pending_approvals[:5]))
    out(f"\n(job {job.id}: {job.status}, run folder {job.dir})")
    return job


def session(swarm, rounds, inp=input, out=print):
    """Prompt after prompt; earlier turns are context for the next one."""
    from . import memory, stop
    turns = []
    out("hive: give it a job. /exit to leave, /stop for the kill switch, /jobs, /remember <fact>.")
    while True:
        try:
            msg = inp("\nyou> ").strip()
        except EOFError:
            break
        if not msg:
            continue
        if msg in ("/exit", "/quit", "exit", "quit"):
            break
        if msg == "/stop":
            out(stop.request("hive session: /stop"))
            continue
        if msg == "/jobs":
            for j in swarm.list(10):
                out(f"  {j.id}  {j.status:<8} {j.task[:80]}")
            continue
        if msg.startswith("/remember "):
            memory.remember(msg[len("/remember "):])
            out("saved to your profile")
            continue
        context = "\n".join(f"Arnav: {u}\nTeam: {a[:1500]}" for u, a in turns[-4:])
        job = run_prompt(swarm, msg, rounds, context=context, out=out)
        turns.append((msg, (job.report or "")[:1500]))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hive", description="Give the swarm a prompt; it does the job.")
    ap.add_argument("prompt", nargs="*", help="the job, in your own words (none: a session)")
    ap.add_argument("--rounds", type=int, default=2, help="follow-up rounds for anything left undone (default 2)")
    ap.add_argument("--unattended", action="store_true",
                    help="never stop to ask: risky actions you did not order are refused and listed at the end")
    ap.add_argument("--file", help="read the prompt from a file")
    a = ap.parse_args(argv)
    from . import sdk, stop
    approve = "never" if a.unattended or not sys.stdin.isatty() else "ask"
    swarm = sdk.Swarm(approve=approve)

    def on_ctrl_c(sig, frame):  # first: kill switch (every specialist stops, what was finished is kept); second: exit
        if stop.requested():
            raise SystemExit(130)
        stop.request("hive: Ctrl+C")
        print("\n*** stopping every specialist now (Ctrl+C again to exit immediately)", flush=True)
    signal.signal(signal.SIGINT, on_ctrl_c)
    prompt = open(a.file).read() if a.file else " ".join(a.prompt).strip()
    if prompt:
        job = run_prompt(swarm, prompt, a.rounds)
        return 0 if job.status == "done" else 1
    session(swarm, a.rounds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
