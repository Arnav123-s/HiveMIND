> **Muse's work** — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# Composite re-runs of b4 and b6 with the fixed web tools — 2026-11-11 (evening, PT)

Re-runs of the two failed Part B composites through team.Hive, using the web-tool
fixes recorded in composites-fix-2026-11-11.md (retry on conn errors/timeouts/
429/5xx, arXiv per-host pacing ≥3.1s, title-first arXiv search). Task texts are
the originals, recovered verbatim from results/hive_runs/b4/TASK.md and
results/hive_runs/b6/TASK.md (copies in results/rerun-tasks/). Scoring mirrors
the original battery record (results/hive_battery.json): b4 = mad.py produced
in the work directory; b6 = the final report contains all three title fragments
('denoising diffusion probabilistic', 'deep bidirectional transformers',
'trained on code'), scored as the fraction present.

Runs executed with the fable-validation venv (transformers 5.22.2, torch
2.15.0+cpu, PyTorch path — no llama_cpp in that venv), OMP/MKL/AGENT_TEAM
threads pinned to 2, --approve never. One run at a time.

## b4 — coder task (median absolute deviation → mad.py)

- Launched 17:38 PT, finished 18:59 PT (B4_EXIT=0). Wall 4,825s (~80 min),
  of which ~40 min was one-time HuggingFace downloads: neither base model was
  cached on this VM (Qwen3-1.7B ~3.4GB, then Qwen2.5-Coder-1.5B-Instruct
  ~3.1GB). Both are cached now, so later runs start warm.
- (Operational note: the first launch at 17:34 PT was killed ~2 min in by a
  runtime restart; the immediate relaunch then failed in 169ms because the
  task file had been staged in /tmp, which the restart wiped. Task files were
  moved to results/rerun-tasks/ and the run relaunched cleanly at 17:38 PT.)
- **Outcome: FAILED, score 0.0 — mad.py was never produced.** Same headline as
  the original run, completely different failure point.
- What went right (the fixed layer): every web call completed. The researcher
  searched Wikipedia (5 results, ~2s), HuggingFace (0 results, clean) and
  PyPI (1 result) with zero timeouts, zero connection errors, zero retries
  exhausted — the exact calls that killed the original run. Both model
  downloads, impossible on the original night, completed.
- Where it failed instead:
  1. Researcher/verifier layer: on every researcher attempt (s1 ×3, and the
     s2r and s3r reroutes), the verifier rejected the extraction with
     "no fact survived checking against its source". Searches returned the
     right pages; no quoted fact passed the source check.
  2. Coder deliverable layer: s2 ran 3 step-attempts; the coder produced
     runnable code in its sandbox scratch (work/s2.py, runs reaching exit 0)
     but never wrote the named deliverable, and the verifier failed each
     attempt with "No files are present." Its converged scratch code also
     drifted from spec (function named calculate_mad; an intermediate version
     computed median(|x|) instead of MAD; one version imported scipy, which
     is not installed, and the checklist forbids the statistics module).
  3. Browser step unavailable in this environment: s3 failed all attempts —
     Playwright's Chromium executable is not installed for this venv
     (ms-playwright cache lacks chromium_headless_shell-1243), and retries
     then hit a Playwright sync-in-asyncio error. Not a web.py issue.
- Irony worth recording: the hive still computed the right answer. The s4
  test step's scratch code (work/s4.py) contains a correct two-step
  median_absolute_deviation and the final REPORT.md states the MAD of
  [1, 1, 2, 2, 4, 6, 9] is 1.0 — correct. The knowledge was there; the
  deliverable file was not.
- Run record: results/hive_runs/b4-rerun-2026-11-11/ (REPORT.md, TRACE.md,
  work/s2.py, work/s4.py); console log results/hive_b4_rerun.log.

## b6 — three-paper arXiv lookup

- Launched 19:02 PT, finished 19:17 PT (B6_EXIT=0). Wall 915s (~15 min) —
  models already cached from the b4 run. Plan: s1 researcher (all three IDs),
  s2 writer. Checklist identical to the original run's.
- **Outcome: FAILED, score 0.0 — 0 of 3 battery fragments in the final
  report** ('denoising diffusion probabilistic' ✗, 'deep bidirectional
  transformers' ✗, 'trained on code' ✗). Against ground truth the report got
  1 of 3 titles right (see the battery-check discrepancy below).
- What went right (the fixed layer): every arXiv call completed in ~3s. No
  HTTP 400, no 429, no timeouts — the original died on exactly those. A direct
  probe of the fixed search_arxiv after the run shows what the researcher was
  served for each ID query: 2103.00020 → 3 results with the correct paper at
  rank 0; 2005.11401 → 1 result, the correct paper; 1810.04805 → 5 results
  with the correct paper at rank 0. The correct title was in the tool output
  for all three IDs.
- Where it failed instead:
  1. Researcher planning/extraction: across all 3 attempts the researcher
     only ever queried the first ID (2103.00020), and each time the verifier
     rejected its listed item — "The source line does not contain the exact
     title of the paper." The title sat in the search results; the
     researcher's extracted fact cited a source line without it. s1 gave up
     after 3 attempts; the other two IDs were never searched.
  2. Writer fallback: with s1 unconfirmed, the writer still produced a
     report listing the one title it had — "Learning Transferable Visual
     Models From Natural Language Supervision" — against all three IDs.
     (That title is in fact correct for 2103.00020 and wrong for the other
     two.) The critic passed the report because it matched "the verified
     results" — of which there were none for two IDs.
- **Battery-check discrepancy (important, and not the hive's fault):** two of
  the original battery's three expected fragments name papers that are not
  in the task's ID list. Verified against the arXiv export API (id_list
  lookup, 2026-11-11): 2103.00020 is the CLIP paper "Learning Transferable
  Visual Models From Natural Language Supervision" — not the Codex paper
  ('trained on code', which is 2107.03374); 2005.11401 is "Retrieval-
  Augmented Generation for Knowledge-Intensive NLP Tasks" (RAG) — not DDPM
  ('denoising diffusion probabilistic', which is 2006.11239). Only the BERT
  fragment matches its ID (1810.04805). So as recorded, b6's checks could
  not have passed with fully correct answers; the overnight battery's
  ID↔paper mapping was wrong for 2 of 3. The fix note's spot-check inherited
  the same mapping (it title-searched for DDPM/Codex). The title-search fix
  itself is sound — this is a defect in the composite's recorded checks.
- Run record: results/hive_runs/b6-rerun-2026-11-11/ (REPORT.md, TRACE.md);
  console log results/hive_b6_rerun.log.

## Bottom line

Both re-runs completed end-to-end and both still score 0.0 — but neither
failed anywhere near the layer that was fixed. The web layer (retries,
pacing, title-first search) performed flawlessly under the real hive: zero
transport failures across both runs, versus the original night where
transport failures were the whole story. The failures moved up a layer:
researcher extraction that the verifier's source check rejects, a coder
that never emits the named deliverable file, a writer that fills gaps with
the one fact it holds, and (b6) a battery check set that misidentifies two
of its own target papers. The composite scores only move when those layers
are addressed; the fetch-layer fix was necessary and is confirmed, and is
not sufficient.

hive_battery.json was NOT updated: its format is one status/score/detail
per task with no re-run history, so recording these outcomes there would
have overwritten the original record. This note is the re-run record.
