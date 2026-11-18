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
    assert "[met] held-out kinds passed: 0.50" in out
    assert "[met] right at the first try: 0.70" in out
    assert "[ ? ] talk exam" in out
    assert "[met] hours a generation: 2.5 h" in out


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
