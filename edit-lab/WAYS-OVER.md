# Ways over the diagnosis (Arnav's order, 2026-11-09)

Diagnosis recap: (1) no headroom — base 0.930, edits trade cases; (2) the original
adapter was trained on scorer-contradicting data (2-step plans vs the 3-7 rule);
(3) data too small/narrow — loss falls, behavior doesn't; the function is diffuse;
(4) the instrument (n=5-14, env-wobbly) is coarser than the win gate.

## Over (2) and (3): rebuild the data, machine-checked, at scale
- Generate candidate gold plans with the base model itself across many task types,
  domains and phrasings; keep ONLY plans that pass every check in observe.py's
  coordinator.normalize + checks (size 3-7, right agents, done_when, ends-writer,
  for_each where required). Checker-in-the-loop synthesis: hundreds of diverse,
  scorer-aligned rows, zero human labeling.
- Data audit gate before any training: a row whose plan violates a check is
  rewritten or dropped. No scorer-contradicting row ever trains again.
- Self-distillation: include the base model's OWN correct outputs as targets, so an
  edit learns to preserve base behavior while adding the missing skills.

## Over (1): stop demanding one adapter beat base everywhere
- Per-case routing: candidates already win individual cases (documented in the
  reports). Serve base + the best variant per case-family, routed by measured
  per-case strength — the hive's variant-routing principle. A composed win is a win.
- Jury option: base and adapter both answer; a verifier rule picks. Opus's guard
  pattern (two readers must agree) applied to plan selection.
- Decompose to where headroom exists: base's 0.930 hides weak CHECKS (for_each
  emission, done_when completeness). Narrow cells for the weak checks, base for
  the rest — Opus's shape, aimed at the base's actual failure profile.

## Over (4): make the instrument finer than the gate
- Pin ONE protocol (OMP=2, fixed threads, greedy) and re-anchor base + finalists
  under it, once, uniformly.
- Expand the held-out suites with fresh cases (n=14 -> 40+), never trained on —
  the set-2/set-3 pattern from make-it-work. One case becomes 0.025, not 0.07.
- Judge by paired per-case deltas vs base across suites (sign test), not one mean.
- Regression gate for every candidate: it may not break a case base passes by
  more than the noise floor — the never-below-baseline principle, per case.

## Order of work
After the drop14 + soup50 tests close the current queue:
1. Build the synthesis pipeline + audit gate; produce the dataset; log counts.
2. Train thin + standard candidates on the new data (both shapes, win-gated).
3. Build the router/jury composition from all measured variants; measure it.
4. Pin the protocol, expand held-out, run the final measurement of everything.
All under the standing rules: observe.py pristine, no test-set tuning, lineage
logged, honest verdicts.
