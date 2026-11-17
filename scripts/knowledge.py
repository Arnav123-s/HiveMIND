"""What is known about HiveMIND, as graphs: docs/knowledge.json drawn into docs/KNOWLEDGE.md.

    python scripts/knowledge.py            draw docs/KNOWLEDGE.md again
    python scripts/knowledge.py --check    only check that the knowledge holds together (the tests run this)

docs/knowledge.json is the one place where an agent working on HiveMIND finds, in a minute, what the goal is, what
each part does and who owns it, what has been found and fixed, what is still open, and the rules learned. Agents add
to it at the end of every cycle (a finding when a cause is found, with the board piece of docs/PLAN.md it belongs
to; its fix when it is fixed; a rule when time was wasted) and draw the page again. The page shows it as Mermaid
diagrams, which GitHub draws, all from the same data:

  1. the hive's own loop, one generation: each step, where it lives, its measured minutes and its open problem
  2. the agents' loop: read the generation, the verdict table of docs/PLAN.md, a board piece, build, prove, merge;
     the verdict's rows and the pieces that still hold open causes are read from docs/PLAN.md and the findings
  3. the findings: what was seen -> its cause -> its fix -> the board piece, open ones marked
  4. where the causes live: the goal, the open problems and how they are measured, each cause inside its file
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "knowledge.json"
PAGE = ROOT / "docs" / "KNOWLEDGE.md"
PLAN = ROOT / "docs" / "PLAN.md"
RECORD = ROOT / "training" / "reports" / "generations.jsonl"
# the steps of the hive's loop (docs/knowledge.json hive_loop) by the step of the run they are timed by
# (training/reads.py writes minutes_by_step into the record); "nextg" is the whole generation
TIMED = {"practise": "practice", "dreams": "dream", "gather": "gather", "plan": "plan", "trainc": "train", "join": "join",
         "trunk": "merge", "pulse": "gate", "recordg": "record"}
_PIECE = re.compile(r"^\| ([A-Z]\d+) \| (.+?) \| .*\| ([^|]*) \|\s*$")


def load(path=SOURCE):
    return json.loads(Path(path).read_text())


def _short(text, most):
    """At most `most` characters, cut at a word."""
    return text if len(text) <= most else text[:most].rsplit(" ", 1)[0] + "..."


def board(plan=PLAN):
    """The board of docs/PLAN.md: {piece id: {"title": short title, "who": its last column}}."""
    out = {}
    text = Path(plan).read_text() if Path(plan).exists() else ""
    for ln in text.splitlines():
        m = _PIECE.match(ln)
        if m:
            title = _short(re.split(r": | \(", m.group(2).replace("`", ""), maxsplit=1)[0], 60)
            out[m.group(1)] = {"title": title, "who": m.group(3).strip()}
    return out


def verdict_rows(plan=PLAN):
    """The verdict table of docs/PLAN.md: [(what the read shows, the piece id or None, the next piece as written)]."""
    rows, inside = [], False
    text = Path(plan).read_text() if Path(plan).exists() else ""
    for ln in text.splitlines():
        if ln.startswith("| What the read shows"):
            inside = True
            continue
        if inside and ln.startswith("|---"):
            continue
        if inside and ln.startswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) >= 3:
                m = re.match(r"([A-Z]\d+)\b", cells[2])
                rows.append((cells[0], m.group(1) if m else None, cells[2]))
            continue
        if inside:
            break
    return rows


def problems(k, root=ROOT):
    """What does not hold together: ids used twice, links to ids that do not exist, files that are not there,
    owners that are not agents, board pieces that are not on the board of docs/PLAN.md. [] when all is well."""
    bad, ids = [], {}
    for group in ("parts", "measures", "open", "findings", "rules"):
        for n in k.get(group, []):
            if n["id"] in ids:
                bad.append(f"{n['id']} is used twice ({ids[n['id']]} and {group})")
            ids[n["id"]] = group
    kind = lambda i, g: ids.get(i) == g  # noqa: E731
    pieces = board(Path(root) / "docs" / "PLAN.md")
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
        if n.get("piece"):
            if n["piece"] not in pieces:
                bad.append(f"{n['id']}: piece {n['piece']} is not on the board of docs/PLAN.md")
            if not n.get("found"):
                bad.append(f"{n['id']}: has a piece but no 'found' (what was seen, in a few words)")
            if n.get("status") == "fixed" and not n.get("fix"):
                bad.append(f"{n['id']}: fixed, with a piece, but no 'fix' (the fix, in a few words)")
    for n in k.get("rules", []):
        if n.get("from") and not kind(n["from"], "findings"):
            bad.append(f"rule {n['id']}: learned from {n['from']}, which is no finding")
    for step in k.get("hive_loop", []):
        if not kind(step.get("part"), "parts"):
            bad.append(f"hive loop step {step.get('id')}: part {step.get('part')} does not exist")
        if step.get("piece") and step["piece"] not in pieces:
            bad.append(f"hive loop step {step.get('id')}: piece {step['piece']} is not on the board of docs/PLAN.md")
    return bad


def _q(*lines):
    """Text safe inside a Mermaid label, its lines joined by line breaks."""
    return '"' + "<br/>".join(re.sub(r'["<>#`]', "'", str(s)) for s in lines if s) + '"'


def run_minutes(record=RECORD):
    """{loop step id: "gNN: X min"} from the newest generation whose record says its minutes (the record job takes them
    from the run's jobs), with "nextg" its hours; {} when no record says them."""
    last = None
    for ln in Path(record).read_text().splitlines() if Path(record).exists() else []:
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("minutes_by_step"), dict) and d["minutes_by_step"]:
            last = d
    if not last:
        return {}
    g, m = last.get("generation", "?"), last["minutes_by_step"]
    out = {i: f"{g}: {m[s]} min" for i, s in TIMED.items() if isinstance(m.get(s), (int, float))}
    if isinstance(last.get("hours"), (int, float)):
        out["nextg"] = f"a whole generation: {g} {last['hours']:.1f} h; the bar is 5"
    return out


def hive_loop(k, minutes=None):
    minutes = run_minutes() if minutes is None else minutes
    steps = [dict(s, minutes=minutes.get(s["id"], s["minutes"])) for s in k["hive_loop"]]
    files = {p["id"]: p["file"] for p in k["parts"]}
    out = ["```mermaid", "flowchart TD"]
    for s in steps:
        problem = f"open: {s['problem']}" + (f" ({s['piece']})" if s.get("piece") else "") if s.get("problem") else ""
        out.append(f"  {s['id']}[{_q(s['title'], files[s['part']], 'minutes: ' + s['minutes'], problem)}]"
                   + (":::open" if s.get("problem") else ""))
    for a, b in zip(steps, steps[1:]):
        out.append(f"  {a['id']} --> {b['id']}")
    out.append(f"  {steps[-1]['id']} -->|\"the weak kinds and the levels steer it\"| {steps[0]['id']}")
    ids = [s["id"] for s in steps]
    out += ["  rel[(\"rows and cells:<br/>release hive-grown\")]", "  rec[(\"generations.jsonl<br/>and body.json\")]"]
    if "gather" in ids:
        out.append("  gather -.-> rel")
    if "recordg" in ids:
        out.append("  recordg -.-> rec")
    if "verdictg" in ids:
        out.append("  rec -.-> verdictg")
    out += ["  classDef open stroke:#d03b3b,stroke-width:2px", "```"]
    return "\n".join(out)


def _piece_node(pid, pieces, cls=""):
    p = pieces.get(pid, {"title": "", "who": ""})
    return f"  pc_{pid}[{_q(pid + ': ' + p['title'], 'who: ' + p['who'] if p['who'] else '')}]" + (f":::{cls}" if cls else "")


def open_pieces(k):
    """The board pieces that still hold an open cause, in board order of first mention."""
    return list(dict.fromkeys(f["piece"] for f in k["findings"] if f.get("piece") and f["status"] == "open"))


def maintainer_loop(k, plan=PLAN):
    steps = k["maintainer_loop"]
    pieces = board(plan)
    out = ["```mermaid", "flowchart TD"]
    for sid, title in steps:
        out.append(f"  {sid}[{_q(title)}]")
    for (a, _), (b, _) in zip(steps, steps[1:]):
        out.append(f"  {a} --> {b}")
    out.append(f"  {steps[-1][0]} -->|next cycle| {steps[0][0]}")
    ids = [s[0] for s in steps]
    # the verdict table of docs/PLAN.md: what the read shows -> the next piece, then that piece is claimed
    if "verdict" in ids:
        drawn = set()
        for j, (shows, pid, said) in enumerate(verdict_rows(plan)):
            shows = _short(re.sub(r" \(.*", "", shows), 60)
            if pid:
                out.append(f"  verdict -->|{_q(shows)}| pc_{pid}")
                if pid not in drawn:
                    out.append(_piece_node(pid, pieces))
                    if "claim" in ids:
                        out.append(f"  pc_{pid} -.-> claim")
                    drawn.add(pid)
            else:
                out.append(f"  vstop{j}[{_q(_short(said, 70))}]:::open")
                out.append(f"  verdict -->|{_q(shows)}| vstop{j}")
        still = open_pieces(k)
        if still and "claim" in ids:
            out.append(f"  waiting[{_q('pieces with open causes (section 3)', ', '.join(still))}]:::open")
            out.append("  waiting -.-> claim")
    out.append("  kj[(docs/knowledge.json)]")
    out.append(f"  kj -.->|read first| {steps[0][0]}")
    out.append(f"  {steps[-2][0] if len(steps) > 1 else steps[-1][0]} -.->|written| kj")
    out += ["  classDef open fill:#fdecec,stroke:#d03b3b,color:#0b0b0b", "```"]
    return "\n".join(out)


def finding_chain(k, plan=PLAN):
    """What was seen -> its cause -> its fix -> the board piece, for every finding that names a piece."""
    pieces = board(plan)
    mine = sorted((f for f in k["findings"] if f.get("piece")), key=lambda f: (list(pieces).index(f["piece"]) if f["piece"] in pieces else 99, f["id"]))
    out = ["```mermaid", "flowchart LR"]
    for pid in dict.fromkeys(f["piece"] for f in mine):
        still = any(f["status"] == "open" for f in mine if f["piece"] == pid)
        out.append(_piece_node(pid, pieces, "open" if still else "fixed"))
    for f in mine:
        i, st = f["id"], f["status"]
        out.append(f"  s_{i}[/{_q(f['found'])}/]")
        out.append(f"  c_{i}[{_q(f['title'])}]:::{st}")
        out.append(f"  x_{i}([{_q(f.get('fix') or 'no fix yet' + (': ' + f['by'] if f.get('by') else ''))}]):::{st}")
        out.append(f"  s_{i} --> c_{i} --> x_{i} --> pc_{f['piece']}")
    out += ["  classDef fixed fill:#e7f4e4,stroke:#0ca30c,color:#0b0b0b", "  classDef open fill:#fdecec,stroke:#d03b3b,color:#0b0b0b", "```"]
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


def size(mermaid):
    """(nodes, edges) of a drawn graph: an edge is an arrow or a dotted line, a node any id that one names or defines."""
    nodes, edges = set(), 0
    for ln in mermaid.splitlines()[2:-1]:
        ln = ln.strip()
        if not ln or ln.startswith(("classDef", "end", "subgraph")):
            continue
        ln = re.sub(r'"[^"]*"', '""', ln)
        arrows = re.findall(r"-\.->|-->|-\.-", ln)
        edges += len(arrows)
        for part in re.split(r"-\.->|-->|-\.-", ln):
            part = re.sub(r"^\|[^|]*\|", "", part.strip()).strip()
            m = re.match(r"([A-Za-z_][\w]*)", part)
            if m:
                nodes.add(m.group(1))
    return len(nodes), edges


def page(k, plan=PLAN):
    fixed = [f for f in k["findings"] if f["status"] == "fixed"]
    still = [f for f in k["findings"] if f["status"] == "open"]
    lines = ["# What is known about HiveMIND", "",
             f"**The goal:** {k['goal']}", "",
             "Drawn from `docs/knowledge.json` (and the board and verdict table of `docs/PLAN.md`) by "
             "`scripts/knowledge.py`; do not edit this page by hand. Every agent reads the file first and adds to it at "
             "the end of a cycle. How the hive is doing in numbers: [PROGRESS.md](PROGRESS.md). Who owns what, and the "
             "log of who is doing what: `docs/AGENTS.md`.", "",
             "## 1. The hive's loop: one generation", "",
             "It runs by itself on GitHub (`.github/workflows/grow.yml`), one generation after another. Each box names where "
             "the step lives, the minutes it was measured to take, and its open problem with the board piece that owns it "
             "(red border: a problem is open).", "", hive_loop(k), "",
             "## 2. The agents' loop", "",
             "Every agent working on the hive follows it, generation after generation. The verdict's branches are the rows "
             "of the verdict table in `docs/PLAN.md`; the red box lists the board pieces that still hold an open cause "
             "(section 3). Agents on other accounts cannot message each other; this file, `docs/AGENTS.md` and the pull "
             "requests are how they work together.", "", maintainer_loop(k, plan), "",
             "## 3. Findings, causes, fixes and the board", "",
             "What was seen (slanted) -> its cause -> its fix -> the board piece of `docs/PLAN.md` it belongs to. Green: "
             "fixed; red: still open (a red piece holds at least one open cause).", "", finding_chain(k, plan), "",
             "## 4. Where the causes live", "",
             "The open problems that stand between the hive and the goal (six-sided), how each is measured (slanted), the "
             "causes found in the members' own work (green: fixed, red: still open), each inside the box of the file where "
             "it lives, with that file's owner.", "", knowledge_graph(k), "",
             "## Open problems", "", "| Problem | Owner | Seen |", "|---|---|---|"]
    lines += [f"| {o['title']} | {o.get('owner') or 'unclaimed'} | {o['seen']} |" for o in k["open"]]
    lines += ["", f"## Causes found ({len(still)} open, {len(fixed)} fixed)", "", "| Cause | Where | Piece | Status | By | Seen |", "|---|---|---|---|---|---|"]
    files = {p["id"]: p["file"] for p in k["parts"]}
    lines += [f"| {f['title']} | `{files[f['lives_in']]}` | {f.get('piece', '')} | {f['status']} | {f.get('by', '')} | {f['seen']} |" for f in still + fixed]
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
        drawn = {name: size(f(k)) for name, f in (("hive loop", hive_loop), ("agents' loop", maintainer_loop),
                                                  ("findings", finding_chain), ("where causes live", knowledge_graph))}
        print(f"drawn: {PAGE.relative_to(ROOT)} ({len(k['findings'])} findings, {len(k['open'])} open problems, {len(k['rules'])} rules); "
              + "; ".join(f"{n}: {a} nodes, {b} edges" for n, (a, b) in drawn.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
