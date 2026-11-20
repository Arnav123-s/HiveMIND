"""Check normalized literal prompts in the archived training/evaluation JSON files at the pre-service revision."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess


def normalized(value):
    return " ".join(value.lower().split())


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)


def overlap(panel):
    revision = "904dc3a387acc056934ff5fbb9249451a5a5d5b2"
    root = Path(__file__).resolve().parents[5]
    old = subprocess.check_output(["git", "ls-tree", "-lr", revision, "--", "training"], cwd=root, text=True)
    wanted = {normalized(r["question"]): r["id"] for r in panel}
    matches, files, count = [], 0, 0
    for line in old.splitlines():
        info, name = line.split("\t", 1)
        if not name.endswith((".json", ".json.gz")) or int(info.split()[-1]) > 2 * 1024 * 1024:
            continue
        blob = subprocess.check_output(["git", "cat-file", "blob", info.split()[2]], cwd=root)
        if name.endswith(".gz"):
            blob = gzip.decompress(blob)
        try:
            value = json.loads(blob)
        except (ValueError, UnicodeError):
            continue
        files += 1
        for text in strings(value):
            count += 1
            ident = wanted.get(normalized(text))
            if ident:
                matches.append(dict(id=ident, file=name))
    return dict(revision=revision, files=files, string_values=count, normalized_matches=matches,
                scope="JSON string values in tracked training/*.json and .json.gz, up to 2 MiB stored per file.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.write_text(json.dumps(overlap(json.loads(args.panel.read_text())), indent=2) + "\n")
