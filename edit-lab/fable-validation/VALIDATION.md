# Validation of Fable's make-it-work claims — 2026-11-10

**Validated at:** `make-it-work` head **b67aad4883a9b42f69ee04806d19b082e45b4110** (fetched 2026-11-10 ~15:03 PT; one commit past the c580c4c head named in the original task). Read-only throughout: detached copy at `~/workspace/fable-audit-copy`, test suite run in a separate copy under this folder. Nothing was written to their branch or files.

**Method note.** HANDOFF.md itself warns that `runs/` and `memory/` are not in git. Anything resting only on those is marked UNVERIFIABLE-FROM-REPO — not confirmed, not denied. Where the repo does hold records (bench reports, school exam records, body records, code, tests), claims were checked number by number against them.

---

## Part 1 — The two claims Arnav quoted from Fable (validated first)

### Claim A — "The new cells are improving on text they never trained on (cell 0 from 1.96 to 1.71, cell 1 from 2.07 to 1.95), so they're specialising rather than memorising."

**The numbers: UNVERIFIABLE-FROM-REPO.**
The values 1.96 → 1.71 and 2.07 → 1.95 appear in **no committed file** at head b67aad4 — not in `training/reports/body.json`, not in any report, README, HANDOFF, or log in the repo (full-tree search). The only body measurement committed is the *first* body (`training/reports/body.json`: stem 2.4276; cells alone 2.67–5.33). The new cells themselves live in `cells/scratch/body/`, which commit 1eabfb7 deliberately gitignored ("Each machine grows its own body: its cells stay out of git"), and the per-cell before/after losses are printed to run logs by `differentiate()`/`grow()` in `training/body.py` — stdout that is never committed. Arnav's guess that a checkpoint might be in the repo does not hold for the new cells: the stem cell checkpoint is (`cells/scratch/base.pt`, 10,475,033 bytes), the body's cells and their scores are not.

**The mechanism behind the numbers: CONFIRMED in code, and it is genuinely built to make the claim meaningful.**
- Each cell's training (`_read` / `_flip_read` in `training/body.py`) holds out every 10th of its own windows as a check set it never trains on, measures on it every 100 steps, keeps the best state, and stops after three checks without improvement. The reported per-cell "was → loss" is exactly a start-vs-best loss on never-trained windows of its territory.
- The stage-level split is separate and stricter: `HELD = 40` — every 40th window is excluded from all training in this stage, and body measurements (`measure()`) run only on those, with a gate/report split so the reported set is never the set births were selected on.
- The windows cannot drift under the cells: commit 29ca4be made the tokenized corpus append-only (only new bytes are tokenized and appended; earlier positions never move), with a regression test (`test_the_corpus_only_grows_at_its_end_so_no_window_moves`, tests/test_spawn.py).
- One honest caveat, disclosed in body.py's own docstring: the stem cell was pretrained on the *whole* harvest, held-out windows included — every cell starts as its copy. "Text they never trained on" is true of the cells in this stage (differentiation/growth), not of the stem cell's original reading.

**The interpretation ("specialising rather than memorising"): OVERSTATED as stated — the evidence supports half of it.**
- *Rather than memorising:* supported by design and by the contrast case. The first body is the recorded picture of memorization — cells that "knew their few thousand windows by heart (one reached loss 0.29 on them and 5.33 on new text)" (`training/reports/body.json`, `why_it_failed`). The second-way design answers it directly: all 55,128 windows placed, per-cell check sets with best-checkpoint keeping and early stopping. An improvement on a never-trained check set is real generalization to unseen text — memorization cannot produce it.
- *Specialising:* not measured for the new cells anywhere in the repo. A cell's check windows come from **its own territory**, so a falling check loss proves it generalizes to unseen text *of the same kind* — it does not by itself prove its improvement is concentrated on its territory rather than spread over all text, and no committed record compares a new cell on its own vs other territories. Differentiation is structural (each cell reads only its territory), not measured comparatively. Train-vs-unseen divergence (the classic memorization signature) also cannot be checked for the new cells from the repo: no train losses for them are committed.
- Verdict on the sentence as a whole: the numbers are plausible and the machinery is real, but the specific values are **unverifiable from the repo**, and "specialising" is an interpretation one step beyond what the (uncommitted) measurements would show even if taken at face value — "improving on unseen text of its own kind, under a design that prevents the memorization failure the first body showed" is what the evidence supports.

### Claim B — "The BitNet model loads in the hive's runtime but its answers look broken there, so I'm building the official runtime to judge it fairly."

**PARTIALLY CONFIRMED — and the state in the repo has not changed.**
- *Loads, but broken:* the only record is Fable's own HANDOFF prose (HANDOFF.md at b67aad4, from commit 41bcb90), and it is more precise than the quote to Arnav: the **official** Microsoft file "does not load in the hive's llama.cpp"; a **community conversion** to TQ2_0 "does load, and answered 'Paris' and then repeated itself, and wrote no program." No artifact, log, or output sample of that broken run is committed anywhere in the repo — the anecdote rests on the handoff text alone. Fable's sentence to Arnav drops the official-vs-conversion distinction; the substance (something loads, its answers are not trustworthy, so the trial is unfair) matches their own written record.
- *"I'm building the official runtime":* **not visible in the repo.** At head b67aad4 there is no bitnet.cpp code, build script, artifact, or commit — the only BitNet commits are about the hive's *own* cells (c580c4c ternary layers; b67aad4 direct ternary-move trainer). HANDOFF.md is unchanged since 41bcb90 and still says building bitnet.cpp "was refused by the session's permissions (code from outside the repository) and **waits for his say**." If building has started, nothing of it had landed in git as of b67aad4 (2026-11-10 23:00 UTC). The vendored converter in `training/llama_cpp_convert/` is stock llama.cpp tooling, not Microsoft's runtime.

---

## Part 2 — The HANDOFF claim list (at c580c4c/b67aad4)

### Claim 1 — Whole-hive bench: normal 15/16; small-only 11/16, later fixes passing lookup/fib

**CONFIRMED — every element has a committed run record, and the records agree with the HANDOFF text in detail.**
- `training/reports/hive_bench/normal_after.md`: "15/16 tasks pass", only arxiv failing. `normal_arxiv.md`: arxiv re-run alone, 1/1 pass. `normal_code.md`: chart, csv, fib 3/3 after the coder changes.
- `small7.md`: "11/16 tasks pass"; its five fails are lookup, arxiv, chart, csv, fib — the same five the HANDOFF names, with the same causes.
- `small8.md`: lookup and fib pass after the fixes, arxiv still fails — as claimed. Later records stay consistent with the HANDOFF's open items: `small10.md` shows chart passing at last; `small11.md` and HANDOFF open item 3 agree that small-only arxiv and csv still fail. `normal_reg.md`/`normal_reg2.md` (3/3 each) cover lookup, explain, arxiv, fib passing.
- `training/reports/hive_bench/small_only_notes.md` is unusually candid for a lab notebook: it discloses that an earlier "13 of 16" small-only figure is "put together from separate runs, not one clean run" — the 11/16 is the clean single run. The two corrected bench checks are documented there too.
- Bonus consistency: the HANDOFF's older held-out line (9 / 11 / 13 of 16) matches `heldout.md`, `heldout2.md`, `heldout3.md` exactly.
- Caveat that applies to all bench claims: these are the development tasks (fixes were tried on them), one run each, on their machine; the committed records are the tool's own reports. Nothing contradicts them.

### Claim 2 — School: planner 30% → 59% (46 unseen; 24/24 short, 3/22 long); suite 0.449 → 0.663, 4B 0.872. Coder 84% of 32 (untouched 66%), not graduated

**CONFIRMED — the exam records carry the exact numbers.**
- `cells/school.json` (coordinator): `test_lessons: 46`, `untouched_agrees: 0.304`, `taught_agrees: 0.587`, `lessons: 232`, `graduated: false` ("it needs 85% and 3% over the untouched student").
- README's planner table supplies the split the HANDOFF quotes: "the 24 one- and two-specialist plans: 24 of 24; the 22 plans with three or more specialists: 3 of 22" — i.e. 24/24 short, 3/22 long, and it adds the honest caveat that the 4B's long plans are themselves poor targets.
- Suite scores are in dedicated report files: `training/reports/school_coord_untouched.json` mean **0.449** (n=14), `school_coord_taught.json` mean **0.663** (n=14), `school_coord_teacher.json` mean **0.872** (n=14).
- Coder: `cells/school.json` (coder): `test_lessons: 32`, untouched **0.656**, taught **0.844**, `lessons: 160`, `graduated: false`. README documents both scorings (first 59%/81%, then 66%/84% after two corrections to the answer key) and that 84% is one lesson short of the 85% bar (27/32).

### Claim 3 — "Specializing is very good," as their record states it

**PARTIALLY CONFIRMED — their record shows specializing working in specific shapes and failing in others, and it records both. As a blanket statement it is overstated; Fable's own files don't actually make the blanket claim — the HANDOFF reports the failures in the same breath.**
Where specializing measurably worked:
- School role specialists: the taught planner specialist beats the untouched student 0.587 vs 0.304 on 46 unseen lessons; the taught coder specialist 0.844 vs 0.656 on 32. In the small-only hive the taught planner holds the job and `small7`'s notes record "every plan was the right one" in the clean 11/16 run.
- Job-level specialists carry measured test scores on unseen rows across 23 jobs (`training/reports/scratch_cells.json`; the same table in `cells/scratch/brain.json`: e.g. orders_login 0.918, orders_delete 0.885, orders_spend 0.787), and jobs are held or taken away by measurement, as the failures below show.
Where it measurably did not:
- **The gap specialist added nothing** — `cells/school.json`, `narrow_in_their_territory`: coordinator_school2 got **9 of 26** in its own territory; the general specialist got the **same 9**. Routed answering scored the same as the general alone (0.587 = 0.587). README states it flatly: "The first narrow specialist … did not help."
- Two cells (answers_q, claims_agree) failed on real research text — `training/evals/answers_q_real.jsonl` holds the 15 real pairs behind the HANDOFF's "3 of 15 right" — and their jobs were taken away and given to the 4B / a code rule.
- The de_grammar cell (0.640 for the 0.5B cell vs 4B 0.733) is trained but **not called by the hive**, because the chain can't beat the 4B alone (HANDOFF measured decisions; `team/org.py` records the same verdict).
- The first body is specialization-by-territory collapsing into memorization (see Claim A).
Pattern in their own data: specializing pays when the specialist is a broadly-taught owner of a whole job (school roles, job cells); it has not paid when the specialist is a narrow patch on someone else's failures (the gap specialist) or when a cell meets real inputs instead of its synthetic test.

### Claim 4 — Cross-family agreement: two families printing the same answer were right 58/58

**CONFIRMED — exactly, in a committed measurement record.**
`training/reports/diverse_coders.json`, section `two_different_models_print_the_same`: the five cross-family pairs with any agreements read 16/16, 11/11, 13/13, 11/11, 7/7 — total **58 agreements, 58 right**. README reproduces the same five fractions and adds the right caveat itself: "On 32 lessons that is a small sample." The same record backs the HANDOFF's adjacent claims: voting gained nothing (most-printed answer 27 = best model alone 27) and the recruits were weaker alone (Yi-Coder 12/32, SmolLM2 0/32 — neither enrolled).

### Claim 5 — BitNet cells (commit c580c4c): three-valued layers trained on fp weights underneath; stored at 2 bits/weight; 2.6M-weight cell ~0.6 MB; a convert command that keeps the old cell

**CONFIRMED as a mechanism (code + tests); the size figure is consistent and test-bounded, but no converted artifact is in the repo to measure directly.**
- `training/scratch.py` (as changed by c580c4c): `BitLinear` quantizes weights to {−1, 0, +1} × layer abs-mean scale in the forward pass with a straight-through gradient to the fp weights underneath — i.e. trained on ordinary weights, exactly as the commit says; activations are rounded to 8 bits. This is a faithful b1.58 shape, not a label.
- `pack()` stores each ternary layer as two bit-planes (+1 plane, −1 plane) plus one scale — 2 bits/weight; the shared word-piece tables are not stored per cell. `to_bitnet()` is the convert command (`python training/scratch.py bitnet`); it copies the old stem cell to `base_full.pt` and moves the old body aside to `body_full/` — the old cell is kept, as claimed.
- Size: the fp stem cell file in-repo, `cells/scratch/base.pt`, is 10,475,033 bytes for 2,615,424 weights (`cells/scratch/record.json`) — the "10 MB each now" half of the claim checks out byte-for-byte. The packed half: pack's own docstring says "about half a megabyte for 1.8 million weights" (the ~1.8M non-table weights × 2 bits ≈ 0.45 MB, plus fp16 norms/biases), and the committed test `test_a_packed_bitnet_cell_answers_exactly_as_before_and_is_small` asserts a packed cell file is **< 700,000 bytes** while reproducing the cell's answers, against > 5,000,000 bytes unpacked. The HANDOFF's "about 0.6 MB" sits inside those bounds. But note: `cells/scratch/record.json` in-repo has no `bit` flag set and no packed cell artifact is committed (body cells are gitignored), so the conversion has not demonstrably been *run* on the committed stem cell — what is proven is that the machinery exists, is tested, and the arithmetic holds.
- The follow-on commit b67aad4 adds the direct ternary trainer (`_flip_read` in `training/body.py`: moves three-valued weights by gradient sign, keeps or undoes rounds by loss on unseen check windows) with its own test.

### Claim 6 — Body: stem cell, overlapping territories, growth where worst; "the first body recorded: worse than its own stem cell"

**CONFIRMED — mechanism in code, and the failure is recorded in their own report file, undisguised.**
- `training/body.py`: every cell starts as a copy of the stem cell; windows are embedded by the stem cell and k-means-clustered into territories, **each window belonging to its two nearest territories** (overlap is literal); `grow()` targets "the fifth of a sample of training windows the body predicts worst" (or the farthest-from-any-territory windows for scouts); births are kept only if the body improves on a gate set with no territory harmed (`judge()`: gain > 0.001, no territory worse by > 0.01); an immune check retires cells the body doesn't need; the stem cell is always a body member.
- `training/reports/body.json` (`first_body.measured`, 300 passages): stem cell alone **2.4276**; body by fit **2.4975**; by territory **2.7008 / 2.5558** — the body was worse than its stem cell under every combination rule, and `why_it_failed` says why in plain words (memorization; stem not a member). The same record keeps a rejected birth (cell 6: gained +0.0000, not kept) and a retired cell. The second-way fixes visible in current code (all windows placed, per-cell check sets with early stopping, stem as member) are direct answers to that recorded failure.

### Claim 7 — "143 tests"

**Count CONTRADICTED (stale, and in their favor); substance CONFIRMED — the suite at this head is 172 tests and all of them pass independently.**
- Static count of test functions at b67aad4: **172** (`tests/test_rules.py` 106, `tests/test_spawn.py` 39, `tests/test_interface.py` 15, `tests/test_cells.py` 12). The HANDOFF's live-status section says 143; its older section says "117 tests pass". Both figures are stale relative to the code at this head — test_spawn.py alone gained tests in c580c4c and b67aad4. 143 was plausibly the count when that line was written; it is not the count now.
- Independent run in a clean copy of the repo (this validator's machine; venv with CPU torch 2.15.0 and the rest of their pinned requirements installed): **172 passed, 0 failed, 0 errors** (437 s). A first run with an incomplete environment produced 45 failures/10 errors, every one of them a missing-module import (bs4, peft, …) in the validator's venv, not a code failure — with the requirements installed, they all pass. So the suite is real, larger than claimed, and green: the "143" figure is **contradicted as a count** (it understates the current suite by 29) while the substance behind it is **confirmed**. Among the passing tests are the three BitNet-cell tests and the append-only-corpus test relied on in Claims A and 5 — those mechanisms are not just code, they execute green.

---

## Is Fable's big success true?

Mostly, yes — with the edges showing. The parts of the success that can be checked from the repo check out *exactly*: the bench records carry 15/16 and 11/16 with the named failures and fixes; the school exam records carry 30% → 59% and 66% → 84% to the third decimal; the 58/58 cross-family agreement is arithmetic in a committed file; and the body/BitNet machinery Fable describes is really in the code, in the shape described — and executes: their full test suite, run independently in a clean copy, passes 172 of 172 (the HANDOFF's "143" is a stale undercount). Just as telling, the record is not curated for show: it keeps the gap specialist that added nothing (9/26 vs 9/26), the first body that lost to its own stem cell, the cells that failed on real text, and a "13 of 16" figure it explicitly flags as assembled from separate runs. Whoever wrote these records was measuring, not marketing.

What is *not* proven by the repo: the newest and most quotable claims. The body cells' improvement numbers (1.96 → 1.71, 2.07 → 1.95) exist only on Fable's machine — the cells and their run logs are deliberately kept out of git — and even if taken at face value they show within-territory generalization, not yet specialization measured against other territories. The Microsoft BitNet has never had a fair trial on their side: by their own handoff the official runtime was still waiting on Arnav's say, and nothing about building it has landed in git. And "specializing is very good" is true only in the shapes their data supports — taught owners of whole jobs — not as a general law; their narrowest specialist is the counterexample.

Bottom line: the success is real where it is recorded, the records are honest about the failures, and the two claims Arnav quoted sit precisely in the part that is not yet recorded anywhere he can check.
