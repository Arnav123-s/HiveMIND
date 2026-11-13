# CANDIDATES-K — Idea Engine wave K (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Produced 2026-11-12 by the Idea Engine
(rotation 6: first-data, meta-control, scarcity, pool governance, deep wild, hive drills)
under Arnav's no-limit ideation order. CANDIDATE file: nothing here is in the pool until
the pool's owner merges it. IDEA-POOL.md was read by every miner and NOT edited. The
hive-drills lens (PL-001..PL-012) is merged into factory/CANDIDATES-IDEAS.md. The
prioritization rotation's output stands as mill/PRIORITIES.md. Waves F–J precede. -->

## Method and de-duplication

Every miner deduped against IDEA-POOL.md (368 entries), CANDIDATES-A/B/C/D/E/F/G/H/I/J
and FABLE-CANDIDATES.md. Two structural findings frame this wave. First (governance):
waves G/H/I are exact 12-per-lens grids — uniform lens quotas, not expected value, set
the pool's shape; K-037/K-038 are the corrective machinery. Second (first-data): the
corpus-v3 build needs verification before its numbers are quoted — when the FD miner
read it, corpus-v3.u16 held 1,777,325 pieces with build.log showing only the blocklist
step, and corpus-v3/SOURCES.md does not exist yet. FD entries are written against the
stated ~21.4M pieces with economics expressed as ratios that rescale; FD-001's first
job is confirming the finished count from corpus-v3.json. FD also found construction
defects in v3 as built (hard-wrapped Gutenberg tokenized BOS-per-line, FD-005;
WikiText valid/test splits inside the training stream, FD-006; document-level leakage
past the line-level guard, FD-004) — those entries are fixes, not criticisms of intent.

## Coordinator's top 3 for this wave ★

1. **K-037 · Family budgets** — one probe slot per dose family per pass, siblings
   unlocking only on promote/near. Cites the unbudgeted families (leak ×5, freeze ×3,
   the 12-member readout cluster K-038's lens-mate collapses to 3 representatives) and
   prices the saving at ~0.9–1.3 mill-hours per pass per generation. With K-038
   (premise graph: F-043 alone gates 9+ entries; a missing `--corpus v2` flag silently
   blocks G-013–G-024's v2 subset, I-002, WH-039/044/048 — a flag-factory action item).
2. **K-001 · Corpus-v3 re-baseline** — the re-denomination run: champion on v3 with
   per-source held slices (predicted v3 held 3.10–3.45 at 160 steps). Carries a
   verified plumbing bug: `train_next.py --corpus v3` does not currently resolve to
   corpus-v3/corpus-v3.u16.
3. **K-051 · Lottery flips** — delete the counters entirely; spend the flip budget
   (0.0011 × N) by uniform lottery among gated weights. If J-002's statistics-only
   rival is true the deletion is free; if it costs ≥ +0.15 at probe, it corroborates
   the memory theory more strongly than the shuffle itself. Zero counter bytes.

**Scarcity discipline worth copying:** the scarcity lens's largest defended claim is
−0.05 held at equal tokens (K-025's range top); its −0.08 upper figure is filed but
explicitly NOT defended as a point claim. Claims in this program should all read
that way.

---

## Lens 1 — First data (was FD-###)

### K-001 ★ · Corpus-v3 re-baseline — the champion's first honest number on real text
- **source:** DATA-AUDIT.md §8 + E-018 (the v2 re-baseline, PRIORITIES.md #9) — E-018 converts
  the champion's currency from leaked v1 to clean-but-tiny v2. v3 is the first corpus that is
  clean *and* comparatively large, and no arm has ever been measured on it. This entry is
  E-018's successor, not its repeat: different corpus, different failure modes (K-004/005/006),
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
  the wrap-BOS tax of K-005 is the predicted reason, and K-005's paired run is the check.
  A pooled number below 3.0 would say real text at 23× v2's volume is already worth more
  than the junk era's flattery cost; above 3.5, the champion's recipe (tuned entirely on
  junk statistics) transfers worse than anyone has priced.
- **status:** queued
```mill
id: K-001
mode: process
run: --arm layered_half --rope --corpus v3 --steps 160
```

### K-002 · The ladder re-run on v3 — the big rungs were starved, not incapable; now feed them
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
- **exact change:** ladder configs on the v3 stream via K-001's resolver:
  `--arm layered --rope --corpus v3 --dim {288,512} --layers-n {2,3} --steps {56,560}`,
  2 seeds per cell (3 at 56 steps), flip-share and per-weight flip-count histograms logged
  at both budgets (F-038's instrumentation, reused).
- **mode:** process — full-trial-only; a 75 s probe at 10M sees a handful of steps and
  cannot read a starvation question.
- **prediction (denominated in v3 held):** at 56 steps the v1 ordering replicates
  (10M beats 2M by ~0.2–0.35, both far above K-001's champion number — fewer steps at
  bigger shapes). At 560 steps the 10M rung improves **−0.25..−0.45** over its own 56-step
  self and the 10M−2M gap **widens ≥2×** — the starvation signature: on fresh data the big
  rung's slope is steeper, where B-009's repeated-data curve would have flattened it. The
  50M diagnostic: flip share stays **≤0.0003/step** even on fresh data (F-043's threshold
  dilution is a V problem, not a data problem — K-012 tests the interaction directly).
  If instead the gap *narrows* at 560 steps, the audit's starvation reading was wrong and
  the ladder's small-is-better shape prior is a real architecture fact on real text too.
- **status:** queued
```mill
id: K-002
mode: process
run: --arm layered --rope --corpus v3 --dim 512 --layers-n 3 --steps 560
```

### K-003 ★ · Junk-era transfer — does a completed v1/v2 phase help or poison v3 training?
- **source:** the v2↔v3 question the context shift forces. WH-039 measures a *mid-run*
  50/50 corpus switch (v1↔v2) and its recovery curve, judged on v2 held; J-040 cross-scores
  a v1↔v2 arm matrix. Neither asks the sequential-training question on v3: the lab owns
  finished junk-era training (every champion/control checkpoint) — is any of it a *starting
  point* for real-text training, or is the only honest v3 run a cold one?
- **mechanism:** Four arms, identical total budget (320 fixed steps), all judged on
  **v3-native held** (K-001's set): (a) v3-only, 320 steps (control); (b) v2 for 160 steps
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
id: K-003
mode: process
run: --arm layered_half --rope --corpus v3 --steps 320 --pretrain-corpus v1 --pretrain-steps 160
```

### K-004 · Document-held re-baseline — the leak guard is line-level; books leak at document level
- **source:** `make_corpus_v3.py`'s held-line leak guard + DATA-AUDIT §4's lesson. The guard
  guarantees no *line* inside a v1/v2 held window enters v3, and global dedup guarantees no
  line repeats inside v3. But v3's own held windows (K-001's set) are windows **inside
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
  are honest as built, K-001's reference stands clean, and this entry retires the whole
  concern with a number. Either outcome is a standing citation for every later v3 verdict.
- **status:** queued
```mill
id: K-004
mode: process
run: --arm layered_half --rope --corpus v3-doc --steps 160
```

### K-005 ★ · De-wrapped Gutenberg — corpus-v3.1 joins the hard wraps the builder mistook for lines
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
id: K-005
mode: process
run: --arm layered_half --rope --corpus v3.1 --steps 160
```

### K-006 · WikiText valid/test excision — v3 swallowed its own external judge; give it back
- **source:** `make_corpus_v3.py`'s WikiText loop: it feeds `wiki.train.raw`,
  `wiki.valid.raw` **and** `wiki.test.raw` into the training stream. E-021 priced the
  same *shape* of error at toy scale (the German test file inside v1/v2, global effect
  <0.01). This instance is not toy: WikiText-103 test is the standard external benchmark
  for this exact text family — any future comparison of a lab model against published
  WikiText numbers, or any use of wiki.test as an untouched judge, is contaminated by
  construction, silently.
- **mechanism:** Build v3.2 = v3 with valid+test excluded at the source list (train split
  only). Then price the contamination directly: score K-001's v3-trained champion and a
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
id: K-006
mode: process
run: --arm layered_half --rope --corpus v3.2 --steps 160
```

### K-007 · Chronological curriculum — read the books in the order English changed
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
id: K-007
mode: process
run: --arm layered_half --rope --corpus v3 --steps 320 --v3-order chrono
```

### K-008 · Context 1024 on v3 — the first long-context read where a long window is one passage
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
  Cost read: ctx-256 held on the same model worsens by **≤+0.02** vs K-001 (long
  training is nearly free at short range). If buckets 256–511 show *no* gain, long
  context is a dead axis for this chassis even when the data finally supports it —
  a finding that closes A-089's question properly instead of leaving it answered by
  a collage.
- **status:** queued
```mill
id: K-008
mode: process
run: --arm layered_half --rope --corpus v3 --ctx 1024 --steps 160
```

### K-009 · The one-pass champion — the lab's first fresh-data scaling curve, and the repetition price
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
  K-001's 160-step v3 number, with no flattening kink before ~10M pieces — the
  champion at one pass sits at ~12.4 pieces/total-param, still under
...[truncated 6852 chars] the ~20 rule, so
  fresh data should keep paying at close to its early rate. The fresh-vs-repeated
  separation at 8M pieces-seen is predicted at **≥0.05** in fresh data's favour — the
  first direct price of the repetition every v1/v2 verdict was bought with. If the
  curves do *not* separate by 8M pieces, B-009's "repetition is nearly free" extends
  much further than filed, and v3's size advantage over v2 shrinks to its cleanliness
  alone — a deflationary but load-bearing answer for K-002's sake.
- **status:** queued
```mill
id: K-009
mode: process
run: --arm layered_half --rope --corpus v3 --sampler deck --steps 2613
```

### K-010 · Gutenberg↔WikiText dose — how much 19th-century narrative does a modern judge want?
- **source:** I-002 dosed v2's German share (0 / 23 / 45.7%) at fixed tokens with
  per-language held; the dose question is the one mixture axis that survived G-016
  (period) and G-019 (placement) unasked. v3's mixture is a different substance: two
  Englishes separated by a century and a genre — narrative prose vs encyclopedic
  article — at a natural share set by raw volume (~85% WikiText by source bytes), not
  by anyone's decision. Whether Gutenberg text helps, taxes, or is irrelevant to
  WikiText-held performance is the cross-genre transfer question in dose form.
- **mechanism:** Three v3 arms at fixed 320 steps and fixed total tokens, fully
  shuffled within each arm: Gutenberg share **0%** (WikiText only), **natural**
  (~15%, the built stream = K-001's mixture extended to 320 steps), and **50%**
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
id: K-010
mode: process
run: --arm layered_half --rope --corpus v3 --steps 320 --src-share gutenberg:0.5
```

### K-011 · Tokenizer fertility on real text — how much of v3's difficulty is the BPE, not the books?
- **source:** v3 is tokenized with the hive's shared BPE (vocab 4096, inherited
  provenance — fitted on hive-era text, certainly not on Gutenberg + WikiText).
  B-002 refits the tokenizer on "the exact training mixture" — but its mixture was
  v1's harvested junk, its verdict pooled nats/byte, and no per-source anatomy was
  filed. WH-013/WH-020 vary vocab *size* on the same sources. Nobody has measured
  the inherited tokenizer's **fertility** (pieces per byte of text) per real source:
  if archaic spellings and 19th-century names fragment into rare pieces, part of
  any v3 Gutenberg difficulty is a tokenization tax, and every Gutenberg-slice
  prediction in this file (K-001, K-005, K-010) inherits the confound.
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
  cleared as a v3 confound — which is itself a deliverable K-001's slices need.
- **status:** queued
```mill
id: K-011
mode: process
run: --arm layered_half --rope --corpus v3-refit
```

### K-012 · V × steps at 10M on fresh data — was the big rung starved of data, or of flips?
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
  with K-002 (reuse K-002's runs where seeds align — do not double-run).
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
  the K-002 reading then stands unqualified.
- **status:** queued
```mill
id: K-012
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
does not just offer a better corpus; it retires the unit of account. K-001 is
therefore not one entry among twelve — it is the re-denomination every other
FD entry (and every future wave) is priced in, exactly as E-018 was for v2,
except v3's number will also be *usable*: clean, leak-guarded at line level,
and large enough that a trial samples 6% of it instead of recycling all of it.

**2. Repetition stops being the water every run swims in.** On v1/v2 the unique
stream (0.91M pieces) was smaller than any serious budget, so repetition,
memorization and duplicate flattery were not variables — they were constants
of the environment, priced only indirectly (J-022, WH-048, B-009). At ~21.4M
pieces the environment flips: fresh data becomes the default and repetition a
*choice* with a measurable price (K-009 draws the fresh curve the repetition
price is read against). The same flip rehabilitates questions the starved era
couldn't ask cleanly: big rungs at long budgets (K-002), threshold-vs-data
factorials (K-012), curricula whose phases are made of whole books (K-007).

**3. The failure modes move from the stream's content to its structure.** v1's
problems were *what* the text was (dumps, merge tables, licenses). v3's text is
real — and its problems are *how it was assembled*: Gutenberg's hard wraps
becoming fake line boundaries under BOS-per-line tokenization (K-005),
WikiText's own test split swallowed as training text (K-006), held windows
that are line-clean but document-leaked (K-004), a tokenizer fitted to a
different era's text (K-011). None of these appear in a token census or a
duplication statistic; all of them were found by reading the builder. The
standing lesson for the v3 series: audit the *construction*, not just the
corpus — on real data, construction is where the junk went to hide.

*End of wave-6 lens-1 (first data). 12 entries, K-001..K-012, all queued.
★ = K-001, K-003, K-005. Nothing here edits IDEA-POOL.md or any CANDIDATES
file; merging is the pool owner's call.*

## Lens 2 — Meta-control (was MT-###)

### K-013 ★ · Saturation-servoed V: the threshold follows the executable backlog
- **source:** control theory (PI control of a queue) + WH-051's code audit, split
  in two. WH-051 counts counters pinned at the clamp; this entry splits that
  population by the one property WH-051's census does not separate out: whether
  the pinned counter's flip is *executable* (the component is not at the boundary
  its sign pushes against, so reaching V would actually flip it) or *frustrated*
  (boundary-blocked; K-014's signal). An executable backlog means evidence is
  queuing behind a threshold that is too high for the current gradient regime;
  a fixed V=32 cannot know that.
- **control law (signal → rule → bounds):** signal `s_t` = global share of
  counters (c1 and c2 pooled) with |c| = V whose pending flip is executable,
  EMA-smoothed over 20 steps (α=0.1), sampled every 20 steps. Target band
  s* ∈ [0.5%, 2%]. Integral-only update, once per interval:
  `V ← V − 1 if s̄ > 2%`, `V ← V + 1 if s̄ < 0.5%`, else hold (deadband).
  Bounds V ∈ [20, 48]. One step of V per interval, never more.
- **exact train.py change:** new flag `--sat-servo` on `Layered`. In `step()`,
  after the existing clamp, compute executability from tensors already present:
  `exec1 = (c1.abs() >= V) & ((t1 + c1.sign()).clamp(-1,1) != t1)` (and likewise
  c2/t2) — the same predicate already inside `go1/go2`, reused before the flip
  test; accumulate the pooled share into `self.sat_ema`; every 20 steps apply
  the rule to `self.votes` (today the local `V = self.votes` read at the top of
  `step()` makes this a one-line actuation). Log `V` and `s̄` in the step-100
  print line. No new per-weight state.
- **stability guard / own failure mode:** the failure mode is a **limit cycle**:
  lowering V drains the backlog in a flip burst, saturation collapses, the
  controller raises V, the backlog rebuilds — V hunting ±1 forever and the run
  effectively training at a dithered threshold. Guards: the deadband (a 4× wide
  target band, not a point), the 20-step interval (≥ the EMA's own horizon, so
  the controller never reacts to its own last action before that action's effect
  is measured), and the ±1 rate limit. Second failure mode: saturation is partly
  *caused* by the clamp itself — gaming by construction — which is exactly why
  the frustrated share is excluded from this signal and given its own dial
  (K-014); if s̄ and frustration rise together, this controller is reading
  alphabet failure as backlog, and the logged pair (s̄, frustration) makes that
  confound visible in one probe.
- **prediction:** −0.01..−0.04 vs champion at full format. The mechanism claim is
  narrow and falsifiable from the log alone: in champion runs s̄ is predicted to
  sit outside the band for most of the run (early: above 2%, evidence-rich;
  late: below 0.5%, evidence-starved), i.e. fixed V=32 is wrong at both ends in
  opposite directions — no fixed schedule can express that, because the crossing
  times are state-driven, not clock-driven.
- **status:** queued
```mill
id: K-013
mode: process
run: --arm layered_half --rope --sat-servo
```

### K-014 · Frustration-servoed leak: pinned evidence is forgotten, live evidence is not
- **source:** WH-051 (frustration census) used as an actuator input for the first
  time + MILL-209..211's fractional leak, which pools λ as three *fixed*
  constants (0.99 / 0.98 / 0.95). Nobody has let the measured frustrated
  population choose λ. A frustrated counter is absorbing agreeing votes into a
  clamp and returning nothing; the longer it pins, the more of the run's evidence
  budget is spent on a state the ternary alphabet cannot express. Leak is the
  dial that retires pinned evidence: with λ < 1 a pinned counter decays off the
  clamp and its weight re-enters play.
- **control law (signal → rule → bounds):** signal `f_t` = WH-051 frustrated
  fraction, global, computed exactly as WH-051 defines it (component at boundary,
  counter saturated, outward sign), EMA over 20 steps, sampled every 20 steps.
  WH-051 predicts champion-family runs at 4–8% end-of-run. Rule (proportional,
  anchored at that band): `λ = clip(1.0 − 0.6·max(0, f̄ − 0.04), 0.96, 1.0)` —
  at or below 4% frustration there is no leak at all (champion behaviour); at
  8% frustration λ = 0.976; the floor 0.96 is reached only above ~10.7%.
  Applied per step as `c ← round(λ·c) + vote` in fixed point (see change).
- **exact train.py change:** new flag `--frust-leak` on `Layered`; requires the
  fractional-leak plumbing of MILL-209 (counters promoted to int16 fixed point,
  ×256 — charged: 4 B/weight of counter state vs the champion's 2 B, stated in
  the run record). In `step()`: compute the frustrated mask from (t1, c1) and
  (t2, c2) before the vote add (four comparisons on tensors already live), update
  `self.f_ema`, set `self.lam` by the rule, then apply leak inside the existing
  counter update in place of the bare `(self.c1[i] + vote).clamp(-V, V)`.
  Frustration fraction logged every 100 steps alongside flip share.
- **stability guard / own failure mode:** the failure mode is **self-exciting
  forgetting**: leak unpins counters → frustration falls → λ returns to 1.0 →
  counters re-pin → leak returns — a relaxation oscillation that periodically
  wipes the evidence of exactly the most-contested weights. Guards: the EMA +
  20-step sampling make λ move slowly against a 25–100-step pinning timescale;
  the 4% deadband means the loop is *open* (λ ≡ 1.0, bit-identical to champion)
  in the regime WH-051 calls healthy; and λ's floor (0.96, horizon 25 steps) is
  set no stronger than MILL-211's weakest pooled dose, so the controller can
  never reach a forgetting rate the pool hasn't already priced as a constant.
  Second failure mode — gaming: leak also decays *non*-frustrated counters,
  so the controller pays for unpinning with global memory loss; the per-layer
  frustration log is the audit (if frustration is concentrated in `down`, as
  WH-051 predicts, a global λ is the wrong scope and K-020 is the repair).
- **prediction:** −0.01..−0.03, concentrated in the second half (frustration is a
  late-run population). Flat-or-better is also a verdict: if f̄ never leaves the
  deadband, the arm is bit-identical to the champion and WH-051's separator claim
  weakens — the probe reports f̄'s trajectory either way.
- **status:** queued
```mill
id: K-014
mode: process
run: --arm layered_half --rope --frust-leak
```

### K-015 ★ · Meta-loop: loss slope sets MILL-207's flip-rate setpoint
- **source:** cascade control (an outer loop trims an inner loop's setpoint —
  the standard industrial answer when the inner setpoint's right value drifts)
  applied to MILL-207, whose per-layer V servo holds flip rate at a *fixed*
  target (0.1% or 0.3%) chosen before the run. That target is a guess about how
  much structural churn the run can profitably absorb, and the profitable amount
  plainly changes as the loss curve bends. This entry files no new inner loop:
  it owns only the setpoint, which is the meta-level the brief reserves.
- **control law (signal → rule → bounds):** inner loop = MILL-207 unchanged
  (per-layer V, flip-rate target φ*). Outer signal: train-loss slope over the
  trailing 100 steps, `m_t` = (EMA₁₀₀ loss now − EMA₁₀₀ loss 100 steps ago)/100,
  normalised by the run's own first-100-step slope m₀, ρ = m_t/m₀. Outer rule,
  every 100 steps: `φ* ← φ* · 1.25 if ρ > 0.7` (loss still falling at ≥70% of
  its early rate — structure churn is still paying, allow more), `φ* ← φ* · 0.8
  if ρ < 0.3` (loss has flattened — churn is now mostly noise, ration it), else
  hold. Bounds φ* ∈ [0.03%, 0.4%], initialised at MILL-207's 0.1%.
- **exact train.py change:** new flag `--meta-flip-target` on `Layered`,
  requires `--vlayer` (MILL-207) to be active; `Layered` gains `self.phi_star`
  (one float) read by the vlayer update in place of its constant, plus a
  100-step loss ring buffer fed from `main()`'s existing `losses` list via the
  `step(loss, done)` argument the trainer already receives. Outer update inside
  `step()` gated on `self.steps % 100 == 0`. Both φ* and ρ logged every 100 steps.
- **stability guard / own failure mode:** the failure mode is **two loops
  fighting**: the inner loop moves V to chase φ*, the outer loop moves φ*
  because loss slope moved — but loss slope also moves *because* V moved, so the
  outer loop can chase its own tail (raise φ* → more flips → transient loss rise
  → ρ collapses → cut φ* → …). Guards: strict timescale separation — the outer
  loop's interval (100 steps) is ≥5× the inner servo's settling time, the
  classical cascade condition; multiplicative steps are small (±20–25%) and
  asymmetric in the safe direction (cuts are faster than raises, 0.8 vs 1.25);
  and ρ is computed on train loss *excluding* the 10 steps immediately after
  each outer update, so the transient the update itself causes is never read as
  evidence. Named residual risk: ρ conflates "churn stopped paying" with "the
  AdamW parts saturated" — the log separates them only if read next to G-002's
  φ-vs-slope correlation diagnostic; the entry accepts that ambiguity openly.
- **prediction:** −0.01..−0.04 over MILL-207 alone at full format (and therefore
  the comparison that matters is K-015 vs MILL-207, not vs champion — the probe
  must run both). Predicted φ* trajectory: rises early (ρ ≈ 1), peaks mid-run,
  ends at or below its 0.03% floor — a *shape* no fixed target and no fixed V
  schedule contains.
- **status:** queued
```mill
id: K-015
mode: process
run: --arm layered_half --rope --vlayer 0.001 --meta-flip-target
```

### K-016 · Contest-servoed gate: c1/c2 disagreement tightens who may vote
- **source:** WH-060 (c1/c2 disagreement anatomy: the contested population —
  sign(c1) ≠ sign(c2), both |c| ≥ 8 — is predicted at 10–16% of weights and
  ≥35% of late flips) as a control input. F-028 servos the same dial (gate
  quantile q) on a different signal (admitted gradient *mass*); the gate's other
  failure is not mass drift but *evidence quality*: when the two components of
  the same weight persistently argue, the layer's gradient stream is internally
  inconsistent, and admitting the median-strength half of it (q = 0.5, the
  hard-coded `median()` gate) feeds that argument at full rate.
- **control law (signal → rule → bounds):** signal `κ_t` = global contested
  fraction per WH-060's exact definition, EMA over 20 steps, sampled every
  20 steps. Rule (proportional on q): `q = clip(0.5 + 1.5·(κ̄ − 0.10), 0.5, 0.8)`
  — at WH-060's predicted healthy κ ≈ 10% the gate is the champion's median
  gate; at κ = 20% only the top 30% by |g| vote; q never goes *below* 0.5
  (this controller may only ever tighten, never loosen past champion).
- **exact train.py change:** new flag `--contest-gate` on `Layered`. In `step()`,
  replace `strong = g.abs() >= g.abs().median()` with
  `strong = g.abs() >= g.abs().quantile(self.q)` when the flag is on; κ computed
  per layer from (c1, c2) already in scope (`(c1.sign() != c2.sign()) &
  (c1.abs() >= 8) & (c2.abs() >= 8)`), pooled globally into `self.k_ema`, q
  updated every 20 steps. Cost: one `quantile` per layer per step replaces one
  `median` — same complexity class, charged honestly at equal minutes.
- **stability guard / own failure mode:** the failure mode is **starving the
  argument instead of settling it**: tightening the gate excludes exactly the
  mid-strength votes that would eventually resolve contested weights, so κ stays
  high *because* q is high — the controller reads its own shadow as a permanent
  condition and the gate ratchets to 0.8 and stays (a windup analogue: not an
  integrator, but a one-way causal loop). Guards: q is a pure proportional
  function of the current κ̄ (no memory, no ratchet — if κ falls, q falls the
  same interval); the 20-step EMA prevents step-to-step gate flicker from
  decorrelating consecutive vote streams; and the tighten-only asymmetry is
  capped at 0.8 so at least the strongest 20% always vote — the contested
  population can never be fully disenfranchised, only slowed. Diagnostic that
  convicts the failure mode if it occurs: κ̄ and q logged together; q pinned at
  0.8 with κ̄ *rising* for >200 steps is the signature, and it is printable from
  one probe.
- **prediction:** −0.01..−0.03. Side value either way: the first causal test of
  WH-060 — if throttling votes *into* contested layers-by-proxy (globally, here)
  helps, contest is noise; if it hurts, contest was load-bearing exploration,
  and WH-060's anatomy flips sign as evidence.
- **status:** queued
```mill
id: K-016
mode: process
run: --arm layered_half --rope --contest-gate
```

### K-017 · Productivity-servoed lr: the FP parts speed up only while flips pay
- **source:** flip *productivity* — held-proxy loss improvement per flip — a
  signal no filed entry controls on. G-002 servos this same dial (AdamW lr) on
  flip *share* (how much structure moved); share says nothing about whether the
  movement helped. G-065 uses loss slope + flip share to kill probes early.
  Here the ratio of the two becomes the controlled quantity for the continuous
  parts: the embedding/norm/scale groups should train fastest exactly when the
  structure they must fit is both moving *and* improving, and should quiet down
  when flips have stopped buying loss (late-run churn), instead of fitting noise
  at full speed.
- **control law (signal → rule → bounds):** every 50 steps, productivity
  `p = −ΔL₁₀₀ / max(F₅₀, 1)` where ΔL₁₀₀ is the change in 100-step EMA train
  loss across the window and F₅₀ is the flip count in the last 50 steps
  (`step()` already returns flip share; the trainer accumulates it). Normalise
  by the run's own first-window productivity p₀. Rule:
  `lr_mult = clip(p/p₀, 0.4, 1.5)`, applied to all AdamW param groups in
  `Layered.opt`, smoothed: `lr_mult ← 0.7·lr_mult_prev + 0.3·clip(p/p₀, …)` so
  no single window moves lr by more than ~±20%. Base lr stays 1e-3; bounds are
  the multiplier's.
- **exact train.py change:** new flag `--prod-lr` on `Layered`: trainer keeps
  `self.flip_hist` (from its own `jumped/total` accounting, already computed),
  a loss EMA fed by the `loss` argument, and every 50 steps rewrites
  `g["lr"] = self.base_lr * self.lr_mult` for each param group — the same
  param-group write `--cooldown` already performs in this class, but driven by
  p/p₀ instead of `done`. lr_mult, p/p₀ logged every 100 steps.
- **stability guard / own failure mode:** the failure mode is **Goodharting the
  ratio**: lr itself affects ΔL, so the controller can discover that *cutting*
  lr makes short-window ΔL smoother and drive itself to the 0.4 floor and call
  it productivity — a controller gaming its own signal by changing the
  measurement conditions. Guards: p₀ is frozen from the first window (the
  yardstick cannot drift with the controller's own actions); the denominator
  floor `max(F₅₀, 1)` plus a rule that windows with F₅₀ < 0.02% of weights
  *hold* lr_mult rather than update it (near-zero flips make the ratio
  meaningless, not infinite); and the 0.4 floor guarantees the FP parts never
  train slower than the closed `--cooldown` arm's mid-run rate, so the worst
  case degrades toward a known arm, not an unknown one.
- **prediction:** −0.01..−0.03. Predicted trajectory: lr_mult ≈ 1.3–1.5 early
  (flips buying loss at the highest rate of the run), decaying through 1.0 to
  the 0.4–0.6 range late — i.e. the controller is expected to *invent* something
  shaped like a cooldown, but timed by measured payoff rather than by the clock
  that defined the closed arm; if it instead holds ≈1.0 throughout, productivity
  is scale-free in this trainer and G-002's share signal was sufficient.
- **status:** queued
```mill
id: K-017
mode: process
run: --arm layered_half --rope --prod-lr
```

### K-018 · Coherence-servoed V: the threshold prices how much the vote stream agrees with itself
- **source:** WH-058's premise (the informative action is *under* the flips, in
  the counters' path) reduced to its cheapest statistic. Define per-step vote
  coherence `a_t` = fraction of gated weights whose vote sign equals the sign of
  their own counter's accumulated direction (c1 and c2 pooled; counters at 0
  excluded). Coherence is the vote stream's self-consistency: high a means
  successive batches keep pushing the same way (evidence is a signal, a low V
  suffices); low a means the stream is arguing with its own recent past
  (evidence is mostly noise, and V — the number of net votes demanded — is
  exactly the dial that prices noise). F-026 prices *magnitude* volatility into
  a spread; A-011/A-012 filter the evidence per weight. Neither moves the global
  threshold on the stream's sign-consistency.
- **control law (signal → rule → bounds):** ā = EMA₂₀ of a_t, sampled every
  20 steps. Rule (stepwise proportional, deadbanded): `V ← V − 2 if ā > 0.75`,
  `V ← V + 2 if ā < 0.55`, else hold. Bounds V ∈ [16, 56] — the floor 16 is
  held at twice the poisoned anneal arm's hot start (8) deliberately, and the
  entry states why: coherence is *lowest* early, when gradients are least
  settled, so this controller's natural early move is to raise V, away from the
  known poison, not toward it.
- **exact train.py change:** new flag `--cohere-v` on `Layered`. In `step()`,
  after `vote` is formed (it already exists as a tensor), per layer compute
  agreement against the pre-update counters:
  `agree = (vote.sign() == c1.sign()) & (c1 != 0)` pooled with the c2 analogue
  over gated (strong) weights only; accumulate into `self.a_ema`; every 20 steps
  apply the rule to `self.votes`. No new per-weight state; ā and V logged
  every 100 steps.
- **stability guard / own failure mode:** the failure mode is a **coherence
  trap**: raising V means fewer flips, counters live longer and accumulate more
  one-directional history, so measured coherence *rises mechanically* — the
  controller then lowers V, flips resume, coherence falls, and the pair
  oscillates with the period of the counter lifetime (~V steps), not of any real
  signal. Guards: coherence is measured only on gated weights with |c| < V/2
  (young counters, whose sign is recent evidence, not the controller's own
  residue — this restriction is the guard, stated as part of the law); the
  ±2 step is small against the [16, 56] range; and the deadband [0.55, 0.75]
  is wide because ā's null level under random signs is 0.5 — the controller
  must see agreement clearly above chance before it spends threshold on it.
- **prediction:** −0.01..−0.03, with the highest diagnostic value in this file
  after K-013: ā's trajectory is the first published trace of vote-stream
  self-consistency for this trainer, and if ā sits inside the deadband for the
  whole run the entry retires itself with that number attached.
- **status:** queued
```mill
id: K-018
mode: process
run: --arm layered_half --rope --cohere-v
```

### K-019 · Meta-loop: loss slope sets F-028's admitted-mass setpoint
- **source:** the second reserved meta-level: F-028's AGC holds admitted
  gradient mass at a set-point of 0.60 chosen by hand, forever. Whether 0.60 is
  right plausibly depends on training phase: early, gradients are diffuse and a
  0.60 mass target forces the gate wide (many marginal voters); late, gradients
  concentrate and 0.60 forces it narrow. This entry owns only the setpoint
  m*; F-028's fast-attack/slow-release inner loop is untouched.
- **control law (signal → rule → bounds):** outer signal ρ = normalised
  train-loss slope, computed exactly as in K-015 (trailing-100-step slope ÷
  first-100-step slope), sampled every 100 steps. Rule:
  `m* ← m* + 0.03 if ρ > 0.7` (loss still falling fast — evidence is plentiful,
  admit more of its mass), `m* ← m* − 0.03 if ρ < 0.3` (flattening — restrict
  the vote to the strongest mass), else hold. Bounds m* ∈ [0.45, 0.75],
  initialised at F-028's 0.60. Inner loop reads m* in place of its constant.
- **exact train.py change:** new flag `--meta-agc` on `Layered`, requires
  `--agc` (F-028) active: the AGC's per-layer `q_t` update reads
  `self.m_star` instead of the literal 0.60; `self.m_star` updated in `step()`
  on `self.steps % 100 == 0` from the loss ring buffer shared with K-015's
  plumbing (if both meta flags are ever combined, they share the buffer and
  update on the same tick — noted, not pooled as a combination here).
  m* and ρ logged every 100 steps.
- **stability guard / own failure mode:** the failure mode is **setpoint
  chasing a moving inner loop**: AGC's q_t needs ~20–50 steps to re-settle after
  m* moves (slow release is 0.005/step by F-028's own law), so an outer tick
  every 100 steps is only ~2–5 inner time-constants — marginal separation, and
  this entry says so rather than claiming cascade textbook conditions. Guards:
  the ±0.03 step is small against the [0.45, 0.75] range (a full traverse takes
  ≥1,000 steps); the deadband on ρ ([0.3, 0.7] = hold) means m* moves only on
  a clear phase change; and the post-update 10-step slope exclusion from K-015
  applies here too. Second failure mode: ρ falls late in *every* run, so m*
  will predictably end low — if the end state is all the entry produces, it has
  reinvented a schedule with extra steps; the probe's defence is that the *time*
  of the descent is slope-triggered, and a paired fixed-m* F-028 probe at the
  same budget is the required control.
- **prediction:** −0.005..−0.02 over F-028 alone — the smallest expected effect
  in this file, filed because the setpoint question is currently answered by a
  constant nobody chose on evidence, and the meta-level is where the brief
  points. Kill criterion stated in advance: if m* never leaves [0.57, 0.63],
  the hand-set 0.60 was right and the entry retires at probe.
- **status:** queued
```mill
id: K-019
mode: process
run: --arm layered_half --rope --agc 0.60 --meta-agc
```

### K-020 · Per-layer frustration leak: K-014's dial, at the scope WH-051 predicts
- **source:** WH-051's per-layer prediction — frustration concentrates in `down`
  projections by ≥2× over `qkv` — taken as a scoping instruction. K-014 applies
  one global λ bought with global memory loss; if the frustrated population
  really lives in two of the eight BitLinear layers of `layered_half`, a global
  leak pays eight layers' worth of forgetting for two layers' worth of problem.
  This is a distinct entry from K-014, not a dose of it: the controlled
  variable is a per-layer vector λᵢ, and the falsifiable claim is about scope.
- **control law (signal → rule → bounds):** per-layer frustrated fraction
  fᵢ (WH-051's definition, per layer), EMA₂₀, sampled every 20 steps.
  Per-layer rule, same anchor as K-014 applied independently:
  `λᵢ = clip(1.0 − 0.6·max(0, f̄ᵢ − 0.04), 0.96, 1.0)`. Layers at or below 4%
  frustration run the champion's exact update; only frustrated layers leak.
- **exact train.py change:** new flag `--frust-leak-layer` on `Layered`; same
  int16 fixed-point counter promotion as K-014 (charged identically). The
  frustrated-mask computation in `step()` is already per layer (the loop is
  `for i, m in enumerate(self.layers)`); this entry keeps `self.f_ema` and
  `self.lam` as per-layer lists and applies `self.lam[i]` inside layer i's
  counter update. Per-layer f̄ᵢ logged every 100 steps (8 numbers).
- **stability guard / own failure mode:** the failure mode is **inter-layer
  desynchronisation**: layers leaking at different rates hold evidence of
  different ages, so a downstream layer's counters describe a network whose
  upstream layers have since forgotten why they flipped — cross-layer staleness
  (F-010's named pathology) manufactured by the controller itself. Guards: all
  λᵢ share K-014's floor (0.96) and anchor, so the maximum evidence-age ratio
  between any two layers is bounded at ~25 steps of horizon difference; the
  shared 4% deadband keeps the vector at all-1.0 (champion) whenever frustration
  is diffuse rather than concentrated — i.e. this controller activates *only*
  in the regime WH-051 predicts, and is inert in the regime that would convict
  its premise. Oscillation guard inherited from K-014 (EMA + 20-step sampling
  per layer).
- **prediction:** −0.01..−0.03 vs champion, and ≥ K-014's effect if WH-051's
  concentration prediction holds; if frustration turns out diffuse, K-020 ≈
  K-014 by construction and the pair together measure the concentration —
  run K-014 first; K-020's probe is only interpretable second.
- **status:** queued
```mill
id: K-020
mode: process
run: --arm layered_half --rope --frust-leak-layer
```

### K-021 · Kurtosis-pre-empted gate: tighten before the loss spike, not after
- **source:** WH-059 (counter-kurtosis early warning: field-shape spikes precede
  loss spikes) — the only *predictive* signal in WH-049..060, and the only one
  whose value exists solely if it is acted on *before* the event it predicts.
  Every other entry in this file is feedback (react to a measured state); this
  one is feedforward: kurtosis of the counter distribution is the leading
  indicator, the gate is the actuator, and the loss spike is the event being
  pre-empted. Distinct from F-028 (reacts to admitted mass, a coincident
  signal) and K-016 (reacts to contest, a coincident signal).
- **control law (signal → rule → bounds):** signal: excess kurtosis K_t of the
  pooled counter distribution (c1, c2), computed every 10 steps from the
  counters' moments (no dump needed — four reductions). Baseline K₀ = median of
  K over the run's first 100 steps, frozen. Rule (event-driven, not
  proportional): if K_t > K₀ + 2.0, tighten the gate for the next 30 steps:
  `q = 0.7`; if K_t > K₀ + 4.0, `q = 0.85`. When neither condition has fired for
  30 consecutive steps, q returns to 0.5. The gate never loosens below the
  champion's 0.5. Each firing logged with step and K_t.
- **exact train.py change:** new flag `--kurt-gate` on `Layered`: moments
  accumulated inside the existing per-layer counter loop into four global sums,
  K assembled every 10 steps in `step()`; q applied exactly as in K-016
  (`quantile(self.q)` in place of `median()`), with `self.q` driven by this
  entry's event rule instead of K-016's proportional rule. The two gate
  entries share one plumbing change and must not be combined in one arm.
- **stability guard / own failure mode:** the failure mode is **crying wolf
  into a self-fulfilling calm**: if kurtosis spikes are actually *caused* by
  healthy large-scale reorganisation, tightening the gate suppresses the
  reorganisation, no loss spike follows, and the controller logs a perfect
  prediction record for events it prevented from being testable — unfalsifiable
  success, the worst outcome in this lab's terms. Guard, stated as part of the
  entry: the probe must report firing count and the counterfactual cannot be
  recovered from the same run, so the entry is judged **only** on held loss vs
  champion, never on "spikes avoided"; a flat held result with many firings
  retires it (it paid gate-tightening costs to prevent nothing measurable).
  Second guard: the 30-step tightening window is fixed and non-retriggerable
  while active, so a sustained high-K regime tightens in discrete 30-step
  blocks with 0.5-gated gaps between them — the run can never be locked into a
  permanently tightened gate by one long event.
- **prediction:** −0.005..−0.02 on average, but the distribution is the claim:
  most seeds ≈ champion (no spikes to pre-empt), the gain concentrated in the
  worst seed — this is a variance-reduction entry, judged on worst-seed held
  across the probe's seeds, and it should be promoted or killed on that
  statistic, not the mean.
- **status:** queued
```mill
id: K-021
mode: process
run: --arm layered_half --rope --kurt-gate
```

### K-022 · Oscillation-taxed leak: sub-flip thrash shortens evidence memory
- **source:** WH-058 (sub-flip oscillation anatomy: the argument underneath the
  flips — counters that travel far and net little) as a control input. Define
  the oscillation index per layer from quantities the trainer can maintain
  exactly: over a trailing 50-step window, `o = Σ|Δc| / max(|ΣΔc|, 1)` pooled
  over weights — a random-walk counter has o ≫ 1, a steadily-pushed counter has
  o ≈ 1. A-005's deadband forgets counters inside a band (a fixed rule);
  MILL-209..213 fix λ globally. Neither prices *measured* thrash into the
  forgetting rate. High o means the gradient stream is spending votes reversing
  itself inside the counters; a shorter evidence horizon (stronger leak) makes
  those reversals cancel sooner and stops stale opposition from delaying flips
  that current evidence supports.
- **control law (signal → rule → bounds):** ō = global oscillation index,
  EMA over the 50-step window itself, sampled every 25 steps. Rule:
  `λ = clip(1.0 − 0.02·max(0, ō − 3), 0.97, 1.0)` — at ō ≤ 3 (already a
  reversal-heavy stream by the definition) no leak; each further unit of ō
  costs 0.02 of λ; floor 0.97 (horizon ~33 steps) is weaker than every pooled
  fixed dose except MILL-209's 0.99, deliberately: this controller's signal is
  noisier than K-014's census, so its authority is smaller.
- **exact train.py change:** new flag `--osc-leak` on `Layered`; same int16
  fixed-point counter promotion as K-014 (charged identically). Path sums
  require one extra int16 accumulator per counter (`self.path1/path2`,
  +4 B/weight — charged, and the reason this entry is not cheap): each step adds
  |vote| contributions into the path accumulator and net Δc into a second;
  every 25 steps ō is computed, the accumulators reset, λ updated and applied
  inside the counter update as in K-014. ō and λ logged every 100 steps.
- **stability guard / own failure mode:** the failure mode is **leak amplifying
  the thrash it measures**: shorter memory → counters reach V on shorter,
  noisier evidence → more flips → flips perturb gradients → more reversal → ō
  rises → more leak. A positive feedback loop with gain through the network
  itself, not just the arithmetic. Guards: λ's floor (0.97) caps the loop's
  authority below the weakest fixed dose the pool already tolerates as an
  *open-loop* constant — if the loop runs away it lands on a constant the lab
  has priced, not in uncharted territory; ō is computed over 50 steps and λ
  updates every 25, so the controller integrates over ≥2 flip-generation cycles
  before acting twice; and ō explicitly excludes weights that flipped inside the
  window (their path is post-reset and would read as pure oscillation — a
  measurement artefact, excluded by construction).
- **prediction:** −0.005..−0.025. Honest prior: this is the entry most likely to
  return a clean zero — ō may sit ≤ 3 for the whole champion run, in which case
  the arm is the champion plus logging, and WH-058 learns that sub-flip thrash
  at this scale is modest. Filed because a priced zero on the lab's most-cited
  unmeasured pathology is worth one probe.
- **status:** queued
```mill
id: K-022
mode: process
run: --arm layered_half --rope --osc-leak
```

### K-023 ★ · The watchdog: a meta-controller that detects a servo oscillating and takes its authority away
- **source:** supervisory control / gain-scheduling practice — every inner loop
  filed in this wave (and MILL-207, F-028 before it) carries an oscillation
  failure mode that its own guards *reduce* but cannot *detect*. Detection
  requires standing outside the loop and watching the dial itself, which no
  filed entry does. This entry controls no dial directly: it watches one inner
  controller (specified per arm; the pooled form watches K-013's V), measures
  the dial's own dynamics, and degrades the inner loop's authority in graded
  steps when the dial — not the loss, not the signal — shows a limit cycle.
  It is the meta-level in its purest form in this file.
- **control law (signal → rule → bounds):** signal: the inner dial's trajectory
  (e.g. V_t sampled at its own update ticks). Oscillation statistic: sign-change
  count of Δdial over the trailing 12 ticks, `z`, plus dial range over the same
  window, `r`. Rule (graded, evaluated every 12 inner ticks): if `z ≥ 8` and
  `r ≥ 4` (V units; rescaled per dial), halve the inner loop's step size
  (K-013: ±1 → ±1 every *other* interval; generic form: step × 0.5, floored at
  0.25× nominal) — authority level 1. If oscillation persists for the next 12
  ticks at level 1, **freeze** the dial at its trailing-12-tick median for the
  rest of the run (authority level 2 — the arm degrades to a fixed-dial run at
  a measured, not guessed, value). If z ≤ 3 for 24 consecutive ticks at level 1,
  restore full authority (the watchdog can forgive). Bounds: the watchdog may
  never move a dial itself, never widen an inner loop's bounds, and never act
  before 24 inner ticks of history exist.
- **exact train.py change:** new flag `--watchdog` on `Layered`, composable with
  exactly one inner control flag (pooled form: `--sat-servo`); implementation is
  a small `Watchdog` class in `train.py` holding the dial's tick history, called
  from the inner controller's update site with (dial value, nominal step),
  returning the permitted step multiplier and a possible freeze value the inner
  update must honour. Watchdog level and every transition logged; the run record
  gains `watchdog_level_final`. Overhead: floats, no per-weight state.
- **stability guard / own failure mode:** the failure mode is **the watchdog
  mistaking adaptation for oscillation**: a healthy controller tracking a
  genuinely moving regime (early-run V *should* walk in one direction, then
  reverse once as the regime changes) can trip z ≥ 8 if the regime itself
  oscillates — e.g. batch-stream periodicity — and the watchdog then freezes a
  dial that was doing its job, converting a controlled run into a fixed-dial run
  at a mediocre value. Guards: the range condition `r ≥ 4` alongside z (a dial
  twitching ±1 around a point has z high but r small — that is deadband
  behaviour, explicitly *not* punished; only full-range hunting counts); the
  freeze value is the window *median*, not the current value, so a freeze lands
  mid-range rather than at an extreme; and level-1 halving precedes any freeze,
  giving a merely-noisy loop a chance to settle at reduced gain — the classical
  answer, since most limit cycles are gain problems before they are concept
  problems. The watchdog's own stability is trivially guaranteed: its actions
  are monotone in authority (full → half → frozen, with one forgiving edge),
  so it cannot itself oscillate a dial.
- **prediction:** ≈ 0.000 on arms whose inner loop is stable (the watchdog is
  inert — by design, and the probe must confirm inertness, not assume it) and
  −0.01..−0.03 of *insurance value* on arms where the inner loop hunts: the
  honest framing is that K-023 is not a gain entry, it is what makes the other
  eleven entries safe to promote past probe scale, where longer runs give limit
  cycles time to develop that a 75-second probe cannot exhibit. Judged on:
  (a) zero held Δ vs K-013 alone when inert, (b) in a deliberately
  destabilised control arm (K-013 with its deadband removed — a *test fixture*,
  not a pooled candidate), the watchdog restores held to within 0.01 of the
  guarded K-013.
- **status:** queued
```mill
id: K-023
mode: process
run: --arm layered_half --rope --sat-servo --watchdog
```

### K-024 · Dead-counter-servoed lr on log_scale only: when structure stops testifying, scales take the gradient alone
- **source:** WH-057 (dead-counter census: counters that never move — the
  silent-weight population as wasted capacity) crossed with F-001's insight
  that pressure which cannot move structure can still move scale. Scope is the
  narrowest in this file: of the AdamW groups, only `log_scale` (the per-layer
  install scales, whose gradient is the hand-set `(g·s)·scale`) is actuated.
  G-002 servos lr on flip share across emb/norm groups and *exempts* log_scale;
  this entry actuates exactly the group G-002 exempts, on a signal G-002 does
  not use.
- **control law (signal → rule → bounds):** signal `d_t` = dead fraction:
  share of counters (c1, c2 pooled) whose value has not changed in the trailing
  50 steps and which sit at |c| ≤ 2 (never engaged — distinct from WH-051's
  frustrated, who are maximally engaged and blocked). Tracked with a per-counter
  last-change step stamp (one int16 per counter, +4 B/weight — charged; see
  change). Sampled every 50 steps, EMA-smoothed (α=0.3 at that cadence). Rule:
  `scale_lr_mult = clip(1.0 + 4·max(0, d̄ − 0.15), 1.0, 2.0)` — below 15% dead,
  scales train at the champion's lr; at 35% dead, they train at 2× — the layer's
  magnitude channel works harder exactly when its structural channel has gone
  quiet. All other param groups: champion lr, untouched, forever.
- **exact train.py change:** new flag `--dead-scale-lr` on `Layered`: the
  `log_scale` parameters are split into their own param group at `self.opt`
  construction (today they are appended to the single AdamW call in
  `Layered.__init__` — the split is mechanical and changes nothing at mult 1.0);
  `self.last_change` int16 tensors updated in `step()` wherever counters are
  written (`torch.where(c_new != c_old, step, last_change)`); every 50 steps
  d̄ is computed, and the scale group's `lr` rewritten as in K-017's plumbing.
  d̄ and scale_lr_mult logged every 100 steps.
- **stability guard / own failure mode:** the failure mode is **scales absorbing
  the loss that structure should have taken**: raising scale lr lets the model
  buy loss reductions by rescaling layers instead of flipping weights, counters
  go *deader* as gradients shrink through rescaled layers, d̄ rises, scale lr
  rises again — a quiet runaway that ends with a well-scaled random-ish
  structure, F-055's reservoir wearing a fitted suit. Guards: the 2.0 cap (the
  runaway, if it starts, saturates at a bounded, known rate); the deadband at
  15% (WH-057 has never published the champion's dead fraction — if it is
  naturally ~30%, the anchor is wrong and the probe's first log line says so,
  which is why the anchor is stated as a number and not hidden); and the
  decisive audit is built into the prediction — dead fraction and flip share are
  both already logged quantities, so the runaway's signature (d̄ ↑, flips ↓,
  held flat) is distinguishable from the intended signature (d̄ ↓ as scales
  re-shape gradients, held ↓) in a single probe record.
- **prediction:** −0.005..−0.02, the weakest prior in this file, filed last
  deliberately: it is the only entry whose actuated parameter can *substitute*
  for the mechanism under study rather than assist it, and the lab should learn
  that price from its cheapest possible experiment. Kill criterion: if d̄ at
  probe end exceeds its value at the first sample while held is not better than
  champion, retire without a trial.
- **status:** queued
```mill
id: K-024
mode: process
run: --arm layered_half --rope --dead-scale-lr
```

---

## Coordinator's ranking and the one to trust first

**★ Top 3: K-013, K-015, K-023.**

1. **K-013 — trust this one first.** Its signal is the only one in the file
   that is (a) exactly computable from tensors already live inside
   `Layered.step` (zero new state, zero estimation), (b) mechanically coupled
   to its dial — a backlog of executable flips behind the threshold *is* a
   statement about the threshold, with no interpretive step in between — and
   (c) bounded into harmlessness: ±1 per 20 steps inside [20, 48] with a wide
   deadband means the worst case is a run that wanders gently around V=32,
   i.e. around the champion. Every other entry inserts at least one inference
   (that contest means noise, that kurtosis means danger, that slope means
   churn stopped paying); K-013's inference is one step long. It also produces,
   as a by-product, the executable/frustrated split of WH-051's census that the
   forensics wave never separated.
2. **K-015** — the cleanest meta-level entry: it files no new inner loop, it
   repairs the one arbitrary constant inside an already-pooled servo
   (MILL-207's fixed flip-rate target), and its guard (≥5× timescale
   separation) is the textbook condition, checkable from the design rather than
   hoped for.
3. **K-023** — expected value ≈ 0 as a gain and highest as infrastructure:
   it is the only entry that makes the *rest* of the closed-loop programme
   promotable to long horizons, where the limit cycles it exists to catch have
   time to appear. Its destabilised-fixture test is the most falsifiable
   protocol in the file.

**Run order note:** K-014 before K-020 (scope question is only interpretable
in that order); K-016 and K-021 share gate plumbing and must never be combined
in one arm; K-019's probe is uninterpretable without a paired fixed-setpoint
F-028 control at the same budget.

*End of wave-6 lens 2 (meta-control). 12 entries, K-013..K-024, all queued,
all `mode: process` on `--arm layered_half --rope`. Champion held 2.8580 ±
0.0161 is the bar throughout.*

## Lens 3 — Scarcity (was SC-###)

### K-025 ★ · Multi-threshold shadow counters — one gradient, three vote extractions (V = 8 / 32 / 128)
- **source:** vote-trainer structure + DATA-AUDIT scarcity premise. The champion commits
  every weight to a single flip threshold V=32. A gradient read at V=8 extracts fast,
  noisy flips; at V=128, slow, high-confidence flips. Today two of those three reads are
  computed (the signed vote exists) and then discarded by the single-threshold choice.
- **mechanism:** Each step's signed vote feeds THREE independent int8 shadow counters per
  weight, at thresholds 8, 32 and 128. Only one counter set is *live* (its flips change
  the weights); the other two run as shadows — they flip a shadow ternary state that is
  never installed. Every 200 steps, each layer's live threshold is re-chosen as the shadow
  whose shadow-state, scored on a fixed 8-window dev micro-batch (already in memory, no
  training tokens spent), has the lowest loss. No extra forward/backward on training data:
  the vote is extracted three ways from the one gradient already computed.
- **exact change:** new flag `--shadow-v 8,32,128 --shadow-eval 200` on Layered in
  train.py: triple counter arrays (state cost +2 B/weight, reported, not hidden), shadow
  flip bookkeeping, periodic per-layer threshold selection on the dev micro-batch.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.02..−0.05 held loss vs the equal-token champion control**
  (same 458,752 pieces, same steps). Honest correlation price: the three extractions share
  one sign stream, so this is NOT three independent runs' worth of evidence — the
  effective extra information is the *threshold-selection* signal only, worth roughly one
  free hyperparameter search over V per layer, which is why the claim is −0.02..−0.05 and
  not the −0.08+ a naive "3× the reads" story would suggest. Distinct from F-022
  (Benna–Fusi cascade: fast counter *drives* a slow one, serial transfer) — here the
  counters are parallel, independent, and selection is by measured dev loss; distinct
  from MILL-207/208 (one adaptive V targeting a flip rate — here V is discrete-chosen by
  loss, not servoed by flip count).
- **status:** queued

### K-026 ★ · Gradient-alignment curriculum — order fresh windows by transfer value, not by loss
- **source:** scarcity premise + the gap in A-041..A-056: every pooled curriculum orders
  or samples by a property of the window ITSELF (its init loss, its Δloss, its coverage).
  None measures what a scarce-token regime actually needs: what training on this window
  does to the REST of the distribution.
- **mechanism:** Maintain a fixed probe gradient g_probe = mean gradient over 16 held-out
  (never-trained) windows, refreshed every 200 steps from the current weights (one extra
  backward per 200 steps = 0.5% token overhead, charged below). Each candidate fresh
  window is scored once, forward+backward on its first appearance, by
  value = cos(g_window, g_probe). Windows are then trained in descending value order
  within each 512-window block. A window whose gradient points where the probe gradient
  points teaches generalisable signal; a window with high loss but orthogonal gradient
  teaches only itself — in a 0.91M-piece corpus, the second kind is the waste.
- **exact change:** new flag `--align-curriculum 512` in the sampler: probe-gradient
  computation, per-window cosine scoring at first sight, block-local descending sort.
  Fresh windows only — no window is ever re-trained by this entry (replay is D-wave
  territory, deliberately excluded).
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.03..−0.08 held loss vs the equal-token control**
  (random-order champion, same 458,752 pieces, control credited with the same 0.5%
  probe overhead as extra training tokens). The wide range is honest: alignment scoring
  is one backward per window that the control spends on a second training pass instead,
  so the net claim already nets out that cost; the effect should be largest exactly
  because the corpus is small and heterogeneous (German sentences vs project prose vs
  residual boilerplate want very different things from the weights).
- **status:** queued

### K-027 ★ · Entropy-selected loss positions — spend the vote budget where the model is actually uncertain
- **source:** DATA-AUDIT §2: median line is 9 pieces in v1 (36 in v2); a 256-piece window
  is mostly collage, and a large share of its positions are near-deterministic (spaces —
  token 222 alone is 10.2% of all pieces — boilerplate continuations, separator runs).
  The champion extracts votes from all 256 positions equally, so most of each batch's
  vote mass is spent confirming what is already known.
- **mechanism:** Per window, run the forward pass as usual; compute per-position entropy
  of the predictive distribution; the loss (and therefore every vote and every FP-part
  gradient) is taken over only the top-50% entropy positions of that window. The other
  positions still serve as context — they are simply not paid for as targets. This is
  credit-assignment sharpening at the position level: the same tokens, half the target
  positions, all of the vote mass concentrated on positions carrying information.
- **exact change:** new flag `--loss-topk-entropy 0.5` in train.py: per-position entropy
  from the existing logits (no extra forward), top-k mask applied to the CE before
  backward. Positions are selected per window, per step, from the current model — not
  from a static list.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.01..−0.04 held loss vs the equal-token champion control**
  (same windows, same pieces seen as context; control takes loss on all positions).
  Priced honestly: halving target positions halves the gradient's token count in the
  statistical sense, so part of the concentration gain is paid back in gradient variance —
  the claim survives only if the discarded positions were really near-zero-information,
  which the audit's token distribution says they mostly are. Distinct from A-052
  (span-noise *input* masking, objective unchanged) and A-049 (frequency-based loss
  downweighting — a static token property; entropy here is the model's own live
  uncertainty at that position, so a rare-but-predictable position is also skipped).
- **status:** queued

---

## Remaining entries

### K-028 · Second-read voting — re-vote the same gradient after the flips it caused have landed
- **source:** vote mechanics: a step's votes are computed against the pre-flip weights.
  When a batch of flips fires, the loss surface changes, and part of the gradient's
  signal was "spent" pushing weights that have now moved — the residual signal in that
  same gradient (its push on the weights that did NOT flip, re-read against the new
  state and the layered gate) is currently discarded and the batch is never seen again.
- **mechanism:** After each step's flips are installed, re-apply the SAME cached signed
  vote vector once, through the gate, against the new ternary state, into the counters
  only (no flip check on the second read — counters accumulate, flips wait for the next
  real gradient). No new forward, no new backward, no data replay: the tokens are not
  re-seen, only their already-paid-for gradient is read a second time against the state
  it changed.
- **exact change:** new flag `--second-read` on Layered: cache the step's signed vote
  tensor, one extra gate+counter pass post-flip per step.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.005..−0.02 held loss vs the equal-token champion
  control.** Correlation priced at its harshest: the second read is ~fully correlated
  with the first, so the claim is only the small state-dependence term — if the gate's
  state-dependence is weak at this scale this reads ~0, and that null is itself the
  measurement of how state-dependent the vote extraction really is. Distinct from
  D-wave replay (no data is re-presented, no extra forward) and from A-003
  (batch-aggregated votes change WHEN votes fire; this changes how many times one
  gradient is read).
- **status:** queued

### K-029 · Per-token vote-mass normalisation — every position gets an equal say in total
- **source:** gradient anatomy: a position's contribution to a weight's gradient scales
  with its activation and error magnitude, so a few loud positions (number streams,
  boilerplate with large errors) can dominate a batch's entire vote while quiet,
  informative positions are outvoted. A-040 clips the GLOBAL gradient norm before
  signing — one budget for the whole batch. Nothing gives each token position its own
  budget.
- **mechanism:** Before signing, rescale each position's per-token gradient contribution
  so that every position contributes equal total L1 vote mass across weights
  (per-position normalisation of the token-gradient outer products, applied in the
  backward hook where per-token gradients are still separable — first and last layers
  exactly, middle layers via the standard per-token activation×delta factorisation).
  Loud positions keep their direction; they lose their volume advantage.
- **exact change:** new flag `--vote-mass-norm` in train.py's vote extraction path.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.01..−0.03 held loss vs the equal-token champion
  control**, concentrated in the v1 corpus where numeric/boilerplate positions are
  loudest; expected smaller on v2. Distinct from A-013 (weights votes by the token's
  LOSS level — loud tokens get MORE say there; here every token gets the SAME total
  say, direction only) and from A-049 (frequency downweighting — a corpus statistic,
  not a per-batch mass budget).
- **status:** queued

### K-030 · Gradient-diversity batch composition — assemble batches whose windows disagree usefully
- **source:** batch statistics: 32 randomly drawn windows from a collage corpus often
  carry near-duplicate gradient content (the audit: 93.2% of lines belong to a duplicated
  group), so a random batch's effective information is well under 32 windows' worth.
  A-053 diversifies by SOURCE FILE; file diversity is a proxy — two files can teach the
  same thing, one file can teach two.
- **mechanism:** Keep a cheap gradient sketch per candidate window: the sign vector of
  its last-layer gradient from its most recent scoring pass (256-dim projection, stored
  int8). Assemble each batch greedily: start from a random window, then repeatedly add
  the candidate whose sketch has the lowest mean cosine similarity to those already in
  the batch, from a candidate pool of 128. Batch size, token count and step count are
  unchanged — only WHICH windows share a batch changes.
- **exact change:** new flag `--diverse-batch 128` in the sampler: sketch store,
  greedy min-similarity assembly per step.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.01..−0.03 held loss vs the equal-token champion
  control** (random batches, same pieces per run in expectation — the sampler draws
  without replacement within each pass so total token exposure matches). Honest cost:
  sketches are one step stale, so the diversity is approximate; the claim is sized for
  approximate, not oracle, decorrelation.
- **status:** queued

### K-031 · Rare-token-density window upsampling — pay more visits to the windows that carry the tail
- **source:** DATA-AUDIT §2: 1,984 of 3,548 used tokens appear <100 times in the whole
  corpus. Under uniform sampling those tokens' embeddings and head rows receive almost
  no gradient, while token 222 (space, 10.2%) is trained to exhaustion. The information
  per token of a window scales with how much of the tail it carries.
- **mechanism:** Score each window once by rare-token density = fraction of its pieces
  whose corpus frequency is <100. Sampling probability ∝ (1 + 2 × density), normalised,
  drawn with replacement caps so no window exceeds 3 visits per pass. Loss and votes are
  untouched — this is purely which windows the token budget is spent on.
- **exact change:** new flag `--rare-upsample 2.0` in the sampler, using corpus
  frequency counts computed at load.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.01..−0.03 held loss vs the equal-token champion
  control** (uniform sampling, same total pieces trained). Nearest neighbour A-049
  downweights frequent tokens INSIDE the loss; this upsamples tail-carrying WINDOWS
  in the sampler and leaves the loss alone — the two compose, and either can win alone.
  Risk priced in: over-visiting tail windows can overfit their specific contexts; the
  3-visit cap is the guard, and the low end of the range assumes it binds.
- **status:** queued

### K-032 · Probe-aligned per-layer vote scaling — layers that teach the probe get louder votes
- **source:** credit assignment across depth: all layers receive votes at the same
  threshold economics (MILL-207 varies V by flip RATE — a layer-local statistic). No
  entry scales a layer's vote increments by whether that layer's gradient agrees with
  the direction the whole model needs to move.
- **mechanism:** Using K-026's probe gradient (or a standalone 16-window probe,
  refreshed every 200 steps, 0.5% overhead charged), compute per-layer alignment
  a_l = cos(g_l, g_probe,l). Scale layer l's vote increments by (1 + a_l), clipped to
  [0.5, 1.5]. Layers pushing with the generalisable gradient accumulate evidence
  faster; layers pushing against it must prove themselves over more tokens.
- **exact change:** new flag `--probe-vote-scale` on Layered: per-layer alignment
  computation at refresh, increment multiplier in the vote step. Usable without
  K-026 (own probe), additive with it (shared probe, overhead counted once).
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.005..−0.025 held loss vs the equal-token champion
  control** credited with the probe overhead as training tokens. Expected to be the
  smaller sibling of K-026: it reweights evidence instead of choosing data, so its
  ceiling is lower and its variance is lower too.
- **status:** queued

### K-033 · In-batch n-gram loss deduplication — a repeated span inside one batch teaches once
- **source:** DATA-AUDIT §4: duplication is usually handled BETWEEN windows (A-047
  removes near-duplicate windows; G-015 moats the held set). But within a single batch
  of 32 collage windows, the same boilerplate 8-grams recur across windows, and each
  recurrence casts its own votes — the batch pays full price repeatedly for one piece
  of information.
- **mechanism:** Within each assembled batch, hash every 8-gram of target pieces; for
  any 8-gram occurring in more than one window of the batch, keep the loss (and votes)
  only at its first occurrence's positions and mask the later occurrences' positions
  out of the loss. Context is untouched; only duplicate target positions stop voting.
- **exact change:** new flag `--batch-dedup-ngram 8` in train.py: per-batch 8-gram
  hash pass over the target tensor, position mask merged with the CE mask.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.005..−0.02 held loss vs the equal-token champion
  control** on v1 (where in-batch duplication is rampant); expected ~0 on v2, and the
  entry should be run on v1 first precisely because that contrast prices how much of
  v1's token budget is intra-batch waste. Distinct from K-027 (entropy selects by
  model uncertainty; this removes by exact content repetition, model-free).
- **status:** queued

### K-034 · Ultra-frequent-target vote muting — positions predicting space cast no votes
- **source:** DATA-AUDIT §2: the top targets (space 10.2%, BOS, newline) are learned
  almost immediately and thereafter generate large volumes of near-zero-information
  votes that still move counters — noise with a voting franchise. A-049 downweights
  frequent tokens in the LOSS for all parameters; the FP parts (embeddings, norms,
  scales) may still want that loss. The ternary side is where the waste is.
- **mechanism:** For target positions whose gold token is in the corpus top-5 by
  frequency, the position contributes to the FP-part loss as usual but its gradient
  is excluded from the VOTE extraction (ternary counters see nothing from it). One
  mask, applied only at the vote step.
- **exact change:** new flag `--vote-mute-topk 5` on Layered/Direct trainers: target-
  frequency mask in the vote path only.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.005..−0.02 held loss vs the equal-token champion
  control.** Small, cheap, and honestly bounded: it can only recover the counter-noise
  those positions inject, and if the champion's counters are not in fact polluted by
  them this reads 0 — a clean diagnostic either way.
- **status:** queued

### K-035 · Equal-token batch ramp — batch 16 early, 64 late, same total pieces
- **source:** step economics: at fixed tokens, batch size trades steps against gradient
  noise. Early training wants many steps (structure finding); late training wants
  low-noise gradients (fine convergence). MILL-1201..1203 and C-B05/B06 measure FIXED
  batch sizes; no entry spends the same tokens as a RAMP.
- **mechanism:** Batch 16 for the first third of the token budget, 32 for the middle
  third, 64 for the final third. Total pieces identical to the control (458,752);
  step count differs by design (that IS the mechanism) and is reported, not hidden.
- **exact change:** new flag `--batch-ramp 16,32,64` in train.py's step loop.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.01..−0.03 held loss vs the equal-token champion
  control** (fixed batch 32, same pieces). This is the one entry whose gain, if any,
  is purely an allocation effect — same tokens, same model, same votes, different
  grouping — which makes it the cleanest test in the file of whether grouping alone
  carries information value.
- **status:** queued

### K-036 · Anti-correlated window pairing — cancel the batch's common-mode gradient
- **source:** F-009 subtracts the layer's MEAN VOTE (common-mode rejection inside the
  counter). The data-side analogue is unclaimed: if a batch's windows share a strong
  common gradient component (same boilerplate, same source dialect), that component is
  counted 32 times while the windows' individual signals are counted once.
- **mechanism:** Assemble each batch as 16 PAIRS: for each seed window, pair it with
  the candidate window (from a 128-pool, using K-030-style last-layer gradient
  sketches) whose sketch is most NEGATIVELY correlated with the seed's. Paired windows
  are trained in the same step, so their shared common-mode components cancel in the
  batch-mean gradient while their opposed, window-specific components survive signing
  with relatively more weight.
- **exact change:** new flag `--anticorr-pairs 128` in the sampler: sketch store
  (shared implementation with K-030 if both land), pair assembly per step. Batch
  size and token count unchanged.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.005..−0.02 held loss vs the equal-token champion
  control.** Deliberately the most conservative claim in the file: cancellation also
  removes genuinely shared signal (the language's common structure IS partly
  common-mode), so the net could be ~0; the pairing is the experiment that prices how
  much of the batch gradient is corpus dialect versus transferable structure.
- **status:** queued

---

## Honest summary

- **Count:** 12 entries (K-025..K-036), all `process` mode, all judged per token
  against the same equal-token champion control (458,752 pieces).
- **Largest per-token gain I can defend:** **≈ −0.05 held loss** — the top of K-025's
  range, with K-026's −0.08 upper end explicitly NOT defended as a point claim (its
  alignment-scoring cost and corpus heterogeneity make the wide range the honest
  statement; its defensible centre is ≈ −0.04). No entry claims √K scaling from
  correlated reads: K-025's three extractions share one gradient and are priced as a
  per-layer threshold search, K-028's second read is priced as a near-null diagnostic
  with a small positive tail.
- **What this lens deliberately did not file:** replay/dreaming variants (D-wave),
  loss-ordered curricula and coverage sampling (A-041..A-056), packing/overlap/deck
  constructions (G-wave), MTP/KD dense-target schemes (MILL-113..124), and any
  per-minute claim (throughput lens). If K-026 and K-030/K-036 both land, their
  sketch/probe infrastructure is shared and the second one's overhead should be
  re-ledgered at the shared cost, not the standalone cost.

## Lens 4 — Pool governance (was GV-###)

### K-037 ★ · Family budget: one slot per dose family per pass, siblings earn entry on signal
- **Structural problem:** Dose-stacking is the pool's default waste. PRIORITIES.md already had
  to hand-pick one point per family (WH-013 over dose siblings WH-020/WH-022; I-038 at 21 EP
  over I-037 at 97 EP and I-039 at 121 EP; G-066 sequential dosing praised precisely because it
  is the exception). Unbudgeted families in the files: vocab dial WH-013/020/022 (3 runs for one
  direction), leak MILL-209/210/211 + integer-leak MILL-212/213 (5), thrash-freeze
  MILL-215/216/217 (3), magnitude-calibrated MILL-201/202/203 (3), V-schedule MILL-204/205/206
  (3), modal readout MILL-218/219 (2), Fisher-flip share MILL-228/229/230 (3). At 75 s/probe a
  dead 3-dose family burns 3 probes to learn one fact; across ~30 dose families in the union
  that is roughly a full probe-pass of rent per generation.
- **Governance mechanism:** A per-pass **family budget**: each named dose family gets exactly
  **1 probe slot per pass** (its central/filed-best dose); a sibling unlocks only when the
  representative lands `promote` or `near` (Δ ≥ 0.02) — the G-066 rule, made pool law instead of
  one entry's private virtue. Families are identified by a `family:` tag (see K-040), not by
  judgement at merge time.
- **Exact change:** Add `family:` + `dose:` fields to the fenced `mill` block schema in
  IDEA-POOL.md; add a pass-planner step in `mill/screen.py` that groups queued entries by
  `family:` and admits only the family's designated representative until its ledger verdict is
  `promote`/`near`. PROMOTE.md gains one paragraph stating the rule and the unlock condition.
- **Payoff:** ~40–60 probes/pass saved at current pool size ≈ **0.9–1.3 mill-hours per pass,
  per generation**, compounding at every champion change (ledger keys are (idea, generation),
  so every generation currently re-buys every dose).
- **Risk:** A non-monotone dose curve (middle dead, extreme alive) is missed for one pass.
  Mitigated by the `near` unlock and by PROMOTE.md's existing human-exception path to trial.

### K-038 ★ · Premise graph: every entry declares its premises; a killed premise cascades
- **Structural problem:** Entries already depend on each other — the files say so, ad hoc, in
  prose nobody can execute on. Real, named dependencies found in F–J: **F-043** (V-scaling law)
  gates F-051/052/053/054 (all four 50M entries presuppose its answer), F-044/046/047/050 and
  I-018 (F-002 × F-043: "at the V the scaling law demands, the slow counter is reset to death");
  **WH-014** (embedding rows join the vote trainer; the 3.81 MB → ~0.86 MB byte claim and its
  ≤ +0.05-nat per-byte bar) is the stated plumbing premise of WH-016 ("depends on WH-014's
  embedding-vote plumbing; defer until it lands"), WH-018, WH-019 and combination I-020;
  **F-055** (reservoir control) is F-061's literal kill test ("retires if within 0.02 of
  F-055") and the premise of headline audit J-046; **G-026/G-030** gate G-035, whose own entry
  says it is "only worth its passes if at least one of them shows the counter field carries
  signal"; **WH-051** prices F-001's target population before F-001 may spend; the missing
  `--corpus v2` flag (E-018's path) silently blocks G-013–024's v2 subset, I-002, WH-039/044/048
  and G-024's v3 successor. Today, if F-043 reads flat or WH-014 fails its bar, nothing stops
  the mill from probing ~10 dependents against a dead premise and ledgering the noise as verdicts.
- **Governance mechanism:** A machine-readable **premise edge**: `premises: [F-043, WH-014]`
  plus `premise_kind: gates|prices|kill-test|plumbing`. When a premise entry's trial verdict is
  `below`/killed, every dependent is auto-flagged `premise-dead` in the ledger and skipped by
  screen.py until a human clears the flag — the cascade is a status, not a deletion.
- **Exact change:** `premises:` field in the `mill` block; a `mill/premises.json` edge list
  seeded with the ~25 edges named above (extracted verbatim from the candidate files' own
  "depends on / gates / ranked below deliberately" sentences); screen.py checks the edge list
  before queueing a probe and writes `premise-dead` skips to `mill/ledger.jsonl`.
- **Payoff:** Prevents the single most expensive failure mode available to this pool: a full
  dependent subtree probed against a dead premise. The F-043 subtree alone is ~9 entries
  (≈ 0.2 probe-hours/pass) plus up to three 24-min trials at 50M format — **~1–2 mill-hours
  saved per killed hub premise**, and verdict quality rises because dependents are never
  "measured" in a regime their own files call uninterpretable.
- **Risk:** A premise read as flat at probe scale may still hold at trial scale (the F-002
  lesson). Cascade therefore flags and skips — it never retires — and PROMOTE.md's exception
  path can clear any flag by name.

### K-039 ★ · Representative-entry clustering: collapse the 12-member readout cluster to 3 entries + variant notes
- **Structural problem:** The largest real near-duplicate cluster in the pool is the
  **post-training readout cluster, G-025–G-036 — all 12 members**: G-025 per-layer install-scale
  calibration · G-026 counter-resolved readout · G-027 checkpoint logit-ensemble · G-028 logit
  temperature · G-029 full-state checkpoint averaging · G-030 counter-soft install · G-031
  validation-selected checkpoint · G-032 disagreement-gated zeroing · G-033 per-head attention
  temperature · G-034 unigram prior-correction · G-035 measured greedy flip polish · G-036
  cross-seed logit ensemble. Twelve separate queue slots, ledger lines and report sentences for
  what is operationally **one eval session on the same existing checkpoints**, differing only in
  readout transform. PRIORITIES.md already collapsed two of them by hand (G-028 "fold into
  G-027's eval batch"; G-035 gated behind G-026/G-030) — proof the cluster is real and the fix
  is manual today. Cross-wave echoes widen it to 16: F-033 (split-stack ensemble), F-058
  (minority readout), I-034 (era-stratified modal readout), MILL-218/219 (modal readout).
- **Governance mechanism:** **Cluster entries**: one representative entry per cluster carries
  the queue slot; siblings become numbered **variant notes** inside it, executed in the same
  eval session in a filed order, each still ledgered under its own id so no verdict is lost.
  Cluster rule: same input state, same cost class, transforms that commute or are explicitly
  ordered — readout qualifies; training arms never cluster.
- **Exact change:** Merge G-025–G-036 into three representatives in IDEA-POOL.md —
  `G-026-cluster` (counter-field readouts: G-026, G-030, G-035, G-032), `G-027-cluster`
  (prediction-space readouts: G-027, G-036, G-028, G-033, G-034) and `G-025-cluster`
  (state-space readouts: G-025, G-029, G-031) — with the other nine ids preserved as variant
  notes; screen.py gains a `variant_of:` ledger key so variants share one session, not one verdict.
- **Payoff:** 9 queue slots and ~9 × (session setup + held eval) removed per pass; at
  eval-only prices this is **~0.5–1.0 mill-hour/pass**, and verdict quality improves because
  all 12 transforms are finally read against the *same* checkpoints in the *same* session —
  today they can drift across generations and become incomparable.
- **Risk:** Variant ordering effects (e.g. G-025's scale search before vs after G-026's
  resolution confounds both — PRIORITIES.md flags exactly this pair). The filed order inside
  the representative is therefore part of the entry, and any variant may be split back out by
  name if its interaction is the question.

### K-040 · Family census tag: no entry merges without a family, a lens and a cost class
- **Structural problem:** Nobody can currently answer "how much of the pool is X?" without
  re-reading 686 entries. The counts exist only as lens headers inside each wave file, and they
  already reveal skew the pool never chose: counter-centric entries dominate (the word "counter"
  appears 658 times across F–J; WH-049–060 is a 12-entry counter-forensics lens, I-025–036 a
  12-entry counter-ageing lens, and F-001–030 a 30-entry vote-mechanics block — together
  ~54 entries, ~17% of all candidates, orbit one int8 field), while whole axes (serving cost,
  safety) survive on single entries (WH-037, WH-015). PRIORITIES.md's top 40 had to be built by
  hand because the pool carries no census of itself.
- **Governance mechanism:** Mandatory merge-time metadata: `family:`, `lens_origin:`,
  `cost_class:` (sweep / process-flag / eval-only / full-trial-only / mill-change — the classes
  PRIORITIES.md already defined) on every entry, plus an auto-generated census table.
- **Exact change:** Extend the `mill` block schema in IDEA-POOL.md; add `mill/census.py`
  (counts entries by family × cost class × status, run at each merge) writing
  `mill/CENSUS.md`; CANDIDATES-F–J merges are blocked (by convention in PROMOTE.md) on the
  three fields being present.
- **Payoff:** Every future prioritisation, budget and coverage decision drops from hours of
  re-reading to one file read — conservatively **2–4 mill-hours saved per wave review**, and
  K-037/K-041/K-045 all become enforceable instead of aspirational.
- **Risk:** Tagging debt on the existing 368 pooled entries. Bounded: census.py can seed tags
  from the MILL number ranges (1xx research, 2xx vote-trainer, 6xx gate, 11xx shape…) and lens
  headers, leaving only genuinely ambiguous entries for a human pass.

### K-041 · Lens-quota abolition: waves file by expected value, not by 12-slot grids
- **Structural problem:** The 12-per-lens grid (GV preamble) guarantees over-supply of whatever
  a lens can generate 12 of, regardless of value: kernel-semantics I-049–060 includes I-050
  (own prediction: +0..+2% end-to-end) and I-060 (own prediction: likely worse than the
  champion) — entries PRIORITIES.md retired on sight — yet they consumed the same filing effort
  and will consume the same merge review as I-038. Conversely a lens with 20 strong ideas is
  capped at 12 and pushes its overflow into the next wave as "combinations" (I-013–024 is
  substantially wave F/G/H overflow wearing a × sign).
- **Governance mechanism:** Replace the per-lens quota with a **per-wave family budget**:
  a wave may file at most **6 entries per mechanism family** and at most **2 predicted-flat or
  predicted-negative controls** (controls are valuable — MILL-136, WH-072 — but they are a
  budget line, not a discovery), with any excess filed to a clearly-marked overflow annex that
  does not enter merge review until a family slot frees.
- **Exact change:** Protocol only: amend the Idea Engine wave brief template (the rotation
  instructions under `mill/.idea-engine/`) to state the 6-per-family / 2-control budget and
  the annex rule; no code change.
- **Payoff:** At wave-5/6 filing rates (~60–72 entries/wave), cutting grid-filler by even a
  third saves **~0.5 mill-hour of probes/pass** plus the larger, unpriced saving: merge-review
  and prioritisation time per wave.
- **Risk:** A miner self-censors a genuinely odd idea to fit its family budget. The annex
  preserves it verbatim; the budget governs merge order, never existence.

### K-042 · Retirement by supersession: a closed question retires its re-filings automatically
- **Structural problem:** IDEA-POOL.md states the pool "only gains entries, it never loses
  them", and its header lists questions already CLOSED with numbers (vote-threshold annealing
  8→64; AdamW cooldown on the layered chassis; the JEPA objective; magnitude votes as
  specified). Yet the candidate waves re-file against closed ground with no supersession
  marker: F-040 (descending V 64→8) re-opens the closed anneal with its sign reversed;
  F-031 re-files JEPA as an initializer; MILL-201–203 exist precisely because the closed
  magnitude-vote verdict needed a "calibrated retest" carve-out argued by hand. Each re-filing
  currently costs a full human adjudication of "is this the closed thing or a different arm?"
- **Governance mechanism:** A **supersession registry**: every closed verdict gets a registry
  line naming the mechanism, the closing numbers, and the exact carve-out that would make a
  re-filing a *different* arm (e.g. "anneal: closed for hot starts; cold-first is a different
  arm only if it never goes below V=32" — the MILL-204 distinction, generalised). A candidate
  matching a registry line without satisfying its carve-out is retired at merge, citing the line.
- **Exact change:** New file `mill/CLOSED.md` seeded from IDEA-POOL.md's appendix of
  already-tested arms + PRIORITIES.md's retire table (G-063, G-062, G-053, G-028, I-060,
  I-050, WH-072, F-065); PROMOTE.md's merge checklist gains "check CLOSED.md first".
- **Payoff:** Kills repeat adjudication and repeat probing of settled ground — the 8 entries
  PRIORITIES.md retired by hand would have been retired at merge; **~0.3–0.6 mill-hours/pass**
  plus the verdict-quality gain of never re-litigating a number the lab already owns.
- **Risk:** A registry line drawn too broadly retires a genuinely different arm (the
  MILL-201 failure mode, in reverse). Carve-outs must therefore quote the closing entry's own
  numbers, and retirement is appealable by naming the differing mechanism in one sentence.

### K-043 · Retirement by premise death and age: the two-generation sunset
- **Structural problem:** Beyond supersession, nothing ever expires. An entry whose premise was
  a *champion property* (e.g. entries premised on V=32 at 0.885M weights, on corpus v1's held
  set, or on the layered stack summing its levels — a premise the half-control already killed:
  plain 2.9010 vs layered 2.8990) survives every generation change untouched, because ledger
  keys are (idea, generation) and a new generation simply re-opens everything. PRIORITIES.md's
  deferral table is a manual, one-off version of the policy the pool needs permanently: F-051–054
  deferred behind F-043, I-013–024 deferred behind both parents' probe records, WH-006 deferred
  behind WH-003 — ~27 entries parked by hand, with named triggers stored only in that file.
- **Governance mechanism:** Two automatic sunsets. **(a) Premise-death:** when K-038's graph
  marks a premise killed, dependents older than that verdict retire unless re-filed against
  the new premise. **(b) Age:** an entry that has survived **two champion generations** without
  a probe record moves to `mill/RETIRED.md` (full text preserved) and leaves the active pool;
  re-filing it is free and explicit. Deferral triggers from PRIORITIES.md become ledger fields
  (`deferred_until: <entry-id + verdict>`), checked by screen.py each pass.
- **Exact change:** `mill/RETIRED.md` + a generation-boundary step in screen.py implementing
  (a)/(b); PROMOTE.md's funnel diagram gains the RETIRE exit it currently lacks.
- **Payoff:** Bounds pool growth: without a sunset the pool doubles roughly every two waves
  and pass cost (7.7 h at 368) scales with it — the sunset is worth **~3–4 mill-hours/pass by
  wave 8** against the no-policy baseline, and keeps the active pool's average premise alive.
- **Risk:** Retiring a slow-burn entry whose moment comes at a larger scale (F-051-class).
  Retirement is archival, not deletion, and the scale-ladder rungs are named re-filing triggers
  in RETIRED.md itself.

### K-044 · Combination quarantine: I-013–I-024 may not merge until both parents hold probe records
- **Structural problem:** Wave I's combination lens filed 12 second-order entries (I-013–024)
  over parents that are themselves unprobed — F-001, F-024, F-007, G-030, G-014, F-022, F-003,
  F-006, F-013, G-022, F-002, F-043, WH-025, F-010, WH-014, G-001, G-013, F-018, G-017, F-048,
  WH-027, F-064, WH-033. PRIORITIES.md admitted exactly one (I-015) and deferred the other 11
  for the right reason: "combining two unmeasured parents produces an unattributable number
  whatever it shows" — and I-013 is worse, deleting the very channel F-001 creates. But that
  deferral lives in one prioritisation file; the next merge pass can still ingest all 12.
- **Governance mechanism:** A hard merge rule for combinations: a `×` entry merges only when
  **both parents hold at least a probe verdict** in the ledger, and its own probe is scheduled
  in the same pass as (or after) the later parent's — the I-015 sequencing, as law. Combinations
  whose parents conflict mechanically (I-013, I-017, I-018, I-024 — the four filed *because*
  the parents fight) are exempt from the ban but reclassified as **collision experiments**,
  judged on their filed interaction prediction, not on Δ alone.
- **Exact change:** PROMOTE.md gains the combination rule; IDEA-POOL.md's `mill` block gains
  `parents: [F-001, F-024]` for combination entries; screen.py refuses (ledgers as
  `quarantined`) a combination whose parents lack probe records.
- **Payoff:** Saves up to **11 probes (~0.25 mill-hours) plus any inline trials** on numbers
  that cannot be attributed, and — the larger prize — protects verdict quality pool-wide: one
  unattributable combination "win" adopted as champion would re-denominate every later verdict.
- **Risk:** Slows a genuinely urgent synergy by one pass. Accepted deliberately; I-015's own
  entry already accepts the same sequencing voluntarily.

### K-045 · Mill-change budget: the 24-entry machinery family competes for one slot per pass
- **Structural problem:** Wave G filed **24 mill-change entries** — G-037–048 (futility stop,
  probe ladder, two-stage gate, near-band extension, drift sentinels, re-screen triage,
  surrogate queue, step-count gate, budget partitioning, interaction mining, champion defence,
  deferral ledger) and G-061–072 (calibration funnel, banded second seed, sequential trials,
  held-eval economy, step-10 kill, dose sequencing, fork screening, steps covariate,
  proxy-context, dual-read, proxy judge, caravan) — plus wave J's fidelity family J-025–036
  (12 more) proposing changes to the same funnel. These are not 36 independent ideas; they are
  36 competing amendments to one small codebase (`screen.py`, `sweep_probe.py`, PROMOTE.md),
  several mutually exclusive (G-039 vs G-062: same purchase, PRIORITIES.md picked one; G-037
  vs G-063: same theorem, filed twice) and each carrying regression risk to every verdict the
  mill issues. PRIORITIES.md's top 40 already spends 5 of its 40 slots on this family — the
  correct instinct, with no standing rule behind it.
- **Governance mechanism:** Mill-changes get their own budget line: **at most 2 machinery
  changes land per pass**, ranked by PRIORITIES-style leverage (saving × pool size), and a
  machinery change may not land in the same pass as a champion adoption (verdict machinery and
  judged population never move together — the stale-reference guard's spirit, extended).
- **Exact change:** PROMOTE.md gains a "machinery budget" section; `mill/CENSUS.md` (K-040)
  reports the mill-change family's size and landed count per pass; duplicate-theorem pairs
  (G-037/G-063 class) are merged at filing under K-042's registry.
- **Payoff:** Verdict comparability across a pass is preserved — worth more than hours: a
  mid-pass funnel change silently splits one pass into two incomparable half-passes. Direct
  saving **~0.5 mill-hour/pass** in avoided duplicate machinery probes (G-062/G-063 class).
- **Risk:** A high-leverage fix (G-038's ladder) waits a pass behind a lesser one. Ranking by
  leverage, not filing order, is the stated tiebreak.

### K-046 · Coverage ledger: the wave-I negative-space map becomes a living file, re-issued every wave
- **Structural problem:** The pool's only coverage map is wave 4 lens 1's negative-space file
  (`.idea-engine/wave4-lens1-negative-space.md`), which mapped IDEA-POOL + CANDIDATES-A–H and
  filed its verified gaps as wave I (I-001–012). It has not been updated since: **wave J (48
  entries) opened an entirely new dimension the map does not contain** — headline falsification
  (J-037–048 audit the lab's own claims: "votes reach ≈97% of STE's gain", "the rotary win is
  real", "held windows are clean") — and waves F–J closed some mapped gaps while opening
  others (e.g. the gate-statistic cell, "open" in the map, was hit independently by F-005,
  I-003, I-004, I-005 and I-050 — five entries, no coordination). A stale map actively misleads:
  the next negative-space miner will re-derive filled cells as "gaps" and file duplicates.
- **Governance mechanism:** Coverage becomes a **ledger, not a wave**: a dimension × state
  table (state ∈ covered / probed / closed / open-verified) regenerated from CENSUS.md +
  ledger.jsonl after every wave lands, with each wave's miner required to file against the
  current table and to mark the cells their wave changed.
- **Exact change:** New file `mill/COVERAGE.md` seeded from wave4-lens1's verified/rejected
  gap lists, extended with J's falsification dimension and the governance dimension (this
  file); the wave brief template gains "update COVERAGE.md" as a deliverable line.
- **Payoff:** Prevents the recurring cost of re-deriving coverage by hand (wave 4 spent a
  full miner on it) and of duplicate filings into filled cells — **~1 miner-wave per two
  waves saved**, and every future "gap" claim becomes checkable in one read.
- **Risk:** The table rots if a wave skips its update. Making the update a named deliverable
  of the wave brief (not a favour) is the enforcement; a stale COVERAGE.md must print its
  own last-updated wave at the top.

### K-047 · The counter-forensics session: WH-049–WH-060 run as one dump, one script, twelve reports
- **Structural problem:** Wave H's counter-forensics lens (WH-049 forecast · WH-050 divergence ·
  WH-051 frustration census · WH-052 per-weight validity · WH-053 fingerprint · WH-054 settled
  selection · WH-055 entropy clock · WH-056 field taxonomy · WH-057 dead-counter census ·
  WH-058 oscillation anatomy · WH-059 kurtosis warning · WH-060 c1/c2 disagreement) is 12
  entries that all read **the same counter-field dump** — WH-051's own entry already names the
  shared vehicle: one `mill/counter_anatomy.py` pass "shared by WH-051/004/009/010/012 — one
  pass over a dump emits the full anatomy table". Filed as 12 pool entries, they will be
  merged, queued and reported as 12 ideas; run as filed, the dump is re-produced and re-loaded
  per entry. The same pattern repeats smaller in J-013–024 (12 held-anatomy slicings of the
  same eval outputs) and I-011/I-012.
- **Governance mechanism:** Generalise K-039's cluster rule to analysis families: entries
  sharing one input artefact and one script merge into **one session entry** with per-report
  sections; each report keeps its own falsifiable prediction and its own ledger line, but the
  artefact is produced once. Rule of thumb for merge review: *same dump, same day, one entry*.
- **Exact change:** Merge WH-049–060 into one IDEA-POOL entry (`WH-049-session`,
  variants WH-050–060) whose run string invokes `mill/counter_anatomy.py --full`; likewise
  bundle J-013–024's slicings behind J-013 as variants when wave J merges.
- **Payoff:** 11 queue slots and 11 artefact productions removed; **~0.3–0.5 mill-hour/pass**
  at analysis prices, and the twelve reports become mutually consistent (same dump, same
  champion generation) instead of twelve readings of twelve slightly different states.
- **Risk:** One buggy shared script corrupts twelve reports at once instead of one. Mitigated
  by WH-053's fingerprint report acting as the session's own sanity check, filed first inside
  the session.

### K-048 · Headline-premise insurance: J-037–J-048 audits are premises, and the pool re-prices when one falls
- **Structural problem:** Twelve wave-J entries (J-037–048) audit claims the *entire pool*
  silently treats as premises: that votes earn ≈97% of STE's gain at ~1/10 state (J-037),
  that rotary's win is real (J-038 — every one of the 686 entries runs `--rope`), that held
  windows are clean (J-042 — every Δ in every ledger line is denominated in them), that equal
  minutes is a fair currency (J-043), that the probe funnel can tell signal from noise (J-044),
  that 8-minute verdicts extrapolate (J-045). These are filed as ordinary candidates in a
  48-entry wave, competing for probes with ordinary arms — yet if J-042 finds the leak large,
  or E-018's corpus-v2 re-baseline (PRIORITIES #9) moves the champion number, **every queued
  entry's prediction interval is denominated in a currency that just changed**, and nothing in
  the pool marks which entries were priced in the old one.
- **Governance mechanism:** Promote headline audits to **premise class** in K-038's graph:
  J-037/038/042/043/044/045 become named hub premises of the whole pool (alongside F-043 and
  WH-014). When a hub premise's verdict lands, census.py re-stamps every active entry with
  the premise generation it was priced under; entries priced under a *fallen* hub premise are
  not killed — they are queued for a one-line re-price note before their next probe.
- **Exact change:** `mill/premises.json` gains the six hub entries with `scope: pool`;
  PROMOTE.md's generation-change procedure (currently: re-measure job zero) gains "re-stamp
  premise generations"; J-037–048 merge ahead of wave J's ordinary arms, by protocol.
- **Payoff:** Verdict quality, priced honestly: it converts a future "half the ledger was
  measured against a leak" discovery from a pool-wide write-off (potentially **tens of
  mill-hours** of verdicts) into a bounded re-pricing pass over only the affected entries.
- **Risk:** Over-centralisation — if everything depends on six hubs, one slow audit stalls
  the pool. Hub status therefore flags and re-stamps only; it never blocks a probe the way
  a plumbing premise (K-038) does.

---

*End of wave-6 lens-4 governance. 12 entries (K-037–K-048); ★ = K-037 (family budgets),
K-038 (premise graph + cascade), K-039 (representative clustering of the readout cluster).
Largest duplicate cluster found: the G-025–G-036 readout cluster, 12 members, named in K-039
(16 with its F/I/MILL echoes). Largest premise hubs: F-043 (~9 dependents), WH-014
(4 dependents + its byte claim reused pool-wide), and the six pool-scope headline premises
of K-048. Nothing here edits the pool — adoption of any rule above is the pool owner's call,
executed through PROMOTE.md, screen.py and the merge checklist as each entry specifies.*

## Lens 5 — Deep wild (was DW-###)

### K-049 · Boundary-pressure damping: saturated votes shrink the step, they don't feed it
- **premise inverted (cited):** F-001 — "gradient pressure is a conserved signal…
  whatever the discrete state cannot express must exit through a continuous channel
  or be lost," so outward votes on saturated weights are rerouted INTO `log_scale`
  as signal. **Premise bet: F-001's conservation premise is FALSE.** Outward pressure
  at a boundary is not conserved information; it is the signature of a weight whose
  evidence stream has gone one-sided — runaway, not riches. In that world F-001's
  rerouting amplifies exactly the layers that are already over-committed, and the
  correct exit for boundary pressure is *damping*: this entry is worth −0.02..−0.04
  there, and is predicted to lose by roughly F-001's gain in the world where F-001
  is right — the pair is a signed discriminator, run both.
- **mechanism:** when a strong vote argues for a boundary no-op (component at +1
  pushed +, or −1 pushed −), it does not increment any counter and does not feed
  `log_scale` positively; instead it adds to a per-layer pressure accumulator, and
  at step end that layer's `log_scale` is nudged DOWN by `0.02 × (net outward
  pressure / strong votes that step)` in log space — saturation literally shrinks
  the physical step the saturated weights take, until inward evidence re-earns it.
  Distinct from F-016 (anti-windup: outward votes are *ignored* — no signal used in
  either direction) and from F-001 (same votes, opposite sign of use).
- **exact change:** new flag `--boundary-damp 0.02` on Layered; accumulator is one
  float per BitLinear, no per-weight state; the AdamW update of `log_scale` is
  untouched, the two contributions sum (same wiring point as F-001, opposite sign).
- **mode:** process
- **prediction:** −0.01..−0.04 at probe scale if the damping world is real (boundary
  saturation exists from early steps per WH-051's census prediction of 4–8% frustrated
  weights); ≈ +0.02..+0.05 (a loss mirroring F-001's predicted gain) if it is not.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.02 — damping is then
  strictly worse than doing nothing with the pressure, F-001's direction stands
  unopposed, and this entry closes as its negative control.
- **status:** queued

### K-050 · Boundary eviction: a saturated weight that keeps pushing outward is reset to 0
- **premise inverted (cited):** F-001 again, at the state level rather than the scale
  level — F-001 and F-016 both assume a saturated weight should KEEP its state and
  have its excess pressure rerouted (F-001) or ignored (F-016). **Premise bet: both
  are wrong about what saturation means.** A component pinned at its boundary while
  outward votes keep arriving is a feature claiming more magnitude than the code
  can express — the ternary answer to an over-claimed feature is not a bigger scale,
  it is eviction: free the slot to 0 and let the evidence re-earn a level honestly.
  Worth −0.01..−0.03 in that world; worthless (pure churn) if saturation is stable
  success, which the kill test prices.
- **mechanism:** each component carries a small outward-pressure count (int8): a
  strong outward vote at the boundary increments it, any inward or ordinary vote
  resets it to 0. At 16 consecutive outward votes the component's state is forced
  to 0, both its counters zero, pressure count zero. The weight must then climb
  from 0 on fresh evidence like any zero weight. Distinct from F-064's zero cull
  (uniform-random, population-fraction target, no evidence condition) and from
  thrash freezing (punishes *flipping*; this punishes *refusing to stop pushing*).
- **exact change:** new flag `--boundary-evict 16` on Layered (one int8 per
  component, +2 B/weight charged; eviction applied inside `step()` after the
  normal flip pass, logged as `evictions/step`).
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale, ~0 at probe (16 *consecutive* outward
  votes need a saturated population to exist). Side signature if real: evictions
  concentrate in ≤ 5% of weights, and evicted weights re-flip to a *different* level
  than they held in ≥ 40% of cases — they were mis-seated, not merely loud.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.03, OR if the logged
  eviction count over the probe is 0 (no population — the premise has no object at
  this scale and the entry is void, not wrong).
- **status:** queued

### K-051 ★ · Lottery flips: delete the counters, spend the flip rate by lot
- **premise inverted (cited):** J-002's rival (A) — MEMORY-IS-THE-MECHANISM: "a weight
  improves because ITS OWN counter integrates ITS OWN evidence stream over time."
  **Premise bet: J-002 comes out for rival (B), STATISTICS-ONLY** — its filed
  prediction under (B) is held within ±0.015 of 2.8580 under a full counter shuffle
  every 10 steps. *Assume it failed for (A); this entry is the design that world
  asks for.* If ownership is bookkeeping, keeping 884,736 individual counters is
  ceremony: all the trainer needs is the counter *field's* one honest output — how
  many flips this step should spend — plus the gate's answer to *which weights are
  eligible*. In that world this entry is worth the champion's loss at **0 counter
  bytes** (vs 2,211,840 B of mechanism state), i.e. the vote trainer's state claim
  improves from "~1/10 of STE" to "~0", and every per-weight counter entry in the
  pool (leak, freeze, SPRT, cascade…) is re-read as field-statistics machinery.
- **mechanism:** no per-weight counters exist. Each step: compute the gated strong
  half as champion; the flip budget is `k = round(0.0011 × N)` flips (the champion's
  measured mean flip share, a field statistic); choose k eligible weights uniformly
  at random from the strong half (own RNG stream) and flip each one step in its
  current vote's direction (boundary no-ops skipped, budget not re-spent). V, clamp,
  and reset have no referent and are gone; AdamW parts unchanged. Distinct from
  J-002 (a *diagnostic* that permutes live counters — the counters still exist and
  still integrate between shuffles), from F-019 sortition (eligibility lottery, but
  counters integrate and decide), and from F-061 bandit votes (counters exist and
  are reinforced by a global bit; here there is nothing to reinforce).
- **exact change:** new trainer mode `--arm lottery --flip-share 0.0011` (Direct
  chassis, plain_half shape + `--rope`); trainer state for the ternary side is
  exactly the ternary states themselves.
- **mode:** process
- **prediction:** under premise (B): probe held within +0.05 of job zero — the field
  statistic plus the gate carries the result, ownership contributed nothing. Under
  premise (A): a collapse of +0.15 or worse, toward the F-055 reservoir direction.
  The band between (+0.05..+0.15) is the interesting residue: partial memory value,
  priced for the first time.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.15 — memory was the
  mechanism after all, the no-counter design is dead in one probe, and J-002's (A)
  gains a corroboration stronger than the shuffle itself (deletion ≫ permutation).
  A landing ≤ job-zero + 0.05 does NOT adopt it — it promotes it to a 3-seed trial
  against J-002's own ±0.015 band.
- **status:** queued

### K-052 · Two-step memory: the counter is a 2-vote window, nothing older exists
- **premise inverted (cited):** the same J-002 premise as K-051, attacked at the
  opposite design point. K-051 bets memory is worth *zero*; the pool's whole
  long-horizon lens (I-025/I-026/I-033) bets the opposite failure — that banks go
  *stale*, i.e. old evidence is worse than no evidence. **Premise bet: the truth is
  between J-002's rivals — integration helps, but only over ~2 steps; everything
  older is staleness wearing memory's clothes.** In that world a V=32 bank is mostly
  a liability the lab has been pricing as an asset, and this entry (worth −0.01..−0.03
  there) beats both the champion and K-051's amnesia.
- **mechanism:** each weight keeps only its last two gated votes (2 bits of history,
  packed). It flips one step when both votes agree in a direction that changes its
  state; any disagreement or abstention clears the window. No counter, no clamp, no
  threshold — the flip rule is "two consecutive agreeing strong votes." Effective
  evidence standard is ~2 net votes instead of 32, so flip share will run far hotter
  than the champion's 0.0011 — that heat is the treatment, logged, not tuned away.
  Distinct from the closed anneal family (a *threshold schedule* on a real counter;
  there is no counter here) and from F-022's cascade (two counters in series whose
  whole point is *longer* effective memory — this is its directional opposite).
- **exact change:** new trainer mode `--arm twostep` on the plain_half + rope shape
  (2-bit history per weight ≈ 0.25 B/weight, charged; gate q=0.5 unchanged).
- **mode:** process
- **prediction:** −0.01..−0.03 if short memory is the truth (fresh evidence, no stale
  bank, flips track the current model); +0.05..+0.15 if the 32-vote climb was doing
  real denoising — in which case flip share ≥ 5× job zero's is the expected
  signature and the entry dies by its own log as much as by its loss.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.05, OR if probe flip
  share ≥ 5× job zero's at flat-or-worse loss (thrash, not freshness — the 2-vote
  window was just a hot threshold, and V-schedule entries already own that axis).
- **status:** queued

### K-053 · Max-witness votes: one token position decides, the other 8,191 are ignored
- **premise inverted (cited):** the evidence-aggregation premise shared by BOTH the
  champion (a weight's vote is the sign of the *summed* gradient over 8,192 token
  positions) and its filed inversion I-049 (vote-then-sum: per-token signs summed
  into a majority, τ = 5% net). Champion says magnitude-summed evidence; I-049 says
  democratic evidence. **Premise bet: both aggregation stories are wrong — evidence
  is *extremal*.** The positions that should move a weight are the rare ones where
  the model is decisively wrong about that weight's input; summing (either way)
  lets thousands of near-zero, near-random positions outvote the one witness that
  knows. In that world this entry is worth −0.02..−0.05, and I-049's detectability
  arithmetic (only p ≳ 0.55 majorities vote at all) is re-read as a *defect*: it
  silences exactly the minority-witness weights.
- **mechanism:** per weight per step, find the single token position maximising
  |upstream_t · x_t| (the largest-magnitude per-token gradient contribution);
  the weight's vote is that position's sign alone, admitted only if that maximum
  exceeds the layer's median of maxima (a gate on witnesses, not on sums). Counter,
  V=32, clamp, arbitration unchanged — only the evidence statistic changes, from
  a sum over positions to an argmax over positions. Distinct from A-013 (loss-
  *weighting* a still-summed gradient) and F-020 quadratic voting (a budget over
  weights within a step; positions are still summed inside each weight).
- **exact change:** new flag `--vote-mode maxwitness` on Layered (per-token
  products computed in the vote path as in I-049's sign-GEMM plumbing, reduced by
  argmax instead of sum; FP backward still runs for the AdamW parts, charged as
  in I-049, ≈ +15–20% step time).
- **mode:** process
- **prediction:** −0.02..−0.05 at equal steps if extremal evidence is real, with
  flip share *rising* vs champion (witnesses are less likely to cancel than sums);
  +0.03..+0.08 if aggregation was the denoiser — a single witness per step is the
  noisiest possible statistic and the loss will say so plainly.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.03 at equal steps
  (per-minute reporting alongside, per I-049's honesty rule — a per-minute-only
  loss with an equal-steps win does not kill it, it queues the step-matched read).
- **status:** queued

### K-054 · Error-only counting: agreeing votes are discarded, only dissent integrates
- **premise inverted (cited):** the counting premise underneath the champion and
  I-049 alike — *every* gated vote increments the counter, so most of what a counter
  integrates over a run is confirmation: votes agreeing with the weight's current
  state, pushing it toward a boundary it may already sit at. **Premise bet:
  confirmation is not evidence.** A vote that says "stay" carries no information
  about where the weight should *go*; the counter's climb should be built only from
  votes that argue for change, and the current design dilutes them ~2:1 with
  applause. Worth −0.01..−0.04 in that world, concentrated late in the run (early,
  most weights are wrong, so dissent dominates anyway — the entry's own onset
  prediction). If confirmation turns out to be load-bearing (it is what holds
  correct weights at their levels against noise), the kill test shows it fast.
- **mechanism:** a gated vote increments the counter ONLY if its direction differs
  from the weight's current installed direction for that component (vote pushes
  toward a different level than the one installed); agreeing votes are dropped
  entirely — not rerouted (F-001), not damped (K-049), simply not counted.
  Counters therefore measure *net pressure to change*, and a flip fires at V=32
  of pure dissent. Boundary no-op votes are a special case of agreement and drop
  with the rest. Nothing else changes.
- **exact change:** new flag `--dissent-only` on Layered (one comparison in
  `step()`'s vote loop: `inc *= (vote_dir != installed_dir)` per component).
- **mode:** process
- **prediction:** −0.01..−0.04 at trial scale; probe ~0 to −0.01 (onset is late by
  the premise itself — a flat probe does not kill, a *bad* probe does). Flip share
  falls 30–50% vs champion (half the stream is discarded); the claim is that the
  surviving flips are the informative ones, so loss per flip rises.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.03, OR if end-of-probe
  state histogram shows the zero-fraction moved > 5 points vs job zero (dissent-only
  counting collapsed the histogram toward 0 — confirmation was the scaffolding,
  premise dead on its own diagnostic).
- **status:** queued

### K-055 · Eat the held set: at v3 scale the 128 windows are data, not a shrine
- **premise inverted (cited):** the founding discipline J-042/J-037 defend and price —
  held windows are never trained on, and 2.8580's authority rests on that purity.
  **Premise bet: the purity is a v1 ritual that v3's arrival made free to break.**
  On a ~21.4M-piece corpus, 128 windows are 0.15% of the stream; a *fresh*
  confirmation set (the PROMOTE offset-by-20 windows, never selected on) can take
  over judging duty at zero cost. If the held windows are ordinary data, eating
  them gains ≈ 0 and the lab learns its judge was replaceable all along; if they
  gain measurably on the *confirmation* set, the held windows were never ordinary —
  they were the most central slice of the corpus, and every "held measures language"
  claim (J-013's anatomy included) inherits that specialness. Either reading is
  worth one run; the entry is the only one in six waves that spends the held set
  itself instead of defending it.
- **mechanism:** on the v3 chassis (champion config, `--corpus v3`): the 128 v1-style
  held windows are added to the *training* stream at their natural rate; judging
  moves entirely to the confirmation windows (every-40th offset by 20 on the v3
  stream, excluded from training by the standard predicate). Control in the same
  pass: identical v3 run with held windows excluded as usual, judged on the same
  confirmation windows. The pair isolates "held windows as food" from "new judge."
- **exact change:** runner-level — `--corpus v3 --eat-held --judge confirm` vs
  `--corpus v3 --judge confirm`; no trainer change. Confirmation-set overlap with
  both training streams asserted 0, per the dream protocol's contamination rules.
- **mode:** process
- **prediction:** Δ(confirmation) between the arms within ±0.01 — held windows are
  ordinary, the shrine was empty, and future series may fold any spent judge into
  training once its replacement is seated. A Δ ≤ −0.02 (eating helps on an
  untouched judge) is the sensation outcome and re-opens J-042's leak pricing from
  the other side.
- **one-probe kill test:** retire if the eat-held arm's confirmation loss is ≥
  control + 0.02 (the held windows were actively *bad* food — e.g. the most
  duplicated, most memorised slice — and purity was protecting the trainer, not
  just the judge), or if either arm's confirmation-vs-standard held gap exceeds
  0.10 (the two judges disagree so much that no verdict transfers and the entry
  is void until J-030's bias curve explains it).
- **status:** queued

### K-056 · Junk-only diet: train on nothing the lab calls language
- **premise inverted (cited):** J-013/J-047's shared assumption in mirror image —
  both anatomise held to ask how much of 2.8580 is junk, assuming junk is the
  *dilutant* and prose the substance. F-032 tests junk as a 25% *appetiser* before
  clean data. **Premise bet: nobody has tested junk as the whole meal, and the
  pooled judge may not be able to tell the difference.** If ≥ 35–45% of held
  targets sit in junk-class windows at mean ≤ 1.5 (J-013's own prediction), a model
  trained ONLY on dump/merges/boilerplate windows should score *respectably on the
  pooled judge* while collapsing on the prose slice — and the size of that gap is
  the most direct price ever put on "the held set measures language": it is worth
  exactly the junk-only model's pooled score. In the world where J-013's anatomy
  comes out flat (classes within 0.15), this entry is worth ≈ 0 and dies by its
  own kill test — stated in advance.
- **mechanism:** sampler restricted to windows whose dominant source class (J-013's
  offsets-sidecar classification) is numeric dump, `merges.txt` gibberish, or
  license/package boilerplate — 100% junk, whole run, champion chassis otherwise.
  Judged twice from the same run: pooled v1 held, and J-013's prose+lab+German
  slice (`prose_held`). No mixed phase, no clean steps — that is what separates it
  from F-032 (junk-*first*, then 75% clean, judged on v2 held).
- **exact change:** new sampler flag `--train-class junk-only` on Layered (class
  tags from the J-013 sidecar; step count matched to job zero, tokens-seen logged
  — the junk stream is smaller, repetition is part of the treatment and is counted,
  per the dream protocol's token rules).
- **mode:** process
- **prediction:** pooled held lands 3.05–3.35 (only +0.20..+0.50 worse than the
  champion despite seeing no prose at all) while `prose_held` lands ≥ 4.2 — the
  split, not either number, is the deliverable. If pooled lands ≥ 3.60 instead,
  junk carried less of the judge than J-013 predicts and the anatomy file needs
  re-reading before its licensed interventions are spent.
- **one-probe kill test:** retire if probe pooled held ≥ job-zero + 0.60 (junk-only
  is catastrophically bad even on its home judge — the pooled number was honest
  language measurement after all), OR if `prose_held` − pooled < 0.30 in the same
  probe (no split exists to price; J-013's premise and this entry die together).
- **status:** queued

### K-057 ★ · Tiny-loop scarcity diet: 512 windows, repeated, beat 21M pieces seen once
- **premise inverted (cited):** the v3 premise — corpus-v3 (~21.4M pieces, G-024's
  construction) was built on "more unique data is the fix," the same assumption
  behind A-055 coverage-first sampling, G-021's without-replacement deck, and
  B-009's fresh-data scaling. **Premise bet: for a VOTE trainer the assumption is
  backwards.** A counter needs ~32 *net agreeing* votes to move a weight once; a
  stream of never-repeated windows gives each pattern one testimony, and
  testimonies from unrelated windows cancel inside the counter. Repetition is not
  memorisation risk for this mechanism — it is the only way evidence ever
  *accumulates*. F-048 discounts repetition (1/n per visit) on exactly the
  opposite theory; the pair cannot both be right, and v3 is the first corpus big
  enough to run the scarcity arm without the loop being the whole corpus. Worth
  −0.02..−0.05 at equal steps in the scarcity world.
- **mechanism:** on v3: before step 0, draw 512 legal windows once (seed-disciplined,
  held predicate applied) and train on that fixed loop, cycling in fixed order for
  the whole run — every window is seen ~10× in a 160-step trial. Control in the
  same pass: the standard broad v3 stream at equal steps. Everything else is the
  champion config. Distinct from D-001 mistake replay (a *phase* replaying
  *hard* windows inside a mostly-fresh run — content selected by loss, majority
  fresh) and from A-044 paired repetition (each window twice *in a row*, stream
  still broad): here the diet is total, loss-blind, and looped.
- **exact change:** new sampler flag `--stream-loop 512` (v3 path; loop drawn from
  legal offsets only, `held_overlap = 0` asserted; unique tokens U = 512 × 256
  logged beside tokens-seen T, per the dream protocol's counting rules).
- **mode:** process
- **prediction:** loop beats broad stream by −0.02..−0.05 on v3-native held at
  equal steps, with flip share ≥ 2× the broad arm's (evidence finally repeats
  enough to resolve counters) and train loss on *fresh* (never-looped) windows —
  logged separately, per the noise-chasing rule — falling with held, not against
  it. If fresh-window train loss falls while held rises, that is memorisation,
  the entry's own suspicion rule fires, and the scarcity story is dead even if
  the pooled number looks kind.
- **one-probe kill test:** retire if probe held ≥ broad-stream job-zero + 0.03 at
  equal steps, OR if the probe's flip share is NOT ≥ 1.5× the broad arm's (the
  accumulation mechanism never fired — repetition did not resolve counters, so
  any loss reading is uninterpretable and the premise has no object).
- **status:** queued

### K-058 · Data annealing: the corpus SHRINKS on a schedule (100% → 50% → 25% → 12.5%)
- **premise inverted (cited):** the same v3 premise as K-057, attacked in time
  rather than in diet. Every schedule in the pool anneals a *trainer* quantity
  (V, lr, temperature); the data pool itself only ever grows or stays fixed, and
  the one data schedule family (A-041..A-046 curricula) reorders a fixed pool.
  **Premise bet: K-057's scarcity effect, if real, is a *late-run* effect** —
  early training wants breadth (find the structure), late training wants
  repetition (resolve the counters against a settled model). In that world a
  shrinking pool beats both the broad stream and K-057's all-loop diet, worth
  −0.02..−0.04; if K-057 wins outright instead, scarcity was a whole-run
  property and this entry's phase story dies — the pair is designed to split
  that difference. (This is a *data* schedule; it is not the closed vote-threshold
  anneal 8→64 — V never moves.)
- **mechanism:** v3 stream in four equal step-quarters with nested legal pools:
  quarter 1 draws from all legal windows; quarter 2 from a fixed random 50%
  subset; quarter 3 from a nested 25%; quarter 4 from a nested 12.5% (each pool
  a subset of the previous, drawn once at run start, seed-disciplined). By the
  final quarter each surviving window has been drawable for the entire run and
  is being re-seen at 8× its quarter-1 rate. Sampler-only; trainer untouched.
- **exact change:** new sampler flag `--data-anneal 1,0.5,0.25,0.125` on the v3
  path (nested pool construction at runner start; held predicate applied before
  nesting; per-quarter unique-token counts logged).
- **mode:** process
- **prediction:** −0.02..−0.04 vs the broad-stream v3 control at equal steps, with
  the gain concentrated in the final quarter's held slope (logged per 20 steps)
  and flip share rising quarter-over-quarter as pools shrink. A gain spread
  evenly across quarters would mean nesting did nothing a smaller fixed pool
  wouldn't — re-read as a K-057 result, not this entry's.
- **one-probe kill test:** retire if probe held ≥ broad-stream job-zero + 0.02
  (at probe scale only the first shrink, to 50%, has room to act — if even that
  costs more than the flat band, the late-scarcity story starts from a deficit
  it is unlikely to repay), OR if quarter-2 flip share in the probe window does
  not rise ≥ 1.25× vs the control's same steps.
- **status:** queued

### K-059 ★ · Exit the family: a vote-trained ternary RNN at the exact champion budget
- **premise inverted (cited):** the pool's founding scope choice, stated in
  IDEA-POOL.md's chassis paragraph and inherited by all six waves — the search
  space IS the Tiny transformer family (blocks, heads, RoPE, FFN), and waves F–I's
  architecture lenses (WH-001..WH-012 shapes, MILL-116/117 DeltaNet/RWKV hybrids)
  vary it from inside: even the "recurrent" entries keep attention blocks in a
  3:1 hybrid and keep the transformer as the host. **Premise bet: the vote
  mechanism has never been separated from its host.** If counters earn their keep
  by integrating sign evidence — a claim about *evidence*, not about attention —
  they should work on any ternary substrate; if they only work inside attention's
  gradient geometry, six waves of vote entries are priced facts about one family,
  not about a trainer. Worth, in the transfer world: a within-0.05 landing re-opens
  the entire architecture axis the pool closed by assumption, at every scale rung.
- **mechanism:** a plain Elman RNN: token embedding (tied, FP, as champion) →
  2 recurrent layers whose input and recurrent matrices are BitLinears trained by
  the *unchanged* Layered vote rule (same gate, V=32, counters, arbitration) →
  final norm → tied head. Hidden width set so total ternary = 884,736 exactly
  (width ≈ 300: per layer input 300×300 + recurrent 300×300, ×2 layers, solved at
  wiring and logged). No attention, no RoPE, no position table — position exists
  only as recurrence. BPTT through 256 steps at batch 32 is the honest cost,
  charged per-minute AND per-step; judged primarily per-step.
- **exact change:** new model class + arm `--arm rnn_vote --rope-off` in a companion
  runner importing the Layered trainer unchanged (the trainer already collects
  BitLinears wherever they live — that reusability is part of the test).
- **mode:** process
- **prediction:** per-step held 2.95–3.10 at trial format — worse than the
  champion's 2.8580 (attention is worth something; the entry does not pretend
  otherwise) but far clear of the F-055 reservoir floor direction, with flip share
  in the champion's band (0.0005–0.002). The deliverable is the *gap*: it is the
  first price ever put on the host family itself, and every shape entry in WH's
  lens is a claim that the answer is "small differences inside the family."
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.25 at equal steps
  (the mechanism does not transfer at all — votes were attention's accessory, and
  the architecture axis closes with a number instead of an assumption), OR if
  probe flip share < 0.2× job zero's (the recurrent gradient stream starves the
  counters — vanishing evidence, a mechanism failure, not a family verdict; the
  distinction is logged either way).
- **status:** queued

### K-060 · No attention at all: fixed-shift token mixing + vote FFNs (a mixer, not a transformer)
- **premise inverted (cited):** the milder half of K-059's premise, kept separate
  because the two exits fail differently: WH-012 tapers attention *windows* per
  block and MILL-137/138 ration global blocks 3:1 / 5:1 — every filed entry keeps
  *learned* attention somewhere. **Premise bet: at ctx 256 and 0.885M weights,
  learned content-based routing may be the part attention is worst at** (coarse
  ternary QK logits, exponentiated — the fragility every QK entry in the pool
  works around), while its *mixing* job can be done by a fixed, parameter-free
  shift pattern that no gradient can corrupt. In that world removing attention
  removes the fragile part and keeps the useful part, worth −0.01..−0.04; in
  K-059's world (recurrence is the right mixing) this entry should land between
  the champion and the RNN, and the K-059/K-060/champion triangle prices
  mixing-by-recurrence vs mixing-by-shift vs mixing-by-attention in one pass.
- **mechanism:** each block = pre-norm → fixed mixing: each position's vector is
  replaced by the mean of itself and the vectors at offsets −1, −4, −16, −64
  (causal, zero-padded; no parameters, no logits, nothing to quantize) → residual
  → pre-norm → vote-trained ternary FFN (width solved so total ternary = 884,736
  exactly) → residual. 4 blocks of FFN-only mixing replace the champion's 2 full
  blocks. No Q, no K, no V, no RoPE, no position table. The FFNs and embeddings
  train exactly as the champion's (votes + AdamW parts respectively).
- **exact change:** new block type `--mixer shift` in the model builder (mixing is
  an indexing/gather op in `forward`; BitLinear collection and the Layered trainer
  are untouched).
- **mode:** process
- **prediction:** −0.01..−0.04 vs champion if routing was the tax (side signature:
  the FFNs' flip share rises vs the champion's FFN layers — freed from compensating
  for attention noise, their evidence cleans up); +0.04..+0.10 if content-based
  routing was carrying the model, in which case attention's value is priced
  against its cheapest possible substitute for the first time.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.08 — a fixed shift
  pattern losing by more than twice rotary's entire filed margin (0.0411) means
  learned routing earns far more than its fragility costs, the no-attention exit
  closes, and K-059's recurrent arm becomes the family's only live challenger.
- **status:** queued

---

*End of wave-6 lens 5 (deep wild). 12 entries, K-049..K-060, all status queued.
Premise map: F-001 boundary pressure → K-049 (damp it), K-050 (evict on it);
J-002 counters-as-memory, assumed failed for rival (A) → K-051 (delete them),
K-052 (keep 2 steps of them); summed evidence (champion) and its inversion I-049
→ K-053 (argmax witness), K-054 (dissent only); held-as-language (J-013/J-037/
J-042) → K-055 (eat the judge), K-056 (junk-only diet); more-data (v3) →
K-057 (512-window loop), K-058 (shrinking pool); the transformer family itself
→ K-059 (recurrent exit), K-060 (attention-free mixer). Nothing here edits
IDEA-POOL.md or any CANDIDATES file; merge is the pool owner's call.*

---

## Appendix — working-id mapping (miners -> wave K)

- FD-001 -> K-001
- FD-002 -> K-002
- FD-003 -> K-003
- FD-004 -> K-004
- FD-005 -> K-005
- FD-006 -> K-006
- FD-007 -> K-007
- FD-008 -> K-008
- FD-009 -> K-009
- FD-010 -> K-010
- FD-011 -> K-011
- FD-012 -> K-012
- MT-001 -> K-013
- MT-002 -> K-014
- MT-003 -> K-015
- MT-004 -> K-016
- MT-005 -> K-017
- MT-006 -> K-018
- MT-007 -> K-019
- MT-008 -> K-020
- MT-009 -> K-021
- MT-010 -> K-022
- MT-011 -> K-023
- MT-012 -> K-024
- SC-001 -> K-025
- SC-002 -> K-026
- SC-003 -> K-027
- SC-004 -> K-028
- SC-005 -> K-029
- SC-006 -> K-030
- SC-007 -> K-031
- SC-008 -> K-032
- SC-009 -> K-033
- SC-010 -> K-034
- SC-011 -> K-035
- SC-012 -> K-036
- GV-001 -> K-037
- GV-002 -> K-038
- GV-003 -> K-039
- GV-004 -> K-040
- GV-005 -> K-041
- GV-006 -> K-042
- GV-007 -> K-043
- GV-008 -> K-044
- GV-009 -> K-045
- GV-010 -> K-046
- GV-011 -> K-047
- GV-012 -> K-048
- DW-001 -> K-049
- DW-002 -> K-050
- DW-003 -> K-051
- DW-004 -> K-052
- DW-005 -> K-053
- DW-006 -> K-054
- DW-007 -> K-055
- DW-008 -> K-056
- DW-009 -> K-057
- DW-010 -> K-058
- DW-011 -> K-059
- DW-012 -> K-060
