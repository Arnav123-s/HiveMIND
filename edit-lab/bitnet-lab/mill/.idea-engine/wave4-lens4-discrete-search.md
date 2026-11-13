# Muse's work — Muse's side

# Wave 4 · Lens 4 — DISCRETE SEARCH: post-training search over ternary states (Muse's work, Muse's side)

> **Territory.** Training has stopped. The champion's discrete state — `t1/t2` on the
> layered_half + rotary chassis, held **2.8580 ± 0.0161** — is the starting point, and this
> lens *searches* that state: local search, tabu lists, population and greedy coordinate
> methods that move component weights through {-1, 0, +1} (installed levels -2..+2),
> guided only by a **legal signal** — dev/calibration windows with block index % 40 ≠ 0.
> The held set is read **exactly once**, at the very end, on the final shipped state.
> This is search, not calibration: wave G's readout lens (G-025..G-036) fitted 8 continuous
> scalars and never moved a weight. Every entry here moves weights, and every entry states
> its budget in eval passes and its overfitting guard.
>
> **Code grounding (train.py, read before drafting).** `Layered.install()` writes, per
> BitLinear layer, `m.weight = s · (exp(log_scale) / mean|s|)` with `s = t1 + t2`. Two
> consequences bind every entry: (1) flipping one component changes `mean|s|` for its
> **whole layer**, so no flip's effect is local — every tentative state must be
> re-`install()`ed and re-scored, never delta-estimated from the flipped weight alone;
> (2) the search surface is 8 BitLinear layers (qkv/out/up/down × 2 blocks), 884,736
> installed positions, 1,769,472 component slots. `held_loss()` sets `EASE[0] = 1.0`,
> runs `model.eval()`, and cross-entropies `Tiny.next_piece` over the 128 windows from
> `held_windows()` (block starts `w·CTX`, `w % 40 == 0`). `offsets()` already defines
> legality for training: `(i // CTX) % 40 != 0 and ((i + CTX) // CTX) % 40 != 0`.
> The final counters `c1/c2` (int8, clamped ±32, reset only on a flip) are used below
> **only as a proposal distribution** — a prior over which weights to try flipping —
> never as an acceptance rule. Acceptance is always measured calibration loss.
>
> **Shared protocol (applies to every entry).**
> - **Start state:** one champion run's dumped final state (`--dump-state`: `t1/t2/c1/c2/
>   log_scale` + FP params, the shared plumbing the G/H waves already assume). All FP
>   parts and all `log_scale`s are **frozen** for the whole search; only `t1/t2` move.
>   A "flip" = one component stepped ±1, clamped to {-1, 0, +1}; boundary no-ops
>   (the clamp would not move the component — WH-051's frustrated population) are
>   never proposed and never counted.
> - **Calibration sets (block-aligned, so windows tile and cannot overlap):**
>   CAL-A (search set) = 256 windows at block starts `w·CTX`, `w % 40 == 13`, picked
>   evenly as `held_windows()` picks; CAL-B (confirmation set) = 128 windows at
>   `w % 40 == 27`. CAL-A, CAL-B and held (residue 0) are pairwise disjoint by
>   construction. Search decisions see CAL-A only (or rotating subsets of it).
> - **Eval pass (EP):** 1 EP = one CE evaluation over 128 windows, the cost of one
>   `held_loss()` call. A 32-window micro-eval = 0.25 EP; a full CAL-A read = 2 EP;
>   CAL-B = 1 EP. Budgets below count CAL-A + CAL-B passes; the single final held
>   read is common to all entries and excluded.
> - **Ship rule (the overfitting gate every entry inherits, tightened per entry):**
>   after search, read CAL-B **once**. Ship the searched state only if it beats the
>   champion state's CAL-B by ≥ 0.01 **and** keeps ≥ 50% of its CAL-A gain; otherwise
>   ship the champion state unchanged. Then read held exactly once, on what shipped.
> - **Per-seed discipline:** at trial, the identical search (same budget, caps, seeds
>   for its internal RNG drawn from `10_000 + seed`) runs independently on each
>   champion seed's weights; the verdict is the 3-seed mean vs 2.8580, PROMOTE bars
>   unchanged. A search that wins on one seed's weights only is a selection artefact.
>
> **Deduped against** `mill/IDEA-POOL.md`, CANDIDATES-A/B/C/D/E/F/G/H (esp. G-025..G-036
> and WH-049..WH-060) and FABLE-CANDIDATES.md. Deliberately NOT re-proposed:
> G-035 (sequential *single* flips, top-200 by |counter|, each individually verified —
> every entry here evaluates **joint batch / pair / population moves**, uses tabu or
> acceptance machinery G-035 does not have, or both); G-026/G-030 (bulk threshold /
> soft readout of the counter field — no measured acceptance, no iteration);
> MILL-223/224 (Metropolis flips *during* training, acceptance from a gradient-estimated
> ΔL, trainer replacement — DS-004 is post-training with *measured* CE deltas);
> MILL-228..230 (Fisher-ranked flips *during* training, training continues around them);
> MILL-231 (verifying pending flips early, inside training); A-024 (ε-greedy random
> flips during training — DS-012 is a post-training black-box *control*); MILL-218 /
> G-027 / G-029 / G-032 (modal / ensemble / average / gated readouts — DS-003 uses the
> same checkpoint saves as *population members for discrete recombination* and ships
> one searched state, never an average or an ensemble).

---

### DS-001 ★ · Tabu batch local search, counter-proposed
- **source:** discrete-search lens; proposal prior from WH-052 (counters predict future flips, FFN AUC 0.72–0.82) and WH-051 (frustrated/boundary population must be excluded from proposals); acceptance machinery from tabu search (Glover) — no pooled entry has memory of where it has already searched.
- **mechanism:** 40 rounds. Each round: build the proposal pool = top 512 unflipped-this-search component slots ranked by proposal score `|c| · (1 + 0.5·[layer is up/down])` (WH-052's FFN weighting), boundary no-ops and tabu slots excluded. Partition the pool's top 192 into 8 disjoint batches of 24 flips (each flip in the counter's sign direction). Score each batch by applying it, `install()`, and micro-evaluating on a rotating 32-window CAL-A slice (slices cycle, so no slice is optimised twice in a row). Accept the best batch **if its micro-Δ < +0.005** (near-neutral batches are accepted — that is the tabu point: walk through flat ground instead of stopping); all 24 flipped slots enter the tabu list for 5 rounds. **Aspiration:** a tabu batch is allowed if its micro-Δ beats the best full-CAL-A score seen so far. Every 5 rounds, score the incumbent on full CAL-A (2 EP) and snapshot it if it is the best full-CAL-A state yet; the search's output is the best snapshot, never the last state.
- **exact change:** new eval-side runner `mill/search.py --search tabu` (loads `--dump-state`, freezes FP/`log_scale`, owns the tabu list + snapshot ring; scoring is the `held_loss()` body pointed at CAL windows). No train.py change.
- **budget:** 40 rounds × 8 batches × 0.25 EP = 80 EP micro + 8 full-CAL-A snapshots × 2 EP = 16 EP + CAL-B 1 EP = **97 EP**.
- **prediction:** −0.03..−0.07 vs 2.8580. Batch evaluation prices flip *interactions* (including the per-layer `mean|s|` renormalisation) that single-flip verification cannot see, tabu memory stops the search re-litigating the same contested weights, and the counter prior concentrates proposals where post-training evidence already points. The champion was trained ~160 steps; its state is a vote equilibrium, not a loss optimum — a measured local search is the first procedure that optimises the actual objective over the actual discrete space.
- **overfitting guard:** CAL-A 256 windows; rotating micro-slices (a batch is never accepted on the same slice twice); hard cap **2,000 accepted component flips** (0.23% of positions); ship rule as protocol (CAL-B ≥ 0.01 and ≥ 50% transfer) — a CAL-A-memorising search fails CAL-B and ships the champion.
- **status:** queued
```mill
id: DS-001
mode: process
run: --arm layered_half --rope --dump-state --search tabu
```

### DS-002 ★ · Layer-sweep greedy coordinate descent (one BitLinear layer at a time)
- **source:** discrete-search lens; block-coordinate descent applied at the granularity `install()` itself defines — the per-layer `mean|s|` renormalisation means a flip's side effects are contained in exactly one layer's scale, so layer-isolated moves have the cleanest measurable deltas in the whole search space. Layer order follows WH-052's validity gradient (FFN layers' counters are the strongest witnesses, attention's the weakest).
- **mechanism:** One sweep = the 8 layers in fixed order: block2-down, block2-up, block2-out, block2-qkv, block1-down, block1-up, block1-out, block1-qkv. Per layer: proposals = that layer's top 256 slots by |counter| (counter direction only, no-ops excluded); form 6 sequential batches of 16 flips; for each batch, apply → `install()` → micro-eval on a fixed 32-window CAL-A slice reserved for this layer; keep the batch iff micro-Δ < 0, else revert it exactly. After each layer, one 128-window CAL-A read (1 EP); if it is worse than the sweep's entry read by > 0.01, restore the layer-entry snapshot (a layer can veto itself). A second sweep runs **only if** the first gained ≥ 0.02 on full CAL-A.
- **exact change:** new runner mode `mill/search.py --search layersweep` (per-layer snapshot/restore over `t1/t2` slices; everything else as DS-001's runner).
- **budget:** per layer 6 × 0.25 EP micro + 1 EP confirm = 2.5 EP → 20 EP per sweep + CAL-B 1 EP = **21 EP** (≤ 41 EP if the second sweep triggers).
- **prediction:** −0.02..−0.05 vs 2.8580. The cheapest procedure here whose every accepted move was jointly measured in the only subspace where its renormalisation side effect lives. Expected to capture most of DS-001's single-basin gain; what it cannot do is cross-layer coordinated moves — that gap is exactly what DS-001/DS-003 are priced against.
- **overfitting guard:** CAL-A 256 windows with a per-layer reserved slice (no layer is judged on another's slice); per-layer self-veto restore; hard cap **1,200 accepted flips**; CAL-B ship rule as protocol.
- **status:** queued
```mill
id: DS-002
mode: process
run: --arm layered_half --rope --dump-state --search layersweep
```

### DS-003 ★ · Checkpoint-population recombination (discrete crossover, one shipped state)
- **source:** discrete-search lens; population methods over the run's own trajectory diversity — the last-5 checkpoint saves that MILL-218/G-027/G-029 already assume exist, used here as *genotypes* instead of things to average or ensemble. WH-060 prices the contested population (10–16% of weights, ≥ 35% of late flips) — crossover is a search move aimed exactly at weights the trajectory itself never settled.
- **mechanism:** Population 12, all derived from the **same run**: the final state, the modal-5 state (MILL-218's readout, as a genotype), the counter-resolved τ=24 state (G-026's readout, as a genotype), the other 4 checkpoint states, and 5 children built by **uniform crossover** — for each installed position, copy the `(t1, t2)` pair *jointly* from one parent chosen per position (pair-joint, so a component combination a checkpoint actually held is never split) — parents drawn from the checkpoint set, plus counter-biased mutation (each position flips one component with probability `0.002 · |c|/32`). Score all 12 on full CAL-A (2 EP each). Then 6 generations: tournament-select 2 parents (best of 3 random members), produce 8 offspring by the same crossover + mutation, score each on full CAL-A, keep the best 12 of (parents + offspring), with the original final state as a permanent elite (the population can never lose the champion). Ship the best final member.
- **exact change:** new runner mode `mill/search.py --search population` (needs the last-5 `--dump-state` saves; crossover/mutation over dumped `t1/t2`, FP frame from the final save only, stated plainly — members are *states*, read through the final FP frame, the same era choice G-027 makes implicitly).
- **budget:** 12 × 2 EP initial + 6 generations × 8 offspring × 2 EP = 24 + 96 = 120 EP + CAL-B 1 EP = **121 EP**.
- **prediction:** −0.03..−0.08 vs 2.8580 — the largest ceiling in this file. Recombination reaches states no local path from the final state reaches cheaply: a weight that was right at checkpoint 3 and flipped away by checkpoint 5 can be restored *in combination with* the rest of the final state, per position, at population scale. If per-position checkpoint disagreement is mostly noise, CAL-B vetoes it and the entry retires the trajectory-diversity hypothesis with a number.
- **overfitting guard:** CAL-A 256 windows, full-set scoring of every member (no micro-slices — population selection on slices is how populations memorise); offspring must differ from the champion state in **≤ 8,000 positions (0.9%)** or they are discarded unscored; elite preservation; CAL-B ship rule as protocol, applied to the single best member only (no CAL-B shopping across the population).
- **status:** queued
```mill
id: DS-003
mode: process
run: --arm layered_half --rope --dump-state --search population
```

### DS-004 · Measured simulated annealing (post-training, CE-accepted)
- **source:** discrete-search lens; the honest post-training form of the idea MILL-223 reached for during training — with the one ingredient MILL-223 lacked: acceptance by **measured** calibration CE, not by a gradient-estimated ΔL.
- **mechanism:** 60 rounds. Each round proposes one batch of 16 flips drawn from the counter proposal distribution (probability ∝ |c|, direction = counter sign, no-ops excluded), applies it, `install()`s, and micro-evaluates on a rotating 64-window CAL-A slice. Δ = micro-CE change vs the incumbent's score **on the same slice** (paired, so slice difficulty cancels). Accept if Δ < 0, or with probability `exp(−Δ/T)` if Δ > 0, with T annealed geometrically 0.020 → 0.002 nats over the 60 rounds (T is in *measured nats*, not gradient units — the calibration MILL-223 could not make). Every 10 rounds, full-CAL-A read (2 EP) and snapshot-if-best; output is the best snapshot, so late hot wandering cannot damage the result.
- **exact change:** new runner mode `mill/search.py --search anneal` (own RNG stream; paired-slice scoring cache so each round costs one new micro-eval, the incumbent's slice score is already known).
- **budget:** 60 × 0.5 EP micro + 6 × 2 EP snapshots = 30 + 12 = 42 EP + final snapshot confirm 2 EP + CAL-B 1 EP = **45 EP**.
- **prediction:** −0.02..−0.06 vs 2.8580, high variance across seeds by design. Annealing's claim over DS-001/DS-002 is escaping the first basin: vote training ends in a state where every *counter-aligned* single move looks flat, and only accepted-worse batches cross to a neighbouring basin. If the 3-seed spread is wide with a good mean, the mill learns the landscape is multi-basin; if it ties DS-002, the landscape is single-basin at this scale and the greedy entries own the territory.
- **overfitting guard:** CAL-A 256 windows; paired rotating slices; hard cap **960 accepted flips** (60 × 16, and rejected batches revert); best-snapshot (never last-state) output; CAL-B ship rule as protocol.
- **status:** queued
```mill
id: DS-004
mode: process
run: --arm layered_half --rope --dump-state --search anneal
```

### DS-005 · Focused search (WalkSAT-style: work only on the worst windows' disagreements)
- **source:** discrete-search lens; WalkSAT / focused local search for SAT — global greedy stalls because most constraints are already satisfied; progress comes from picking an *unsatisfied* constraint and fixing what it complains about. Transplant: an unsatisfied constraint is a high-loss calibration window; its complaint is its gradient.
- **mechanism:** 400 iterations. Maintain a rotating panel of 32 CAL-A windows with individually cached losses (panel re-scored every 20 iterations, 0.25 EP). Each iteration: take the panel's worst window, run **one backward** on it alone (cost counted below), and among that window's gradient's top-50 counter-aligned candidate slots (gradient sign agrees with a flip direction *and* the slot's counter does not oppose it), flip the single slot with the largest |gradient| — with probability 0.15 flip a random one of the 50 instead (the WalkSAT noise move, the escape hatch against cycling). No per-flip eval: the discipline is focus + the periodic full read. Every 50 iterations, full-CAL-A read (2 EP), snapshot-if-best, and any slot flipped 3 times is frozen for the rest of the search (anti-thrash, WH-058's hidden-thrash population is this entry's named enemy).
- **exact change:** new runner mode `mill/search.py --search focused` (per-window loss cache + single-window backward path reusing `Tiny.next_piece`; the only entry that computes gradients, and it never updates anything with them except the flip choice).
- **budget:** gradient cost 400 × (1 window fwd+bwd ≈ 0.016 EP) ≈ 7 EP + panel re-scores 20 × 0.25 EP = 5 EP + 8 × 2 EP full reads = 16 EP + CAL-B 1 EP = **29 EP** (stated as ≈ 29 EP; the gradient term is a compute-equivalent estimate, charged, not hidden).
- **prediction:** −0.01..−0.04 vs 2.8580. Per-flip cost is ~50× cheaper than any verified entry, so it makes 400 *targeted* moves inside a small budget; the risk is the mirror image — unverified flips chase the worst windows' idiosyncrasies. The snapshot discipline bounds the downside to the CAL-B veto.
- **overfitting guard:** CAL-A 256 windows but the panel rotates through all of them (no window is focused twice until all have been panel members); per-slot 3-flip freeze; hard cap **400 flips** (one per iteration); snapshot-if-best every 50 iterations; CAL-B ship rule as protocol — this entry is the one most likely to *need* the veto, and it is priced accordingly.
- **status:** queued
```mill
id: DS-005
mode: process
run: --arm layered_half --rope --dump-state --search focused
```

### DS-006 · Compensating-pair search (2-flip moves that preserve each row)
- **source:** discrete-search lens; 2-opt reasoning — a single-flip local optimum can hide improving *pairs*: one flip that hurts alone (+δ) and one that helps alone (−ε) with ε < δ, whose joint move improves because the pair preserves the row's total drive while rearranging it. G-035's single-flip walk is blind to this entire neighbourhood by construction.
- **mechanism:** Candidate pairs live inside one output row of one BitLinear: slot *i* flips in its counter's direction, slot *j* (same row) flips *against* the installed-sum direction so the row's sum of `s` is unchanged by the pair. Rank all such pairs by `|c_i| + |c_j|`, take the top 200. Evaluate in groups: apply 10 pairs (20 flips), `install()`, micro-eval on a 64-window CAL-A slice (0.5 EP); if the group improves, bisect it (≤ 4 further micro-evals) to isolate the contributing pairs and keep only those; if not, revert the group whole. 20 groups maximum. Output = incumbent after all kept pairs, confirmed on full CAL-A.
- **exact change:** new runner mode `mill/search.py --search pairs` (row index built from the dumped layer shapes; pair generator + group-bisect driver).
- **budget:** 20 × 0.5 EP groups = 10 EP + bisection ≤ 20 × 0.5 EP = 10 EP (capped) + 4 full-CAL-A confirms × 2 EP = 8 EP + CAL-B 1 EP = **29 EP**.
- **prediction:** −0.01..−0.03 vs 2.8580 standalone; its larger value is sequential — run *after* DS-002 on DS-002's output, it is the priced test of whether the greedy optimum was a real optimum or a single-flip artefact. Standalone-first is deliberate: if pairs win from the champion directly, pair structure exists in the vote equilibrium itself.
- **overfitting guard:** CAL-A 256 windows; pair cap 200 proposed / **≤ 80 kept pairs (160 flips)**; row-sum preservation means the level histogram and `mean|s|` denominators move only through the kept pairs' arrangement, not their totals; CAL-B ship rule as protocol.
- **status:** queued
```mill
id: DS-006
mode: process
run: --arm layered_half --rope --dump-state --search pairs
```

### DS-007 · Row best-response search (the output row as the coordinate)
- **source:** discrete-search lens; F-008's per-neuron perturbation bound read backwards — if a row's output is what the function prices, the row (not the weight, not the layer) is the natural coordinate: a row move rearranges all of one neuron's incoming ternary weights at once, in the direction that neuron's own evidence points.
- **mechanism:** Rank all 3,456 output rows (per block: qkv 576, out 192, up 768, down 192) by their total counter mass `Σ|c|` over both components; take the top 512 rows. For each row in rank order: the row move = flip every slot in the row with |c| ≥ 16 in its counter direction (typically 2–8 flips; rows with zero qualifying slots are skipped). Moves are evaluated in blocks of 8 rows: apply 8 row moves, `install()`, micro-eval on a 32-window CAL-A slice (0.25 EP); if the block improves, keep all 8 and then test dropping each row move in turn only if the block gain was < 0.002 (marginal blocks pay for attribution); if the block does not improve, revert all 8. Three passes over the 512 rows, re-ranked between passes by fresh counter mass (counters do not change during search — re-ranking is by *kept-move* history: rows whose moves were kept drop out, reverted rows return at half priority).
- **exact change:** new runner mode `mill/search.py --search rows` (row-mass ranking + block-of-8 evaluation driver in the DS-001 runner).
- **budget:** per pass 512/8 × 0.25 EP = 16 EP → 3 passes = 48 EP + marginal-block attribution ≤ 4 EP + full-CAL-A confirms 2 × 2 EP = 4 EP + CAL-B 1 EP = **57 EP** (attribution capped; overflow blocks skip attribution, stated in the log).
- **prediction:** −0.015..−0.045 vs 2.8580. Row moves are the smallest moves that can express a *feature* change (one neuron re-deciding what it detects); weight moves mostly express noise around a feature. If row search beats DS-002 per EP, the coordinate granularity lesson generalises to every future search entry.
- **overfitting guard:** CAL-A 256 windows; hard cap **2,500 accepted flips** across all passes; a row may be kept-moved at most once per pass; CAL-B ship rule as protocol.
- **status:** queued
```mill
id: DS-007
mode: process
run: --arm layered_half --rope --dump-state --search rows
```

### DS-008 · Iterated local search (greedy descent + counter-weighted kicks)
- **source:** discrete-search lens; iterated local search (Lourenço et al.) — the standard answer when greedy descent works but its basin is not trusted: descend, perturb the *result* (not the start), descend again, keep the best. Distinct from DS-004: ILS's acceptance is elitist (only near-best restarts survive) where annealing's is thermal (worse states are *lived in*, not just visited).
- **mechanism:** Descent operator = a fixed cheap greedy: DS-002's batch rule restricted to the top 2 layers by counter mass, micro-evaluated, ≈ 6 EP per descent (budgeted, not re-derived). Iteration: from the best state so far, apply a **kick** of 100 flips drawn ∝ |c| (counter-weighted, so kicks explore plausible territory, not uniform noise), run one descent, read full CAL-A (2 EP); accept the result as the new restart point iff its CAL-A ≤ best + 0.005, else restart from the best snapshot. 6 iterations. Output = best snapshot ever read on full CAL-A.
- **exact change:** new runner mode `mill/search.py --search ils` (composes DS-002's descent as a subroutine — the one entry that depends on another's code landing first; flagged as such).
- **budget:** 6 × (6 EP descent + 2 EP read) = 48 EP + CAL-B 1 EP = **49 EP**.
- **prediction:** −0.02..−0.05 vs 2.8580. Kicks of 100 counter-weighted flips are large enough to leave the greedy basin (≈ 0.01% of positions, ~10× a training step's flip volume) and small enough that one descent re-settles them; the +0.005 acceptance band is what lets it drift along a ridge instead of re-descending into the same basin six times — the failure mode the iteration count is there to reveal if it happens (log restart-point Hamming distances; six identical restarts = single-basin evidence, reported as such).
- **overfitting guard:** CAL-A 256 windows; cumulative distinct flipped positions **≤ 3,000**; best-snapshot elitism (the shipped state is always a full-CAL-A-read state, never a post-kick state); CAL-B ship rule as protocol.
- **status:** queued
```mill
id: DS-008
mode: process
run: --arm layered_half --rope --dump-state --search ils
```

### DS-009 · Large-neighbourhood search: destroy-and-repair the two most contested layers
- **source:** discrete-search lens; LNS (Shaw) aimed by WH-051 + WH-060's anatomy — frustration (boundary-pinned counters) and c1/c2 disagreement (both |c| ≥ 8, opposite signs) jointly name the layers where the installed state and its own evidence disagree most. Those layers are where a *large* move has its best prior; everywhere else the state is left exactly alone.
- **mechanism:** From the dump, compute per layer: frustrated fraction (WH-051) + contested fraction (WH-060). Take the top 2 layers. **Destroy:** in those layers only, revert every contested slot (sign(c1) ≠ sign(c2), both |c| ≥ 8) to its modal-5 checkpoint value (MILL-218's saves) — an evidence-chosen alternative state, not a random reset. **Repair:** run DS-001's batch rule (counter-proposed batches of 24, micro-evaluated, best-batch acceptance) restricted to the 2 destroyed layers, 20 rounds. **Restore guarantee:** if the repaired state's full-CAL-A is worse than the champion's, ship the champion — the destroy step is fully reversible from the dump, by construction.
- **exact change:** new runner mode `mill/search.py --search lns` (anatomy computation over the dump + DS-001's batch driver with a layer mask; needs modal-5 saves).
- **budget:** repair 20 rounds × 8 batches × 0.25 EP = 40 EP + 2 full-CAL-A reads × 2 EP = 4 EP + CAL-B 1 EP = **45 EP**.
- **prediction:** −0.01..−0.05 vs 2.8580, the highest variance in the file after DS-004. Concentrating the entire move budget on the two layers with a measured state/evidence conflict is either exactly right (the conflict was the loss) or exactly wrong (the conflict was load-bearing tension the loss needs) — the restore guarantee caps the cost of being wrong at the budget, and the anatomy-vs-outcome pair is a deliverable either way: it is the first test of whether WH-051/060's statistics *cause* anything.
- **overfitting guard:** CAL-A 256 windows; only 2 of 8 layers may move at all (a structural cap no scalar budget can imitate); accepted flips **≤ 5,000** including the destroy step's reverts, all inside the 2 layers; CAL-B ship rule as protocol.
- **status:** queued
```mill
id: DS-009
mode: process
run: --arm layered_half --rope --dump-state --search lns
```

### DS-010 · Beam search over flip batches (width-4, depth-10)
- **source:** discrete-search lens; beam search — the middle point between DS-001's single path and DS-003's population: several partial solutions are carried in parallel and pruned by measured score, so an early batch that looks neutral is not discarded if its *children* score well (the failure mode of pure greedy batch acceptance).
- **mechanism:** Beam = 4 states, all starting at the champion. Depth 10. Each state expands 3 children, each child = one 20-flip batch from a **different proposal family** (this is the beam's diversity mechanism, stated explicitly): (a) counter-top batch, (b) checkpoint-difference batch (positions where the modal-5 state differs from this state, flipped toward modal), (c) counter-weighted random batch. Score every child on a 64-window CAL-A slice fixed per depth (0.5 EP each; all children at a depth share the slice, so pruning compares like with like). Keep the best 4 of 12 as the next beam. Every 3 depths, re-score the whole beam on full CAL-A (2 EP each) and re-rank by that, not by slice scores. Ship the best final beam member by full CAL-A.
- **exact change:** new runner mode `mill/search.py --search beam` (multi-state driver — the runner holds 4 `t1/t2` state copies, 4 × ~0.9 MB of ternary state, negligible; FP frame shared).
- **budget:** per depth 12 × 0.5 EP = 6 EP → 10 depths = 60 EP + re-scores 3 × 4 × 2 EP = 24 EP + CAL-B 1 EP = **85 EP**.
- **prediction:** −0.02..−0.05 vs 2.8580. Beam's edge over DS-001 is keeping the modal-difference and random lineages alive alongside the counter lineage for 10 depths; its cost is the widest per-depth evaluation in the file. If the winning lineage is (a) in ≥ 8 of 10 depths, the counter prior was sufficient and DS-010 retires itself in favour of DS-001 — lineage tracking is logged for exactly that verdict.
- **overfitting guard:** CAL-A 256 windows; per-depth shared slices (no child is scored on a private slice); path cap **≤ 200 flips per member** (10 × 20) and final shipped member must differ from champion in **≤ 600 positions**; CAL-B ship rule as protocol, applied to the shipped member only.
- **status:** queued
```mill
id: DS-010
mode: process
run: --arm layered_half --rope --dump-state --search beam
```

### DS-011 · Histogram-preserving swap search (arrangement only, totals frozen)
- **source:** discrete-search lens; a controlled experiment disguised as a search — every other entry can win by *changing* the level histogram (more/fewer zeros, different ±2 mass). A swap move (one slot +1 step, another slot −1 step, same layer) preserves the layer's installed-sum histogram and its `mean|s|` denominator **exactly**, so any win is pure *arrangement*: the right weights at the levels, not more of a level. No pooled or candidate entry has ever separated those two claims.
- **mechanism:** Donors = slots whose counter argues down (c ≤ −8) at a level above the layer minimum; receivers = slots whose counter argues up (c ≥ +8) below the layer maximum; a swap pairs one donor flip with one receiver flip in the same layer. Evaluate batches of 8 swaps (16 flips) on rotating 32-window CAL-A micro-slices (0.25 EP): accept the best of 4 candidate batches per round iff its micro-Δ < 0, with a swap-tabu (a swapped pair may not be re-swapped, in either direction, for the rest of the search — swaps can otherwise undo themselves invisibly). 40 rounds. Confirm on full CAL-A every 10 rounds, snapshot-if-best.
- **exact change:** new runner mode `mill/search.py --search swaps` (donor/receiver pairing from the counter field; histogram assertion after every accepted batch — `mean|s|` per layer bit-compared before/after, a free correctness check no other entry gets).
- **budget:** 40 × 4 × 0.25 EP = 40 EP + 4 × 2 EP confirms = 8 EP + CAL-B 1 EP = **49 EP**.
- **prediction:** −0.01..−0.035 vs 2.8580 — deliberately the most conservative win prediction among the batch entries, because the histogram channel (plausibly part of any search gain) is closed to it by construction. Its verdict disciplines the whole lens: DS-001's gain minus DS-011's gain at matched flips *is* the histogram's share of post-training search value, a number the lab will otherwise never know.
- **overfitting guard:** CAL-A 256 windows; swap cap **320 swaps (640 flips)**; exact histogram preservation asserted per batch (a violated assertion voids the run, not just the batch); CAL-B ship rule as protocol.
- **status:** queued
```mill
id: DS-011
mode: process
run: --arm layered_half --rope --dump-state --search swaps
```

### DS-012 · (1+λ) black-box evolution, unguided — the guidance control
- **source:** discrete-search lens; filed as a **control**, not a hope — every other entry spends the counter field, gradients, or checkpoint structure as guidance, and none of that guidance has ever been priced against no guidance at matched eval budget. This entry is the price tag.
- **mechanism:** (1+8) evolution, 8 generations. Parent = best state so far by CAL-A (128-window subset, 1 EP per evaluation — the subset is fixed for the whole entry). Each generation: 8 offspring, each = parent + exactly 60 **uniformly random** component flips (uniform over slots, uniform direction among legal moves; no counter, no gradient, no checkpoint information anywhere in the loop). Offspring scoring on the same 128-window subset; the best offspring replaces the parent iff it scores better, else the parent survives unchanged. Ship the final parent.
- **exact change:** new runner mode `mill/search.py --search evolve-control` (the DS-003 population driver with its proposal machinery removed — sharing the driver is what makes the comparison honest).
- **budget:** 8 generations × 8 offspring × 1 EP = 64 EP + CAL-B 1 EP = **65 EP**.
- **prediction:** −0.00..−0.02 vs 2.8580, and most of that is expected to be CAL-A selection noise that the CAL-B ship rule vetoes — i.e. the honest prediction is that this entry usually ships the champion. That is its function: if DS-012 instead matches DS-001/DS-003 on held, the counter/checkpoint guidance in this whole lens earns nothing and the file should be re-read as one expensive null; if it ships the champion while they win, guidance is priced at the difference.
- **overfitting guard:** CAL-A **128 windows only** (deliberately the weakest set in the file — the control should face the *hardest* time transferring, so a transfer here cannot be attributed to a bigger calibration set); mutation distance fixed at 60 flips/offspring (no distance tuning); CAL-B ship rule as protocol, expected to fire often.
- **status:** queued
```mill
id: DS-012
mode: process
run: --arm layered_half --rope --dump-state --search evolve-control
```

---

## Lens ranking note

Ranked by expected held gain × probability of real transfer ÷ eval budget, with the
overfitting guard's strength counted in the probability term:

1. **DS-001 ★ (tabu batch, 97 EP)** — the complete procedure: interaction-aware batch
   acceptance, tabu memory, aspiration, best-snapshot output. The entry the lens
   would run first at full size.
2. **DS-003 ★ (checkpoint population, 121 EP)** — the highest ceiling and the only
   non-local move set; recombination over the run's own states is information no
   local search can synthesise.
3. **DS-002 ★ (layer sweep, 21 EP)** — the best value in the file: clean per-layer
   attribution, a self-veto per layer, and the smallest budget of any entry with a
   joint-measurement acceptance rule.
4. DS-004 (annealing, 45 EP) · 5. DS-010 (beam, 85 EP) · 6. DS-008 (ILS, 49 EP) ·
7. DS-007 (rows, 57 EP) · 8. DS-009 (LNS, 45 EP) · 9. DS-005 (focused, ≈29 EP) ·
10. DS-006 (pairs, 29 EP) · 11. DS-011 (swaps, 49 EP) · 12. DS-012 (control, 65 EP).

**Cheapest search with a real chance: DS-002 at 21 EP** (≈ 21 held-eval equivalents,
no retraining) — one layer sweep, every accepted batch jointly measured, per-layer
restore if a layer hurts. DS-005/DS-006 match its price (~29 EP) but buy unverified
or second-order moves; DS-002 is the cheapest entry whose acceptance rule is the
same kind (measured, joint, reversible) as the top-ranked entry's.

**The lens's shared bet, stated once:** the champion's 2.8580 is a *vote equilibrium* —
a state where 32-vote evidence stopped moving weights — and no procedure in the lab
has ever optimised measured loss over the discrete state directly, at any budget.
If all twelve entries ship the champion under their CAL-B rules, that is a strong,
priced result: the vote equilibrium is a loss optimum at calibration resolution,
and post-training search joins the readout lens as a closed direction — with the
budgets above as the cost of knowing.
