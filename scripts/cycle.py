"""Start of every work cycle: one screen of where the hive stands, drawn from the records.

    python scripts/cycle.py            # the last 8 generations
    python scripts/cycle.py --last 15

It reads only files in the repo (no network): training/reports/generations.jsonl, docs/reads/latest.md,
training/reports/talk/<gen>.json, docs/progress/*.svg and the log at the end of docs/AGENTS.md.
It prints, in order:
  1. the goal's bars against the newest generation;
  2. a table and a text graph of the last generations (score, hard, easy, first try, hours, slices lost);
  3. which graphs in docs/progress are older than the newest record (stale: the record job did not redraw them);
  4. the newest read's next piece;
  5. the board's pieces and who holds them;
  6. who holds the loop now (the newest "holds the loop" log line) and the last log lines.
Read it before choosing any work, so that nobody redoes what the records already settle.
"""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORDS = ROOT / "training/reports/generations.jsonl"
LATEST = ROOT / "docs/reads/latest.md"
TALK = ROOT / "training/reports/talk"
GRAPHS = ROOT / "docs/progress"
LOG = ROOT / "docs/AGENTS.md"
PLAN = ROOT / "docs/PLAN.md"
CLAIM = re.compile(r"\b(claim|done|drop) ([A-Z][0-9]+[a-z]?)\b")

# The goal's bars (docs/PLAN.md): hard 18 of 23, half the held-out kinds, 0.7 at the first try, talk 8 of 10, 3 hours.
BARS = {"hard": 18 / 23, "held": 0.5, "first": 0.7, "talk": 0.8, "hours": 3.0}


def records(root=ROOT):
    path = root / RECORDS.relative_to(ROOT)
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def row(rec):
    paired = rec.get("paired") or {}
    after = paired.get("after") or {}
    before = paired.get("before") or {}
    ft = rec.get("first_try") or []
    lost = rec.get("lost_slices") or []
    return {
        "gen": rec.get("generation", "?"),
        "verdict": rec.get("verdict") or ("kept" if rec.get("kept") else "dropped"),
        "passed": after.get("passed"), "tasks": after.get("tasks"), "before": before.get("passed"),
        "hard": after.get("hard"), "easy": after.get("easy"),
        "first": (ft[0] / ft[1]) if len(ft) == 2 and ft[1] else None,
        "hours": rec.get("hours"),
        "lost": f"{lost[0]}/{lost[1]}" if len(lost) == 2 else "-",
        "by": rec.get("started_by", "-"),
        "trial": rec.get("trial", False),
    }


def frac(pair):
    return f"{pair[0]}/{pair[1]}" if isinstance(pair, list) and len(pair) == 2 else "-"


def table(rows):
    lines = ["| gen | verdict | body after (before) | hard | easy | first try | hours | slices lost | started by |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        score = f"{r['passed']}/{r['tasks']} ({r['before']})" if r["passed"] is not None else "-"
        first = f"{r['first']:.2f}" if r["first"] is not None else "-"
        hours = f"{r['hours']}" if r["hours"] is not None else "-"
        lines.append(f"| {r['gen']}{' (trial)' if r['trial'] else ''} | {r['verdict']} | {score} | {frac(r['hard'])} | "
                     f"{frac(r['easy'])} | {first} | {hours} | {r['lost']} | {r['by']} |")
    return "\n".join(lines)


def spark(rows, width=40):
    """A text graph of the body's score, one line a generation."""
    out = []
    for r in rows:
        if r["passed"] is None or not r["tasks"]:
            continue
        share = r["passed"] / r["tasks"]
        hard = r["hard"][0] / r["hard"][1] if isinstance(r["hard"], list) and r["hard"][1] else 0
        out.append(f"{r['gen']:>5} score {'#' * round(share * width):<{width}} {share:4.0%}   "
                   f"hard {'=' * round(hard * 20):<20} {hard:4.0%}")
    return "\n".join(out)


def talk_of(gen, root=ROOT):
    path = root / TALK.relative_to(ROOT) / f"{gen}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    value = data.get("out_of_10")
    return float(value) if isinstance(value, (int, float)) else None


def first_note(rec):
    """Where the first try is measured, and its split by orders and by the kinds' age when the record has them."""
    def share(c):
        return f"{c[0] / c[1]:.2f}" if isinstance(c, list) and len(c) == 2 and c[1] else "-"
    ab = rec.get("orders_ab") if isinstance(rec.get("orders_ab"), dict) else {}
    age = rec.get("first_try_by_age") if isinstance(rec.get("first_try_by_age"), dict) else {}
    out = ["practice"]
    if ab:
        out.append("orders " + ", ".join(f"{a} {share((ab[a] or {}).get('first_try'))}" for a in ("short", "full") if isinstance(ab.get(a), dict)))
    if age:
        out.append(f"old kinds {share(age.get('old'))}, new kinds {share(age.get('new'))}")
    return "; ".join(out)


def bars(newest, root=ROOT):
    r = row(newest)
    hard = None
    talk = talk_of(r["gen"], root)
    held = None
    latest = root / LATEST.relative_to(ROOT)
    if latest.exists():
        text = latest.read_text()
        m = re.search(r"never practised \(held out\) \| (\d+) of (\d+)", text)
        if m and int(m.group(2)):
            held = int(m.group(1)) / int(m.group(2))
        m = re.search(r"Hard kinds that have lessons \| (\d+) of (\d+)", text)
        if m and int(m.group(2)):
            hard = int(m.group(1)) / int(m.group(2))
    checks = [
        ("hard kinds passed", hard, BARS["hard"], True, "hard kinds that have lessons, from the newest read"),
        ("held-out kinds passed", held, BARS["held"], True, "from the newest read"),
        ("right at the first try", r["first"], BARS["first"], True, first_note(newest)),
        ("talk exam, of 10", (talk / 10) if talk is not None else None, BARS["talk"], True, "training/reports/talk"),
        ("hours a generation", r["hours"], BARS["hours"], False, "first job to last"),
    ]
    lines = []
    for name, value, bar, higher, note in checks:
        if value is None:
            lines.append(f"  [ ? ] {name}: not measured ({note})")
            continue
        met = value >= bar if higher else value <= bar
        show = f"{value:.2f}" if name != "hours a generation" else f"{value} h"
        want = f"{bar:.2f}" if name != "hours a generation" else f"{bar} h"
        split = f"; {note.split('; ', 1)[1]}" if name == "right at the first try" and "; " in note else ""
        lines.append(f"  [{'met' if met else ' no'}] {name}: {show} (bar {want}){split}")
    return "\n".join(lines)


def stale_graphs(newest, root=ROOT):
    when = newest.get("when")
    try:
        recorded = datetime.strptime(when, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return []
    folder = root / GRAPHS.relative_to(ROOT)
    out = []
    for svg in sorted(folder.glob("*.svg")) if folder.exists() else []:
        text = svg.read_text(errors="ignore")
        if newest.get("generation", "") not in text and svg.stat().st_mtime < recorded:
            out.append(svg.name)
    return out


def next_piece(root=ROOT):
    latest = root / LATEST.relative_to(ROOT)
    if not latest.exists():
        return "no read yet (docs/reads/latest.md)"
    for line in latest.read_text().splitlines():
        if line.startswith("next piece:"):
            return line[:400]
    return "the newest read has no next piece line"


def log_lines(root=ROOT, last=6):
    path = root / LOG.relative_to(ROOT)
    if not path.exists():
        return None, []
    lines = [l for l in path.read_text().splitlines() if re.match(r"- 20\d\d-\d\d-\d\d \d\d:\d\d ", l)]
    holder = next((l for l in reversed(lines) if "holds the loop" in l), None)
    return holder, lines[-last:]


def board(root=ROOT):
    """(id, piece, who) of each row of the board in docs/PLAN.md, with the latest claim/done/drop from the log."""
    plan = root / PLAN.relative_to(ROOT)
    if not plan.exists():
        return []
    text = plan.read_text()
    start = text.find("## The board")
    if start == -1:
        return []
    rows = []
    for line in text[start:].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and re.fullmatch(r"[A-Z][0-9]+[a-z]?", cells[0]):
            rows.append([cells[0], cells[1], cells[-1]])
    log = root / LOG.relative_to(ROOT)
    latest = {}
    if log.exists():
        for line in log.read_text().splitlines():
            m = re.match(r"- (20\d\d-\d\d-\d\d \d\d:\d\d) ([A-Za-z0-9]+)", line)
            if not m:
                continue
            for verb, pid in CLAIM.findall(line):
                latest[pid] = f"{verb} by {m.group(2)} at {m.group(1)}"
    for r in rows:
        if r[0] in latest:
            r[2] = f"{r[2]}; log: {latest[r[0]]}"
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(description="Where the hive stands, before any work.")
    p.add_argument("--last", type=int, default=8)
    args = p.parse_args(argv)
    recs = records()
    if not recs:
        print("no generation records yet (training/reports/generations.jsonl)")
        return 0
    rows = [row(r) for r in recs[-args.last:]]
    newest = recs[-1]
    print(f"# Where the hive stands: newest record {newest.get('generation')} ({newest.get('when')} UTC)\n")
    print("## The goal's bars, newest generation\n" + bars(newest) + "\n")
    print(f"## The last {len(rows)} generations\n" + table(rows) + "\n")
    print("```\n" + spark(rows) + "\n```\n")
    stale = stale_graphs(newest)
    print("## Graphs (docs/progress, drawn into docs/PROGRESS.md)\n" +
          (f"  STALE, not redrawn since {newest.get('generation')}: {', '.join(stale)}"
           " (run: python training/progress.py)" if stale else "  all redrawn for the newest record") + "\n")
    print("## Next piece (docs/reads/latest.md)\n  " + next_piece() + "\n")
    pieces = board()
    print("## The board (docs/PLAN.md; claims on other branches: python scripts/agents_log.py --board)")
    for pid, piece, who in pieces:
        print(f"  {pid:<4} {who[:60]:<60} {piece[:90]}")
    print()
    holder, lines = log_lines()
    print("## Who holds the loop\n  " + (holder or "nobody has claimed it in the log") + "\n")
    print("## Last log lines (docs/AGENTS.md)")
    for line in lines:
        print("  " + line[:220])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
