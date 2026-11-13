# Muse's work — Muse's side

# Wave 5 · Lens 3 — ERROR ANATOMY (ER-001 … ER-012)

<!-- Muse's work — Muse's side of the BitNet lab. Idea Engine rotation 5, miner 3:
the champion's ERROR STRUCTURE as the idea source. Measurement-first: every entry is an
anatomy cut × the intervention that cut licenses IF the predicted pattern is found. The
intervention is conditional — it is not filed as a standalone bet. Nothing here is in the
pool until the pool's owner merges it. IDEA-POOL.md was read and NOT edited. -->

## Subject, bars, and the one runner change every entry shares

- **Subject:** the champion — `layered_half --rope`, plain votes, held **2.8580 ± 0.0161**
  on v1 (5,917,236 pieces). Adoption bar as in waves F–I: beat champion by >2 sd
  (>0.0322) AND >0.01, judged at the mill's standard formats. Controls where a Δ is
  needed: `plain_half` (2.9010 no-rope control family) and the no-rope layered_half
  (2.8990), plus STE-half (2.8205) in ER-012.
- **The held set as it exists:** `train.py held_loss()` reduces cross-entropy with
  `reduction="sum"` over 128 windows × 256 targets = **32,768 target tokens** and returns
  one scalar. No per-token loss, position, token id, or provenance survives the call.
  **Every entry below needs the same runner change, stated once here:** a new eval mode
  `held_loss_anatomy()` (flag `--held-anatomy <cut>` on the eval/readout path) that keeps
  `reduction="none"`, and emits one row per target: `(window_id, position, target_id,
  loss)`. No trainer, sampler, or model change for any cut itself.
- **Provenance sidecar (needed by ER-001/004/005/007/010/011):** neither corpus stream
  carries an offset→source map. Build `mill/anatomy_offsets.py`: re-tokenize the sources
  in `make_corpus.py` / `make_corpus_v2.py` build order, assert the rebuilt stream equals
  `corpus.u16` / `corpus-v2.u16` byte-for-byte, and emit per-piece tags `(source_file,
  source_class, line_id, offset_in_line, line_length)`. If the assert fails, the
  provenance entries void themselves — a stream that cannot be re-derived cannot be
  anatomised by source, and that failure is itself reported.
- **Corpus facts the predictions are priced from (DATA-AUDIT.md):** v1 is 73.9% venv /
  HF-cache junk by source bytes; ~23.0% of pieces sit in lines >1,000 pieces (scipy
  numeric dumps, nine lines of 120k–154k pieces); Qwen `merges.txt` tables are 42% of
  source bytes; 30.8% of all pieces are exact-duplicate copies; median v1 line is 9
  pieces; bare space is 10.2% of all pieces; UTF-8 fragment tokens (`Ä Ã Â ł`) sit at
  frequency ranks 4–8; 1,984 of 3,548 used tokens occur <100×. v2 (907,409 pieces, all
  lines unique): **German 45.7% / HiveMIND docs 41.9% (Muse side 28.8% + Fable side
  13.1%) / lab notes 12.4%**; median line 36 pieces.
- **Boundary with wave I (NG lens):** I-011 filed frequency-binned held and I-012 filed
  position-binned held as **standalone diagnostics**, and I-002 filed the German
  dose–response with per-language held slices. Those three are not re-filed here. Every
  ER entry either cuts on an axis I-011/I-012 do not touch (provenance, line-offset,
  seams, entropy, duplication, purity, token class), cuts two axes jointly, or — where
  an axis overlaps — attaches the conditional intervention that turns the diagnostic
  into a decision. Also not re-filed: E-019/E-020/E-021 (excision repricings), G-013
  (boundary-masked packing), G-015 (held moat), G-019 (German placement), A-048
  (per-file balance), A-049 (frequent-token window downweighting), B-012 (DoReMi),
  WH-019 (tail-row V), WH-048 (duplication dose), F-013/I-007/I-008 (position-weighted
  or position-dropped training loss on *window* position). Each entry names its nearest
  neighbour and the exact difference.

---

### ER-001 ★ · Held-window provenance census: what fraction of 2.8580 is junk windows? (v1, by source file class)
- **the cut:** Classify each of the 128 v1 held windows by its dominant source class via
  the offsets sidecar — numeric dump / `merges.txt` gibberish / license+package
  boilerplate / German Tatoeba / English project prose / lab notes — and report, per
  class: target share, mean loss, and share of total held loss mass. One eval pass on
  the existing champion checkpoints (seeds 0–2), no retraining. This is the cut G-019 /
  I-002 cannot make: they slice *v2* held by language; nobody has ever asked what the
  *v1 held set itself* is made of.
- **predicted pattern:** ≥35–45% of held targets sit in junk-class windows (dumps +
  merges + boilerplate) with mean loss ≤1.5; German windows ≈2.2–2.5; real English prose
  + lab-notes windows ≈3.4–3.7 and carry ≥55% of the loss mass on ≤40% of targets.
  I.e. the pooled 2.8580 is a junk-diluted average, and the prose-only held number —
  the number that describes the modelling the lab actually cares about — is ≈3.3–3.6,
  roughly 0.5 worse than the headline.
- **licensed intervention (exact change, conditional):** If the split lands as predicted,
  two changes, in order: (1) the mill's adoption gate gains a second, binding number —
  `prose_held` (mean loss over prose+lab+German held targets only) reported beside every
  verdict, with adoption requiring the >2 sd margin on prose_held, not on the pooled
  scalar; (2) one training arm, `--train-class-mask junk`: windows whose dominant class
  is dump/merges/boilerplate are excluded from the *training* loss entirely (both vote
  and AdamW paths). Distinct from E-020, which ablates numeric dumps only (~23%) and
  reports a pooled number; this masks all three junk classes (~40%+ of windows) and is
  judged on the prose slice.
- **pointless if:** Class means land within 0.15 of each other, or junk-class targets are
  <10% of the held set — then 2.8580 was an honest average all along, the gate change is
  ceremony, and the mask arm would only shrink the training stream.
- **status:** queued

### ER-002 ★ · Local context entropy: loss by the entropy of the 32 pieces before the target
- **the cut:** For every held target, compute the empirical entropy of its preceding
  32-piece context from corpus statistics (bigram conditional entropy of the context's
  pieces, computed offline once, no model involved), bin targets into entropy quintiles,
  and report mean loss + loss-mass share per quintile, for champion and plain_half.
  Context entropy is the one mandated axis no filed entry measures at all — WH-055's
  entropy is the *counter field's*, B-004's is a patcher's; neither touches the loss.
- **predicted pattern:** Strongly convex: bottom quintile mean ≤1.2 (formulaic German,
  boilerplate, float streams), top quintile mean ≥4.5, and the top quintile carries
  ≥35% of total loss mass on its 20% of targets. The champion−plain Δ concentrates in
  quintiles 2–3 (Δ −0.04..−0.08) and is ≈0 (±0.01) in the top quintile — votes earn
  where context is *moderately* informative and earn nothing where it is chaotic.
- **licensed intervention (exact change, conditional):** Entropy-band evidence weighting
  in the shared training loss: targets in the top context-entropy quintile get loss
  weight 0.5, quintile 4 gets 0.75, quintiles 1–3 stay 1.0 (`--entropy-weight
  1,1,1,0.75,0.5`, quintile boundaries frozen from the corpus pass, applied to both
  vote and AdamW paths). Rationale the anatomy would license: the top quintile's
  gradient is mostly irreducible surprise; at full weight it casts full-strength votes
  for noise. Distinct from A-013 (loss-weighted votes — weights by the *loss value*)
  and failweight (weights by *window* loss): this weights by a property of the context
  known before the forward pass.
- **pointless if:** Loss-mass share per quintile tracks token share within ±3 points
  (entropy explains nothing beyond base rates), or the top quintile's excess is ≥80%
  mojibake/dump artefacts — then the problem is ER-005/ER-001's, and downweighting by
  entropy is a blunt proxy for a class mask.
- **status:** queued

### ER-003 · Distance since BOS: loss by offset-in-line, not position-in-window
- **the cut:** Using the sidecar's `offset_in_line`, bin every v2-held target (E-018
  re-baseline checkpoint) by offset 0 / 1 / 2–4 / 5–9 / 10–19 / 20–39 / 40+, and report
  mean loss and target share per bin. I-012 bins by *window* position; but v2's median
  line is 36 pieces and v1's is 9, so most targets' true context boundary is a line
  start inside the window, invisible to window-position binning. G-018 (BOS-anchored
  starts) bets on this axis without ever measuring it.
- **predicted pattern:** Offset 0 mean ≥4.2 and offset 1 ≥3.6, falling to ≈2.4 by
  offsets 10–19 and flat after; because lines are short, ≥22% of all targets sit at
  offsets 0–4 and carry ≥32% of loss mass. The curve's *shape* is the deliverable: a
  cliff at 0–1 (a line's first pieces are near-irreducible) over a long shallow slope.
- **licensed intervention (exact change, conditional):** Line-relative early-target
  discount in training: targets at line-offset 0 get loss weight 0.25, offset 1 gets
  0.5, all others 1.0 (`--bos-weight 0.25,0.5`, line offsets from a build-time sidecar
  the sampler already needs for G-013-class flags). Distinct from I-008, which hard-
  drops *window* positions 0–15 for both paths, and F-013, which soft-weights *window*
  position in the vote path only: this is keyed to where a *line* starts, which occurs
  ~28 times per v1 window, not once.
- **pointless if:** The offset curve is flat within ±0.1 beyond offset 1, or offsets 0–4
  hold <10% of targets — then line starts are a negligible slice and G-018's premise
  should be re-read as a window-start claim only.
- **status:** queued

### ER-004 · Language seams: targets within ±8 pieces of a German↔English switch
- **the cut:** On v2 held, flag every target whose 17-piece neighbourhood straddles a
  language switch (a BOS seam where the sidecar's line language changes German↔English),
  and compare its mean loss against non-seam targets matched on offset-in-line and
  frequency band. Report seam share, seam premium, and the premium separately for
  DE→EN and EN→DE directions. No filed entry isolates the seam: G-019 varies placement
  of whole blocks, G-016 the alternation period; both read pooled/slice numbers, never
  the boundary targets themselves.
- **predicted pattern:** Seams are dense (v2 mean line 43.5 pieces ⇒ a 256-window holds
  ~6 lines, so ~10–14% of targets fall in a ±8 seam band), and the seam premium is
  +0.6..+1.0 over matched controls, asymmetric: EN→DE costs more (+0.8..+1.1) than
  DE→EN (+0.4..+0.7), because the model's English-shaped expectations are the stronger
  prior at 54.3% English share.
- **licensed intervention (exact change, conditional):** Language-homogeneous packing:
  the sampler builds each training window from consecutive lines of one language only
  (`--pack-lang`), so seam targets vanish from training evidence instead of teaching
  the counters that language switches are unpredictable noise; held eval unchanged
  (mixed windows still judged). Distinct from G-013 (masks loss *at* boundaries inside
  mixed windows — the seam context is still in the forward pass) and from I-002 (changes
  the *amount* of German; this changes only its *arrangement*, share fixed at 45.7%).
- **pointless if:** The matched seam premium is <0.15 in both directions — then switches
  cost no more than any line start (ER-003's cliff explains the whole effect) and
  packing by language buys nothing a BOS discount doesn't.
- **status:** queued

### ER-005 · Mojibake anatomy: UTF-8 fragment targets, and the targets that follow them
- **the cut:** On v1 held, split targets into three groups: (a) the target IS a UTF-8
  byte-fragment token (the `Ä Ã Â ł` family at frequency ranks 4–8, exact id list from
  the tokenizer), (b) the target immediately FOLLOWS a fragment in the context, (c) all
  others. Report share, mean loss, loss-mass share per group. DATA-AUDIT §5 names
  encoding damage as a first-class citizen; no entry has ever priced it in the loss.
- **predicted pattern:** Group (a) is 3–5% of targets with mean ≤1.0 — multi-byte
  continuations are near-deterministic, so fragments are *easy* targets silently
  diluting 2.8580 by ≈0.05–0.08 — while group (b) runs +0.25..+0.40 above group (c):
  the model pays for the corruption one token later, where nobody has looked.
- **licensed intervention (exact change, conditional):** Two-step, anatomy-gated:
  (1) training-loss mask on group-(a) targets only (`--target-mask-frag`, id list
  frozen from this cut) — the model stops spending votes learning byte plumbing;
  (2) IF group (b)'s premium is ≥0.25, a corpus-v3 build fix is licensed: decode
  sources as UTF-8 with error *detection* and drop/repair mojibake lines at build
  time (builder change in `make_corpus_v3.py`, not a trainer flag). Step (2) is the
  only ER intervention that touches corpus construction, and only on this evidence.
- **pointless if:** Group (a) is <1% of targets or its mean is within 0.1 of the pooled
  mean, AND group (b)'s premium is <0.1 — then the encoding damage is cosmetic, the
  audit's ranks 4–8 are a frequency curiosity, and both steps are waste.
- **status:** queued

### ER-006 · Frequency band × position: the tail, split by where in the window it sits
- **the cut:** Cross I-011's axis with I-012's — deliberately joint, which is what makes
  it not either entry: target-frequency bands by raw corpus count (≥10,000 / 1,000–9,999
  / 100–999 / 10–99 / <10; recall 1,984 tokens occur <100×) × window half (positions
  0–127 / 128–255), reporting mean loss, loss-mass share, and champion−plain Δ per cell,
  on v1 held.
- **predicted pattern:** The <10 band means ≥6.0 (barely below the ln(4096)≈8.32 of an
  untrained head — the tail is essentially unlearned) and the two sub-100 bands together
  carry ≥45% of loss mass on ~15–18% of targets; critically, the champion's Δ vs plain
  in the <100 bands is ≈0 in the early half but −0.03..−0.06 in the late half — tail
  tokens are learnable by votes *only* with long context, so the tail problem is a
  context problem, not a capacity problem.
- **licensed intervention (exact change, conditional):** Band-and-half-specific loss
  weight: training targets with corpus count 10–999 (the *learnable* tail — hapax <10
  explicitly excluded as unlearnable at this budget) get weight 2.0 when they occur at
  window positions ≥128, weight 1.0 elsewhere (`--band-weight 10-999:2.0@pos>=128`).
  Distinct from A-049 (downweights whole *windows* rich in frequent tokens), WH-019
  (lowers tail *embedding rows'* V — a trainer-state change), and G-034 (readout-side
  unigram correction): this is a training-loss weight keyed jointly on band × position,
  exactly the two axes of the cut.
- **pointless if:** The sub-100 bands carry <25% of loss mass, or the champion's tail Δ
  is uniform across halves (within ±0.01) — in the first case the tail is a rounding
  error in the pooled number; in the second, position is not the tail's binding
  constraint and a plain band weight (a different, simpler entry) is the right tool.
- **status:** queued

### ER-007 · Four-class held on v2: German vs HiveMIND-Muse vs HiveMIND-Fable vs lab notes
- **the cut:** Per-class held means on the v2 re-baseline checkpoint (E-018), classes
  from the sidecar at *line* granularity (not G-019/I-002's window-majority slicing):
  German 45.7% / HiveMIND Muse side 28.8% / HiveMIND Fable side 13.1% / lab notes
  12.4% of v2 pieces. Plus one derived number nobody has: the Muse side vs Fable side
  gap — same project, same dialect, different authors' scaffolding.
- **predicted pattern:** German ≈2.3–2.5 (short, formulaic Tatoeba); HiveMIND docs
  ≈3.0–3.2; lab notes worst at ≈3.4–3.6 (dense numbers, hashes, result tables — the
  closest thing to prose-formatted dumps); and a Muse side−Fable side gap of
  ≥0.20 despite the shared dialect, driven by differing boilerplate/scaffolding shares.
  Pooled v2 held lands in E-018's predicted +0.15..+0.45 worse band, but the *spread*
  across classes (≥1.0) is 3× the pooled shift — the average hides the anatomy.
- **licensed intervention (exact change, conditional):** Anatomy-set class weights in
  the v2 sampler, set from this cut's table to equalise per-class held, first dose:
  `--src-weight de:0.7,hive-c:1.0,hive-f:1.0,lab:1.5` (German down-weighted because it
  is already the best-learned class at the largest share; lab notes up-weighted as the
  worst class), total tokens fixed. Distinct from I-002 (sweeps the German *dose* on a
  German-vs-rest binary), A-048 (equal weight per *file* — 186 files, class-blind),
  and B-012 (DoReMi's *automatic* proxy-learned weights): these are four hand-set,
  anatomy-derived class weights with the derivation printed in the entry.
- **pointless if:** The four class means span <0.20 total — then v2's mixture is
  homogeneous in difficulty, class weighting can only shuffle noise, and I-002's dose
  question is the only mixture question worth the mill's time.
- **status:** queued

### ER-008 · Fine position curve × RoPE: 16 buckets of 16, and the first-token anomaly
- **the cut:** I-012's four buckets, refined to sixteen 16-position buckets plus a
  separate read on position 0 alone, champion (rope) vs no-rope control, v1 held —
  reporting per-bucket Δ (rope−no-rope), not just per-bucket means. The refinement is
  the entry: a 64-wide bucket can hide a win that lives in 32 positions and a loss
  that lives in 8.
- **predicted pattern:** Bucket means fall from ≈3.5 (0–15) to ≈2.45 (240–255), but
  RoPE's −0.0411 pooled win is *not* spread smoothly: ≥50% of it sits in buckets
  128–191 alone, buckets 192–255 contribute <20%, and at positions 0–7 RoPE is
  actively *worse* by +0.03..+0.06 (rotary phases at near-zero angles give the first
  targets a worse geometry than the learned table they replaced).
- **licensed intervention (exact change, conditional):** Hybrid position scheme:
  learned position table for positions 0–31, RoPE from position 32 on (`--rope-from
  32`), everything else champion. Distinct from the pooled partial-RoPE entries
  (MILL-133..135), which rotate a *fraction of head dimensions* at all positions; this
  splits by *position range*, which is the axis the anatomy indicted. If instead the
  win concentrates in 192–255, the licensed variant flips: full RoPE kept, and the
  entry licenses *extending* judged context rather than hybridising — stated here so
  the intervention follows the cut either way.
- **pointless if:** Per-bucket Δ is uniform within ±0.02 across all sixteen buckets —
  then RoPE's win is position-blind, I-012's coarse read was sufficient, and no
  position-keyed scheme can beat plain RoPE.
- **status:** queued

### ER-009 · Trivial-target anatomy: space, newline, and digit targets by source class
- **the cut:** Split v1 held targets by token class — bare space (10.2% of all corpus
  pieces), newline/BOS-adjacent structural tokens, digit/float-fragment tokens, and
  everything else — and cross the digit class by source class (digits inside dump
  windows vs digits inside prose windows). Report share, mean, and mass share per cell.
- **predicted pattern:** Space+structural targets are 14–17% of all held targets with
  mean ≤0.7 and <4% of loss mass — a seventh of the judging set is nearly free. Digits
  split violently by source: ≈1.6–1.9 inside dump windows (predictable float streams)
  vs ≥4.5 inside prose (dates, measurements, results — the least predictable tokens in
  the project's own writing). Same token class, a ≥2.6 gap: token identity explains
  almost nothing here; provenance explains almost everything.
- **licensed intervention (exact change, conditional):** Trivial-target discount in the
  training loss: targets in the frozen {space, newline} id set get weight 0.25
  (`--trivial-weight 0.25`), returning ~10% of every batch's vote evidence to tokens
  that carry information. Explicitly NOT licensed by this cut: touching digit targets
  — their prose/dump split says the fix for digits is ER-001's class mask, and this
  entry says so rather than double-filing it. Distinct from A-049 (window-level
  frequency downweighting) and ER-005 (fragment targets): this set is defined by
  *structural role*, and its predicted loss (≤0.7) is far below the fragments'.
- **pointless if:** Space+structural targets are <8% of held targets or their mean is
  ≥1.5 — then there is no free slice to reclaim, and discounting them would only
  distort the loss the AdamW parts calibrate against.
- **status:** queued

### ER-010 ★ · Duplication anatomy: per-target loss, leaked vs unique lines (v1)
- **the cut:** Tag every v1 held target by whether its *line* (sidecar `line_id`)
  appears verbatim anywhere in the training stream — DATA-AUDIT §4 says 30.8% of all
  pieces are exact-duplicate copies and 93.2% of lines belong to a duplicated group, so
  held content routinely also appears in training. Report leaked share of held targets,
  mean loss leaked vs unique, and the implied honest pooled number (unique-only mean).
  E-019 prices the flattery by *rebuilding the corpus without the leak*; this prices
  it per-target on the existing champion, with no rebuild — the two numbers must agree,
  and if they don't, one of them is wrong, which is also a finding.
- **predicted pattern:** Leaked targets are 28–34% of the held set, mean ≈1.9–2.1 vs
  unique ≈3.3–3.5 — a gap ≥1.2 — putting the unique-only held at ≈3.35, i.e. roughly
  0.5 of the champion's headline is memorised boilerplate being re-read, not language
  being modelled. The gap is largest for license/boilerplate lines (≥1.8) and smallest
  for German (≤0.6, formulaic enough to earn its loss honestly).
- **licensed intervention (exact change, conditional):** Duplicate-capped sampling:
  the sampler tracks per-line occurrence counts and caps any exact line at 2 training
  presentations per run (`--dup-cap 2`, line ids from the sidecar; windows drawn from
  capped-out lines are resampled). Distinct from A-047 (near-duplicate *removal* —
  binary, and near- not exact-), G-020 (duplicate *spacing* — keeps all copies, fixes
  timing), F-048 (repetition-discounted *votes* — trainer-side), and WH-048 (bulk
  duplication *dose* on v2, where duplication is zero by construction): this caps
  exact-line repetition on v1, the corpus the champion actually trains on.
- **pointless if:** The leaked−unique gap is <0.3, or leaked targets are <10% of held —
  then duplication flatters the *training* stream but not the *judge*, E-019's rebuild
  is the only repricing needed, and capping duplicates would just shrink an already
  starved corpus (0.91M unique pieces) for nothing.
- **status:** queued

### ER-011 · Window purity: loss by how many distinct lines/sources a held window mixes
- **the cut:** For each v1 and v2 held window, compute purity = the largest single
  line's share of the window, and the distinct-line count; bin windows by purity
  (≥90% single-line / 50–90% / <50% collage) and report mean loss per bin, with context
  entropy (ER-002's statistic) as a control variable so purity is not re-measuring
  entropy under another name. Training windows are random-offset collages of unrelated
  fragments (DATA-AUDIT §2) — the collage structure itself has never been priced.
- **predicted pattern:** Pure windows mean ≈2.3–2.5, collage windows ≈3.0–3.2 — a
  ≥0.6 purity gap that survives the entropy control with ≥0.35 intact. On v1 the
  pure bin is dominated by the mega-lines (dumps), so the v1 read is confounded by
  class; the v2 read (longest line 596 pieces, no dumps) is the clean one and is
  predicted to keep a ≥0.4 gap.
- **licensed intervention (exact change, conditional):** Line-coherent window packing
  on v2: training windows are built from consecutive lines of a single source file,
  filled to 256 pieces before moving on (`--pack-lines`), replacing random-offset
  collage sampling; held eval unchanged. Distinct from G-014 (stream walk — preserves
  corpus *order* globally), G-024 (whole-book order on v3), and ER-004's `--pack-lang`
  (groups by language across files): this groups by *document*, the unit the purity
  cut measures. Licensed only on the v2 read, per the prediction's own confound note.
- **pointless if:** The purity gap collapses below 0.15 once entropy is controlled, on
  v2 — then collage windows are hard only because their content is high-entropy, ER-002
  already owns the effect, and packing is an expensive sampler rewrite for a proxy.
- **status:** queued

### ER-012 · The Δ anatomy: where the champion's edge over plain and STE actually lives
- **the cut:** The meta-cut: one anatomy pass, three checkpoints (champion, plain_half,
  STE-half), every axis above applied to the *differences* — Δ(champion−plain) and
  Δ(champion−STE) per cell of {language class × frequency band × position half ×
  entropy tercile} on v1 held, reporting the five cells with the largest |Δ| in each
  direction. Every other ER entry anatomises the champion's loss; this one anatomises
  its *advantage*, which is the quantity adoption decisions actually spend.
- **predicted pattern:** The champion's edge over plain (−0.043 pooled) is not spread:
  ≥70% of it sits in German + mid-frequency (100–9,999) + late-position cells, and the
  champion is *worse* than STE-half by +0.05..+0.15 in the lab-notes / English-tail
  cells — i.e. votes win the formulaic centre and lose the project's own hard tail to
  gradients, and the pooled 2.8580 vs 2.8205 ordering reverses inside identifiable
  cells. (STE-half's pooled win is already known; *where* it wins is not.)
- **licensed intervention (exact change, conditional):** Anatomy-guided continuation:
  take the champion checkpoint and run a final 25%-of-budget continuation phase on
  English lab-notes + HiveMIND windows only, with the trainer swapped to STE for that
  phase (`--continue-class lab,hive-en --continue-trainer ste --continue-frac 0.25`) —
  spend gradient training exactly on the cells where the Δ anatomy says votes lose,
  and nowhere else. Distinct from every hybrid-by-*layer* entry (A-028/A-032 split
  trainers by module): this splits by *data cell and phase*, a partition only an
  error anatomy can draw. If the losing cells are instead German, the class argument
  flips to `de` — the flag is the intervention, the anatomy chooses its value.
- **pointless if:** Both Δ tables are uniform within ±0.02 across cells — then the
  champion is uniformly a bit better than plain and uniformly a bit worse than STE,
  no cell-targeted phase can beat simply scaling the better trainer, and this lens's
  whole premise (that pooled numbers hide exploitable structure) takes its hardest
  available hit.
- **status:** queued

---

## Miner's ranking note

★★★ are ER-001, ER-002, ER-010. ER-001 first: it is the cheapest cut in the file (one
eval pass, no retraining) and the one most likely to embarrass the champion — if a
third or more of the judging set is dump/merges/boilerplate windows scoring ≤1.5, then
"2.8580" has never been a language-modelling number, it is a weighted average of
language modelling and float-stream re-reading, and every verdict the mill has issued
in that currency inherits the dilution. ER-010 is its twin from the training side
(leaked lines re-read at ≈2.0 vs unique text at ≈3.4), and the pair put a hard number
— predicted ≈0.5 — on how much of the headline is real. ER-002 second because context
entropy is the only mandated axis with *no* filed measurement of any kind, and its
predicted shape (top quintile: ≥35% of the loss, ≈0 of the champion's edge) is the
single most actionable pattern in the file if it lands.
