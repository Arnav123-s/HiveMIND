"""scripts/agents_log.py: parsing, merging, claims (pure functions, no git)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("agents_log", Path(__file__).resolve().parents[1] / "scripts" / "agents_log.py")
al = importlib.util.module_from_spec(spec)
spec.loader.exec_module(al)

DOC = """# Agents

## Who
- 2026-01-01 00:00 Z: not a log line

## Log (newest last)
- 2026-11-16 22:11 B: first line
  continued here
  - C: sub-bullet, claim R2
- 2026-11-16 17:00 UTC, C (the lead; x): **text** claim T1
- 2026-11-15 21:30 UTC, A: older
- 2026-11-16 23:00 no letter here

## After
- 2026-11-17 00:00 D: outside the log
"""


def test_parse_formats_and_continuation():
    es = al.parse_entries(DOC)
    assert [e["agent"] for e in es] == ["B", "C", "A", "?"]
    assert es[0]["ts"] == "2026-11-16 22:11"
    assert "continued here" in es[0]["text"] and "sub-bullet" in es[0]["text"]
    assert "continued" not in es[1]["text"]


def test_merge_dedup_and_sort():
    other = DOC.replace("first line\n  continued", "first line\n  continued")
    es = al.merge([("origin/main", DOC), ("origin/claude/x", "## Log\n- 2026-11-16 18:00 A: extra\n")])
    assert len(es) == 5 and len({al.collapse(e["text"]) for e in es}) == 5
    assert [e["ts"] for e in es] == sorted(e["ts"] for e in es)
    assert es[0]["agent"] == "A"


def test_dedup_ignores_whitespace():
    a = "## Log\n- 2026-11-16 10:00 A: a  b\n"
    b = "## Log\n- 2026-11-16 10:00 A: a b\n"
    assert len(al.merge([("here", a), ("origin/claude/x", b)])) == 1


def test_branch_label():
    assert al.branch_label(["origin/claude/foo", "origin/main"]) == "main"
    assert al.branch_label(["here", "origin/claude/foo"]) == "foo"
    assert al.branch_label(["here"]) == "here"


def test_select_last_and_since():
    es = al.merge([("here", DOC)])
    assert len(al.select(es, last=2)) == 2
    assert [e["ts"] for e in al.select(es, since="2026-11-16 22:00")] == ["2026-11-16 22:11", "2026-11-16 23:00"]


def test_format_wraps():
    e = {"ts": "2026-11-16 10:00", "agent": "A", "branches": ["here"],
         "text": "- 2026-11-16 10:00 A: " + "word " * 80}
    lines = al.format_entry(e).splitlines()
    assert lines[0].startswith("2026-11-16 10:00 A [here] ")
    assert all(len(x) <= 118 for x in lines) and lines[1].startswith("    ")


def test_claims_states():
    t = ("## Log\n- 2026-11-16 10:00 A: claim R2 and claim T1\n- 2026-11-16 11:00 B: done R2\n"
         "- 2026-11-16 12:00 A: drop T1\n")
    table, clashes = al.claims(al.merge([("here", t)]))
    assert table["R2"]["state"] == "done" and table["R2"]["agent"] == "B"
    assert table["T1"]["state"] == "dropped" and not clashes


def test_clash_and_subbullet_agent():
    t = ("## Log\n- 2026-11-16 10:00 A: claim R2\n- 2026-11-16 11:00 B: claim R2\n"
         "- 2026-11-16 12:00 C: x\n  - D: claim S1\n")
    es = al.merge([("here", t)])
    table, clashes = al.claims(es)
    assert clashes == [("R2", "A", "B")]
    assert table["S1"]["agent"] == "D"
    out = al.format_claims(es)
    assert "CLASH: R2" in out and "A" in out and "B" in out


def test_board_section():
    plan = "# P\n## The board\nrow 1\nrow 2\n\n## Next\nno\n"
    assert al.board_section(plan) == "## The board\nrow 1\nrow 2"
    assert al.board_section("## Other\nx") is None
