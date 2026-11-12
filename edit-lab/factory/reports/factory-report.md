# Factory report — section-9 contract (auto-generated)

Computed from factory lineage, cycle states, and per-subject outcomes. A number appears only if a run recorded it.

## Cost per verdict (per cycle)
- `daemon-dry-proof-001` (dry_run): wall 2.0s — error-class-model: HOLD; contract-judgment-model: HOLD; gap-move-model: HOLD; commit-type-model: SHADOW_PASS; secret-line-model: HOLD; bug-pattern-composed: SHADOW_PASS; synthv1-r4-coordinator: HOLD
- `dream-niche-commit-001` (real): wall 10.0s — commit-type-model: REVERT
- `dream-niche-contract-001` (real): wall 10.0s — contract-judgment-model: WIN
- `dream-phaseC-001` (real): wall 9.0s — bug-pattern-composed: REVERT
- `dream-phaseC-002` (real): wall 16.0s — bug-pattern-composed: WIN
- `dry-phaseA-001` (dry_run): wall 2.0s — error-class-model: HOLD; contract-judgment-model: SHADOW_PASS; gap-move-model: SHADOW_PASS; commit-type-model: SHADOW_PASS; secret-line-model: SHADOW_PASS; bug-pattern-composed: SHADOW_PASS; synthv1-r4-coordinator: HOLD
- `dry-phaseB-smoke` (dry_run): wall 2.0s — error-class-model: HOLD; contract-judgment-model: SHADOW_PASS; gap-move-model: SHADOW_PASS; commit-type-model: SHADOW_PASS; secret-line-model: SHADOW_PASS; bug-pattern-composed: SHADOW_PASS; synthv1-r4-coordinator: HOLD
- `dry-phaseC-check` (dry_run): wall 2.0s — error-class-model: HOLD; contract-judgment-model: SHADOW_PASS; gap-move-model: HOLD; commit-type-model: SHADOW_PASS; secret-line-model: HOLD; bug-pattern-composed: SHADOW_PASS; synthv1-r4-coordinator: HOLD
- `phaseC-growth-001` (growth): standalone run (no loop state) — bug-wrong-operator-expression-model: rejected; bug-off-by-one-index-model: rejected
- `phaseC-ternary-001` (ternary): standalone run (no loop state) — error-class-model: fp stays; contract-judgment-model: fp stays; gap-move-model: fp stays; secret-line-model: fp stays; commit-type-model: fp stays
- `phaseC-ternary-002` (ternary): standalone run (no loop state) — error-class-model: fp stays; contract-judgment-model: fp stays; gap-move-model: fp stays; secret-line-model: fp stays; commit-type-model: fp stays
- `real-phaseB-001` (real): wall 2.0s — contract-judgment-model: WIN
- `real-phaseB-002` (real): wall 18.0s — gap-move-model: WIN
- `real-phaseB-003` (real): wall 14.0s — commit-type-model: WIN; secret-line-model: WIN
- `real-phaseB-004` (real): wall 0.0s — error-class-model: HOLD; bug-pattern-composed: BLOCKED; synthv1-r4-coordinator: HOLD

## Cost per adopted specialist
- coding/swarm/models/contract-judgment-model-v3.json (cycle `dream-niche-contract-001`): train examples 296, candidates trained 3
- coding/swarm/models/bug-wrong-operator-model.json (cycle `dream-phaseC-002`): train examples 87, candidates trained 18
- coding/swarm/models/contract-judgment-model-v2.json (cycle `real-phaseB-001`): train examples 138, candidates trained 3
- coding/swarm/models/gap-move-model-v2.json (cycle `real-phaseB-002`): train examples 308, candidates trained 3
- coding/swarm/models/commit-type-model-v2.json (cycle `real-phaseB-003`): train examples 416, candidates trained 3
- coding/swarm/models/secret-line-model-v2.json (cycle `real-phaseB-003`): train examples 163, candidates trained 3

## Eval budget vs caps
- Candidate evaluations recorded across outcomes: 54 (cap: 300 dev evaluations per search — no search approached it; the largest single search was the ternary flip map, recorded in its run directory).

## Stress ledger
- Heavy legs run: 0 (no Tier-1/Tier-2 leg has ever been admitted; every Phase A–C leg is seconds-class Tier-0).
- Governor backoff events recorded: 0 (none tripped)
- Thermal incidents: none recorded (this host exposes no thermal sensor; the heat gate is inert here and says so in every host profile).

## Substrate line (ternary vs fp, per niche)
- error-class-model: fp 0.9583 vs ternary 0.95 (ptq) — default stays **fp**; packed 4941 B vs fp artifact 264151 B; cross-substrate agreement 0.975
- contract-judgment-model: fp 1.0 vs ternary 0.9375 (ptq) — default stays **fp**; packed 311 B vs fp artifact 35286 B; cross-substrate agreement 0.9375
- gap-move-model: fp 0.9333 vs ternary 0.8667 (qat-h4) — default stays **fp**; packed 680 B vs fp artifact 117639 B; cross-substrate agreement 0.9333
- secret-line-model: fp 1.0 vs ternary 0.9923 (qat-h4) — default stays **fp**; packed 252 B vs fp artifact 67047 B; cross-substrate agreement 0.9923
- commit-type-model: fp 0.9625 vs ternary 0.7625 (qat-h4) — default stays **fp**; packed 397 B vs fp artifact 85910 B; cross-substrate agreement 0.7375

## Portability line
- cpu=4, gpu=False, chunk=20min: 12 cycle(s)
- All results to date were produced on the single probed profile above; no result has been re-verified on a second profile yet, and none is claimed to be.
