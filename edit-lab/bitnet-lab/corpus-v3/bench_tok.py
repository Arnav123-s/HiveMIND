# Muse's work — Muse's side. Micro-benchmark for the corpus v3 builder:
# filter loop vs encode_batch variants on a real WikiText sample.
import hashlib, re, sys, time
from pathlib import Path
from tokenizers import Tokenizer

mode = sys.argv[1]
P = Path.home() / "workspace/edit-lab/bitnet-lab/corpus-v3/raw/wikitext/wikitext-103-raw-v1/wiki.train.raw"
lines = []
with open(P, encoding="utf-8", errors="replace") as fh:
    for ln in fh:
        ln = ln.rstrip("\n")
        if ln.strip():
            lines.append(ln)
        if len(lines) >= 20000:
            break
print(f"sample: {len(lines)} lines, {sum(len(l) for l in lines)} chars")

SEP_RE = re.compile(r"^\s*[-=*_~#]{3,}\s*$")
TABLE_RE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
FENCE_RE = re.compile(r"^\s*```\w*\s*$")
NUMTBL = {ord(c): None for c in "0123456789.,+-eE \t"}

def numeric_heavy(line):
    if len(line) <= 40:
        return False
    rest = line.translate(NUMTBL)
    return (len(line) - len(rest)) / len(line) > 0.7

if mode == "filter":
    t0 = time.time(); kept = 0; seen = set()
    for line in lines:
        if len(line) > 4000: continue
        if SEP_RE.match(line) or FENCE_RE.match(line) or (TABLE_RE.match(line) and "-" in line): continue
        if numeric_heavy(line): continue
        dig = hashlib.md5(line.encode()).digest()
        d = int.from_bytes(dig[:8], "little")
        if d in seen: continue
        seen.add(d); kept += 1
    dt = time.time() - t0
    print(f"filter: {kept} kept in {dt:.2f}s = {len(lines)/dt:.0f} lines/s")
elif mode.startswith("enc"):
    tk = Tokenizer.from_file(str(Path.home() / "workspace/fable-audit-copy/cells/scratch/tokenizer.json"))
    batch = int(mode[3:])
    t0 = time.time(); pieces = 0
    for i in range(0, len(lines), batch):
        for e in tk.encode_batch([l + "\n" for l in lines[i:i + batch]]):
            pieces += 1 + len(e.ids)
    dt = time.time() - t0
    print(f"enc{batch}: {pieces} pieces in {dt:.2f}s = {len(lines)/dt:.0f} lines/s, {pieces/dt:.0f} pieces/s")
