"""The hive harvests its own reading matter: plain text for the models it trains from nothing (training/scratch.py).

    python -m team harvest [--mb 20]

A model trained from scratch knows no words until it has read some. Nobody hands the hive a corpus; it collects one:
- its own work: every instruction, task, page excerpt and reply in its logged calls (runs/**/calls.jsonl) and its
  recorded decisions (memory/decisions). This is the text its cells will read on the job.
- general English it fetches itself: open text datasets on Hugging Face (SOURCES; ungated, licence checked each
  time, --mb megabytes of each), and the opening paragraphs of random Wikipedia articles from the public API (a slow
  trickle: the API allows about two requests a minute).
Lines are kept once. The harvest lives in memory/harvest/ (not in git: each machine harvests its own); what was
gathered is recorded in memory/harvest/record.json. A later run adds to it.
"""
import hashlib
import json
import re
import sys
import time

from . import config, memory

HOME = memory.HOME / "harvest"
WIKI = "https://en.wikipedia.org/w/api.php"
_WS = re.compile(r"[ \t\r\f\v]+")


def _lines(text):
    for ln in str(text).splitlines():
        ln = _WS.sub(" ", ln).strip()
        if 30 <= len(ln) <= 2000 and sum(c.isalpha() for c in ln) > len(ln) * 0.5:
            yield ln


class _Shelf:
    """One text file of the harvest: lines appended once (by hash), its size known."""

    def __init__(self, name):
        HOME.mkdir(parents=True, exist_ok=True)
        self.path = HOME / f"{name}.txt"
        self.seen = set()
        if self.path.exists():
            with open(self.path, encoding="utf-8", errors="replace") as f:
                self.seen = {hashlib.md5(ln.strip().encode()).digest()[:8] for ln in f}
        self.f = open(self.path, "a", encoding="utf-8")
        self.added = 0

    def add(self, text):
        for ln in _lines(text):
            h = hashlib.md5(ln.encode()).digest()[:8]
            if h not in self.seen:
                self.seen.add(h)
                self.f.write(ln + "\n")
                self.added += len(ln) + 1

    def size(self):
        self.f.flush()
        return self.path.stat().st_size


def own_work(log=print):
    """Text from the hive's own logged calls and decisions."""
    shelf = _Shelf("own_work")
    files = sorted((config.ROOT / "runs").rglob("calls.jsonl")) + sorted((memory.HOME / "decisions").glob("*.jsonl"))
    for f in files:
        for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                c = json.loads(ln)
            except ValueError:
                continue
            for m in c.get("messages") or []:
                shelf.add(m.get("content", ""))
            for k in ("output", "text"):
                if isinstance(c.get(k), str):
                    shelf.add(c[k])
    log(f"[harvest] own work: {shelf.added / 1e6:.2f} MB new, {shelf.size() / 1e6:.2f} MB in all, from {len(files)} logs", flush=True)
    return shelf.size()


def wikipedia(mb, log=print, pause=20.0, minutes=10):
    """Opening paragraphs of random Wikipedia articles: a slow trickle (the API allows about two requests a minute),
    for at most `minutes` a run or until the shelf holds mb megabytes."""
    from .tools import web
    shelf, failed = _Shelf("wikipedia"), 0
    params = {"action": "query", "format": "json", "generator": "random", "grnnamespace": 0, "grnlimit": 20,
              "prop": "extracts", "exintro": 1, "explaintext": 1, "exlimit": 20}
    until = time.time() + minutes * 60
    while shelf.size() < mb * 1e6 and failed < 5 and time.time() < until:
        try:
            r = web._S.get(WIKI, params=params, timeout=config.HTTP_TIMEOUT)
            if r.status_code == 429:  # the API says how long to wait; it allows about two such requests a minute
                time.sleep(min(120, int(r.headers.get("retry-after") or 60)) + 1)
                continue
            pages = (r.json().get("query") or {}).get("pages") or {}
            failed = 0
        except Exception as e:  # noqa: BLE001 - a failed request is waited out, five in a row end the harvest
            failed += 1
            log(f"[harvest] wikipedia: {type(e).__name__}; waiting", flush=True)
            time.sleep(10 * failed)
            continue
        for p in pages.values():
            shelf.add(p.get("extract", ""))
        if int(shelf.size() / 1e6) != int((shelf.size() - 40_000) / 1e6):
            log(f"[harvest] wikipedia: {shelf.size() / 1e6:.1f} of {mb} MB", flush=True)
        time.sleep(pause)
    log(f"[harvest] wikipedia: {shelf.added / 1e6:.2f} MB new, {shelf.size() / 1e6:.2f} MB in all", flush=True)
    return shelf.size()


OPEN = {"cc-by-sa-3.0", "cc-by-sa-4.0", "cc-by-4.0", "cc0-1.0", "apache-2.0", "mit", "cdla-sharing-1.0",
        "cdla-permissive-2.0", "gfdl"}
# open text the hive may read, in the order it tries them: (dataset on Hugging Face, file, the text column for parquet)
SOURCES = [("wikimedia/wikipedia", "20231101.simple/train-00000-of-00001.parquet", "text"),
           ("roneneldan/TinyStories", "TinyStoriesV2-GPT4-valid.txt", None)]


def dataset(repo, file, column, mb, log=print):
    """Up to mb megabytes of lines from one file of an open dataset: ungated (no login, no token) and under a licence
    in OPEN, checked here each time. A parquet file needs pyarrow; without it the source is skipped, not installed."""
    from huggingface_hub import HfApi, hf_hub_download
    info = HfApi(token=False).dataset_info(repo)
    lic = {t.split(":", 1)[1] for t in info.tags or [] if t.startswith("license:")}
    if info.gated or not lic or not lic <= OPEN:
        log(f"[harvest] {repo}: not taken (gated: {bool(info.gated)}, licence: {sorted(lic) or 'none stated'})", flush=True)
        return 0
    shelf = _Shelf(re.sub(r"[^a-z0-9]+", "_", repo.lower()))
    if shelf.size() >= mb * 1e6:
        return shelf.size()
    if file.endswith(".parquet"):
        try:
            import pyarrow.parquet as pq
        except ImportError:
            log(f"[harvest] {repo}: a parquet file, and pyarrow is not installed here: skipped", flush=True)
            return 0
        path = hf_hub_download(repo, file, repo_type="dataset", token=False)
        for batch in pq.ParquetFile(path).iter_batches(batch_size=500, columns=[column]):
            for text in batch.column(0).to_pylist():
                shelf.add(text or "")
            if shelf.size() >= mb * 1e6:
                break
    else:
        path = hf_hub_download(repo, file, repo_type="dataset", token=False)
        with open(path, encoding="utf-8", errors="replace") as f:
            for ln in f:
                shelf.add(ln)
                if shelf.added >= mb * 1e6:
                    break
    log(f"[harvest] {repo}: {shelf.added / 1e6:.2f} MB new, {shelf.size() / 1e6:.2f} MB in all", flush=True)
    return shelf.size()


def files():
    return sorted(HOME.glob("*.txt"))


def main(argv):
    mb = float(argv[argv.index("--mb") + 1]) if "--mb" in argv else 20.0
    rec = {"when": time.strftime("%Y-%m-%d %H:%M"), "own_work_bytes": own_work()}
    for repo, file, column in SOURCES:
        try:
            rec[repo] = dataset(repo, file, column, mb)
        except Exception as e:  # noqa: BLE001 - one source failing does not end the harvest
            rec[repo] = f"failed: {type(e).__name__}: {str(e)[:120]}"
    rec["wikipedia_api_bytes"] = wikipedia(mb, minutes=0 if "--no-trickle" in argv else 10)
    (HOME / "record.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
