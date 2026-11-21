"""Run known-correct references and an unrelated program through the same WASI and host graders."""
import argparse
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

from training import exam, lessons
from training.experiments.astra_cpu.five_kinds.transfer import native
from training.experiments.replay_archive.native_cycles import pilot


def controls(sdk):
    cases = pilot.load(pilot.HERE / "panel.json", pilot.PANEL_SHA)["rows"]
    checks = {}
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        for label in ("reference", "wrong"):
            calls = []
            for row in cases:
                task, check = exam.remake(row["name"], row["seed"], 0)[2:]
                source = lessons.program_for(task, check) if label == "reference" else 'print("unknown")'
                assert source
                calls.append({"name": row["name"], "text": f"```python\n{source}\n```"})
            native.save(home / f"{label}-calls.json", {"complete": True, "panel_sha256": pilot.PANEL_SHA,
                        "lora_sha256": "grader-control", "calls": calls})
            pilot.score(SimpleNamespace(scratch=home, arm=label, sdk=sdk))
            results = json.loads((home / f"{label}-grades.json").read_text())["results"]
            checks[label] = {name: result["passed"] for name, result in results.items()}
    assert all(checks["reference"].values()) and not any(checks["wrong"].values()), checks
    return checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    native.save(pilot.HERE / "grader-controls.json", controls(parser.parse_args().sdk))
