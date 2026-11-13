# Muse's work — Muse's side

# Wave-3 Lens 2 — VOCABULARY / TOKENIZATION as a vote-trainer variable (Muse's work, Muse's side)

> Territory: vocabulary and tokenization treated as dials on the **vote trainer** — how
> vocab size trades against vote evidence, whether embedding rows should vote, how the
> frequency tail starves, and what can be pruned after training. This is NOT the data-side
> tokenizer territory: B-002 (refit at the same size) and B-003 (SuperBPE superwords) are
> taken and are not re-proposed; every entry below varies something they hold fixed.
>
> **Champion:** layered_half + rotary + plain votes — held **2.8580 ± 0.0161**, vocab 4096,
> ctx 256, dim 192, 2 blocks, 884,736 ternary weights, V=32. Any entry that changes
> tokenization is judged in **nats/byte**, never nats/token.
>
> **Code grounding (train.py, read before drafting).** `VOCAB, DIM, HEADS, CTX = 4096, 192, 4, 256`
> are module constants — there is no `--vocab` flag today. `Tiny.tok` is ONE
> `nn.Embedding(4096, 192)` used twice: as the input embedding and, transposed, as the LM
> head (`next_piece = body(ids) @ tok.weight.T`) — the table is tied by construction.
> In the vote trainers, votes exist ONLY on `BitLinear` weights; the embedding sits in the
> AdamW group (lr 1e-3, betas (0.9, 0.95)) with the norms and `log_scale`s. **No embedding
> row has ever cast or received a vote in this lab.** Two gradient streams hit each tied
> row asymmetrically: the head role gives every row a dense gradient at every position
> (mostly the negative push `p_v · h`), while the input role touches a row only when its
> token actually occurs.
>
> **Corpus grounding (DATA-AUDIT.md, measured on `corpus.u16`).** 5,917,236 pieces over
> 11,834,472 source bytes = **2.00 bytes/piece**, so the champion's 2.8580 nats/token is
> **1.429 nats/byte**. Only **3,548 of 4,096 ids ever occur** — 548 rows are dead by
> construction. **1,984 of the 3,548 used ids occur <100 times** in the whole corpus; in a
> single 458,752-piece ladder-format run most of those rows expect <8 input-side updates.
> The single most common piece is a bare space (id 222, 604,047×, 10.2% of all pieces).
>
> **Byte grounding.** The tied FP table is 4096 × 192 × 4 B = **3,145,728 B ≈ 83% of the
> champion's 3,806,208 B served total** (G-049's figure). At the 2M rung (dim 288) it is
> 4,718,592 B. At lab scale the vocabulary IS the model, byte-wise; the ternary body is
> the minority tenant. That inversion is what this lens exploits.
>
> **Deduped against** `mill/IDEA-POOL.md`, CANDIDATES-A/B/C/D/E/F/G, FABLE-CANDIDATES.md,
> DATA-AUDIT.md. Taken, with the exact difference stated again at each adjacent entry:
> MILL-118 (tied table quantized to INT8, per-row scales — a precision price, table stays
> FP-trained by AdamW, no votes, no size change), MILL-119 (untied FP head, champion shape
> only), A-081 (ternary head as a BitLinear, input embedding stays FP and untied), A-083
> (bigram hash side-table), A-091 (norm on embedding output), G-001/G-005/G-007 (per-part
> lr/decay/betas for the AdamW embedding), G-012 (row max-norm cap), G-034 (unigram
> prior-correction bias at readout), E-016 (embedding-exempt cooldown), B-002 (tokenizer
> refit at the SAME 4096 size on the exact mixture), B-003 (SuperBPE cross-word superwords),
> B-004 (BLT — deletes the vocab entirely; a build, not a dial), F-051 (vocab 4096→16384
> at the 50M rung ONLY, ternary count held, predicted negative at 10M), A-049 (frequent-token
> window downweighting — sampling, not tokenization), A-013/A-106/A-107 (per-token loss/vote
> weighting at fixed tokenization), F-013 (position-weighted votes).

---

### TK-001 ★ · Vocab 2048 at the champion — the down-dial nobody has run
- **source:** byte grounding above + DATA-AUDIT §2 — at 0.885M ternary weights the FP tied table is ~83% of served bytes and 548 of its rows are dead; F-051 varies vocab only upward and only at 50M. The small end of the dial, where the embedding dominates, has never been touched.
- **mechanism:** Refit the BPE tokenizer at vocab 2048 on the same corpus sources (B-002's refit procedure, different size), rebuild the corpus, run the unchanged champion chassis. Three effects compound: (a) the table halves to 1,572,864 B; (b) pieces get shorter, so at equal BYTES each run casts votes over more positions — vote evidence per byte of text rises; (c) every surviving id is roughly twice as frequent, so the tail-starvation documented in the audit halves with it. Judged at equal bytes (steps rescaled by the measured bytes/piece ratio) and reported in nats/byte.
- **exact change:** new `--vocab N` in train.py (threaded into `Tiny` and the corpus loader) + tokenizer build flag `--tokenizer refit --vocab 2048`; corpus rebuilt as `corpus-v2048.u16`; run `--arm layered_half --rope --vocab 2048` with `--steps` scaled to the equal-byte budget.
- **mode:** process — isolated train.py subprocess (new flag + rebuilt corpus); stays isolated until it has a full-trial record
- **prediction:** nats/token worsens (+0.05..+0.15, expected and irrelevant); **nats/byte −0.01..−0.04 vs the champion's 1.429** at equal bytes, driven by evidence density and table halving. Falsifier: if nats/byte is flat at 2048, the evidence-density story is wrong and TK-010's endpoint is not worth its probe.
- **status:** queued
```mill
id: TK-001
mode: process
run: --arm layered_half --rope --vocab 2048
```

### TK-002 ★ · Embedding rows join the vote trainer (tied, ternary, vote-trained)
- **source:** train.py code audit — the vote trainers vote on every `BitLinear` weight and nothing else; the tied table, 83% of served bytes, is the one large weight matrix still trained by full FP AdamW, the exact arrangement the vote trainer exists to replace.
- **mechanism:** The tied table gets the Layered treatment: each element carries two int8 counters (V=32, median strong gate, one component flip per step), installed as ternary × per-row scale, and the SAME installed table serves both roles (input lookup and head, transposed). Rows flip on accumulated sign evidence exactly like body weights. AdamW keeps only norms, `log_scale`s and the per-row scales. Exact differences from taken entries: MILL-118 quantizes the table to INT8 but keeps it AdamW-trained FP underneath — no counters, no flips, no trainer change; A-081 ternarizes an UNTIED head while the input embedding stays FP — here both roles share one vote-trained table and tying is the point (a flip must earn its keep in both roles at once).
- **exact change:** new trainer path `--emb-vote` on Layered: `model.tok.weight` is removed from the AdamW group, given `t1/t2/c1/c2` state (786,432 × 2 counters ≈ 1.57 MB of trainer state, charged honestly) and an `install()` analogous to BitLinear's, with per-row scales replacing the per-layer scalar.
- **mode:** process — isolated train.py subprocess (trainer code-path change)
- **prediction:** held +0.04..+0.12 nats/token (a real cost — the head is a classifier and ternary classifiers are coarse), against served bytes 3,806,208 → ~860,000 (table becomes 196,608 B packed + 16,384 B of per-row scales). Adoption bar, stated in advance: **a cost ≤ +0.05 buys a 4.4× served-byte cut and is a per-byte win; ≥ +0.12 kills it** and prices FP embeddings as genuinely load-bearing, which retires TK-004/TK-006/TK-007 with it.
- **status:** queued
```mill
id: TK-002
mode: process
run: --arm layered_half --rope --emb-vote
```

### TK-003 ★ · Post-training vocab excision and tail merge (readout-side compression)
- **source:** DATA-AUDIT §2 — 548 of 4,096 ids never occur anywhere in the token stream (train or held; held windows are windows of the same stream), and 1,984 ids occur <100 times. Their rows are 420,864 B (dead ids alone) of served weight that no input can ever address.
- **mechanism:** Readout-only, on a finished champion, in two separately reported steps. (a) **Excision:** delete the 548 never-occurring rows and renumber — zero loss by construction, verified by re-scoring held before/after (any delta at all means the audit's count was wrong, which is itself a finding). (b) **Tail merge:** for ids occurring <10 times, delete the row and retokenize — at build time those pieces are re-segmented into their BPE children, which exist by construction (every merge has parents in the table). The served model never sees the deleted ids because the tokenizer can no longer emit them. No retraining anywhere; the merge step's cost is measured on held in nats/byte (retokenization changes piece counts).
- **exact change:** no training change; new eval/build tooling `mill/vocab_prune.py --drop-dead --merge-below 10` producing a pruned checkpoint + pruned tokenizer; held scored with the standard `held_loss()` body on the retokenized held stream.
- **mode:** process — eval-side runner; stays isolated until it has a full-trial record
- **prediction:** step (a) −420,864 B served (−11.1%) at exactly 0.000 nats cost; step (b) a further −0.4..−0.7 MB at **nats/byte +0.000..+0.005** (the merged pieces carried almost no trained structure — their rows sat near the std-0.02 init). If (b) costs more than +0.01 nats/byte, tail rows were earning real bytes and the starvation picture in TK-007 needs revising downward.
- **status:** queued
```mill
id: TK-003
mode: process
run: --arm layered_half --rope --readout vocab-prune
```

### TK-004 · Frequency-split embedding: frequent rows FP, tail rows vote-ternary
- **source:** DATA-AUDIT §2 frequency split + the task's own question (should embedding rows be ternary *partially*?) — the corpus's frequency distribution is so skewed that a single precision for all 4,096 rows is the one choice nobody would pick from the data.
- **mechanism:** Split the tied table by corpus frequency at rank 1024: the top-1,024 rows (which carry the overwhelming majority of positions) stay FP/AdamW exactly as today; rows 1025–4096 are vote-trained ternary with per-row scales, TK-002's machinery restricted to the tail. The bet: tail rows receive so few input-side updates that they sit near init under AdamW anyway, so ternarizing them destroys almost nothing, while the rows that matter keep full precision. Exact difference from MILL-118: uniform INT8 over all rows, AdamW-trained — this is a *split by frequency* with two different trainers, not one quantizer. Difference from TK-002: TK-002 ternarizes the head-critical frequent rows too; this entry is the conservative half of that bet, and the pair brackets the cost curve.
- **exact change:** new flag `--emb-split 1024` on Layered: tail rows leave the AdamW group and gain counters/install as in TK-002; the split is computed from corpus counts at build time and logged.
- **mode:** process — isolated train.py subprocess (depends on TK-002's embedding-vote plumbing; defer until it lands)
- **prediction:** held +0.00..+0.03 nats/token vs champion, served bytes −~2.2 MB (tail becomes 147,456 B packed + 12,288 B scales, top stays 786,432 B). If the cost lands at the top of that range or above, frequency is not the right split variable and TK-002's uniform form is the honest comparison.
- **status:** queued
```mill
id: TK-004
mode: process
run: --arm layered_half --rope --emb-vote --emb-split 1024
```

### TK-005 · BPE-dropout segmentation: rare pieces testify through their children
- **source:** Provilkov et al., "BPE-dropout" (ACL 2020) and Kudo, "Subword Regularization" (ACL 2018), aimed at the audit's specific pathology: 1,984 ids with <100 occurrences whose rows and whose downstream vote evidence are starved *as units*, even though their sub-pieces are frequent.
- **mechanism:** During training only, each piece is stochastically decomposed: with probability p=0.1 per merge, a token is replaced by its BPE children (recursively), so the same text reaches the model at varied segmentations. Rare long pieces stop being atomic dead ends — their occurrences distribute evidence to their frequent children, and the body learns compositional structure the atomic table cannot express. Eval/held always uses the canonical segmentation, so the judge is unchanged. Exact difference from B-002/B-003: both change the *fixed* tokenizer (refit / superwords) and rebuild one canonical corpus; this keeps the canonical tokenizer and varies segmentation per presentation — the variable is evidence routing inside the vote trainer, not the merge table. Difference from A-052 (span-noise masking): that corrupts inputs with a mask embedding; this re-segments into real pieces.
- **exact change:** corpus pipeline change — training windows are drawn from the source texts and tokenized on the fly with `--bpe-dropout 0.1` (merge-dropout in the tokenizer encode step); held path untouched. Requires the text-side pipeline B-002's refit already implies; the pre-tokenized `corpus.u16` cannot express this arm.
- **mode:** process — isolated train.py subprocess (data-path change); full-trial only, probe horizons under-sample the segmentation variety
- **prediction:** **nats/byte −0.01..−0.04** at equal bytes, with the diagnostic that decides *why*: per-row input-update counts for tail ids' children rise measurably, and held loss on windows containing rare pieces improves more than the global mean. A global win with no rare-window concentration would mean it acted as generic regularization, not as the starvation fix claimed.
- **status:** queued
```mill
id: TK-005
mode: process
run: --arm layered_half --rope --bpe-dropout 0.1
```

### TK-006 · Dual-role counters: a tied row flips only when both its jobs agree
- **source:** train.py code audit — under tying, one row's gradient is the sum of two streams with wildly different characters: head-role evidence is dense (every row, every position, mostly small negative pushes `p_v·h`) and input-role evidence is sparse but large (only on occurrence). A single counter (TK-002's form) lets the dense stream outvote the sparse one ~256:1 per occurrence, so rows would flip to please the classifier role while their input representation is still unformed.
- **mechanism:** On the TK-002 chassis, each row-element carries TWO counters: `c_head` accumulates votes from the head-role gradient component, `c_in` from the input-role component (the two are separable — they arrive through different ops on the same weight). A flip fires when `|c_head + c_in| ≥ 32` AND `sign(c_in) == sign(c_head + c_in)` — the input role holds a veto, the head role cannot flip a row against the direction its occurrences are pulling. Costs one extra int8 per element over TK-002 (~0.79 MB trainer state, charged).
- **exact change:** new flag `--emb-dual` on top of `--emb-vote`: the trainer splits `tok.weight.grad` into its two role components by computing the head gradient from the logits path and taking the input component as the remainder; dual counters, veto flip rule, shared install.
- **mode:** process — isolated train.py subprocess (depends on TK-002's plumbing)
- **prediction:** −0.01..−0.04 nats/token vs TK-002 at identical served bytes — i.e. it recovers a quarter to a third of TK-002's predicted cost if role interference is real. Read against TK-002 directly, never against the champion: a flat result kills the interference story and leaves TK-002 as the simpler truth.
- **status:** queued
```mill
id: TK-006
mode: process
run: --arm layered_half --rope --emb-vote --emb-dual
```

### TK-007 · Tail-row threshold discount: V scaled to the evidence a row can actually receive
- **source:** DATA-AUDIT §2 + F-043's dilution logic applied per-row instead of per-model — F-043 argues a global V=32 starves weights as N grows; a rare token's row is the limiting case: at <8 expected occurrences per run, its elements cannot accumulate 32 net *input-role* votes in a run of any length the lab can afford. Under a uniform V, tail rows are not trained slowly — they are structurally frozen at init while still costing full FP bytes.
- **mechanism:** On the TK-002/TK-004 chassis, the flip threshold becomes per-row: `V_row = clamp(round(32 · sqrt(f_med / f_row)), 4, 32)` for rows below the median frequency `f_med`, 32 above it. A row expecting 1/64th of the median evidence gets V=4 — it can flip a handful of times per run on the evidence it actually receives, no more (the sqrt keeps the discount conservative: full proportional scaling would hand the rarest rows V<1, i.e. flip-on-first-vote). Exact difference from MILL-207/208 (per-LAYER flip-rate feedback) and F-043 (one global V chosen from N): this V is per-ROW, set from corpus frequency before the run, no feedback loop. Difference from A-049: that downweights frequent-token *windows* in sampling; this changes no sampling — it reprices the flip for the rows sampling cannot save.
- **exact change:** new flag `--emb-vfreq` on the embedding-vote trainer: per-row threshold tensor computed from the corpus count table at trainer construction; flip test uses `V_row` broadcast across the row.
- **mode:** process — isolated train.py subprocess (depends on TK-002 or TK-004 landing first)
- **prediction:** −0.005..−0.025 nats/token vs its undiscounted parent arm (TK-002 or TK-004), concentrated in held windows containing tail pieces — report the rare-window split, not just the mean. Failure signature to watch: tail-row flip counts exploding while held worsens = the discounted rows were better frozen, and V=32's "starvation" was actually protection.
- **status:** queued
```mill
id: TK-007
mode: process
run: --arm layered_half --rope --emb-vote --emb-vfreq
```

### TK-008 · Vocab 8192 at the champion and the 2M rung — the small end of the crossover
- **source:** F-051's own framing, completed at the end it skips — F-051 runs 16384 only at 50M and predicts the 10M point negative without running anything between 4,096 and 16,384 or below 10M. The crossover it promises as "the deliverable" cannot be located from one point.
- **mechanism:** Refit at vocab 8192, rebuild, run at BOTH the champion shape (dim 192 × 2) and the 2M rung (dim 288 × 2, ladder format, 56 steps), judged in nats/byte at equal bytes. Longer pieces mean fewer positions per byte (less vote evidence per byte — the anti-TK-001 direction) but each position carries more text and ctx 256 spans ~15–25% more real text. At dim 192 the table doubles to 6,291,456 B — this arm is expected to lose at the champion and is run to *measure* the loss slope, so the dial's curve has three points (2048 / 4096 / 8192) at lab scale instead of opinions.
- **exact change:** `--tokenizer refit --vocab 8192` + `--vocab 8192` runs at both shapes (2M form: `--dim 288 --layers-n 2 --steps 56 --tag scale2m`).
- **mode:** process — isolated train.py subprocess (new flag + rebuilt corpus, shared with TK-001)
- **prediction:** champion shape: **nats/byte +0.02..+0.06 (worse)**; 2M rung: +0.00..+0.04 — the penalty shrinking with dim is the prediction that matters, because its slope extrapolates to F-051's claimed 50M crossover. If the penalty *grows* with dim instead, F-051's premise (vocab gets cheaper as the body grows) is inverted at every scale this lab can reach and F-051 should be re-read before its 50M probe is spent.
- **status:** queued
```mill
id: TK-008
mode: process
run: --arm layered_half --rope --vocab 8192
```

### TK-009 · Untied FP head at the 2M rung (ladder format)
- **source:** MILL-119 (untied FP head) exists only at the champion shape, where untying doubles a 3,145,728 B table to win capacity the shape may not need; CANDIDATES-C's Family A established that several champion-shape readings do not transfer across rungs, and tying is exactly the kind of claim that flips with the table-to-body ratio (at dim 288 the table is 4,718,592 B against 1,990,656 ternary weights).
- **mechanism:** The 2M rung with `--untie-head`: input embedding stays FP/AdamW, the head becomes its own FP table (another 1,179,648 params). Ladder format (56 steps, equal tokens) removes the step-count confound that makes the champion-shape version hard to read. The question is rung-specific: does the head's classification geometry, freed from the input representation, earn more at dim 288 — where each row is wider and the two roles' geometry differs more — than the +4,718,592 B it costs?
- **exact change:** no new flag (MILL-119's `--untie-head`); run `--arm layered --rope --dim 288 --layers-n 2 --steps 56 --untie-head --tag scale2m`. Exact difference from MILL-119: shape (2M rung vs champion), format (ladder vs probe/trial), and verdict (per-byte at the rung vs per-byte at the champion) — a merge should keep both records, not collapse them.
- **mode:** sweep — config-only via the pooled flag once it lands; ladder format only, a 75 s probe is a smoke read and must not be verdicted as a rung result
- **prediction:** −0.01..−0.04 nats/token vs the rung's 3.2745 if untying earns more with width; judged per served byte it must clear the doubled table, so the adoption bar is the strict one: a nats/token win under −0.02 is still a per-byte loss and should be recorded as such.
- **status:** queued
```mill
id: TK-009
mode: sweep
run: --arm layered --rope --dim 288 --layers-n 2 --untie-head
```

### TK-010 · Vocab 1024 — the dial's endpoint
- **source:** TK-001's dose curve — CANDIDATES-C's discipline (a dial is not measured until its extremes are priced) applied to vocab: 2048 tests the direction, 1024 tests whether the direction *keeps paying* or turns over.
- **mechanism:** Refit at vocab 1024, rebuild, champion chassis, equal bytes, nats/byte. At 1024 the table holds 196,608 params (786,432 B FP32 — fewer parameters than the 884,736 ternary weights for the first time), pieces approach character n-grams, and ctx 256 covers the least text of any arm — the context-starvation cost that must eventually beat the evidence-density gain. Where the curve turns over IS the vocab law for this trainer: below the turn, positions are too poor in content; above it, rows are too starved to train.
- **exact change:** `--tokenizer refit --vocab 1024` + `--arm layered_half --rope --vocab 1024`, steps rescaled to the equal-byte budget as in TK-001.
- **mode:** process — isolated train.py subprocess (shares TK-001's plumbing)
- **prediction:** nats/byte +0.01..+0.05 vs TK-001's 2048 point (the turn is expected between 1024 and 2048) but still within ±0.03 of the 4096 champion's 1.429 — i.e. a wide plateau, which would make vocab a *byte-allocation* choice (pick by served bytes, loss barely cares) rather than a quality dial. A continued gain at 1024 instead re-opens the whole dial downward and is the highest-information surprise available in this file.
- **status:** queued
```mill
id: TK-010
mode: process
run: --arm layered_half --rope --vocab 1024
```

### TK-011 · Space-attachment pretokenization: kill the bare-space piece
- **source:** DATA-AUDIT §2 — the corpus's most common piece is a bare space (id 222, 10.2% of all pieces). One position in ten carries no content, casts votes on a whitespace prediction, and shortens every 256-piece window's real span by ~10%.
- **mechanism:** Change only the pretokenization rule: a space attaches to the FOLLOWING piece (the GPT-style `Ġword` convention this tokenizer evidently lacks), then refit merges at the same vocab 4096 and rebuild. Pieces per byte falls ~9–10%; every position in every window is content-bearing, so vote evidence per byte rises by the same fraction with no size, trainer, or budget change. Exact differences: B-002 refits with the SAME rules (the space piece survives its refit); B-003's SuperBPE drops whitespace pretokenization to merge ACROSS words into multi-word superwords — this keeps word boundaries intact and absorbs exactly one leading space, the minimal rule change that removes the waste piece.
- **exact change:** tokenizer build flag `--pretok space-attach` + refit at 4096; run `--arm layered_half --rope --pretok space-attach` at equal bytes vs champion.
- **mode:** process — isolated train.py subprocess (tokenizer build change + rebuilt corpus)
- **prediction:** **nats/byte −0.005..−0.02** — the smallest predicted win in this file, but also the cheapest mechanism per unit effect (one rule, no new parameters, no trainer state), and it stacks multiplicatively with TK-001/TK-010 (the dial arms should be re-read under whichever pretokenization wins). Falsifier: if pieces/byte does not fall by ≥7% at refit, the corpus's spaces are not where the audit's count implied and the entry dies at build time, before any probe.
- **status:** queued
```mill
id: TK-011
mode: process
run: --arm layered_half --rope --pretok space-attach
```

### TK-012 · Byte-metered windows: sample fixed bytes, not fixed pieces (the judging enabler)
- **source:** mill methodology, from this lens's own problem — every cross-vocab verdict above (TK-001/005/008/010/011) compares arms whose windows hold different amounts of text, because train.py samples windows of 256 PIECES (`offsets()` over the piece stream) and the held set is 128 piece-windows. "Equal bytes" is currently an accounting correction applied after the fact, not a property of the runs.
- **mechanism:** The sampler draws windows of a fixed BYTE budget (512 source bytes = the champion's 256 pieces × 2.00 B/piece at vocab 4096; the piece count per window then varies with the tokenizer), and held is rebuilt as fixed-byte windows scored as total nats over total bytes. Two claims: (a) methodological — cross-vocab comparisons become equal-text by construction, removing the rescaling assumption TK-001/TK-008/TK-010 otherwise carry; (b) as a training arm at 4096 itself — windows of uniform *text mass* rather than uniform piece count remove a subtle bias where dense, short-piece regions of the corpus (the audit's boilerplate and number streams tokenize short) are over-represented per window relative to their byte share.
- **exact change:** new sampler flag `--byte-windows 512` in train.py (offsets drawn over a byte-indexed stream; window = the pieces covering the next 512 bytes) + held-set builder emitting `held_bytes` alongside `held_loss` for every arm that runs under it.
- **mode:** process — isolated train.py subprocess (sampler code-path change); the 4096 control arm runs first and must reproduce 2.8580 ± 0.0161 within noise before any cross-vocab reading is trusted
- **prediction:** at 4096, held within ±0.01 of the champion (a flat control is the PASS condition — this entry sells validity, not loss). Its real prediction is about the other entries: at least one of TK-001/TK-008's rescaled verdicts will move by ≥0.01 nats/byte when re-judged under byte-metered windows, because piece-uniform sampling is not byte-uniform sampling on this corpus.
- **status:** queued
```mill
id: TK-012
mode: process
run: --arm layered_half --rope --byte-windows 512
```

---

## Ranking rationale (one line each)

1. **TK-001 ★** — the territory's central untested claim, at the scale where the table is 83% of served bytes; cheap (one refit + one run) and it sets the dial's direction for everything below it.
2. **TK-002 ★** — the largest byte prize in the file (4.4× served) and the only entry that asks whether the lab's founding mechanism should govern its largest matrix; its verdict also gates TK-004/006/007.
3. **TK-003 ★** — the only entry with a zero-risk component: 420,864 B back at exactly 0.000 nats by construction, on already-trained champions, today.
4. **TK-004** — TK-002's conservative half; the likeliest per-byte win among the training entries, ranked below it only because it depends on its plumbing.
5. **TK-005** — attacks starvation from the evidence side rather than the threshold side; the rare-window diagnostic makes it falsifiable in a way pure regularization entries are not.
6. **TK-006** — a genuinely new mechanism (role-veto counters) that only exists because the table is tied; high information whether it wins or reads flat against TK-002.
7. **TK-007** — the direct starvation fix, but it is a companion arm twice-dependent on TK-002/TK-004 landing, and its effect size is bounded by the tail's held share.
8. **TK-008** — expected-negative at the champion by design; its value is the slope toward F-051's crossover, and it is the only entry here that can falsify another file's premise.
9. **TK-009** — completes MILL-119 at the rung where tying is most expensive; cheap in ladder format, but the per-byte bar is strict and a nats/token win may still lose.
10. **TK-010** — prices the dial's endpoint; mostly curve-completion, with a small chance of the file's biggest surprise.
11. **TK-011** — smallest effect, near-zero cost, stacks with everything; ranked low on size, not on efficiency.
12. **TK-012** — sells verdict validity rather than loss; ranked last as an idea, but it should probably be BUILT first, since TK-001/008/010/011 all borrow its judging law.

*End of wave-3 lens 2. 12 entries (TK-001..TK-012), Muse's work, Muse's side. Nothing here edits IDEA-POOL.md or any CANDIDATES file; merge is the pool owner's call.*
