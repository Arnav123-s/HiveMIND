"""School: a small model learns a bigger member's job from that member, and takes the job when it does it the same.

    python -m team school [ROLE] [--lessons 160] [--no-train]

The hive's biggest members (the 4B that plans, reads and judges; the 7B that writes programs) hold their jobs because
a small model was measured worse at them. School is how a small model gets the job anyway:

1. lessons    inputs for the job: the real ones from the logs, and new tasks the teacher writes itself
2. teach      the teacher does the job on every lesson; a lesson is kept only if its answer is usable
3. train      the student's weights are edited on the lessons that are not exam lessons (training/train_lora.py)
4. exam       on the exam lessons, never trained on: how often does each specialist alone, and all of them
              answering together (what most decide), do what the teacher did? The role graduates only if that clears
              GRADUATE and beats the untouched student.
5. graduate   cells/school.json records it; with AGENT_TEAM_SMALL=1 the role then runs on its small specialists

Every later visit can add a specialist and removes none. The teacher writes new lessons; the present specialists
take them first, and the lessons the hive gets wrong are a gap. The teacher writes more tasks of that kind, and a
new specialist learns that gap and nothing else: it does not have to know what the older ones know. A task that
lies in its territory (most like one of its lessons) goes to it; everything else stays with the general ones, who
answer together. The exam measures each way of holding the job (the best one alone, the general ones together,
routed to the narrow ones), and a way with more specialists is used only where it measures better.

Without ROLE, the role that most needs it is taken (the always-on agent does this when idle). Nothing is taken on
trust: the record holds every exam number and the lessons are kept (training/data/school/).
"""
import json
import random
import re
import subprocess
import sys
import time

from . import config, llm

DATA = config.ROOT / "training" / "data" / "school"
RECORD = config.ROOT / "cells" / "school.json"
GRADUATE, MARGIN, MIN_TEST, DONE, MIN_GAP = 0.85, 0.03, 30, 0.97, 6

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
    """Every lesson of the role, oldest first, each marked exam (never trained on) or not."""
    f = DATA / f"{role}.jsonl"
    rows = [json.loads(ln) for ln in f.read_text().splitlines() if ln.strip()] if f.exists() else []
    first = [x for x in rows if "exam" not in x]  # the first class was split in one piece: its newest fifth is exam
    k = max(MIN_TEST, len(first) // 5)
    for i, x in enumerate(first):
        x["exam"] = i >= len(first) - k
    return rows


def teach(role, n, log=print, tasks=None):
    """Bring the role's lessons up to n: each a task, the teacher's answer, and what that answer decides.
    Returns (all lessons, the new ones). After the first class every fifth new lesson is an exam lesson.
    With tasks, exactly those are taught (new tasks the teacher wrote for a gap)."""
    r, have = ROLES[role], lessons(role)
    if len(have) >= n:
        return have, []
    DATA.mkdir(parents=True, exist_ok=True)
    later, new = bool(have), []
    done = [x["task"] for x in have]
    if tasks is None:
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
            row = {"task": t, "messages": msgs, "output": out, "key": key}
            if later:
                row["exam"] = len(have) % 5 == 4
            have.append(row)
            new.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            if len(have) % 10 == 0:
                log(f"[school] {role}: {len(have)} of {n} lessons taught", flush=True)
    return lessons(role), new


def split(rows):
    return [x for x in rows if not x["exam"]], [x for x in rows if x["exam"]]


def train(role, name, only=None, log=print, epochs=2, rank=8, seed=0):
    """Edit the student's weights on the lessons that are not exam lessons. With only (a set of tasks), on those
    lessons alone: a specialist for one gap learns that gap and nothing else."""
    tr, _ = split(lessons(role))
    if only is not None:
        tr = [x for x in tr if x["task"] in only]
    f = DATA / f"{role}_train.jsonl"
    f.write_text("".join(json.dumps({"messages": x["messages"], "output": x["output"]}, ensure_ascii=False) + "\n" for x in tr))
    llm.unload_all()  # the training process gets the RAM
    out = config.ADAPTERS / name
    cmd = [sys.executable, str(config.ROOT / "training" / "train_lora.py"), role, "--data", str(f), "--out", str(out),
           "--rank", str(rank), "--epochs", str(epochs), "--seed", str(seed)]
    log(f"[school] {role}: training {name} on {len(tr)} lessons", flush=True)
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


# ---- the specialists of a role answer together -------------------------------------------------------------------
def _spec(role, voter):
    st = ROLES[role]["student"]
    return (st, False) if voter == "untouched" else (f"{st}+{voter}", True)


def _ask(role, voter, messages, task):
    """One specialist's answer and what it decides."""
    spec, adapter = _spec(role, voter)
    with _as(role, spec):
        out = llm.chat(role, messages, max_new_tokens=ROLES[role]["tokens"], prefix="{", stop="json", adapter=adapter)
    return out, ROLES[role]["key"](out, task)


def majority(keys, order):
    """What most specialists decided; on a tie, the decision of the one that did best in its exam (order)."""
    count = {}
    for v in order:
        k = keys.get(v)
        if k is not None:
            count[json.dumps(k)] = count.get(json.dumps(k), 0) + 1
    if not count:
        return None
    top = max(count.values())
    return next(keys[v] for v in order if keys.get(v) is not None and count[json.dumps(keys[v])] == top)


def answers(role, voters, rows, log=print):
    """What each specialist decides on each lesson; kept on disk, so an old specialist answers only new lessons."""
    f = DATA / f"{role}_answers.json"
    try:
        memo = json.loads(f.read_text())
    except (OSError, ValueError):
        memo = {}
    for v in voters:
        mine = memo.setdefault(v, {})
        for i, x in enumerate(rows):
            if x["task"] not in mine:
                mine[x["task"]] = _ask(role, v, x["messages"], x["task"])[1]
                if i % 10 == 9:
                    f.write_text(json.dumps(memo))
        f.write_text(json.dumps(memo))
    return {v: {x["task"]: memo[v][x["task"]] for x in rows} for v in voters}


SIMILAR = """You write tasks that Arnav might type to his team of AI specialists. You are given ONE task.
Write {n} new tasks of exactly the same kind (the same sort of work, done by the same specialists), each about a
different subject, site, text or numbers. One task per line, no numbering, nothing else."""


def similar_tasks(gaps, have, teacher, per=4, log=print):
    """For each lesson the present specialists got wrong, the teacher writes more tasks of the same kind."""
    seen, out = {t.lower() for t in have}, {}
    with _as("examiner", teacher):
        for g in gaps:
            text = llm.chat("examiner", [{"role": "system", "content": SIMILAR.format(n=per)},
                                         {"role": "user", "content": g}], max_new_tokens=400, temperature=0.8)
            mine = []
            for ln in text.splitlines():
                t = ln.strip(" -*\t0123456789.)")
                if 25 <= len(t) <= 400 and t.lower() not in seen:
                    seen.add(t.lower())
                    mine.append(t)
            out[g] = mine[:per]
    return out


def _words(t):
    return set(re.sub(r"\d+", "0", t.lower()).replace("'", " ").split())


def _near(a, b):
    wa, wb = _words(a), _words(b)
    return len(wa & wb) / max(1, len(wa | wb))


def territories(role):
    """Who knows which lessons: {"right": lessons the general specialists got right, <specialist>: its gap lessons}."""
    try:
        return json.loads((DATA / f"{role}_territory.json").read_text())
    except (OSError, ValueError):
        return {}


def route(role, task, terr=None):
    """Which narrow specialist this task belongs to, or None for the general ones: the owner of the known lesson
    most like it. A specialist is asked only inside what it learned."""
    terr = territories(role) if terr is None else terr
    best, who = 0.0, None
    for owner, tasks in terr.items():
        for t in tasks:
            sim = _near(task, t)
            if sim > best:
                best, who = sim, owner
    return None if who in (None, "right") else who


def exam(role, names, log=print):
    """The exam lessons, never trained on. Every specialist alone; the general ones answering together (what most
    decide); and routed: a task that lies in a narrow specialist's territory goes to it, the rest to the general ones."""
    _, te = split(lessons(role))
    terr = territories(role)
    narrow = [n for n in names if n in terr]
    general = ["untouched", *[n for n in names if n not in terr]]
    everyone = general + narrow
    got = answers(role, everyone, te, log)
    n = len(te)
    alone = {v: round(sum(got[v][x["task"]] == x["key"] for x in te) / n, 3) for v in everyone}
    order = sorted(general, key=lambda v: -alone[v])

    def decide(x, scheme):
        t = x["task"]
        if scheme == "alone":
            return got[order[0]][t]
        if scheme == "routed":
            who = route(role, t, terr)
            if who in narrow and got[who][t] is not None:
                return got[who][t]
            scheme = "together" if len(order) > 2 else "alone"
            return decide(x, scheme)
        return majority({v: got[v][t] for v in order}, order)

    schemes = ["alone"] + (["together"] if len(order) > 2 else []) + (["routed"] if narrow else [])
    score = {sc: round(sum(decide(x, sc) == x["key"] for x in te) / n, 3) for sc in schemes}
    # how many exam lessons at least one specialist gets right: what a perfect choice between them could reach
    someone = round(sum(any(got[v][x["task"]] == x["key"] for v in everyone) for x in te) / n, 3)
    best = "alone"
    for sc in schemes[1:]:  # more specialists answering only where that measures better
        if score[sc] >= score[best] + MARGIN:
            best = sc
    in_territory = {w: [x for x in te if route(role, x["task"], terr) == w] for w in narrow}
    res = {"test_lessons": n, "alone": alone, "schemes": score, "someone_right": someone, "scheme": best,
           "untouched_agrees": alone["untouched"], "taught_agrees": score[best], "general": order, "narrow": narrow,
           "narrow_in_their_territory": {w: {"exam_lessons": len(xs),
                                             "specialist_right": sum(got[w][x["task"]] == x["key"] for x in xs),
                                             "general_right": sum(decide(x, "together" if len(order) > 2 else "alone") == x["key"] for x in xs)}
                                         for w, xs in in_territory.items()},
           "misses": [{"task": x["task"][:160], "teacher": x["key"], "hive": decide(x, best)}
                      for x in te if decide(x, best) != x["key"]][:12]}
    log(f"[school] {role}: on {n} unseen lessons, alone: {alone}; schemes: {score}; at least one right: {someone:.0%}; "
        f"the job would be done: {best}", flush=True)
    return res


def holders(role):
    """How the role is held after its exams: (scheme, general specialists best first, narrow ones); None if the
    role has not graduated."""
    v = record().get(role, {})
    return (v.get("scheme", "alone"), list(v.get("general") or []), list(v.get("narrow") or [])) if v.get("graduated") else None


def answer(role, messages, task):
    """The role's answer from its small specialists: a task in a narrow specialist's territory goes to that one;
    otherwise the general ones answer and the hive takes what most decide. None if the role has not graduated."""
    h = holders(role)
    if not h:
        return None
    scheme, general, narrow = h
    if scheme == "routed":
        who = route(role, task)
        if who in narrow:
            out, key = _ask(role, who, messages, task)
            if key is not None:
                return out
    vs = general if scheme in ("together", "routed") and len(general) > 2 else general[:1]
    outs, keys = {}, {}
    for v in vs:
        outs[v], keys[v] = _ask(role, v, messages, task)
    top = majority(keys, vs)
    return next((outs[v] for v in vs if keys[v] is not None and keys[v] == top), None)


def attend(role, n=160, train_it=True, log=print):
    r = ROLES[role]
    rec = record()
    old = rec.get(role, {})
    names = list(old.get("specialists") or ([f"{role}_school"] if "taught_agrees" in old else []))
    rows, new = teach(role, n, log)
    entry = {**old, "teacher": r["teacher"], "student": r["student"], "what": r["what"],
             "when": time.strftime("%Y-%m-%d %H:%M"), "specialists": names}
    entry.setdefault("graduated", False)
    tr, te = split(rows)
    if len(te) < MIN_TEST or len(tr) < MIN_TEST:
        entry["why"] = f"only {len(rows)} lessons; an exam needs {MIN_TEST} unseen ones and more to learn from"
    elif train_it:
        if not names:  # the first class: one general specialist, taught everything
            names.append(train(role, f"{role}_school", None, log))
        elif new:
            # the new lessons are unseen by everyone: the present specialists take them first. What they get wrong
            # is a gap; the teacher writes more tasks of that kind, and a new specialist learns that gap and nothing
            # else. The older ones keep what they know; nobody is retrained or replaced.
            terr = territories(role)
            quiz = [x for x in new if not x["exam"]]
            first = [*names, "untouched"] if old.get("taught_agrees", 0) > old.get("untouched_agrees", 0) else ["untouched", *names]
            h = (old.get("scheme", "alone"), old.get("general") or first, old.get("narrow") or [])
            got = answers(role, ["untouched", *names], quiz, log)

            def hive(x):
                who = route(role, x["task"], terr) if h[0] == "routed" else None
                if who in h[2] and got[who][x["task"]] is not None:
                    return got[who][x["task"]]
                vs = h[1] if h[0] != "alone" and len(h[1]) > 2 else h[1][:1]
                return majority({v: got[v][x["task"]] for v in vs}, vs)
            gaps = [x["task"] for x in quiz if hive(x) != x["key"]]
            terr.setdefault("right", [])
            terr["right"] += [x["task"] for x in quiz if x["task"] not in gaps]
            entry["last_quiz"] = {"new_lessons": len(quiz), "hive_wrong": len(gaps)}
            log(f"[school] {role}: the hive got {len(gaps)} of {len(quiz)} new lessons wrong", flush=True)
            if len(gaps) >= MIN_GAP:
                more = similar_tasks(gaps[:24], [x["task"] for x in rows], r["teacher"], log=log)
                rows, taught = teach(role, len(rows) + sum(len(v) for v in more.values()), log,
                                     tasks=[t for v in more.values() for t in v])
                name = f"{role}_school{len(names) + 1}"
                terr[name] = gaps + [x["task"] for x in taught if not x["exam"]]
                (DATA / f"{role}_territory.json").write_text(json.dumps(terr, indent=1, ensure_ascii=False))
                names.append(train(role, name, set(terr[name]), log, epochs=3, seed=len(names)))
            else:
                (DATA / f"{role}_territory.json").write_text(json.dumps(terr, indent=1, ensure_ascii=False))
                log(f"[school] {role}: fewer than {MIN_GAP} gaps: no new specialist this time", flush=True)
        entry.update(exam(role, names, log))
        ok = entry["taught_agrees"] >= GRADUATE and entry["taught_agrees"] >= entry["untouched_agrees"] + MARGIN
        entry["graduated"] = ok
        best = entry["general"][0]
        entry["runs_on"] = r["student"] if best == "untouched" else f"{r['student']}+{best}"
        entry["why"] = ("graduated" if ok else
                        f"not yet: it needs {GRADUATE:.0%} and {MARGIN:.0%} over the untouched student")
    entry["lessons"] = len(lessons(role))
    rec[role] = entry
    RECORD.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    log(f"[school] {role}: {entry.get('why', 'lessons taught')}", flush=True)
    return entry


def next_role():
    """The role that most needs school: one never taught, else the one whose specialists agree least with their
    teacher. A role that graduated keeps going back while there is something left to learn (under DONE)."""
    rec = record()
    todo = [r for r in ROLES if rec.get(r, {}).get("taught_agrees", 0) < DONE]
    return min(todo, key=lambda r: rec.get(r, {}).get("taught_agrees", -1)) if todo else None


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    role = next((a for a in argv if a in ROLES), None) or next_role()
    if not role:
        print("every role in school does what its teacher does")
        return 0
    # a role goes back with new lessons, not the same ones again
    tried = record().get(role, {})
    more = min(800, tried.get("lessons", 0) + 80) if "taught_agrees" in tried else 160
    attend(role, n=opt("--lessons", more), train_it="--no-train" not in argv)
    return 0
