"""Extract repeatable top-level function syntax from individually graded practice workers."""
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

from team.helper_source import signature

HERE = Path(__file__).resolve().parent
ROW_SHA = "c33f707c7120d279c050748a5752067be708687711aa9acc84a4f434208fadfd"


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def question(text):
    return sha(" ".join(text.casefold().split()))


def read_kind_map(path):
    if sha(path.read_bytes()) != ROW_SHA:
        raise ValueError("unexpected G55 label archive")
    labels = defaultdict(set)
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if row.get("kind"):
            labels[question(row["task"])].add(row["kind"])
    return {key: next(iter(val)) for key, val in labels.items() if len(val) == 1}


def worker_source(z, prefix, leaves, events, member):
    num = member["member"]
    name = f"member{num}"
    seen = [e for e in events if e["agent"] == name and e["kind"] in {"run", "answer"}]
    if len(seen) < 2 or seen[-1]["kind"] != "answer" or seen[-1]["msg"] in ("", "no answer"):
        return None
    run = next((e for e in reversed(seen[:-1]) if e["kind"] == "run"), None)
    match = re.fullmatch(r"turn (\d+): exit 0, printed \d+ characters", run["msg"]) if run else None
    if not match:
        return None
    filename = f"{name}_{match[1]}.py"
    # solo.member assigns work exclusively to seat 1. Other seats use their own numbered directory.
    folder = "work" if num == 1 else name
    candidates = [n for n in leaves if n.startswith(prefix+"members/") and n.rsplit("/", 1)[-1] == filename]
    expected = prefix + "members/" + folder + "/" + filename
    return expected if candidates == [expected] else None


def mine(archives, kind_map):
    counts, groups, examples, seen_tasks, seen_workers, matched = Counter(), defaultdict(list), {}, set(), set(), {}
    for origin in json.loads((HERE / "practice-artifacts.json").read_text()):
        path = archives / (str(origin["id"]) + ".zip")
        if origin["generation"] not in {50,51,52} or sha(path.read_bytes()) != origin["sha256"]:
            raise ValueError("unexpected original practice artifact")
        with ZipFile(path) as z:
            leaves = set(z.namelist())
            for exam in sorted(n for n in leaves if re.fullmatch(r"practice_\d+/[ech]\d+_\d+/exam\.json", n)):
                prefix = exam.removesuffix("exam.json")
                head = prefix + "members/"
                q = question(z.read(head + "TASK.md").decode())
                seen_tasks.add(q)
                kind = kind_map.get(q)
                if kind:
                    matched[q] = kind
                events = [json.loads(l) for l in z.read(head + "events.jsonl").splitlines()]
                counts["question_sittings"] += 1
                for worker in json.loads(z.read(exam))["members"]:
                    counts["graded_workers"] += 1
                    if worker["ok"] is not True:
                        continue
                    counts["individually_passing_workers"] += 1
                    source = worker_source(z, prefix, leaves, events, worker)
                    if not source:
                        continue
                    seen_workers.add(worker["who"])
                    raw = z.read(source)
                    counts["linked_last_successful_sources"] += 1
                    try:
                        tree = ast.parse(raw)
                    except (SyntaxError, ValueError):
                        counts["unparseable_sources"] += 1
                        continue
                    for node in tree.body:
                        if not isinstance(node, ast.FunctionDef):
                            continue
                        counts["top_level_definitions"] += 1
                        signature_id = signature(node)
                        if signature_id:
                            counts["standalone_definitions"] += 1
                            groups[signature_id].append(dict(artifact=origin["id"],source=source,source_sha256=sha(raw),
                                line=node.lineno,question_sha256=q,kind=kind,worker=worker["who"]))
                            examples.setdefault(signature_id, ast.get_source_segment(raw.decode(), node))
    ordered = sorted(groups, key=lambda key: (-len({r["kind"] for r in groups[key] if r["kind"]}),
                                              -len({r["question_sha256"] for r in groups[key]}),key))
    repeated = {key:groups[key] for key in ordered if len({r["question_sha256"] for r in groups[key]}) >= 2}
    counts.update(unique_questions=len(seen_tasks), labelled_questions=len(matched), unique_standalone_signatures=len(groups),
                  recurring_across_questions=len(repeated), distinct_linked_workers=len(seen_workers),
                  recurring_across_known_kinds=sum(len({r["kind"] for r in v if r["kind"]}) >= 2 for v in repeated.values()))
    selected = next(iter(repeated), None)
    return dict(counts=dict(counts),selected=selected,recurring_provenance=repeated), examples.get(selected), matched


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("archives", type=Path)
    p.add_argument("--original-labels", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a=p.parse_args()
    labels=read_kind_map(a.original_labels) if a.original_labels else json.loads((HERE/"kind-map.json").read_text())
    result, source, matched=mine(a.archives, labels)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"results.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    (a.out/"kind-map.json").write_text(json.dumps(matched,sort_keys=True,indent=1)+"\n")
    if source:
        (a.out/"selected.py").write_text(source+"\n")
    print(result["counts"], result["selected"])


if __name__ == "__main__":
    main()
