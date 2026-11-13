# Muse's work — Muse's side of the BitNet lab. Fable's side was not touched.

# Tilt-feasibility: bucketing corpus.u16 windows into specialties

**Question:** for the overlap program (large tilted BitNet generalists), can the
lab corpus's 256-token windows be split into 3–5 "specialties" — deterministically,
from window content alone, cheaply — with per-bucket held slices large enough to
measure a tilt?

**Short answer:** the bucketing mechanics work and the buckets are cleanly
separable — but on corpus v1 they are mostly *artifact types, not specialties*.
54% of all windows are BPE merge-table gibberish and 25% are numeric test-data
dumps; only ~21% is language at all (13.6% English prose, 7.0% German). And the
held-set hygiene is bad: in the standard judged set of 128 windows, three of the
five buckets have <20 windows (German 9, prose 18, lists 0). Details and the
exact recommended rule below. Prototype: `scale-next/bucket_probe.py`.

---

## 1. How corpus.u16 was built, and whether a window's source can be recovered

From `make_corpus.py` (read directly):

- **Sources:** every `.md` / `.txt` / `.rst` file under three trees, in this
  order — `~/workspace/fable-audit-copy`, `~/workspace/hivemind-muse`,
  `~/workspace/edit-lab` — walked with `sorted(tree.rglob("*"))`, `.git` paths
  excluded, exact-file dedup by SHA-256. 393 unique files kept.
- **Tokenization:** the hive's shared BPE tokenizer
  (`fable-audit-copy/cells/scratch/tokenizer.json`, vocab 4096, read as a data
  file), applied **line by line**: each source line (split with
  `splitlines(keepends=True)`, encoded in batches of 512 lines) is written as
  `[BOS=1] + ids` in a flat uint16 stream. No file separators, no per-file
  token counts, no offset index.
- **`corpus.json` records only** `{pieces: 5,917,236, files: 393, bytes, sources:
  [paths in write order]}`.

### Source recovery after the fact: NO (not reliably)

- **From `corpus.u16` alone: impossible.** The stream is flat. BOS tokens
  recover *line* boundaries (343,465 lines), but lines are not files — there is
  no marker where one file ends and the next begins, and identical lines recur
  across many files (48% of lines are exact duplicates, per `DATA-AUDIT.md`).
- **By replaying the builder: deterministic in principle, broken in practice —
  measured.** All 393 listed paths still exist on disk, so I re-ran the exact
  tokenization over them in `corpus.json` order. Result: **5,931,173 tokens,
  not 5,917,236 (+13,937, +0.24%)**, and the replayed stream **first diverges
  from `corpus.u16` at absolute offset 4,566 — inside the very first file**
  (`fable-audit-copy/HANDOFF.md`). The sources are living documents that were
  edited after the corpus was built; after the first divergence every
  downstream file boundary shifts by an unknown amount. Per-window file
  attribution is therefore unrecoverable except, at best, for the first
  ~4.5k tokens. Any bucketing that needs to work on this corpus must be
  **content-only** — which is what §2 does.

### Source mix of the 393 files

There are **zero code files**. The builder only admits `.md`/`.txt`/`.rst`, so
"code" exists only as fenced snippets inside markdown (windows containing a
```` ``` ```` fence: ~0.9% of sampled windows). By suffix: `.md` 192 files,
`.txt` 185, `.rst` 16.

Token shares below are from the replay above (current file contents; ≈ the
original shares — the +0.24% drift sits in the living docs, while the big
static artifacts that dominate the shares are not files anyone edits). They
agree in direction with `DATA-AUDIT.md`'s byte shares, and are *worse* for
junk, because merges tables tokenize very densely:

| Content class | Files | Share of replay tokens |
|---|---|---|
| `merges.txt` BPE merge tables (2 Qwen files, near-identical) | 2 | **54.1%** (3,210,797) |
| venv / HF-cache junk excl. merges (licenses, `entry_points.txt`, `top_level.txt`, scipy/sklearn test data, package metadata) | 221 | 29.9% (1,773,110) |
| German Tatoeba sentences (`de_sentences_train` + `_test`) | 2 | 7.0% (414,201) |
| Edit-lab notes/results (real docs) | 78 | 5.5% (325,393) |
| Fable-side HiveMIND docs/data (read as data only) | 82 | 2.5% (146,681) |
| Muse-side HiveMIND docs | 8 | 1.0% (60,991) |

So by content: **markdown/docs prose ≈ 9% of tokens, German data 7%, numeric
dumps ~23% (inside the junk rows — the nine largest scipy files alone are
~1.36M tokens of single-line float matrices), merge-table gibberish 54%, the
rest licenses/metadata/lists.** This is the same picture as `DATA-AUDIT.md` §3/§5.

---

## 2. Recommended bucketing rule (content-only, deterministic, cheap)

Implemented in `bucket_probe.py` (`bucket_of`). Input: a window's 256 token ids
only — works identically on aligned windows, on `train.py`'s random-offset
training windows, and on held windows, so train/held assignment can never
disagree about a window's bucket. Pure function, no state, no RNG. Cost: one
256-token decode + a few passes over ~1.3k decoded chars ≈ **0.9 ms/window**
single-threaded (20,706 windows bucketed in ~19 s in the probe).

Priority order, first match wins:

| # | Bucket | Rule (on the decoded window, BOS tokens excluded from text) |
|---|---|---|
| 1 | **numeric** | digit share of decoded chars ≥ 0.30 |
| 2 | **gibberish** | count of literal `Ġ`+`Ċ` chars ≥ 8, **or** non-ASCII share ≥ 0.20 (excluding box-drawing U+2500–U+257F, so ASCII-art diagrams in docs don't count) |
| 3 | **german** | German function-word rate ≥ 0.05 of words **and** > English function-word rate (word lists in `bucket_probe.py`) |
| 4 | **lists** | BOS count ≥ 28 (very short lines: name lists, `entry_points`/`top_level`, heading-dense templates) |
| 5 | **prose** | residual — English markdown/docs/licenses |

Why these signals:

- **Ġ/Ċ is a nearly free gibberish detector.** Ordinary text decodes with no
  Ġ at all (the tokenizer renders spaces as spaces). Ġ/Ċ appear as literal
  characters only when a `merges.txt` file *is* the content. The bucket share
  it produces (54.2%, §3) independently matches the replay-measured merges
  share of the corpus (54.1%) — two unrelated methods agreeing.
- **Digit share** cleanly separates the scipy float dumps: windows with digit
  share ≥ 0.5 almost always have BOS count 0–1 (a single mega-line fills the
  whole window). The 0.30 threshold also catches numeric *tables* in docs,
  which are genuinely numeric in content.
- **German function words** (`der/die/das/und/ist/…`) separate the Tatoeba
  sentences with a wide margin (observed rates 0.22–0.37 vs threshold 0.05).
  It is checked *after* gibberish because merges fragments randomly spell
  German-looking words.
- **A standalone CODE bucket was tested and rejected.** Code-keyword-dense
  windows are ~0.1% of the corpus and fence-bearing windows ~0.9% — and what
  exists is documentation *about* code inside venv READMEs (e.g. Typer docs),
  not code. There is no code specialty in this corpus to tilt toward.

---

## 3. Prototype results (20,000 evenly spaced aligned windows of 23,114)

| Bucket | Windows | Share |
|---|---|---|
| numeric | 4,981 | 24.9% |
| gibberish | 10,844 | 54.2% |
| german | 1,401 | 7.0% |
| lists | 54 | 0.3% |
| prose | 2,720 | 13.6% |

Spot-checks (~10 windows per bucket, read by eye from the probe output):

- **numeric — pure.** 10/10 are float matrices or numeric result tables
  (scipy `pdist-*` dumps, sklearn description tables, lab result tables).
  This is a real, homogeneous content class.
- **gibberish — pure, one boundary case.** 9/10 are solid merge-table salad
  (`Ġfollow ed`, `ĠĠĠĠ`, fragment pairs). 1/10 (window 4308) is a *straddle*
  window: it starts as English prose and the merges file begins mid-window
  (Ġ count 32) — correctly labelled by majority content. Straddle windows are
  bounded by the number of file boundaries (≤393, ~1.7% of windows worst case).
- **german — pure.** 10/10 are fluent German Tatoeba prose (traffic-light
  news, theatre reviews, tax articles). The one genuinely language-like
  specialty in the corpus.
- **lists — real format, negligible size.** The 10 shown split between
  AUTHORS name lists (pip's contributor list) and heading-dense HuggingFace
  model-card templates full of `[More Information Needed]`. A real
  short-line/structured class, but at 0.3% it is not a specialty — it's a
  rounding error.
- **prose — clean but heterogeneous.** 10/10 are readable English (HiveMIND
  handoffs/reports). The residual also contains license boilerplate and
  package READMEs further along the stream, so "prose" is a grab-bag held
  together by being English and not fitting the rules above — the least
  specialty-like of the large buckets.

---

## 4. CRITICAL hygiene check: per-bucket held slices

Held rule replicated exactly from `train.py`: aligned windows `w` with
`w % 40 == 0` are held candidates (578 of them); the standard judged set is
128 of those picked evenly (`starts[int(i·(len−1)/127)]`). Bucketing each
held window with the same content-only rule:

| Bucket | Of 578 held candidates | Of the standard 128 judged |
|---|---|---|
| numeric | 144 | 32 |
| gibberish | 313 | 69 |
| german | 40 | **9 — <20, too few** |
| lists | 3 | **0 — unmeasurable** |
| prose | 78 | **18 — <20, too few** |

**Plainly: on the standard 128-window judged set, only numeric and gibberish
have enough held windows for a per-bucket held loss.** German (9) and prose
(18) per-bucket losses on that set would be noise; lists (0) cannot be
measured at all. If per-bucket measurement is needed, define the per-bucket
held slices from **all 578 every-40th candidates** instead of the 128 pick —
that gives numeric 144 / gibberish 313 / german 40 / prose 78, usable for the
four real buckets, and lists is still dead (3). Any tilt comparison must
also keep the caveat from `DATA-AUDIT.md` §4: ~31% of corpus pieces are exact
duplicates, so held content leaks into training windows and all v1 held
losses are flattered; arm-vs-arm (tilt-vs-untilted) comparisons on the same
slices remain valid.

---

## 5. Honest verdict

**The buckets are real as content strata, and mostly mush as "specialties."**

- As *strata*, the rule works better than expected: numeric, gibberish and
  german are each ~pure by eye, deterministic, and cheap; the gibberish
  share cross-validates against the independent source replay (54.2% vs
  54.1%). Nothing about the bucketing machinery blocks the overlap program.
- As *specialties to tilt a generalist toward*, v1 offers: one language
  (German, 7%), one residual English grab-bag (prose, 13.6%), and two
  artifact classes that `make_corpus_v2.py` exists specifically to delete
  (merge-table gibberish 54.2%, numeric dumps 24.9%). **A tilt experiment run
  on v1 would mostly measure how well a model can be tilted toward tokenizer
  tables and float matrices** — 79.1% of its tokens are those two buckets.
- **Recommendation:** do not build the tilt program on v1 buckets. Either
  (a) run it on corpus-v2, where the natural content buckets are German
  sentences (45.7%) vs HiveMIND docs vs edit-lab notes (v2's own
  `per_category` in `corpus-v2/corpus-v2.json`) — all real text, though v2 is
  only 0.91M pieces; or (b) if v1 must be used for comparability with the
  existing series, restrict tilt claims to the german-vs-prose contrast,
  measure per-bucket loss on the full 578-candidate held slices, and treat
  numeric/gibberish tilts as artifact-fitting controls, not specialties.
  Drop the lists bucket either way (0.3%, 0 held windows).

*Method: source replay and window features measured directly on `corpus.u16`
with the lab's tokenizer; held sets replicated from `train.py`'s
`held_windows` logic without modifying it. `runs.jsonl`, `run_scale_ladder.py`
and `train.py` were not modified.*
