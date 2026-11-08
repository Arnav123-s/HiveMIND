"""Evolution harness: specialists whose job is improving the other specialists.

  examiner      reads real failures (held-out eval cases the role got wrong, and failed steps in past runs)
                and writes a one-line diagnosis of each
  prompt-smith  breeds variants of the role's system prompt aimed at those diagnoses
  trainer       for the 1.7B roles, retrains the role's weight edit from new verified examples (see dream.py)
  selector      scores parent and every variant on the role's held-out evals and promotes a variant only if it
                scores strictly higher; every candidate, score and decision is logged (lineage)

    python -m team evolve verifier [--variants 3] [--generations 1] [--prompt VERIFIER]

Winners are written to team/evolved/<PROMPT>.txt, which team/prompts.py loads in place of the default.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from . import config, llm, memory, prompts

ROLES = {  # role -> (prompt constants it uses, eval suites that measure it)
    "coordinator": (["COORDINATOR"], ["coordinator"]),
    "researcher": (["RESEARCHER_EXTRACT", "RESEARCHER_PLAN"], ["researcher_extract", "researcher_plan"]),
    "browser": (["BROWSER"], ["browser"]),
    "verifier": (["VERIFIER", "VERIFIER_FACT"], ["verifier"]),
    "writer": (["WRITER"], ["writer"]),
    "coder": (["CODER"], ["coder"]),
}
WORK = config.ROOT / "training" / "runs" / "evolve"
LOG = memory.HOME / "evolution.jsonl"


def score(role, tag, env_extra=None):
    """Run the role's held-out evals in a fresh process (so prompt overrides apply) and return (mean, report)."""
    llm.unload_all()  # give the scoring process the RAM
    env = dict(os.environ, **(env_extra or {}))
    suites = ROLES[role][1]
    subprocess.run([sys.executable, str(config.ROOT / "training" / "observe.py"), "--tag", tag, "--only", *suites],
                   env=env, check=True, capture_output=True)
    rep = json.loads((config.ROOT / "training" / "reports" / f"{tag}.json").read_text())
    vals = [rep["scores"][s]["mean"] for s in suites if s in rep["scores"]]
    return (sum(vals) / len(vals) if vals else 0.0), rep


# ------------------------------------------------------------------ examiner
def examine(role, report, max_cases=6):
    """One-line diagnosis per failure: from the eval report, then from failed steps in real runs."""
    failures = []
    for suite in ROLES[role][1]:
        for c in report["cases"].get(suite, []):
            if c["score"] < 1:
                failures.append(f"Case: {c['case'][:200]}\nIts reply: {str(c['output'])[:400]}\n"
                                f"Checks failed: {[k for k, v in (c.get('checks') or {}).items() if not v] or 'wrong answer'}")
    if config.RUNS.exists():
        for run in sorted(config.RUNS.iterdir())[-10:]:
            db = run / "board.db"
            if not db.exists():
                continue
            con = sqlite3.connect(db)
            for task, fb in con.execute("SELECT task, feedback FROM steps WHERE agent=? AND verdict='FAIL'", (role,)):
                failures.append(f"Real run step: {task[:200]}\nWhy it was rejected: {str(fb)[:300]}")
    out = []
    for f in failures[:max_cases]:
        d = llm.chat("examiner", [{"role": "system", "content": "You are the examiner in the team's evolution harness. "
                                   "Say in ONE sentence what the specialist did wrong and what rule would have prevented it."},
                                  {"role": "user", "content": f"Specialist: {role}\n{f}"}], max_new_tokens=80)
        out.append(d.strip().split("\n")[0][:300])
    return out


# ------------------------------------------------------------------ prompt-smith
FORMAT_LINE = re.compile(r"(reply with json|^\s*\{|^\s*-\s*\w+:|output only)", re.I)


def breed(name, parent, diagnoses, n):
    variants = []
    for i in range(n):
        txt = llm.chat("prompt_smith", [
            {"role": "system", "content": prompts.PROMPT_SMITH},
            {"role": "user", "content": f"CURRENT PROMPT ({name}):\n<<<\n{parent}\n>>>\n\nMISTAKES SEEN:\n"
                                        + "\n".join(f"- {d}" for d in diagnoses) +
                                        f"\n\nWrite variant {i + 1} of {n}: " +
                                        ["add precise rules for the mistakes",
                                         "add one short correct example",
                                         "rewrite more clearly and strictly"][i % 3]}],
            max_new_tokens=900, temperature=0.7)
        txt = txt.replace("<<<", "").replace(">>>", "").strip()
        # never lose the reply format: re-attach any format line the variant dropped
        missing = [ln for ln in parent.splitlines() if FORMAT_LINE.search(ln) and ln.strip() not in txt]
        if missing:
            txt += "\n" + "\n".join(missing)
        if len(txt) > 80:
            variants.append(txt)
    return variants


# ------------------------------------------------------------------ selector
def evolve(role, variants=3, generations=1, prompt_name=None, margin=0.0):
    names, _ = ROLES[role]
    name = prompt_name or names[0]
    WORK.mkdir(parents=True, exist_ok=True)
    parent = getattr(prompts, name)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    lineage = {"role": role, "prompt": name, "started": stamp, "generations": []}
    parent_score, report = score(role, f"evo-{role}-{stamp}-g0-parent")
    print(f"[evolve] {role}/{name} parent score {parent_score:.3f}", flush=True)
    for g in range(1, generations + 1):
        diagnoses = examine(role, report)
        print(f"[evolve] examiner: {len(diagnoses)} diagnoses", flush=True)
        kids = breed(name, parent, diagnoses, variants)
        gen = {"generation": g, "parent_score": round(parent_score, 3), "diagnoses": diagnoses, "candidates": []}
        best = (parent_score, parent, report, None)
        for i, kid in enumerate(kids):
            path = WORK / f"{role}-{stamp}-g{g}-v{i + 1}-{name}.txt"
            path.write_text(kid)
            sc, rep = score(role, f"evo-{role}-{stamp}-g{g}-v{i + 1}", {f"AGENT_TEAM_PROMPT_{name}": str(path)})
            print(f"[evolve] g{g} v{i + 1}: {sc:.3f}", flush=True)
            gen["candidates"].append({"variant": i + 1, "score": round(sc, 3), "file": str(path.relative_to(config.ROOT))})
            if sc > best[0] + margin:
                best = (sc, kid, rep, i + 1)
        gen["winner"] = best[3] or "parent"
        lineage["generations"].append(gen)
        if best[3]:
            parent_score, parent, report = best[0], best[1], best[2]
    promoted = parent != getattr(prompts, name)
    if promoted:
        (config.ROOT / "team" / "evolved" / f"{name}.txt").write_text(parent)
    lineage.update(final_score=round(parent_score, 3), promoted=promoted, finished=time.strftime("%Y%m%d-%H%M%S"))
    (config.ROOT / "training" / "reports" / f"evolution_{role}.json").write_text(json.dumps(lineage, indent=1))
    with open(LOG, "a") as f:
        f.write(json.dumps({k: lineage[k] for k in ("role", "prompt", "started", "final_score", "promoted")}) + "\n")
    print(json.dumps({k: lineage[k] for k in ("role", "prompt", "final_score", "promoted")}), flush=True)
    return lineage
