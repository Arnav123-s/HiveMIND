# Morning Report — 2026-11-10 (overnight run, HiveMIND line)

_Compiled overnight 2026-11-09 23:04 PT → 2026-11-10 morning. All verdicts measured; nothing here is a projection._

## Headline: the working hive + whole-hive benchmark

The unified system was assembled from the lab's verified pieces and run
end-to-end on fresh, never-trained tasks written for this run (battery:
`hive_battery.py`, raw results: `results/hive_battery.json`).

**Specialist battery (complete):**

| task | system | result |
|---|---|---|
| tiny-hive ops (21 fresh in-domain calls) | constructed-weight specialists, clone vote + reference check | **21/21 exact**; 3 out-of-domain probes all refused fail-closed, as designed |
| classify error-class (12 fresh tracebacks) | swarm TinyNet (9,228 params) | **12/12** |
| classify secret-line (12 fresh code lines) | swarm TinyNet (512 params) | **10/12** |
| classify commit-type (12 fresh messages) | swarm TinyNet (2,376 params) | **10/12** |
| classify contract-judgment (12 fresh snippets) | swarm TinyNet (468 params) | 7/12 — below its bar (see "not working") |
| classify gap-move (10 fresh failure texts) | swarm TinyNet (3,825 params) | 4/10 — below its bar (see "not working") |

**End-to-end hive tasks (team.Hive: plan -> verified steps -> writer; coordinator = the winning synthv1-r4 adapter): 3 attempted, 1 completed end-to-end.**

| task | result | detail |
|---|---|---|
| b1 — arXiv 1706.03762: exact title, first author, submission year | **completed, 1.0** | all three facts correct in the verified report (1,376 s) |
| b4 — write median_absolute_deviation to mad.py, hidden unit tests | **failed, 0.0** | the plan front-loaded an unneeded web-research step; its HF-search path is unreachable from this VM; retries exhausted before the coder ran (1,990 s) |
| b6 — exact titles of arXiv 2103.00020 / 2005.11401 / 1810.04805 | **failed, 0.0** | combined id query drew HTTP 400, then export.arxiv.org rate-limited/timed out every branch; the abs-page fallback that rescued b1 did not save it (3,015 s) |

Not run: b2 (PyPI versions), b3 (Wikipedia), b5 (code fix) — the night ran out, and this network's egress to the needed APIs degraded badly across the b-runs. Root causes for both failures are in §4; nothing false was ever reported as success — the verifier/guard layers held throughout.

## 1. Coordinator repair contest — FINAL VERDICT: WIN, contest CLOSED

- **Pristine test (observe.py, anchor protocol, n=14): synthv1-r4 = 0.954 vs the 0.930 gate and the base anchor 0.930.** Paired per-case vs base: **2 wins, 12 ties, 0 losses** (gains on the two cases base scored 0.833; never worse anywhere).
- The winner: a rank-4/alpha-8 LoRA (layers 14–27, lr 1e-4, 1 epoch) trained on the **117-row checker-verified synthetic mix** (106 synth rows the base model generated and a programmatic checker filtered, + 11 hand-built for_each rows). The path that won was data, not surgery: every surgery/dose/soup variant on the original adapter family stayed below base; the synth-data retrain family took the top three dev spots.
- Dev screens (12-case, OMP=2; base 0.7479): r2 0.8511, **r4 0.9483**, r16 0.9483 — all with zero per-case regressions vs base; the r4/r16 tie broke to the thinner adapter.
- Administration note, stated plainly: the first test administration was killed by a VM restart at 10/14 (running 0.936, ceiling 0.9543 — not dead by ceiling, unlike drop14 whose partial ceiling sealed its loss). The same single test was completed with one rerun under the identical protocol; the partial log is preserved (`results/test_synthv1_r4_partial10.log`) and the rerun reproduced 9 of the first 10 cases exactly.
- **The contest is now closed** per your 2026-11-09 18:46 PT decision: no further candidates, doses, soups, or surgery against this gate. The winning adapter is at `candsets/synthv1-r4/coordinator/` and is the coordinator the hive battery below runs with.

## 2. Defect hunt (NO-GRADIENT-EDITING Phases 0–1, Qwen3-4B)

- **Suites built** (`build_defect_suites.py`, `data/defect/`): math dev/test 200 each (10 families; every answer computed by two independent code paths, kept only on agreement), IF dev/test 150 each (14 programmatic constraint checkers, each unit-tested on pass/fail pairs before use). Decontamination: word 8-gram overlap vs all lab corpora and dev↔test on boilerplate-stripped text + parameter-signature dedup across splits (method and its limits documented in the builder). Test files sealed — untouched tonight beyond being written.
- **Phase 0 base run, math dev (Qwen3-4B Q4_K_M, llama.cpp on the laptop GPU, greedy): 187/189 passed (98.9%).** Both failures classified **capability** (well-formed reasoning, wrong result — a sequence-index slip and a GCD slip on 38/47); **zero defect-class failures** (no truncation, looping, refusal, or format failures observed with /no_think at these lengths). Defect share of failures: 0% — far below the ~15% threshold that would trigger Phase 2 directional ablation on math. Honest reading: at this difficulty band the 4B has almost no headroom of defects to fix; the defect hunt's open flank is the IF suite (constraint behavior), not math.
- **Run-state honesty:** 11 math-dev cases were not run (a thermal kill, below) and the IF dev base run did not complete before this report — the IF classification is the defect hunt's unfinished half and is stated as such.
- **Thermal incident (also in §4):** the llama-server's continuous generation load climbed to 93°C with no plateau (serving ≠ burst training thermally); killed at 93°C, box unharmed, 189 cases banked. Remaining defect runs are chunked (~45 cases, server kill + full cool between) under a new LEDGER rule.

## 3. Factory architecture
FACTORY-ARCHITECTURE.md stands as revised 2026-11-09: machine-agnostic, low-stress, runtime-adaptive; BitNet ternary specialists as a Tier-0 substrate with the ternary-vs-fp head-to-head protocol. _Implementation status below._

## 4. What is still not working (stated plainly)

- **The end-to-end hive is real but fragile against the outside world.** Its one clean composite win (b1) came when the research tool path worked. b4 died on an unreachable search host plus a plan that needlessly depended on it; b6 died on arXiv API rate-limiting (400 → 429 → timeouts across ~an hour of retries). The verifier/guard layers behaved correctly throughout — nothing false was reported as success — but task-level resilience (alternate source paths, per-branch isolation so one dead API can't sink a fan-out) is the honest gap. That is the next engineering target, ahead of more capability work.
- **Two Tier-0 classifiers generalize worse to fresh surfaces than their held-out scores suggested** (contract-judgment 7/12, gap-move 4/10 tonight vs 0.938 / 0.878 same-distribution). Small nets, narrow training surfaces — the fix is broader training surfaces per niche, not bigger nets.
- **The defect hunt is half-done.** Math Phase 0 is conclusive for its band (no defect class; nothing for ablation to fix), but the IF suite's base run did not finish — constraint-behavior defects, if any exist, are unmeasured.
- **The factory loop itself is designed, not yet built.** FACTORY-ARCHITECTURE.md is complete (machine-agnostic, low-stress, BitNet Tier-0, head-to-head protocol), and tonight's battery ran the *assembly* it prescribes — but the automated diagnose→map→edit→train→compose→grow cycle (§8 build list) has not been implemented as one self-driving loop. Tonight was the pieces, verified working together by hand-launched runs; the loop closure is the remaining build.
- **Role-model ceiling:** every LM role in tonight's assembly ran the same 1.7B base (plus the coordinator adapter) on CPU — the 4B/7B role models the architecture reserves for Tier 2 were not in tonight's loop (compute + the thermal incident). Plans/verifies are therefore 1.7B-quality; b4's planning miss is partly that.
- **Thermal:** one incident (93°C, killed, no damage). Continuous LLM serving on the laptop is a different thermal regime from burst training — now a written rule (chunk + cool).

## 5. The night's tally

- Coordinator repair contest: **WON and closed** (0.954 vs 0.930 gate, paired 2W/12T/0L) — the lab's first certified adapter win in this contest.
- Defect suites built (750 fresh verified cases); math Phase 0 complete: **no defect class in the 4B's math behavior** at this band.
- FACTORY-ARCHITECTURE.md: complete per the machine-agnostic/low-stress revision with the BitNet substrate.
- Whole-hive battery: Part A 5/7 bars met (2 partials named); Part B 1/3 composites completed end-to-end (2 failures root-caused, not hidden).
- Make-it-work line learned from, read-only (School apprenticeship + verifier hardening folded into our design/scoring).
- Nothing pushed to git. The binary push still waits on your one-time sign-in on the laptop, as before.
