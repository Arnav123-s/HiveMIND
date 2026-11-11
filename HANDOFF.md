# Handoff: HiveMIND (`main` has PR #7; work continues on `make-it-work`, draft PR #8; checkpoint branch `checkpoint-2026-11-10`)

Written 2026-11-09 at commit aa301bc. Everything is committed and pushed. Nothing is running.

## Live status (kept current; read this first)
Updated 2026-11-10 (evening UTC). PR #6 is merged into `main` on his approval. Work continues on `make-it-work`, restarted from `main` (draft PR #7); everything is pushed.

**Arnav's direction now (2026-11-10, his words in short):** the codebase is the agent's to run; full approval to act
freely. What he wants is a hive of a great many small specialist models that together are highly capable, follow
every order, are always on and keep growing. New specialists cover gaps; they do not have to relearn what older ones
know and they replace nobody: "a huge amount of cells acting as one creature". Under 10 GB RAM, no GPU. Rules written
by older agents may be outdated; what he described is what counts. Kept from the old rules because they protect him:
the guard (nothing that spends, deletes, sends as him or logs in unless he ordered it), credentials stay local, no
benchmaxing, held-out sets run once, no model names in commits.

**Added by him later the same day (2026-11-10):**
- The small hive may be losing because its members are all the same model. (Measured so far: the planner's two
  specialists got the same 9 exam lessons right. Being tested: `training/diverse.py`.)
- A weight edit may do nothing where the model has no capability; train specialists, then edit. (Measured: the edit
  taught the planner 24 of 24 short plans and 3 of 22 long ones.)
- The hive must not depend on the agent: it must multiply and gain models and capabilities on its own.
- He would rather the hive train its own specialists (training, editing, fine-tuning) than recruit. Told him: that is
  the main path; a model that plans or codes cannot be trained from nothing on four CPU cores, so recruiting stays
  only as the way the hive gets a new starting model when the ones it has cannot learn a job.
- The machine is the agent's: disk space may be freed. (Freed: an unused 2.5B model file and the package download
  cache. The models the hive uses were kept.) "Don't delete caches" below no longer holds for this machine.
- All specialists are trained on the CPU already (128 lessons: 25 minutes); he asked for exactly that.
- Train from scratch on the CPU, and let the hive find, harvest and train on its own data. (Built: `team/harvest.py`,
  `training/scratch.py`.)
- Cells trained together, depending on each other, acting as one brain. (Built: `scratch.py together [--consult]`.)
- His picture, in his words: thousands of cells in a body, each with a function, alone not always important, together
  doing big jobs; all different; specialities may overlap; each cell the smallest model that can be made; more cells
  with more data, conquering more. (Built: `training/body.py`: one stem cell, overlapping territories, cells that weigh
  in by fit, growth where the body is worst.)
- It must get better on its own: the agent cannot watch over it and his access to the agent is limited. (Built:
  `python -m team body`, one unattended turn with a keep-only-if-measured-better gate, in `serve`'s idle loop.)
- Research he pointed to, looked up: weight-space programming (MIT CSAIL, Nov 2026; tiny localized edits expose an
  ability a model has, do not create one); LeCun and Balestriero's JEPA paper (Oct 2026; a 109M model lines up with
  image models better than a 72B one; the training method counted, 42x fewer examples); Tiny Recursive Model (7M
  weights, narrow puzzles, heavy augmentation); BitNet (fast on CPU, needs its own runtime).
- BitNet (his question, 2026-11-10: many big generalist BitNets, each different, each working on the others'
  weaknesses, trained by dreams that get harder). Checked: `microsoft/bitnet-b1.58-2B-4T` is 2.41B weights, MIT,
  ungated, a 1.19 GB file; its bf16 master weights (4.83 GB) exist for fine-tuning. The official file does not load
  in the hive's llama.cpp. A community conversion to the TQ2_0 format does load, and answered "Paris" and then
  repeated itself, and wrote no program: either the conversion or the stock runtime's BitNet support is not right,
  so that is not a fair trial. The fair trial needs Microsoft's own runtime (bitnet.cpp); building it here was
  refused by the session's permissions (code from outside the repository) and waits for his say. Not true of BitNets:
  cheap training (they are trained on full-precision weights underneath, as costly as any model), and "many
  different big ones" (one strong one exists; different edits of one model share their mistakes, as measured).
  True: small and fast to run, so several fit awake in 10 GB; three-valued weights suit small exact edits; cells
  with three-valued weights would let thousands fit (2.6M weights: 10 MB each now, about 0.6 MB then).
- Later the same day, his orders and what was done:
  - "Product first, measuring last; solve the missing parts." Done: PR #7 merged on his "merge yes"; `setup.sh` run
    from start to end on a fresh clone of `main` (165 tests passed there); scouts that find new text sources; the
    from-nothing brain wired into the cell jobs (it holds none yet: 65% mean test, today's cells are better).
  - "Keep the success safe." The branch `checkpoint-2026-11-10` on GitHub holds the code, the full-precision stem
    cell and the grown body (six cells). This session cannot push tags; a branch is the checkpoint.
  - The body: the first one was worse than its stem cell (cells knew their windows by heart). The second beats it:
    2.294 against 2.428 on 300 passages nobody trained on; each cell alone is worse than the stem cell; waking the
    stem cell and the two nearest cells is as good as waking all (2.295). Growth on the worst-read windows learned
    nothing (noise); growth is now by cell division (`body._division`), not run yet.
  - "Train our own BitNets, the same hive with BitNets that multiply." Built: `scratch.BitLinear`, packed cells under
    0.7 MB (`pack`/`unpack`), `scratch.py bitnet` converts the stem cell and keeps the old one (`base_full.pt`,
    `body_full/`); `cells/scratch/stem.json` says which kind the stem cell is.
  - "Find or make a direct way to train a BitNet." 8-minute runs from one random start, loss: no jumps 4.241; first
    direct way (jump with probability in proportion to the gradient) 4.237 to 4.293: it taught nothing; by votes (a
    small counter per weight) 4.667 / 4.450 / 4.181 / 4.141 / 4.174 at 4 / 8 / 16 / 32 / 64 votes; the published way
    4.031. So votes work (half of the published way's gain at 32) and nothing-at-all-underneath does not. For
    growing a cell from the stem cell there is `body._flip_read` (moves the best share of three-valued weights,
    keeps or undoes); it is a trainer in the body's population and has only run in a toy test.
  - "Data from dreaming." `harvest.dream`: the small member writes passages on what the body reads worst, harder
    after every forty; part of every harvest. Tested with the member mocked; not run with a real model yet.
  - BitNet from Microsoft as a recruit: the official file does not load in the hive's llama.cpp; building
    Microsoft's runtime here was refused by the session's permissions. Open, for his device or his say.
- **This cloud machine is reclaimed when idle.** The hive goes on evolving only where it is installed and left
  running: `python -m team install` on a device of his (README "Install", "Always on").

**Built on this branch (143 tests):**
- `python -m team school` (`team/school.py`, README "School"): a small model learns a bigger member's job from that
  member's own work, takes an exam on lessons it never trained on, and goes back for new lessons; gaps get new
  narrow specialists that sit beside the old ones (routing by the nearest known lesson; general ones can vote).
  A visit is resumable (`training/data/school/<role>_visit.json`). `serve` sends one role to school when idle, each
  in turn. Roles: `coordinator` (4B teaches 1.7B) and `coder` (7B teaches 1.5B, lessons judged by what the program
  prints; no class held yet).
- Planner after two visits (232 lessons): same plan as the 4B on 46 unseen lessons: untouched 30%, taught 59%
  (24 of 24 short plans, 3 of 22 long ones). Planner eval suite (14 cases): untouched 0.449, taught 0.663, 4B 0.872.
  Not graduated (needs 85%). The 4B's long plans are padded and inconsistent, so agreement on them is a poor target;
  the narrow specialist trained on the gaps added nothing (9 of 26 in its territory, the general one the same 9).
- In the small-only hive (`AGENT_TEAM_SMALL=1`) a taught specialist that is ahead of the untouched student holds the
  job (`school.holds`; `AGENT_TEAM_SCHOOL=0` switches it off). The taught planner holds it there now.
- Checks added on the way (all general, all tested): a research result that says it found nothing fails its step;
  fewer items than ordered asks the researcher once for others; a sort-direction check and a next-page check before
  the coder's review; an unchanged program after feedback is asked for once more with sampling; a juror objection
  that sets a number against itself is void.
- `serve`, when idle: evolve the specialist that failed most, then school, then a life turn.
- Found by reading the small-only failures: an example value in an instruction is copied by a 1.7B model
  ("X has 0.135B parameters" in the small reader's instruction came back as a fact). Instructions for small models
  carry no example values.

**Measured on the 16 development tasks (fixes were tried on these):**
- Normal hive: 15 of 16 in one run (`normal_after`); the one fail (arxiv) passed after the short-list retry
  (`normal_arxiv`); csv, chart, fib pass after the coder changes (`normal_code`).
- Nothing above 1.7B, one clean run of all 16 (`small7`), the taught planner planning: 11 of 16; every plan right.
  Fails: lookup, chart (the small reader copied its instruction's example value instead of reading what was asked),
  fib (a program failing his examples was passed by the jury), arxiv, csv. After the fixes: lookup and fib pass
  (`small8`); chart and arxiv with the reader's new instruction: see `small9` and `small_only_notes.md`.
- Normal hive after all of today's check changes (`normal_reg`, `normal_reg2`): lookup, explain, arxiv, fib pass.
- Two bench checks were wrong on right answers and were corrected (papers listed by title; "135M" for "0.135B").

**Open, in order:**
1. Cleaner lessons for long plans: teach the plan after the reviewer and the code checks (`coordinator.reviewed_plan`)
   or plans from runs that passed, instead of the 4B's first plan. Then re-examine.
2. The coder's first class is held: 160 lessons, the taught 1.5B prints what the 7B's program prints on 84% of 32
   unseen lessons (untouched 66%; first scored 81% and 59%, before two corrections to the key); not graduated (one
   lesson short), holds the job in the small-only hive (`coder15+coder_school`).
   Its lessons are pure computations; a second kind is needed for what fails without the 7B: changing a working
   program on feedback without breaking it (csv), and reading a number from a fetched page.
3. Small-only arxiv and csv still fail. The item juror is now asked without the whole list's requirements
   (`verifier.item_question`); arxiv's facts still do not survive the checks. csv: see 2.
4. More roles in school: researcher (extract), critic, plan_reviewer, each with its own key.
   Built, no class held: `coder_fix` (fixing a program from the hive's own feedback; lessons from the students' real
   mistakes, `school.teach_fixes`; several hours of the 7B for a first class).
4b. Recruits (`python -m team recruit`, `team/recruit.py`, `cells/recruits.json`): the hive finds, checks, downloads
   and tries small models of other families on the roles' exams, enrols and teaches by measurement. First tryouts
   First tryouts: Yi-Coder-1.5B and SmolLM2-1.7B, neither enrolled (under the untouched students on both exams).
   `training/diverse.py`: other families share fewer mistakes but are weaker, so voting gained nothing (27 of 32, as
   the best alone); two different families printing the same was right every time (58 of 58 over five pairs): a
   check to build into the coder's run loop (run a second family's program, trust agreement, spend effort on
   disagreement).
4c. From scratch on the CPU (`python -m team harvest`, `training/scratch.py`; his order of 2026-11-10): the hive
   harvests text (own logs + open datasets, licence-checked; 48 MB so far in `memory/harvest/`, not in git), learns a
   4096-piece vocabulary, a 2.6M-weight model reads it, then is trained whole on one cell job, same rows and test as
   today's cells. Without reading first: licence_open 99% dev, 53% on unseen words. Next: `scratch.py all` after the
   reading run, table in `training/reports/scratch_cells.json`; then harvest and reading in the idle loop, and the
   hive finding datasets itself as it finds models.
5. If routing by shared words sends tasks to the wrong narrow specialist once there are several, train a router cell.
6. Older: more logged work for the item juror's site (about 60 decisions, needs about 200); near-miss numbers for
   the spawned cell; held-out set 4 (run once, on frozen code).

**This machine (a cloud VM; restarts lose running jobs, files survive):**
- Python: `/home/user/agent-team/.venv/bin/python`. Background jobs are cut at 2 hours; school visits resume.
- A 4B plan costs about a minute; a 1.7B weight edit on 128 lessons takes 25 minutes.
- `runs/` and `memory/` (logged calls, decisions, audits) are not in git and do not travel to a new session; lessons
  (`training/data/school/`), exam records (`cells/school.json`), weight edits (`adapters/`, `adapters_gguf/`) do.
  `.gitignore` skips `adapters_gguf/*2.gguf`; a narrow specialist's file there needs `git add -f`.

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
- CPU only, 10 GB budget, no spending. Don't delete his files. (Caches and disk on this cloud machine: his word on
  2026-11-10 is that the agent may free space as it sees fit.)
- The final report uses the headings **Blocked on me / Changed / Found**, and marks anything unconfirmed.
- Merging any PR needs **his explicit yes for that PR**. PR #5 and PR #6 had it and are merged; the next one needs it again.
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
- **GitHub:** use `gh api` (REST; GraphQL returns 403). The PR is Arnav123-s/HiveMIND#7.
