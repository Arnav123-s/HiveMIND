"""The smith swarm: members whose job is improving the other members (and each other).

Every job has several smiths with different strategies. They compete; only measured winners are kept; the ledger
(memory/smiths.json) records each smith's wins, and the smith-smith rewrites losing smiths from winning ones.

jobs and what each smith does
  gap_spotter      reads run boards and eval reports -> what keeps failing / keeps coming up
  data_builder     builds training data for a niche (distil verified calls; paraphrase task wording)
  test_writer      writes new held-out tests from real verified runs (labels come from the verifier, not a model)
  internals        finds the layer and direction behind a mistake and edits it there   (training/steer.py)
  weight_trainer   trains weight edits, each smith with its own recipe                  (training/train_lora.py)
  prompt_tuner     breeds better instructions, each smith with its own strategy        (team/evolve.py)
  cloner           clones a member and specializes the clone on a niche
  router_teacher   teaches the hive which member to route a step to (measured wins only)
  retirer          retires members whose measured score falls behind their parent
  smith_smith      improves the smiths themselves: losing smiths are replaced by mutated copies of winners

    python -m team smiths cycle ROLE      one improvement cycle on a role (gap -> tune -> measure -> keep winners)
    python -m team smiths ledger          who is winning
"""
import json
import random
import shutil
import sqlite3
import time
from pathlib import Path

from . import config, llm, memory, prompts

LEDGER = memory.HOME / "smiths.json"
ROUTES = memory.HOME / "routes.json"
MEMBERS = memory.HOME / "members.json"

DEFAULT_SMITHS = [
    {"id": "gap-failures", "job": "gap_spotter", "strategy": "Find the mistakes that repeat most across runs and evals."},
    {"id": "gap-demand", "job": "gap_spotter", "strategy": "Find the kinds of tasks Arnav asks for most that no member is specialised in."},
    {"id": "data-distil", "job": "data_builder", "strategy": "distil: every model call inside a verified step becomes an example."},
    {"id": "data-paraphrase", "job": "data_builder", "strategy": "paraphrase: reword the task part of verified examples; keep the verified answer."},
    {"id": "tests-from-runs", "job": "test_writer", "strategy": "Turn verified browser steps from real runs into page/goal/expected-action tests."},
    {"id": "internals-diff", "job": "internals", "strategy": "Mean hidden-state difference between right and wrong replies, best layer by sweep."},
    {"id": "train-top-half", "job": "weight_trainer", "strategy": "--layers 14-27 --rank 16 --epochs 2"},
    {"id": "train-narrow", "job": "weight_trainer", "strategy": "--layers 20-27 --rank 8 --epochs 3"},
    {"id": "prompt-rules", "job": "prompt_tuner", "strategy": "Add precise rules that would have prevented each mistake."},
    {"id": "prompt-example", "job": "prompt_tuner", "strategy": "Add one short correct worked example of the exact reply format."},
    {"id": "prompt-rewrite", "job": "prompt_tuner", "strategy": "Rewrite the instructions to be shorter, stricter and clearer."},
    {"id": "clone-niche", "job": "cloner", "strategy": "Clone the member that handles a niche and specialise the clone on it."},
    {"id": "router-wins", "job": "router_teacher", "strategy": "Route a step to a specialised member only where it measurably wins."},
    {"id": "retire-behind", "job": "retirer", "strategy": "Retire a member whose score falls behind its parent's."},
    {"id": "smith-of-smiths", "job": "smith_smith", "strategy": "Replace the worst smith of a job with a mutated copy of the best."},
]


# ------------------------------------------------------------------ ledger
def ledger():
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    led = {s["id"]: {**s, "wins": 0, "trials": 0, "born": time.strftime("%F %T"), "parent": None} for s in DEFAULT_SMITHS}
    LEDGER.write_text(json.dumps(led, indent=1))
    return led


def save(led):
    LEDGER.write_text(json.dumps(led, indent=1))


def smiths_for(job):
    return [s for s in ledger().values() if s["job"] == job and not s.get("retired")]


def credit(smith_id, won):
    led = ledger()
    led[smith_id]["trials"] += 1
    led[smith_id]["wins"] += int(bool(won))
    save(led)


def rate(s):
    return (s["wins"] + 1) / (s["trials"] + 2)  # Laplace: new smiths get a fair chance


# ------------------------------------------------------------------ gap spotters
def spot_gaps(max_items=8):
    """Each gap spotter reports what it sees; the union, most frequent first."""
    failures, asks = [], []
    if config.RUNS.exists():
        for run in sorted(config.RUNS.iterdir())[-30:]:
            db = run / "board.db"
            if not db.exists():
                continue
            con = sqlite3.connect(db)
            failures += [f"{a}: {str(fb)[:120]}" for a, fb in con.execute(
                "SELECT agent, feedback FROM steps WHERE verdict='FAIL'")]
            if (run / "TASK.md").exists():
                asks.append((run / "TASK.md").read_text()[:200])
    gaps = {}
    for s in smiths_for("gap_spotter"):
        evidence = failures if "mistake" in s["strategy"] else asks
        if not evidence:
            continue
        out = llm.chat("examiner", [{"role": "system", "content": s["strategy"] + " Reply with up to 5 lines, one gap per "
                                     "line, each starting with the member it concerns (e.g. 'browser: ...')."},
                                    {"role": "user", "content": "\n".join(evidence[:40])}], max_new_tokens=200)
        for line in out.splitlines():
            line = line.strip("-* ").strip()
            if ":" in line and len(line) > 10:
                gaps[line] = gaps.get(line, 0) + 1
    return [g for g, _ in sorted(gaps.items(), key=lambda x: -x[1])][:max_items]


# ------------------------------------------------------------------ data builders
def build_paraphrases(role, n=20):
    """data-paraphrase: reword the TASK part of verified examples (keep the verified answer) so a member stops
    depending on one phrasing (e.g. 'for each of the top 3' confused the browser in a real run)."""
    src = config.ROOT / "training" / "data" / "self" / f"{role}.jsonl"
    rows = [json.loads(x) for x in src.read_text().splitlines()] if src.exists() else []
    out = []
    for r in random.sample(rows, min(n, len(rows))):
        user = r["messages"][-1]["content"]
        head, sep, rest = user.partition("\n")
        new = llm.chat("examiner", [{"role": "system", "content": "Reword this instruction with different words and the "
                                     "same meaning. Keep every name, number and URL exactly. Reply with the instruction only."},
                                    {"role": "user", "content": head}], max_new_tokens=120).strip()
        if new and new != head:
            msgs = r["messages"][:-1] + [{"role": "user", "content": new + sep + rest}]
            out.append({"messages": msgs, "output": r["output"]})
    dst = config.ROOT / "training" / "data" / "self" / f"{role}_paraphrase.jsonl"
    with open(dst, "a") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(out)


# ------------------------------------------------------------------ test writer
def write_field_tests(max_tests=20):
    """tests-from-runs: verified browser 'done' steps from real runs -> held-out field tests (start url, goal,
    evidence that must be found). The label is what the verifier confirmed on the live page, not a model's guess."""
    tests = []
    if config.RUNS.exists():
        for run in sorted(config.RUNS.iterdir()):
            db = run / "board.db"
            if not db.exists():
                continue
            con = sqlite3.connect(db)
            for sid, task, res in con.execute("SELECT id, task, result FROM steps WHERE agent='browser' AND verdict='PASS'"):
                try:
                    r = json.loads(res)
                except (TypeError, json.JSONDecodeError):
                    continue
                if r.get("evidence") and r.get("url", "").startswith("http"):
                    tests.append({"name": f"{run.name}/{sid}", "url": r["url"], "goal": task.split("\n")[0][:300],
                                  "evidence": r["evidence"][:200]})
    path = config.ROOT / "training" / "evals" / "field_browser.json"
    path.write_text(json.dumps(tests[-max_tests:], indent=1, ensure_ascii=False))
    return len(tests[-max_tests:])


# ------------------------------------------------------------------ cloner, router teacher, retirer
def members():
    if MEMBERS.exists():
        return json.loads(MEMBERS.read_text())
    m = {r: {"brain": b, "parent": None, "niche": None, "status": "active"} for r, b in config.GGUF_ROSTER.items()}
    MEMBERS.write_text(json.dumps(m, indent=1))
    return m


def clone(parent, niche, keywords):
    """clone-niche: a new member = copy of the parent's edits, to be specialised on `niche` (trained by a
    weight_trainer smith on niche data). It joins the hive only through the router teacher, i.e. after it wins."""
    m = members()
    name = f"{parent}_{niche}"
    for ext in (".gguf", ".cvec.json"):
        src = config.ROOT / "adapters_gguf" / f"{parent}{ext}"
        if src.exists():
            shutil.copy(src, config.ROOT / "adapters_gguf" / f"{name}{ext}")
    base = config.GGUF_ROSTER.get(parent, config.BRAIN).split("+")[0]
    m[name] = {"brain": f"{base}+{name}", "parent": parent, "niche": niche, "keywords": keywords, "status": "candidate",
               "born": time.strftime("%F %T")}
    MEMBERS.write_text(json.dumps(m, indent=1))
    return name


def teach_route(member, keywords, member_score, parent_score):
    """router-wins: route steps whose task matches `keywords` to `member` only if it beat its parent there."""
    routes = json.loads(ROUTES.read_text()) if ROUTES.exists() else []
    if member_score > parent_score:
        routes = [r for r in routes if r["member"] != member] + [
            {"member": member, "keywords": keywords, "score": member_score, "parent_score": parent_score}]
        ROUTES.write_text(json.dumps(routes, indent=1))
        m = members()
        m[member]["status"] = "active"
        MEMBERS.write_text(json.dumps(m, indent=1))
        return True
    return False


def route(agent, task):
    """The hive asks this before dispatching: is there a specialised member that measurably wins here?"""
    if not ROUTES.exists():
        return agent
    low = task.lower()
    for r in json.loads(ROUTES.read_text()):
        parent = members().get(r["member"], {}).get("parent")
        if parent == agent and any(k.lower() in low for k in r["keywords"]):
            config.GGUF_ROSTER.setdefault(r["member"], members()[r["member"]]["brain"])
            return r["member"]
    return agent


def retire_losers(scores):
    """retire-behind: members scoring below their parent are retired (files kept, roster entry removed)."""
    m, retired = members(), []
    for name, info in m.items():
        p = info.get("parent")
        if p and name in scores and p in scores and scores[name] < scores[p] and info["status"] != "retired":
            info["status"] = "retired"
            retired.append(name)
    MEMBERS.write_text(json.dumps(m, indent=1))
    return retired


# ------------------------------------------------------------------ smith-smith
def improve_smiths(job, min_trials=2):
    """smith-of-smiths: the worst smith of a job (after enough trials) is replaced by a mutated copy of the best."""
    pool = [s for s in smiths_for(job) if s["trials"] >= min_trials]
    if len(pool) < 2:
        return None
    pool.sort(key=rate)
    worst, best = pool[0], pool[-1]
    if rate(best) <= rate(worst):
        return None
    new_strategy = llm.chat("prompt_smith", [
        {"role": "system", "content": "Write a new strategy for an improvement specialist: keep what makes the WINNING "
         "strategy work and add one new idea. One or two sentences only."},
        {"role": "user", "content": f"WINNING: {best['strategy']}\nLOSING: {worst['strategy']}"}], max_new_tokens=90).strip()
    led = ledger()
    led[worst["id"]]["retired"] = True
    nid = f"{best['id']}-g{sum(1 for s in led.values() if s['job'] == job)}"
    led[nid] = {"id": nid, "job": job, "strategy": new_strategy or best["strategy"], "wins": 0, "trials": 0,
                "born": time.strftime("%F %T"), "parent": best["id"]}
    save(led)
    return nid


# ------------------------------------------------------------------ one improvement cycle
def cycle(role, variants_per_smith=1):
    """gap spotters -> prompt tuners compete (each smith breeds its own variant) -> selector measures every
    variant on the held-out evals -> winner kept only if it beats the current member -> ledger credited ->
    smith-smith improves the prompt-tuner pool."""
    from . import evolve
    names, _ = evolve.ROLES[role]
    name = names[0]
    log = {"role": role, "prompt": name, "started": time.strftime("%F %T"), "gaps": spot_gaps(), "entries": []}
    parent = getattr(prompts, name)
    parent_score, report = evolve.score(role, f"smiths-{role}-parent-{time.strftime('%H%M%S')}")
    diagnoses = evolve.examine(role, report) + [g for g in log["gaps"] if g.lower().startswith(role)]
    best = (parent_score, None, None)
    for s in smiths_for("prompt_tuner"):
        for k in range(variants_per_smith):
            txt = llm.chat("prompt_smith", [
                {"role": "system", "content": prompts.PROMPT_SMITH + "\nYour strategy: " + s["strategy"]},
                {"role": "user", "content": f"CURRENT PROMPT ({name}):\n<<<\n{parent}\n>>>\n\nMISTAKES SEEN:\n"
                                            + "\n".join(f"- {d}" for d in diagnoses[:8])}],
                max_new_tokens=900, temperature=0.7).replace("<<<", "").replace(">>>", "").strip()
            missing = [ln for ln in parent.splitlines() if evolve.FORMAT_LINE.search(ln) and ln.strip() not in txt]
            txt += ("\n" + "\n".join(missing)) if missing else ""
            path = evolve.WORK / f"smith-{s['id']}-{role}-{time.strftime('%H%M%S')}.txt"
            evolve.WORK.mkdir(parents=True, exist_ok=True)
            path.write_text(txt)
            sc, _ = evolve.score(role, f"smiths-{role}-{s['id']}-{k}", {f"AGENT_TEAM_PROMPT_{name}": str(path)})
            log["entries"].append({"smith": s["id"], "score": round(sc, 3), "file": str(path.relative_to(config.ROOT))})
            if sc > best[0]:
                best = (sc, s["id"], txt)
    for e in log["entries"]:
        credit(e["smith"], e["smith"] == best[1])
    if best[1]:
        (config.ROOT / "team" / "evolved" / f"{name}.txt").write_text(best[2])
    log.update(parent_score=round(parent_score, 3), winner=best[1] or "current member (no smith beat it)",
               final_score=round(best[0], 3), new_smith=improve_smiths("prompt_tuner"), finished=time.strftime("%F %T"))
    (config.ROOT / "training" / "reports" / f"smiths_{role}.json").write_text(json.dumps(log, indent=1))
    with open(memory.HOME / "smith_cycles.jsonl", "a") as f:
        f.write(json.dumps({k: log[k] for k in ("role", "parent_score", "final_score", "winner", "new_smith")}) + "\n")
    print(json.dumps({k: log[k] for k in ("role", "gaps", "parent_score", "entries", "winner", "new_smith")}, indent=1))
    return log
