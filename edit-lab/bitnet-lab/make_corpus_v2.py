# Muse's work — built and run by Muse on Muse's side of the lab.
# Corpus v2 builder: same source trees and same tokenizer as make_corpus.py (v1),
# with the junk v1 swallowed removed. Never touches corpus.u16.
# Filters (all recorded in corpus-v2/corpus-v2.json):
#   1. Path exclusions: /venv/, site-packages, .dist-info, /hf/, .pytest_cache,
#      __pycache__, and any file named merges.txt (BPE merge tables tokenize to gibberish).
#   2. File-level exact dedup by sha256 (same as v1).
#   3. Line filters: drop empty/whitespace-only lines; drop pure separator lines
#      (---, ===, markdown table rules, bare code fences); drop numeric dumps
#      (lines >40 chars that are >70% digits/symbols/e-notation); drop mega-lines
#      (>4000 chars — newline-free numeric test-data dumps).
#   4. Global exact line dedup, first occurrence kept.
# Tokenization identical to v1: BOS (id 1) + BPE ids per line, uint16 stream.
import hashlib, json, re
from pathlib import Path
import numpy as np
from tokenizers import Tokenizer

LAB = Path(__file__).resolve().parent
OUT = LAB / "corpus-v2"
OUT.mkdir(exist_ok=True)
BOS = 1
TREES = [Path.home() / "workspace" / t for t in ("fable-audit-copy", "hivemind-muse", "edit-lab")]
tk = Tokenizer.from_file(str(Path.home() / "workspace/fable-audit-copy/cells/scratch/tokenizer.json"))

EXCLUDE_PARTS = ("/venv/", "site-packages", ".dist-info", "/hf/", ".pytest_cache", "__pycache__")
SEP_RE = re.compile(r"^\s*[-=*_~#]{3,}\s*$")
TABLE_RE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
FENCE_RE = re.compile(r"^\s*```\w*\s*$")

def category(p: str) -> str:
    low = p.lower()
    if "de_sentences" in low:
        return "german_sentences"
    if "fable-audit-copy" in low:
        return "hivemind_docs_fable_side"
    if "hivemind-muse" in low:
        return "hivemind_docs_claude_side"
    return "edit_lab_notes"

def numeric_heavy(line: str) -> bool:
    if len(line) <= 40:
        return False
    num = sum(ch.isdigit() or ch in ".,+-eE \t" for ch in line)
    return num / len(line) > 0.7

stats = {"files_seen": 0, "files_excluded_path": 0, "files_dup_exact": 0, "files_kept": 0,
         "lines_in": 0, "lines_dropped_empty": 0, "lines_dropped_separator": 0,
         "lines_dropped_numeric": 0, "lines_dropped_mega": 0, "lines_dropped_dup": 0,
         "lines_kept": 0}
seen_files, seen_lines = set(), set()
kept = []  # (path, [lines])
per_cat = {}

for tree in TREES:
    for p in sorted(tree.rglob("*")):
        if p.suffix not in (".md", ".txt", ".rst") or ".git" in p.parts or not p.is_file():
            continue
        stats["files_seen"] += 1
        sp = str(p)
        if any(x in sp for x in EXCLUDE_PARTS) or p.name == "merges.txt":
            stats["files_excluded_path"] += 1
            continue
        raw = p.read_bytes()
        h = hashlib.sha256(raw).hexdigest()
        if h in seen_files:
            stats["files_dup_exact"] += 1
            continue
        seen_files.add(h)
        text = raw.decode("utf-8", errors="replace")
        lines_out = []
        for line in text.splitlines():
            stats["lines_in"] += 1
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
            lh = hashlib.md5(line.encode("utf-8")).hexdigest()
            if lh in seen_lines:
                stats["lines_dropped_dup"] += 1
                continue
            seen_lines.add(lh)
            lines_out.append(line)
        if lines_out:
            kept.append((sp, lines_out))
            stats["files_kept"] += 1
            stats["lines_kept"] += len(lines_out)

out_path = OUT / "corpus-v2.u16"
total = 0
with open(out_path, "wb") as out:
    for name, lines in kept:
        file_pieces = 0
        for i in range(0, len(lines), 512):
            for e in tk.encode_batch([l + "\n" for l in lines[i:i + 512]]):
                np.asarray([BOS] + e.ids, dtype=np.uint16).tofile(out)
                file_pieces += 1 + len(e.ids)
        total += file_pieces
        c = category(name)
        pc = per_cat.setdefault(c, {"files": 0, "lines": 0, "pieces": 0})
        pc["files"] += 1
        pc["lines"] += len(lines)
        pc["pieces"] += file_pieces

meta = {"pieces": total, "bytes": out_path.stat().st_size, "stats": stats,
        "per_category": per_cat, "sources": [n for n, _ in kept],
        "build": "make_corpus_v2.py — see header for the exact filter list"}
(OUT / "corpus-v2.json").write_text(json.dumps(meta, indent=1))
print(f"corpus v2: {total/1e6:.2f}M pieces from {stats['files_kept']} files, {stats['lines_kept']} unique kept lines")
print(json.dumps(stats, indent=1))
print(json.dumps(per_cat, indent=1))
