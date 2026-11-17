"""What is known about HiveMIND (docs/knowledge.json) holds together, and is drawn as the graphs of docs/KNOWLEDGE.md."""
import copy
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("knowledge", ROOT / "scripts" / "knowledge.py")
knowledge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(knowledge)


def test_the_knowledge_holds_together_and_the_page_is_drawn_from_it():
    k = knowledge.load()
    assert knowledge.problems(k) == []  # every link names something that exists, every file is there
    page = knowledge.page(k)
    assert len(re.findall(r"```mermaid\n", page)) == 4 and k["goal"] in page
    assert (ROOT / "docs" / "KNOWLEDGE.md").read_text() == page  # the page in the repository is drawn from the file as it is


def test_what_does_not_hold_together_is_named():
    k = knowledge.load()
    bad = copy.deepcopy(k)
    bad["findings"][0]["lives_in"] = "nowhere"
    bad["findings"][1]["blocks"] = "no such problem"
    bad["findings"][2]["status"] = "maybe"
    bad["parts"][0]["file"] = "no/such/file.py"
    bad["open"][0]["owner"] = "Z"
    bad["rules"].append(dict(bad["rules"][0]))
    said = " | ".join(knowledge.problems(bad))
    for words in ("lives in nowhere", "blocks no such problem", "status is maybe", "no file no/such/file.py", "owner Z", "used twice"):
        assert words in said
    # a finding names a piece of the board, says what was seen, and says its fix once fixed; a loop step's piece is real
    bad = copy.deepcopy(k)
    with_piece = [f for f in bad["findings"] if f.get("piece")]
    with_piece[0]["piece"] = "Q9"
    del with_piece[1]["found"]
    next(f for f in with_piece[2:] if f["status"] == "fixed").pop("fix")
    bad["hive_loop"][0]["piece"] = "Q8"
    said = " | ".join(knowledge.problems(bad))
    for words in ("piece Q9 is not on the board", "no 'found'", "no 'fix'", "piece Q8 is not on the board"):
        assert words in said


def test_the_board_and_the_verdict_are_read_from_the_plan():
    pieces = knowledge.board()
    assert {"L1", "L2", "L3", "T1", "T2", "T4", "R2", "M3"} <= set(pieces) and pieces["L2"]["who"]
    rows = knowledge.verdict_rows()
    assert len(rows) >= 4 and {"T1", "R2"} <= {pid for _, pid, _ in rows}
    assert any(pid is None for _, pid, _ in rows)  # the row that stops the line names no piece


def test_the_hive_loop_says_each_steps_minutes_and_open_problem():
    k = knowledge.load()
    g = knowledge.hive_loop(k)
    steps = k["hive_loop"]
    names = [s["id"] for s in steps]
    for want in ("practise", "dreams", "gather", "plan", "trainc", "join", "trunk", "pulse", "recordg", "verdictg", "nextg"):
        assert want in names
    for s in steps:
        assert s["minutes"] and "minutes: " + s["minutes"] in g
        if s.get("problem"):
            assert f"open: {s['problem']} ({s['piece']})" in g
    for a, b in zip(names, names[1:]):
        assert f"  {a} --> {b}\n" in g
    assert re.search(rf"  {names[-1]} -->\|.*\| {names[0]}\n", g)  # the last step leads back to the first
    assert "Study, T1" in g


def test_the_agents_loop_is_drawn_from_the_plan_and_the_findings():
    k = knowledge.load()
    g = knowledge.maintainer_loop(k)
    for words in ("read_generation.py", "verdict table in docs/PLAN.md", "Claim a board piece", "smaller agents",
                  "cheapest first", "owner's yes", "Merge to main", "next generation"):
        assert words in g
    for _, pid, _ in knowledge.verdict_rows():
        if pid:
            assert f"| pc_{pid}" in g and g.count(f"  pc_{pid} -.-> claim") == 1
    still = knowledge.open_pieces(k)
    assert still and ", ".join(still) in g
    assert set(still) == {f["piece"] for f in k["findings"] if f.get("piece") and f["status"] == "open"}
    # one more open cause on a new piece shows at once in the loop the agents follow
    more = copy.deepcopy(k)
    more["findings"].append(dict(more["findings"][-1], id="newone", piece="M1", status="open", found="seen"))
    assert "M1" in knowledge.maintainer_loop(more).split("pieces with open causes")[1].split("]")[0]


def test_each_finding_is_drawn_from_what_was_seen_to_its_board_piece():
    k = knowledge.load()
    g = knowledge.finding_chain(k)
    mine = [f for f in k["findings"] if f.get("piece")]
    assert len(mine) >= 14
    for f in mine:
        i = f["id"]
        assert f"  s_{i} --> c_{i} --> x_{i} --> pc_{f['piece']}" in g
        assert g.split(f"  c_{i}[", 1)[1].split("\n", 1)[0].endswith(f":::{f['status']}")
        if f["status"] == "open":
            assert re.search(rf"  pc_{f['piece']}\[.*\]:::open", g)  # a piece with an open cause is marked open
    # the findings of 2026-11-16 and 17 asked for, each on its piece
    want = {"stalebody": "L3", "cpuflags": "L1", "colaball": "L2", "twowaves": "L2", "practicetail": "L2",
            "slicememory": "L1", "fewpasses": "T1", "keptback": "T2", "lessonswrong": "R2", "rows32": "T4"}
    got = {f["id"]: f["piece"] for f in mine}
    assert all(got.get(i) == p for i, p in want.items())
    assert {f["id"] for f in mine if f["status"] == "open"} >= {"lessonswrong", "rows32"}
    nodes, edges = knowledge.size(g)
    assert nodes == 3 * len(mine) + len({f["piece"] for f in mine}) and edges == 3 * len(mine)
