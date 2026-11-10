"""One turn of the hive's life: notice new jobs, grow cells for them, check the working cells, retire the bad ones.

    python -m team life [--min 200] [--rehearse 200] [--quick] [--runs DIR ...] [--bench] [--no-train]

1. notice   read every logged member call; find the call sites that are small decisions (team/cells/spawn.py);
            declare the ones with at least --min distinct decisions as spawned skills
2. review   every working spawned cell: its agreement with its member on audited live calls; under 93% it is retired
3. grow     practice first: up to --rehearse (200) new inputs recombined from the job's older real ones, decided by
            the member itself (training only; a cell is judged on real decisions). Then train a cell for every new job, for every failed or retired one whose log grew by half since, and for
            every working one whose log grew by a quarter (so a cell keeps up with new data); each training runs in
            its own process and the gate decides (training/cells_spawn.py)
4. report   cells/LIFE.md: every site, what the member spends there, whether it is a job, and who holds it

The always-on agent (python -m team serve) runs a turn when the device is idle and healthy.
"""
import json
import subprocess
import sys
import time

from . import config, memory
from .cells import runtime, spawn, use

REPORT = runtime.CELLS / "LIFE.md"
LOG = memory.HOME / "life.jsonl"


def due(name, sp):
    """Why this spawned skill should be (re)trained now, or None."""
    rows, st = sp.get("rows", 0), sp.get("status")
    if st == "candidate":
        return "new job"
    if st in ("failed", "retired") and rows >= 1.5 * max(1, sp.get("rows_at_fail", rows)):
        return f"{st}, and its log grew from {sp.get('rows_at_fail')} to {rows} decisions"
    trained = runtime.registry().get(name, {}).get("rows_trained", 0)
    if st == "on" and trained and rows >= 1.25 * trained:
        return f"working, and its log grew from {trained} to {rows} decisions"
    return None


def turn(min_rows=200, dirs=None, bench=False, train=True, rehearse=200, quick=False, log=print):
    out = {"started": time.strftime("%F %T"), "trained": {}, "retired": []}
    sites = spawn.notice(min_rows, dirs, bench, log)
    out["sites"] = len(sites)
    out["decision_sites"] = sum(1 for s in sites.values() if s["decision"])
    out["retired"] = [k for k, v in spawn.review(log).items() if v.get("retired")]
    for name, sp in spawn.spawned().items():
        why = due(name, sp)
        if not (why and train):
            continue
        log(f"[life] growing {name}: {why}")
        if rehearse:
            try:
                spawn.rehearse(name, rehearse, log)
            except Exception as e:  # noqa: BLE001 - without practice the cell still trains on the real decisions
                log(f"[life] {name}: no practice ({type(e).__name__}: {str(e)[:120]})")
            from . import llm
            llm.unload_all()  # the training process gets the RAM
        r = subprocess.run([sys.executable, str(config.ROOT / "training" / "cells_spawn.py"), name,
                            *(["--quick"] if quick else [])],
                           cwd=config.ROOT, capture_output=True, text=True)
        tail = (r.stdout or "").strip().splitlines()[-1:] or [(r.stderr or "").strip()[-300:]]
        out["trained"][name] = {"why": why, "status": spawn.spawned()[name].get("status"), "result": tail[0]}
        log(f"[life] {tail[0]}")
    out["finished"] = time.strftime("%F %T")
    REPORT.write_text(report(sites))
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps(out) + "\n")
    except OSError:
        pass
    log(json.dumps({k: out[k] for k in ("sites", "decision_sites", "trained", "retired")}, indent=1))
    return out


def report(sites):
    sp, w = spawn.spawned(), use.wins()
    lines = ["# The hive's life: jobs it noticed by itself, and who holds them", "",
             f"Written by `python -m team life` on {time.strftime('%Y-%m-%d %H:%M')} from the members' logged calls.",
             "A site is one member with one instruction. A job is a site whose replies are a few fixed values.", "",
             "## Spawned cells", ""]
    if sp:
        lines += ["| cell | does a job of | labels (it may answer) | decisions | status | newest unseen decisions: answers / agrees | live: answered, audits, agreement |",
                  "|---|---|---|---|---|---|---|"]
        for name, s in sp.items():
            ww, lv = w.get(name, {}), spawn.live(name)
            test = (f"{ww.get('answered')} of {ww.get('test_rows')} ({ww.get('covers', 0):.0%}) / "
                    f"{ww.get('agree_when_sure', 0):.0%}") if "answered" in ww else "not trained yet"
            live = f"{lv['answered']}, {lv['audits']}, {lv['agreement'] if lv['agreement'] is not None else 'no audits yet'}"
            status = s.get("status") + (f": {s.get('failed_why') or s.get('retired_why')}"
                                        if s.get("status") in ("failed", "retired") else "")
            lines.append(f"| {name} | {s['member']} | {' / '.join(s['labels'])} ({', '.join(s['answers'])}) | "
                         f"{s.get('rows')} | {status} | {test} | {live} |")
    else:
        lines.append("None yet.")
    lines += ["", "## Every call site in the logs", "",
              "| member | calls | member time | a job? | why / status | instruction starts |", "|---|---|---|---|---|---|"]
    for s in sorted(sites.values(), key=lambda s: -s["seconds"]):
        head = " ".join(s["system"].split())[:70].replace("|", "/")
        lines.append(f"| {s['specialist']} | {s['calls']} | {s['seconds']:.0f} s | {'yes' if s['decision'] else 'no'} | "
                     f"{s.get('why', '')} | {head} |")
    return "\n".join(lines) + "\n"


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    dirs = []
    if "--runs" in argv:
        for a in argv[argv.index("--runs") + 1:]:
            if a.startswith("--"):
                break
            dirs.append(a)
    turn(min_rows=opt("--min", 200), dirs=dirs or None, bench="--bench" in argv, train="--no-train" not in argv,
         rehearse=opt("--rehearse", 200), quick="--quick" in argv)
    return 0
