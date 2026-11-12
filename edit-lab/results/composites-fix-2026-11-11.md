> **Muse's work** — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# Composite (Part B) reliability — diagnosis and tool-layer fix, 2026-11-11

Battery record (results/hive_battery.json, overnight 2026-11-09/10): b1 arXiv lookup
COMPLETED 1.0 (1376s); b4 coder task FAILED (1990s); b6 three-paper lookup FAILED
(3015s); b2/b3/b5 never run. Note: an earlier "0/6" framing in chat summaries does
not match this record — the record is 1 completed / 2 failed / 3 unrun.

## Root causes found

1. **Fetch layer had no transient-failure tolerance** (team/tools/web.py `get()`):
   retried only HTTP 429 (3 attempts, 3s/6s). Connection errors, timeouts and 5xx
   failed on the first attempt. b4's researcher step died this way (HF host
   unreachable at that hour; the same host answers 200 today).
2. **No pacing for arXiv's politeness rule** (1 request / 3s). b6's rapid fan-out
   drew 400 → 429 → timeouts across an hour of hive-level retries.
3. **arXiv query form buried the target papers**: `all:{title}` relevance ranking
   does not return the DDPM or Codex paper in its top 6 for their own titles
   (measured live 2026-11-11). Even a perfectly reliable network would likely have
   failed b6's checker — the researcher was reading the wrong papers.

## Fixes (~/workspace/hivemind-muse/team/tools/web.py, local working tree)

- `get()`: retries connection errors, timeouts, 429 and 5xx — 4 attempts,
  exponential backoff, honors Retry-After (capped 30s); permanent failures raise
  FetchError with the attempt count spent.
- Per-host pacing: export.arxiv.org / arxiv.org held to ≥3.1s between calls
  (lock-guarded).
- `search_arxiv()`: title-field phrase search (`ti:"..."`) first, topped up from
  `all:` deduped by id; HTTP 400 retries once with punctuation stripped.

## Verification

- Stub tests (stubbed session): 429→200, conn-error+timeout→200, 503→200 all
  recover; permanent 500 and permanent conn-error raise FetchError after exactly
  4 attempts. All pass.
- Live arXiv, b6's three queries, limit 6: **3/3 target papers at rank 0**
  (Denoising Diffusion Probabilistic Models; BERT; Evaluating Large Language
  Models Trained on Code). Three-call pacing total 8.0s (floor ~6.2s).
- Live HF search returns results; hivemind-muse test suite: 16 passed.

## Still open

- Full end-to-end re-runs of b4 and b6 through team.Hive (30–50 min each at
  overnight speeds) — queued for a free VM window after growth cycle 3; the
  tool-layer evidence says both failure modes are now covered, but the composite
  score only moves when a full run completes.
- b2/b3/b5 were never defined in any saved file — the overnight battery runner
  itself was not kept, only its results. Rebuilding those three tasks is a
  separate decision.
- The web.py change is uncommitted in the local hivemind-muse working tree;
  nothing pushed.
