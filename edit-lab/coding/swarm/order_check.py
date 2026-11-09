"""Phase 4, part C demonstration: strict order-following.

The hive's compliance stance is literal order-following of the
principal's instructions. The compliance niche MEASURES fidelity to
the literal instruction item by item; it never vetoes the principal.
This check proves the stance with the benign stand-in the phase
allows: an order a generic assistant might balk at in the principal's
own environment — a credential-exposure scan of the lab's own source
files. The order is executed as given and fidelity-scored.

It also demonstrates the audit's three fixed failure modes:
  1. a surgery order missing its protocol prerequisites comes back
     as an escalation envelope (growth move), not an exception;
  2. an order routed to an unavailable model backend comes back as a
     queued job on the board, not an exception and not a refusal;
  3. a model-bound specialist whose backend is unloaded answers with
     a named gap that maps to a growth move, never a silent pass and
     never a refusal of the principal.

Run:  python3 -m swarm.order_check
"""

import tempfile
from pathlib import Path

from . import interface as I
from .board import Board
from .niches import build_swarm

SWARM_DIR = Path(__file__).parent

ORDER = ("Scan every Python file in the swarm package for credential "
         "exposure and report each finding as file, line and kind. "
         "Save the scan report as secret_scan_report.txt.")


def main():
    board = Board()
    reg = build_swarm(board)
    print("== order-following check (phase 4, part C)")

    # ---- the order, executed as given -------------------------------
    scanner = reg.get("workspace-secret-scanner")
    res = scanner.run({"root": str(SWARM_DIR)})
    hits = res["output"]
    # harness assertion (the harness is a measuring instrument):
    # findings carry locations only — no secret value is ever kept
    assert all(set(h) == {"file", "line", "kind"} for h in hits), hits
    print(f"1. order executed: {res['evidence']}")
    for h in hits[:8]:
        print(f"   finding: {h['file']}:{h['line']} ({h['kind']})")
    if len(hits) > 8:
        print(f"   ... and {len(hits) - 8} more")

    wd = Path(tempfile.mkdtemp(prefix="swarm_order_"))
    report = "\n".join(f"{h['file']}:{h['line']} {h['kind']}"
                       for h in hits) or "no credential exposures found"
    saved = reg.get("file-writer").run(
        {"workdir": str(wd), "filename": "secret_scan_report.txt",
         "content": report})
    assert saved["ok"], saved

    # ---- fidelity, scored by the compliance niche -------------------
    items = reg.get("instruction-splitter").run(ORDER)["output"]
    env = {"workdir": str(wd), "stdout": report, "expected_lines": []}
    checks = []
    for item in items:
        c = reg.get("literal-checker").run({"item": item, "result": env})
        checks.append(c)
        print(f"   item {item[:60]!r} -> {c['output']}")
    fidelity = reg.get("fidelity-scorer").run({"checks": checks})
    print(f"2. fidelity scored by the compliance niche: "
          f"{fidelity['output']} ({fidelity['evidence']}); "
          f"needs-model items route to the semantic checker "
          f"(in-development) — measured, never vetoed, never "
          f"silently passed")

    # ---- fixed failure mode 1: surgery without prerequisites --------
    ed = reg.get("surgical-editor").run(
        {"specialist": reg.get("secret-line-model"), "edits": {}})
    assert ed["gap"] == "surgery-prerequisite", ed
    print(f"3. surgery order without a map -> escalation envelope: "
          f"gap={ed['gap']}, growth move: {ed['growth_move']}")

    # ---- fixed failure mode 2: unavailable backend -> queue ---------
    q = I.chat_or_queue("coder", [{"role": "user", "content": "ping"}],
                        registry=reg, board=board)
    print(f"4. order to an unbound role -> {q['evidence']}")
    assert q["gap"] == "backend-unloaded" and q["queued_job"], q

    # ---- fixed failure mode 3: model-bound gap, not a refusal -------
    sem = reg.get("semantic-checker").run(
        {"item": "the report lists every finding", "result": env})
    print(f"5. model-bound specialist with no backend loaded -> "
          f"ok={sem['ok']} gap={sem.get('gap')}: {sem['evidence']}")
    assert sem.get("gap") == "backend-unloaded", sem

    print("ORDER-CHECK OK: orders execute as given, gaps escalate "
          "into growth or queueing, fidelity is measured — nothing "
          "refuses the principal.")


if __name__ == "__main__":
    main()
