# Muse's work — Muse's side

# Corpus v3 — completion record (2026-11-12)

Builder: `make_corpus_v3.py`. Metadata: `corpus-v3.json`. Sources/licenses: `SOURCES.md`.
Verification status: **the corpus is built; the independent split check crashed before
running and has NOT produced a verdict — held overlap is UNVERIFIED (see §4).**

## 1. Final size — three-way cross-check, full agreement

| Source | Figure |
|---|---|
| File on disk: `corpus-v3.u16` = 382,512,504 bytes ÷ 2 (uint16) | **191,256,252 pieces** |
| `corpus-v3.json` (`"pieces"`; `"bytes"` = 382,512,504) | **191,256,252 pieces** |
| `build.log` summary (per-category pieces summed: 24,586,780 + 166,669,472) | **191,256,252 pieces** |

No disagreement anywhere. Internal consistency also checks out exactly:
per-category lines 1,168,121 + 977,422 = 2,145,543 = lines kept = unique lines;
per-category raw bytes 73,663,011 + 543,536,921 = 617,199,932 = the acquired total in
`SOURCES.md`; and lines-in 4,486,949 minus every drop category below = 2,145,543 kept.
Median line 24 pieces, mean 89.1 (WikiText's long lines dominate the piece count).

## 2. Source breakdown and licenses

| Source | License | Raw bytes | Lines kept | Pieces | Share |
|---|---|---|---|---|---|
| Project Gutenberg — 67 books, all published before 1930 | **Public domain (US)**; Gutenberg license wrappers stripped at build (text taken only between the START/END ebook markers) | 73,663,011 | 1,168,121 | 24,586,780 | 12.9% |
| WikiText-103 (`Salesforce/wikitext`, config `wikitext-103-raw-v1`, rev `b08601e04326c79dfdd32d625aee71d232d685c3`) | **CC BY-SA 3.0** (also tagged GFDL on the dataset record) | 543,536,921 | 977,422 | 166,669,472 | 87.1% |

Only openly-licensed / public-domain text, from official distributions (details and the
full book list in `SOURCES.md`). Tokenization: the lab's shared BPE tokenizer (vocab
4,096), BOS (id 1) + BPE ids per line, uint16 stream — the same format as v1/v2.

## 3. Dedup / filtering method (the v2 discipline, in `make_corpus_v3.py`)

Line-level processing of all 70 source files (0 exact-duplicate files):

- lines in: 4,486,949
- dropped empty: 2,094,585 · separator: 25 · numeric: 963 · mega-lines: 19
- dropped **exact-duplicate lines: 245,764** (global line dedup)
- dropped by the **build-time held-window leak guard: 50 lines**, against a blocklist of
  18,706 held-window segment keys (`held_blocklist_keys` in `corpus-v3.json`)
- lines kept: **2,145,543 unique lines** → 191,256,252 pieces

## 4. Split check — CRASHED, no verdict (read this before quoting any v3 number)

`check_v3_split.py` was run detached against the finished corpus. It **crashed at
startup, before any of its four checks ran**, and the process has exited:

```
File "check_v3_split.py", line 25, in <module>
    mm = mmap.mmap(P.open("rb").fileno(), 0, access=mmap.ACCESS_READ)
OSError: [Errno 9] Bad file descriptor
```

Cause: `P.open("rb")` is a temporary — the file object is closed before `mmap` uses its
descriptor. One-line fix (bind the open file to a variable first), but **no second copy
was started and the corpus was not patched — that call belongs to the head of ops.**

Consequences, stated plainly:

- `corpus-v3/split-check.json` **does not exist**. There is no held-overlap number.
- The held overlap must **not** be quoted as 0. What exists is the build-time guard
  (§3: 50 lines dropped against 18,706 blocklist keys) — a construction measure, not
  the independent post-build verification the check was written to provide.
- Until the checker is fixed and run to completion, every v3 result carries
  "split unverified" next to it.

## 5. Known construction defects (from the endgame plan, E-4) — status as built

1. **Document-level leakage past the line guard.** Dedup and the leak guard operate per
   line; a held document reappearing with altered/split lines could pass in pieces.
   Status: **known, unfixed in v3 as built.** No document-level near-duplicate analysis
   has been run. (This is also why §4's verification matters.)
2. **Hard-wrapped Gutenberg text, tokenized BOS-per-line.** Gutenberg plain texts are
   hard-wrapped at ~70 columns, and each wrapped fragment became a BOS-delimited
   segment — Gutenberg "lines" are wrap fragments, not sentences/paragraphs (median
   line = 24 pieces). Status: **known, inherent to the build as run.** Harmless for
   next-token training; it does mean line-level statistics and any per-line semantics
   for the Gutenberg slice are wrap artifacts.
3. **WikiText valid/test splits inside the stream.** `wiki.valid.raw` (1,148,008 B) and
   `wiki.test.raw` (1,292,014 B) were ingested as ordinary corpus text (both are listed
   in `corpus-v3.json` sources). Status: **known, present in the built corpus.** It
   matters only if WikiText's own validation/test splits are ever used to evaluate a
   v3-trained model — they would be train-contaminated. The lab's own held windows are
   carved from the stream itself; those are what the (crashed) split check targets.

---

## Addendum — Split-check rerun (2026-11-13 01:41 PST)

This addendum supersedes §4 above: the checker was fixed and run to completion, so
corpus v3's held overlap is now **verified** — with the exact numbers below, not
assumed. (The original "split unverified" statement above stands as the record of
the state before this rerun; it is not edited.)

**The fix:** `check_v3_split.py` line 25 crashed at startup with
`OSError: [Errno 9] Bad file descriptor` — the temporary file object in
`mmap.mmap(P.open("rb").fileno(), 0, access=mmap.ACCESS_READ)` was discarded, its
descriptor closed, and the mmap died. One-line fix: the open file object is now
bound to `_corpus_file` for the life of the mmap. Nothing else in the script changed.

**Run history:** the first post-fix attempt was killed mid-check-1 by a runtime
restart (its buffered output was lost; no partial results survived). The rerun then
completed with exit code 0 in ~36 minutes under load, writing
`corpus-v3/split-check.json`. Verdict, exactly as recorded there:

- Pieces checked: **191,256,252**
- Check 1 — eval windows in the training region: **0** (128 total occurrences of the
  128 evaluation windows, all at their aligned held positions — no held window
  occurs anywhere in training).
- Check 2 — duplicate aligned 256-piece blocks: **1** of 747,094 blocks, of which
  **0 involve a held block**.
- Check 3 — duplicate BOS-delimited segments: **1,149** duplicate occurrences among
  2,145,543 segments.
- Check 4 — 24-piece shingle spot check: **58 of 2,000** shingles sampled from held
  blocks also touch a training block.
- Script verdict: **`split_clean: false` — SPLIT NOT CLEAN.**

**Reading of the result:** the strongest leakage test passes exactly — no complete
held window leaks into the training region, and no held block is part of the single
duplicate aligned block. The "not clean" verdict comes from the finer-grained
checks: short 24-piece fragments from held blocks do recur in training blocks
(58/2,000 sampled), and the stream contains duplicate segments (1,149) and one
duplicate aligned block. That is consistent with known construction defect §5.1
(the build's guard and dedup operate per line, so documents/fragments can reappear
in pieces). Any v3 result should therefore quote: held-window leakage **0**;
shingle-level overlap **58/2,000**; `split_clean` **false**.
