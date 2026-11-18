"""Run a frozen field worker on one new JSON input and write its actual result to stdout."""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

from .guest import Guest
from .numeric_guest import NumericGuest


def load_worker(archive, name):
    with zipfile.ZipFile(archive) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        if name not in manifest:
            raise ValueError("choose one of " + ", ".join(sorted(manifest)))
        worker = manifest[name]
        payload = bundle.read("workers/" + name + ".py")
        if hashlib.sha256(payload).hexdigest() != worker["sha256"]:
            raise ValueError("source does not match the worker's manifest")
    return payload.decode(), worker["runtime"]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--worker", required=True)
    p.add_argument("--sdk", type=Path, help="CPython WASI directory for standard-library workers")
    p.add_argument("--input", type=Path, help="one JSON object or array (defaults to stdin)")
    args = p.parse_args(argv)
    source, runtime = load_worker(args.archive, args.worker)
    if runtime == "wasi":
        if args.sdk is None:
            p.error("this worker requires --sdk")
        guest = Guest(args.sdk)
    elif runtime == "numpy":
        guest = NumericGuest()
    else:
        p.error("unsupported runtime in the worker manifest")
    sample = json.loads(args.input.read_text()) if args.input else json.load(sys.stdin)
    rows, _, _ = guest.run(source, [sample], fuel=115_000_000_000)
    if "error" in rows[0]:
        p.exit(1, rows[0]["error"] + "\n")
    print(json.dumps(rows[0]["value"], allow_nan=False))


if __name__ == "__main__":
    main()
