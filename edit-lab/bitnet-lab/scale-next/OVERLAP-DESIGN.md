# OVERLAP-DESIGN.md — Large Overlapping BitNet Generalists (Muse's work, Muse's side)

## 1. The idea, in Arnav's words (2026-11-10 14:39 PT)

> "BitNets can be huge and take less space, so we don't need specific specialists anymore. We need huge overlapping generalists specializing in something, working as one — each member in the hive targets the others' weaknesses and is good at that, while being a generalist to a small extent."

Addendum (14:40 PT): the data problem this creates is to be fixed "by simply the same dreaming method."

**What would prove it:** a system of tilted, mutually-patched generalists beats — at equal total serving bytes — both one plain generalist and a set of narrow specialists, on text none of them trained on.
**What would kill it:** the tilt never shows up in the served weights, the patching loop does no better than a placebo, or the win is fully explained by ordinary ensemble averaging.

This design was red-teamed before being written down (REDTEAM-MECHANISM.md, REDTEAM-MEASUREMENT.md in this folder). Two of their objections were strong enough to restructure the program; both are built in below as Gate 0 and the byte rule, not footnotes.

## 2. The two hard facts the design must respect

**Fact 1 — tilt lives in counters that are thrown away.** The served model is the ternary states `t1+t2`. Tilt and weakness-training act on vote counters, which do not ship. Measured flip share per step falls with size (runs.jsonl): ~0.0012 at 0.885M weights, ~0.00055 at 2M, **0.00021 at 10M**. A whole 56-step round at 10M produces ~1.2% cumulative flip events per weight, and a specialty-driven weight needs on the order of 190 tilted steps to accumulate the 32 net votes for a single flip. At ladder budgets, four "tilted" members would reach the ensemble read as four near-copies of one init — no specialty in the artifact, no diversity to exploit, and "large members" selects *against* the mechanism. **Consequence: no overlap run happens until a divergence test proves tilt registers in served states at a stated dose (Gate 0), and round budgets are set in flips, not steps.**

**Fact 2 — "equal bytes" was rigged by default.** At the member shape, most serving bytes are not ternary: a dim 512×3 member is 11,356,160 B served, of which 79.2% is FP parameters (token embedding alone ~65%). Counting ternary only hides a 2.91× budget; sharing embeddings hides 1.95×; FP16 embeddings hide another ~33% — every miscount biases toward the multi-member system, and a hidden 2-3× budget is by itself enough to manufacture the 0.01–0.02 win this program exists to detect. **Consequence: the byte rule in §6 is frozen before any training.**

Supporting measurements: NUMBERS.md (sizes, budgets), BUCKETS.md (what "specialty" can even mean on this corpus).

## 3. Gate 0 — the divergence test (fires first, ~15–25 min at the 2M shape)

Question: does a data tilt move the *served* ternary states more than seed noise does, and at what dose?

- Shape: 2M rung (dim 288 × 2 layers), recipe layered + rotary + votes, corpus and buckets per §4.
- Arms (same init seed unless stated): **U** uniform diet; **T** tilted diet (55% uniform + 45% own bucket); **U′** uniform diet, different seed (noise floor).
- Doses: 56 steps and 168 steps.
- Measurements: Hamming distance between served states (t1+t2) for pairs (U,T) vs (U,U′); tilted member's held loss on its own bucket's unseen windows vs its uniform twin's.
- **Pass (pre-registered):** at some dose, dist(U,T) ≥ 2× dist(U,U′) **and** T beats U on T's own bucket by > 0.02 held loss. The passing dose sets the program's round budgets (converted to a flip target: rounds run until cumulative flip events reach the share Gate 0 shows is needed, with a step cap).
- **Fail at both doses:** the overlap program stops here. The result — tilt does not register in the artifact at lab budgets — is reported as the finding, with the named follow-up branches (lower vote threshold V during tilt phases; smaller members; longer doses) each treated as a *new* Gate 0, not a quiet tweak.

## 4. Corpus and buckets

- Program corpus: **corpus-v2** (real text; v1 is 79.1% merge-table gibberish + numeric dumps by content). All arms — tilted, controls, baselines — train on the same corpus universe, so results are internally comparable. They are **not** comparable to ladder numbers (v1); nobody quotes them side by side.
- Buckets: content-only deterministic rule (v1 version exists and is validated: `bucket_probe.py`'s `bucket_of(ids)`; the v2 bucketing swaps in behind the same interface before the full run). On v1 the only real-text contrast is **german vs prose**; the skeleton (§9) therefore runs a 2-tilt configuration on v1, and numeric/gibberish tilts, if run at all, are labelled controls, not specialties.
- Held hygiene: the every-40th rule, exactly as `train.py`. Per-bucket judged slices use **all 578 held candidates**, not just the standard 128 (on the 128, prose gets 18 windows and german 9 — unmeasurable; on 578: prose 78, german 40). Buckets with < 40 candidate windows are excluded from per-bucket claims. The composite primary metric still uses the standard fixed 128.

## 5. Members, tilt, and the exchange loop

- **Member shape:** the ladder's per-byte winning rung (planning numbers assume the 10M shape, dim 512 × 3, per NUMBERS.md), recipe **layered + rotary + plain votes** — the lab's champion stack, unchanged. The full run's shape is set by the ladder verdict + CONFIRM-PLAN, not by this document.
- **Tilt:** data mixture only — 55% uniform corpus + 45% own-bucket oversample (≈58.75% own-bucket exposure counting the uniform share). No architectural tilt, no specialty heads: the claim under test is that data tilt alone creates a tilted generalist.
- **Weakness, defined so it is learnable:** window *w* is a weakness of member *i* if the **best other member's** loss on *w* is at least a pre-registered margin (planning value 0.5) below *i*'s loss on *w*. Windows where *all* members are bad are excluded — on this corpus the worst-decile-by-absolute-loss pool is scipy float streams, merges gibberish and mojibake: irreducible entropy, not weakness. Training on it is the known boosting-on-noise failure, and it is also a leakage pump (48% duplicate lines means selected training windows can be near-copies of held windows).
- **Exchange round:** each member trains on its tilt mix **plus** its relative-weakness set (windows the others demonstrably *can* do), drawn from training-pool windows only, capped per bucket, after a near-duplicate guard: any candidate window sharing an exact 64-token shingle with any held-candidate window is dropped. Round size is set by the Gate-0 flip target, not by a token fraction (the draft's "25% of round 1" was ~0.3% of weights flipped at 10M — homeopathic). Probing cost is capped by subsampling the probe pool (≤ 2,048 windows per bucket).
- **Dreaming (Arnav's addendum), as a gated option:** only if the exchange round beats its placebo (§6) does a round 3 run, in which weakness windows seed member-generated continuations as extra training data for the members weak on that bucket. Dream data is tagged in every record, never enters held slices, and its arm is reported separately.

## 6. Arms, controls, and the byte rule

Arms (all same recipe, same token budget per member, seeds recorded):

1. **TILT-X** — tilted members + exchange round. The claim.
2. **UNTILT-ENS** — 4 untilted members, different seeds, uniform diet, **placebo exchange** (random training-pool windows, same count). The control that separates overlap/tilt/exchange from free ensemble averaging. *No result is reported without this arm beside it.*
3. **TILT-NOX** — tilted members, no exchange. Isolates the exchange.
4. **SELF-MINE** — one member, exchange round on its *own* relative weaknesses (vs a held-out twin). Isolates "others' failures" from ordinary hard-example mining.
5. **GENERALIST** — one plain model at equal total serving bytes (planning match for 4×10M members: dim 896 × 12 layers, 45,065,216 B vs the system's 45,424,640 B, −0.79%; NUMBERS.md).
6. **NARROW** — 4 members, each trained *only* on its bucket, read with the same system reads as TILT-X.

**Byte rule (frozen, from REDTEAM-MEASUREMENT):** serving bytes = the **measured serialized size** of the served artifact (router included if used), counting everything — embeddings, position tables, scales, norms, biases. Layered positions count as two physical ternary components in all estimates. One precision for all arms; any sharing (e.g., a shared embedding variant) is a separately-labelled sensitivity, applied symmetrically, never the headline. Before the first training run of any phase, a manifest (per-tensor shapes/dtypes/bytes + hash) for every arm is written to this folder; arm budgets must match within ±1%. FLOPs/token and training tokens are reported next to every result, so a compute-bought win is visible.

**System reads:** primary = averaged next-token distribution (labelled 4× inference compute). Secondary = router that peeks at a window's first 32 tokens and is **scored only on tokens 33–256** (the peeked prefix is excluded from its score; baselines are scored on the same positions for that comparison). Best-member oracle is an upper bound only, never a headline.

## 7. Yardstick (pre-registered)

- **Primary metric (single):** composite held loss on the standard fixed 128 held windows, averaged-distribution read, ≥ 3 seeds (at smoke size; see §8).
- **Secondaries:** per-bucket held loss on the 578-candidate slices (buckets with ≥ 40 windows only); worst-bucket loss among those.
- **Win condition:** TILT-X beats GENERALIST **and** NARROW on the primary by > 0.02 **and** > 2 sd across seeds, **and** beats UNTILT-ENS on the primary by the same bar (otherwise the win is ensemble averaging, not overlap). Generalist-retention check: each tilted member's solo composite within 0.05 of an UNTILT-ENS member's — a "tilted generalist" that stopped being a generalist fails Arnav's definition even if the system wins.
- Reference noise scale: the champion recipe's seed sd on held loss is ~0.016 (RESULTS-ROPE), so a 0.02 margin is ~1.2 seed-sd at n=1 — which is why the bar is defined on the *mean across ≥ 3 seeds*, with the sd of the difference reported.

## 8. Budgets (NUMBERS.md; re-cut after Gate 0 sets the dose)

- Smoke (2M shape, all arms, 70 steps/run, 1 seed): **≈ 2.0–2.6 h**; at 3 seeds ≈ 5–7 h of VM. The generalist arm needs `--ckpt` and is the single longest run.
- Full (winning shape, 3 seeds): planning figure **≈ 15.7–21.1 h**, staged per seed with the generalist runs chunked — never one block. If Gate 0's passing dose is 168 steps rather than 56, member-arm costs roughly triple and the full program is re-budgeted before it is approved to fire.
- These are exclusive-VM hours on a shared box; the program queues behind the ladder, confirmations, and growth cycles like everything else in the lab.

## 9. Kill criteria (any one stops the program; the finding is reported, not buried)

1. Gate 0 fails at 56 and 168 steps → tilt does not register in the artifact; stop.
2. TILT-X ≤ UNTILT-ENS on the primary at smoke (3 seeds) → the effect is ensemble averaging; the overlap claim is dead at this scale.
3. Exchange ≤ placebo exchange (TILT-X vs TILT-NOX within noise, or UNTILT-ENS's placebo matching TILT-X) → the exchange loop is dead; report tilt-only result if it survives.
4. TILT-X fails the primary win vs GENERALIST or vs NARROW → no full run.
5. Composite worsens across two consecutive exchange rounds (oscillation) → exchange stops; rounds do not chase moving targets.
6. NARROW wins worst-bucket **and** composite → at this scale, disjoint specialists beat overlapping generalists; Arnav's premise fails here and that is the headline.

## 10. What the red-teams changed (summary)

- Mechanism red-team's strongest objection (tilt can't survive in the artifact at ladder budgets) became **Gate 0** and flip-denominated round budgets.
- Measurement red-team's strongest objection (bytes rigged by accounting) became the **serialized-artifact byte rule + pre-training manifests**.
- Absolute-loss failure pool → **relative, learnable weakness** + near-duplicate guard + placebo control.
- Router peek leakage → prefix-excluded scoring. Per-bucket noise → 578-candidate slices and a single pre-registered primary.
- Missing attribution controls → UNTILT-ENS and SELF-MINE are mandatory, not optional.

Full attacks: REDTEAM-MECHANISM.md, REDTEAM-MEASUREMENT.md. Sizes/budgets: NUMBERS.md. Buckets: BUCKETS.md.

## 11. Firing order (the moment the ladder verdict lands)

1. **Gate 0** (this design, §3) and the **CONFIRM-PLAN 280-step set** — both are verdict-independent and cheap relative to everything downstream; queue order between them is by lab availability.
2. CONFIRM-PLAN 448-step set (settles member size + token dose).
3. **Smoke** via `run_overlap.py --launch` (2M shape, all arms, 3 seeds) — only if Gate 0 passed.
4. **Full run** at the confirmed shape — only if the smoke meets the §7 win condition.
