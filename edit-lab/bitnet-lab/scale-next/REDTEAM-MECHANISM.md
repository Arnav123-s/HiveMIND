# Muse's work — written by Muse, on Muse's side. Fable's side was not touched.

# RED TEAM: the overlap program (4 tilted generalists + weakness exchange)

**Design under attack:** 4 members, 10M-rung shape (dim 512 × 3 layers, 9.44M ternary
weights), layered + rotary + vote-counter recipe, same token budget. Tilt: 55% uniform
corpus + 45% own bucket. Round 2 (25% of round-1 tokens): each member trains on the
other members' worst-decile training-pool windows, weighted toward its own specialty.
System read: mean-distribution ensemble + a cheap router. Yardstick: beat (a) one plain
generalist of equal total serving bytes and (b) 4 bucket-only specialists at equal total
bytes, on composite and worst-bucket held loss.

**Verdict up front: do not build this as drafted.** The mechanism has a physics problem
that fires before any of its interesting questions get asked (§1), the corpus does not
contain the buckets the design is built on (§3), the "weaknesses" being exchanged are
mostly corpus garbage (§4), and the yardstick as specified cannot attribute a win to
the mechanism even if one appears (§8). Every prior transplant this lab tested with a
sparse, indirect signal (JEPA, magnitude votes, cooldown, carry) lost or dissolved
under its control. This design is three such transplants stacked, with the controls
removed.

All numbers below are from this lab's own records: `runs.jsonl`, `RESULTS-*.md`,
`DATA-AUDIT.md`, `train.py`.

---

## The ground numbers this attack stands on

| Fact | Value | Source |
|---|---|---|
| Flip share, 10M rung (9,437,184 ternary w) | **0.00021 / step** | `layered_rope_scale10m` s0 |
| Flip share, 2M rung | 0.00054–0.00059 / step | `layered_rope_scale2m` s0–2 |
| Flip share, 0.88M champion rung | 0.00107–0.00116 / step | `layered_half_rope` |
| Ladder budget | 56 steps = 458,752 tokens/run, all rungs | `run_scale_ladder.py` |
| 10M rung held loss at ladder budget | 2.9472 (1 seed), vs champion 2.8580 at 0.88M / ~160 steps | runs.jsonl |
| 10M final state histogram | −1: 0.3437, 0: 0.3081, +1: 0.3436, ±2: **0.47% total** | runs.jsonl |
| Init state histogram (any run) | −1: ~0.344, 0: ~0.310, +1: ~0.345 | runs.jsonl |
| Vote rule | flip at **32 net votes**; vote = sign only if \|g\| ≥ layer median; counters clamp ±32, reset on flip | `train.py` `Layered.step` |
| Corpus | 5.92M pieces, only **~0.91M unique real text**; 48% of lines redundant; 23% of pieces in numeric mega-lines; venv/HF junk 73.9% of source bytes | `DATA-AUDIT.md` |
| Corpus v2 natural categories | German 45.7%, Muse-side docs 28.8%, Fable-side docs 13.1%, lab notes 12.4% | `corpus-v2.json` |
| Held set | **128 windows** total, every-40th window of the same flat stream | `train.py` |
| Lab adoption bar | beat baseline mean by >2 seed-sd **and** >0.01, 3 seeds per arm | every RESULTS note |

---

## 1. The tilt cannot physically register in the served weights — this is the fatal one

The served model is the ternary states `t1 + t2` and nothing else. The vote counters —
where a tilt's influence accumulates — are **training state and are discarded at
serving**. A tilt that never pushes a counter to ±32 net votes leaves *zero trace* in
the artifact that gets ensembled, routed, and judged. So the whole design reduces to
one question: can a 45% mixture tilt push enough counters over the line, differentially
per member, inside the budget? The lab's own flip numbers say no, at exactly the rung
the design insists on.

- At the 10M rung, mean flip share is **0.00021/step**. Over the ladder's 56-step
  round 1 that is 0.00021 × 56 ≈ **1.18% cumulative flip events per weight** — about
  111k flip events spread over 9.44M weights. Even if every event hit a distinct
  weight (they don't; flips concentrate on high-gradient weights), **~98.8% of served
  weights are still the random init**. The final histogram proves it: after round 1
  at 10M the state distribution (−1: 0.3437 / 0: 0.3081 / +1: 0.3436) is the init
  distribution to the third decimal, and the layered ±2 levels — the second component
  that is supposed to carry nuance — are populated at 0.47%, vs 6.9–7.9% at the
  champion rung.
- Flip share *falls* as members grow: 0.11%/step at 0.88M → 0.057% at 2M → 0.021% at
  9.4M. The premise "members should be LARGE" selects for the regime where the
  trainer moves least. The mechanism has a scale ceiling that points the wrong way.
- Now the tilt arithmetic specifically. A weight gets at most **one vote per step**
  (the vote is the sign of the *batch* gradient, batch = 32 windows), and only if
  |g| clears the layer median — roughly half of weights vote 0 each step. Member i's
  diet is 58.75% own bucket (55% × ¼ uniform + 45% tilt) vs 13.75% for any other
  bucket. That 45-point exposure gap does **not** translate into 45-point vote drift:
  the batch gradient averages the tilt windows against the uniform majority, its sign
  per weight is majority-dominated, and the median gate then deletes the small-but-
  consistent specialty components outright — a specialty direction that is real but
  modest is below-median in most layers and receives literally zero votes, forever.
  Sign-voting is the worst aggregator imaginable for minority specialties: it throws
  away exactly the magnitude information that would let a strongly-needed rare
  feature outvote generalist indifference.
- Generous bound: suppose a purely specialty-driven weight's gated votes go its way
  with net drift 0.17/step (tilt differential ~0.34 × gate pass ~0.5). Reaching 32
  net votes takes **~190 steps — 3.4× the entire 56-step round 1** — for *one* flip,
  on the weights most favourable to the story. Typical specialty weights are nowhere
  near that bound. Round 1 therefore produces four members whose *served* ternary
  weights differ from shared init by ~1% generalist churn, with the tilt's fingerprint
  sitting in counters that get thrown away.
- What *does* move every step is the AdamW-trained share (embeddings, norms, scales).
  At dim 512 the embedding is 2.1M of 11.7M params, and it will absorb most of
  whatever tilt effect exists. If a tilted pair ever shows a per-bucket difference,
  the first hypothesis to exclude is "it's all in the token embedding" — i.e. the
  BitNet weights, the thing this lab exists to study, contributed nothing.

**Consequence:** the system read will be an ensemble of four near-copies of one init.
Any gain it shows is init/seed averaging and embedding drift, wearing the overlap
program's name. See §8 for why the yardstick cannot catch this substitution.

## 2. Round 2 is homeopathic, and the probing costs more than round 2 delivers

- Round 2 is 25% of round-1 tokens = **14 steps** at ladder budget. At 0.00021
  flip share that is ≤ ~28k flip events ≈ **0.3% of weights** — and those flips must
  simultaneously (a) encode three other members' failure profiles, (b) preserve the
  member's tilt, and (c) not wreck the general distribution. Fourteen steps cannot
  carry that freight. Whatever round 2 changes in the loss, it will do so mostly
  through the AdamW parts and through *recency*: the last steps' votes are the ones
  that complete flips, so the final artifact disproportionately reflects the weirdest
  diet it ever saw (see §10).
- The probe that feeds round 2 is not cheap. The training pool is ~23,100 windows
  (5.92M pieces / 256). Scoring all of them with 4 members is ~2,900 batch-32 forward
  passes — on the order of **50× round 2's step count** in forward passes. The
  program spends more compute *diagnosing* weaknesses than *treating* them, at a
  scale where treatment is already below the noise floor.
- If the answer is "then use a bigger token budget," price it honestly: a 10M step
  is ~12.9 s of wall clock on this VM (723 s / 56 steps). The ~190 steps needed for
  specialty weights to flip *once* is ~41 min/member for round 1 alone; a budget
  where tilts are actually expressed (multiple flips per specialty weight) is hours
  per member, one heavy job at a time, × 4 members × 3 seeds × all baselines in §8.
  The design's budget line ("same token budget") never states the number, and every
  plausible number is either too small for the mechanism or too big for the machine.

## 3. The buckets do not exist in this corpus

The design's first move — "corpus bucketed into 4 specialties" — assumes a corpus
with four specialties in it. `DATA-AUDIT.md` measured what is actually there:

- **73.9% of v1's source bytes are venv / HuggingFace-cache junk**: license texts,
  package metadata, and the Qwen `merges.txt` BPE tables (~42% of source bytes,
  token-fragment gibberish). **23% of all pieces sit in nine numeric mega-lines**
  (scipy test matrices, up to 154k pieces each). The only clean categories in v2
  are German sentences (45.7%), Muse-side HiveMIND docs (28.8%), Fable-side
  HiveMIND docs (13.1%), and lab notes (12.4%). Bucket by provenance and the four
  "specialties" are: a language, two near-identical dialects of the same project's
  paperwork (Muse-side vs Fable-side docs — tilting between them is tilting between
  near-duplicates), and lab notes. Bucket by anything else and you are clustering
  boilerplate.
- **Windows are collages.** Training windows are 256 pieces at random offsets over
  one flat stream whose median line is 9 pieces (v1). A window spans ~15–28 lines
  of mixed provenance; it has no bucket. To train on "45% bucket" you must build a
  bucket sampler that assembles bucket-pure windows — which changes the window
  distribution itself. The held set is collage windows from the flat stream. So
  tilted and specialist members are trained on a different *kind of object* than
  they are judged on. That mismatch alone can manufacture or erase a few hundredths
  of loss — the entire size of the effects this lab hunts (the RoPE win was 0.041).
  No result from this design can be read until the sampler confound is separated,
  and the design doesn't separate it.
- **Oversampling a bucket = memorizing it.** Unique real text totals ~0.91M pieces,
  so a bucket holds on average ~227k unique pieces, and the smallest natural bucket
  (lab notes) ~113k. At ladder budget, member i consumes 58.75% × 458,752 ≈ 270k
  own-bucket tokens — **>2 epochs over the smallest bucket's entire unique supply**,
  while its uniform content is at <0.1 epoch. The "tilt" for small buckets is not a
  preference, it is a repetition regime, applied to a 9.44M-weight model with
  ~0.04 tokens/param overall. What looks like specialty strength on the member's
  own bucket will be memorization until proven otherwise — and the probe in §5 is
  built in a way that cannot tell the difference.

## 4. The failure pool is a noise pool — and a leakage pump

"Weakness exchange" assumes worst-decile loss = learnable weakness. On *this*
corpus, worst-decile loss is where the garbage lives:

- After round 1, the highest-loss training windows will be dominated by the
  irreducibly high-entropy content the audit catalogued: scipy float streams
  (digits are near-random; the loss is entropy, not ignorance), merges-table
  gibberish, mojibake (byte-fragment tokens sit at ranks 4–8 of the vocabulary),
  and one-off weird lines. A member cannot fix these by training on them; it can
  only memorize or distort itself trying. This is the classic boosting pathology:
  AdaBoost-style reweighting toward hardest examples degrades fastest exactly when
  the hard tail is label noise, and here the hard tail is *literally* noise by
  construction of the corpus.
- The members' failure sets will also be heavily **correlated**: same init family,
  same recipe, 55% identical diet, ~1% of weights moved (§1). The union pool billed
  as "the *others'* failures" is mostly *everyone's shared* failures — the common
  garbage — so the exchange largely reduces to "everyone trains more on the
  corpus's worst windows," a solo hard-example-mining run with extra steps and a
  better story.
- Worst of all: **the pool is drawn from the training stream of a corpus with 48%
  redundant lines and 30.8% duplicate pieces** (audit §4). Held content routinely
  appears inside training windows. Round 2 deliberately selects unusual,
  high-loss training windows and trains every member on them again — if any of
  those windows have duplicate copies inside the 128 held windows, round 2 is a
  direct leakage pump into the yardstick, and the "win" will be partly or wholly
  memorized held content. The design specifies no dedup guard between the failure
  pool and the held set. On this corpus that guard is not optional.

## 5. The probe measures exposure, not weakness

Failures are probed **on training-pool windows** — windows every member already
trained on. Loss there conflates three things the design needs kept apart:
aptitude, exposure count, and memorization. Member i saw its own bucket at 4.3×
the rate of other buckets (58.75% vs 13.75%), so its per-bucket training losses
are ordered by diet before any question of skill arises. The failure pool will
therefore over-select (a) intrinsically high-entropy buckets regardless of member,
and (b) each member's least-seen content — meaning "weakness exchange" degenerates
into exposure rebalancing, something uniform training already does for free.
A weakness probe that means anything must run on *unseen* windows per bucket —
but the design (correctly) refuses to touch the 128 held windows, and the corpus
has no spare clean held material: the unique supply is 0.91M pieces total.
The probe as specified cannot measure the quantity the mechanism is named after.

## 6. The exchange destroys the only asset the system has: diversity

Ensemble gains come from *decorrelated* errors. This design maximizes correlation
at every joint, then spends its one diversity-generating step undoing it:

- Shared: shape, recipe, init distribution (and, under this lab's convention that
  same seed ⇒ same init *and* same batch stream, possibly the literal init),
  55% of the diet drawn from one distribution, and in round 2 a **single shared
  failure pool** fed to all four members.
- Round 1's tilt is the sole decorrelator — and §1 shows it writes ~nothing into
  the served weights. Round 2 then explicitly optimizes all members toward the
  *same* windows. Pairwise distance between members is highest before the exchange
  and is spent down by it. The mechanism's second half works against its first
  half, on purpose, by design.
- A correlated 4-model ensemble is a single model with averaged noise, at **4×
  serving compute per token** (the mean-distribution read runs all four members
  for every token). The yardstick counts bytes and ignores FLOPs — for a BitNet
  program whose entire selling point is cheap compute, the system read quietly
  spends the savings and the scorecard doesn't notice.

## 7. Nothing is actually "exchanged" — there is no transfer object

Training member i on a window where member j failed does not transfer j's
weakness into i. The gradient i computes on that window is i's own, in i's own
basin. If i already handles that window class, the gradient is small and nothing
happens; if i fails there too, it's a shared hard example (§4). What crosses
between members is a *data-selection decision* — hard-example mining with the
mining outsourced to siblings. That may or may not be a good curriculum, but it
is not a new mechanism, and it has an obvious solo control the design omits:
**one generalist, same total tokens, round 2 on its OWN worst-decile windows.**
If solo self-mining matches the exchange — and §4–§5 predict it will, because the
pools mostly coincide — the entire multi-member apparatus is theatre around a
reweighting trick. The design cannot distinguish its headline idea from its
trivial ablation.

## 8. The yardstick cannot attribute a win — the missing controls are the story

Even if the system posts a better number, the design as specified cannot say why:

1. **No untilted-ensemble control.** The decisive baseline — 4 members, identical
   in every way except tilt = uniform and no exchange (or exchange on a *random*
   pool), same ensemble/router read — is absent. Seed-to-seed held sd at the
   champion rung is 0.0161 with a ~0.029 spread; averaging four predictive
   distributions routinely buys gains of that order. Yardstick (a) is *one* model
   and (b) is specialists: neither isolates tilt, neither isolates exchange.
   The minimum honest design is a 2×2 (tilt × exchange) plus a random-pool
   exchange arm plus the §7 solo-mining arm. None are in the draft.
2. **Baseline token budgets are undefined, and every reading rigs the race.**
   "Equal total serving bytes" fixes (a)'s size (~37.7M ternary weights — a shape
   that doesn't exist yet; the 50M rung needs gradient checkpointing and ~85 min
   a run on this VM) but not its tokens. If (a) gets one member's budget, the
   system wins on 5× the compute. If (a) gets the system's total, (a) gets ~229
   steps where the ladder shows step count is the dominant variable at this
   scale. Pick either; the conclusion is baked in before a run starts.
3. **"Serving bytes" is undefined to within 4×.** This lab's recorded byte figure
   for a layered member is mechanism state — 2 counters + states at 2.5 B/weight
   (23.6 MB/member, ~94 MB for the system). Packed served levels are ~0.625
   B/weight. Which accounting (a) must match changes its size by 4×. The router's
   parameters, training data, and bytes are counted nowhere.
4. **Baseline (b) is a strawman with an undefined read.** Bucket-only specialists
   train on ~25% of a corpus whose smallest bucket is ~113k unique pieces — a
   memorization exhibit — and are then judged on composite loss. And how is (b)
   itself read as a system: single member? ensemble? routed (with what router —
   an oracle bucket label the tilted system doesn't get)? The comparison that
   could actually embarrass the design — routed specialists vs routed tilted
   generalists *per bucket* — is left unspecified at exactly the joint where it
   matters.
5. **Two system reads = two lottery tickets.** Reporting both the ensemble and
   the router and (inevitably) leading with whichever wins is an uncorrected
   multiple comparison on top of everything else, in a lab whose history
   (plain_half vs layered_half, seed-by-seed sign flips on a 0.002 gap) shows how
   easily noise dresses as signal here.

## 9. The statistics are blind at bucket level, and the budget buys one seed

- Worst-bucket held loss is computed on ~**32 windows** (128 / 4) — and the held
  windows are collages without true bucket labels (§3), so "per-bucket held" first
  requires assigning buckets to mixed windows, another unforced source of noise.
  Full-set seed sd is already 0.007–0.032 across this lab's arms; per-bucket
  estimates on 32 correlated windows will carry roughly double that, and taking
  the *worst* of 4 buckets × several systems stacks a winner's-curse bias on top.
  The effects being hunted are 0.02–0.04. The yardstick's bucket half cannot
  resolve them.
- Programme cost at the 10M rung: 4 members × (round 1 + probe + round 2) +
  the (a) giant + 4 specialists + the §8 controls the draft forgot ≈ 13+ big runs
  ≈ **6–10 hours of exclusive VM**, which in practice means **one seed**.
  The lab's own adoption bar — beat by >2 sd *and* >0.01 across 3 seeds — cannot
  even be evaluated with one seed. As budgeted, the program is guaranteed to end
  in an anecdote, whichever way the number lands.
- Precedent check: this is the third time a plausible mechanism has arrived with
  a story about indirect signal. JEPA's signal reached its trunk through 64
  masked positions and produced representations *indistinguishable from the
  untrained init* (probe 3.2428 vs floor 3.2445). Carry and cooldown lost by
  +0.018 and +0.113. The exchange's signal path — *another model's loss ranking,
  on garbage-heavy windows, delivered in 14 steps* — is more indirect than any
  of those.

## 10. Dynamics: oscillation you can't see, forgetting you can't afford, knobs you can't audit

- With one exchange round you cannot observe oscillation — but the dynamic is
  loaded: failures are defined against round-1 models, round 2 shifts every
  member, and the new failure surface is never re-probed or repaired (no round 3
  is budgeted). You ship the state *after* the perturbation, mid-swing.
- Round 2's mix ratio (tilt : failures) is **not specified**, nor is the
  "weighted toward its own specialty" function. These are the two knobs that
  decide whether round 2 is a nudge or a distribution takeover — and as free,
  post-hoc-adjustable parameters they make any outcome explainable and any win
  unreplicable. Combined with unspecified seeds, bucketing method, absolute
  round-1 budget, router training data, and byte accounting (§8.3), the draft
  has enough slack to manufacture a positive result from noise alone. That is
  not an accusation; it is what under-specification *does*, and this lab has
  already retracted one headline (layered-beats-gradient) that died exactly
  this way when its missing control was finally run.

---

## The single strongest objection

**At the chosen scale, the served members cannot become different models.** The
tilt lives in vote counters that are discarded at serving; at the 10M rung only
~1.18% of weights flip in an entire round 1 (flip share 0.00021/step × 56 steps),
the post-training state histogram is the init histogram, and a specialty-driven
weight needs on the order of 190 tilted steps to earn a *single* flip — 3.4× the
whole budget. The four "large overlapping tilted generalists" that reach the
system read are four near-identical copies of one init with ~1% generalist churn.
There is no specialty in the artifact, no diversity for the ensemble to exploit,
and no weakness profile that is any member's own — so any system win the
yardstick reports is necessarily produced by something else (seed averaging,
embedding drift, sampler mismatch, or held-set leakage via the failure pool)
while being credited to overlap and exchange. The mechanism does not fail at the
margin; at this rung and budget, it does not occur.

## The cheapest experiment that answers it

**A divergence test at the 2M rung — before any 10M run exists.** The ladder
config (dim 288 × 2 layers, 56 steps) already runs in ~5 min. Train three models,
same seed, same init:

1. uniform diet (the existing `layered_rope_scale2m` recipe),
2. tilted diet (55/45 toward one bucket — the bucket sampler has to be built
   anyway; build it here, where mistakes are cheap),
3. uniform diet, different seed (the diversity yardstick).

Then measure, with pre-registered kill criteria:

- **Hamming distance between served ternary states**: tilted-vs-uniform (same
  seed) against uniform-vs-uniform (different seeds). If the tilt's fingerprint
  is not *clearly larger* than raw seed noise, tilt does not survive the trainer
  — kill the program, or fix the trainer (lower V, longer budget, smaller rung)
  before scaling anything.
- **Per-bucket held delta**: the tilted member must beat the uniform member on
  its own bucket by >0.02 (the lab's JEPA margin bar) on unseen windows. If not,
  there is no specialty to exchange weaknesses about.

Total cost: 2 new short runs + a distance script — under an hour, against
6–10 hours for the full program. Add one design change regardless of outcome:
**no overlap result gets reported without the untilted 4-member ensemble and the
solo self-mining arm beside it** (§7, §8.1). If the tilt survives the divergence
test, those controls are what would let a win mean something. If it doesn't —
the expected outcome, on this lab's own flip numbers — the program dies for the
price of a ladder run, which is what a red team is for.
