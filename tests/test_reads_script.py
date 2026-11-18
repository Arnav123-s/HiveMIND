import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_the_read_is_written_when_run_as_a_script(tmp_path):
    """The record job runs `python3 training/reads.py write ...` from the repository: the kinds (training/kinds/) must
    be found without the repository on the path (g43's read was lost to this)."""
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps({}))
    out = tmp_path / "reads"
    r = subprocess.run([sys.executable, str(ROOT / "training" / "reads.py"), "write", "g43", "--facts", str(facts),
                        "--gate", str(tmp_path / "none"), "--out", str(out)], cwd=tmp_path, capture_output=True, text=True)
    assert "ModuleNotFoundError" not in r.stderr, r.stderr[-800:]
