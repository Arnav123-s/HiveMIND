"""Check physical JSON outputs from the post-study publisher against the sealed transfer panel."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from training.experiments.verified_growth.transfer.score import EXTRAS, equal


HERE = Path(__file__).resolve().parent
SUITE = HERE.parent / "transfer"


def measure():
    requests = json.loads((SUITE / "panel/requests.json").read_bytes())
    tables = json.loads((SUITE / "panel/tables.json").read_bytes())
    demonstrations = json.loads((SUITE / "teacher.json").read_bytes())
    records = []
    for case in requests:
        for arm in ("rules", "seen_library"):
            teacher = next((t for t in demonstrations.values() if case["id"] in t["answers"]), None)
            if arm == "seen_library" and teacher is None:
                continue
            outputs = []
            for edition in case["tables"]:
                with TemporaryDirectory() as tmp:
                    d = Path(tmp)
                    source = d / (edition + ".csv")
                    source.write_text(tables[edition]["csv"])
                    request = case["request"] + " Save the answer as result.json."
                    args = [sys.executable, "-m", "training.experiments.verified_growth.composer.checked_files",
                            str(source), request, "--out-dir", str(d / "out")]
                    if arm == "seen_library":
                        demonstration = d / "demo.json"
                        demonstration.write_text(json.dumps({"rows":teacher["rows"], "answer":teacher["answers"][case["id"]]}))
                        args += ["--example", str(demonstration)]
                    proc = subprocess.run(args, cwd=HERE.parents[3], capture_output=True, text=True, timeout=20)
                    result = json.loads(proc.stdout)
                    file = d / "out/result.json"
                    data = file.read_bytes() if file.exists() else None
                    if (proc.returncode == 0) != (data is not None) or (result["status"] == "answered") != (data is not None):
                        raise RuntimeError("file and delivery receipt disagree")
                    outputs.append({"edition": edition, "answered": data is not None,
                                    "value": json.loads(data) if data is not None else None,
                                    "file_sha256": sha256(data).hexdigest() if data is not None else None})
            records.append({"id":case["id"], "pattern":case["pattern"], "arm":arm, "outputs":outputs})
    keys = json.loads((SUITE / "panel/keys.json").read_bytes())
    for record in records:
        grades = []
        for output in record["outputs"]:
            key = keys[record["id"] + "/" + output["edition"]]
            grades.append("withheld" if not output["answered"] else
                          "correct" if record["pattern"] != "clarify" and equal(output["value"], key["value"]) else "wrong")
        record["paired"] = "correct" if all(g=="correct" for g in grades) else "wrong" if "wrong" in grades else "withheld"
    counts = {arm:dict(Counter(r["paired"] for r in records if r["arm"] == arm and r["pattern"] not in EXTRAS))
              for arm in ("rules", "seen_library")}
    return {"publisher_sha256":sha256((HERE / "checked_files.py").read_bytes()).hexdigest(),
            "counts_primary":counts, "records":records}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = measure()
    print(result["counts_primary"])
    args.out.write_text(json.dumps(result, indent=2)+"\n")
