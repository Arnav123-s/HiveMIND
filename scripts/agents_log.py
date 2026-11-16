"""One view of every agent's log: docs/AGENTS.md from all branches, merged.

Each coding agent pushes only to its own branch (origin/claude/*) and writes its log lines in its own copy of
docs/AGENTS.md. This script reads that file from every origin/claude/* branch, origin/main and the working tree
(label "here"), merges the log entries, drops duplicates, sorts them by time and prints the newest.

    python scripts/agents_log.py [--last N] [--since "2026-11-16 22:00"] [--board] [--no-fetch]

    --last N      print the last N entries (default 25)
    --since T     print every entry from T on (instead of --last)
    --board       also print the "## The board" section of the newest docs/PLAN.md among those refs
    --no-fetch    do not run `git fetch origin` first

Entries may hold the words `claim R2`, `done T1`, `drop X3` (an id is a capital letter and digits). After the
entries a table "Pieces claimed" shows each id's latest state; two agents with a live claim on one id print "CLASH:".
"""
import argparse
import re
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDTH = 118
START = re.compile(r"^- (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})")
AGENT = re.compile(r"(?<![A-Za-z0-9])([A-Z])(?=:| \(|,)")
CLAIM = re.compile(r"\b(claim|done|drop) ([A-Z][0-9]+)\b")
SUB_AGENT = re.compile(r"^\s+- ([A-Z])\b")
STATE = {"claim": "claimed", "done": "done", "drop": "dropped"}


# ---- pure functions: text in, data out ----

def parse_entries(text):
    """Log entries of one AGENTS.md as dicts: ts ("YYYY-MM-DD HH:MM"), agent, lines (list of str)."""
    entries, cur, in_log = [], None, False
    for line in text.splitlines():
        if line.startswith("#"):
            in_log = line.lower().startswith("## log")
            cur = None
            continue
        if not in_log:
            continue
        m = START.match(line)
        if m:
            rest = line[m.end():]
            a = AGENT.search(rest)
            cur = {"ts": f"{m.group(1)} {m.group(2)}", "agent": a.group(1) if a else "?", "lines": [line]}
            entries.append(cur)
        elif line.startswith("- "):
            cur = None
        elif cur is not None:
            cur["lines"].append(line)
    for e in entries:
        while e["lines"] and not e["lines"][-1].strip():
            e["lines"].pop()
        e["text"] = "\n".join(e["lines"])
    return entries


def collapse(s):
    return " ".join(s.split())


def merge(sources):
    """sources: list of (label, text). One list of entries, no duplicates, sorted by time (stable).

    Each entry gets "branches": the labels it was found on."""
    seen, out = {}, []
    for label, text in sources:
        for e in parse_entries(text):
            key = collapse(e["text"])
            if key in seen:
                seen[key]["branches"].append(label)
            else:
                e["branches"] = [label]
                seen[key] = e
                out.append(e)
    out.sort(key=lambda e: e["ts"])
    return out


def branch_label(branches):
    """"main" if on main, else the first branch that is not the working tree, else "here"."""
    if "origin/main" in branches:
        return "main"
    named = [b for b in branches if b != "here"]
    return short(named[0]) if named else "here"


def short(ref):
    return ref.removeprefix("origin/").removeprefix("claude/")


def format_entry(e, width=WIDTH):
    head = f"{e['ts']} {e['agent']} [{branch_label(e['branches'])}] "
    body = collapse(re.sub(r"^- \d{4}-\d{2}-\d{2} \d{2}:\d{2}\s*", "", e["text"].replace("\n  - ", "\n  / ")))
    return textwrap.fill(body, width=width, initial_indent=head, subsequent_indent=" " * 4)


def select(entries, last=25, since=None):
    if since:
        return [e for e in entries if e["ts"] >= normalize_since(since)]
    return entries[-last:] if last > 0 else []


def normalize_since(s):
    s = s.strip()
    return s + " 00:00" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else s


def claims(entries):
    """Latest state per id and the clashes. entries sorted by time.

    Returns (table, clashes): table {id: {state, agent, ts, branch}}, clashes [(id, agent1, agent2), ...]."""
    table, live = {}, {}
    for e in entries:
        agent = e["agent"]
        for line in e["lines"]:
            sub = SUB_AGENT.match(line)
            who = sub.group(1) if sub else agent
            for verb, cid in CLAIM.findall(line):
                table[cid] = {"state": STATE[verb], "agent": who, "ts": e["ts"], "branch": branch_label(e["branches"])}
                holders = live.setdefault(cid, {})
                if verb == "claim":
                    holders[who] = e["ts"]
                elif verb == "done":
                    holders.clear()
                else:
                    holders.pop(who, None)
    clashes = []
    for cid, holders in live.items():
        names = sorted(holders)
        if len(names) > 1:
            clashes.append((cid, names[0], names[1]))
    return table, clashes


def format_claims(entries):
    table, clashes = claims(entries)
    lines = ["Pieces claimed"]
    if not table:
        lines.append("  (none)")
    for cid in sorted(table, key=lambda i: (i[0], int(i[1:]))):
        t = table[cid]
        lines.append(f"  {cid:<5} {t['state']:<8} {t['agent']}  {t['ts']}  [{t['branch']}]")
    for cid, a, b in clashes:
        lines.append(f"CLASH: {cid} is claimed by both {a} and {b}")
    return "\n".join(lines)


def board_section(text):
    """The "## The board" section of PLAN.md, up to the next "## " heading; None if absent."""
    out, on = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            if on:
                break
            on = line.startswith("## The board")
        if on:
            out.append(line)
    return "\n".join(out).rstrip() if out else None


# ---- git access ----

def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def fetch():
    r = git("fetch", "origin", "--quiet")
    if r.returncode != 0:
        print("git fetch origin failed (ignored): " + r.stderr.strip(), file=sys.stderr)


def refs():
    r = git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/claude/", "refs/remotes/origin/main")
    return sorted(set(r.stdout.split()))


def show(ref, path):
    r = git("show", f"{ref}:{path}")
    return r.stdout if r.returncode == 0 else None


def read_here(path):
    p = ROOT / path
    return p.read_text() if p.exists() else None


def read_sources(ref_list):
    out = []
    for ref in ref_list:
        text = show(ref, "docs/AGENTS.md")
        if text is not None:
            out.append((ref, text))
    here = read_here("docs/AGENTS.md")
    if here is not None:
        out.append(("here", here))
    return out


def newest_plan(ref_list):
    """(label, text) of docs/PLAN.md from the ref with the newest commit touching it, or None."""
    best = None
    for ref in ref_list:
        if show(ref, "docs/PLAN.md") is None:
            continue
        r = git("log", "-1", "--format=%ct", ref, "--", "docs/PLAN.md")
        ct = int(r.stdout.strip() or 0)
        if best is None or ct > best[0]:
            best = (ct, ref)
    here = read_here("docs/PLAN.md")
    if here is not None:
        head = git("log", "-1", "--format=%ct", "HEAD", "--", "docs/PLAN.md").stdout.strip()
        ct = int(head or 0)
        if best is None or ct > best[0]:
            return "here", here
    return (best[1], show(best[1], "docs/PLAN.md")) if best else None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge every agent's docs/AGENTS.md log into one view.")
    ap.add_argument("--last", type=int, default=25)
    ap.add_argument("--since")
    ap.add_argument("--board", action="store_true")
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args(argv)
    if not a.no_fetch:
        fetch()
    ref_list = refs()
    entries = merge(read_sources(ref_list))
    for e in select(entries, a.last, a.since):
        print(format_entry(e))
    print()
    print(format_claims(entries))
    if a.board:
        print()
        plan = newest_plan(ref_list)
        sec = board_section(plan[1]) if plan else None
        if plan and sec:
            print(f"The board (from {plan[0]}):")
            print(sec)
        elif plan:
            print(f"docs/PLAN.md on {plan[0]} has no '## The board' section")
        else:
            print("no docs/PLAN.md yet")


if __name__ == "__main__":
    main()
