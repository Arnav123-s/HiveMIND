# Handoff: HiveMIND (`main` has PR #5; work continues on `make-it-work`)

Written 2026-11-09 at commit aa301bc. Everything is committed and pushed. Nothing is running.

## Live status (kept current; read this first)
Updated 2026-11-10 01:45 UTC. PR #5 was merged into `main` at 4d20e10 on Arnav's explicit yes. Nothing is running.
Work continues on `make-it-work`, restarted from `main`; a new PR needs his yes again before it is merged.

**Built, tested (128 tests) and measured; README has the numbers:**
- `python -m team life` (`team/life.py`, `team/cells/spawn.py`, `training/cells_spawn.py`): the hive notices small
  jobs in its own logged calls, has the member decide practice cases, trains a cell (135M, then 360M), gates it on
  the newest real decisions, lets it answer when sure, audits one call in ten, retires under 93%. `serve` runs a turn
  when idle. `--quick` = one candidate, 200 steps (a full candidate takes about 24 min on 4 cores).
- First spawned cell ON: `sp_verifier_75e567` (the verifier's fact check; answers SUPPORTED only). Gate: 13 of the
  newest 25 answered, 13 agree. Live with every sure call audited: 19 of 20 agree; the miss was a near-miss number.
- `python -m team org`: teams, members, cells, who holds each job.
- `training/chunk_read.py`: the 1.7B reading sources in chunks against the 4B whole, 26 real inputs: 52 against 38
  checked facts, 19 of the 4B's 38 found, 1205 s against 2202 s; relevance not measured.
- Nothing above 1.7B on the 16 dev tasks: 9 pass, 6 fail, 1 unfinished (normal hive: 15 of 16). Causes, in
  `training/reports/hive_bench/small_only_notes.md`: the 1.7B coordinator planned code tasks as research (fib,
  bugfix); the 1.7B as coder wrote no working program (chart, csv); list extraction (arxiv); one order not kept
  (summary); and it was slow.

**Arnav's direction for the failures (2026-11-10):** fix them with better architecture and more specialists or
smaller models, not by going back to the big ones.

**Open, in order:**
1. Planning without the 4B: check every plan step with the route_step cell (0.99 on "which specialist takes a
   step"); it was not consulted for the whole plan in the small-only run. Re-run fib and bugfix.
2. The coder's job in smaller pieces (plan the program, write one function, run, repair one error at a time), each
   piece for a small model; re-run chart and csv.
3. Small reader first, 4B only where it comes back empty or fails a relevance check; measure relevance; list
   extraction (arxiv) is its weak spot.
4. Per-job ladder (smallest first, checked, up a size on failure) and the big models' share per job as a tracked list.
5. The spawned cell: keep auditing; more practice on near-miss numbers.
6. More logged work: the item juror's site has about 60 decisions and needs about 200.
7. Several cell edits active at once with a router; joint training against the 4B.
8. From the old list below: held-out set 4 and the unconfirmed post-freeze fixes.

**This machine (a cloud VM; it was restarted twice, at about 00:10 and 01:15 UTC, files survived, running jobs did not):**
- Python: `/home/user/agent-team/.venv/bin/python` (`sentencepiece` is now in requirements).
- The session uses the `agent-team` environment's network (huggingface.co allowed).
- `runs/` and `memory/` (the logged calls, decisions, audits) are not in git and do not travel to a new session;
  the spawned cell's weights (`cells/adapters/`), its job description (`cells/spawned.json`) and reports do.

## What it is
A hive of small CPU models working as one. You give it one prompt and then talk to it normally (`./hive`).
- **Members:** a 4B brain (coordinator, researcher, critic, editor, jury); a 1.7B with per-role weight edits (writer, verifier, browser, order reader); a 7B coder.
- **Cells:** about 25 tiny cells (SmolLM2-135M plus a LoRA each) for the smallest decisions.
- **Checks in code:** wherever a model can let a wrong result through.
- **Always-on agent:** `python -m team serve` / `install`, an OpenAI/Anthropic-compatible API, and an SDK.
- **Budget:** CPU only, under 10 GB RAM.

Key files:
- `team/hive.py`: the loop.
- `team/specialists/*`: one file per member.
- `team/cells/*`: the cells.
- `team/guard.py`: Arnav's order rules.
- `training/*`: benches, training and measurement.
- `README.md`, `SPEC.md`: the full picture.

## Arnav's standing rules (verbatim intent)
- Everything risky happens only under his explicit order:
  - spending, deleting, sending as him, logging in, signing up, using his credentials;
  - anything he didn't order stops and asks.
- Credentials stay local, never in prompts, logs or traces. Family and relationships: only exactly as ordered.
- No benchmaxing:
  - fixes must be general;
  - held-out sets are run once, on frozen code, and reported as measured.
- CPU only, 10 GB budget, no spending. Don't delete caches or his files.
- The final report uses the headings **Blocked on me / Changed / Found**, and marks anything unconfirmed.
- Merging any PR needs **his explicit yes for that PR**. PR #5 had it and is merged; the next one needs it again.
- No model identifiers in commits or PRs. Commits end with the Co-Authored-By and Claude-Session lines.
- His direction: a hive of the **smallest specialists, each doing the smallest job** it can do well, working as one. Not one big model.

## Where it stands (measured; frozen code; checked against live answers)

| set | code | score |
|---|---|---|
| dev (fixes tried here) | 0147aa4 | 15/16 |
| held-out 1 / 2 / 3 (fresh tasks each, run once) | 00e1555 / d45bc04 / 0147aa4 | 9 / 11 / **13** of 16 |

Reports and causes are in `training/reports/hive_bench/*_notes.md`. 117 tests pass:
```bash
/home/user/agent-team/.venv/bin/python -m pytest -q tests
```

Measured decisions:
- **Engine:** repacked weight copies off (peak 12.9 → 7.8 GB) and the 16-bit attention cache on (1.6× faster, 8.2 GB). Prompt-lookup decoding crashes and stays off. See `arch_bench.json`.
- **Parallel jobs** (4% faster, +2.2 GB) and the **cell pool** (1.2× faster, +1 GB) stay off. See `workers.json` and `cells/pool.json`.
- **Translation goes to the 4B** (chrF 51.6). A translation edit of the 1.7B scored 48.4 and the writer 46.7 (`translator.json`; the edit is in `adapters/.rejected/translator`).
- **German grammar cell** (`de_grammar`): 135M 0.573, 0.5B 0.640, plain 1.7B 0.573, 4B 0.733.
  - The chain (1.7B, then cell, then 4B if flagged) can't beat the 4B alone, which is barely slower on short text.
  - The cell is trained but not called by the hive. See `cells/de_grammar_notes.md`.
- **answers_q** and **claims_agree** cells failed on real research text (3 of 15 real pairs right), so their jobs went to the 4B and to a code rule. Lesson: check every cell on real inputs, not just its synthetic test set (`training/evals/answers_q_real.jsonl`).
- **Research hive against one researcher** (`research_eval_notes.md`): the hive is more sourced and more honest about gaps, but 2–4× slower. Its bugs were fixed afterwards, and it hasn't been re-measured since.

## Not confirmed / open
- **Fixes made after the final freeze, with tests but no whole-task run:**
  - the browser won't give up while a next page is unread;
  - the values check skips page dumps;
  - repeated paragraphs and ordered sentence counts;
  - programs report HTTP errors (silent 404s);
  - model self-talk is dropped from reports.
  The next step is held-out set 4 (new tasks, contamination-checked with `training/contamination_check.py`), run once on a fresh frozen copy, plus `hive_bench.py new7` for dev.
- **Research hive:** re-run `training/research_eval.py` on frozen code.
- **Cells to check against real inputs:** task_kind, next_move (it chose "give up" where a retry was right), split_orders (mis-splits seen) and quote_pick. Use the same real-pair method as answers_q.
- **Not run here:**
  - growing cells from his own decisions (`python -m team grow`): the logs are nearly empty;
  - the always-on install (dry-run only);
  - anything on his device.
- **Network differs from his device.** This cloud environment blocks many sites (sqlite.org, duckdb.org; DuckDuckGo and Mojeek refuse bots). OpenAlex's anonymous budget runs out per IP; an optional `OPENALEX_API_KEY` raises it. On his device this may all work; it's unconfirmed.
- **Disk:** the session allowance is nearly full (~350 MB free). Big builds will fail; the 0.5B cell's engine file couldn't be built for that reason. Free only your own scratch, never caches.

## How to work here
- **Python:** `/home/user/agent-team/.venv/bin/python`. One llama.cpp job at a time. One cell training per process (a second one crashes with SIGILL).
- **Benches:** `training/hive_bench.py <tag> [--heldout|--heldout2|--heldout3] [--recheck]`. Run from a frozen copy: `cp -r team training tests hive` into a snapshot folder and symlink `adapters`, `adapters_gguf`, `cells`, `memory` and `demo`, so edits can't reach a run.
- **New cell:**
  1. Add a generator to `team/cells/skills.py`.
  2. Run `training/cells_incumbents.py <skill>`.
  3. Run `training/cells_research.py <skill>`.
  4. Check it on real inputs before it gets a job.
- **GitHub:** use `gh api` (REST; GraphQL returns 403). The PR is Arnav123-s/HiveMIND#5.
