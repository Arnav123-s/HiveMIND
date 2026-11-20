"""Bound the archived first-answer savings on the gate job that actually finished last."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
PULSE = HERE.parents[1] / "atlas/pulse"


def build(archives):
    snapshot = json.loads((HERE/"jobs.json").read_text())["runs"]
    changed = json.loads((PULSE/"composed/results.json").read_text())["changed_or_applicable_jobs"]
    manifest = json.loads((PULSE/"artifacts.json").read_text())
    output = {}
    for generation in ("g51", "g52"):
        job = max((j for j in snapshot[generation]["jobs"] if j["name"].startswith("gate (")),
                  key=lambda j: j["completed_at"])
        match = re.fullmatch(r"gate \((before|after), (\d+)\)", job["name"])
        assert match
        eligible_ids = {r["id"] for r in changed if r["generation"] == generation and r["certified"]
                        and match[1] == "after" and int(r["id"][1:].split("_")[0]) % 10 == int(match[2])}
        evidence = []
        if eligible_ids:
            for a in manifest:
                if a["generation"] != generation or "after" not in a["name"]:
                    continue
                path = archives/(str(a["id"])+".zip")
                assert sha256(path.read_bytes()).hexdigest() == a["sha256"]
                with ZipFile(path) as z:
                    for name in z.namelist():
                        if Path(name).name != "exam.json" or Path(name).parent.name not in eligible_ids:
                            continue
                        exam = json.loads(z.read(name))
                        evidence.append({"id": exam["id"], "seconds_entire_job": exam["seconds"],
                                         "artifact": a["id"], "path": name, "digest": a["sha256"]})
        assert set(eligible_ids) == {r["id"] for r in evidence}
        output[generation] = {"critical_gate": job["name"], "job_id": job["id"], "after_arm_matches": evidence,
                              "upper_bound_seconds": sum(r["seconds_entire_job"] for r in evidence)}
    return output


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archives", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.write_text(json.dumps(build(args.archives), indent=2) + "\n")
