"""Does any training data, cell generator or prompt already hold a bench task's specifics?

    python training/contamination_check.py
For every development and held-out task: its specific terms (model ids, quoted tags and texts, a named category,
person names, numbers of 3+ characters) and its 5-word phrases. Each is looked up in what trained or steers the hive:
the members' training data (training/data/*.jsonl: in the goals/claims they were trained on, and anywhere in the
text), the cells' data generators (team/cells/skills.py) and the prompts (team/prompts.py). Page text the browser saw
(category lists, tag clouds) mentions many site words, so only a goal or claim that names a task's specific counts as
contamination. Writes training/reports/hive_bench/contamination.json.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.argv = sys.argv[:1]
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("hb", ROOT / "training" / "hive_bench.py")
hb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hb)

COMMON = {"Hugging", "Face", "Python", "The", "What", "Which", "Write", "Find", "Give", "Save", "Plot", "Make", "Monday",
          "Friday", "French", "Spanish", "CSV", "PyPI", "January", "March", "June", "May", "July", "Fix", "Correct",
          "Summarise", "Translate", "Convert", "List", "Rewrite", "This", "Test", "Monthly", "How", "Starting", "Desks",
          "Parking", "IT", "In", "On", "It", "Who", "One", "Send", "She"}


def terms(task):
    t = set(re.findall(r"\b[\w.-]+/[\w.-]+\b", task))  # model ids
    t |= {q for q in re.findall(r"'([^']{3,60})'", task)}  # quoted tags and texts
    t |= {m for m in re.findall(r"\b([A-Z][a-z]+) category\b", task)}
    t |= {w for w in re.findall(r"\b[A-Z][a-z]{2,}\b", task) if w not in COMMON}
    t |= {n for n in re.findall(r"\d[\d.,]{2,}", task)}
    return sorted(t)


def phrases(task, n=5):
    w = re.findall(r"[a-z0-9']+", task.lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def goals_and_text(path):
    goals, text = [], path.read_text(errors="ignore")
    for ln in text.splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        msgs = d.get("messages") or []
        user = next((m["content"] for m in msgs if m["role"] == "user"), "") if msgs else ""
        m = re.search(r"(?:GOAL|Goal|TASK|Task|CLAIM|ARNAV'S TASK)[^:\n]*:\s*(.+)", user)
        goals.append(m.group(1) if m else user[:300])
    return "\n".join(goals), text


def main():
    sources = {p.name: goals_and_text(p) for p in sorted((ROOT / "training" / "data").glob("*.jsonl"))}
    code = {"skills.py": (ROOT / "team/cells/skills.py").read_text(), "prompts.py": (ROOT / "team/prompts.py").read_text()}
    out = {}
    for tid, kind, task, _ in hb.TASKS + hb.HELDOUT:
        hits = []
        for term in terms(task):
            rx = re.compile(r"(?<![\w.])" + re.escape(term) + r"(?![\w])", re.I)  # whole words only
            for name, (goals, _) in sources.items():
                n = len(rx.findall(goals))
                if n:
                    hits.append(f"term {term!r} in {n} training goal(s) of {name}")
            for name, src in code.items():
                if rx.search(src):
                    hits.append(f"term {term!r} in {name}")
        ph = phrases(task)
        for name, (goals, _) in sources.items():
            g = goals.lower()
            shared = [p for p in ph if p in re.sub(r"[^a-z0-9' ]+", " ", g)]
            if shared:
                hits.append(f"{len(shared)} 5-word phrase(s) in training goals of {name}: {shared[0]!r}")
        out[tid] = {"heldout": tid.startswith("ho_"), "task": task[:120], "hits": hits}
        print(f"{'HELD-OUT' if tid.startswith('ho_') else 'dev     '} {tid:14s} {len(hits):3d}  " + "; ".join(hits)[:300])
    (ROOT / "training" / "reports" / "hive_bench" / "contamination.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
