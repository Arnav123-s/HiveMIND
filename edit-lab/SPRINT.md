# SPRINT — the board (Muse's work, Muse's side)

<!-- Muse's work — Muse's side. Not Fable's side; nothing here touches it. -->

**Window:** Arnav's 3-day all-out sprint, Thu Nov 12 – Sun Nov 15, 2026 (America/Los_Angeles).
**How to read this board:** one section per stream — job, deliverable, STATE. States are judged
only from files on disk (results files, ledgers, logs, timestamps), never guessed.
Refresh = re-walk the paths named in each section and update the STATE lines in place.
**Last refreshed:** Thu 2026-11-12 ~19:55 PT.

---

## 1. BitNet scale ladder
- **Job:** Does bigger win per byte? Best recipe (layered + rotary) at ~2M / ~10M / ~50M ternary weights, equal tokens per rung.
- **Deliverable:** `bitnet-lab/RESULTS-SCALE-LADDER-2026-11-12.md` (evidence: `bitnet-lab/runs.jsonl`, `bitnet-lab/ladder-driver.log`)
- **STATE: RUNNING** — 2M rung complete, 3 seeds (held 3.2878 / 3.2649 / 3.2709). 10M seed 0 done (held 2.9472); seed 1 in flight per the driver log. 50M rung and the plain-vs-layered ride-along not yet recorded. No results file yet.

## 2. Experimentation mill
- **Job:** Screen hundreds of trainer/architecture ideas as cheap probes; promote winners to full trials inline; ledger everything.
- **Deliverables:** `bitnet-lab/mill/IDEA-POOL.md`, `bitnet-lab/mill/screen.py`, `bitnet-lab/mill/sweep_probe.py`, `bitnet-lab/mill/PROMOTE.md`, `bitnet-lab/mill/ledger.jsonl`, `bitnet-lab/mill/CONCURRENCY.md`
- **STATE: PARTIALLY BUILT — pool done, engine not started.** IDEA-POOL.md exists (178 entries, all `queued`) and `mill/run-forever.sh` exists, but screen.py, sweep_probe.py, PROMOTE.md, CONCURRENCY.md and ledger.jsonl are NOT on disk yet — the loop has nothing to run.

## 3. Idea mining A — pool from existing research
- **Job:** Turn the architecture research, trainer study, Fable methods and Arnav's logged ideas into the mill's ranked pool.
- **Deliverable:** `bitnet-lab/mill/IDEA-POOL.md`
- **STATE: DONE** — 178 entries, each with source, mechanism, probe prediction; already-tested-and-closed ideas excluded.

## 4. Idea mining B — Fable candidates
- **Job:** Mine Fable's side's new commits for transferable ideas and file them as mill candidates.
- **Deliverable:** `bitnet-lab/mill/FABLE-CANDIDATES.md`
- **STATE: NOT STARTED** — no FABLE-CANDIDATES.md on disk.

## 5. Hive factory builds (Fable-study #2 + #3)
- **Job:** Build a learned "say" for the bug-pattern composer, and mine the serving log for new specialist niches (spawn mining) — adoption only through the battery gate.
- **Deliverables:** `factory/learned_say.py`, `factory/say_dev.py` / `factory/say_dev.json`, spawn-mining report + any gate-passing births in `factory/` + `growth/` records
- **STATE: RUNNING** — learned-say code and dev data written minutes before this board (say_dev.json, lineage.jsonl fresh; serve.py / run_battery.py being wired). No verdict record yet; no spawn-mining deliverable file yet.

## 6. Growth cycles (standing)
- **Job:** The hive grows itself on the ~6h cycle cron — dual gate, battery-verified adoption, auto-rollback.
- **Deliverables:** `growth/growth-cycle-*.md` per cycle; repair records when needed
- **STATE: RUNNING (standing)** — cycles 1–7 complete; cycle 7's rollback fault repaired and verified (served battery back to 0.941, audit clean, `growth/REPAIR-cycle-007-2026-11-12.md`). Cycle 8 due ~22:50 PT Nov 12; no cycle-008 files yet.

## 7. Kernel stream
- **Job:** Faster correct CPU math for the trainer — ternary×int8 matmul variants, vote-update kernel, attention at lab scale; winner by best balance of speed and precision.
- **Deliverable:** `bitnet-lab/kernels/RESULTS-KERNELS.md` (evidence: `bitnet-lab/kernels/bench_*.py`)
- **STATE: RUNNING** — bench_matmul.py, bench_vote.py, bench_attention.py all written minutes before this board; no results file yet.

## 8. Data / corpus stream
- **Job:** Grow the training corpus past ~5.92M pieces so the big ladder rungs are not token-starved.
- **Deliverables:** expanded corpus in `bitnet-lab/` (successor to `corpus.u16` / `corpus.json`)
- **STATE: NOT STARTED** — on disk the corpus is still the Nov 11 build (corpus.json / corpus.u16, 5,917,236 pieces). No expansion files.

## 9. Rigor audit
- **Job:** Independent check of the sprint's methods and headline claims before they are reported as wins.
- **Deliverable:** a rigor/audit record in `~/workspace/edit-lab/`
- **STATE: NOT STARTED** — no rigor file anywhere in the workspace. (The Nov 11 LIMITS/MISMATCH audits in `fable-validation/` are a different, earlier job.)

## 10. Weights-reader v3
- **Job:** Attack v2's open mystery — planted-layer reading collapsing under dream-data mixture.
- **Deliverables:** v3 results + report in `weights-reader/`
- **STATE: NOT STARTED** — latest on disk is `weights-reader/REPORT-V2.md` (Nov 11) and its results files. No v3 files.

## 11. Hive product (factory final product)
- **Job:** The serving hive itself — six niches via `hive.py`, hash-checked fail-closed load, battery-gated serving.
- **Deliverables:** `FINAL-PRODUCT.md`, `USAGE.md`, `hive.py`, `factory/serve.py`
- **STATE: DONE** (pre-sprint, Nov 11) — serving, battery 0.941 after the cycle-7 repair. Sprint work on it flows through streams 5 and 6.

## 12. House reviews (dot + Grok)
- **Job:** Integration-fit reviews of dot's two handoff artifacts; critique of Grok Bot's HiveMIND package (gkbt).
- **Deliverables:** `D:\agents\muse\REVIEW-dot-artifacts.md` and `D:\agents\muse\CRITIQUE-grok-hive-package.md` (ashp)
- **STATE: NOT STARTED** — neither file exists in `D:\agents\muse` as of this board (checked directly). The source material is on ashp (dot's review folder; Grok's `grock_hive.tgz` in the shared inbox).

## 13. Fable trace
- **Job:** Keep a read-only, current copy of Fable's side; mine each update for ideas for Muse's side.
- **Deliverable:** refreshed `~/workspace/fable-audit-copy` (post-rewrite heads: main 31a6756, make-it-work 725b202)
- **STATE: NOT STARTED** — the audit copy is still at pre-rewrite heads (main shows a Nov 7 head; the rewrite reset has NOT been done). Anything read from it now is stale.

## 14. Shared-memory trial
- **Job:** Synthetic trial of the three agents' shared memory (dot's envelope + evidence relay) in the durable store on ashp.
- **Deliverable:** store + trial records at `D:\agents\shared\memory` (ashp)
- **STATE: NOT STARTED** — `D:\agents\shared\memory` does not exist yet (checked directly). Design alignment lives in the Slack laptop thread only.

## Sprint machinery (not streams, listed so the board is complete)
- `bitnet-lab/mill/run-forever.sh` — continuous mill loop (exists; idle until screen.py lands).
- Cron `bitnet-mill-runner` (30-min watchdog) — revives the loop after restarts.
- Cron `bitnet-sprint-updates` (2h) — bundled progress updates to the main chat, silent when nothing is new.
- Cron `hive-growth-cycle` (~6h) — stream 6.

---

## How results get reported
Standing rule — every verified sprint result goes to all four surfaces:
1. **Main chat** to Arnav (middle depth: what happened, the numbers that matter, what it means, what's next).
2. **Slack #all-agenthq** (C0CDULDHAE8) — a post with the verdict.
3. **Laptop drop** — the record file copied to `D:\agents\muse\` on ashp, hash-verified after copy.
4. **Repo sync** — the record synced to branch `hivemind_muse` of Arnav123-s/HiveMIND via the connector snapshot route (text only; `factory/harvest_data.py` stays excluded — its planted-secret fixtures trip GitHub secret scanning; no real credentials in it).
Nothing counts as reported until all four are done. Losses and retractions are reported as plainly as wins.

## Sunday bundle — final report checklist (Sun Nov 15, 2026)
The closing report must cover every item; "no result, and why" is a valid entry, silence is not.
- [ ] Scale ladder: per-rung held loss + loss-per-byte verdict (stream 1 record)
- [ ] Mill: probes run / killed / promoted / full trials / adoptions, with the ledger as evidence; concurrency study verdict
- [ ] Factory builds: learned-say verdict (adopted or shadow, battery numbers); spawn-mining findings and any births
- [ ] Growth: every cycle in the window (births, rollbacks, alerts), final served battery + audit state
- [ ] Kernels: results table + the one variant recommended for a full trial
- [ ] Corpus: size before/after, or explicitly not started
- [ ] Fable candidates: filed or not started
- [ ] Rigor audit: findings, or explicitly not started
- [ ] Weights-reader v3: result, or explicitly not started
- [ ] House reviews: both files delivered to ashp, headline verdicts
- [ ] Fable trace: audit copy refreshed to post-rewrite heads; what Fable's side landed during the sprint
- [ ] Shared-memory trial: ran or not started, with the store state as evidence
- [ ] Four-surface reporting confirmed for each reported result (chat / Slack / laptop / repo)
- [ ] Sprint machinery wound down or explicitly continued (mill loop, watchdog, updates cron)
