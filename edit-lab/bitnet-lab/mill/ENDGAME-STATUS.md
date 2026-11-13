# ENDGAME-STATUS — Muse's work, Muse's side

Executor log for mill/ENDGAME.md (E-1…E-11). Each item closes here with evidence + numbers.
Plan copied to mill/ENDGAME.md at start.

## E-2 (ledger fixes) — CODE SIDE VERIFIED 2026-11-12 ~21:05 PT
All RIGOR-AUDIT §4 fixes confirmed present in screen.py by direct inspection:
- code_sha stamped on every ledger/trial line (stamp(), screen.py:152); corpus fingerprint (sha+bytes+pieces) on baseline lines (:470).
- "seed" explicit on probe lines (:432) and baselines (:467); trial seed events carry steps + wall_s.
- kind:"deferrals" line per pass per generation (ledger_deferrals :615, called :875).
- verdict=="error" = not-done, re-queues; explicit benched line after 3 errors (ERROR_BENCH_AFTER=3).
- sample_sd (÷n−1) at :160; per-seed adoption guard (≥2/3 seeds beat ref mean) in judge_trials; confirmation set (offset windows, run_confirmation :555); champion install inside one Locked() flock section.
- sweep_probe.py validates its copied argparse against train.py --help at startup, refuses loudly on drift.
REMAINING for E-2: the gen-0 pass itself + one hand-inspection of the ledger. Pass starts after E-1 + E-3.

## E-1 (preflight) — PARITY PASS; noise pending a genuinely free slot
- Parity: **PASS, twice** — sweep seed-0 champion held_init = **8.3138 exactly** both runs. The sweep is bit-faithful at init; sweep verdicts are licensed on that axis.
- Probe-noise: NOT yet measured. Both preflight attempts aborted at noise seed 0 ("did not complete"). Root cause found by a hand-run sweep job: sweep_probe prints `MILLSTOP busy:run_scale_ladder` — **the scale ladder is active again** and the sweep yields mid-preflight (parity's 15 s job slips through; the 75 s noise job gets stopped). Per hard rules the ladder is never preempted: the noise half (3 × 75 s) runs in the first slot where lab_busy() is clear at job start. PREFLIGHT-RESULTS.md on disk records parity PASS / noise FAIL-incomplete.
- PROMOTE_DELTA decision waits on the noise sd. Note E-11's bar audit (below) independently supports treating 0.05 as a floor, not a given.

## E-11 (fidelity floor) — ANALYSIS HALF CLOSED 2026-11-12 ~21:11 PT (mill/FIDELITY.md, mill/OVER-HORIZON.md)
- Scope finding: runs.jsonl contains **zero probe-budget runs** — true 75 s→8 min fidelity is unmeasured; the filed stand-in (seed-0 at full budget) was scored instead. 13 comparable arms × 3 seeds (snapshot reproduced champion ref 2.8580 ± 0.0161 exactly).
- Spearman ρ vs 3-seed mean-held ranking: seed-0 held **+0.934 global but +0.371 in the |Δ|≤0.10 decision band**; train_last100 +0.846 (near-band +0.257); mean_flip_share **−0.193 (no fidelity)**; null control held_init ρ +0.730 → most headline correlation is chassis structure, not treatment signal.
- Bar audit at PROMOTE_DELTA=0.05: sign flips 2/12 (16.7%); **false-promote 1/1 promotions issued (100%)** — ste_half, Δ_seed0 +0.0615 vs true +0.0374 (39% winner's-curse shrink); false kills 0 but vacuously (kill side untested). J-028 admission test FAILS → probe demoted to advisory judge, serviceable as bottom-killer.
- Over-horizon (J-027 minimal): **95/380 entries = 25.0%** (44 HARD 11.6% — mechanisms arithmetically cannot act in ~25 steps; 51 SOFT 13.5%) — their flat probes must ledger INCONCLUSIVE—horizon, never kills.
- REMAINING for E-11: concurrency — bench_concurrency.py in a free slot, or the bundle confesses CONCURRENCY=1 for all gen-0 numbers.

## E-3 (merge) — GATED
FLAGS-BUILT.md results section still unfilled — flag factory verification suites not yet complete (re-running from flaglab/ after runtime restart). NO MERGE until its completion report shows baseline-identity suite green.

## E-4 (corpus-v3) — IN PROGRESS (corpus stream)
SOURCES.md now exists (6,569 B); build.log shows Gutenberg ingestion past the blocklist step; corpus-v3.u16 currently 4,776,400 B = 2,388,200 pieces and growing. check_v3_split.py runs when the build settles. True count TBD from finished file — never ~21.4M.
