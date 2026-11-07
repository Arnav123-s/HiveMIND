"""Dreaming: what the team does while Arnav isn't asking it for anything.

1. Replay   - read every past run (board + recorded model calls).
2. Lessons  - turn each verified failure into a short rule the team reads next time.
3. Rehearse - re-attempt failed steps with today's weights + lessons; keep wins.
4. Distil   - every model call inside a step the verifier PASSED becomes a
              training example for that specialist (its own verified work).
5. Retrain  - when a specialist has enough new examples, train a candidate
              weight edit, score it on the held-out evals, and promote it only
              if it does not score lower than the current weights.

    python -m team dream [--no-train] [--rehearse N]
"""
import hashlib
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from . import config, llm, memory

SELF = config.ROOT / "training" / "data" / "self"
SELF.mkdir(parents=True, exist_ok=True)
SUITES = {"coordinator": ["coordinator"], "researcher": ["researcher_plan", "researcher_extract"],
          "browser": ["browser"], "verifier": ["verifier"], "writer": ["writer"], "coder": ["coder"]}
MIN_NEW = 12


def _runs():
    if not config.RUNS.exists():
        return []
    return sorted(p for p in config.RUNS.iterdir() if (p / "board.db").exists())


def _steps(run):
    db = sqlite3.connect(run / "board.db")
    db.row_factory = sqlite3.Row
    return {r["id"]: dict(r) for r in db.execute("SELECT * FROM steps")}


def _seen():
    f = SELF / "_seen.txt"
    return set(f.read_text().split()) if f.exists() else set()


def distil(log):
    seen, new = _seen(), {}
    for run in _runs():
        calls = run / "calls.jsonl"
        if not calls.exists():
            continue
        steps = _steps(run)
        for line in calls.read_text().splitlines():
            c = json.loads(line)
            st = steps.get(c["step"])
            ok = (st and st.get("verdict") == "PASS") or (c["step"] == "plan" and steps and
                                                          sum(s.get("verdict") == "PASS" for s in steps.values()) >= 0.7 * len(steps))
            if not ok:
                continue
            h = hashlib.sha1((c["specialist"] + json.dumps(c["messages"]) + c["output"]).encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            new.setdefault(c["specialist"], []).append({"messages": c["messages"], "output": c["output"]})
    for spec, rows in new.items():
        with open(SELF / f"{spec}.jsonl", "a") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (SELF / "_seen.txt").write_text("\n".join(sorted(seen)))
    log["distilled"] = {k: len(v) for k, v in new.items()}
    return new


def lessons(log):
    n = 0
    for run in _runs():
        for sid, st in _steps(run).items():
            if st.get("verdict") != "FAIL" or not st.get("feedback"):
                continue
            prompt = [{"role": "system", "content": "Turn a failure report into ONE short rule (max 25 words) that would "
                                                    "prevent it next time. Reply with the rule only."},
                      {"role": "user", "content": f"Specialist: {st['agent']}\nTask: {st['task'][:300]}\n"
                                                  f"Why it was rejected: {st['feedback'][:300]}"}]
            rule = llm.chat("writer", prompt, max_new_tokens=60).strip().split("\n")[0][:220]
            if rule:
                memory.add_lesson(st["agent"], rule, st["task"], source=f"{run.name}/{sid}")
                n += 1
    log["lessons"] = n


def rehearse(log, limit=3):
    """Re-run failed tasks from past runs (approvals are never granted while dreaming)."""
    from .hive import Hive
    failed = []
    for run in _runs()[-10:]:
        if run.name.startswith("dream-"):
            continue
        steps = _steps(run)
        if any(s.get("verdict") == "FAIL" for s in steps.values()):
            failed.append((run / "TASK.md").read_text().strip())
    done = []
    for goal in list(dict.fromkeys(failed))[:limit]:
        out = Hive(goal, config.RUNS / f"dream-{time.strftime('%Y%m%d-%H%M%S')}", approve="never").run()
        done.append({"goal": goal[:120], "dir": out["dir"]})
    log["rehearsed"] = done


def _score(tag, spec, adapters_dir=None):
    env = dict(**__import__("os").environ, AGENT_TEAM_ENGINE="hf")  # edits are trained and scored on PyTorch
    if adapters_dir:
        env["AGENT_TEAM_ADAPTERS"] = str(adapters_dir)
    cmd = [sys.executable, str(config.ROOT / "training" / "observe.py"), "--tag", tag, "--only", *SUITES[spec]]
    subprocess.run(cmd, env=env, check=True, capture_output=True)
    rep = json.loads((config.ROOT / "training" / "reports" / f"{tag}.json").read_text())
    vals = [rep["scores"][s]["mean"] for s in SUITES[spec] if s in rep["scores"]]
    return sum(vals) / len(vals) if vals else 0.0


def retrain(log, force=False):
    results = {}
    for spec in SUITES:
        f = SELF / f"{spec}.jsonl"
        n_self = sum(1 for _ in open(f)) if f.exists() else 0
        meta_path = config.ADAPTERS / spec / "training_meta.json"
        trained_on = json.loads(meta_path.read_text()).get("self_examples", 0) if meta_path.exists() else 0
        if n_self - trained_on < MIN_NEW and not force:
            continue
        cand_root = config.ROOT / "adapters_candidates"
        cand = cand_root / spec
        cmd = [sys.executable, str(config.ROOT / "training" / "train_lora.py"), spec, "--out", str(cand)]
        subprocess.run(cmd, check=True, capture_output=True)
        before = _score(f"dream-before-{spec}", spec)
        after = _score(f"dream-after-{spec}", spec, adapters_dir=cand_root)
        promoted = after >= before
        if promoted:
            backup = config.ADAPTERS / ".previous" / f"{spec}-{time.strftime('%Y%m%d-%H%M%S')}"
            backup.parent.mkdir(exist_ok=True)
            if (config.ADAPTERS / spec).exists():  # keep every old version; nothing is deleted
                (config.ADAPTERS / spec).rename(backup)
            cand.rename(config.ADAPTERS / spec)
            m = json.loads((config.ADAPTERS / spec / "training_meta.json").read_text())
            m["self_examples"] = n_self
            (config.ADAPTERS / spec / "training_meta.json").write_text(json.dumps(m, indent=1))
            # the llama.cpp engine loads edits as GGUF LoRAs
            subprocess.run(["bash", str(config.ROOT / "training" / "to_gguf.sh"), spec], capture_output=True)
        results[spec] = {"before": round(before, 3), "after": round(after, 3), "promoted": promoted, "self_examples": n_self}
    log["retrain"] = results


def dream(train=True, rehearse_n=2):
    log = {"started": time.strftime("%F %T")}
    distil(log)
    lessons(log)
    if rehearse_n:
        rehearse(log, rehearse_n)
        distil(log)
    if train:
        retrain(log)
    log["finished"] = time.strftime("%F %T")
    memory.log_dream(log)
    print(json.dumps(log, indent=1))
    return log
