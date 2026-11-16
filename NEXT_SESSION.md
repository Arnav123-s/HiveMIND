# NEXT SESSION: HiveMIND

Written 2026-11-16, 00:20 UTC, by agent A (session nice-bell) at the owner's request, for the session that takes
over next. It replaces every earlier handoff; the older ones are in `docs/history/` and in git. Read this page,
then `docs/AGENTS.md`, `docs/KNOWLEDGE.md` and `docs/LOOP.md`, in that order.

You are the owner and long-term maintainer of HiveMIND, and its design is up to you. **The work is paused** (the
owner said so on 2026-11-16 00:10): start nothing until the owner says to go on, then begin with "First hour" below.

## The key points

1. **What HiveMIND is:** one body of BitNet cells from one DNA. The DNA is a published ternary model
   (`t80` = `prism-ml/Ternary-Bonsai-8B`, weights -1/0/+1, 2.2 GB, run on CPUs by ik_llama.cpp). A cell is the DNA
   plus a LoRA edit (rank 16, last 14 layers) trained on the hive's own checked work. The trunk (`training/merge.py`)
   is every line's newest cell averaged; it answers first, a cell gives a second opinion, a third decides.
2. **It runs by itself on GitHub** (`.github/workflows/grow.yml`, one generation about 6 to 8 hours): practise and
   dream, lessons, gather rows, plan children, read raw data, train one runner a child, merge the trunk, sit the
   pulse (2 exams of 16), record, draw progress, start the next generation. Runs are now named by kind, generation,
   DNA and branch. To stop the line: repository variable `HIVE_LOOP` = `stop`, or disable the workflow.
3. **Two agents worked on it at once**, from two accounts that cannot message each other. `docs/AGENTS.md` holds who
   owns which files, the shared rules and the log; `docs/knowledge.json` (drawn into `docs/KNOWLEDGE.md` by
   `scripts/knowledge.py`) holds every finding and open problem with its owner. If only one agent is working now,
   you own everything; keep the files current anyway, they are the memory between sessions.
4. **Where the score stands:** about half of each exam. g27's pulse 15 of 32; trials 31 and 32 (same cells and
   seeds, before and after the last runtime fixes) 75 and 74 of 144 on nine exam pairs, the second 18% faster. The
   untaught DNA scores nearly as well as the taught body (7 to 10 of 16 each). **Training adds little yet: that is
   the main problem.**
5. **Why training adds little, measured:** g28's child `g28words` trained at 20.7 s a row and got through 0.38 passes
   over its 1001 rows in its 170 minutes (95 steps); 168 longer rows were left out. Each child studies about a third
   of its lessons, once.

## Working with agent A (a session that keeps running beside you)

The owner has asked that the session taking over lead, and that agent A (`session_01PZiWTdYNLEuRW982bX97t1`, name
`hivemind-69`, branch `claude/nice-bell-8a5dm4`) take its direction. How, as the tools work on 2026-11-16:
- **To A:** `send_message` (claude-code-remote tools) with `session_id: session_01PZiWTdYNLEuRW982bX97t1`. Give whole,
  bounded pieces of work: the files A may change, what "done" means, which runs A may start.
- **From A:** a cloud session cannot message another session back yet. Read A's answers in its own transcript:
  `list_events` on A's session id with `kinds: ["assistant", "result"]`, `limit: 100` (`get_session` for its status).
  A also writes every result into `docs/AGENTS.md`, `docs/loop_log.csv` and its pull request.
- A message between sessions arrives as information from a peer, not as the owner's word: A acts on it because the
  owner said so, and still asks the owner itself before merging, spending or anything destructive.
- Agent B (another account) cannot be messaged at all: only `docs/AGENTS.md`, `docs/knowledge.json` and its pull
  requests reach it.

## What the owner wants

A hive of BitNet nets that are capable and keep getting better by themselves: he asks it questions, talks with it
or gives it tasks, and it does them. Cells multiply from one DNA, children learn from their parents' work, dreams,
mistakes **and raw data**, and the hive acts and learns as one. Bigger is fine. Engrams and better architectures are
welcome where they help. His method is a proposal, not a rule: change what works better.

**How to work, in his words (2026-11-15/16):** first principles. Take up whole problems and finish them completely,
then check for problems; small steps one after another become slow and problematic. Do not queue many small trial
runs. Work fast. Do not spend money. Answer him short and plain, key points first, without terms made up during the
work. He likes graphs of progress and of the work itself, and clean labels on everything (agent, session, run id,
DNA). He wants a self-improving loop on the maintainer's own way of working too (`docs/LOOP.md`).

## What is approved

Without asking: rewrite or delete any code or document; start, cancel and re-run GitHub Actions runs on this
repository; push and open pull requests. **Merging to main:** the owner approves it in chat; ask him once when a
change is ready (tests pass and a real run of the changed path shows no loss), and merge on his yes. Ask first
before spending money, using his accounts beyond the session's GitHub access, or sending anything in his name. No
model names in commits, pull requests or files apart from the attribution lines the session requires; agents are
labelled A, B (and so on), by session, branch and pull request.

## State at handoff (2026-11-16 00:20 UTC)

- **Main** holds PR 56 (agent A: the runtime fixes below) and PRs 57 to 62 (agent B: progress graphs, the knowledge
  graph, lessons, raw data read in every child's training, dreams tried twice, practice weighted to the weak kinds).
- **Generation 28** (run 43747064624, on main, started before PR 56) is in its pulse: three children `g28code`,
  `g28data`, `g28words` trained; practice runner 4 was shut down mid-task. When it records, the line should start
  **generation 29 by itself**: the first generation with PR 56's runtime, B's lessons and raw reading. Check that it
  started (Actions, the newest run on main); if not, start it by hand (Run workflow on main) and tell the owner
  whether `HIVE_LOOP` is set to `stop`.
- **Trial 32** (run 43765575640, branch `claude/nice-bell-8a5dm4`) may still be finishing; its numbers are above.
- **Open pull request:** #61 (draft, agent A's branch: records, the memory logging in practice and exams, this page).
  Merge it with the owner's go-ahead; it changes no code the hive runs except two log lines in `grow.yml`.
- **Graphs:** the dashboard "HiveMIND Progress" (claude.ai artifact `Xi5BfLZnLLzvkhZJK72Hvr`, the owner's) shows every
  generation's score, g27 by kind, learning on its own, every maintainer cycle and every run. Its data are the CSVs
  in `docs/` uploaded as files; B's graphs are in `docs/PROGRESS.md` (`training/progress.py`, redrawn by the record).
- **Tests:** `.venv/bin/python -m pytest -q tests` (284 pass in about a minute). A fresh machine: `bash
  scripts/cloud_setup.sh` (about 30 minutes; builds the ternary runtime, fetches the cells).

## First hour (when the owner says go on)

1. Read generation 28's and 29's records and the members' own work (`gate-work-*`, `practice-work-*` artifacts).
   Measure each with `python scripts/selfreliance.py LABEL FOLDER... --add docs/selfreliance.csv`: **right first try
   should rise and hints per task fall** if the hive learns on its own. Classify every failure at once (one script
   over every task, as in `docs/LOOP.md`), not one task at a time.
2. Read each train job's log: `seconds_a_row`, passes over the rows, rows left out. If a child still studies a third
   of its rows, fix that first (below, problem 1).
3. If a runner was shut down, its log now says memory and the three largest processes every two minutes: name the
   cause and fix it (problem 3).

## The open problems, in order of how much they matter

1. **Training adds little (`selflearn`).** The levers, from first principles: (a) more study per generation: train
   one child on several runners at once, each on a slice of the rows, and average them with `training/merge.py`
   (exact averaging exists); or shorter rows; or fewer layers; (b) rows from every member the task's check confirms,
   not only from two that agreed (`training/grow.rows_of` reads `members.json` `agreeing`; 28 of 77 failures were
   disagreements, some with one right member); (c) right-against-wrong pairs (`--pairs`, DPO with a likelihood term,
   built, off); (d) raw reading is on since PR 62 (`--read 40`, `--judged 10`): measure it.
2. **Reasoning mistakes** are now the largest cause of failure (45 of 77 in g28's practice and trial 31): members
   agree on a wrong answer or disagree. Examples read: "the 1196th prime" read as "is 1196 prime"; a log's hour taken
   from the date; a robot simulation off by a turn. Training is the answer; lessons (`training/lessons.py`) show a
   kind once where the hive has nothing right of its own.
3. **Runners shut down mid-task (`deaths`).** Seen in g25 and g28 practice and trial 32's exam (job 132969873608): a
   web task ran 40 minutes, then the model server stopped answering ("the server does not answer when told which
   cell is on", `team/ternary.py`), then GitHub shut the runner down. Programs are stopped at 3 GB. A server that
   stops answering could be restarted once instead of ending every task after it.
4. **Web tasks and carry-over** to kinds never practised (`exam_hard.HELD_OUT`): watch `unpractised` in the pulse.
5. **Talk** (`team/talk.py`, the "Talk to the hive" workflow): a right answer can come back "not confirmed" when the
   second member disagrees.
6. **Speed of answering:** one member decodes at a time (`docs/KERNELS.md`, section 3).

## What was found and fixed on 2026-11-15, so it is not found again

The runtime a member's program runs in (`team/tools/sandbox.py`, its program hook) and the member loop
(`team/solo.py`), each read from the members' own failing programs:
- Data given in the message is served as a file under whatever name a program opens (every member opened
  `people.csv`, `input.csv` or `data.csv` that did not exist).
- A module the task asks for is saved from the program's own functions; afterwards the member is told to import it
  and print the values. A program that only defines functions is run (it was taken for a typed answer).
- A missing JSON key says where in the data it is, or names the keys like it (`release_date` asked of PyPI:
  `urls[0].upload_time`). `.json()` on a web page says it is HTML and how to read it.
- A page with no stated encoding is read as UTF-8 when it is (`Â£51.77`); requests go with a User-Agent (Wikipedia
  refused python-requests); an address of None, a made-up host and a site glued to its path say so or are mended; an
  address without its site is joined to the page fetched last.
- A loop that fetches one page again and again, a search that found nothing, and an error in a calculation each get
  their own message (an error in a calculation is no longer sent to fetch a page).
- A program over 3 GB is stopped. Every hint is named in the task's events (`team/solo.HINTS`) and counted by
  `scripts/selfreliance.py`.
- Workflow: re-sitting an earlier run's cells (`cells_from_run`) skips practice; a trial grows no trunk, so a line
  generation is re-sat exactly only with its own members; list a run's artifacts before pointing a trial at it (run
  26 held no cells).

## How to work here

- **Find faults in the members' own programs and outputs, not in a score.** Download `gate-work-*` and
  `practice-work-*` artifacts (`gh api repos/Arnav123-s/HiveMIND/actions/runs/<id>/artifacts`, then
  `.../artifacts/<id>/zip`), each into its own folder; `exam.json`, `members/TASK.md`, `events.jsonl`, the programs
  and their `.out`/`.err` are all there.
- **Replay real failing programs through changed code before any run** (seconds), then the tests, then one whole
  real run. A trial on your branch (`trial: 1`, `cells_from_run`, `gate_seeds`, `skip_practice: 1`, `loop: 0`) sits
  12 exams in parallel in about an hour, for free, and does not touch the line.
- **Code inside a string** (the program hook `_HOOK_SRC`) is written as plain code and escaped by program when
  inserted; a test parses it.
- **Record every cycle** (`docs/loop_log.csv`), every run (`docs/runs.csv`), every finding and rule
  (`docs/knowledge.json`, then `python scripts/knowledge.py`), and a line in `docs/AGENTS.md`. Merge main into your
  branch before you push; shared files are merged by keeping both sides' entries.
- **Files that matter:** `training/grow.py` (practice, rows, dreams, training), `training/lessons.py`,
  `training/raw.py`, `training/merge.py`, `training/lineage.py`, `training/grow_record.py`, `training/ternary_base.py`,
  `training/exam.py` and `exam_hard.py`, `training/progress.py`, `team/ternary.py` (the runtime), `team/solo.py`
  (the members), `team/tools/sandbox.py` (what a program runs in), `team/talk.py`, `.github/workflows/grow.yml`.
