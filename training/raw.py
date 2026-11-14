"""Raw text and code from the open web, drawn at random, for the cells to read.

A cell cannot learn the world from raw text at a CPU's pace: a runner trains a few million pieces a day, and the
DNA was made from trillions. So the hive reads the way a person with little time does: it takes random pieces from
huge open collections, measures how well it already predicts each one (its own error), and studies only those in
the middle, which it does not know yet but can learn. The easiest are already known; the hardest are mostly noise,
other scripts or broken text. What it reads therefore shifts by itself as the body learns (training/grow.py,
`--read N`). Each cell reads mostly from the sources nearest its organ.

Sources (open, ungated, licences that allow it): FineWeb-Edu (educational web pages, ODC-BY), Wikipedia in English
(CC BY-SA), and GitHub code under permissive licences (codeparrot/github-code-clean, Apache-2.0 for the set). Only
one row group of one Parquet file is read per draw, over HTTP, never a whole file.
"""
import random

SOURCES = {
    "web": ("HuggingFaceFW/fineweb-edu", "data/", "text"),
    "wiki": ("wikimedia/wikipedia", "20231101.en/", "text"),
    "code": ("codeparrot/github-code-clean", "data/", "code"),
}
# which sources each organ reads, in proportion
BY_ORGAN = {"code": {"code": 3, "web": 1}, "data": {"code": 2, "web": 1, "wiki": 1}, "sources": {"web": 2, "wiki": 2},
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
