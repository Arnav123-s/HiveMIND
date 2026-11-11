"""The hive's living state as one file, so the hive can move and outlive any one machine.

What lives: every body (its stem cell, its cells, its map, its trainers' records), the vocabulary, the harvest and
the last measurements. What is left out can be made again from these (the text stream) or is not part of the living
hive (bodies put away).

  python training/hive_state.py pack [file]          write the state to a file; prints a short account of it
  python training/hive_state.py pull [--force] [file] bring the hive here: from a file, else from where the hive
                                                      grows on GitHub (the release "hive-state"), else from the
                                                      seed (the branch "hive-seed"). It is not unpacked over a hive
                                                      that has as many living cells or more, unless --force.
  python training/hive_state.py log                   one line on the hive as it is, added to the record of its
                                                      growth (training/reports/hive_growth.jsonl)

Nothing here logs in or needs a token: a public repository's release is fetched over plain HTTPS."""
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPO, RELEASE, SEED, NAME = "Arnav123-s/HiveMIND", "hive-state", "hive-seed", "hive-state.tar.gz"
GROWTH = ROOT / "training" / "reports" / "hive_growth.jsonl"
# what is kept of cells/scratch (everything of a body's own folder is kept, except what is named in LEFT)
TOP = ("base.pt", "stem.json", "tokenizer.json", "record.json", "corpus.json", "bodies.json", "bodies_rule.json",
       "bodies_turns.json")
LEFT = (".part", ".hard.json", "corpus.u16")


def _homes():
    from team import harvest
    from training import scratch as T
    return {"scratch": T.SHARED, "harvest": harvest.HOME, "reports": ROOT / "training" / "reports"}


def _files():
    """(name in the state, path here) of everything that lives."""
    h = _homes()
    s = h["scratch"]
    out = [(f"scratch/{n}", s / n) for n in TOP if (s / n).exists()]
    for folder in [s / "body"] + sorted(p for p in (s / "bodies").glob("*") if p.is_dir()):
        out += [(f"scratch/{p.relative_to(s).as_posix()}", p) for p in sorted(folder.rglob("*"))
                if p.is_file() and not p.name.endswith(LEFT)]
    out += [(f"harvest/{p.name}", p) for p in sorted(h["harvest"].glob("*")) if p.is_file() and p.suffix in (".txt", ".json")]
    out += [(f"reports/{p.name}", p) for p in sorted(h["reports"].glob("*.json")) if re.fullmatch(r"body(_\w+)?\.json|hive_of_bodies\.json", p.name)]
    return out


def manifest(files=None):
    """The hive in a few numbers: how many bodies and living cells, how much text, how it last measured."""
    files = _files() if files is None else files
    names = [n for n, _ in files]
    h = _homes()
    try:
        last = json.loads((h["reports"] / "hive_of_bodies.json").read_text())
    except (OSError, ValueError):
        last = {}
    if isinstance(last, list):  # the report keeps every measurement; the last one counts
        last = last[-1] if last else {}
    return {"when": time.strftime("%Y-%m-%d %H:%M"),
            "bodies": len({n.split("/")[2] for n in names if n.startswith("scratch/bodies/")}) + any(n.startswith("scratch/body/") or n == "scratch/base.pt" for n in names),
            "cells": sum(bool(re.search(r"/cell_\d+\.pt$", n)) for n in names),
            "harvest_mb": round(sum(p.stat().st_size for n, p in files if n.startswith("harvest/") and n.endswith(".txt")) / 1e6, 1),
            "each": last.get("bodies"), "as_one": last.get("as_one"), "measured": last.get("when"),
            "yardstick": (last.get("yardstick") or {}).get("as_one", last.get("as_one"))}


def pack(out):
    files = _files()
    m = manifest(files)
    with tarfile.open(out, "w:gz", compresslevel=6) as tar:
        blob = json.dumps(m, indent=1).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size, info.mtime = len(blob), int(time.time())
        tar.addfile(info, io.BytesIO(blob))
        for name, path in files:
            tar.add(path, arcname=name, recursive=False)
    return m


def _manifest_of(path):
    with tarfile.open(path) as tar:
        for member in tar:
            if member.name == "manifest.json":
                return json.loads(tar.extractfile(member).read())
    raise ValueError("not a hive state: it has no manifest")


def unpack(path):
    """Every file of the state goes to its place here. A name that is not one of the hive's own places is refused."""
    h = _homes()
    n = 0
    with tarfile.open(path) as tar:
        for member in tar:
            if member.isdir() or "/" not in member.name:  # folders, the manifest, a note beside it
                continue
            top, _, rest = member.name.partition("/")
            parts = Path(rest).parts
            if top not in h or not member.isfile() or not parts or ".." in parts or Path(rest).is_absolute():
                raise ValueError(f"refused: {member.name!r} is not a file of the hive")
            dest = h[top] / rest
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".part")
            with open(tmp, "wb") as f:
                f.write(tar.extractfile(member).read())
            tmp.replace(dest)
            n += 1
    return n


def _repo():
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, capture_output=True, text=True).stdout
        m = re.search(r"github\.com[:/]+([\w.-]+/[\w.-]+?)(\.git)?\s*$", url)
        return m.group(1) if m else REPO
    except OSError:
        return REPO


def fetch(to, log=print):
    """The grown hive, from where it grows; else the seed it started from. Returns where it came from, or None."""
    url = f"https://github.com/{_repo()}/releases/download/{RELEASE}/{NAME}"
    try:
        with urllib.request.urlopen(url, timeout=60) as r, open(to, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        return url
    except OSError as e:
        log(f"[hive] no grown hive at {url} ({type(e).__name__}); trying the seed", flush=True)
    got = subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", SEED], cwd=ROOT, capture_output=True, text=True)
    if got.returncode:
        log(f"[hive] no seed either (branch {SEED!r}): {got.stderr.strip()[:120]}", flush=True)
        return None
    with open(to, "wb") as f:  # the seed is kept as plain files (no one file over the size a repository takes)
        subprocess.run(["git", "archive", "--format=tar", "FETCH_HEAD"], cwd=ROOT, stdout=f, check=True)
    return f"the branch {SEED}"


def pull(path=None, force=False, log=print):
    """Bring the hive here. Returns what was done, in one line."""
    with tempfile.TemporaryDirectory() as tmp:
        where = path
        if path is None:
            path = Path(tmp) / NAME
            where = fetch(path, log)
            if where is None:
                return "no hive to bring: this one starts from what is here"
        theirs, mine = _manifest_of(path), manifest()
        if not force and mine["cells"] >= theirs["cells"]:
            return (f"left as it is: the hive here has {mine['cells']} living cells, the one from {where} has "
                    f"{theirs['cells']} (use --force to take it anyway)")
        n = unpack(path)
        return (f"the hive from {where} is here: {theirs['bodies']} bodies, {theirs['cells']} living cells, "
                f"{theirs['harvest_mb']} MB of text, as one {theirs['as_one']} ({n} files)")


def notes(m):
    each = ", ".join(f"{k} {v}" for k, v in (m.get("each") or {}).items())
    return (f"The hive as it is now ({m['when']} UTC): **{m['bodies']} bodies, {m['cells']} living cells**, "
            f"{m['harvest_mb']} MB of harvested text.\n\n"
            f"Loss on passages nobody trained on (lower is better), measured {m.get('measured')}: "
            f"each body alone: {each or 'not measured yet'}; all as one: {m.get('as_one')} (on text spread over all it has "
            f"harvested, which grows and changes). **On the yardstick, the same passages every time: {m.get('yardstick')}**.\n\n"
            f"Bring it to your device: `python training/hive_state.py pull`\n")


def log_growth():
    m = manifest()
    GROWTH.parent.mkdir(parents=True, exist_ok=True)
    with open(GROWTH, "a") as f:
        f.write(json.dumps(m) + "\n")
    return m


def seed(folder):
    """The state as plain files in a folder: what the seed branch holds."""
    folder = Path(folder)
    files = _files()
    for name, path in files:
        dest = folder / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
    m = manifest(files)
    (folder / "manifest.json").write_text(json.dumps(m, indent=1))
    return m


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "pack":
        print(notes(pack(argv[1] if len(argv) > 1 else NAME)))
    elif cmd == "pull":
        rest = [a for a in argv[1:] if a != "--force"]
        print(pull(rest[0] if rest else None, force="--force" in argv))
    elif cmd == "seed":
        print(notes(seed(argv[1])))
    elif cmd == "log":
        print(json.dumps(log_growth()))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
