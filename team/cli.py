"""hive: talk to the swarm like to an assistant. One prompt, then a normal conversation; it does the rest.

    hive "find the three cheapest Mystery books on books.toscrape.com and save them to a CSV"
    hive                                  start talking
After each answer you just keep talking: "now make it a table", "thanks", "why that one?", "stop", "remember that I
prefer prices in INR". Each message is answered at once when the conversation already holds the answer, or becomes a
hive job (looking things up, websites, code, files, calculations, writing) that runs until nothing is left undone
(team/converse.py). Your words are the order: what they order (buy, delete, send, log in, sign up) is approved by the
order itself; anything risky they do not order stops and asks you (or, unattended, is refused and listed).
When the always-on agent runs (python -m team install / serve), the conversation goes to it: the models are loaded
there and a job keeps running if you close the terminal.
Options: --once (answer the prompt and exit, for scripts), --rounds N (follow-up rounds per job, default 2),
--unattended (never stop to ask), --local (run in this terminal even when the service is up).
Ctrl+C is the kill switch: every running job stops; Ctrl+C again exits. "exit" or Ctrl+D leaves.
"""
import argparse
import json
import os
import signal
import sys
import time

SHOW = {"assign", "triage", "plan", "pass", "fail", "give-up", "reroute", "retry", "decompose", "gap", "conflict", "drop",
        "format", "escalate", "kept", "nothing-verified", "same-error", "error-kind", "file-check", "form", "echo", "weekday", "examples", "finished", "round",
        "approval", "refused", "stopped"}
SERVICE = os.environ.get("HIVE_URL", "http://127.0.0.1:8766")
EXIT = {"exit", "quit", "/exit", "/quit", ":q"}


def line(e):
    """One event as a short progress line."""
    t = time.strftime("%H:%M:%S", time.localtime(e.get("ts", time.time())))
    return f"  {t}  {e.get('agent', ''):<14} {e.get('kind', ''):<9} {str(e.get('msg', ''))[:150]}"


def show(job, out=print):
    """Progress while a job works, then its answer, files and run folder. Returns the answer."""
    out(f"hive: on it (job {job.id})")
    for e in job.events(follow=True, poll=0.5):
        if e.get("kind") in SHOW or e.get("agent", "").startswith("cell:task_kind"):
            out(line(e))
    job.wait()
    answer = (job.report or job.error or "(no report)").strip()
    out("\n" + answer)
    if job.files:
        out("\nFiles:\n" + "\n".join(f"  {f}" for f in job.files))
    if job.unmet:
        out(f"\nStill not done after {len(job.rounds)} round(s): " + "; ".join(job.unmet[:5]))
    if job.pending_approvals:
        out("\nNeeds your approval (not done): " + "; ".join(str(p) for p in job.pending_approvals[:5]))
    out(f"\n(job {job.id}: {job.status}, run folder {job.dir})")
    return answer


def run_prompt(swarm, prompt, rounds=2, context="", out=print):
    """One prompt as a job, shown as it works. Returns the job."""
    job = swarm.submit(prompt, until_done=rounds, context=context)
    show(job, out)
    return job


def say(swarm, msg, history, rounds=2, out=print):
    """One message of a local conversation: answered at once, or a job shown as it works. Returns the answer."""
    from . import converse
    if not converse.on():
        return show(swarm.submit(msg, until_done=rounds, context=converse.context(history)), out)
    from . import project
    res = converse.handle(msg, history, lambda t, c: swarm.submit(t, until_done=rounds, context=c),
                          start_project=lambda g: project.launch(g, swarm, log=lambda m: out("  [project] " + m)))
    if isinstance(res, converse.Reply):
        out("hive> " + res.report)
        return res.report
    return show(res, out)


# ---- the always-on service ------------------------------------------------------------------------------------
def service_up(url=None, timeout=0.5):
    """Is the always-on service answering?"""
    import urllib.request
    try:
        with urllib.request.urlopen((url or SERVICE) + "/health", timeout=timeout) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def _call(method, path, body=None, url=None, timeout=30):
    import urllib.request
    key = os.environ.get("AGENT_TEAM_API_KEY")
    req = urllib.request.Request((url or SERVICE) + path, json.dumps(body).encode() if body is not None else None,
                                 {"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})},
                                 method=method)
    return urllib.request.urlopen(req, timeout=timeout)


def say_remote(msg, history, rounds=2, out=print, url=None):
    """One message of a conversation on the always-on service (its chat endpoint decides talk or work)."""
    msgs = [{"role": r, "content": t} for r, t in history] + [{"role": "user", "content": msg}]
    answer = []
    with _call("POST", "/v1/chat/completions", {"model": "hivemind", "stream": True, "messages": msgs,
                                                 "until_done": rounds}, url, timeout=None) as r:
        for raw in r:
            ln = raw.decode("utf-8", "replace").strip()
            if not ln.startswith("data: {"):
                continue
            delta = json.loads(ln[6:])["choices"][0]["delta"]
            if delta.get("reasoning_content"):  # the hive at work
                out("  " + delta["reasoning_content"].rstrip())
            if delta.get("content"):
                answer.append(delta["content"])
    text = "".join(answer).strip()
    out("\n" + text if len(text) > 300 or "\n" in text else "hive> " + text)
    return text


def run_remote(prompt, rounds=2, context="", out=print, url=None):
    """A prompt as a job on the service, shown as it works (the job API). Returns the finished job as a dict."""
    with _call("POST", "/v1/jobs", {"task": prompt, "until_done": rounds, "context": context}, url) as r:
        job = json.loads(r.read())
    out(f"hive: job {job['id']} on the always-on service")
    with _call("GET", f"/v1/jobs/{job['id']}/events", url=url, timeout=None) as r:
        event = None
        for raw in r:
            ln = raw.decode("utf-8", "replace").rstrip("\n")
            if ln.startswith("event: "):
                event = ln[7:]
            elif ln.startswith("data: "):
                d = json.loads(ln[6:])
                if event == "done":
                    job = d
                    break
                if d.get("kind") in SHOW or str(d.get("agent", "")).startswith("cell:task_kind"):
                    out(line(d))
                event = None
    out("\n" + (job.get("report") or "(no report)").strip())
    if job.get("files"):
        out("\nFiles:\n" + "\n".join(f"  {f}" for f in job["files"]))
    out(f"\n(job {job['id']}: {job.get('status')}, run folder {job.get('dir')})")
    return job


# ---- the conversation -------------------------------------------------------------------------------------------
def converse_loop(first, step, inp=input, out=print, keep_going=True):
    """The conversation: the first prompt (if any), then message after message. step(msg, history) -> answer."""
    history = []
    if not first:
        out("hive: what should I do? (just talk; 'exit' to leave, Ctrl+C stops a running job)")
    msg = first
    while True:
        if not msg:
            if not keep_going and history:
                break
            try:
                msg = inp("\nyou> ").strip()
            except EOFError:
                break
            if not msg:
                continue
        if msg.lower() in EXIT:
            break
        answer = step(msg, history)
        history += [("user", msg), ("assistant", (answer or "")[:1500])]
        msg = None
        if not keep_going:
            break
    return history


def session(swarm, rounds, inp=input, out=print):
    """A local conversation with no opening prompt (kept for callers)."""
    return converse_loop(None, lambda m, h: say(swarm, m, h, rounds, out), inp, out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hive", description="Talk to the swarm; it does the job.")
    ap.add_argument("prompt", nargs="*", help="what you want, in your own words (none: just start talking)")
    ap.add_argument("--once", action="store_true", help="answer the prompt and exit (scripts)")
    ap.add_argument("--rounds", type=int, default=2, help="follow-up rounds per job for anything left undone")
    ap.add_argument("--unattended", action="store_true",
                    help="never stop to ask: risky actions you did not order are refused and listed at the end")
    ap.add_argument("--local", action="store_true", help="run in this terminal even when the always-on service is up")
    ap.add_argument("--file", help="read the first prompt from a file")
    a = ap.parse_args(argv)
    first = (open(a.file).read() if a.file else " ".join(a.prompt)).strip() or None
    keep_going = not a.once and sys.stdin.isatty()
    if first is None and not sys.stdin.isatty():  # piped in: the whole input is the prompt
        first, keep_going = sys.stdin.read().strip() or None, False
    if not a.local and service_up():  # the always-on agent has the models loaded: the conversation goes there
        def step(msg, history):
            try:
                return say_remote(msg, history, a.rounds)
            except KeyboardInterrupt:
                _call("POST", "/v1/stop", {})
                print("\n*** kill switch sent: every running job stops now")
                return "(stopped)"
        converse_loop(first, step, keep_going=keep_going)
        return 0
    from . import sdk, stop
    swarm = sdk.Swarm(approve="never" if a.unattended or not sys.stdin.isatty() else "ask")

    def on_ctrl_c(sig, frame):  # first: kill switch (every specialist stops, what was finished is kept); second: exit
        if stop.requested():
            raise SystemExit(130)
        stop.request("hive: Ctrl+C")
        print("\n*** stopping every specialist now (Ctrl+C again to exit immediately)", flush=True)
    signal.signal(signal.SIGINT, on_ctrl_c)
    converse_loop(first, lambda m, h: say(swarm, m, h, a.rounds), keep_going=keep_going)
    return 0


if __name__ == "__main__":
    sys.exit(main())
