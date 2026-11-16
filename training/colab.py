"""A GPU that trains the hive's children: the owner's Colab notebook (colab/hive_gpu.ipynb), reached through the release.

    python training/colab.py serve [--hours 12]          in the notebook: say it is there, and train every child ordered
    python training/colab.py order --gen G --name N ...  in a train job: order the child from the notebook, if it is there
    python training/colab.py wait --gen G --name N --minutes 90 --out DIR
                                                          in a train job: the cell the notebook grew, or exit 1

Why: a child of the 8B trains on a free runner's CPU for close to three hours (9 to 18 s a row); on a Colab GPU (an L4
or an A100) the same rows take minutes. The notebook is the owner's, on the compute he already has; nothing is bought.

How the two meet, with nothing but the release `hive-grown` between them (no server, nothing to keep running):
  colab-alive.json             the notebook writes it every few minutes: when, and which GPU
  colab-order-G-N.json         a train job, when the notebook said it was there in the last ALIVE seconds: what to grow
  colab-rows-G-N.jsonl         the rows the child is grown from (the job's own got/rows.jsonl)
  colab-taken-G-N.json         the notebook, as it starts on an order (two notebooks never grow the same child)
  colab-done-G-N.tar.gz        the notebook: the cell, as the train job would have made it (gguf, json, safetensors)
  colab-failed-G-N.txt         the notebook: why it could not; the train job then trains on its CPU at once
The train job waits at most `--minutes`; with no answer it trains on its CPU as always, so a closed notebook costs a
generation nothing but the wait. The train job removes the order's files when it has what it waited for.

The notebook needs a token that may write this repository's releases (a fine-grained token for this repository only,
"Contents: read and write"), kept in Colab's secrets as HIVE_GITHUB_TOKEN; it is never printed or written to a file.
"""
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = os.environ.get("GITHUB_REPOSITORY", "Arnav123-s/HiveMIND")
TAG = "hive-grown"
ALIVE = 900  # seconds: a notebook that has not said it is there for this long is taken to be gone
API = "https://api.github.com"


def _token():
    return os.environ.get("HIVE_GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def _session():
    import requests
    s = requests.Session()
    s.headers.update({"Accept": "application/vnd.github+json", "User-Agent": "hive-colab/1.0"})
    if _token():
        s.headers["Authorization"] = f"Bearer {_token()}"
    return s


def release(s=None):
    """The release's id, upload address and assets {name: asset}."""
    s = s or _session()
    r = s.get(f"{API}/repos/{REPO}/releases/tags/{TAG}", timeout=30)
    r.raise_for_status()
    d = r.json()
    assets = {a["name"]: a for a in d.get("assets", [])}
    if len(assets) >= 100:  # the release lists 100 at a time; the hive keeps more than that
        page = 2
        while True:
            more = s.get(f"{API}/repos/{REPO}/releases/{d['id']}/assets", params={"per_page": 100, "page": page}, timeout=30).json()
            if not more:
                break
            assets.update({a["name"]: a for a in more})
            page += 1
    return d["id"], d["upload_url"].split("{")[0], assets


def put(name, data, s=None, kind="application/octet-stream"):
    """An asset of the release, replaced if it is there."""
    s = s or _session()
    rid, up, assets = release(s)
    if name in assets:
        s.delete(f"{API}/repos/{REPO}/releases/assets/{assets[name]['id']}", timeout=30)
    r = s.post(up, params={"name": name}, data=data, headers={"Content-Type": kind}, timeout=600)
    r.raise_for_status()


def drop(names, s=None):
    s = s or _session()
    _, _, assets = release(s)
    for n in names:
        if n in assets:
            s.delete(f"{API}/repos/{REPO}/releases/assets/{assets[n]['id']}", timeout=30)


def get(name, to, s=None):
    """An asset of the release saved to a file; False when it is not there."""
    s = s or _session()
    _, _, assets = release(s)
    if name not in assets:
        return False
    with s.get(assets[name]["url"], headers={"Accept": "application/octet-stream"}, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(to, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return True


def alive(s=None):
    """{"when", "gpu", "age"} of the notebook's last word, or None when it has said nothing."""
    s = s or _session()
    with tempfile.TemporaryDirectory() as tmp:
        if not get("colab-alive.json", Path(tmp) / "a.json", s):
            return None
        d = json.loads((Path(tmp) / "a.json").read_text())
    d["age"] = time.time() - float(d.get("when", 0))
    return d


def order(o, rows, s=None):
    """Order one child from the notebook when it said it was there within ALIVE seconds. True when ordered."""
    s = s or _session()
    a = alive(s)
    if not a or a["age"] > ALIVE:
        seen = "never seen" if not a else "last seen {:.0f} minutes ago".format(a["age"] / 60)
        print(f"colab: no notebook ({seen}): this runner trains the cell")
        return False
    key = f"{o['gen']}-{o['name']}"
    put(f"colab-rows-{key}.jsonl", Path(rows).read_bytes(), s)
    put(f"colab-order-{key}.json", json.dumps(o | {"ordered": time.time()}).encode(), s, "application/json")
    print(f"colab: the notebook ({a.get('gpu', '?')}, seen {a['age']:.0f} s ago) is growing {o['name']}")
    return True


def wait(gen, name, minutes, out, s=None):
    """The cell the notebook grew, unpacked into `out`: True; False when it failed or did not answer in time."""
    s = s or _session()
    key = f"{gen}-{name}"
    t0 = time.time()
    while time.time() - t0 < minutes * 60:
        _, _, assets = release(s)
        if f"colab-failed-{key}.txt" in assets:
            with tempfile.TemporaryDirectory() as tmp:
                get(f"colab-failed-{key}.txt", Path(tmp) / "f.txt", s)
                print("colab: the notebook could not grow it: " + (Path(tmp) / "f.txt").read_text()[-600:])
            break
        if f"colab-done-{key}.tar.gz" in assets:
            Path(out).mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory() as tmp:
                get(f"colab-done-{key}.tar.gz", Path(tmp) / "d.tgz", s)
                with tarfile.open(Path(tmp) / "d.tgz") as t:
                    t.extractall(out, filter="data")
            print(f"colab: {name} grown on the notebook's GPU in {(time.time() - t0) / 60:.0f} minutes")
            drop([f"colab-{w}-{key}{x}" for w, x in (("order", ".json"), ("rows", ".jsonl"), ("taken", ".json"), ("done", ".tar.gz"))], s)
            return True
        time.sleep(60)
    else:
        print(f"colab: no cell from the notebook in {minutes} minutes")
    drop([f"colab-{w}-{key}{x}" for w, x in (("order", ".json"), ("rows", ".jsonl"), ("taken", ".json"), ("failed", ".txt"))], s)
    return False


def grow(o, s=None, log=print):
    """In the notebook: one ordered child grown on the GPU, and sent back as colab-done (or colab-failed)."""
    s = s or _session()
    key = f"{o['gen']}-{o['name']}"
    work = Path(tempfile.mkdtemp(prefix="hive-colab-"))
    try:
        get(f"colab-rows-{key}.jsonl", work / "rows.jsonl", s)
        args = [sys.executable, "training/grow.py", "train", "--rows", str(work / "rows.jsonl"), "--name", o["name"], "--base", o["dna"],
                "--lean", o.get("organ", ""), "--gen", o["gen"], "--epochs", str(o.get("epochs", 2)), "--read", str(o.get("read", 0)),
                "--judged", str(o.get("judged", 0)), "--layers", "last14", "--no-checkpoint", "--minutes", str(o.get("minutes", 60))]
        for what in ("parent", "trunk"):
            asset = o.get(what) or ""
            if asset and get(asset, work / f"{what}.safetensors", s):
                args += [f"--{what}", str(work / f"{what}.safetensors")]
        if o.get("parent_cell"):
            args += ["--parent-cell", o["parent_cell"]]
        log(f"colab: growing {o['name']} ({o.get('organ', '')}) of {o['gen']}", flush=True)
        done = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
        (work / "train.log").write_text(done.stdout + done.stderr)
        if done.returncode:
            raise RuntimeError(f"training ended with {done.returncode}: {(done.stdout + done.stderr)[-1500:]}")
        name, dna = o["name"], o["dna"]
        files = {f"{dna}.{name}.gguf": ROOT / "cells" / "members" / f"{dna}+{name}.gguf",
                 f"{dna}.{name}.json": ROOT / "cells" / "members" / f"{dna}+{name}.json",
                 f"{dna}.{name}.safetensors": ROOT / "runs" / "grow" / f"{dna}+{name}" / "adapter_model.safetensors"}
        with tarfile.open(work / "done.tgz", "w:gz") as t:
            for arc, f in files.items():
                t.add(f, arcname=arc)
        put(f"colab-done-{key}.tar.gz", (work / "done.tgz").read_bytes(), s, "application/gzip")
        log(f"colab: {o['name']} sent back ({json.loads(files[f'{dna}.{name}.json'].read_text()).get('seconds')} s of training)", flush=True)
    except Exception as e:  # noqa: BLE001 - said to the train job, which then trains the cell itself
        put(f"colab-failed-{key}.txt", f"{type(e).__name__}: {e}"[-3000:].encode(), s, "text/plain")
        log(f"colab: {o['name']} could not be grown: {type(e).__name__}: {str(e)[-400:]}", flush=True)


def serve(hours=12, every=180, log=print):
    """In the notebook: say every few minutes that it is there, and grow each child ordered, until `hours` have
    passed with nothing ordered."""
    import torch
    if not torch.cuda.is_available():
        raise SystemExit("colab: no GPU in this runtime (Runtime, Change runtime type: an L4 or A100 GPU)")
    gpu = torch.cuda.get_device_name(0)
    mem = torch.cuda.get_device_properties(0).total_memory / 2**30
    if mem < 22:
        raise SystemExit(f"colab: this GPU ({gpu}, {mem:.0f} GB) cannot hold the 8B DNA in 16-bit numbers (16 GB) and train it: choose an L4 or A100")
    if not _token():
        raise SystemExit("colab: no token (Colab's secrets: HIVE_GITHUB_TOKEN, a token that may write this repository's releases)")
    s = _session()
    last = time.time()
    log(f"colab: ready on {gpu} ({mem:.0f} GB); the hive's train jobs will send their children here", flush=True)
    while time.time() - last < hours * 3600:
        put("colab-alive.json", json.dumps({"when": time.time(), "gpu": gpu}).encode(), s, "application/json")
        _, _, assets = release(s)
        for n in sorted(assets):
            if not (n.startswith("colab-order-") and n.endswith(".json")):
                continue
            key = n[len("colab-order-"):-len(".json")]
            if any(f"colab-{w}-{key}{x}" in assets for w, x in (("taken", ".json"), ("done", ".tar.gz"), ("failed", ".txt"))):
                continue
            with tempfile.TemporaryDirectory() as tmp:
                get(n, Path(tmp) / "o.json", s)
                o = json.loads((Path(tmp) / "o.json").read_text())
            put(f"colab-taken-{key}.json", json.dumps({"when": time.time(), "gpu": gpu}).encode(), s, "application/json")
            grow(o, s, log)
            last = time.time()
            put("colab-alive.json", json.dumps({"when": time.time(), "gpu": gpu}).encode(), s, "application/json")
        time.sleep(every)
    log(f"colab: nothing ordered for {hours} hours; stopping", flush=True)


def main(argv):
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else d  # noqa: E731
    cmd = argv[0] if argv else ""
    if cmd == "serve":
        serve(float(opt("--hours", 12)))
        return 0
    if cmd == "order":
        o = {k: opt(f"--{k.replace('_', '-')}", "") for k in ("gen", "name", "organ", "dna", "parent", "parent_cell", "trunk")}
        o |= {"epochs": float(opt("--epochs", 2)), "read": int(opt("--read", 0)), "judged": int(opt("--judged", 0)), "minutes": int(opt("--minutes", 60))}
        try:
            return 0 if order(o, opt("--rows")) else 1
        except Exception as e:  # noqa: BLE001 - the release not reachable: the runner trains the cell
            print(f"colab: could not order ({type(e).__name__}: {e}); this runner trains the cell")
            return 1
    if cmd == "wait":
        try:
            return 0 if wait(opt("--gen"), opt("--name"), float(opt("--minutes", 90)), opt("--out", "colab_out")) else 1
        except Exception as e:  # noqa: BLE001
            print(f"colab: could not wait ({type(e).__name__}: {e}); this runner trains the cell")
            return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
