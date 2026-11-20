"""Score independent English requests using fresh processes for the actual, model-free CLI and stock local prepass."""
import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
from resource import RUSAGE_CHILDREN, getrusage
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
MODULE = "training.experiments.atlas.service.ask"
ALLOWED_UNITS = {
    "weekday": {"weekday", "day of the week", "day-of-week", "weekday name"},
    "days": {"days", "day"}, "integer": {"int", "integer", "gcd", "number"},
    "fahrenheit": {"f", "°f", "fahrenheit", "degrees fahrenheit"}, "dollars": {"dollar", "dollars", "usd"},
    "cents": {"cent", "cents", "usd cents"},
}


def match(value, unit, key):
    expected_quantity = key["unit"]
    if unit is None and expected_quantity in {"weekday", "integer"}:
        unit = expected_quantity
    unit = str(unit).strip().casefold()
    if unit not in ALLOWED_UNITS[expected_quantity]:
        return False
    if expected_quantity == "weekday":
        return isinstance(value, str) and value.strip().casefold() == key["value"]
    if type(value) not in (str, int, float):
        return False
    try:
        return Decimal(str(value)) == Decimal(str(key["value"]))
    except InvalidOperation:
        return False


def invoke(command, env, cpus):
    before = getrusage(RUSAGE_CHILDREN)
    start = time.monotonic()
    try:
        proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
                              preexec_fn=lambda: os.sched_setaffinity(0, cpus))
        stdout, stderr, code = proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except subprocess.TimeoutExpired:
        stdout, stderr, code = "", "60-second process timeout", None
    after = getrusage(RUSAGE_CHILDREN)
    return dict(stdout=stdout, stderr=stderr, exit=code, seconds=round(time.monotonic()-start, 4),
                user_seconds=round(after.ru_utime-before.ru_utime, 4),
                system_seconds=round(after.ru_stime-before.ru_stime, 4))


def run(sdk, cpus, expected_hash):
    src = ROOT / "training/experiments/atlas/service/ask.py"
    bank = ROOT / "training/reports/retained-skills/shipping/bank"
    assert hashlib.sha256(src.read_bytes()).hexdigest() == expected_hash
    pinned = json.loads((HERE / "tested-source.json").read_text())
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in pinned.items())
    panel = json.loads((HERE / "panel.json").read_text())
    keys = json.loads((HERE / "keys.json").read_text())
    for filename, digest in json.loads((HERE / "commitment.json").read_text()).items():
        assert hashlib.sha256((HERE / filename).read_bytes()).hexdigest() == digest
    rows, smoke = [], []
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ | {"HIVE_BANK": str(bank), "HIVE_FIELDWORK_SDK": str(sdk.resolve()),
                            "HIVE_ROLES": "0", "HIVE_TERNARY_BIN": str(Path(tmp)/"absent-model"),
                            "HF_HUB_OFFLINE": "1", "AGENT_TEAM_HOME": str(Path(tmp)/"state"),
                            "RAYON_NUM_THREADS": str(len(cpus)), "OMP_NUM_THREADS": str(len(cpus)),
                            "OPENBLAS_NUM_THREADS": "1"}
        service = [sys.executable, "-m", MODULE, "--sdk", str(sdk.resolve()), "--bank", str(bank)]
        for i, case in enumerate(panel):
            # Alternate the first arm to distribute startup and machine drift.
            for arm in (("combined", "stock") if i % 2 == 0 else ("stock", "combined")):
                ident = case["id"]
                prompt, key = case["question"], keys[ident]
                command = (service + ["--json", prompt] if arm == "combined"
                           else [sys.executable, str(HERE/"stock.py"), prompt])
                result = invoke(command, env, cpus)
                try:
                    response = json.loads(result["stdout"])
                except (ValueError, TypeError):
                    response = {}
                status = str(response.get("status", "")).casefold()
                value = response.get("value")
                if status == "answered" and result["exit"] == 0:
                    verdict = "correct" if key["value"] is not None and match(value, response.get("unit"), key) else "wrong"
                elif status in {"withheld", "abstain", "abstained", "unsupported", "missing", "ambiguous", "unavailable",
                                "declined"} and value is None and result["exit"] in (0, 1, 2):
                    verdict = "justified_abstention" if key["value"] is None else "missed"
                else:
                    verdict = "error"
                rows.append(dict(arm=arm, id=ident, key=key, verdict=verdict, response=response, **result))
                print(arm, ident, verdict, result["seconds"], flush=True)
        for ident in ("leap-appointment", "separate-parcels"):
            case = next(c for c in panel if c["id"] == ident)
            smoke.append(dict(id=ident, **invoke(service+[case["question"]], env, cpus)))
    summary = {}
    for arm in ("stock", "combined"):
        group = [r for r in rows if r["arm"] == arm]
        summary[arm] = dict(counts=dict(Counter(r["verdict"] for r in group)),
                            routes=dict(Counter(str(r["response"].get("route")) for r in group)),
                            seconds=round(sum(r["seconds"] for r in group), 4),
                            user_seconds=round(sum(r["user_seconds"] for r in group), 4),
                            system_seconds=round(sum(r["system_seconds"] for r in group), 4))
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in pinned.items())
    return dict(service_sha256=expected_hash, sources=pinned, python=sys.version.split()[0], cpus=sorted(cpus),
                sdk_wasm_sha256=hashlib.sha256((sdk/"python.wasm").read_bytes()).hexdigest(),
                bank_files={f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(bank.glob('*.json'))},
                per_process_limit_seconds=60, summary=summary, records=rows, terminal=smoke)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--service-sha256", required=True)
    parser.add_argument("--cpus", help="one CPU assigned to the run")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    cpus = {int(s) for s in args.cpus.split(",")} if args.cpus else {min(os.sched_getaffinity(0))}
    assert cpus <= os.sched_getaffinity(0) and len(cpus) == 1
    args.out.write_text(json.dumps(run(args.sdk, cpus, args.service_sha256), indent=2, ensure_ascii=False)+"\n")
