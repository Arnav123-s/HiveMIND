"""The hive harvests its own reading matter: plain text for the models it trains from nothing (training/scratch.py).

    python -m team harvest [--mb 20]

A model trained from scratch knows no words until it has read some. Nobody hands the hive a corpus; it collects one:
- its own work: every instruction, task, page excerpt and reply in its logged calls (runs/**/calls.jsonl) and its
  recorded decisions (memory/decisions). This is the text its cells will read on the job.
- general English it fetches itself: open text datasets on Hugging Face (SOURCES; ungated, licence checked each
  time, --mb megabytes of each), and the opening paragraphs of random Wikipedia articles from the public API (a slow
  trickle: the API allows about two requests a minute).
- new sources it finds itself: on every harvest one scout looks on Hugging Face for a text dataset it has not seen,
  and lets it in only if it is open, small enough, and reads like running text (scout, readable). --no-scout: not now.
- dreams: the hive's own small member writes practice passages on the kind of text its body reads worst, harder
  after every forty (dream). --no-dream: not now.
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


# ---- scouts: the hive finds new reading matter itself --------------------------------------------------------------
SEEK = ["simple english", "stories", "encyclopedia", "news articles", "questions and answers", "instructions how to",
        "python code", "dialogue", "science explained", "books", "summaries", "definitions"]
MAX_SOURCE, DISK_FLOOR = 300e6, 4e9


def _record(**new):
    f = HOME / "record.json"
    try:
        rec = json.loads(f.read_text())
    except (OSError, ValueError):
        rec = {}
    rec.update(new)
    HOME.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rec, indent=1))
    return rec


def sources():
    """Where the harvest reads: the first sources, and every one a scout found and the check let in."""
    return SOURCES + [tuple(x) for x in _record().get("found", [])]


def pick_file(siblings):
    """The file of a dataset to read: plain text first, else a parquet file of its training part; the smallest that
    is not tiny, and never over MAX_SOURCE. siblings: [(name, bytes)]."""
    ok = [(n, b) for n, b in siblings if b and 1e6 <= b <= MAX_SOURCE]
    txt = sorted((b, n) for n, b in ok if n.endswith(".txt"))
    par = sorted((("train" not in n.lower()), b, n) for n, b in ok if n.endswith(".parquet"))  # its training part first
    return txt[0][1] if txt else par[0][2] if par else None


def readable(lines):
    """The check a new source must pass before it is let in (the body's guard against bad food), on a sample of its
    lines: (True, "") or (False, why). It must be running text in the alphabet the hive reads, in sentences, and not
    one line repeated."""
    kept = [ln for raw in lines for ln in _lines(raw)]
    if len(kept) < 50 or len(kept) < 0.2 * max(1, len(lines)):
        return False, f"only {len(kept)} of {len(lines)} sampled lines are running text"
    text = " ".join(kept)
    latin = sum(c.isascii() and c.isalpha() for c in text) / max(1, sum(c.isalpha() for c in text))
    if latin < 0.9:
        return False, f"only {latin:.0%} of its letters are in the alphabet the hive reads"
    words = text.split()
    # different words among the first 2000 (a count over the whole sample falls with its length: a megabyte of simple
    # stories was turned away as repeating itself)
    if len(set(words[:2000])) < 0.15 * len(words[:2000]) or len(set(kept)) < 0.8 * len(kept):
        return False, "it repeats itself"
    if sum(len(w) for w in words) / len(words) > 9 or not any(ln.rstrip()[-1:] in ".!?\"'" for ln in kept[:200]):
        return False, "it does not read like sentences"
    return True, ""


def _sample(repo, file, mb=1.0):
    """(lines, text column) from the start of a file: up to mb megabytes."""
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(repo, file, repo_type="dataset", token=False)
    out, size = [], 0
    if file.endswith(".parquet"):
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(path)
        first = next(pf.iter_batches(batch_size=200))
        cols = {n: [v for v in first.column(i).to_pylist() if isinstance(v, str)] for i, n in enumerate(first.schema.names)}
        cols = {n: v for n, v in cols.items() if len(v) > 100}
        if not cols:
            return [], None
        column = max(cols, key=lambda n: sum(map(len, cols[n])) / len(cols[n]))  # the column with the longest text
        for batch in pf.iter_batches(batch_size=500, columns=[column]):
            for t in batch.column(0).to_pylist():
                out += str(t or "").splitlines()
                size += len(t or "")
            if size >= mb * 1e6:
                break
        return out, column
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            out.append(ln)
            size += len(ln)
            if size >= mb * 1e6:
                break
    return out, None


def scout(log=print, tries=8):
    """One scouting trip: look on Hugging Face for a text dataset the hive has not looked at (one search word a trip,
    in turn), and let in the first one that is open (ungated, licence in OPEN), has a file it can read, leaves the
    disk its floor, and passes `readable`. Every dataset looked at is recorded with the verdict, so none is looked at
    twice. Returns the source let in, or None."""
    import shutil
    from huggingface_hub import HfApi
    api, rec = HfApi(token=False), _record()
    seen, trips = rec.get("scouted", {}), rec.get("scout_trips", 0)
    have = {r for r, _, _ in sources()}
    term, found, looked = SEEK[trips % len(SEEK)], None, 0
    for d in api.list_datasets(search=term, sort="downloads", limit=tries * 3):
        if d.id in seen or d.id in have:
            continue
        if looked >= tries:  # a trip looks at so many and comes home
            break
        looked += 1
        try:
            info = api.dataset_info(d.id, files_metadata=True)
            lic = {t.split(":", 1)[1] for t in info.tags or [] if t.startswith("license:")}
            file = pick_file([(x.rfilename, x.size) for x in info.siblings or []])
            if info.gated or not lic or not lic <= OPEN:
                verdict = f"not open (gated: {bool(info.gated)}, licence: {sorted(lic) or 'none stated'})"
            elif not file:
                verdict = "no text or parquet file of a size it can read"
            elif file.endswith(".parquet") and not __import__("importlib").util.find_spec("pyarrow"):
                verdict = "a parquet file, and pyarrow is not installed here"
            elif shutil.disk_usage(HOME).free - dict((x.rfilename, x.size) for x in info.siblings)[file] < DISK_FLOOR:
                verdict = "the disk would get too full"
            else:
                lines, column = _sample(d.id, file)
                ok, why = readable(lines)
                verdict = "let in" if ok else f"not let in: {why}"
                if ok:
                    found = (d.id, file, column)
        except Exception as e:  # noqa: BLE001 - a dataset that cannot be read is one more verdict
            verdict = f"could not be read: {type(e).__name__}"
        seen[d.id] = f"{term}: {verdict}"
        log(f"[harvest] scout ({term}): {d.id}: {verdict}", flush=True)
        if found:
            break
    _record(scouted=seen, scout_trips=trips + 1, found=rec.get("found", []) + ([list(found)] if found else []))
    return found


# ---- dreams: the hive writes its own practice text, aimed at what its body reads worst --------------------------------
DREAMER = """You write practice reading for a very small language model that is learning to read. You are shown a \
passage it found hard. Write ONE new passage on the same kind of subject, in plain running sentences: no title, no \
list, no questions to the reader. About 120 words."""
LEVELS = ["Use short sentences and common words, as for a child.",
          "Explain one thing clearly, in a few connected sentences.",
          "Explain it and give the reason for it and one example.",
          "Work through a small problem step by step, each step following from the one before.",
          "Compare two things, say how they differ and why, and end with a conclusion."]
PER_LEVEL = 40


def dream(n=12, log=print):
    """The hive's own small member writes n practice passages on the kind of text its body reads worst (the passage
    the body's last turn recorded: training/reports/body.json, "weakest"). The dreams get harder: after every
    PER_LEVEL of them the next level of LEVELS is asked for. Each dream passes the same line filter as all harvested
    text and goes to the shelf "dreams"; in the body it lies in no territory yet, so the scouts find it.
    A dream is as good as the member that writes it: this gives text aimed at a weakness, not a great amount of it."""
    from . import llm
    try:
        hard = json.loads((config.ROOT / "training" / "reports" / "body.json").read_text())["weakest"]["text"]
    except (OSError, ValueError, KeyError):
        return 0
    rec, shelf = _record(), _Shelf("dreams")
    done = rec.get("dreams", 0)
    for i in range(n):
        level = min(len(LEVELS) - 1, (done + i) // PER_LEVEL)
        text = llm.chat("lesson_writer", [{"role": "system", "content": DREAMER},
                                          {"role": "user", "content": f"The passage it found hard:\n{hard[:900]}\n\n{LEVELS[level]}"}],
                        max_new_tokens=220, temperature=0.8)
        shelf.add(text)
    _record(dreams=done + n, dream_level=min(len(LEVELS), (done + n) // PER_LEVEL + 1), dreams_bytes=shelf.size())
    log(f"[harvest] dreams: {n} written at level {min(len(LEVELS), (done + n - 1) // PER_LEVEL + 1)} of {len(LEVELS)}, "
        f"{shelf.added / 1e3:.1f} kB kept, {shelf.size() / 1e3:.1f} kB of dreams in all", flush=True)
    return shelf.added


def files():
    return sorted(HOME.glob("*.txt"))


def main(argv):
    mb = float(argv[argv.index("--mb") + 1]) if "--mb" in argv else 20.0
    if "--more" in argv:  # each run the shelves may hold so much more than the fullest one does now: the harvest grows
        mb = max([mb] + [p.stat().st_size / 1e6 + float(argv[argv.index("--more") + 1]) for p in files()])
    rec = {"when": time.strftime("%Y-%m-%d %H:%M"), "own_work_bytes": own_work()}
    if "--no-scout" not in argv:
        try:
            scout()
        except Exception as e:  # noqa: BLE001 - a failed trip is not a failed harvest
            print(f"[harvest] scout: {type(e).__name__}: {str(e)[:120]}", flush=True)
    for repo, file, column in sources():
        try:
            rec[repo] = dataset(repo, file, column, mb)
        except Exception as e:  # noqa: BLE001 - one source failing does not end the harvest
            rec[repo] = f"failed: {type(e).__name__}: {str(e)[:120]}"
    rec["wikipedia_api_bytes"] = wikipedia(mb, minutes=0 if "--no-trickle" in argv else 10)
    if "--no-dream" not in argv:
        try:
            dream()
        except Exception as e:  # noqa: BLE001 - no member to dream with (models not downloaded yet) is not a failed harvest
            print(f"[harvest] dreams: none this time ({type(e).__name__}: {str(e)[:100]})", flush=True)
    _record(**rec)
    print(json.dumps(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
