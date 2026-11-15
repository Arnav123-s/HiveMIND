"""Raw text and code from the open web, drawn at random, for the cells to read.

A cell cannot learn the world from raw text at a CPU's pace: a runner trains a few million pieces a day, and the
DNA was made from trillions. So the hive reads the way a person with little time does: it takes random pieces from
huge open collections, measures how well it already predicts each one (its own error), and studies only those in
the middle, which it does not know yet but can learn. The easiest are already known; the hardest are mostly noise,
other scripts or broken text. What it reads therefore shifts by itself as the body learns (training/grow.py,
`--read N`). Each cell reads mostly from the sources nearest its organ.

People's corrections are raw data too, and they teach what plain text does not: how a mistake looks and how it
is spotted. Two kinds are drawn. Commits that changed code, with the author's words for what was wrong
(bigcode/commitpackft, permissively licensed code, MIT for the set), read as a diff (`--read`, source "fix"). And
questions with answers that many people voted on (HuggingFaceH4/stack-exchange-preferences, CC BY-SA 4.0): the
best-voted answer set beside the worst-voted one is a right-against-wrong pair judged by people, trained the way
the hive's own pairs are, with DPO (`--judged N`). Only the text of questions, answers and code is used, never
the names or profiles of the people who wrote them.

Sources (open, ungated, licences that allow it): FineWeb-Edu (educational web pages, ODC-BY), Wikipedia in English
(CC BY-SA), and GitHub code under permissive licences (codeparrot/github-code-clean, Apache-2.0 for the set). Only
one row group of one Parquet file is read per draw, over HTTP, never a whole file.
"""
import random

SOURCES = {
    "web": ("HuggingFaceFW/fineweb-edu", "data/", "text"),
    "wiki": ("wikimedia/wikipedia", "20231101.en/", "text"),
    "code": ("codeparrot/github-code-clean", "data/", "code"),
    "fix": ("bigcode/commitpackft", "data/python/data.jsonl", None),
}
# which sources each organ reads, in proportion
BY_ORGAN = {"code": {"code": 2, "fix": 2, "web": 1}, "data": {"code": 1, "fix": 1, "web": 1, "wiki": 1}, "sources": {"web": 2, "wiki": 2},
            "words": {"wiki": 2, "web": 2}, "": {"web": 1, "wiki": 1, "code": 1}}
CHUNK = 1600  # characters: about 400 pieces of text


def _files(repo, prefix):
    from huggingface_hub import HfApi
    return sorted(f for f in HfApi().list_repo_files(repo, repo_type="dataset") if f.startswith(prefix) and f.endswith(".parquet"))


def draw(n, seed, organ="", log=print):
    """n raw chunks [{"type": "read", "text", "source"}], drawn by the seed (the same seed, the same chunks while the
    collections stay the same). A source that cannot be reached is passed over and said."""
    import pyarrow.parquet as pq
    from huggingface_hub import HfFileSystem
    r = random.Random(f"raw:{seed}:{organ}")
    weights = BY_ORGAN.get(organ, BY_ORGAN[""])
    fs, files, out = HfFileSystem(), {}, []
    tries = 0
    while len(out) < n and tries < 4 * n + 8:
        tries += 1
        src = r.choices(list(weights), weights=list(weights.values()))[0]
        repo, prefix, col = SOURCES[src]
        if src == "fix":
            got = _fix(fs, repo, prefix, r, log)
            if got:
                out.append({"type": "read", "text": got, "source": src})
            continue
        try:
            if src not in files:
                files[src] = _files(repo, prefix)
            f = r.choice(files[src])
            pf = pq.ParquetFile(fs.open(f"datasets/{repo}/{f}", "rb"))
            g = r.randrange(pf.num_row_groups)
            texts = pf.read_row_group(g, columns=[col]).column(col).to_pylist()
        except Exception as e:  # noqa: BLE001 - a busy or moved collection: drawn from another
            log(f"raw: {src} not read ({type(e).__name__}: {str(e)[:120]})", flush=True)
            continue
        for t in r.sample(texts, min(len(texts), 8)):
            if not isinstance(t, str) or len(t) < 400:
                continue
            start = r.randrange(max(1, len(t) - CHUNK))
            out.append({"type": "read", "text": t[start:start + CHUNK], "source": src})
            if len(out) >= n:
                break
    return out


def pick(scored, keep):
    """Of [(loss, row)], the ones in the middle: the easiest 30% are known already and the hardest 10% are mostly
    noise. Up to `keep` of the rest, the hardest of them first (the most to learn that can be learned)."""
    s = sorted(scored, key=lambda x: x[0])
    lo, hi = int(len(s) * 0.3), max(int(len(s) * 0.3) + 1, int(len(s) * 0.9))
    band = s[lo:hi]
    return [row for _, row in sorted(band, key=lambda x: -x[0])[:keep]]


def _fix(fs, repo, path, r, log=print):
    """One commit drawn at random from a JSON-lines file (a random place in the file, the next whole line), as its
    message and the diff it made; None when it is too big or is no change."""
    import difflib
    import json
    try:
        size = fs.info(f"datasets/{repo}/{path}")["size"]
        with fs.open(f"datasets/{repo}/{path}", "rb") as f:
            f.seek(r.randrange(max(1, size - 200_000)))
            f.readline()
            d = json.loads(f.readline())
    except Exception as e:  # noqa: BLE001
        log(f"raw: fix not read ({type(e).__name__}: {str(e)[:120]})", flush=True)
        return None
    old, new = d.get("old_contents") or "", d.get("new_contents") or ""
    if old == new or len(old) + len(new) > 60_000:
        return None
    diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), d.get("old_file", "a"), d.get("new_file", "b"), n=3))
    if not diff or len(diff) > 2 * CHUNK:
        return None
    return f"A change to {d.get('new_file', 'a file')}. What it fixes, in its author's words: {d.get('subject', '').strip()}\n\n{diff}"


SITES = {"code": ["Stackoverflow.com"], "data": ["Stackoverflow.com", "datascience.stackexchange.com"],
         "words": ["english.stackexchange.com", "writing.stackexchange.com"], "sources": ["superuser.com", "webapps.stackexchange.com"],
         "": ["Stackoverflow.com"]}
SE = "HuggingFaceH4/stack-exchange-preferences"


def _text(html):
    import html as H
    import re
    t = re.sub(r"<pre[^>]*>(.*?)</pre>", lambda m: "\n```\n" + m.group(1) + "\n```\n", html or "", flags=re.S)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\n{3,}", "\n\n", H.unescape(t)).strip()


def judged(n, seed, organ="", log=print):
    """n pairs judged by people: a question, its best-voted answer and its worst-voted one (at least 3 votes apart),
    as rows {"type": "judged", "messages", "output", "rejected"} that train like the hive's own pairs."""
    import pyarrow.parquet as pq
    from huggingface_hub import HfApi, HfFileSystem
    r = random.Random(f"judged:{seed}:{organ}")
    fs, out, tries = HfFileSystem(), [], 0
    files = {}
    while len(out) < n and tries < n + 8:
        tries += 1
        site = r.choice(SITES.get(organ, SITES[""]))
        try:
            if site not in files:
                files[site] = sorted(f for f in HfApi().list_repo_files(SE, repo_type="dataset") if f.startswith(f"data/{site}/") and f.endswith(".parquet"))
            pf = pq.ParquetFile(fs.open(f"datasets/{SE}/{r.choice(files[site])}", "rb"))
            rows = pf.read_row_group(r.randrange(pf.num_row_groups), columns=["question", "answers"]).to_pylist()
        except Exception as e:  # noqa: BLE001
            log(f"raw: judged answers from {site} not read ({type(e).__name__}: {str(e)[:120]})", flush=True)
            continue
        r.shuffle(rows)
        for row in rows:
            ans = [a for a in row.get("answers") or [] if isinstance(a, dict) and a.get("text")]
            if len(ans) < 2:
                continue
            best = max(ans, key=lambda a: (a.get("pm_score") or 0, bool(a.get("selected"))))
            worst = min(ans, key=lambda a: a.get("pm_score") or 0)
            if best is worst or (best.get("pm_score") or 0) - (worst.get("pm_score") or 0) < 3 or (best.get("pm_score") or 0) < 2:
                continue
            # short enough that the question twice and both answers fit one row's memory on a 16 GB machine (grow.train)
            q, good, bad = _text(row.get("question"))[:900], _text(best["text"])[:900], _text(worst["text"])[:900]
            if len(q) < 40 or len(good) < 40 or len(bad) < 20:
                continue
            out.append({"type": "judged", "source": site, "messages": [{"role": "user", "content": q}], "output": good, "rejected": bad})
            if len(out) >= n or sum(o["source"] == site for o in out) >= max(2, n // 4):
                break
    return out[:n]
