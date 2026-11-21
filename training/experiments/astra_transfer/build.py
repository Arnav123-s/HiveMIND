"""Rebuild prior evidence, never running candidate source programs."""
import argparse
import ast
import hashlib
import itertools
import json
from collections import defaultdict
from pathlib import Path

from tokenizers import Tokenizer
from training import grow, kinds
from training.experiments.astra_transfer.scaffolds import CARDS, HERE, PREFIX, digest, signature
from team.deliverables import wanted


def operations(program, task):
    try:
        tree = ast.parse(program.removeprefix("```python\n").removesuffix("\n```"))
    except (SyntaxError, ValueError):
        return set()
    reads, writes, calls = set(), set(), set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ast.unparse(node.func)
        calls.add(name)
        if name != "open" or not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        path = node.args[0].value
        if not isinstance(path, str):
            continue
        mode = node.args[1] if len(node.args) > 1 else next((kw.value for kw in node.keywords if kw.arg == "mode"), None)
        if mode is None or isinstance(mode, ast.Constant) and mode.value in ("r", "rt"):
            reads.add(path)
        elif isinstance(mode, ast.Constant) and mode.value == "w" and path in wanted(task):
            writes.add(path)
    out = set()
    if "csv.DictReader" in calls and any(f.endswith(".csv") for f in reads):
        out.add("read_csv")
    if "json.loads" in calls and reads and any(isinstance(n, (ast.For, ast.ListComp)) for n in ast.walk(tree)):
        out.add("read_jsonl")
    if any(p.endswith(".csv") for p in writes) and "csv.writer" in calls and all(any(c.endswith(n) for c in calls) for n in (".writerow", ".writerows")):
        out.add("write_csv")
    if any(p.endswith(".json") for p in writes) and "json.dump" in calls:
        out.add("write_json")
    if any(p.endswith(".py") for p in writes) and "inspect.getsource" in calls and any(isinstance(n, ast.Assert) for n in ast.walk(tree)):
        out.add("write_module")
    return out


def build(rows_file, tokenizer_file):
    rows = [json.loads(line) for line in rows_file.read_bytes().splitlines()]
    held = {t for tasks in grow.kept_back(rows, n=2).values() for t in tasks}
    records = defaultdict(dict)
    for row in rows:
        if row.get("type") != "first" or row.get("who") != "lesson" or row.get("lesson") not in kinds.SOLVERS:
            continue
        task = row["task"]
        if task in held:
            continue
        identity = digest(json.dumps(row, sort_keys=True))
        for key in operations(row["output"], task):
            sig = signature(task)
            if sig not in records[key] or identity < records[key][sig]:
                records[key][sig] = identity
    cards, source = {}, set()
    for key in CARDS:
        witnesses = sorted(records[key].items(), key=lambda p: p[1])[:3]
        if len(witnesses) == 3:
            cards[key] = {"supported_tasks": len(records[key]), "three_witness_rows": [r for _, r in witnesses]}
            source.update(t for t, _ in records[key].items())
    tokenizer = Tokenizer.from_file(str(tokenizer_file))
    tokens = {}
    for size in range(1, len(cards) + 1):
        for group in itertools.combinations(cards, size):
            text = "\n\n" + PREFIX + "\n".join(CARDS[k] for k in group)
            tokens["+".join(group)] = len(tokenizer.encode(text, add_special_tokens=False).ids)
    return dict(rows_file_sha256=hashlib.sha256(rows_file.read_bytes()).hexdigest(),
                tokenizer_sha256=hashlib.sha256(tokenizer_file.read_bytes()).hexdigest(),
                excluded_kept_back=len(held), cards=cards, source_prompts=sorted(source), tokens=tokens)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("rows", type=Path)
    parser.add_argument("tokenizer", type=Path)
    parser.add_argument("--out", type=Path, default=HERE / "bank.json")
    args = parser.parse_args()
    args.out.write_text(json.dumps(build(args.rows, args.tokenizer), indent=1) + "\n")
