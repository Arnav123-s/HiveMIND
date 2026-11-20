"""Read one user table and publish a requested JSON result without replacing existing files."""
import argparse
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .native import select
from .solver import load_csv, run_files


def publish(destination, products):
    if not products:
        return []
    if len(products) != 1:
        raise ValueError("only one output file can be published")
    name, contents = next(iter(products.items()))
    if Path(name).name != name or not name.lower().endswith(".json"):
        raise ValueError("expected a plain JSON filename")
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / name
    temporary = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=destination, delete=False) as tmp:
            temporary = Path(tmp.name)
            tmp.write(contents)
        # Linking publishes the complete file and fails if the requested name already exists.
        os.link(temporary, target)
        return [str(target)]
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("request")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("learned","flat","single","rules","agree","native"), default="learned")
    parser.add_argument("--server", help="local t80 URL when using native planning")
    args = parser.parse_args()
    text = args.file.read_text(encoding="utf-8")
    code = None
    if args.mode == "native":
        if not args.server:
            parser.error("native planning needs --server")
        rows = load_csv(text) if args.file.suffix.lower()==".csv" else json.loads(text)
        code = select(args.server, args.request, sorted(rows[0]) if rows else [])["code"]
    result = run_files(args.request, {args.file.name:text}, args.mode, code)
    if result["status"] == "answered":
        try:
            result["published"] = publish(args.out_dir, result["files"])
        except (OSError, ValueError) as error:
            result = {"status":"abstained", "reason":str(error), "published":[]}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"] == "answered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
