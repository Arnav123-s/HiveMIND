"""Builds demo/README.md from the demo run's own records (nothing hand-written about results)."""
import json
import sqlite3
from pathlib import Path

D = Path(__file__).resolve().parent
RUN = D / "run"


def main():
    task = (RUN / "TASK.md").read_text().strip()
    plan = json.loads((RUN / "plan.json").read_text()) if (RUN / "plan.json").exists() else []
    db = sqlite3.connect(RUN / "board.db")
    db.row_factory = sqlite3.Row
    steps = [dict(r) for r in db.execute("SELECT * FROM steps ORDER BY rowid")]
    facts = [dict(r) for r in db.execute("SELECT * FROM facts")]
    approvals = [dict(r) for r in db.execute("SELECT * FROM approvals")]
    events = [json.loads(x) for x in (RUN / "events.jsonl").read_text().splitlines()]
    calls = sum(1 for _ in open(RUN / "calls.jsonl")) if (RUN / "calls.jsonl").exists() else 0
    t0, t1 = events[0]["ts"], events[-1]["ts"]
    shots = sorted(p.name for p in (RUN / "screens").glob("*.png"))
    work = sorted(p.name for p in (RUN / "work").iterdir()) if (RUN / "work").exists() else []

    out = ["# Demo: one prompt, whole team, end to end", "",
           "Everything below is generated from the run's own records in `demo/run/` "
           "(`board.db`, `events.jsonl`, `calls.jsonl`). Nothing was edited by hand.", "",
           "## The one prompt", "", "> " + task.replace("\n", "\n> "), "",
           f"Wall time: {(t1 - t0) / 60:.0f} min on a 4-core CPU, no GPU. Model calls: {calls}.", "",
           "## The plan the coordinator made", ""]
    for s in plan:
        fe = f" (repeated for each item of {s['for_each']})" if s.get("for_each") else ""
        out.append(f"- **{s['id']} → {s['agent']}**{fe}: {s['task']}  \n  _done when:_ {s.get('done_when', '')}")
    out += ["", "## What happened to each step", "", "| step | specialist | verdict | attempts | verifier's reason |",
            "|---|---|---|---|---|"]
    for s in steps:
        out.append(f"| {s['id']} | {s['agent']} | {s.get('verdict') or s['status']} | {s.get('attempts') or 0} | "
                   f"{str(s.get('feedback') or '').replace('|', '/')[:200]} |")
    sup = [f for f in facts if f["status"] == "supported"]
    rej = [f for f in facts if f["status"] != "supported"]
    out += ["", f"## Facts: {len(sup)} supported, {len(rej)} rejected", ""]
    for f in sup:
        out.append(f"- ✅ {f['claim'][:200]}  \n  quote: `{f['quote'][:200]}`  \n  source: {f['url']}")
    for f in rej:
        out.append(f"- ❌ {f['claim'][:200]} ({f['note'][:120]})")
    out += ["", "## Browser work (real Chromium, screenshots after each action)", ""]
    for s in steps:
        if s["agent"] == "browser" and s.get("result"):
            try:
                r = json.loads(s["result"])
            except (TypeError, json.JSONDecodeError):
                continue
            out.append(f"**{s['id']}** - {s['task'][:160]}")
            for a in r.get("actions", []):
                out.append(f"  - {a}")
            if r.get("summary"):
                out.append(f"  - **answer:** {r['summary'][:200]}  \n  - **evidence on page:** `{r.get('evidence', '')[:200]}`")
            out.append("")
    out += [f"Screenshots: {len(shots)} in `demo/run/screens/`.", "", "## Code the team wrote and ran", ""]
    for name in work:
        out.append(f"- `demo/run/work/{name}`")
    out += ["", "## Approvals", ""] + ([f"- {a['agent']}: {a['kind']} - {a['detail']} -> {a['decision']}" for a in approvals]
                                       or ["- none were needed"])
    out += ["", "## The finished report", "", "See [`run/REPORT.md`](run/REPORT.md). Copied here:", "", "---", "",
            (RUN / "REPORT.md").read_text(), ""]
    (D / "README.md").write_text("\n".join(out))
    print("wrote", D / "README.md")


if __name__ == "__main__":
    main()
