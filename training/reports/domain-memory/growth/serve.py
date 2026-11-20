"""Read back the first predeclared qualification example through the ordinary talk service."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, default=HERE / "example-bank", help="checked personal bank to use")
    parser.add_argument("--out", type=Path, required=True, help="new, empty receipt directory")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--grade", action="store_true", help="re-score all four original held-outs using the packaged weights")
    args = parser.parse_args()
    home, bank = args.out.resolve(), args.bank.resolve()
    if home.exists() and any(home.iterdir()):
        raise SystemExit("The receipt directory must be empty.")
    os.environ.update(HIVE_ENGRAMS_HOME=str(bank), HIVE_TERNARY_HOME=str(home / "runtime"),
                      HIVE_TERNARY_BIN=str(args.runtime.resolve()), HIVE_BANK="off", HIVE_TERNARY_CTX="2048",
                      HIVE_TALK_LONG="12", HIVE_MEMBERS="t80", AGENT_TEAM_THREADS="1", OMP_NUM_THREADS="1",
                      OPENBLAS_NUM_THREADS="1")
    sys.path.insert(0, str(ROOT))
    from team import engram, ternary
    from training.domain_engram import _base_hash, validate
    saved = json.loads((HERE / "result.json").read_bytes())
    expected = saved["stages"][-1]["refresh"]
    selected = engram.bank_entries("t80", bank).get(expected["name"])
    if not selected or not selected[1] or selected[1].get("sha256") != expected["sha256"]:
        raise SystemExit("The checked example-bank revision is required for this reproduction.")
    model = args.model.resolve()
    stat = model.stat()
    if _base_hash(model, (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)) != expected["measurement"]["base_sha256"]:
        raise SystemExit("Use the Ternary-Bonsai 8B base from the recorded fit.")
    if args.grade:
        raw = (HERE / "incident-labels.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != saved["corpus_sha256"]:
            raise SystemExit("The frozen exercise file changed.")
        corpus = json.loads(raw)
        rows = {}
        for batch in corpus["batches"]:
            for stem, answer in batch:
                prompt = corpus["instruction"] + stem
                rows[hashlib.sha256(prompt.encode()).hexdigest()] = dict(prompt=prompt, answer=answer)
        held_out = [rows[c["prompt_sha256"]] for c in expected["measurement"]["validation"]["cases"]]
        result = validate(held_out, selected[0], model=model, runtime=args.runtime, threads=1)
        home.mkdir(parents=True, exist_ok=True)
        (home / "grade.json").write_text(json.dumps(result, indent=2) + "\n")
        print(f"Base {result['before']}/{result['count']}, edit {result['after']}/{result['count']}, regressions {result['regressions']}.")
        return
    # Isolate the port and locate the same local base without fetching any weights.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    ternary.weights = lambda base: str(model)
    witness = ROOT / "training/reports/domain-engrams/serve.py"
    sys.argv = [str(witness), "--cases", str(HERE / "served-case.json"), "--form", "choice",
                "--port", str(port), "--out", str(home)]
    try:
        runpy.run_path(str(witness), run_name="__main__")
    finally:
        owned = ternary._PROC.get(port)
        if owned is not None and owned.poll() is None:
            owned.terminate()
            try:
                owned.wait(timeout=10)
            except subprocess.TimeoutExpired:
                owned.kill()
                owned.wait()


if __name__ == "__main__":
    main()
