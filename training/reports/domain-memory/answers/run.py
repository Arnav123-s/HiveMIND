"""Replay frozen questions through an installed checkout's real talk.reply with a CPU model."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ARM_SWITCHES = {
    "baseline": ("0", "0"), "integrated": ("1", "1"),
    "signal_only": ("1", "0"), "engram_only": ("0", "1"), "scope_followup": ("1", "1"),
}


def save(path, row):
    path.write_text(json.dumps(row, indent=2, ensure_ascii=False) + "\n")


def worker(args):
    sys.path.insert(0, str(args.checkout))
    from team import talk, ternary

    tasks = json.loads((HERE / "panel.json").read_text())
    task = next(t for t in tasks if t["id"] == args.case)
    directory = args.out / args.arm / task["id"]
    # Save the emitted route before generation so a later work timeout cannot erase it.
    if os.environ.get("HIVE_SIGNALS") == "1":
        from team import domain_consensus

        route = domain_consensus.read_consensus
        def observed_route(*args, **kwargs):
            decision = route(*args, **kwargs)
            save(directory / "route.json", decision)
            return decision
        domain_consensus.read_consensus = observed_route
    if os.environ.get("HIVE_ENGRAMS") == "1":
        from team import domain_advice

        choose_work = talk.route
        def observed_work(*args, **kwargs):
            way, messages = choose_work(*args, **kwargs)
            save(directory / "work-choice.json", way)
            return way, messages
        talk.route = observed_work
        consult = domain_advice.consult
        def observed_advice(*args, **kwargs):
            decision = consult(*args, **kwargs)
            save(directory / "advice.json", decision)
            return decision
        domain_advice.consult = observed_advice
    # An isolated port lets the ordinary native server run beside other CPU jobs.
    ternary.port = lambda member: args.port
    original = ternary._ask
    calls = []

    def measured(member, at, cell, path, body, pieces):
        started = time.monotonic()
        response = original(member, at, cell, path, body | {"seed": 87361 + len(calls)}, pieces)
        active = {k: v for k, v in ternary._loaded(at, scales=True).items() if v}
        event = dict(member=member, active_cell=cell, native_active=active, requested_tokens=pieces,
                     used=response.get("usage"), seconds=round(time.monotonic() - started, 2))
        calls.append(event)
        with (directory / "calls.jsonl").open("a") as stream:
            stream.write(json.dumps(event) + "\n")
        return response

    ternary._ask = measured
    start = time.monotonic()
    try:
        result = talk.reply(task["prompt"], run_dir=str(directory / "work"), name="the user")
        fields = {"text", "worked", "agreed", "domain_signal", "engram_advice", "saved", "engrams"}
        row = {k: v for k, v in result.items() if k in fields}
    except Exception as exc:
        row = {"error": f"{type(exc).__name__}: {exc}"}
    row.update(id=task["id"], arm=args.arm, seconds=round(time.monotonic() - start, 2), model_calls=calls)
    save(directory / "reply.json", row)


def run(args):
    signals, engrams = ARM_SWITCHES[args.arm]
    env = os.environ | {
        "HIVE_SIGNALS": signals, "HIVE_ENGRAMS": engrams, "HIVE_BANK": "off",
        "HIVE_LIGHT": "1", "AGENT_TEAM_THREADS": "2", "AGENT_TEAM_SOLO": "2", "AGENT_TEAM_SOLO_ALONE": "1",
        "AGENT_TEAM_SOLO_TURNS": "2", "AGENT_TEAM_SOLO_LONG": "120", "HIVE_TALK_LONG": "80",
        "HIVE_TERNARY_CTX": "4096", "HIVE_TERNARY_RESTARTS": "1", "HF_HUB_OFFLINE": "1",
        "HIVE_LIBRARY": "0", "HIVE_NOTES": "0", "TZ": "UTC",
    }
    tasks = json.loads((HERE / "panel.json").read_text())
    if args.only and not set(args.only) <= {t["id"] for t in tasks}:
        raise ValueError("the requested subset contains an unknown task")
    for task in tasks:
        ident = task["id"]
        if args.only and ident not in args.only:
            continue
        dest = args.out / args.arm / ident
        dest.mkdir(parents=True, exist_ok=True)
        if (dest / "reply.json").exists():
            continue
        command = [sys.executable, str(Path(__file__).resolve()), "--checkout", str(args.checkout),
                   "--out", str(args.out), "--arm", args.arm, "--port", str(args.port), "--case", ident]
        start = time.monotonic()
        with (dest / "process.log").open("w") as log:
            try:
                proc = subprocess.run(command, env=env, cwd=args.checkout, stdout=log,
                                      stderr=subprocess.STDOUT, timeout=args.seconds)
                if not (dest / "reply.json").exists():
                    raise RuntimeError(f"exit {proc.returncode}; see process log")
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                save(dest / "reply.json", dict(id=ident, arm=args.arm, error=str(exc),
                                                seconds=round(time.monotonic() - start, 2)))
        print(args.arm, ident, round(time.monotonic() - start, 1), flush=True)


def routes(args):
    sys.path.insert(0, str(args.checkout))
    from team import domain_route, signals

    os.environ["HIVE_SIGNALS"] = "1"
    rows = []
    for task in json.loads((HERE / "panel.json").read_text()):
        message = task["prompt"]
        sender = signals.read_request(message)
        with domain_route.for_request(message) as serving:
            rows.append(dict(id=task["id"], expected=task["domain"], sender=sender, serving_consensus=serving))
    args.out.mkdir(parents=True, exist_ok=True)
    save(args.out / "routing.json", rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--arm", choices=ARM_SWITCHES)
    parser.add_argument("--routes-only", action="store_true", help="evaluate all frozen routing decisions without an LLM")
    parser.add_argument("--port", type=int, default=18214)
    parser.add_argument("--case", help=argparse.SUPPRESS)
    parser.add_argument("--only", nargs="+", help="subset of the frozen task IDs; default is the whole panel")
    parser.add_argument("--seconds", type=int, default=150)
    args = parser.parse_args()
    args.checkout = args.checkout.resolve()
    args.out = args.out.resolve()
    if args.routes_only:
        return routes(args)
    if not args.arm:
        parser.error("--arm is required for the live model comparison")
    return worker(args) if args.case else run(args)


if __name__ == "__main__":
    main()
