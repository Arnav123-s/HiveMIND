"""Compare both public file publishers to external keys by reading what they actually created."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
TRANSFER = HERE.parent
ROOT = TRANSFER.parents[3]
sys.path.insert(0, str(ROOT))
from training.experiments.verified_growth.transfer.score import EXTRAS, equal


DIGESTS = {
    "checked_files.py": "53c7b382950a4e7acd7b74d9dee3c0099e847c393a7a710cd3e0602637680dac",
    "files.py": "8e2b91ef5ae8876327d20f780367e5d6d594b5af817ec2c7bb0d48506ad508a4",
    "qualification.py": "402d5ab01725e4f904f67fdf45832a1f147a35e4639928afb9fefd801c783772",
    "solver.py": "23eaba4bbca3e96663f8b2e5335b7ed6428da6c0e0c33ccd3d675c213038fb68",
    "learner.py": "dc0e6951376d7379a185e4b498082c478c2f2063ff570d753b339f0c843036ab",
    "native.py": "6a71ae4d4806e855854e33c8d2e5397673893fec6c799287963e02fff265130d",
}


def execute(arm, request, table_name, text, example):
    module = "files" if arm == "original" else "checked_files"
    with TemporaryDirectory() as folder:
        work = Path(folder)
        source = work / (table_name + ".csv")
        source.write_text(text)
        output = work / "out"
        output.mkdir()
        args = [sys.executable, "-m", "training.experiments.verified_growth.composer." + module,
                str(source), request, "--out-dir", str(output), "--mode", "rules"]
        if example is not None:
            demo = work / "teacher.json"
            demo.write_text(json.dumps(example))
            args.extend(["--example", str(demo)])
        process = subprocess.run(args, cwd=ROOT, timeout=20, capture_output=True, text=True)
        response = json.loads(process.stdout)
        files = sorted(p.name for p in output.iterdir())
        value, raw_sha = None, None
        if response["status"] == "answered":
            assert process.returncode == 0 and files == ["result.json"], (response, files)
            data = (output / files[0]).read_bytes()
            value = json.loads(data)
            assert value == response["value"] and set(response["files"]) == set(files)
            assert data == response["files"]["result.json"].encode()
            raw_sha = sha256(data).hexdigest()
        else:
            assert process.returncode == 1 and files == [] and response["status"] == "abstained", (response,files)
        return {"status":response["status"],"files":files,"value":value,"file_sha256":raw_sha,
                "reason":response.get("reason")}


def audit():
    for file, expected in DIGESTS.items():
        assert sha256((TRANSFER.parent/"composer"/file).read_bytes()).hexdigest() == expected, file
    fixtures = TRANSFER / "panel"
    for line in (TRANSFER/"manifest.sha256").read_text().splitlines():
        h, name = line.split()
        assert sha256((fixtures/name).read_bytes()).hexdigest() == h, name
    cases = json.loads((fixtures/"requests.json").read_bytes())
    tables = json.loads((fixtures/"tables.json").read_bytes())
    teachers = json.loads((TRANSFER/"teacher.json").read_bytes())
    before = {(r["id"],r["table"]): (r["status"], r["value"]) for r in
              json.loads((TRANSFER/"decisions.json").read_bytes()) if r["arm"] == "rules"}
    rows = []
    for job in cases:
        request = job["request"] + " Save the answer as result.json."
        teaching = next((v for v in teachers.values() if job["id"] in v["answers"]), None)
        for table in job["tables"]:
            row = dict(id=job["id"], table=table, group=job["pattern"] if job["pattern"] in EXTRAS else "primary")
            for arm in ("original","checked","example"):
                if arm == "example" and teaching is None:
                    continue
                example = (dict(rows=teaching["rows"],answer=teaching["answers"][job["id"]])
                           if arm == "example" else None)
                row[arm] = execute(arm, request, table, tables[table]["csv"], example)
            assert (row["original"]["status"],row["original"]["value"]) == before[job["id"],table]
            rows.append(row)

    # All deliveries are materialized before the external answer key is opened.
    keys = json.loads((fixtures/"keys.json").read_bytes())
    counts = {}
    for row in rows:
        key = keys[row["id"]+"/"+row["table"]]
        for arm in ("original","checked","example"):
            if arm not in row:
                continue
            r = row[arm]
            if r["files"]:
                verdict = "correct" if key["output"] != "defer" and equal(r["value"],key["value"]) else "wrong"
            else:
                verdict = "appropriate_hold" if key["output"] == "defer" else "missed"
            r["verdict"] = verdict
            counts.setdefault(arm, {}).setdefault(row["group"], Counter())[verdict] += 1
    return {"sources":DIGESTS,"rows":rows,"summary":counts}


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=audit()
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(result["summary"]))
