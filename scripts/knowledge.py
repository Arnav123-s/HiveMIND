"""What is known about HiveMIND, as graphs: docs/knowledge.json drawn into docs/KNOWLEDGE.md.

    python scripts/knowledge.py            draw docs/KNOWLEDGE.md again
    python scripts/knowledge.py --check    only check that the knowledge holds together (the tests run this)

docs/knowledge.json is the one place where an agent working on HiveMIND finds, in a minute, what the goal is, what
each part does and who owns it, what has been found and fixed, what is still open, and the rules learned. Agents add
to it at the end of every cycle (a finding when a cause is found, its status when it is fixed, a rule when time was
wasted) and draw the page again. The page shows it as Mermaid diagrams, which GitHub draws:

  1. the hive's own loop, one generation, and where each step lives in the code
  2. the maintainers' loop, which every agent follows
  3. the knowledge graph: the goal, the open problems and how they are measured, the findings that block them, and
     the parts of the code where those live
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "knowledge.json"
PAGE = ROOT / "docs" / "KNOWLEDGE.md"


def load(path=SOURCE):
    return json.loads(Path(path).read_text())


def problems(k, root=ROOT):
    """What does not hold together: ids used twice, links to ids that do not exist, files that are not there,
    owners that are not agents. [] when all is well."""
    bad, ids = [], {}
    for group in ("parts", "measures", "open", "findings", "rules"):
        for n in k.get(group, []):
            if n["id"] in ids:
                bad.append(f"{n['id']} is used twice ({ids[n['id']]} and {group})")
            ids[n["id"]] = group
    kind = lambda i, g: ids.get(i) == g  # noqa: E731
    for n in k.get("parts", []) + k.get("measures", []):
        if n.get("file") and not (Path(root) / n["file"]).exists():
            bad.append(f"{n['id']}: no file {n['file']}")
    owners = set(k.get("agents", {})) | {""}
    for n in k.get("parts", []) + k.get("open", []):
        if n.get("owner", "") not in owners:
            bad.append(f"{n['id']}: owner {n.get('owner')} is not one of {sorted(owners - {''})}")
    for n in k.get("open", []):
        bad += [f"{n['id']}: measured by {m}, which is no measure" for m in n.get("measured_by", []) if not kind(m, "measures")]
    for n in k.get("findings", []):
        if not kind(n.get("lives_in"), "parts"):
            bad.append(f"{n['id']}: lives in {n.get('lives_in')}, which is no part")
        if n.get("blocks") and not kind(n["blocks"], "open"):
            bad.append(f"{n['id']}: blocks {n['blocks']}, which is no open problem")
        if n.get("status") not in ("open", "fixed"):
            bad.append(f"{n['id']}: status is {n.get('status')}, not open or fixed")
    for n in k.get("rules", []):
        if n.get("from") and not kind(n["from"], "findings"):
            bad.append(f"rule {n['id']}: learned from {n['from']}, which is no finding")
    for step in k.get("hive_loop", []):
        if not kind(step[2], "parts"):
            bad.append(f"hive loop step {step[0]}: part {step[2]} does not exist")
    return bad


def _q(s):
    """Text safe inside a Mermaid label."""
    return '"' + re.sub(r'["<>]', "'", str(s)) + '"'


def hive_loop(k):
    steps = k["hive_loop"]
    files = {p["id"]: p["file"] for p in k["parts"]}
    out = ["```mermaid", "flowchart LR"]
    for sid, title, part in steps:
        out.append(f"  {sid}[{_q(title + '<br/>' + files[part])}]".replace("'br/'", "<br/>"))
    for (a, *_), (b, *_) in zip(steps, steps[1:]):
        out.append(f"  {a} --> {b}")
    out.append(f"  {steps[-1][0]} -->|the weak kinds and the levels steer the next generation| {steps[0][0]}")
    out += ["  rel[(rows and cells:<br/>release hive-grown)]", "  rec[(generations.jsonl<br/>and body.json)]",
            f"  {steps[1][0]} -.-> rel", "  recordg -.-> rec", "  rec -.-> graphs", "```"]
    return "\n".join(out)


def maintainer_loop(k):
    steps = k["maintainer_loop"]
    out = ["```mermaid", "flowchart TD"]
    for sid, title in steps:
        out.append(f"  {sid}[{_q(title)}]")
    for (a, _), (b, _) in zip(steps, steps[1:]):
        out.append(f"  {a} --> {b}")
    out.append(f"  {steps[-1][0]} -->|next cycle| {steps[0][0]}")
    out.append("  kj[(docs/knowledge.json)]")
    out.append(f"  kj -.->|read first| {steps[0][0]}")
    out.append(f"  {steps[-1][0]} -.->|written| kj")
    out.append("```")
    return "\n".join(out)


def knowledge_graph(k):
    out = ["```mermaid", "flowchart LR", f"  goal(({_q('The goal')}))"]
    used = set()
    for o in k["open"]:
        who = f" ({o['owner']})" if o.get("owner") else " (unclaimed)"
        out.append(f"  {o['id']}{{{{{_q(o['title'] + who)}}}}}")
        out.append(f"  {o['id']} --> goal")
        for m in o.get("measured_by", []):
            used.add(m)
            out.append(f"  {o['id']} -.-|measured by| m_{m}")
    for m in k["measures"]:
        if m["id"] in used:
            out.append(f"  m_{m['id']}[/{_q(m['title'])}/]")
    # each cause sits inside the box of the file where it lives, so no line is needed to say where
    for p in k["parts"]:
        mine = [f for f in k["findings"] if f["lives_in"] == p["id"]]
        if not mine:
            continue
        out.append(f"  subgraph p_{p['id']}[{_q(Path(p['file']).name + ' (' + p['owner'] + ')')}]")
        out += [f"    f_{f['id']}[{_q(f['title'])}]:::{f['status']}" for f in mine]
        out.append("  end")
    for f in k["findings"]:
        if f.get("blocks"):
            out.append(f"  f_{f['id']} -->|{'blocked' if f['status'] == 'fixed' else 'blocks'}| {f['blocks']}")
    out += ["  classDef fixed fill:#e7f4e4,stroke:#0ca30c,color:#0b0b0b", "  classDef open fill:#fdecec,stroke:#d03b3b,color:#0b0b0b", "```"]
    return "\n".join(out)


def page(k):
    fixed = [f for f in k["findings"] if f["status"] == "fixed"]
    still = [f for f in k["findings"] if f["status"] == "open"]
    lines = ["# What is known about HiveMIND", "",
             f"**The goal:** {k['goal']}", "",
             "Drawn from `docs/knowledge.json` by `scripts/knowledge.py`; do not edit this page by hand. Every agent reads the "
             "file first and adds to it at the end of a cycle. How the hive is doing in numbers: [PROGRESS.md](PROGRESS.md). "
             "Who owns what, and the log of who is doing what: `docs/AGENTS.md`.", "",
             "## 1. The hive's loop: one generation", "",
             "It runs by itself on GitHub (`.github/workflows/grow.yml`), one generation after another. Each box names where "
             "the step lives.", "", hive_loop(k), "",
             "## 2. The maintainers' loop", "",
             "Every agent working on the hive follows it, cycle after cycle. Agents on other accounts cannot message each "
             "other; this file, `docs/AGENTS.md` and the pull requests are how they work together.", "", maintainer_loop(k), "",
             "## 3. The knowledge graph", "",
             "The open problems that stand between the hive and the goal (six-sided), how each is measured (slanted), the "
             "causes found in the members' own work (green: fixed, red: still open), each inside the box of the file where "
             "it lives, with that file's owner.", "", knowledge_graph(k), "",
             "## Open problems", "", "| Problem | Owner | Seen |", "|---|---|---|"]
    lines += [f"| {o['title']} | {o.get('owner') or 'unclaimed'} | {o['seen']} |" for o in k["open"]]
    lines += ["", f"## Causes found ({len(still)} open, {len(fixed)} fixed)", "", "| Cause | Where | Status | By | Seen |", "|---|---|---|---|---|"]
    files = {p["id"]: p["file"] for p in k["parts"]}
    lines += [f"| {f['title']} | `{files[f['lives_in']]}` | {f['status']} | {f.get('by', '')} | {f['seen']} |" for f in still + fixed]
    lines += ["", "## Rules learned", ""] + [f"- {r['rule']}" for r in k["rules"]]
    lines += ["", "## The parts", "", "| Part | File | Owner | What it does |", "|---|---|---|---|"]
    lines += [f"| {p['title']} | `{p['file']}` | {p['owner']} | {p['does']} |" for p in k["parts"]]
    lines += ["", "Agents: " + "; ".join(f"**{a}**: {d}" for a, d in k["agents"].items()) + ".", ""]
    return "\n".join(lines)


def main(argv):
    k = load()
    bad = problems(k)
    for b in bad:
        print("knowledge:", b)
    if bad:
        return 1
    if "--check" not in argv:
        PAGE.write_text(page(k))
        print(f"drawn: {PAGE.relative_to(ROOT)} ({len(k['findings'])} findings, {len(k['open'])} open problems, {len(k['rules'])} rules)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
