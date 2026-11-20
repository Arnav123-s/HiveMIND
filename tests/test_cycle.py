"""scripts/cycle.py: the start-of-cycle summary reads the records and says what it cannot measure."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import cycle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _home(tmp_path, recs, read="", log=""):
    (tmp_path / "training/reports").mkdir(parents=True)
    (tmp_path / "training/reports/generations.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    (tmp_path / "docs/reads").mkdir(parents=True)
    (tmp_path / "docs/reads/latest.md").write_text(read)
    (tmp_path / "docs/AGENTS.md").write_text(log)
    return tmp_path


REC = {"generation": "g9", "when": "2026-11-18 02:41", "verdict": "kept", "hours": 2.5, "first_try": [7, 10],
       "lost_slices": [0, 20], "started_by": "line",
       "paired": {"before": {"passed": 50, "tasks": 64}, "after": {"passed": 52, "tasks": 64, "hard": [20, 32], "easy": [32, 32]}}}
READ = ("| Hard kinds that have lessons | 19 of 23 | x |\n| Hard kinds never practised (held out) | 3 of 6 | x |\n"
        "next piece: K9: something\n")


def test_bars_read_the_newest_read_and_record(tmp_path):
    home = _home(tmp_path, [REC], READ)
    out = cycle.bars(REC, root=home)
    assert "[met] hard kinds passed: 0.83" in out
    assert "[ ? ] held-out kinds passed: not measured (pulse only 3/6)" in out
    assert "[met] right at the first try: 0.70" in out
    assert "[ ? ] talk exam" in out
    assert "[met] hours a generation: 2.5 h" in out


def test_recorded_kind_scores_take_precedence_over_the_published_read(tmp_path):
    arm = {"tasks": 3, "kinds": {"a class with rules, with hidden tests": [1, 2],
                                 "a queue served by priority, with hidden tests": [0, 1]}, "unpractised": [0, 0]}
    rec = dict(REC, arms={"after": arm})
    out = cycle.bars(rec, root=_home(tmp_path, [rec], READ))
    assert "hard kinds passed: 0.50" in out and "held-out kinds passed: not measured (pulse only 0/1)" in out


def test_talk_is_read_when_sat(tmp_path):
    home = _home(tmp_path, [REC], READ)
    (home / "training/reports/talk").mkdir()
    (home / "training/reports/talk/g9.json").write_text(json.dumps({"out_of_10": 7.5}))
    assert "[ no] talk exam, of 10: 0.75" in cycle.bars(REC, root=home)


def test_table_spark_and_holder(tmp_path):
    log = ("- 2026-11-18 05:00 B: holds the loop from now (session x)\n"
           "- 2026-11-18 06:00 C: holds the loop from now (session y)\n- 2026-11-18 06:10 C: a note\n")
    home = _home(tmp_path, [{"generation": "g1", "kept": False}, REC], READ, log)
    rows = [cycle.row(r) for r in cycle.records(home)]
    assert "| g9 | kept | 52/64 (50) | 20/32 | 32/32 | 0.70 | 2.5 | 0/20 | line |" in cycle.table(rows)
    assert "| g1 | dropped |" in cycle.table(rows)
    assert "g9 score" in cycle.spark(rows) and "g1 score" not in cycle.spark(rows)
    holder, last = cycle.log_lines(home)
    assert "C: holds the loop" in holder and len(last) == 3
    assert cycle.next_piece(home) == "next piece: K9: something"


def test_runs_on_the_real_repo():
    out = subprocess.run([sys.executable, str(ROOT / "scripts/cycle.py"), "--last", "3"], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "The goal's bars" in out.stdout and "Who holds the loop" in out.stdout


def test_board_rows_and_latest_claim(tmp_path):
    home = _home(tmp_path, [REC], READ, "- 2026-11-18 05:00 D: claim H1. by cause\n- 2026-11-18 06:00 E: done F1 (0.71)\n")
    (home / "docs/PLAN.md").write_text("# Plan\n\n## The board\n\n| Id | Piece | Files | Done when | Who |\n|---|---|---|---|---|\n"
                                       "| H1 | Held out | x | y | open |\n| F1 | First try | x | y | open |\n| J1 | Join | x | y | open |\n\n## After\n")
    rows = {r[0]: r for r in cycle.board(home)}
    assert set(rows) == {"H1", "F1", "J1"}
    assert rows["H1"][2] == "open; log: claim by D at 2026-11-18 05:00"
    assert rows["F1"][2] == "open; log: done by E at 2026-11-18 06:00"
    assert rows["J1"][2] == "open"


def test_unseen_goal_uses_fixed_kinds_and_requires_a_complete_sitting(tmp_path):
    home = _home(tmp_path, [REC], READ)
    exam = {"kinds": [5, 10], "right": 12, "of": 30}
    rec = dict(REC, held_exam={"after": exam})
    assert "[met] held-out kinds passed: 0.50 (bar 0.50) — fixed exam 5/10 kinds, 12/30 tasks" in cycle.bars(rec, home)
    exam["of"] = 29
    assert "not measured (fixed exam 5/10 kinds, 12/29 tasks, incomplete fixed exam)" in cycle.bars(rec, home)
