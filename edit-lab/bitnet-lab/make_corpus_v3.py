# Muse's work — built and run by Muse on Muse's side of the lab.
# Corpus v3 builder: openly-licensed English text only (Project Gutenberg public-domain
# books + WikiText-103, CC BY-SA 3.0 — see corpus-v3/SOURCES.md), downloaded into
# corpus-v3/raw/. Never touches corpus.u16 or corpus-v2.
# Same format and cleaning discipline as make_corpus_v2.py (identical filters, identical
# tokenization: BOS (id 1) + BPE ids of line+"\n", uint16 stream), plus two v3 additions:
#   1. Gutenberg header/footer stripped (text taken between the START/END OF THE PROJECT
#      GUTENBERG EBOOK markers — the license boilerplate never enters the stream).
#   2. Held-window leak guard: every line whose text appears inside an existing lab held
#      window (v1 corpus.u16 and v2 corpus-v2.u16, every-40th-256-block split, exactly as
#      train.held_windows constructs them) is dropped, so no held text can leak into v3
#      training. Inside v3 itself, the global exact line dedup (v2 discipline) guarantees
#      no line — hence no held window content — can repeat in a training window.
import hashlib, json, os, re, sys
from pathlib import Path
import numpy as np
# Measured on this contended VM (corpus-v3/bench_tok.py): encode_batch with the
# tokenizer's parallel thread pool collapses to ~11k pieces/s under CPU quota
# contention, while single-threaded batch encoding sustains ~56k pieces/s.
# Must be set before the tokenizers import.
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from tokenizers import Tokenizer

LAB = Path(__file__).resolve().parent
OUT = LAB / "corpus-v3"
RAW = OUT / "raw"
BOS, CTX, HELD_EVERY = 1, 256, 40
tk = Tokenizer.from_file(str(Path.home() / "workspace/fable-audit-copy/cells/scratch/tokenizer.json"))

SEP_RE = re.compile(r"^\s*[-=*_~#]{3,}\s*$")
TABLE_RE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
FENCE_RE = re.compile(r"^\s*```\w*\s*$")
GSTART = re.compile(r"\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*")
GEND = re.compile(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*")

def numeric_heavy(line: str) -> bool:
    # v2 semantics (>70% digits/symbols over >40 chars), C-speed implementation:
    # v2's per-char Python loop is the bottleneck at v3 scale (~500M chars).
    # Difference vs v2: isdigit() also caught non-ASCII digits; this table covers
    # ASCII digits + v2's exact symbol set — immaterial on this corpus.
    if len(line) <= 40:
        return False
    rest = line.translate(_NUMTBL)
    return (len(line) - len(rest)) / len(line) > 0.7

_NUMTBL = {ord(c): None for c in "0123456789.,+-eE \t"}

def held_line_keys(u16_path):
    """Text keys of every BOS-delimited segment inside the held blocks of an existing
    lab corpus (the positional split train.py uses). Both the raw decoded text and its
    stripped variant are keyed, to catch whitespace jitter in either direction."""
    data = np.memmap(u16_path, dtype=np.uint16, mode="r")
    keys = set()
    nblocks = (len(data) - CTX) // CTX
    for w in range(0, nblocks):
        if w % HELD_EVERY:
            continue
        block = np.asarray(data[w * CTX:(w + 1) * CTX], dtype=np.uint16)
        seg = []
        for tid in block.tolist() + [BOS]:
            if tid == BOS:
                if seg:
                    txt = tk.decode(seg)
                    keys.add(hashlib.md5(txt.encode("utf-8")).hexdigest())
                    keys.add(hashlib.md5(txt.strip().encode("utf-8")).hexdigest())
                seg = []
            else:
                seg.append(tid)
    return keys

print("building held-window leak blocklist from v1 + v2 held blocks...", flush=True)
held_keys = held_line_keys(LAB / "corpus.u16") | held_line_keys(LAB / "corpus-v2" / "corpus-v2.u16")
print(f"held blocklist: {len(held_keys)} segment keys", flush=True)

stats = {"files_seen": 0, "files_dup_exact": 0, "files_kept": 0,
         "gutenberg_files_skipped_no_markers": 0, "replacement_chars": 0,
         "lines_in": 0, "lines_dropped_empty": 0, "lines_dropped_separator": 0,
         "lines_dropped_numeric": 0, "lines_dropped_mega": 0, "lines_dropped_dup": 0,
         "lines_dropped_held_leak": 0, "lines_kept": 0}
seen_files, seen_lines = set(), set()
per_cat = {}
line_piece_counts = []

def feed(lines_iter, cat, out):
    """Run the v2 line discipline over one source's lines; tokenize kept lines in
    512-line batches straight to the output stream. Returns pieces written."""
    kept_batch, pieces = [], 0
    def flush():
        nonlocal pieces
        if not kept_batch:
            return
        ids_all = []
        for e in tk.encode_batch([l + "\n" for l in kept_batch]):
            ids_all.append(BOS)
            ids_all.extend(e.ids)
            pieces += 1 + len(e.ids)
            line_piece_counts.append(1 + len(e.ids))
        np.asarray(ids_all, dtype=np.uint16).tofile(out)
        kept_batch.clear()
    for line in lines_iter:
        stats["lines_in"] += 1
        if stats["lines_in"] % 200000 == 0:
            print(f"... {stats['lines_in']} lines in, {stats['lines_kept']} kept", flush=True)
        if not line.strip():
            stats["lines_dropped_empty"] += 1
            continue
        if len(line) > 4000:
            stats["lines_dropped_mega"] += 1
            continue
        if SEP_RE.match(line) or FENCE_RE.match(line) or (TABLE_RE.match(line) and "-" in line):
            stats["lines_dropped_separator"] += 1
            continue
        if numeric_heavy(line):
            stats["lines_dropped_numeric"] += 1
            continue
        dig = hashlib.md5(line.encode("utf-8")).digest()
        raw_md5 = dig.hex()
        stripped_md5 = (hashlib.md5(line.strip().encode("utf-8")).hexdigest()
                        if line.strip() != line else raw_md5)
        if raw_md5 in held_keys or stripped_md5 in held_keys:
            stats["lines_dropped_held_leak"] += 1
            continue
        d = int.from_bytes(dig[:8], "little")
        if d in seen_lines:
            stats["lines_dropped_dup"] += 1
            continue
        seen_lines.add(d)
        kept_batch.append(line)
        stats["lines_kept"] += 1
        if len(kept_batch) >= 512:
            flush()
    flush()
    pc = per_cat.setdefault(cat, {"files": 0, "lines": 0, "pieces": 0, "raw_bytes": 0})
    pc["pieces"] += pieces
    return pieces

out_path = OUT / "corpus-v3.u16"
sources = []
with open(out_path, "wb") as out:
    # --- Project Gutenberg (public domain) ---
    for p in sorted((RAW / "gutenberg").glob("pg*.txt")):
        raw = p.read_bytes()
        stats["files_seen"] += 1
        h = hashlib.sha256(raw).hexdigest()
        if h in seen_files:
            stats["files_dup_exact"] += 1
            continue
        seen_files.add(h)
        text = raw.decode("utf-8", errors="replace")
        stats["replacement_chars"] += text.count("\ufffd")
        m0, m1 = GSTART.search(text), GEND.search(text)
        if not m0 or not m1:
            stats["gutenberg_files_skipped_no_markers"] += 1
            print(f"SKIP (no Gutenberg markers): {p.name}", flush=True)
            continue
        body = text[m0.end():m1.start()]
        before = stats["lines_kept"]
        feed(body.splitlines(), "gutenberg_public_domain", out)
        pc = per_cat["gutenberg_public_domain"]
        pc["files"] += 1
        pc["lines"] += stats["lines_kept"] - before
        pc["raw_bytes"] += len(raw)
        stats["files_kept"] += 1
        sources.append({"file": p.name, "category": "gutenberg_public_domain", "raw_bytes": len(raw)})
        print(f"gutenberg {p.name}: kept lines so far {stats['lines_kept']}", flush=True)
    # --- WikiText-103 (CC BY-SA 3.0) ---
    wt_dir = RAW / "wikitext" / "wikitext-103-raw-v1"
    for name in ("wiki.train.raw", "wiki.valid.raw", "wiki.test.raw"):
        p = wt_dir / name
        if not p.exists():
            print(f"MISSING wikitext file: {p}", flush=True)
            continue
        stats["files_seen"] += 1
        before = stats["lines_kept"]
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            feed((ln.rstrip("\n").rstrip("\r") for ln in fh), "wikitext103_cc_by_sa", out)
        pc = per_cat["wikitext103_cc_by_sa"]
        pc["files"] += 1
        pc["lines"] += stats["lines_kept"] - before
        pc["raw_bytes"] += p.stat().st_size
        stats["files_kept"] += 1
        sources.append({"file": name, "category": "wikitext103_cc_by_sa", "raw_bytes": p.stat().st_size})
        print(f"wikitext {name}: kept lines so far {stats['lines_kept']}", flush=True)

total = int(np.memmap(out_path, dtype=np.uint16, mode="r").shape[0])
counts = np.asarray(line_piece_counts, dtype=np.int64)
meta = {"pieces": total, "bytes": out_path.stat().st_size,
        "unique_lines": int(stats["lines_kept"]),
        "median_line_pieces": float(np.median(counts)) if len(counts) else 0,
        "mean_line_pieces": float(counts.mean()) if len(counts) else 0,
        "stats": stats, "per_category": per_cat, "sources": sources,
        "held_blocklist_keys": len(held_keys),
        "build": "make_corpus_v3.py — v2 filter discipline + Gutenberg strip + held-window leak guard; see header"}
(OUT / "corpus-v3.json").write_text(json.dumps(meta, indent=1))
print(f"corpus v3: {total/1e6:.2f}M pieces from {stats['files_kept']} files, {stats['lines_kept']} unique kept lines")
print(json.dumps(stats, indent=1))
print(json.dumps(per_cat, indent=1))
