# Muse's work — built and run by Muse on Muse's side of the lab. Fable's HiveMIND was read read-only for the mechanism; nothing on Fable's side was touched or used.

"""Build this lab's own corpus: prose text from the local workspace trees, tokenized with the
hive's shared BPE vocabulary (read from the audit copy; data file only, nothing executed from
there), line by line with a BOS piece per line — the same construction as scratch.corpus.
Fable's harvested corpus itself is not in the repo (it is regenerated on their side), so
absolute losses here are NOT comparable to their 4.141; arm-vs-arm comparisons are the point."""
import hashlib, json
from pathlib import Path
import numpy as np
from tokenizers import Tokenizer

LAB = Path(__file__).resolve().parent
BOS = 1
TREES = [Path.home() / "workspace" / t for t in ("fable-audit-copy", "hivemind-muse", "edit-lab")]
tk = Tokenizer.from_file(str(Path.home() / "workspace/fable-audit-copy/cells/scratch/tokenizer.json"))

seen, files = set(), []
for tree in TREES:
    for p in sorted(tree.rglob("*")):
        if p.suffix in (".md", ".txt", ".rst") and ".git" not in p.parts and p.is_file():
            raw = p.read_bytes()
            h = hashlib.sha256(raw).hexdigest()
            if h not in seen:
                seen.add(h)
                files.append((str(p), raw.decode("utf-8", errors="replace")))

out_path = LAB / "corpus.u16"
total = 0
with open(out_path, "wb") as out:
    for name, text in files:
        lines = text.splitlines(keepends=True)
        for i in range(0, len(lines), 512):
            for e in tk.encode_batch(lines[i:i + 512]):
                np.asarray([BOS] + e.ids, dtype=np.uint16).tofile(out)
                total += 1 + len(e.ids)
meta = {"pieces": total, "files": len(files), "bytes": out_path.stat().st_size,
        "sources": [n for n, _ in files]}
(LAB / "corpus.json").write_text(json.dumps(meta, indent=1))
print(f"corpus: {total/1e6:.2f}M pieces from {len(files)} unique prose files")
