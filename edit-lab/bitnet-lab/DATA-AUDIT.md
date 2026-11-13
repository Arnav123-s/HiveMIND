# Muse's work — Muse's side

# BitNet lab corpus audit — 2026-11-12/13

**Question:** is the lab's corpus (~5.92M pieces) good enough to train on, especially at the scale
ladder's 10M–50M-weight rungs — and if not, what can be fixed from material already on this machine?

**Short answer:** the corpus is much worse than its headline size. Only about **0.91M of its 5.92M
pieces are unique, real text**. The rest is exact duplicates (30.8% of all pieces), numeric test-data
dumps (~23%), BPE merge-table gibberish, software-license boilerplate, and package metadata that the
v1 builder swallowed by accident. Corpus v2 (built alongside, original untouched) contains the clean
0.91M. v2 fixes honesty, not volume: the big rungs stay token-starved either way, and the real fix —
a proper external text corpus — needs a download decision, flagged below, **not** done here.

---

## 1. How v1 was built (from `make_corpus.py`)

Every `.md` / `.txt` / `.rst` file under three workspace trees (`fable-audit-copy`, `hivemind-muse`,
`edit-lab`), exact-file-deduped by SHA-256 (393 files kept), tokenized line-by-line with the hive's
shared BPE tokenizer, one BOS piece per line, stored as a uint16 stream (`corpus.u16`, 11,834,472
bytes). Nobody looked at *which* files those trees contained. The trees include two Python virtual
environments and a HuggingFace cache — and everything in them that ends in .txt/.md/.rst came along.

## 2. Profile of the token stream (measured on `corpus.u16` directly)

| Measure | Value |
|---|---|
| Total pieces (incl. BOS) | 5,917,236 |
| Lines (BOS-marked segments) | 343,465 |
| Line length: median / mean / p90 / p99 | 9 / 17.2 / 25 / 73 pieces |
| Longest single "line" | 154,016 pieces |
| Pieces in lines >1,000 pieces | 1,358,824 (**23.0%** of the corpus) |
| Vocab used | 3,548 / 4,096 ids |
| Tokens appearing <100 times | 1,984 of 3,548 |
| Most common token | id 222 = a bare space, 604,047× (**10.2%** of all pieces) |
| Next most common | BOS, newline, then `Ä` `Ã` `Â` (UTF-8 byte fragments), `00`, `ł` |
| First ordinary English pieces | `.` and `e`, at ranks 9–10 |

The median training "line" is 8 real tokens. Training windows (256 pieces, random offsets) are
mostly collages of unrelated fragments, boilerplate and number streams — not prose.

## 3. Source mix (v1's own 393 files, by file bytes; piece shares are worse for the junk — see §5)

| Category | Files | Share of source bytes |
|---|---|---|
| venv / HuggingFace-cache junk: licenses, `merges.txt`, scipy/sklearn test data, package metadata | 222 | **73.9%** |
| German Tatoeba sentences (`de_sentences_train` + `de_sentences_test`) | 2 | 10.6% |
| Muse edit-lab notes/results | 79 | 9.4% |
| HiveMIND docs/reports (Fable side, read as data only) | 19 | 2.7% |
| HiveMIND docs (Muse side) | 8 | 1.8% |
| Fable training/other small files | 63 | 1.6% |

The two largest source files in the whole corpus are the Qwen models' `merges.txt` BPE merge
tables (1.67 MB each) — lists of token fragments that tokenize into byte-level gibberish
(random-position decodes show e.g. `åį± éĻ©`, `éĺµ å®¹`).

## 4. Duplication (measured on the token stream)

- **Exact duplicate lines:** 343,465 lines → only 178,581 unique. **48.0% of all lines are redundant
  copies; 30.8% of all pieces (1,821,470) are spent on copies.** 93.2% of lines belong to some
  duplicated group.
- The most-repeated lines are pure boilerplate: `" \n"` ×5,700, `" ```\n"` ×284, `" ```bash\n"` ×169,
  markdown table rules ×80, dashed separator lines ×68.
- Much of this is the same license/readme/test-data files repeated across two venvs and many
  packages — file-level dedup could not catch them because the copies sit inside different files.
- **Near-duplicates:** in a 20,000-line sample, 15.1% of distinct 5-token shingles appear in more
  than one sampled line (shared boilerplate phrases, license wording, repeated report scaffolding).
- **Consequence for measurement:** held windows are every 40th 256-piece window of this same stream.
  With ~31% of pieces duplicated, held-out content routinely also appears in training windows, so
  all v1 held losses are flattered by an unknown amount. Arm-vs-arm comparisons (same corpus, same
  split) remain valid; absolute loss values should not be trusted as "language modelling quality."

## 5. Quality problems, plainly

1. **~23% numeric dumps.** Nine "lines" of 120k–154k pieces each are scipy test matrices — endless
   floats like `5.0817745e-01 4.4535192e-01 …`. They teach number-stream statistics, not language,
   and they are long enough to fill entire training windows by themselves.
2. **Merge-table gibberish.** The Qwen `merges.txt` files contribute on the order of a million+
   pieces of token-fragment noise (exact share not separable in the interleaved stream; they are
   42% of all source bytes).
3. **Boilerplate domination.** License texts, `top_level.txt` / `entry_points.txt` one-word files,
   README templates and separator lines make up most of what remains outside the real prose.
4. **Encoding damage.** v1 decoded sources with `errors="replace"` and byte-fragment tokens
   (`Ä Ã Â ł`) sit at ranks 4–8 of the whole vocabulary — mojibake is a first-class citizen here.
5. **German test split inside training data.** `de_sentences_test.txt` was included as training
   text (same in v2, kept for parity — flagged, not silently fixed).
6. **What real text there is** is narrow: HiveMIND project documents, lab notes, and German
   sentences. No books, no general web prose, no dialogue. A model can only ever learn this
   project's own paperwork dialect from it.

## 6. What this means at 10M–50M weights

Ladder runs use a fixed budget of 56 steps × 32 batch × 256 context = **458,752 pieces per run**.

| Rung | Total params | Pieces per param (one run) | vs ~20 pieces/param rule of thumb |
|---|---|---|---|
| ~2M ternary (3.25M total) | 3,252,096 | 0.14 | ~140× short |
| ~10M ternary (11.69M total) | 11,686,400 | 0.039 | ~500× short |
| ~50M ternary (~53M total) | ~53,000,000 | ~0.009 | ~2,300× short |

And that is against the *junk* count. Against unique real text (0.91M pieces), the whole corpus is
about **two ladder runs' worth of data**. Published BitNet results are trained on hundreds of
billions of tokens; this lab's earlier scaling research (Spectra exponents: data 0.81 vs params
0.32) says data is the stronger lever of the two. Conclusion: at the big rungs the models are not
"undertrained on a small corpus" — they are effectively being asked to memorize ~1M real pieces
with 10–50M weights while most of their gradient signal comes from numbers and boilerplate.
Ladder results at 10M/50M should be read as *lower bounds under data starvation*, never as
evidence about the architecture's ceiling.

## 7. Corpus v2 — what was built

`make_corpus_v2.py` (same trees, same tokenizer, same BOS-per-line format), output in
`corpus-v2/corpus-v2.u16` + `corpus-v2.json`. `corpus.u16` was **not** touched.

Filters: exclude venv/site-packages/dist-info/HF-cache/pytest-cache paths and any `merges.txt`;
file-level SHA-256 dedup; drop empty lines, pure separator/fence/table-rule lines, numeric-dump
lines (>70% digits/symbols over >40 chars), and mega-lines (>4,000 chars); global exact line dedup.

| | v1 | v2 |
|---|---|---|
| Pieces | 5,917,236 | **907,409** |
| Lines | 343,465 | 20,848 (all unique) |
| Median / mean line | 9 / 17.2 | 36 / 43.5 pieces |
| Longest line | 154,016 | 596 pieces |
| Pieces in >1,000-piece lines | 1,358,824 | 0 |
| Exact duplicate lines | 48.0% redundant | 0 |
| Vocab used | 3,548 | 3,292 |

v2 composition: German sentences 414,201 pieces (45.7%), HiveMIND docs Muse side 261,768 (28.8%),
HiveMIND docs Fable side 118,801 (13.1%), edit-lab notes 112,639 (12.4%). Note: v2 was built from
today's trees, which have grown since v1 (the `hivemind-muse` clone now mirrors edit-lab), so file
counts differ from v1's 393 — the dedup stats in `corpus-v2.json` record exactly what was dropped
(498 exact-duplicate files, 3,188 empty lines, 840 separator lines, 150 numeric lines, 2,943
duplicate lines, 391 junk-path files excluded).

## 8. Recommendation

1. **Keep v1 as the canonical corpus for the current experiment series** (vote sweep, RoPE, round 2,
   JEPA, the ladder in flight). Every comparison the lab has published is arm-vs-arm on v1; switching
   mid-series would break comparability for zero scientific gain.
2. **Adopt v2 for any new series, and use v2 numbers when talking about the big rungs.** If the
   ladder is re-run or extended (more seeds, more steps), run it on v2: the absolute losses will
   look worse and mean more. Expect v2 held loss to read higher partly because the duplicate leakage
   in §4 is gone.
3. **Do not expect v2 to rescue the 10M/50M rungs.** It fixes the signal, not the starvation:
   0.91M unique pieces against ~53M params is still ~0.017 pieces/param for a full pass. Cap
   useful epochs at ~2–4 before repetition dominates.
4. **The real fix needs a decision, not more cleaning.** On-machine additions are marginal
   (`research_notes` ≈ +0.1–0.2M pieces of the same project dialect). A genuine corpus — a few
   hundred MB of clean public-domain/open text — has to be downloaded, which this audit did not
   do. Flagged for Arnav: one download decision would change the lab's ceiling more than any
   trainer lever tested so far.
5. Minor, for the next rebuild: exclude `de_sentences_test.txt` from training text (it is a test
   split), and build corpora from an explicit source allowlist, never from whole workspace trees.

*Method note: all v1 statistics were measured directly on `corpus.u16` and v1's own
`corpus.json` source list (full-stream passes for lengths/duplication; a 20k-line sample for
near-duplicates; 5k-line sample for numeric-line share). v2 statistics are from the build log in
`corpus-v2/corpus-v2.json`, verified by an independent pass over `corpus-v2.u16`.*
