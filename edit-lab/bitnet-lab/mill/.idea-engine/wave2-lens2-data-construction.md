# Muse's work — Muse's side

# Wave G · Lens 2 — DATA CONSTRUCTION: how training sequences are built and ordered (Muse's work, Muse's side)

<!-- Idea Engine wave 2, miner 2 — data-construction lens. Muse's side of the BitNet lab only;
nothing here touches Fable's side. CANDIDATE file: nothing here is in the pool until the pool's
owner merges it. Deduped in full against mill/IDEA-POOL.md, CANDIDATES-A/B/C/D/E/F,
FABLE-CANDIDATES.md and bitnet-lab/DATA-AUDIT.md. -->

## Grounding: what the current construction actually is (train.py, verified)

- `offsets(rnd, n, batch)` draws **uniform random byte-offsets with replacement**, rejecting only
  offsets whose 256-piece window touches a held block (`(i // CTX) % 40 == 0` at either end).
  There is no stride, no tiling, no packing, no order, no coverage guarantee, and no spacing
  between similar windows. A window is a blind slice of the stream: it starts mid-line, crosses
  every BOS boundary inside it, and ends mid-line.
- Corpus-v2 (DATA-AUDIT §7): 907,409 unique pieces, 20,848 unique lines, median line 36 pieces —
  so a 256-piece window crosses **~7 line boundaries** and typically splices fragments of several
  unrelated documents. Mix: German sentences 45.7%, HiveMIND docs 41.9% (28.8% Muse side +
  13.1% Fable side, read as data only), edit-lab notes 12.4%.
- Corpus-v3 has landed (`corpus-v3/corpus-v3.u16`, ~21.4M pieces): Gutenberg public-domain books +
  WikiText-103, built with v2's filter discipline plus a held-line leak guard (any line appearing
  inside a v1/v2 held window was dropped at build time). Its lines are book paragraphs — far longer
  than v2's — so v2's construction questions do not transfer automatically.
- Champion: layered_half + rotary, held **2.8580 ± 0.0161** (v1 stream). Objective stays next-token
  CE everywhere below — no JEPA-style objective changes (closed). Masking a target position out of
  the CE sum is a construction change, not an objective change: the loss is still next-token CE on
  the positions that remain.

## Deliberately NOT re-proposed (taken, per the dedupe pass)

B-001 staged mixture *ratios* (this file varies order at **fixed** ratios — DC-004/DC-007 say where
they differ), B-002/B-003 tokenizer refits, B-005/B-006/B-008 filtering, B-007 document MinHash
dedup, B-009 epoch scaling, B-010/B-011 rewrite/synthetic slices, B-012 DoReMi weights,
A-041/42/43 loss-ordered curricula, A-044 paired repetition, A-045/46 monotone ctx-length
curriculum (DC-010 is the *stationary* mixed-length distribution, not a schedule), A-047
near-duplicate window *removal* (DC-008 keeps the windows and spaces them), A-048 per-file
mixture reweighting, A-049 frequent-token downweighting, A-050 the ±2 **positional** held buffer
(DC-003 is content-based and wider), A-051 cyclic-shift augmentation (DC-011 pads, never wraps),
A-052 span-noise input corruption, A-053 the ≥8-files-per-batch diversity floor (DC-004 fixes the
alternation *period* of source classes), A-054 regression weighting, A-055 coverage-*weighted*
sampling (DC-009 is a strict without-replacement deck), A-056 worst-2% trim, MILL-406/407
failweight, D-001/D-007 replay, F-032 junk-first curriculum, F-048 repetition-discounted *votes*
(trainer-side; DC-008 is sampler-side spacing), E-018/19/20/21 corpus rebuilds and excisions
(DC-003 is a sampler exclusion that needs no rebuild).

**Chassis** unless an entry says otherwise: layered_half + rotary, V=32, batch 32, ctx 256,
probe = 75 s / seed 0 vs job zero, trial = 3 seeds × 8 min, adoption >2 sd and >0.01.
All entries are `mode: process` honestly: every one changes `offsets()` or the batch builder,
which train.py does not expose as a flag today.

---

### DC-001 · Boundary-masked line packing ★
- **source:** data-construction derivation from DATA-AUDIT §7 + train.py's slicing — v2's median
  line is 36 pieces, so the champion's windows each splice ~7 unrelated line/document fragments
  and train full CE on the seams: the model is paid to predict the first tokens of a lab note
  from the tail of a German sentence. No pooled entry touches packing at all (the architecture
  report's do-not-test list even set packing aside as "kernel-only" — for the vote trainer it is
  an evidence-quality question, not a kernel question).
- **mechanism:** Build windows by **packing whole lines** in stream order until 256 pieces are
  filled (last line truncated only if it alone exceeds 256), and **mask out of the CE sum** every
  target position whose prediction crosses a line start — i.e. the first target after each BOS
  inside the window contributes no loss and no gradient. All other positions train exactly as
  champion. The vote stream then integrates only within-document evidence; seam positions stop
  casting systematically misleading votes ~7 times per window.
- **exact change:** corpus-builder + runner change — `make_corpus_v2.py` variant emits a
  line-boundary sidecar for the stream; train.py gains `--pack-mask` (batch builder packs from
  the sidecar instead of slicing offsets; CE computed with a per-position mask). Applies to v2
  first; v3 form is DC-012's territory.
- **mode:** process
- **prediction:** −0.02..−0.06 at trial scale on v2-native held. Reasoning: ~7/256 ≈ 3% of
  positions are seam targets, but they are the *highest-loss, most contradictory* positions in
  every window — exactly the gradients whose signs disagree batch-to-batch and cancel inside
  the counters. Removing them should raise flip efficiency (fewer wasted votes) measurably:
  log flip share and counter-reversal rate alongside held.
- **contamination control:** packing draws lines only from the non-held side — any line that
  appears inside a held block (exact-line match, the v3 builder's test) is excluded from the
  pack stream, and held windows are constructed exactly as today (every-40th block, unpacked)
  and never packed, masked, or trained on. Runner asserts `packed_held_overlap = 0` per run.
- **status:** queued
```mill
id: DC-001
mode: process
run: --arm layered_half --rope --corpus v2 --pack-mask
```

### DC-002 · Sequential stream walk (read the corpus, don't sample it) ★
- **source:** data-construction derivation — `offsets()` is i.i.d. sampling and has never been
  varied in any record the lab owns; every curriculum entry (A-041ff) reorders *scored windows*
  but keeps i.i.d. draws underneath. A vote counter is an integrator with a ~32-vote memory:
  the *temporal coherence* of its evidence stream is a property of the sampler, and i.i.d.
  sampling is the zero-coherence extreme.
- **mechanism:** Replace i.i.d. offsets with a **contiguous walk**: the run reads the legal
  (non-held) stream in order, one non-overlapping 256-piece tile after another, batch = 32
  consecutive tiles, reshuffling tile order only at pass boundaries (two arms in one entry:
  strict stream order, and per-pass shuffled tiles — the pair separates "contiguity within the
  batch" from "global order"). Each legal piece is seen exactly once per pass.
- **exact change:** train.py flag `--sampler stream|stream-shuffled` replacing the `offsets()`
  call in the training loop; tiles are the stream cut at fixed 256 boundaries, held tiles
  skipped by the same predicate `offsets()` uses today.
- **mode:** process
- **prediction:** −0.01..−0.05 for stream-shuffled; strict stream order is the high-variance
  arm (local topics give counters long agreeing runs — fast early flips, but German-only
  stretches are a forgetting risk, read against DC-007). Diagnostic either way: flip share in
  the first 25% of steps vs the i.i.d. champion — coherence should show there first.
- **contamination control:** the walk enumerates only tiles that pass the existing held
  predicate (a tile is legal iff neither its first nor last block index is ≡ 0 mod 40, the
  `offsets()` test applied to tile boundaries); held tiles are skipped, never split, and the
  runner logs `tiles_total / tiles_held_skipped` and asserts no trained tile overlaps a held
  block.
- **status:** queued
```mill
id: DC-002
mode: process
run: --arm layered_half --rope --sampler stream-shuffled
```

### DC-003 · Content-based held moat: 8-gram exclusion + ±16-block positional moat ★
- **source:** DATA-AUDIT §4 (held content routinely recurs in training windows on v1) +
  A-050's known limit — A-050 excludes only windows within ±2 *positions* of a held window,
  but duplication in this corpus is **content-scattered, not position-local**: a held window's
  lines recur hundreds of blocks away (license text, repeated report scaffolding), where a
  positional buffer never looks. E-019 prices this by rebuilding v1; this entry enforces it in
  the sampler, on any corpus, with no rebuild.
- **mechanism:** A training offset is legal only if (a) its window shares **no 8-token shingle**
  with any held window (shingle sets precomputed once per corpus, charged to wall-clock), and
  (b) it sits at least **16 blocks** from the nearest held block. Everything else is champion.
  On v2 (all lines unique) the shingle test should exclude almost nothing beyond the positional
  moat — that near-zero count is itself the verification that v2 held numbers are clean; on v1
  the excluded fraction prices the leak in sampler units.
- **exact change:** train.py flag `--held-moat 16,8` in `offsets()` (shingle index built at
  runner start from the held windows only; legality test replaces the current two-endpoint
  predicate). No corpus file is modified.
- **mode:** process
- **prediction:** On v1: held worsens by +0.02..+0.10 vs 2.8580 — a *worse* number that is the
  deliverable (the honest v1 reference, complementing E-018's v2 number). On v2: held within
  ±0.01 of the v2 re-baseline (E-018) if v2 is as clean as its build log claims. Any v1 arm
  whose margin over champion is smaller than this entry's Δ must be re-read.
- **contamination control:** this entry *is* the contamination control. The shingle test runs
  against the exact 128 held windows used for judging (not a proxy set), the exclusion is
  applied before any training draw, and the runner logs `offsets_rejected_shingle`,
  `offsets_rejected_moat`, and asserts a post-hoc audit pass over every offset actually
  trained on returns zero held-shingle collisions.
- **status:** queued
```mill
id: DC-003
mode: process
run: --arm layered_half --rope --held-moat 16,8
```

### DC-004 · Mixture-order period sweep on v2 (fixed ratios, three alternation periods)
- **source:** data-construction lens on v2's actual mix (German 45.7% / HiveMIND docs 41.9% /
  lab notes 12.4%, DATA-AUDIT §7). B-001 changes mixture *ratios* across coarse stages;
  A-053 imposes a per-batch file-diversity floor. Neither varies the **period** at which
  sources alternate inside a run at fixed global ratios — and period is the variable a vote
  counter is most sensitive to, because a 16-step single-source block lets one source's
  evidence climb counters uninterrupted, then the next source's block votes against it.
- **mechanism:** Three arms, identical v2 mixture ratios, identical total tokens: (a) fully
  shuffled offsets (champion-equivalent control), (b) **batch-grain round-robin** — each batch
  of 32 is composed ~15 German / ~13 HiveMIND / ~4 lab-note windows, every batch, (c)
  **block-grain rotation** — 16 consecutive steps draw from one source only, rotating
  German → HiveMIND → lab. The (b)-vs-(c) gap at fixed ratios is the pure order effect.
- **exact change:** train.py flag `--mix-order shuffle|batch|block16` (sampler partitions
  legal offsets by source class using the v2 build's per-file provenance; batch builder
  composes per arm). Source tags come from `corpus-v2.json`, no corpus rebuild.
- **mode:** process
- **prediction:** batch-grain beats shuffled by −0.01..−0.04 and beats block16 by −0.02..−0.05:
  per-batch source balance makes every vote a vote on the full mixture, while block16 spends
  its middle steps un-flipping the previous block's structure (watch cross-block flip-reversal
  rate — predicted highest in (c)). If all three tie, within-run order is a dead axis at this
  scale and B-001's stage question is the only mixture question left.
- **contamination control:** source partitioning is applied to legal offsets only — the held
  predicate runs first, per source, and each source's sampler asserts zero held-block overlap
  independently, so no source arm can re-admit a held window the unified sampler would reject.
- **status:** queued
```mill
id: DC-004
mode: process
run: --arm layered_half --rope --corpus v2 --mix-order batch
```

### DC-005 · Stride-64 overlap lattice (each token testifies at four positions)
- **source:** data-construction derivation — with random offsets, a token's *position inside
  its window* is whatever chance assigns, and most corpus positions are never sampled at all
  in a ~160-step run (5,120 windows over 907k v2 pieces ≈ 1.4 passes, unevenly). Overlap and
  stride have never been set deliberately; the architecture report excluded packing/kernel
  ideas but never priced designed overlap for a vote trainer.
- **mechanism:** Tile the legal stream at **stride 64** (256-piece windows overlapping by
  75%): every token appears in exactly 4 windows, at 4 different window positions (p, p+64,
  p+128, p+192 phase classes). Windows are dealt in shuffled lattice order at equal *steps*
  to champion (so tokens-seen is matched; unique-token coverage per run falls 4× — that trade
  is the measurement, stated plainly, against A-055/DC-009's coverage pole).
- **exact change:** train.py flag `--stride 64` (offsets restricted to the stride-64 lattice
  over legal starts; legality = the window passes the held predicate at both ends, as today).
- **mode:** process
- **prediction:** −0.01..−0.04 at equal steps if position-phase diversity is the active
  ingredient (the same text voting from four RoPE phases is four partially independent
  witnesses — the counter integrates them like extra data); +0.02..+0.05 if unique coverage
  dominates, which would jointly confirm DC-009's premise from the opposite side. The pair
  DC-005/DC-009 brackets the overlap dial with the champion in the middle.
- **contamination control:** lattice starts are filtered by the unchanged held predicate
  *before* dealing — any lattice window whose span touches a held block is removed from the
  lattice entirely (not shifted to a legal neighbour, which would silently change the stride),
  and the removed count is logged.
- **status:** queued
```mill
id: DC-005
mode: process
run: --arm layered_half --rope --corpus v2 --stride 64
```

### DC-006 · BOS-anchored window starts (position 0 is always a real beginning)
- **source:** data-construction derivation from v2's line structure — random offsets start
  ~255/256 of windows mid-line, so position 0's statistics are "arbitrary mid-document
  token," and the carried position table + RoPE spend their early positions on fragments.
  No entry constrains *where in a line* a window may start.
- **mechanism:** Window starts are restricted to **BOS positions** (line starts) in the legal
  stream: every window opens with a genuine document/line onset and its first line is whole.
  Control arm in the same entry: anti-anchored starts (starts at line-midpoint ±0 only) —
  the pair prices anchoring itself rather than any particular text. Token budget, ratios,
  and all else champion.
- **exact change:** train.py flag `--anchor bos|mid` in `offsets()` (legal-start set
  precomputed from the stream's BOS positions; the held predicate applied to the anchored
  start exactly as to a random one).
- **mode:** process
- **prediction:** −0.01..−0.03 for BOS-anchored. The effect should concentrate in early-position
  loss (log per-position held loss: positions 0–31 improve most). If the anti-anchored control
  matches it, start-phase is irrelevant and DC-011's dither premise dies with it — the entry
  is designed to be decisive for both.
- **contamination control:** anchoring never relaxes exclusion — an anchored start is legal
  only if its full window passes the existing held predicate, and BOS positions *inside* held
  blocks are excluded from the start set at construction (asserted count logged).
- **status:** queued
```mill
id: DC-006
mode: process
run: --arm layered_half --rope --corpus v2 --anchor bos
```

### DC-007 · German placement on v2: first, last, or interleaved (the majority-source order test)
- **source:** v2-specific construction (DATA-AUDIT §7): 45.7% of the clean corpus is one
  language (German Tatoeba sentences) and 54.3% is English project prose. F-032 orders *junk
  vs clean*; B-001 stages *ratios*. Nobody has placed a single dominant source at different
  run positions at fixed ratio — and for a vote counter the placement question is a forgetting
  question: does the last-seen source's structure overwrite the first's, since late flips face
  no further counter-evidence?
- **mechanism:** Three arms at the identical 45.7% German share: (a) German block first
  (steps 0–46% German-only, then English-only), (b) German block last, (c) shuffled control.
  Judged on the pooled v2 held **and** on per-source held slices (German-majority held windows
  vs English-majority held windows reported separately) — the slice gap is the mechanism's
  signature, the pooled number alone cannot see it.
- **exact change:** train.py flag `--src-place de-first|de-last|shuffle` (sampler-level, v2
  provenance tags as in DC-004; per-source held slicing is an eval-side tag on the standard
  held windows, no new held data).
- **mode:** process
- **prediction:** de-last wins the German slice by ≥0.08 over de-first and loses the English
  slice by a smaller margin; pooled, de-last −0.01..−0.03 vs shuffled if recency dominates,
  or shuffled wins pooled if interference is symmetric. Any of the three outcomes sets the
  default ordering policy for every future multi-source corpus (v3 included).
- **contamination control:** both blocks draw only from offsets passing the held predicate
  within their own source partition; the per-source held slices are a *tagging* of the same
  untouched 128 held windows, so no held window is ever trained on in any arm and slice
  membership cannot leak into sampling.
- **status:** queued
```mill
id: DC-007
mode: process
run: --arm layered_half --rope --corpus v2 --src-place de-last
```

### DC-008 · Duplicate-adjacency spacing: near-dupes must wait 32 steps (kept, not removed)
- **source:** data-construction derivation from DATA-AUDIT §4 — on v1, 30.8% of pieces are
  exact-duplicate copies and i.i.d. sampling deals near-identical windows back-to-back by
  chance; for a counter, two identical windows 3 steps apart are not two witnesses, they are
  one witness counted twice at full strength, and they can push a weight across V=32 on what
  is effectively a single observation repeated. A-047 *removes* near-dupes, F-048 *discounts
  their votes* inside the trainer — neither keeps the data and fixes only its **spacing**.
- **mechanism:** The sampler keeps a last-dealt step per 8-gram shingle signature; a candidate
  window sharing any signature with a window dealt in the previous **32 steps** is deferred
  to a holding queue and dealt only after the gap clears (never dropped; total tokens and
  window multiset identical to control by construction — only the order changes).
- **exact change:** train.py flag `--dup-gap 32` (sampler wrapper around `offsets()` with a
  signature ring buffer; deferral queue drained in FIFO order whenever the gap allows).
- **mode:** process
- **prediction:** On v1: −0.01..−0.04 vs champion (spacing breaks up duplicate vote-storms;
  watch the flip-reversal rate fall). On v2: ~0 expected — v2 has no duplicate lines, so a
  v2 win would falsify the mechanism and indict shingle collisions instead; run v1 first,
  v2 as the built-in negative control.
- **contamination control:** spacing operates only on the legal-offset stream (held predicate
  applied upstream, unchanged); deferral never substitutes a replacement window from outside
  the legal set, and the queue is flushed by re-dealing deferred legal windows, so no held
  window can enter through the spacing machinery.
- **status:** queued
```mill
id: DC-008
mode: process
run: --arm layered_half --rope --dup-gap 32
```

### DC-009 · Without-replacement epoch deck (every legal window exactly once per pass)
- **source:** data-construction derivation — `offsets()` samples **with replacement**: at
  trial scale (160 steps × 32 = 5,120 draws) some windows are drawn 3+ times while a large
  share of the legal stream is never drawn, purely by birthday-paradox arithmetic. A-055
  *weights* unseen windows higher but still samples with replacement, so collisions persist;
  B-009 counts epochs but keeps the same sampler. The strict deck has never been run.
- **mechanism:** Enumerate all legal block-aligned starts once, shuffle them into a deck,
  deal without replacement; reshuffle a fresh deck only when the first is exhausted. At
  probe/trial scale on v2 this guarantees maximum unique coverage per step — the exact
  opposite pole from DC-005's designed overlap, with the champion's i.i.d. sampler between
  them.
- **exact change:** train.py flag `--sampler deck` (deck built at runner start from legal
  starts; seed-disciplined shuffle via the run's own RNG stream, per the dream protocol's
  seed rules).
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale, growing with run length (the with-replacement
  waste compounds: by 5,120 draws ~35–40% of v2's legal windows are expected undrawn under
  i.i.d.). At probe scale (~800 draws) the gap should be small — a probe win is not required,
  a probe *loss* >0.02 kills it.
- **contamination control:** the deck is enumerated from legal starts only (held predicate
  applied at enumeration, before shuffling); reshuffles re-enumerate from the same legal set,
  and the runner asserts deck ∩ held = ∅ by construction check on the start list.
- **status:** queued
```mill
id: DC-009
mode: process
run: --arm layered_half --rope --corpus v2 --sampler deck
```

### DC-010 · Stationary mixed context lengths (ctx drawn per batch: 64 / 128 / 256)
- **source:** data-construction derivation — A-045/46 test a monotone ctx *curriculum*
  (thirds of the run at one length each). The untested alternative is a **stationary mixture**:
  every batch independently draws its ctx from {64, 128, 256} uniformly, for the whole run.
  The two designs differ exactly where it matters for votes: the curriculum confounds length
  with run phase (early flips only ever see short contexts), the mixture does not.
- **mechanism:** Per-batch ctx ∈ {64, 128, 256} (mean 149 pieces/window — step-matched *and*
  token-matched controls are both reported; primary verdict at equal steps, per the lab's
  step-currency lesson from F-038). Position distribution shifts by design: positions 0–63
  receive 3× the gradient exposure of positions 192–255. Final judging is always at ctx 256
  on the standard held windows.
- **exact change:** train.py flag `--ctx-mix 64,128,256` (batch builder slices each drawn
  window to the batch's drawn length; RoPE buffers already span 256; no model change).
- **mode:** process
- **prediction:** −0.01..−0.03 at equal steps if early-position undertraining is real (at fixed
  ctx 256 every position trains equally per window, but short-window structure — the local
  syntax the first blocks must learn — is diluted across 256 positions of loss). If it ties
  A-045's curriculum arm, phase-confounding was harmless; if it beats it, the curriculum
  family's readings need the stationary control before any adoption.
- **contamination control:** slicing never extends a window — a mixed-ctx window is a prefix
  of a legal full-length draw, so its legality is inherited from the parent draw's held
  predicate; truncated windows are never re-padded from neighbouring (possibly held) text.
- **status:** queued
```mill
id: DC-010
mode: process
run: --arm layered_half --rope --ctx-mix 64,128,256
```

### DC-011 · Position-phase dither by masked left-pad (same text, new RoPE phase, no wrap)
- **source:** data-construction derivation — A-051 cyclically *rotates* a window's tokens
  (tail wraps to head: token adjacency is destroyed at the seam and every token keeps a
  neighbour it never had). The gentler transform nobody has tried: shift the window's content
  right by k ∈ {0..31} **masked pad positions** — adjacency fully preserved, nothing wraps,
  the content simply sits at a different absolute phase for RoPE and the carried position
  table. Pad positions carry no loss and no targets.
- **mechanism:** Each drawn window is left-padded by a fresh uniform k per window per visit,
  so across a run the same passage votes from up to 32 different absolute phases. This directly
  attacks absolute-phase overfitting in a chassis that carries *both* rotary and a (dormant
  under `--rope`) position table — phase-locked memorisation is a plausible hidden tax on a
  0.91M-piece corpus seen repeatedly.
- **exact change:** train.py flag `--pad-dither 31` (sampler transform in the batch builder;
  pad token = BOS id with its target positions masked out of the CE sum — construction-side
  masking as in DC-001, objective unchanged).
- **mode:** process
- **prediction:** −0.01..−0.03, largest on v2/v1 where repetition makes phase-locking
  learnable; ~0 on v3's 21M pieces (too little repetition to phase-lock — v3 is the negative
  control). Read against A-051: if pad-dither ≥ cyclic-shift, adjacency preservation was the
  active ingredient; if cyclic wins, the wrap seam was harmless and phase diversity alone
  explains both.
- **contamination control:** the transform is applied *after* the held predicate, to the
  drawn window only — padding adds no corpus tokens, shifts no offsets, and cannot pull held
  text into a training window; the underlying draw's legality is asserted before padding.
- **status:** queued
```mill
id: DC-011
mode: process
run: --arm layered_half --rope --pad-dither 31
```

### DC-012 · Corpus-v3 book-block order (whole books as the unit of order)
- **source:** corpus-v3 construction (make_corpus_v3.py; ~21.4M pieces, Gutenberg books +
  WikiText-103) — v3's documents are *books*: single sources run to hundreds of thousands of
  pieces, so "order" on v3 has a grain v2 never had. The first v3 series will pick an ordering
  by default (whatever the sampler happens to do); this entry makes that choice a measured
  one before it hardens into the v3 baseline every later arm is judged against.
- **mechanism:** Three orderings at fixed v3 mixture: (a) i.i.d. offsets (default control),
  (b) **book-block walk** — books taken one at a time in ascending length order (short books
  first: the only curriculum here is document length, not loss or difficulty), read
  contiguously within each book (DC-002's walk at book grain), WikiText interleaved at its
  natural share between books, (c) book-block walk in *descending* length order (control for
  (b)'s direction). Long coherent documents give counters multi-thousand-step agreeing
  evidence runs that v2's 36-piece lines never could.
- **exact change:** runner change — new companion runner flag `--v3-order iid|book-asc|book-desc`
  (book boundaries from the v3 build's per-category source table; v3-native held windows per
  the E-018 pattern on the v3 stream). Requires the `--corpus v3` path (same dependency as
  E-018's v2 path).
- **mode:** process
- **prediction:** book-asc beats i.i.d. by −0.02..−0.05 at ladder format on v3 (coherence is
  worth more, not less, as documents lengthen — the DC-002 mechanism at its natural scale);
  book-desc within ±0.02 of book-asc if only contiguity matters, worse by ≥0.03 if the
  short-first direction itself earns. Full-trial/ladder format only — a 75 s probe sees a
  fraction of one book and cannot read this.
- **contamination control:** v3 was built with a held-line leak guard (every line appearing
  inside a v1/v2 held window was dropped at build time, and global line dedup prevents any
  line repeating); on top of that, the v3 series' own held windows are excluded by the
  standard predicate in all three arms, book walks skip held blocks inside a book rather
  than splitting the book around them, and the runner asserts zero overlap between dealt
  windows and v3 held windows per arm.
- **status:** queued
```mill
id: DC-012
mode: process
run: --arm layered_half --rope --corpus v3 --v3-order book-asc
```

---

## Miner's ranking note

The construction layer is the least-owned territory in the lab: the sampler has exactly one
form in every record (`offsets()`, i.i.d., blind slices), while the trainer above it has
hundreds of pooled variants. My top 3 are the three that change what a *vote is evidence of*:
**DC-001** stops ~7 seam positions per window from casting contradictory votes at all;
**DC-002** tests whether evidence *coherence in time* — the property an integrator is built
to exploit — has been sitting at zero by accident; **DC-003** is the integrity entry, the one
whose (possibly worse) number every other v1 verdict silently depends on. DC-004/DC-007 are
the cheapest decisive pair in the file (same flags, two questions about v2's real mixture),
and DC-005/DC-009 are a designed bracket: designed overlap vs guaranteed coverage, champion
in the middle — whichever way they land, the overlap dial gets its first two measurements.

*End of wave-G lens-2 (data construction). 12 entries, DC-001..DC-012, all queued, all
process mode, none duplicating IDEA-POOL.md or CANDIDATES-A/B/C/D/E/F.*
