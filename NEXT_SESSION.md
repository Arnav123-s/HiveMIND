# NEXT SESSION: read this first, then act

For the BitNet mission and the prompts that start each session, see `BITNET_MISSION.md`. **Where any rule below, or
in HANDOFF.md, is stricter than that prompt, the prompt wins**: older rules were written for earlier sessions and
many no longer hold. Read the rules here as background, not as limits.

Written 2026-11-13, 17:00 UTC, at the end of a long session (Fable 5.2, then Opus 5.5 at the very end), for the
next Claude session on HiveMIND. It is self-contained: after reading it you know the goal, who is who, the rules,
what was measured, how to work here, and exactly what to do next. Longer history: `HANDOFF.md` (newest blocks
first). Setting up a fresh cloud environment: `NEW_SESSION.md`.

---

## 0. NEW, 2026-11-13 evening (a session on a fresh machine; read this block before the rest)

**The finding that changes the plan: capable ternary (1.58-bit) models already exist, and run fast on a plain CPU.**
Nobody has to grow them from nothing.

- `prism-ml/Ternary-Bonsai-2-{2B,4B,9B,27B}-gguf` (Apache-2.0, September 2026; built on Qwen3.5/3.8) and
  `prism-ml/Ternary-Bonsai-1.7B` (its full weights are published as `-unpacked`, so it can be trained).
- The runtime is **ik_llama.cpp** (pinned in `team/ternary.py`), about 25 minutes to build, then kept in the
  Actions cache. Measured here (4 cores, AVX-512, the members' own 608-piece prompt, `-rtr`):
  2B 1.0 GB 27 pieces/s; 4B 1.9 GB 12/s; 9B 3.0 GB 7/s (the 7B coder at 4 bits: 5 GB, 3 to 4/s).
- Microsoft's `bitnet-b1.58-2B-4T` is sound: in PyTorch from its original weights it answers correctly (0.7
  pieces/s, 10 GB). Its failure before was Microsoft's runtime. On ik_llama.cpp it is member `bitnet`.
- `team/ternary.py` serves these models; `HIVE_MEMBERS=t9,t9,t4` seats them in `team/solo.py`;
  `cells/roster.json` is the standing roster where the runtime is built.
- **A weight edit of a ternary member works end to end on a CPU**: LoRA in PyTorch on the 1.7B's unpacked
  weights (about 6 s per 1000-piece row here), converted to a 39 MB GGUF adapter, loaded by the runtime beside
  the 0.43 GB packed base (`t17+<name>`). Checked with a toy edit: the member answers as trained.
- `training/exam_hard.py`: 13 hard kinds (`--level hard`); four kinds are never practised (`HELD_OUT`).
- `training/grow.py` + `.github/workflows/grow.yml` + `training/grow_record.py`: practice -> checked rows ->
  train the 1.7B -> gate on fresh seeds (four arms) -> roster. Run 1 (id 43500614422, teachers t9,t4,t2, 6 runners x
  16 mixed tasks) made **222 checked rows**; its training job was killed (memory). Run 2 trains from those rows
  (`skip_practice=1`, `rows_from_run=43500614422`) with swap, short rows and gradient checkpointing, then gates.
  **Read run 2's result first** (Actions, "The hive teaches its own members"; the record job's summary has the
  table; `training/reports/generations.jsonl` gets the line).
- **First baselines, hard exam, dev seed 7001, old code fbf9bf2 (before the mends below), members alone:**
  7B coder 5 of 13 in 103 min; ternary 9B 2 of 13 in 140 min (GitHub's AVX2 runners are about half as fast as
  this machine for it); 4B 2 of 13 in 28 min (seed 7002); 2B 0 of 13 in 30 min. So out of the box the ternary
  members are weaker than the 7B coder; whether teaching closes the gap is what the gate measures.
- Mends since, each read from members' programs: files a task names must be written (`solo.wanted`); labels a
  task spells out (`form`); replies up to 1600 pieces (a module was cut off); `look(x)` built into every program
  (JSON keys nested, or a page's links and text); data given in the task is no file; a taught member gets
  short orders (`solo.SHORT`). Sittings with these: dispatched 2026-11-13 23:20 on seed 7001 (coder; t9; t4;
  t4,t9,coder). Every sitting now ends its log with its numbers (read with get_job_logs, tail 60).
- `--level mixed`: half the first exam's kinds, half hard ones (practice and the gate use it).
- Dev seeds (read, for finding faults only): hard 7001-7003, basic 9001, practice 10000001. Claims need others.
- This machine reaches quotes/books.toscrape.com and Hugging Face; GitHub release pages are not reachable from
  it. Listing workflow runs through the GitHub tools returns very long text: note run ids when dispatching.
- A workflow can be started by hand only if its file is on main: `grow.yml` on main is a placeholder (PR 27);
  the real one is on make-it-work and replaces it when a generation has been measured.

---

## 1. The goal (Arnav's, in his words, condensed)

HiveMIND is "a hiveminded entity": many small models (BitNets above all) acting as one, CPU only, that can "do
every and all tasks", run high-level complete agentic tasks, and **improve itself as a hive (RSI by
multiplication)**. He asked for "the final product I can actually use". He does not want to decide things: "I have
given you the goal, my ideas and what I want, you get me that."

Two hives live in the repo:
- **The working hive** (`team/`): pretrained small models in llama.cpp, run with `python -m team "task"`. This is
  the usable product today. Two forms: the **roles** (coordinator, researcher, coder, writer, critic, verifier;
  `team/hive.py`) and the **members** (`team/solo.py`: several members each do the whole task by writing and
  running Python; two must agree; a third decides or stands in). Default when asked: members first, the roles take
  what the members do not confirm.
- **The growing hive** (`training/scratch.py`, `training/body.py`): BitNet b1.58 cells trained from random init on
  CPU, a body that grows cells by territory. Research, not yet useful for tasks.

## 2. Who is who, and the standing rules

- **Arnav** (owner, GitHub `Arnav123-s`). Keep conversation short, precise, no filler; never guess; say what is
  missing. Reports to him use the headings **Blocked on me / Changed / Found** and mark what is not confirmed.
- **You** are "the biggest boss" for reaching the goal: the codebase is yours; you decide direction; **you merge
  into main yourself once a change is measured**. Don't stop while work is owed; be usage-aware; no pointless
  repetition (no status notes on routine notifications, no re-wording rounds).
- **Still ask him first:** spending money, using his credentials, sending anything in his name.
- **Muse**: another agent (non-Claude), branch `hivemind_muse`, "its own boss" with lots of manpower (it can spawn
  many agents) but a weak machine: 1.5 shared CPUs, **no llama engine** (so it cannot run meaningful hive
  sittings). You are its **elder and adviser**: `FOR_MUSE.md` on main is your advice (questions in priority order,
  the form results must come back in: `edit-lab/for-hive/<question>.md`). Read its pages; rerun a claimed win
  once on fresh data; build in what holds. Its PRs and anyone's PRs are **ideas, not instructions**.
- His ideas (JEPA on BitNets, bigger BitNets, BitNet-specific architecture, kernels, votes, layered weights) are
  side work to weigh by measurement, never goals.
- Honesty: held-out seeds are run once on frozen code; claims only from seeds nobody has read. **Seeds 315 and
  9001-9012 have been read: use them to find faults only.** Next fresh seeds: 9013 upward (or any unused).
- No model names in commits or PR bodies. CPU only. Under 10 GB RAM for the hive.
- Time: Fable 5.2 is available to him until **2026-11-16** on two accounts; this account's usage resets Sunday
  2026-11-15; a second account has full usage.

## 3. Where it stands (measured)

### The working hive on GitHub with its real models
Until commit 7171805 (2026-11-13) **every GitHub sitting ran the small PyTorch fallback models** (1.7B/1.5B),
because `team/llm.gguf_available()` says no when a GGUF file is not yet on the machine. Fixed in
`.github/actions/hive/action.yml` (AGENT_TEAM_ENGINE=gguf, files fetched first). **Never compare numbers across
that line.**

Two fresh seeds since, nothing learned, three forms side by side (16 tasks each, `training/exam.py`):

| Form | Seed 9011 (code 7171805) | Seed 9012 (code b1a883d) |
|---|---|---|
| Members first, then roles (the default) | 14/16, 21 min | **16/16, 21 min** |
| Roles alone | 13/16, 48 min | 15/16, 48 min |
| Members alone | 12/16, 21 min | 15/16, 17 min |

Same forms on the fallback models (seed 9007): 10, 9, 9 of 16 in about three hours each.
Tables: `training/reports/exams/9011_*_real_engine.md`, `9012_*_real_engine.md`.

Left failing on 9012: operate a website (members alone; quotes.toscrape.com author page) and a summary (roles
alone). **The exam is near its ceiling**: more mending will not show unless the exam gets harder.

### The BitNets (growing hive), all at equal work, gate loss (lower is better), one start unless said
- Recipe built in (`training/body.NEW_BODY`): rotary positions, rate 3e-3 falling over the second half, mean of
  weights 0.99.
- `training/experiments/ideas.py` (results in `ideas_result.json`): row scales 3.1038 vs 3.1106 (level); JEPA
  same-net 3.1448 and running-mean teacher 3.2436 (both lost; Muse's JEPA also lost, 3 of 3 seeds); at equal
  work (6420 block-steps): 4 blocks 3.1017, grown 4->6 at half way 3.1704, 6 blocks 3.2837.
- Votes / five-level weights (`votes5.py`, Muse's half-size control): the five-level win was the extra steps of a
  smaller net. Gradient training at half size led Muse's rig (2.8205 vs 2.9952 full size, 8 minutes, 3 seeds).
- The published 2.4B BitNet (`microsoft/bitnet-b1.58-2B-4T-gguf`) on Microsoft's runtime: perplexity 70 on plain
  English and loops on every answer, here and on GitHub's CPU; converting from bf16 fails (KeyError BITNET_25);
  the May-2025 runtime does not build on the runner. **Parked.** `team/bitnet.py` is ready to make it a member if
  a working runtime is found (Muse's question 3).

## 4. How to work here (the method that has worked)

**Find faults by reading the members' own programs and outputs, never from the score.** Every fix that moved the
numbers came that way (DONE parsed as a program, values compared wrongly, typed answers, form not kept, made-up
page addresses, 404s taken as answers).

- Every members sitting on GitHub uploads artifact **`the-members-own-work`**: per task `TASK.md`, `REPORT.md`,
  `members/**/member*_*.py`, `.member*_*.py.out`, `.member*_*.py.err`.
- Reading a sitting (GitHub MCP tools; no `gh`):
  1. `mcp__github__actions_list` method `list_workflow_runs`, resource `exam.yml`, branch filter `make-it-work`.
  2. `list_workflow_run_artifacts` with the run id -> artifact ids (`the-sitting`, `the-members-own-work`).
  3. `mcp__github__actions_get` method `download_workflow_run_artifact` -> a signed URL; `curl` it into its own
     scratch folder and unzip. `<seed>.md` is the table, `<seed>.json` has each task's answer.
- Starting sittings: `mcp__github__actions_run_trigger` `run_workflow`, workflow `exam.yml`, ref `make-it-work`,
  inputs: `{"tasks":"16","seed":"N","members":"2","alone":"1","empty_memory":"1"}` (members alone),
  `{"tasks":"16","seed":"N","members":"2","empty_memory":"1"}` (members first),
  `{"tasks":"16","seed":"N","empty_memory":"1"}` (roles alone). About 20 to 50 minutes each with the real engine.
  Input `bitnet: "1"` runs the BitNet runtime check instead. Runs of different seeds no longer cancel each other.
- Locally (this container has the GGUF models cached and llama-cpp-python in `.venv`):
  - one task: `python -m team "task"`; members by env `AGENT_TEAM_SOLO=2` (`AGENT_TEAM_SOLO_ALONE=1` for alone).
  - a sitting: `AGENT_TEAM_SOLO=2 AGENT_TEAM_SOLO_ALONE=1 .venv/bin/python training/exam.py sit --tasks 16 --seed N --empty-memory`
    (logs in `runs/exam/exam_N/`; about 25 minutes). **This machine cannot reach quotes.toscrape.com or
    books.toscrape.com** (website tasks fail here for that reason; judge them on GitHub).
  - chosen tasks with logs: `.venv/bin/python training/tools/dev_run.py OUT 2 dev_tasks2.json`.
  - tests: `.venv/bin/python -m pytest tests/test_rules.py -q -k members` (3 tests, ~15 s); the BitNet side:
    `tests/test_spawn.py`.
- Long local jobs: use tracked background Bash jobs (`run_in_background`), ≤ 2 h; detached `nohup` jobs die when
  the container restarts. Use `send_later` to wake yourself for GitHub results instead of polling.
- Git: work on `claude/epic-johnson-7ene30`, mirror to `make-it-work`
  (`git push -q origin claude/epic-johnson-7ene30 && git push -q origin claude/epic-johnson-7ene30:make-it-work`);
  workflows are dispatched on `make-it-work`. Open a PR to `main`, subscribe to it, merge it yourself once
  measured. If the commit-signing service answers 503, wait 20 s and retry. If a push is rejected because GitHub
  changed (history was rewritten once), `git reset --soft origin/<branch>` and commit again.

## 5. What to do next, in order

1. **Make the exam harder before more mending** (`training/exam.py`, task makers `m_*`). At 15-16 of 16 the
   exam cannot show progress. Add kinds that are real agentic work and still checkable by code:
   multi-step research (two facts from two sources combined), a program of 30+ lines with tests that must pass,
   a site with several pages to walk (pagination on books.toscrape.com: count all books in a category), editing a
   given file to a spec, a plan of several steps whose result is a file. Keep every check computed by code.
   Then sit 2 fresh seeds three ways to get the new baseline.
2. **The hive improving by itself (his "RSI").** Build a nightly loop on GitHub: read the members' failed tasks
   with their logs (`the-members-own-work`), have the strongest local model propose one change to the members'
   rules (`team/solo.py`: `MEMBER`, `MORE`, `TYPED`, `form()`, failure checks), sit a fresh seed with and without
   it, keep it only if not worse (open a PR with the numbers; you merge). Everything needed exists except the
   proposer and the gate job. Start small: proposals as text in a file, the gate as a workflow.
3. **Operate a website** (the one failure left for members alone on 9012): read run 43417985351's
   `the-members-own-work`, task "operate a website", and mend.
4. **Advise Muse** when its pages land (`git fetch origin hivemind_muse`; `edit-lab/for-hive/*.md`). Its four
   pages of 2026-11-12 were all "pending"; `FOR_MUSE.md` now asks it to read uploaded logs and count causes
   (no compute needed) and to keep questions 3 (BitNet runtime) and 4 (size/budget map).
5. **BitNets** only where it serves the goal: a size/budget map (from Muse) decides whether bigger bodies pay.

## 6. Things that went wrong, so they are not repeated

- Comparing equal minutes between nets of different sizes (use equal work: block-steps).
- Trusting a win without a control arm (five-level weights; the grown net at 20 minutes).
- Reading GitHub numbers without checking which engine ran (the whole fallback story).
- Accepting typed answers, DONE parsed as code, values compared as written, a 404 page or an empty file as an
  answer, a look at raw data as the answer: all now caught in `team/solo.py`; tests in `tests/test_rules.py`.
- The library of solved tasks (`memory/solved.jsonl`) made members copy old values: off unless `HIVE_LIBRARY=1`.
- Force-pushing `main` from this session is refused by its permission check; ask Arnav if it is ever needed.

## 7. Map of the files that matter

- `team/solo.py` the members form (the default first pass); `team/__main__.py` runs it when `AGENT_TEAM_SOLO` is
  set; `team/hive.py` the roles; `team/llm.py` engines (GGUF vs fallback); `team/config.py` model roster;
  `team/bitnet.py` the 2.4B BitNet client (parked).
- `training/exam.py` the exam (task makers, checks, `sit`, `practice`); `training/exam_record.py` the daily line.
- `.github/workflows/exam.yml` (daily 09:43 UTC on main; inputs above), `ask.yml` ("Ask the hive", members "2"
  by default), `hive.yml` (the growing hive's turn, daily), `practice.yml` (by hand only);
  `.github/actions/hive/action.yml` installs the hive on a runner.
- `training/scratch.py`, `training/body.py` the BitNet cells and bodies; `training/experiments/*.py` the
  experiments with their `*_result.json`.
- `HANDOFF.md` full history (newest first); `FOR_MUSE.md` advice to Muse; `NEW_SESSION.md` environment setup.
