"""School: a small model learns a bigger member's job from that member, and takes the job when it does it the same.

    python -m team school [ROLE] [--lessons 160] [--no-train]

The hive's biggest members (the 4B that plans, reads and judges; the 7B that writes programs) hold their jobs because
a small model was measured worse at them. School is how a small model gets the job anyway:

1. lessons    inputs for the job: the real ones from the logs, and new tasks the teacher writes itself
2. teach      the teacher does the job on every lesson; a lesson is kept only if its answer is usable
3. train      the student's weights are edited on the oldest lessons (training/train_lora.py)
4. exam       on the newest lessons, never trained on: how often does the untouched student, and the taught one,
              do what the teacher did? It graduates only if the taught one clears GRADUATE and beats the untouched one.
5. graduate   cells/school.json records it; with AGENT_TEAM_SMALL=1 the role then runs on the taught small model

Without ROLE, the first role that has not graduated is taken (the always-on agent does this when idle). Nothing is
taken on trust: the record holds both exam numbers and the lessons are kept (training/data/school/).
"""
import json
import random
import subprocess
import sys
import time

from . import config, llm

DATA = config.ROOT / "training" / "data" / "school"
RECORD = config.ROOT / "cells" / "school.json"
GRADUATE, MARGIN, MIN_TEST = 0.85, 0.03, 30

WRITE_TASKS = """You write tasks that Arnav might type to his team of AI specialists: a researcher who reads live web \
sources, a browser operator, a coder who writes and runs Python, a calculator, and a writer.
Write one task per line, no numbering, nothing else. Each is one order as he would type it, concrete (real sites, \
real package or model names, real numbers), doable without logging in or paying.
Vary the kind of task: look-ups, lists from a source, scraping to a file, charts, arithmetic, dates, unit \
conversion, translating a sentence he gives, summarising a short text he gives, fixing grammar, short emails, code to \
write, code to fix, explanations."""
TOPICS = ["Python packages on PyPI", "models on Hugging Face", "arXiv papers", "GitHub repositories", "Wikipedia facts",
          "books.toscrape.com and quotes.toscrape.com", "money and percentages", "dates and calendars", "unit conversion",
          "travel", "cooking", "school maths", "physics", "chemistry", "biology", "history", "geography", "health",
          "small business", "emails to colleagues", "German and French sentences", "CSV files and data", "sorting and "
          "searching code", "string handling code", "bugs in short Python snippets", "statistics", "the weather and "
          "climate", "sports results", "music and films", "computers and networks"]


def _plan_key(output, task):
    """What a plan decides: which specialists, in which order."""
    from .specialists import coordinator
    steps, _ = coordinator.normalize(llm.parse_json(output), task)
    return [s["agent"] for s in steps] if steps else None


def _plan_messages(task):
    from .specialists import coordinator
    return coordinator.plan_messages(task)


ROLES = {  # role: its teacher, its student, how a lesson is asked, and what in the answer must match the teacher's
    "coordinator": {"teacher": "brain4b", "student": "fast", "messages": _plan_messages, "key": _plan_key,
                    "tokens": 900, "what": "plans: the same specialists in the same order"},
}


def record():
    try:
        return json.loads(RECORD.read_text())
    except (OSError, ValueError):
        return {}


def graduated():
    """Roles a small model holds after passing its exam: {role: roster entry}."""
    return {r: v["runs_on"] for r, v in record().items() if v.get("graduated") and v.get("runs_on")}


class _as:
    """For the length of a block, the role is done by this model."""

    def __init__(self, role, spec):
        self.role, self.spec = role, spec

    def __enter__(self):
        self.old = config.GGUF_ROSTER.get(self.role)
        config.GGUF_ROSTER[self.role] = self.spec

    def __exit__(self, *a):
        config.GGUF_ROSTER[self.role] = self.old


def logged_tasks():
    """Tasks he (or a drill) really gave: the planner's logged inputs, outside the bench runs."""
    out = []
    for f in sorted((config.ROOT / "runs").rglob("calls.jsonl")):
        if "bench" in f.parts:
            continue  # the bench tasks are what the hive is measured on: never lessons
        for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                c = json.loads(ln)
            except ValueError:
                continue
            m = c.get("messages") or []
            if c.get("specialist") == "coordinator" and c.get("step") == "plan" and len(m) == 2 \
                    and "Task from Arnav:\n" in m[1]["content"]:
                out.append(m[1]["content"].split("Task from Arnav:\n", 1)[1].split("\n\nLessons from earlier runs:")[0].strip())
    return list(dict.fromkeys(out))


def write_tasks(n, have, teacher, log=print, seed=0):
    """The teacher writes new tasks, eight at a time, each call on another topic with other examples."""
    rnd, new, seen = random.Random(seed + len(have)), [], {t.lower() for t in have}
    examples = have or ["What is the latest version of the flask package on PyPI?"]
    tries = 0
    with _as("examiner", teacher):
        while len(new) < n and tries < n:
            tries += 1
            topic = TOPICS[(len(have) + tries) % len(TOPICS)]
            user = (f"Topic: {topic}.\nExamples of his tasks:\n" + "\n".join(rnd.sample(examples, min(4, len(examples))))
                    + "\n\nWrite 8 new tasks, each different from the examples and from each other.")
            text = llm.chat("examiner", [{"role": "system", "content": WRITE_TASKS}, {"role": "user", "content": user}],
                            max_new_tokens=500, temperature=0.8)
            for ln in text.splitlines():
                t = ln.strip(" -*\t0123456789.)")
                if 25 <= len(t) <= 400 and t.lower() not in seen:
                    seen.add(t.lower())
                    new.append(t)
            log(f"[school] the teacher wrote {len(new)} of {n} new tasks", flush=True)
    return new[:n]


def lessons(role):
    f = DATA / f"{role}.jsonl"
    return [json.loads(ln) for ln in f.read_text().splitlines() if ln.strip()] if f.exists() else []


def teach(role, n, log=print):
    """Bring the role's lessons up to n: each a task, the teacher's answer, and what that answer decides."""
    r, have = ROLES[role], lessons(role)
    if len(have) >= n:
        return have
    DATA.mkdir(parents=True, exist_ok=True)
    done = [x["task"] for x in have]
    tasks = [t for t in logged_tasks() if t not in done]
    pool = done + tasks
    extra = (config.ROOT / "training" / "data" / "life_tasks.txt")
    tasks += [t.strip() for t in extra.read_text().splitlines() if t.strip() and t.strip() not in pool] if extra.exists() else []
    need = n - len(have) - len(tasks)
    if need > 0:
        tasks += write_tasks(int(need * 1.15) + 4, done + tasks, r["teacher"], log)
    with _as(role, r["teacher"]), open(DATA / f"{role}.jsonl", "a") as f:
        for t in tasks:
            if len(have) >= n:
                break
            msgs = r["messages"](t)
            out = llm.chat(role, msgs, max_new_tokens=r["tokens"], prefix="{", stop="json")
            key = r["key"](out, t)
            if key is None:
                continue  # the teacher's own answer was unusable: nothing to learn from
            have.append({"task": t, "messages": msgs, "output": out, "key": key})
            f.write(json.dumps(have[-1], ensure_ascii=False) + "\n")
            f.flush()
            if len(have) % 10 == 0:
                log(f"[school] {role}: {len(have)} of {n} lessons taught", flush=True)
    return have


def split(rows):
    k = max(MIN_TEST, len(rows) // 5)
    return rows[:-k], rows[-k:]


def train(role, log=print, epochs=2, rank=8):
    """Edit the student's weights on the older lessons; returns the name of the edit."""
    tr, _ = split(lessons(role))
    name = f"{role}_school"
    f = DATA / f"{role}_train.jsonl"
    f.write_text("".join(json.dumps({"messages": x["messages"], "output": x["output"]}, ensure_ascii=False) + "\n" for x in tr))
    llm.unload_all()  # the training process gets the RAM
    out = config.ADAPTERS / name
    cmd = [sys.executable, str(config.ROOT / "training" / "train_lora.py"), role, "--data", str(f), "--out", str(out),
           "--rank", str(rank), "--epochs", str(epochs)]
    log(f"[school] {role}: training on {len(tr)} lessons", flush=True)
    r = subprocess.run(cmd, cwd=config.ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("training failed: " + (r.stderr or r.stdout)[-600:])
    from huggingface_hub import snapshot_download
    base = snapshot_download(config.SPECIALISTS[role], allow_patterns=["*.json", "*.safetensors", "*.txt"])
    conv = config.ROOT / "training" / "llama_cpp_convert"
    (config.ROOT / "adapters_gguf").mkdir(exist_ok=True)
    r = subprocess.run([sys.executable, str(conv / "convert_lora_to_gguf.py"), str(out), "--base", base, "--outfile",
                        str(config.ROOT / "adapters_gguf" / f"{name}.gguf"), "--outtype", "f16"], capture_output=True,
                       text=True, env={**__import__("os").environ, "PYTHONPATH": f"{conv / 'gguf-py'}:{conv}"})
    if r.returncode != 0:
        raise RuntimeError("converting the edit failed: " + (r.stderr or r.stdout)[-600:])
    return name


def exam(role, name, log=print):
    """The newest lessons, never trained on: the untouched student and the taught one against the teacher."""
    r = ROLES[role]
    _, te = split(lessons(role))
    score = {"untouched": 0, "taught": 0}
    misses = []
    for x in te:
        for who, spec, adapter in (("untouched", r["student"], False), ("taught", f"{r['student']}+{name}", True)):
            with _as(role, spec):
                out = llm.chat(role, x["messages"], max_new_tokens=r["tokens"], prefix="{", stop="json", adapter=adapter)
            key = r["key"](out, x["task"])
            score[who] += key == x["key"]
            if who == "taught" and key != x["key"]:
                misses.append({"task": x["task"][:160], "teacher": x["key"], "taught": key})
    n = len(te)
    res = {"test_lessons": n, "untouched_agrees": round(score["untouched"] / n, 3), "taught_agrees": round(score["taught"] / n, 3),
           "misses": misses[:12]}
    log(f"[school] {role}: on {n} unseen lessons the untouched student does what the teacher did on "
        f"{res['untouched_agrees']:.0%}, the taught one on {res['taught_agrees']:.0%}", flush=True)
    return res


def attend(role, n=160, train_it=True, log=print):
    r = ROLES[role]
    rows = teach(role, n, log)
    rec = record()
    entry = {"teacher": r["teacher"], "student": r["student"], "what": r["what"], "lessons": len(rows),
             "when": time.strftime("%Y-%m-%d %H:%M"), "graduated": False}
    if len(rows) < 2 * MIN_TEST:
        entry["why"] = f"only {len(rows)} lessons; an exam needs {MIN_TEST} unseen ones and more to learn from"
    elif train_it:
        name = train(role, log)
        entry.update(exam(role, name, log))
        ok = entry["taught_agrees"] >= GRADUATE and entry["taught_agrees"] >= entry["untouched_agrees"] + MARGIN
        entry["graduated"] = ok
        entry["runs_on"] = f"{r['student']}+{name}"
        entry["why"] = ("graduated" if ok else
                        f"not yet: it needs {GRADUATE:.0%} and {MARGIN:.0%} over the untouched student")
    rec[role] = entry
    RECORD.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    log(f"[school] {role}: {entry.get('why', 'lessons taught')}", flush=True)
    return entry


def next_role():
    rec = record()
    return next((r for r in ROLES if not rec.get(r, {}).get("graduated")), None)


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    role = next((a for a in argv if a in ROLES), None) or next_role()
    if not role:
        print("every role in school has graduated")
        return 0
    attend(role, n=opt("--lessons", 160), train_it="--no-train" not in argv)
    return 0
