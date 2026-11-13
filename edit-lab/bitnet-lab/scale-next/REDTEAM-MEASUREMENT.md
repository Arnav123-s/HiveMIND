# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# RED TEAM: measurement attack on the overlap program (tilted BitNet ensemble/router)

**Target design, as specified:** 4 tilted BitNet generalists (dim 512 × 3 layers,
9.44M ternary weights each; layered + rotary + vote training; tilt = 55% uniform +
45% own-bucket data) + a weakness-exchange round, read as an ensemble/router system.
Must beat, at EQUAL TOTAL SERVING BYTES: (a) one plain generalist, (b) 4 narrow
specialists trained only on their buckets. Metrics: composite held loss on the lab's
standard fixed 128 held windows (256 tokens each, every-40th rule), per-bucket held
loss, worst-bucket loss. Historical adoption bar: >2 sd and >0.01–0.02, 3 seeds.

**Verdict up front:** as specified, this design can declare at least five different
wins that are not real, and two of them are *biases* (they do not average away with
more seeds). Do not build it until §1 and §3 are fixed in a written pre-registration.
Grounding below is from this lab's own files: `train.py` (`held_windows`,
`held_loss`, `offsets`, the `Tiny`/`Layered` shapes), `runs.jsonl`, `DATA-AUDIT.md`,
and `RESULTS-HALF-CONTROL-2026-11-12.md`.

---

## 1. Serving-bytes accounting — the equality in the headline is currently undefined, and every plausible miscount favours the ensemble

Exact param arithmetic for the proposed member shape (dim 512, 3 blocks, vocab
4096, CTX 256 — matches the `layered_rope_scale10m` record in `runs.jsonl`:
9,437,184 ternary, 11,686,400 total params):

| Component | Params | FP32 bytes |
|---|---|---|
| Ternary positions per member | 9,437,184 | see below |
| Token embedding (4096×512) | 2,097,152 | 8,388,608 |
| Position table (256×512) | 131,072 | 524,288 |
| Norms + biases + final norm | 20,992 | 83,968 |
| **Non-ternary (FP) total** | **2,249,216** | **8,996,864** |

Three facts that break naive accounting:

1. **FP dominates.** Honest serving size per member, with the layered weights packed
   at 2 bits per ternary *component* (see point 2): 4,718,592 B ternary +
   8,996,864 B FP = **13,715,456 B, of which 65.6% is FP, and 65.0% is embeddings
   alone** (token + position). At the ladder's 2M shape it is the same disease:
   1,261,440 of 3,252,096 params are FP. Any accounting error on embeddings is an
   error on two-thirds of the budget. "BitNet" in the name does not make the model
   mostly ternary *by bytes*.
2. **The design's own headline number already undercounts the ternary part.**
   "9.44M ternary weights" is the *position* count (`runs.jsonl`'s
   `ternary_weights` = `t1` numel). A layered weight is `t1 + t2` — **two** physical
   ternary components, 5 levels (−2..+2). At 2-bit packing that is 0.50 B/position,
   not 0.25 B/position. Anyone who budgets `9.44M × 0.25 B` has silently halved the
   ternary bytes before the experiment starts. (A 3-bit code for 5 levels,
   0.375 B/position, is legitimate — but only with working pack/unpack code and a
   lossless round-trip test in the repo, not as an assumption in a spreadsheet.)
3. **The cheat surface is worth 2–3×, asymmetrically.** Per-system totals under
   different "honest mistakes":
   - Honest, unshared, FP32: 4 × 13,715,456 = **54,861,824 B**.
   - Embeddings shared across the 4 members (one token+position table loaded once):
     **28,123,136 B** — a 1.95× saving. Sharing may even be the right engineering;
     it is still a *different budget* than the unshared number, and baseline (b),
     4 narrow specialists, could claim the identical trick. If the ensemble shares
     and the specialists are counted unshared (or vice versa), one side gets ~2×
     the real budget of the other.
   - Counting only ternary weights: ensemble "costs" 18,874,368 B against a real
     54,861,824 B — a **2.91× hidden budget**.
   - FP16 embeddings (all FP at FP16): 9,217,024 B/member, 32.8% smaller than FP32
     honest. If the ensemble ships FP16 embeddings and baseline (a) is costed at
     FP32, the ensemble has bought ~4.5 MB/member of extra ternary capacity with a
     precision change that was never declared as an arm.
   - The position table is a free 524,288 B/member of ambiguity by itself:
     `train.py` carries it even with `--rope` ("the table of places (pos) is
     carried, as in Fable's shape, but not used"). Count it in all arms or drop it
     from all artifacts — not per-arm convenience.
   - The router is not free either: any learned prefix router has weights,
     thresholds, or a codebook; the per-layer FP scales, biases and norms count
     too. Individually small, collectively unaudited = collectively gameable.
   - Precedent for exactly this confusion exists in the lab: `runs.jsonl` records
     `mech_state_bytes`, which is *training* state (vote counters included — 2.5
     B/position for layered). Serving bytes and mechanism state have already been
     used interchangeably once in this lab's bookkeeping. This design must not
     inherit that.

   For scale: in this lab, budget differences of this size are worth far more than
   the adoption margin. Full→half size changes moved held loss by ~0.17
   (`RESULTS-HALF-CONTROL-2026-11-12.md`); the 2M→10M ladder rungs differ by ~0.33.
   A hidden 1.95–2.91× byte advantage is not a rounding error — it is larger than
   any effect the program is trying to detect, pointed in one direction.

4. **"Equal bytes" does not even pin down baseline (a).** Two readings of the
   design differ by 4×: (i) the plain generalist is one member-sized model
   (13.7 MB) — then the ensemble has 4× its bytes and the headline is false on its
   face; (ii) the generalist is scaled to the full 54.86 MB — then it is a
   different ladder rung entirely (at fixed FP it could afford ~9.7× one member's
   ternary positions; in practice a wider/deeper shape whose own FP also grows),
   with different steps/minute, different token starvation, and no established
   variance. The design as written does not say which. Until it does, "beats (a)
   at equal bytes" is not a claim, it is a slogan.

## 2. Equal bytes is the wrong sole equality — compute, steps, and training tokens are all free to confound

- **Inference compute.** A logit-averaging read of 4 members costs ~4× the FLOPs
  per token of one member; a routed read costs ~1× but keeps 4× resident. A single
  generalist honestly scaled to 54.86 MB dense costs ~4× per token too. So
  "ensemble wins" can mean three different systems (4× bytes/1× compute,
  4× bytes/4× compute, 1×-bytes-equivalent/4× compute) with three different
  deployment stories. The design must declare **one** serving read as primary
  (routed or averaged), and report FLOPs/token and wall/token for every system.
- **The steps confound has already burned this lab once.** The layered-half "win"
  was retracted because a time-boxed smaller model took ~40% more steps
  (`RESULTS-HALF-CONTROL-2026-11-12.md`: plain_half 2.9010 vs layered_half 2.8990,
  difference 0.0020). This design multiplies that risk: 4 members + an exchange
  round, against baselines with different per-step costs. If runs are time-boxed,
  step counts will differ; if step-matched, training tokens and wall differ.
  Pre-register the primary training equality (fixed steps × batch × CTX = fixed
  tokens, as the ladder does with `--steps 56`), and publish steps/tokens/wall
  per arm regardless.
- **The exchange round is extra training until proven otherwise.** If members get
  tilt training + exchange training while (a) and (b) get only their first phase,
  the ensemble has strictly more gradient steps on strictly more curated data.
  Any exchange effect is then indistinguishable from "trained longer on selected
  data" (see §7 for the placebo control that separates them).
- **Tilt arithmetic nobody has written down.** A member's stream is 55% uniform
  (≈13.75% own-bucket in expectation) + 45% own-bucket = **58.75% own, 41.25%
  other**. A narrow specialist at equal tokens sees 100% own-bucket but cycles a
  pool one quarter the size ~4× as often (repetition, not fresh data — and per
  `DATA-AUDIT.md` the whole corpus holds only ~0.91M unique real pieces). Publish
  the per-bucket token counts actually consumed by every arm; "trained only on
  its bucket" without a token count is not a specification.

## 3. Per-bucket and worst-bucket losses cannot resolve the adoption margin — the numbers forbid it

- The judge is 128 windows (`held_windows` in `train.py`: every-40th aligned
  window, 128 picked evenly from 578 held starts; `held_loss` scores 128 × 256 =
  32,768 tokens). Split 4 ways that is **≈32 windows per bucket — if the split is
  even, which nothing guarantees** (§6). The unit of independence is the window,
  not the token: anyone quoting a standard error over 8,192 tokens per bucket is
  manufacturing ~16× too much precision.
- What sd does 32 windows buy? Seed-to-seed sd of the *composite* (128-window)
  mean in `runs.jsonl` runs 0.0073 (layered_half) to 0.0316 (plain), 0.0119 at the
  2M ladder rung. Per-bucket means carry window-sampling noise on top of that:
  for any plausible per-window loss spread (σ_w ≈ 0.4–1.0 across this corpus's
  mix of prose, boilerplate and number streams), the standard error of a 32-window
  bucket mean is **0.07–0.18**, and of an unpaired bucket difference **0.10–0.25**.
  Even a fully paired per-window difference with an optimistic difference-sd of
  0.2–0.3 gives SE ≈ **0.035–0.053** — still 2–5× the 0.01–0.02 margin the design
  wants to resolve. **A 0.02 per-bucket "win" at n=32 is 0.4–0.6 standard errors.
  It is not a measurement; it is a coin flip with a narrative attached.**
- **Worst-bucket is worse: it is a maximum of 4 noisy estimates.** Its sampling
  distribution is wider than any single bucket's, it is biased upward, and across
  arms it does not even necessarily name the same bucket. An arm with higher
  per-bucket variance is mechanically punished on worst-bucket at equal true
  means; an arm can also "win" worst-bucket because its noisiest bucket happened
  to draw easy windows. As a *decision* metric at n≈32/bucket it is unusable; as
  a descriptive statistic it is fine.
- **The ">2 sd" bar is soft exactly where this design leans on it.** With 3 seeds,
  the sample sd has 2 degrees of freedom; its 95% CI spans roughly 0.52×–6.3× the
  true sd. The lab has already hit the ambiguity in print: the half-control note
  records that the same comparison's 2-sd bar is 0.0145 using one arm's sd or
  0.0552 using the other's. A 0.02 margin against a bar that can be quoted as
  0.015 or 0.055 depending on which sd you pick is a bar that can be picked
  *after* seeing the result. And formally, a 2-sd margin at n=3 is t ≈ 3.46 on
  2 df, p ≈ 0.074 per comparison — before any multiplicity correction (§5).

## 4. The router read: prefix peeking, oracle confusion, and the free ensemble gain

- **As specified, the prefix read leaks into the lab's own judge.** The router
  "peeks at the first 32 tokens of the judged window." `held_loss` scores **all
  256 positions**, including positions ≤32. For those positions the router has
  seen tokens the causal model has not — including the target token itself and
  its successors — when choosing which member predicts them. That is lookahead
  on 32/256 = **12.5% of every scored window**. The fix is trivial and therefore
  inexcusable to skip: either score only positions 33–256 for every arm in the
  routed read, or make the router causal (route position *t* using only tokens
  < *t*). Note the asymmetry if left in: baseline (a) gets no equivalent
  lookahead, so even a small per-position gain on the prefix (~0.02–0.05 would
  suffice) converts to a composite gain on the order of the adoption bar.
- **Routing on the prefix is legitimate only under conditions the design does not
  state:** the router's parameters/thresholds are fit on training-pool data only,
  frozen before judging, and never selected using held losses (including "we tried
  three routers and report the best"). A router chosen by held performance is
  held-set training with extra steps.
- **Oracle routing is not a serving system.** If any read picks the member with
  the lowest loss on the window (or on its prefix, scored), that is a per-window
  winner-pick on test data. Reported, it will look like the program's best number
  and will be cited as such forever. Oracle numbers, if computed at all, must be
  labelled "ceiling, not a system" and excluded from the adoption comparison.
- **The missing control that kills the attribution:** logit-averaging 4 models
  reduces held loss *generically* — different seeds of the same recipe, no tilt,
  no exchange, will also "win" against a single model on log-loss. Without a
  control arm **4 untilted generalists, same recipe, different seeds, same bytes,
  same read**, the program cannot distinguish "tilt + exchange works" from
  "ensembles work." The same applies to routing: a router over 4 seeds is the
  honest null for a router over 4 tilts.

## 5. Multiple comparisons: the design as listed will find a win by construction

Count the reads the design already names: systems {tilted ensemble, tilted+exchange
ensemble, (a), (b)} × reads {routed, averaged, oracle?} × metrics {composite,
4 per-bucket, worst-bucket} — conservatively **30–60 comparisons**, before anyone
looks at per-member losses, alternative router thresholds, or "the exchange helped
bucket 3" sub-stories. At the lab bar's effective per-comparison false-positive
rate (~0.05 nominal, ~0.074 at n=3 as computed in §3), the family-wise chance of
at least one spurious "win" is **≈79–90% at 30 comparisons, ≈95–99% at 60**.
With no declared primary metric, the three named metrics also form a pick-your-
winner set: composite can be carried by the majority bucket while worst-bucket
regresses, and either story can be headlined after the fact.

**Required pre-registration (minimum):** one primary system comparison, one
primary read, one primary metric, the exact sd to be used (pooled, named in
advance), a Bonferroni or hierarchical gate for everything else, and a written
rule that all other numbers are exploratory and cannot trigger adoption. Freeze
it, with the byte manifest (§8), before the first training run.

## 6. Buckets and the held set are not what the design assumes

- **Held windows are picked by stream position, not stratified by bucket.**
  `held_windows` spaces 128 picks evenly over the token stream; the corpus was
  built file-by-file in sorted path order (`make_corpus.py`), so sources — and
  any source-defined buckets — occupy *contiguous* stream regions. Bucket counts
  among the 128 will follow source shares, not 32/32/32/32. `DATA-AUDIT.md`'s
  source mix (73.9% of source bytes are venv/HF-cache junk; two German files
  10.6%) shows how skewed those shares can be. A small bucket may contribute
  single-digit windows, making its "per-bucket loss" a anecdote. Publish the
  bucket label and count of every held window in the pre-registration; if counts
  are unequal, either build a stratified held set for this program (new judge,
  declared as such) or demote per-bucket/worst-bucket to descriptive-only.
- **Bucket labels must be a property of the source, fixed before training** —
  never the router's predicted bucket, never a member's assignment. If the router
  defines the slices it is judged on, it can win by relabelling hard windows.
- **Composite is a stream-weighted mean** (`held_loss` sums over tokens), so it
  silently weights buckets by held-window count. A tilt that helps the biggest
  bucket and hurts the smallest wins composite while failing the program's stated
  purpose. Report the bucket-equal mean alongside, and say in advance which one
  decides.
- **Which corpus?** The standard judge sits on v1, where `DATA-AUDIT.md` measured
  30.8% of pieces as exact duplicates of other pieces and concluded held content
  "routinely also appears in training windows." That flattery is common-mode for
  static arm-vs-arm comparisons — §7 shows why the exchange round breaks the
  common-mode defence. If this program runs on v2 instead, every historical sd
  and margin quoted above must be re-derived; do not carry v1 bars onto a v2 judge.

## 7. The exchange round: three contamination paths, one of them targeted

Selection rule as specified: exchange windows are training-pool windows selected
**by the members' own losses**. Paths to a fake win:

1. **Pool construction can quietly include held material.** The lab's clean pool
   exists only inside `offsets()`, which rejects any random-offset window whose
   start *or* end aligned block is a held block. An exchange pipeline needs a
   *fixed window list with per-member losses* — the natural implementation is an
   aligned stride over the corpus, i.e. the `held_windows` construction, which
   **includes** the held windows themselves and their neighbours unless the
   every-40th exclusion is explicitly re-applied. One forgotten filter and the
   exchange round is training on the judge. Requirement: the selection manifest
   (window start offsets + content hashes) is published before exchange training,
   with a machine-checked assertion of zero token-span overlap with the 128 held
   windows — not a verbal assurance.
2. **Duplication turns loss-based selection into a targeted leak.** Even with a
   perfectly span-disjoint pool, ~31% of this corpus's pieces are duplicates of
   text elsewhere, including in held windows. Static training samples that
   duplication blindly and roughly equally for all arms. The exchange round does
   not sample blindly: it selects precisely the windows a member is *worst* on —
   i.e. it preferentially harvests pool windows whose held-set twins the member
   has not memorised, trains on them, and is then re-judged on the twins. The
   resulting held gain is memorisation of held-adjacent text, concentrated
   exactly where the metric will look (that member's bucket). This is the one
   place in the design where the corpus's known duplication stops being a shared
   caveat and becomes a mechanism for manufacturing the headline result.
3. **Adaptive selection + extra steps, uncontrolled.** Iterated rounds (select by
   loss → train → re-select) adaptively overfit the pool; and any version where
   exchange adds steps instead of replacing tilt-phase steps confounds "exchange"
   with "more training." Required controls: (i) exchange replaces, not adds —
   total tokens per member identical across arms; (ii) a **placebo-exchange arm**:
   same extra/replacement steps, windows swapped at random instead of by loss.
   If placebo ≈ exchange, the loss-selection story is dead and must be reported
   dead. Also: selection is computed once, frozen and hashed; anyone inspecting
   held per-bucket losses between rounds and adjusting the exchange converts the
   held set into a validation set, after which it can no longer judge anything.

## 8. The narrow-specialist baseline (b) is a strawman unless its specification is repaired

- As specified, each specialist trains *only* on its bucket: no uniform anchor,
  ~1/4 the distinct data, repeated epochs over a small pool (§2). It will fail on
  shared structure, on bucket-boundary windows, and on any held window whose
  bucket is ambiguous — and the tilted members, which see 58.75% own-bucket data
  *plus* everyone else's, will look brilliant by comparison. That comparison
  proves "some shared data helps," which nobody doubts. It does not prove the
  tilt ratio, the overlap, or the exchange.
- It is also not the factory's notion of a specialist: the lab's actual specialist
  work trains task models through full pipelines with gates and held-out
  acceptance, not a data-starved single-bucket LM. Beating this baseline must not
  be reported as "beats specialists."
- Minimum repairs: specialists get the same total tokens, same steps, same
  recipe; add the fairer intermediate the design is afraid of — **tilted
  specialists** (e.g. 85–100% own-bucket with the same pipeline) or a specialist
  + shared-embedding variant if the ensemble is allowed shared embeddings (§1).
  And decide in advance how (b) is *served*: routed by true bucket (an oracle —
  label it), routed by the same prefix router (then router errors are part of
  (b)'s score, fairly), or all-4-averaged. Each choice moves (b)'s number; picking
  after the fact picks the winner.

## 9. Smaller holes that still move numbers at the 0.01–0.02 scale

- **Seed handling for members.** `train.py`'s convention — same seed → same init
  and batch stream — means "4 members, seeds 0–3" vs "4 members, seed 0 ×4 with
  different data order" are different systems with different ensemble diversity.
  Declare it. The untilted 4-seed control (§4) must use the identical convention.
- **Judge reuse.** The same 128 windows have now judged every arm in this lab for
  two days of experiments. Each published comparison adapts the lab's research
  direction to this set's idiosyncrasies. A fresh confirmation set (new held
  rule offset, e.g. every-40th shifted by 20, or v2's held windows) for the final
  adoption read would cost one eval pass and is the cheapest insurance in this
  whole document.
- **Reporting discipline.** Per-bucket tables must show window counts next to
  losses; any bucket with <20 held windows is reported as "unresolved," never as
  a win or a loss. All runs — including failed tilts and placebo arms — go to
  `runs.jsonl`; a design with this many reads and a selective log is a fishing
  log.

---

## The single strongest objection

**The headline claim — "beats (a) and (b) at equal total serving bytes" — is
currently meaningless, because serving bytes are dominated by FP parameters the
design never budgets, and every plausible accounting choice moves the real budget
by 2–3× in the ensemble's favour.** Per member, 65.6% of honest serving bytes are
FP (embeddings alone 65.0%); the design's "9.44M ternary weights" already halves
the ternary cost by counting layered positions instead of components; sharing
embeddings across members is a further 1.95×; counting ternary only is 2.91×.
These are not noise — they do not shrink with more seeds or more windows — and at
this lab's measured scale effects (0.17 for a 2× size change, 0.33 across ladder
rungs) a hidden budget of that size is *sufficient by itself* to produce the
0.01–0.02 "win" the program exists to detect, with no tilt, no overlap, and no
exchange effect present at all. Every other flaw above (§3's unresolvable
per-bucket margins run a close second) corrupts a comparison; this one corrupts
the *terms* of the comparison, asymmetrically, before training starts.

### The exact fix (pre-registration + accounting rule, to be frozen before any run)

1. **Serving system = the serialized artifact(s) actually loaded at inference**,
   including the router. Serving bytes = the sum of the artifact file sizes
   produced by one named serializer, verified by loading the artifacts and
   summing the distinct tensors resident in memory. Formula-based byte claims
   are not accepted.
2. **Everything counts:** token embedding, position table (present in the
   artifact ⇒ counted; the clean option is to drop it from *all* arms under
   rotary), per-layer scales, norms, biases, router weights/thresholds/codebooks,
   and any per-member metadata needed to serve. Layered positions count as two
   ternary components (floor 0.50 B/position at 2-bit packing); any denser code
   requires the pack/unpack code and a lossless round-trip test committed before
   runs begin.
3. **One precision for all:** FP32 for every non-ternary parameter in every arm,
   unless a precision change is itself a pre-registered arm applied identically
   in kind to all compared systems. No FP16-embedding ensemble vs FP32-costed
   baseline.
4. **Sharing is a property of the loader, not the spreadsheet:** a tensor is
   counted once only if the serving code demonstrably loads one copy used by all
   members — and the same rule is applied to baseline (b), whose specialists may
   share under exactly the same condition. Whether the program's systems share
   embeddings is declared in the pre-registration, for all arms, in advance.
5. **Budgets matched to ±1% on measured artifact bytes.** Baseline (a) is a
   single generalist whose shape is chosen to fill the ensemble's measured
   budget; its shape, and (b)'s serving read, are frozen in the same document.
   A per-system byte manifest (per-tensor table, total, artifact hash) is
   published **before the first training run**; any change to a manifest voids
   all runs made under it.
6. **Bytes are the headline equality, not the only reported one:** FLOPs/token
   and wall/token for the routed and averaged reads separately, plus training
   steps/tokens/wall per arm, are reported with the results — so a win bought
   with 4× inference compute is visible as exactly that.

With §8's rule frozen and §5's pre-registration (one primary comparison, read,
and metric; per-bucket and worst-bucket demoted to descriptive until a stratified
held set with adequate per-bucket counts exists), the remaining objections become
manageable. Without them, a positive result from this program should be assumed
to be an accounting artifact until proven otherwise.
