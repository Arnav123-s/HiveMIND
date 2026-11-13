# Muse's work — Muse's side

# Wave 6 · Lens 1 — FIRST DATA: what corpus-v3 makes possible, and what it breaks (Muse's work, Muse's side)

<!-- Idea Engine wave 6, rotation-6 miner 1 — first-data lens. Muse's side of the BitNet lab
only; nothing here touches Fable's side. CANDIDATE file: nothing here is in the pool until the
pool's owner merges it. Deduped against mill/IDEA-POOL.md, CANDIDATES-A/B/C/D/E/F/G/H/I/J and
FABLE-CANDIDATES.md. This file extends, and does not repeat: E-018 (v2 re-baseline — FD-001 is
its v3 successor, FD-003/J-040 own the cross-corpus matrices), J-013 (what fraction of the v1
headline is junk windows — FD-004 is the v3-native version of that suspicion, at document
grain), J-037/J-042 (leak pricing on v1 — FD-004/FD-006 price v3's two *new* leak shapes). -->

## Grounding (verified at filing time)

- **v1:** 5,917,236 pieces, of which ~0.91M unique real text (DATA-AUDIT: 30.8% exact-duplicate
  pieces, ~23% numeric dumps, merge-table gibberish as the largest sources, median line 9 pieces).
- **v2:** 907,409 pieces, 20,848 unique lines, median line 36 pieces. Honest, tiny.
- **v3 (as landed, per the build record):** ~21.4M pieces — Project Gutenberg public-domain books
  + WikiText-103, built by `make_corpus_v3.py` with v2's filter discipline plus two additions:
  Gutenberg header/footer stripped at the START/END markers, and a **held-line leak guard**
  (every line appearing inside a v1/v2 held window — 18,706 segment keys — dropped at build
  time; global exact line dedup on top). Same hive BPE tokenizer (vocab 4096), same
  BOS-per-line uint16 stream format.
- **Champion:** layered_half + rotary + plain votes, 884,736 ternary weights, ~1.73M total
  params, held **2.8580 ± 0.0161** — denominated in v1. Every prior wave's verdict is.
- **The economics that frame this whole file:** one full pass over v3 at batch 32 × ctx 256
  (8,192 pieces/step) is **~2,613 steps**. Against the ~20 pieces/param rule of thumb, one v3
  pass funds ~1.07M total params — i.e. **v3 is a champion-sized corpus, not a big-rung
  corpus**: pieces per total param for one pass are ~12.4 (champion), ~6.6 (2M rung,
  3,252,096 total), ~1.8 (10M rung, 11,686,400 total), ~0.40 (50M rung, 52,958,976 total).
  A standard trial (160 steps ≈ 1.31M pieces) now samples only ~6% of the corpus, all fresh —
  on v1/v2 the same trial recycled the unique stream ~1.4×.
- **Two builder facts the entries below lean on, both measured, not assumed:** (1) Gutenberg
  plain text is **hard-wrapped** — median line 67–69 chars on pg1342/pg11/pg2600 (~11–13 BPE
  pieces), while WikiText lines are real paragraphs (median 395 chars on the first 20k lines).
  Under BOS-per-line tokenization, the Gutenberg share therefore gets a BOS **mid-sentence
  every ~12 pieces**; the two sources enter the stream under two different line semantics.
  (2) The builder feeds **all three** WikiText files — `wiki.train.raw`, `wiki.valid.raw`,
  `wiki.test.raw` — into the training stream. WikiText-103's test split is the canonical
  external judge for exactly this corpus family; inside v3 it is training text.
- **Plumbing fact:** `train_next.py --corpus v3` does not currently resolve to
  `corpus-v3/corpus-v3.u16` (its candidates are `corpus-v3.u16` and `v3.u16` at lab root, and
  `corpus-v2/corpus-v3.u16`). Every FD entry inherits FD-001's one-line resolver fix.

**Chassis** unless an entry says otherwise: layered_half + rotary, V=32, batch 32, ctx 256,
3 seeds. Budgets are quoted in **fixed steps**, not minutes (J-010/J-043's lesson: wall-clock
budgets drift 129–176 steps on this VM). Every prediction states its corpus denomination.
Adoption bar as in PROMOTE.md (>2 sd and >0.01) unless an entry is itself a measurement,
in which case the number is the deliverable.

## ★ Top 3

1. **FD-001 · Corpus-v3 re-baseline** — the E-018 move for the corpus that actually changes
   the lab's ceiling. Until it lands, every v3 idea is denominated in a currency (v1 held)
   the audit already proved is junk-diluted and leak-flattered.
2. **FD-003 · Junk-era transfer** — does a completed v1/v2 phase help or poison v3 training
   at equal total steps? This is the v2↔v3 question stated as one experiment, and its answer
   decides whether the lab's junk-era checkpoints are an asset or a write-off.
3. **FD-005 · De-wrapped Gutenberg (corpus-v3.1)** — the break found in the builder itself:
   v3's Gutenberg half is chopped mid-sentence by hard line wraps under BOS-per-line
   tokenization. A build fix, priced by one paired run, that plausibly taxes every
   Gutenberg-held number the v3 series will ever produce.

---

### FD-001 ★ · Corpus-v3 re-baseline — the champion's first honest number on real text
- **source:** DATA-AUDIT.md §8 + E-018 (the v2 re-baseline, PRIORITIES.md #9) — E-018 converts
  the champion's currency from leaked v1 to clean-but-tiny v2. v3 is the first corpus that is
  clean *and* comparatively large, and no arm has ever been measured on it. This entry is
  E-018's successor, not its repeat: different corpus, different failure modes (FD-004/005/006),
  and per-source slices E-018 never had to report because v2's slices were project dialect.
- **mechanism:** Champion config trained on corpus-v3 with v3-native held windows (the
  every-40th rule on the v3 stream, 128 windows, evenly spaced picks as `held_windows`
  constructs them), judged pooled **and** split Gutenberg-held vs WikiText-held. The split is
  part of the deliverable: v3 is the lab's first two-genre corpus, and a pooled v3 number
  would hide exactly the anatomy J-013/J-047 exposed on v1.
- **exact change:** `train_next.py` corpus resolver gains `LAB / "corpus-v3" / "corpus-v3.u16"`;
  run `--arm layered_half --rope --corpus v3 --steps 160`, 3 seeds, plus a per-source tag on
  the 128 held windows (source of the stream region each window was drawn from) in the eval
  report. No trainer change.
- **mode:** process
- **prediction (denominated in v3 held):** pooled held **3.10–3.45** at 160 steps — worse than
  2.8580 and meaning more: no dump/merge easy wins, no duplicate leakage, and every window
  fresh (the run sees ~6% of the corpus, so nothing is memorized into place). Gutenberg slice
  reads **+0.05..+0.25 worse** than the WikiText slice despite being the "simpler" English —
  the wrap-BOS tax of FD-005 is the predicted reason, and FD-005's paired run is the check.
  A pooled number below 3.0 would say real text at 23× v2's volume is already worth more
  than the junk era's flattery cost; above 3.5, the champion's recipe (tuned entirely on
  junk statistics) transfers worse than anyone has priced.
- **status:** queued
```mill
id: FD-001
mode: process
run: --arm layered_half --rope --corpus v3 --steps 160
```

### FD-002 · The ladder re-run on v3 — the big rungs were starved, not incapable; now feed them
- **source:** DATA-AUDIT.md §6 — at ladder format (56 steps = 458,752 pieces) the 10M/50M
  rungs got 0.039 / 0.009 pieces per param against the ~20 rule, and against v1's 0.91M unique
  pieces the whole corpus was ~2 ladder runs of real data. The audit's verdict was explicit:
  big-rung results are "lower bounds under data starvation, never evidence about the
  architecture's ceiling." C-A01..C-A12 fill the trainer×size×rotary grid *at 56 steps on
  v1*; F-038 re-runs one rung at champion steps *on v1*. Neither re-runs a rung where a
  longer budget is spent on **fresh** data — on v1/v2, 560 steps means ~5 passes over the
  unique stream (B-009's repetition-decay regime); on v3 it is ~21% of one pass.
- **mechanism:** Rungs 2M (dim 288×2) and 10M (dim 512×3), layered+rope, on v3, each at two
  fixed budgets: 56 steps (comparability with the v1 ladder) and **560 steps** (4.59M fresh
  pieces). Plus the 50M shape (dim 768×7) at 56 steps only, as a flip-share diagnostic, not
  a verdict (~91 s/step makes 560 steps a ~14 h claim this entry does not make).
- **exact change:** ladder configs on the v3 stream via FD-001's resolver:
  `--arm layered --rope --corpus v3 --dim {288,512} --layers-n {2,3} --steps {56,560}`,
  2 seeds per cell (3 at 56 steps), flip-share and per-weight flip-count histograms logged
  at both budgets (F-038's instrumentation, reused).
- **mode:** process — full-trial-only; a 75 s probe at 10M sees a handful of steps and
  cannot read a starvation question.
- **prediction (denominated in v3 held):** at 56 steps the v1 ordering replicates
  (10M beats 2M by ~0.2–0.35, both far above FD-001's champion number — fewer steps at
  bigger shapes). At 560 steps the 10M rung improves **−0.25..−0.45** over its own 56-step
  self and the 10M−2M gap **widens ≥2×** — the starvation signature: on fresh data the big
  rung's slope is steeper, where B-009's repeated-data curve would have flattened it. The
  50M diagnostic: flip share stays **≤0.0003/step** even on fresh data (F-043's threshold
  dilution is a V problem, not a data problem — FD-012 tests the interaction directly).
  If instead the gap *narrows* at 560 steps, the audit's starvation reading was wrong and
  the ladder's small-is-better shape prior is a real architecture fact on real text too.
- **status:** queued
```mill
id: FD-002
mode: process
run: --arm layered --rope --corpus v3 --dim 512 --layers-n 3 --steps 560
```

### FD-003 ★ · Junk-era transfer — does a completed v1/v2 phase help or poison v3 training?
- **source:** the v2↔v3 question the context shift forces. WH-039 measures a *mid-run*
  50/50 corpus switch (v1↔v2) and its recovery curve, judged on v2 held; J-040 cross-scores
  a v1↔v2 arm matrix. Neither asks the sequential-training question on v3: the lab owns
  finished junk-era training (every champion/control checkpoint) — is any of it a *starting
  point* for real-text training, or is the only honest v3 run a cold one?
- **mechanism:** Four arms, identical total budget (320 fixed steps), all judged on
  **v3-native held** (FD-001's set): (a) v3-only, 320 steps (control); (b) v2 for 160 steps
  → v3 for 160 steps, full state carried (ternary + counters + FP parts); (c) v1 for
  160 steps → v3 for 160 steps, full state carried; (d) reverse control — v3 for 160 steps
  → v2 for 160 steps, judged on v3 held (what does a junk *finish* do to a real-text start?
  the forgetting direction nobody prices). The (b)-vs-(c) gap separates "clean but alien
  dialect" (v2: project prose + German) from "dirty and alien" (v1: the same, plus dumps,
  merges and duplicates) as pretraining sources.
- **exact change:** runner gains `--pretrain-corpus {v1|v2|v3} --pretrain-steps 160`
  (train on the first corpus, checkpoint full trainer state, swap the stream, continue;
  held set fixed to v3's throughout). Champion chassis, 3 seeds.
- **mode:** process
- **prediction (denominated in v3 held):** (b) lands **within ±0.02 of (a)** — v2's dialect
  and German transfer almost nothing to Gutenberg/WikiText prose, but its clean statistics
  do not actively hurt either; the FP parts' calibration is worth roughly what the ternary
  body's dialect lock-in costs. (c) lands **+0.03..+0.08 worse than (a)**: the junk phase's
  flips (earned on float streams and merge gibberish) must be un-flipped on real evidence,
  and 160 steps is not enough to finish the un-flipping — junk-era pretraining is a small
  poison, not a free warm start. (d) degrades v3 held by **≥+0.10** vs its own step-160
  checkpoint — catastrophic forgetting of real text under a junk finish is fast, which is
  why (c)'s damage is bounded: the same forgetting works *for* the v3 phase there. If (c)
  instead *beats* (a) by >0.02, F-032's junk-as-load-bearing suspicion gains its strongest
  evidence yet, from the transfer direction it never tested.
- **status:** queued
```mill
id: FD-003
mode: process
run: --arm layered_half --rope --corpus v3 --steps 320 --pretrain-corpus v1 --pretrain-steps 160
```

### FD-004 · Document-held re-baseline — the leak guard is line-level; books leak at document level
- **source:** `make_corpus_v3.py`'s held-line leak guard + DATA-AUDIT §4's lesson. The guard
  guarantees no *line* inside a v1/v2 held window enters v3, and global dedup guarantees no
  line repeats inside v3. But v3's own held windows (FD-001's set) are windows **inside
  books and articles whose remaining text is all in training**: same author, same chapter's
  characters and place names, same article's entities, recurring chapter boilerplate. v1's
  flattery was line duplication (J-022 prices it at ~0.5); v3's candidate flattery is
  document co-membership, and no filed entry measures it — G-015's 8-gram moat would catch
  only the near-verbatim part of it.
- **mechanism:** A second, document-level split of v3: hold out **8 whole Gutenberg books
  and 200 whole WikiText articles** (article = the stream region between `= Title =`
  headings) from training entirely; train the champion on the remainder; score the same
  finished model on (i) the standard window-held set (windows inside trained documents)
  and (ii) the document-held set (windows inside never-seen documents). The gap between
  the two numbers, on one model, is the document-leak price.
- **exact change:** corpus variant build `corpus-v3-doc` (source-level exclusion list in
  the v3 builder, same filters) + eval-side `--held-doc` window set; champion run
  `--arm layered_half --rope --corpus v3-doc --steps 160`, 3 seeds, both held sets scored
  at the end of each run.
- **mode:** process
- **prediction (denominated in v3 held):** document-held reads **+0.15..+0.35 worse** than
  window-held on the same model — smaller than v1's line-leak ~0.5 (no verbatim repeats
  to re-read) but large enough to swallow most margins the mill trades in, and concentrated
  in the WikiText slice (entity-dense articles: a held window about a subject the model
  read 40 other paragraphs about). If the gap lands **<0.05**, v3's window-held numbers
  are honest as built, FD-001's reference stands clean, and this entry retires the whole
  concern with a number. Either outcome is a standing citation for every later v3 verdict.
- **status:** queued
```mill
id: FD-004
mode: process
run: --arm layered_half --rope --corpus v3-doc --steps 160
```

### FD-005 ★ · De-wrapped Gutenberg — corpus-v3.1 joins the hard wraps the builder mistook for lines
- **source:** `make_corpus_v3.py`'s `feed()` + measurement at filing time: the builder
  tokenizes **line-by-line with one BOS per line** (v2 discipline), but Gutenberg .txt
  lines are hard typographic wraps — median **67–69 chars** (pg1342: 69, pg11: 67,
  pg2600: 68), i.e. ~11–13 pieces — while WikiText lines are genuine paragraphs (median
  395 chars). So the Gutenberg share of v3 is chopped **mid-sentence every ~12 pieces**,
  each chop marked BOS: the model is trained that a new "line" begins every dozen pieces
  inside a sentence, and J-015's line-start loss cliff is manufactured ~5× more often in
  Gutenberg windows than the text justifies. No filed entry touches wrap semantics:
  G-013 masks *real* line seams on v2, J-015 prices offsets from *real* line starts.
- **mechanism:** Rebuild the Gutenberg share as paragraphs: join consecutive wrapped
  lines (a line joins the next when it does not end in terminal punctuation or the next
  line opens lowercase — the standard de-wrap heuristic), blank line = paragraph break =
  one BOS. WikiText share byte-identical. Everything downstream of the join (filters,
  dedup, leak guard, held construction) rerun unchanged, so v3.1 differs from v3 in the
  Gutenberg line semantics only.
- **exact change:** builder variant `make_corpus_v3_1.py` (de-wrap pass on Gutenberg
  bodies between the START/END strip and `feed()`); paired runs
  `--arm layered_half --rope --corpus {v3|v3.1} --steps 160`, 3 seeds, each model scored
  on both corpora' held sets (cross-scored, so a held-difficulty shift is separable from
  a training gain); per-offset-in-line loss reported for offsets 0–4 (J-015's bins).
- **mode:** process
- **prediction (denominated in v3.1 held, cross-checked on v3 held):** de-wrapped wins
  **−0.02..−0.06 pooled**, concentrated where the defect lives: Gutenberg slice
  **−0.04..−0.09**, WikiText slice within ±0.01 (its text never changed — a WikiText move
  would indict the comparison, not the fix). The offsets 0–1 loss premium shrinks by
  ≥30%: BOS positions become real boundaries, so their targets stop being mid-sentence
  continuations wearing a boundary marker. If the paired run is flat, the wrap was
  cosmetic — the tokenizer's pieces never cared where BOS fell — and v3 stands as built;
  the entry is cheap precisely because it should be run before the v3 series hardens.
- **status:** queued
```mill
id: FD-005
mode: process
run: --arm layered_half --rope --corpus v3.1 --steps 160
```

### FD-006 · WikiText valid/test excision — v3 swallowed its own external judge; give it back
- **source:** `make_corpus_v3.py`'s WikiText loop: it feeds `wiki.train.raw`,
  `wiki.valid.raw` **and** `wiki.test.raw` into the training stream. E-021 priced the
  same *shape* of error at toy scale (the German test file inside v1/v2, global effect
  <0.01). This instance is not toy: WikiText-103 test is the standard external benchmark
  for this exact text family — any future comparison of a lab model against published
  WikiText numbers, or any use of wiki.test as an untouched judge, is contaminated by
  construction, silently.
- **mechanism:** Build v3.2 = v3 with valid+test excluded at the source list (train split
  only). Then price the contamination directly: score FD-001's v3-trained champion and a
  v3.2-trained champion (equal steps) on the **raw WikiText test text** as an external
  held set neither v3.2 model has seen. The v3 model's advantage on that set is the
  contamination dividend, measured instead of asserted. As a side effect the lab gains
  its first genuinely external judge — every prior held set in the lab's history was
  drawn from the same stream the model trained on.
- **exact change:** builder variant (WikiText source list = train only) + eval-only
  scoring path for an out-of-stream held file (tokenize wiki.test.raw with the lab
  tokenizer, window it, `held_loss` unchanged); runs
  `--arm layered_half --rope --corpus v3.2 --steps 160`, 3 seeds.
- **mode:** process
- **prediction (denominated in WikiText-test external held, and v3-native held):** the
  v3-trained champion beats the v3.2-trained champion on wiki.test by **0.05–0.15** —
  a dividend made of memorized articles, worthless as evidence — while on v3-native
  held the two training corpora are indistinguishable (**within ±0.02**; valid+test are
  ~1% of v3's pieces, so excision is free). Deliverable either way: v3.2 becomes the
  canonical v3 build and wiki.test the lab's external reference; if the dividend lands
  <0.02, the contamination was numerically harmless and the excision still stands as
  procedure (E-021's rule, finally applied where it matters).
- **status:** queued
```mill
id: FD-006
mode: process
run: --arm layered_half --rope --corpus v3.2 --steps 160
```

### FD-007 · Chronological curriculum — read the books in the order English changed
- **source:** v3 is the first lab corpus whose sources carry a **time axis**: Gutenberg
  books span ~1813 (Austen) to the early 1920s, and WikiText is contemporary encyclopedic
  English. A-041/042/043 order windows by *init-model loss* (on junk windows); G-024
  orders v3 books by *length*; B-001 stages *source-class ratios*; G-019 places a
  *language*. Nobody has ordered by publication date — the one ordering that is also a
  domain-drift schedule, ending training on the English closest to the modern slice that
  dominates v3 held.
- **mechanism:** Books sorted ascending by first-publication year and read in that order
  (book-granular stream, FD-agnostic sampler within each book), with WikiText interleaved
  at its natural share throughout as a modern anchor. Control: identical books, identical
  mixture, identical total steps, book order shuffled (seed-fixed). Judged on v3 held
  split by source: the prediction is a *trade* — modern slice gains, archaic slice pays
  a recency tax — and only the split can see it.
- **exact change:** runner flag `--v3-order chrono|shuffled` (publication-year table for
  the Gutenberg files added to the v3 build metadata; book boundaries as in G-024's
  plumbing, direction and key differ — G-024's key is length, its question is contiguity;
  this entry's key is year, its question is drift). Champion chassis, fixed 320 steps,
  3 seeds. Full-trial-only: a probe sees a fraction of one era.
- **mode:** process
- **prediction (denominated in v3 held):** WikiText slice **−0.02..−0.05** vs the shuffled
  control (the run ends annealed toward modern usage), Gutenberg slice **+0.01..+0.03**
  (the recency tax — the last-seen era is not Austen's), pooled **−0.01..−0.03**. If the
  Gutenberg tax exceeds the WikiText gain, drift-annealing is a slice trade the lab
  should refuse, and the shuffled mixture stands as v3 policy with a measurement behind
  it instead of a default.
- **status:** queued
```mill
id: FD-007
mode: process
run: --arm layered_half --rope --corpus v3 --steps 320 --v3-order chrono
```

### FD-008 · Context 1024 on v3 — the first long-context read where a long window is one passage
- **source:** A-089 (ctx 512 at the chassis shape) was filed against v1, where a 512-piece
  window splices ~50 unrelated 9-piece lines — its result, whatever it showed, priced
  collage tolerance, not long context. G-022/I-010 vary ctx as a *schedule* on v2, whose
  longest line is 596 pieces. v3 is the first corpus where a 1024-piece window is
  ordinarily **one continuous passage** (a WikiText article section, a book chapter
  stretch): the long-document structure neither v1 nor v2 had is precisely what makes
  the ctx axis meaningful for the first time.
- **mechanism:** Champion shape trained at **ctx 1024** on v3 (RoPE as filed, base
  unchanged), judged on v3 held windows of length 1024 with loss binned by position
  (16 buckets of 64), plus the standard ctx-256 held for the cost read: what long
  training does to short-window performance on the same model.
- **exact change:** `--ctx 1024` run configuration (train_next's ctx plumbing; RoPE
  buffers extended, no model change) — `--arm layered_half --rope --corpus v3
  --ctx 1024 --steps 160`, 3 seeds; position-binned held reporting per J-020's method
  at the new length. Fixed steps, not minutes: steps at ctx 1024 cost ~4× the champion's,
  charged openly.
- **mode:** process
- **prediction (denominated in v3 held@1024):** buckets 256–511 beat the ctx-256
  champion's late-position loss by **−0.03..−0.08** (real antecedents — names, topics,
  argument threads — exist at those distances in v3 and in no earlier corpus); buckets
  768–1023 are **flat within ±0.02** of that gain's decay to zero — a 2-block model's
  composition, not RoPE's angles, is the predicted binding constraint at 4× length.
  Cost read: ctx-256 held on the same model worsens by **≤+0.02** vs FD-001 (long
  training is nearly free at short range). If buckets 256–511 show *no* gain, long
  context is a dead axis for this chassis even when the data finally supports it —
  a finding that closes A-089's question properly instead of leaving it answered by
  a collage.
- **status:** queued
```mill
id: FD-008
mode: process
run: --arm layered_half --rope --corpus v3 --ctx 1024 --steps 160
```

### FD-009 · The one-pass champion — the lab's first fresh-data scaling curve, and the repetition price
- **source:** B-009 (epoch/repetition scaling, Muennighoff et al.) prices repeated data
  on a *fixed small* corpus: up to ~4 epochs nearly free, decay after. Every lab run to
  date lives on B-009's side of the world — the unique stream is smaller than the budget
  wants. v3 inverts the regime: a full pass (~2,613 steps) is affordable and **no piece
  needs to repeat**. The fresh-vs-repeated divergence — where exactly repetition starts
  costing, in pieces-seen — has never been measurable here because there was never
  enough fresh data to draw the fresh curve.
- **mechanism:** One champion run over the **whole v3 stream exactly once** (deck
  sampler, G-021's without-replacement discipline at stream scale), held logged every
  160 steps: the vote trainer's loss-vs-pieces-seen curve from 1.3M to ~21.4M fresh
  pieces, exponent fitted. Read against B-009-style repeated-data points on v2 at
  matched pieces-seen (2M / 4M / 8M), the curves' separation at each checkpoint *is*
  the repetition price, in nats, at this scale.
- **exact change:** `--arm layered_half --rope --corpus v3 --sampler deck
  --steps 2613 --log-held-every 160`, 1 seed (the curve is the product; a second seed
  if the first lands clean). Cost stated plainly: ~3 s/step at champion shape ≈ **2.2 h
  solo** — the most expensive entry in this file, bought once.
- **mode:** process — full-trial-only by construction (the entry *is* a long run).
- **prediction (denominated in v3 held):** final held improves **−0.35..−0.55** over
  FD-001's 160-step v3 number, with no flattening kink before ~10M pieces — the
  champion at one pass sits at ~12.4 pieces/total-param, still under
...[truncated 6852 chars] the ~20 rule, so
  fresh data should keep paying at close to its early rate. The fresh-vs-repeated
  separation at 8M pieces-seen is predicted at **≥0.05** in fresh data's favour — the
  first direct price of the repetition every v1/v2 verdict was bought with. If the
  curves do *not* separate by 8M pieces, B-009's "repetition is nearly free" extends
  much further than filed, and v3's size advantage over v2 shrinks to its cleanliness
  alone — a deflationary but load-bearing answer for FD-002's sake.
- **status:** queued
```mill
id: FD-009
mode: process
run: --arm layered_half --rope --corpus v3 --sampler deck --steps 2613
```

### FD-010 · Gutenberg↔WikiText dose — how much 19th-century narrative does a modern judge want?
- **source:** I-002 dosed v2's German share (0 / 23 / 45.7%) at fixed tokens with
  per-language held; the dose question is the one mixture axis that survived G-016
  (period) and G-019 (placement) unasked. v3's mixture is a different substance: two
  Englishes separated by a century and a genre — narrative prose vs encyclopedic
  article — at a natural share set by raw volume (~85% WikiText by source bytes), not
  by anyone's decision. Whether Gutenberg text helps, taxes, or is irrelevant to
  WikiText-held performance is the cross-genre transfer question in dose form.
- **mechanism:** Three v3 arms at fixed 320 steps and fixed total tokens, fully
  shuffled within each arm: Gutenberg share **0%** (WikiText only), **natural**
  (~15%, the built stream = FD-001's mixture extended to 320 steps), and **50%**
  (Gutenberg oversampled ~3× from its book pool — possible without repetition
  because the run still sees a minority of the books). Judged on v3 held split by
  source, per I-002's slicing discipline.
- **exact change:** sampler weights by source class on the v3 stream —
  `--src-share gutenberg:{0.0|natural|0.5}` (source tags from the v3 build's
  per-category table; same plumbing family as I-002's `--de-share`, new corpus).
  Champion chassis, 3 seeds.
- **mode:** process
- **prediction (denominated in v3 held, by slice):** WikiText slice: natural and 50%
  agree **within 0.02**, and both beat 0% Gutenberg by only **−0.01..−0.03** —
  narrative prose is a mild diversity tonic for the encyclopedic judge, not a
  teacher. Gutenberg slice: collapses **+0.25..+0.40** at 0% (a century of usage is
  not free from modern text alone) and improves **−0.03..−0.06** at 50% vs natural.
  Pooled optimum therefore sits at the oversampled dose, not the built one: if
  pooled-at-50% beats pooled-at-natural by >0.02, v3's canonical mixture should be
  rebuilt at the measured dose rather than inherited from download sizes. A flat
  WikiText slice across all three doses retires the cross-genre hope cleanly: the
  two Englishes would be separate subjects sharing a tokenizer.
- **status:** queued
```mill
id: FD-010
mode: process
run: --arm layered_half --rope --corpus v3 --steps 320 --src-share gutenberg:0.5
```

### FD-011 · Tokenizer fertility on real text — how much of v3's difficulty is the BPE, not the books?
- **source:** v3 is tokenized with the hive's shared BPE (vocab 4096, inherited
  provenance — fitted on hive-era text, certainly not on Gutenberg + WikiText).
  B-002 refits the tokenizer on "the exact training mixture" — but its mixture was
  v1's harvested junk, its verdict pooled nats/byte, and no per-source anatomy was
  filed. WH-013/WH-020 vary vocab *size* on the same sources. Nobody has measured
  the inherited tokenizer's **fertility** (pieces per byte of text) per real source:
  if archaic spellings and 19th-century names fragment into rare pieces, part of
  any v3 Gutenberg difficulty is a tokenization tax, and every Gutenberg-slice
  prediction in this file (FD-001, FD-005, FD-010) inherits the confound.
- **mechanism:** Step 1 (measurement, eval-only): fertility and vocab-coverage
  census of the inherited tokenizer on each v3 source vs v1 prose — pieces/byte,
  share of pieces from the bottom-frequency quartile, mean pieces per word. Step 2
  (conditional arm): refit BPE at the **same 4096** on a v3 sample, rebuild the
  v3 stream with it, champion at equal **bytes** (steps rescaled by the measured
  bytes/piece ratio), judged in nats/byte per source slice.
- **exact change:** census script over `corpus-v3/raw/` with the lab tokenizer;
  conditional: `--tokenizer refit-v3 --vocab 4096` rebuild + run
  `--arm layered_half --rope --corpus v3-refit --steps <byte-matched>`, 3 seeds.
- **mode:** process (step 1 is eval-only and gates step 2)
- **prediction (denominated in v3, nats/byte by slice):** step 1 shows Gutenberg
  fertility **≥15% worse** than WikiText's (more pieces per byte — archaic forms
  fragment) and a bottom-quartile piece share ≥1.5× WikiText's. Step 2, if run:
  refit gains **−0.01..−0.03 nats/byte on the Gutenberg slice** and ~0 (±0.005)
  on WikiText — i.e. a real but bounded tax, worth paying once at build time,
  not a hidden explanation for the whole v1→v3 level shift. If step 1 shows
  fertility within 5% across sources, step 2 is not run and the tokenizer is
  cleared as a v3 confound — which is itself a deliverable FD-001's slices need.
- **status:** queued
```mill
id: FD-011
mode: process
run: --arm layered_half --rope --corpus v3-refit
```

### FD-012 · V × steps at 10M on fresh data — was the big rung starved of data, or of flips?
- **source:** F-043 (vote-threshold scaling law: flip share fell ~5× from 0.885M to
  10M at fixed V=32; if V must fall as N rises, every big-rung reading is a
  near-frozen trainer) × DATA-AUDIT §6 (the same rungs were simultaneously
  data-starved). On v1 the two defects are inseparable: more steps means more
  *repeated* data, so "give the rung more steps" confounds flip opportunity with
  repetition. v3 separates them for the first time — 560 steps at 10M is 4.59M
  **fresh** pieces, ~0.4 of a pass, no repetition anywhere in the design.
- **mechanism:** A 2×2 factorial at the 10M rung on v3: V ∈ {32, 8} × steps ∈
  {56, 560}, layered+rope, flip share and flip-count distribution logged per cell.
  The interaction is the entry: if V binds only when steps exist, the (560, V=8)
  cell separates from (560, V=32) while the two 56-step cells tie; if data was
  the whole story, both 560 cells improve together and V never matters.
- **exact change:** `--arm layered --rope --corpus v3 --dim 512 --layers-n 3
  --votes {32|8} --steps {56|560}` (`--votes` pass-through per the pool's
  MILL-501..509 plumbing), 2 seeds per cell, 3 in the (560, V=32) cell it shares
  with FD-002 (reuse FD-002's runs where seeds align — do not double-run).
- **mode:** process — full-trial-only; the 560-step cells are ~2 h each at 10M
  step costs and no probe can stand in for them.
- **prediction (denominated in v3 held):** at 56 steps, V=8 ties V=32 **within
  ±0.02** (at 0.00021 flips/step almost nothing flips under either threshold —
  the frozen regime reads flat, which is why F-043's v1 sweep risks a false
  null). At 560 steps, V=8 beats V=32 by **−0.03..−0.07**: with fresh evidence
  finally arriving for ~10× longer, the threshold becomes the binding
  constraint and lowering it converts directly into flips that earn. If V=8
  *still* ties at 560 steps on fresh data, F-043's scaling law dies in the
  regime it was filed for, and the big rungs' problem is data and shape only —
  the FD-002 reading then stands unqualified.
- **status:** queued
```mill
id: FD-012
mode: process
run: --arm layered --rope --corpus v3 --dim 512 --layers-n 3 --votes 8 --steps 560
```

---

## Miner's closing note — what most changes when the data stops being junk

Three things, in order of how much of the lab's record they touch.

**1. The currency changes, and the old exchange rate is unknown.** Every verdict
the lab owns — 2.8580, the layered retraction, rotary's −0.0411, JEPA's loss — is
denominated in v1 held: a stream the audit showed is ~79% junk by source bytes,
30.8% duplicated, with held content leaking into training by construction. v3
does not just offer a better corpus; it retires the unit of account. FD-001 is
therefore not one entry among twelve — it is the re-denomination every other
FD entry (and every future wave) is priced in, exactly as E-018 was for v2,
except v3's number will also be *usable*: clean, leak-guarded at line level,
and large enough that a trial samples 6% of it instead of recycling all of it.

**2. Repetition stops being the water every run swims in.** On v1/v2 the unique
stream (0.91M pieces) was smaller than any serious budget, so repetition,
memorization and duplicate flattery were not variables — they were constants
of the environment, priced only indirectly (J-022, WH-048, B-009). At ~21.4M
pieces the environment flips: fresh data becomes the default and repetition a
*choice* with a measurable price (FD-009 draws the fresh curve the repetition
price is read against). The same flip rehabilitates questions the starved era
couldn't ask cleanly: big rungs at long budgets (FD-002), threshold-vs-data
factorials (FD-012), curricula whose phases are made of whole books (FD-007).

**3. The failure modes move from the stream's content to its structure.** v1's
problems were *what* the text was (dumps, merge tables, licenses). v3's text is
real — and its problems are *how it was assembled*: Gutenberg's hard wraps
becoming fake line boundaries under BOS-per-line tokenization (FD-005),
WikiText's own test split swallowed as training text (FD-006), held windows
that are line-clean but document-leaked (FD-004), a tokenizer fitted to a
different era's text (FD-011). None of these appear in a token census or a
duplication statistic; all of them were found by reading the builder. The
standing lesson for the v3 series: audit the *construction*, not just the
corpus — on real data, construction is where the junk went to hide.

*End of wave-6 lens-1 (first data). 12 entries, FD-001..FD-012, all queued.
★ = FD-001, FD-003, FD-005. Nothing here edits IDEA-POOL.md or any CANDIDATES
file; merging is the pool owner's call.*
