# Muse's work — written by Muse, on Muse's side of the BitNet lab.
# Fable's side was not touched. Companion to scale-next/BUCKETS.md.
"""Tilt-feasibility probe: bucket aligned 256-token windows of corpus.u16 by
CONTENT ALONE (deterministic, cheap), and check per-bucket held slices.

Bucket rule (priority order, first match wins) — see BUCKETS.md for rationale:
  1. numeric   digit share of decoded chars >= 0.30
  2. gibberish count of literal 'Ġ'+'Ċ' chars >= 8, or non-ASCII share >= 0.20
               (non-ASCII counted excluding the box-drawing/geometric block
               U+2500–U+257F, so ASCII-art diagrams in docs are not counted)
               (BPE merge-table fragment salad; ordinary decoded prose never
               contains Ġ/Ċ — they only appear when merges.txt is the *content*)
  3. german    German function-word rate >= 0.05 and > English function-word rate
  4. lists     BOS count >= 28 (very short lines: name lists, entry_points,
               top_level files, dense enumerations)
  5. prose     residual: English markdown/docs/licenses

Inputs per window: the 256 uint16 ids only. Decode via the same tokenizer
make_corpus.py used (fable-audit-copy/cells/scratch/tokenizer.json, read-only
data file). No source-file information is used — by design, since corpus.u16
stores no offsets (see BUCKETS.md §1).

Held sets replicate train.py exactly: aligned windows w with w % 40 == 0 are
held candidates; the standard judged set is 128 of them picked evenly
(starts[int(i*(len(starts)-1)/127)]).

Usage: python bucket_probe.py [--sample 20000] [--show 3]
Requires: numpy + tokenizers (the fable-validation venv python has both).
"""
import argparse, re
from collections import Counter
from pathlib import Path
import numpy as np
from tokenizers import Tokenizer

LAB = Path(__file__).resolve().parent.parent
CTX, HELD_EVERY, N_EVAL = 256, 40, 128
BOS = 1

GER = set("der die das und ist ich nicht ein eine den mit von zu auf für sich es im am auch "
          "werden war sind haben als an bei nach wie aber oder wenn schon noch nur so diese "
          "diesem dieser einem einen zur zum vom ins ans ums".split())
ENG = set("the of and to in is a for that with as on are be by it from or an at this have "
          "was were will would can could should their there these those then than".split())
WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+")

tk = Tokenizer.from_file(str(Path.home() / "workspace/fable-audit-copy/cells/scratch/tokenizer.json"))
data = np.memmap(LAB / "corpus.u16", dtype=np.uint16, mode="r")
NW = len(data) // CTX


def bucket_of(ids):
    """ids: np.uint16 array of CTX token ids -> (bucket_name, feature_dict)."""
    bos = int((ids == BOS).sum())
    txt = tk.decode([int(x) for x in ids if x != BOS])
    nch = max(1, len(txt))
    dig = sum(c.isdigit() for c in txt) / nch
    gcount = txt.count("Ġ") + txt.count("Ċ")
    nonascii = sum(ord(c) > 127 and not 0x2500 <= ord(c) <= 0x257F for c in txt) / nch
    words = WORD_RE.findall(txt.lower())
    nw = max(1, len(words))
    ger = sum(w in GER for w in words) / nw
    eng = sum(w in ENG for w in words) / nw
    feats = {"bos": bos, "dig": round(dig, 3), "g": gcount, "na": round(nonascii, 3),
             "ger": round(ger, 3), "eng": round(eng, 3)}
    if dig >= 0.30:
        return "numeric", feats, txt
    if gcount >= 8 or nonascii >= 0.20:
        return "gibberish", feats, txt
    if ger >= 0.05 and ger > eng:
        return "german", feats, txt
    if bos >= 28:
        return "lists", feats, txt
    return "prose", feats, txt


def held_starts():
    starts = [w * CTX for w in range(0, (len(data) - CTX) // CTX) if w % HELD_EVERY == 0]
    pick = [starts[int(i * (len(starts) - 1) / (N_EVAL - 1))] for i in range(N_EVAL)]
    return starts, pick


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=20000)
    ap.add_argument("--show", type=int, default=3, help="spot-check excerpts per bucket")
    a = ap.parse_args()

    idx = sorted({int(i * (NW - 1) / (a.sample - 1)) for i in range(a.sample)})
    counts, examples = Counter(), {}
    for w in idx:
        b, f, txt = bucket_of(np.asarray(data[w * CTX:(w + 1) * CTX]))
        counts[b] += 1
        examples.setdefault(b, []).append((w, f, txt))
    print(f"== sample: {len(idx)} evenly spaced aligned windows of {NW} total ==")
    for b in ("numeric", "gibberish", "german", "lists", "prose"):
        print(f"  {b:10s} {counts[b]:6d}  {counts[b]/len(idx)*100:5.1f}%")

    starts, pick = held_starts()
    hc = Counter(bucket_of(np.asarray(data[s:s + CTX]))[0] for s in starts)
    pc = Counter(bucket_of(np.asarray(data[s:s + CTX]))[0] for s in pick)
    print(f"\n== held candidates (every 40th window): {len(starts)} ==")
    for b in ("numeric", "gibberish", "german", "lists", "prose"):
        print(f"  {b:10s} {hc[b]:4d}")
    print(f"\n== standard judged set: {len(pick)} windows ==")
    for b in ("numeric", "gibberish", "german", "lists", "prose"):
        flag = "  <-- <20: too few for a per-bucket held loss" if pc[b] < 20 else ""
        print(f"  {b:10s} {pc[b]:4d}{flag}")

    print("\n== spot-check excerpts ==")
    for b in ("numeric", "gibberish", "german", "lists", "prose"):
        for w, f, txt in examples.get(b, [])[:a.show]:
            preview = " ".join(txt.split())[:180]
            print(f"[{b} win {w} {f}] {preview!r}")


if __name__ == "__main__":
    main()
