# agent-team

A team of small AI specialists that works as one. You give it **one prompt**; it breaks the job down,
assigns the pieces, checks every result against its evidence, retries what fails, and hands back the
finished work with sources. It does research from live sources, real browser work (clicking, typing,
navigating websites), and writes and runs code.

Every specialist is a small open-weight model that runs on a CPU: no GPU, no VRAM, under 16 GB RAM,
no API keys, no accounts, nothing to pay for. Each specialist has its own weights: I observed every one
on held-out tasks, wrote training data aimed at what it got wrong, and edited its weights on CPU
(details and before/after numbers below).

## The team

| specialist | brain (all Apache-2.0, run on CPU) | job | tools |
|---|---|---|---|
| **coordinator** | Qwen3-4B, 4-bit | turns your prompt into a plan of assigned steps, fans steps out over lists | the shared board |
| **researcher** | Qwen3-4B, 4-bit | picks live sources and queries, reads them, returns facts with exact quotes | Hugging Face, Hacker News, arXiv, PyPI, Wikipedia, any URL |
| **browser** | Qwen3-1.7B + **its own weight edit** | drives a real Chromium: opens pages, types in search boxes, clicks links/tabs, reads what is shown | Playwright browser |
| **coder** | Qwen2.5-Coder-7B, 4-bit | writes Python, runs it, reads errors, fixes it; sees real samples of the data first | Python sandbox, data preview |
| **verifier** | Qwen3-1.7B + **its own weight edit** | checks every result before anyone relies on it | hard checks + judgment |
| **writer** | Qwen3-1.7B + **its own weight edit** | writes the finished deliverable from verified results only, with numbered sources | the shared board |

Quality control, also specialists in the hive:

| specialist | brain | job |
|---|---|---|
| **plan reviewer** | Qwen3-4B | second look at every plan: uncovered deliverables, wrong specialist, missing fan-out → coordinator re-plans |
| **condenser** | Qwen3-1.7B | picks the lines of a long source that matter for the task; extractive, so quotes stay exact |
| **jury** | verifier (1.7B + edit), Qwen3-4B, Qwen3-1.7B | every step verdict is a majority vote of three different models |
| **critic** | Qwen3-4B | checks the final report claim by claim against the verified results; the writer fixes what it flags |

Specialists that improve the specialists (evolution harness, `python -m team evolve <role>`):

| specialist | brain | job |
|---|---|---|
| **examiner** | Qwen3-4B | turns failures (held-out cases and real run steps) into one-line diagnoses |
| **prompt-smith** | Qwen3-4B | breeds variants of a specialist's instructions aimed at those diagnoses |
| **trainer** | (CPU LoRA) | retrains a 1.7B specialist's weight edit from its own verified work (`dream`) |
| **selector** | (code) | scores parent and variants on held-out evals; promotes only a strict improvement; logs lineage |
| **lesson writer** | Qwen3-1.7B | turns each verified failure into a rule the team reads next time (`dream`) |

Adding a specialist is one line in `team/config.py` (role → brain, optionally `+edit`) plus its prompt:
on a shared base it costs a few MB, not GB.

Which brain each role gets was decided by measurement, not by guess: every role was scored on held-out
tasks with each candidate (1.7B base, 1.7B + its edit, 4B, 1.5B/7B coder), and it gets the best one;
ties go to the faster model. Table under "How the specialists were improved".

**Engine.** llama.cpp with 4-bit/8-bit weights (`team/llm.py`):
- the three 1.7B specialists share **one** copy of the base weights; each one's edit (a few MB) is
  hot-swapped in per call
- at most 2 models are resident at once; the least recently used is unloaded (reload: ~4 s)
- JSON replies are constrained by a grammar, so they are valid JSON by construction
- measured on this 4-core CPU: Qwen3-4B 7.6 tok/s using 3.9 GB, the shared 1.7B with three edits 3.3 GB,
  Qwen2.5-Coder-7B 4.8 tok/s; peak for the whole team about 10 GB with the browser
- the PyTorch engine (`AGENT_TEAM_ENGINE=hf`) is kept: it is what trains and scores weight edits

## How it works as one

```
your prompt
   │
   ▼
guard ── family/relationships? → refused
   │
coordinator → plan: s1 researcher → s2 browser (for each item of s1) → s3 coder → s4 writer
   │
   ▼            ┌────────────── shared board (hive memory) ──────────────┐
for each step:  │ steps, results, facts + source URL + exact quote,      │
  specialist ──►│ files, approvals, event log; each specialist reads the │
  verifier   ──►│ verified results of the steps it depends on            │
  retry with    └────────────────────────────────────────────────────────┘
  feedback (×2)
   │
writer → REPORT.md (sources numbered, gaps listed under "Not confirmed")
```

- **Shared board** (`team/board.py`): one SQLite file per run. Nobody works from a private copy.
- **Verification is not optional.** Facts are rejected unless their quote is literally in the source
  the team read. Browser answers are rejected unless the evidence is literally on the page. Code is
  rejected unless it exits 0 and creates the files the task asked for. Then the verifier model judges
  whether the evidence meets the step's check.
- **Failures are fed back.** A rejected step is retried with the verifier's reason, up to twice. If it
  still fails, the coordinator re-routes it to a different specialist (e.g. a website that will not load
  → the researcher reads the site's API). What still fails is listed in the report, never papered over.
- **Every run leaves a trace** in `runs/<timestamp>/`: `TASK.md`, `plan.json`, `board.db`,
  `events.jsonl`, `calls.jsonl` (every model call), `screens/` (browser screenshots), `work/` (code and
  files), `TRACE.md`, `REPORT.md`.

## Many small specialists working as one

The bigger members do what needs generation (planning, extracting claims with quotes, writing code and reports); every
judgement around them is split into the smallest jobs, each with its own specialist: a **cell** (a 135M model with its
own small weight delta, `team/cells/`), a code rule where a rule is exact, or a member. A cell takes a job only where
it measured at least as well as what did the job before (`cells/wins.json`).

**Research hive** (`team/specialists/research_hive.py`): a research question ("research ...", "compare ...", "how does
...", "run an experiment ...", "prove ...", several questions at once) is not one look-up. Research is reading, and
also testing, measuring, simulating and doing the math:

```
question ─ decomposer (4B): 2-4 sub-questions, each with how it is answered: read, experiment or math
   read:        planner (sources, queries) ─ search ─ relevance check on every result ─ reader (whole arXiv papers
                when arXiv has the HTML version) + condenser ─ extractor (claims with exact quotes)
   experiment / math: the coder writes and runs one program (fixed seed; numpy, sympy, pandas, networkx, matplotlib)
                that prints its METHOD and each RESULT; every RESULT line is a claim whose evidence is the program's
                own output, and the jury sees the program
   gap-finder cell: does any claim answer each sub-question? a gap gets one more search, other words
   cross-check: two sources on the same point - agree, conflict or unrelated? conflicts are listed
   verifier: every claim against its quote or output ─ writer: findings, method, disagreements, open questions
```

The research cells, measured on the same test inputs (`training/reports/cells/`):

| job | cell (135M, as served) | without the cell | the 4B member | used |
|---|---|---|---|---|
| does a claim answer its sub-question (gap finder) | **0.933**, 81 ms | 0.500 (any claim counts) | 0.840, 1.8 s | cell |
| is a search result about the question | 1.000, 70 ms | 1.000 (word overlap), 1 ms | 0.753, 1.8 s | word rule (a tie; the test data has no paraphrases) |
| do two sources agree or conflict (cross-check) | **0.953**, 92 ms | none (no cross-check) | 0.853, 2.1 s | cell |

**Long projects** (`team/project.py`): a goal too big for one job ("build me an app ...", "a research study on ...",
anything over days) becomes 3-12 milestones, each a deliverable with how to check it, run one after another as jobs in
the project's own workspace: files accumulate across milestones and days, and every job sees the work so far. A
milestone still undone after its attempts blocks the project with the reason. Progress is saved after every milestone,
so a restart or the device turning off resumes it; the always-on agent works on open projects whenever it is idle.
In a conversation, "build me ..." starts one and "how is it going?" is answered from its progress.
`python -m team project "goal"`, `python -m team projects`, `POST/GET /v1/projects`.

**Coding hive** (`team/specialists/coder.py`): the coder sees a preview of the real data first (the site its task
names, the page the task points at, whether a listing has more pages); an error reader names the kind of each
failure (syntax, import, network, file, data, timeout) and tells the coder what that kind needs; examples you give in
the task ("fib(1) = 1") are run against the program's own functions; a program that prints nothing goes back; the code
reviewer reads it; the jury sees the program, its output and every file it saved; a fix that changes nothing stops.

**Many cells at once** (`team/cells/pool.py`): worker processes, one CPU thread each, sharing the memory-mapped base:
a batch of cell questions (every search result, every fact, every pair of claims, every line of a page) is answered in
parallel. Its first measurement was a failure: 160 questions took 9.8 s with no pool and 728 s with 2 workers, because
llama-cpp-python reads prompts on every core unless told otherwise, so the workers fought over the cores (fixed), and
workers of a killed run kept computing (they now exit with their parent). Measured again after the fix
(`training/cells_pool_bench.py`, training/reports/cells/pool.json): 160 questions in 9.5 s with no pool, 7.9 s with 2
workers (+1.0 GB), 7.7 s with 4 (+2.8 GB). Cells answer in about 0.1 s and a task asks 3 to 19 of them, so 2 workers
save about a second a task for a gigabyte of RAM: it stays off (`AGENT_TEAM_CELL_WORKERS=1`); set 2 on a machine with
RAM to spare and many cell questions per task.

**The hive grows new cells from its own work** (`team/cells/learn.py`, `python -m team grow`): the verifier's claim
checks, the juror's item checks and the condenser's line choices are logged with their inputs
(`memory/decisions/`). When a kind of decision has enough examples, a cell is trained on them with the member as the
teacher (oldest 70% to train, next 15% to choose, newest 15% to judge), and it answers only from the confidence at which
it agreed with the member at least 97% of the time; the member answers the rest, and those answers keep being logged,
so the next `grow` learns from newer work. The always-on agent runs `grow` by itself when the device is idle. Tests
and bench runs use a throwaway memory, so they never teach the hive.

## Just talk to it: `hive`

One prompt, then a normal conversation, the way you talk to an assistant. It decides the rest.

```bash
./hive "Find the three cheapest Mystery books on books.toscrape.com and save them to a CSV"
```

You see the hive work (plan, each specialist's step, each check), then the answer, the files it made and the run
folder, and then you keep talking:

```
you> thanks! why those three?          answered at once from what was found (no job)
you> now add their star ratings        a new job, with the conversation as context
you> remember that I prefer prices in INR     saved; every report follows it
you> stop                              the kill switch: every running job halts
```

Each message is answered directly when the conversation already holds the answer, or becomes a hive job (anything to
look up, a website, code, files, a calculation, writing, a fact that must be right) that runs until nothing is left
undone (`team/converse.py`). Your words are the order: what they order (buy, delete, send, log in, sign up) is approved
by the order itself; anything risky they do not order stops and asks you. `./hive` alone starts the conversation
without a prompt; `--once` answers one prompt and exits (scripts). Ctrl+C is the kill switch, `exit` leaves.

When the always-on agent runs (next section), the conversation goes to it: the models are already loaded there and a
job keeps running if you close the terminal. Chat apps on the API get the same conversation.

## Always on: your personal agent

```bash
python -m team install
```
starts HiveMIND with the device and keeps it running: a systemd user service on Linux (to start before you log in,
also run `loginctl enable-linger $USER` once), a launchd agent on macOS, a logon task on Windows. It restarts after a
crash. `python -m team install --dry-run` shows exactly what it writes and runs; `python -m team uninstall` stops it
and removes only that entry. Without installing: `python -m team serve`.

It is reachable while the device is on:
- `hive "prompt"` from any terminal
- the chat page at http://127.0.0.1:8766 (shows the hive working live)
- the API at http://127.0.0.1:8766/v1 for any OpenAI- or Anthropic-compatible app (next section)
- the inbox: drop a `.md`/`.txt` file into `inbox/` (or `python -m team add "task"`); the report lands in `outbox/`
- the schedule: recurring tasks in `memory/schedule.json`, e.g. `[{"task": "...", "every_hours": 24}]`

**It does not harm the device** (`team/health.py`, `team/service.py`):
- it runs at low priority (nice 10, idle IO); models use every core but one; on Linux, systemd also caps it at half
  the machine's CPU time and 10 GB of RAM
- after 10 minutes without a job every model is unloaded, so the RAM goes back to you
- heavy background work (dreaming, growing cells) runs only when the device is plugged in, the CPU is under 75 C and
  not busy with your own programs, and there are 3 GB of RAM and 2 GB of disk to spare
- between model calls, a CPU above 90 C waits until it is under 80 C
- when less than 1 GB of disk is free, new jobs are refused with the reason; nothing is ever deleted to make room
- only one service runs at a time; it never keeps the device awake

Other ways in:

```bash
python -m team "your task"            # one round in this terminal (the original command)
python -m team chat                   # small talk handled directly, tasks go to the hive
python -m team remember "Prices in INR. Short answers, table first."   # every report follows it
```

## Use it like Claude, ChatGPT or Codex: hand over a task and leave it (`team/sdk.py`, `team/api.py`)

Unattended: nobody is asked anything. Risky actions (spend, delete, send, log in, sign up) happen only where your task
orders them; anything else is not done and listed in the report. `until_done` adds follow-up rounds: whatever the
critic marked not done, and any step the team could not confirm, goes back to the swarm (your task stays the only
order; the earlier answer is context). The job's report is the round with the least left undone.

```bash
python -m team "Find the three cheapest Mystery books on books.toscrape.com and save them to a CSV" --approve never --until-done 2
```

Python:

```python
from team.sdk import Swarm
job = Swarm().submit("What licence does Qwen/Qwen3-1.7B use?", until_done=2)
for ev in job.events(follow=True):      # live progress
    print(ev["agent"], ev["msg"])
print(job.report, job.files, job.unmet)  # deliverable, files made, anything still undone
```

As an API that the OpenAI and Anthropic SDKs, and apps that let you set a base URL, can use (model `hivemind`):

```bash
python -m team api
```
(http://127.0.0.1:8766; set `AGENT_TEAM_API_KEY` to require a key; `--until-done 2` makes follow-up rounds the default)
`--workers 2` runs two jobs at once in one process: they share the loaded models and take turns on the CPU for model
calls, so one job's waiting (web pages, the browser, a program running) is the other's compute. The kill switch still
stops every running job. Measured (`training/workers_bench.py`, training/reports/workers.json; a lookup, a calculation
and a short draft): 196 s against 205 s one at a time (4% faster), peak memory 11.1 GB against 8.9 GB. On a CPU the
models already use every core, so jobs mostly take turns: the default stays one job at a time.

| endpoint | for |
|---|---|
| `POST /v1/chat/completions`, `GET /v1/models` | OpenAI SDK, chat apps with an "OpenAI-compatible" setting |
| `POST /v1/responses` | newer OpenAI clients (Responses API) |
| `POST /v1/messages` | Anthropic SDK |
| `POST /v1/jobs`, `GET /v1/jobs/<id>`, `GET /v1/jobs/<id>/events`, `POST /v1/stop` | submit and leave; follow live; kill switch |

```python
from openai import OpenAI
c = OpenAI(base_url="http://127.0.0.1:8766/v1", api_key="local", timeout=3600)
for ch in c.chat.completions.create(model="hivemind", stream=True,
                                     messages=[{"role": "user", "content": "Summarise this in one sentence: ..."}]):
    print(ch.choices[0].delta.content or "", end="")
```

A task takes minutes on a CPU, so stream (progress arrives while the swarm works and keeps the connection open) or use
the jobs API. The latest user message is the task; earlier messages are context for the planner and writer, never
orders; a client's system prompt is not used. Checked with the official `openai` (chat, streaming, Responses) and
`anthropic` (messages, streaming) Python SDKs against a stand-in hive: `python training/api_clients_check.py`.
Not tested here: specific apps (Open WebUI, Codex CLI, Hermes Agent, Claude Code). They talk to the same endpoints, but
an agent app that expects the model to call its own tools gets a finished report back, not tool calls.

## Your rules: everything risky happens only under your explicit order (`team/guard.py`)

**Your order is the approval.** Risky kinds of action: spending money, deleting, sending a message as you,
logging in, signing up, using your credentials, and family/relationship matters. The team does one only when
your task orders it, and only as ordered. Every approval in the log quotes the sentence of yours it relied on.
Anything you did not order stops: in the terminal it asks you (`y/N`); in `serve`/`web` it is not done and is
listed in the report as waiting for you.

| your task says | what the team may do |
|---|---|
| "Buy 'Soumission' on books.toscrape.com" | add it to the basket and check out on that site |
| "Find the price of a book" | read prices; any buy/checkout button stops and asks (a noun is not an order) |
| "No paying, no accounts" | nothing risky; negations are never orders |
| "Log in to quotes.toscrape.com and list my quotes" | log in there with your vault credentials; anywhere else, refused |
| "Plan my wife's birthday dinner and book a table" | family matters for this task, and booking (spend) |
| a step that drifts into something you did not mention | dropped before it runs |

**Two readers must agree.** What you ordered is read twice, independently: a rule-based parser (verbs in
command position; negations, nouns and terms like "text-generation" excluded) and the order-reader member
(the 1.7B base with its own weight edit). A risky kind counts as ordered only if both say so; a disagreement
is logged and the kind is treated as not ordered (it asks you). Measured on 63 held-out sentences:
parser alone 1.00 exact, 0 false approvals; order reader 0.51 → 0.73 exact after its
weight edit; both-must-agree 0.71 → 0.87 exact with **0 false approvals** (`training/reports/orders_*.json`).

**Everything you ordered, nothing else.** Your task is turned into a checklist of your instructions, in your
own words (items that are not grounded in your text are dropped). The plan reviewer checks that the plan
covers every instruction and adds nothing you did not order; the critic checks the finished report, and the
report ends with "Your instructions" ✅/❌ and a "Done without your order" section if anything was.

**Standing orders.** `memory/policy.json`: `{"spend": "ask", "delete": "allow", "send": "ask"}` (`ask`,
`allow` or `deny`) for kinds you want permanently allowed or banned.

**Your credentials.** Kept in `~/.agent-team/credentials.json` on your machine (`chmod 600`), never in the repo:
```json
{"quotes.toscrape.com": {"username": "you", "password": "..."}}
```
When your task orders a login on that site, the browser's `login` action fills the form from the vault itself.
Models never type passwords or card numbers; the values never enter a prompt, the board, a log or a trace.
`--allow-login SITE` grants a login for one run from the command line.

## Kill switch: stop everything, now (`team/stop.py`)

| from | how |
|---|---|
| the terminal running the task | **Ctrl+C** (a second Ctrl+C exits at once) |
| any other terminal | `python -m team stop` |
| the web page | the red **Stop** button |
| serve mode | drop a file named `STOP` into `inbox/` |

All of them set one flag that every specialist checks: the models between every generated token, the browser
before every action, the coder's program is killed with its whole process group, and the hive between steps.
Nothing runs after it. The run folder gets `STOPPED.md` (what finished, what was cut off, what never started)
and `TRACE.md`; the flag is moved into the run folder as a record. Tested: `tests/test_rules.py` (running code
and its child processes die within a second; model calls refuse to start) and `training/test_kill_switch.sh`
(a real task stopped mid-run).

## How the specialists were improved

Every number here is a measurement on held-out cases (`training/evals/`, none of them in any training data), produced by `training/observe.py`; per-case outputs are in `training/reports/<tag>.json`. Evals are small (3-18 cases), so treat single-case differences as noise.

**1. Observe.** Each specialist ran its held-out cases on the base model. What failed, and the design fix:
- browser invented URLs and missed targets buried in page chrome → it now sees the page lines that match its goal and the 40 most relevant elements (rare goal words weigh more); navigation errors come back as a reason, not a crash
- coder guessed HTML classes and JSON keys blind and imported unrelated packages → it gets a real preview of every URL/file in its task, and is told when a file it should have made is missing
- small models kept talking after the answer → decoding stops when the JSON object or code block closes; on llama.cpp, JSON is grammar-constrained so it is always valid
- Hugging Face search matched descriptive words against model names → the tool strips them; PyPI needs an exact name → the tool tries each word
- "for each" without fan-out → the plan is repaired; a step that fails 3 times is re-routed to a different specialist

**2. Edit the weights.** For each 1.7B specialist I wrote training data aimed at its failures (`training/build_*.py`: hand-written plans; expert browser runs recorded on live sites; live Hugging Face / PyPI / Hacker News / arXiv / quotes pages; true and perturbed claims) and trained a weight delta W' = W + (α/r)·B·A on the top 14 of 28 transformer layers, all 7 projection matrices per layer, on CPU, loss on the reply tokens only. Exact tensors changed: `training/reports/weights_<specialist>.md`.

| edit | examples | layers | rank | epochs | train loss start → end | CPU time | kept? |
|---|---|---|---|---|---|---|---|
| coordinator | 38 | 14-27 | 16 | 3.0 | 2.69 → 0.30 | 7 min | no: 0.79 vs 0.94 without it (learned 2-step plans) |
| researcher | 71 | 14-27 | 16 | 2.0 | 0.87 → 0.06 | 10 min | no: extraction 0.57 vs 0.77 (looped, broke JSON) |
| browser | 107 | 14-27 | 16 | 2.0 | 1.44 → 0.03 | 39 min | yes: 0.79 vs 0.43 |
| verifier | 225 | 14-27 | 8 | 1.0 | 5.06 → 0.01 | 5 min | yes: 0.89 vs 0.83 |
| writer | 13 | 14-27 | 8 | 3.0 | 2.86 → 0.42 | 2 min | yes: tie 0.88, faster model |

**3. Bigger brains for the same RAM.** A second engine (llama.cpp, 4-bit) runs a 4B model in about the RAM and speed the 1.7B needed in PyTorch (measured, this 4-core CPU):

| engine | model | tokens/s | RAM it allocates | + mapped weights (evictable) |
|---|---|---|---|---|
| llama.cpp | Qwen3-4B 4-bit | 7.6 | 3.87 GB | 2.66 GB |
| PyTorch | Qwen3-1.7B bf16 | 8.4 | 0.58 GB | 3.67 GB |

**4. Pick each role's brain by score.** Same held-out cases, every candidate:

| eval (held out) | cases | 1.7B base, first design | 1.7B base, improved design | 1.7B + own edit (PyTorch) | 1.7B 8-bit + own edit (llama.cpp) | 4B 4-bit / coder 7B 4-bit | in the team now |
|---|---|---|---|---|---|---|---|
| coordinator | 14 | 0.94 | - | 0.79 | - | 1.00 | 4B |
| researcher_plan | 10 | 0.95 | - | 0.97 | - | 1.00 | 4B |
| researcher_extract | 5 | 0.77 | - | 0.57 | - | 0.80 | 4B |
| verifier | 18 | 0.83 | - | 0.89 | 0.89 | 0.89 | 1.7B + edit |
| writer | 3 | 0.88 | - | 0.88 | 1.00 | 1.00 | 1.7B + edit |
| browser | 14 | 0.36 | 0.43 | 0.79 | 0.71 | 0.43 | 1.7B + edit |
| browser_live | 4 | 0.50 | - | 0.75 | 0.75 | 0.50 | 1.7B + edit |
| coder | 8 | 0.50 | - | - | - | 0.88 | coder 7B |

Rule: a candidate replaces the current one only if it scores at least as well; ties go to the faster model. Rejected edits are kept in `adapters/.rejected/` for the record.

<!-- cells:start -->
## Cells: one tiny model per smallest skill (`team/cells/`, `training/cells*.py`)

Every smallest job in the hive is its own specialist, a **cell**. A cell is trained for one micro-skill only (is a purchase ordered? which specialist takes this step? does this quote state this claim? retry, reroute or give up?) and is allowed to be bad at everything else: other cells cover that. All cells share **one** frozen SmolLM2-135M (144 MB at 8-bit) in RAM; each cell owns only a small weight delta, hot-swapped per call in llama.cpp. A label cell answers through a grammar that only allows its labels.

**19 cells**, 12.4M edited parameters in total, 50 MB of deltas on one 144 MB base.

### Measured: each cell against what does that job today

Test inputs use other words, frames and sites than training. The winner per skill is chosen on a dev split built from **held-out training words** (a dev split with the training words scored 1.0 for every variant and could not pick a winner). `takes the job` = the cell scored at least as well as the incumbent, so the hive now hands it that job (`cells/wins.json`, `team/cells/use.py`).

Each cell = SmolLM2-135M (shared, frozen) + its own weight delta. Scores are on the TEST split (other words, frames, sites than training). Variant columns are the PyTorch test scores of each candidate edit; the winner is chosen on dev. `cell` = the winner served by llama.cpp. The five orders_* cells take the job only together, judged as the guard uses them (the organizer table below), so one of them can lose alone and still say yes here.

| skill | hive part | base | locator pick (r8) | pick r8 + r2 elsewhere | r2 everywhere | random K (r8) | r8 everywhere | winner | params changed | cell (llama.cpp) | ms/call | incumbent | incumbent score | ms/call | takes the job |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| route_step | coordinator: which specialist takes a plan step | 0.19 | 0.99 (263K) | 0.97 (808K) | 0.99 (611K) | - | - | all_r2 | 610,560 | 0.99 | 87 | coordinator = brain4b | 0.9746 | 7094.6 | yes |
| next_move | hive loop: what to do after a failed step | 0.25 | 0.95 (387K) | 0.97 (901K) | 0.88 (611K) | - | - | mlp_r2 | 380,160 | 0.90 | 75 | coordinator = brain4b | 0.5667 | 6449.4 | yes |
| orders_spend | guard: is a 'spend' action ORDERED | 0.31 | 0.89 (304K) | 0.97 (839K) | 0.97 (611K) | - | - | all_r2 | 610,560 | 0.97 | 76 | order_reader = fast+order_reader | 0.918 | 1162.3 | yes |
| split_orders | coordinator: the instruction checklist | 0.01 | 0.81 (209K) | 0.90 (767K) | 0.83 (611K) | - | - | thin | 767,232 | 0.91 | 148 | coordinator = brain4b | 0.28 | 11057.9 | yes |
| json_repair | engine: repair a member's broken JSON | 0.36 | 1.00 (226K) | 1.00 (780K) | 1.00 (611K) | - | - | all_r2 | 610,560 | 1.00 | 155 | code:parse_json | 0.4933 | 0.0 | yes |
| family_topic | guard: does a step touch family/relationships | 0.50 | 0.85 (313K) | 0.75 (846K) | 0.79 (611K) | - | - | all_r2 | 610,560 | 0.80 | 63 | code:guard.FAMILY | 0.875 | 0.0 | yes |
| orders_send | guard: is a 'send' action ORDERED | 0.21 | 0.89 (306K) | 0.89 (840K) | 0.93 (611K) | - | - | thin | 839,808 | 0.89 | 71 | order_reader = fast+order_reader | 0.918 | 0.0 | yes |
| quote_pick | researcher: which sentence is the evidence | 0.17 | 0.62 (319K) | 0.98 (850K) | 0.99 (611K) | 0.67 (290K) | 0.99 (2442K) | thin | 850,176 | 0.97 | 115 | researcher = brain4b | 0.9333 | 7313.7 | yes |
| orders_delete | guard: is a 'delete' action ORDERED | 0.33 | 0.87 (253K) | 0.90 (801K) | 0.95 (611K) | - | - | all_r2 | 610,560 | 0.95 | 77 | order_reader = fast+order_reader | 0.8852 | 0.0 | yes |
| claim_support | verifier: does a quote support a claim | 0.49 | 0.59 (252K) | 0.80 (799K) | 0.83 (611K) | 0.67 (249K) | 0.81 (2442K) | thin | 799,488 | 0.83 | 128 | verifier = fast+verifier | 0.88 | 10270.6 | no |
| orders_login | guard: is a 'login' action ORDERED | 0.15 | 0.93 (280K) | 0.98 (820K) | 0.98 (611K) | - | - | all_r2 | 610,560 | 0.98 | 74 | order_reader = fast+order_reader | 1.0 | 0.0 | yes |
| pick_source | researcher: which search source to query | 0.12 | 0.93 (412K) | 0.88 (919K) | 0.88 (611K) | - | - | pick | 411,648 | 0.93 | 54 | researcher = brain4b | 0.7027 | 6362.5 | yes |
| pick_element | browser: which element to act on | 0.00 | 0.47 (313K) | 0.89 (846K) | 0.93 (611K) | - | - | all_r2 | 610,560 | 0.93 | 116 | browser = fast+browser | 0.88 | 2314.3 | yes |
| orders_signup | guard: is a 'signup' action ORDERED | 0.25 | 0.84 (315K) | 0.93 (847K) | 1.00 (611K) | - | - | thin | 846,720 | 0.92 | 82 | order_reader = fast+order_reader | 0.9836 | 0.0 | yes |
| licence_open | verifier: is a licence open for any use | 0.44 | - | - | - | - | - | clone_orders_spend | 610,560 | 0.74 | 62 | juror_brain = brain4b | 0.9333 | 5087.4 | no |
| gate | the router: which cell (or group of cells) handles an input | 0.11 | 0.91 (281K) | 0.89 (821K) | 0.93 (611K) | - | - | all_r2 | 610,560 | 0.94 | 87 | - | - | - | no |
| orders_any | guard: is ANY risky action ordered (new skill made by the factory) | 0.67 | - | - | - | - | - | clone_route_step | 610,560 | 0.97 | 81 | - | - | - | no |
| element_match | browser: does this one element reach the goal (pick_element's organizer asks it per element) | 0.50 | 0.87 (295K) | 0.99 (832K) | 0.98 (611K) | - | - | thin | 831,744 | 0.99 | 61 | - | - | - | yes |

family_topic as the guard uses it (the rule OR the cell; the cell only adds blocks): 0.875 vs the rule alone 0.875 -> on.

#### pick_element split into a smaller cell plus an organizer

`element_match` answers one question per element (does this element reach the goal?); the organizer asks it about every element on the page and acts on the most likely yes (`runtime.pick_element`).

| reader | test (exact id) | ms per page |
|---|---|---|
| one cell reads the whole list (pick_element) | 0.9267 | 116.5 |
| organizer over element_match | 1.0 | 182.2 |
| incumbent (browser = fast+browser) | 0.88 | - |

#### The five order cells as one organizer (as the guard uses them, 63 held-out tasks)

| reader | exact | false approvals | missed orders |
|---|---|---|---|
| order cells alone | 0.73 | 12 | 6 |
| parser AND order cells | 0.905 | 0 | 6 |
| order reader member (Qwen3-1.7B + edit) alone | 0.73 | 12 | 8 |
| parser AND order reader member | 0.873 | 0 | 8 |


### Finding which part of the model does what (the locator)

Until a trained locator cell exists, I acted as the locator. For each skill, `training/cells.py probe` maps where the skill lives in the base: (1) |W x dL/dW| per module, the first-order loss change if that module moved; (2) a knockout per layer, the loss when one layer's attention or MLP output is removed. I read the maps and wrote my rules down so they are explicit and testable (`training/cells_view.py`, every pick logged with its reason in `training/reports/cells/locator_log.jsonl`, the future locator cell's training data):

- **R1 read**: q and v in the band of layers most sensitive per parameter (layers ~9-17 for every skill: the value projections there are where the input is read)
- **R2 unblock**: o of layers whose attention knockout LOWERS the loss, down of layers whose MLP knockout lowers it: these push toward the base's default answer
- **R3 bottleneck**: down of middle layers whose MLP knockout raises the loss by >= 1.0
- **R5**: R2 only from layer 3 up; **R6**: the last two layers' MLPs always (they write the answer out)

What the measurements taught the locator (route_step and orders_spend were the tuning skills; the rules were then frozen and applied to the other skills):

- My first rules (without R6) lost to a **random** choice of the same number of modules (route_step 0.941 vs 0.915 random, next_move 0.847 vs 0.893). Adding the output MLPs (R6) moved route_step to 0.966-0.992.
- More rank on the same modules did nothing (rank 32: 0.941). On route_step, editing only the MLPs of every layer scored 1.000 and attention only 0.958: routing by meaning lives in the MLPs (word -> category memories); attention mostly moves information.
- **Breadth beats concentration.** Across 15 skills, the locator's concentrated pick (~0.2-0.4M edited parameters) was the best edit on 2 (family_topic, pick_source), tied on 2 (json_repair, route_step) and lost on 11 to rank 2 on every module or the pick plus rank 2 everywhere else (`thin`). A random pick of the same size beat it where that control ran (claim_support 0.667 vs 0.587; quote_pick 0.667 vs 0.620). A skill is not stored in one small set of modules: a small change in every module edits it best.
- Rank 8 everywhere (2.4M edited parameters) beat rank 2 everywhere (0.6M) once in four skills (orders_spend 0.984 vs 0.967, one test sentence) and lost on the other three: 4x the size, no gain.
- So each skill trains the candidates below from its maps and **dev** picks (dev = held-out training words; test is never used to choose). Where dev and test disagree it is reported, not fixed by peeking at test (next_move: dev picked MLP-only rank 2, 0.880 on test, while `thin` scored 0.973).

Every skill, every candidate edit (test score, edited parameters; * = the edit dev chose and the hive runs):

| skill | base | locator pick (r8) | pick r8 + r2 elsewhere | r2 everywhere | random K (r8) | r8 everywhere | served (dev pick) |
|---|---|---|---|---|---|---|---|
| claim_support | 0.493 | 0.587 (252K) | 0.800* (799K) | 0.833 (611K) | 0.667 (249K) | 0.807 (2442K) | thin 0.800 |
| element_match | 0.500 | 0.867 (295K) | 0.993* (832K) | 0.980 (611K) | - | - | thin 0.993 |
| family_topic | 0.500 | 0.850 (313K) | 0.750 (846K) | 0.787* (611K) | - | - | all_r2 0.787 |
| json_repair | 0.360 | 1.000 (226K) | 1.000 (780K) | 1.000* (611K) | - | - | all_r2 1.000 |
| licence_open | 0.444 | - | - | - | - | - | clone_orders_spend 0.756 |
| next_move | 0.253 | 0.947 (387K) | 0.973 (901K) | 0.880 (611K) | - | - | mlp_r2 0.880 |
| orders_any | 0.672 | - | - | - | - | - | clone_route_step 0.967 |
| orders_delete | 0.328 | 0.869 (253K) | 0.902 (801K) | 0.951 (611K) | - | - | all_r2_questions 0.951 |
| orders_login | 0.148 | 0.934 (280K) | 0.984 (820K) | 0.984* (611K) | - | - | all_r2 0.984 |
| orders_send | 0.213 | 0.885 (306K) | 0.885* (840K) | 0.934 (611K) | - | - | thin 0.885 |
| orders_signup | 0.246 | 0.836 (315K) | 0.934 (847K) | 1.000 (611K) | - | - | thin_questions 1.000 |
| orders_spend | 0.311 | 0.885 (304K) | 0.967 (839K) | 0.967 (611K) | - | - | all_r2_questions 0.967 |
| pick_element | 0.000 | 0.473 (313K) | 0.887 (846K) | 0.927* (611K) | - | - | all_r2 0.927 |
| pick_source | 0.122 | 0.932* (412K) | 0.878 (919K) | 0.878 (611K) | - | - | pick 0.932 |
| quote_pick | 0.167 | 0.620 (319K) | 0.980* (850K) | 0.993 (611K) | 0.667 (290K) | 0.987 (2442K) | thin 0.980 |
| route_step | 0.186 | 0.992 (263K) | 0.975 (808K) | 0.992* (611K) | - | - | all_r2 0.992 |
| split_orders | 0.007 | 0.813 (209K) | 0.900* (767K) | 0.833 (611K) | - | - | thin 0.900 |
| task_kind | 0.441 | - | - | 0.906* (611K) | - | - | all_r2_300 0.906 |

### Architecture edit: a smaller base by removing layers

The knockout maps show some layers barely matter to any probed skill. `training/cells_cut.py` removed the 8 least important ([4, 5, 7, 9, 21, 22, 25, 26]) -> a 22-layer base (106M params, 115 MB). Cells retrained on it:

| skill | 30 layers | 22 layers | ms/call 30 | ms/call 22 |
|---|---|---|---|---|
| route_step | 0.992 | 0.771 | 58 | 34 |
| next_move | 0.880 | 0.807 | - | - |

Average test 0.936 (30 layers) vs 0.789 (22 layers); the cut base is 1.70x faster per call. The cut base loses accuracy: cells stay on the full base. training/reports/cells/cut2.log (quiet CPU, 4 threads, same edit type, data and steps on both bases). A first run on a busy CPU gave 0.797 and 0.653 on the cut base. Both runs of training/cells_cut_eval.py were killed by SIGILL (illegal instruction) while timing the second skill, so quote_pick and orders_spend were not measured and next_move has no timing; the cause was not found.

### Cloning: a new skill gets a cell by copying the nearest one and editing the copy

`training/cells_factory.py <skill>`: the parent finder runs every registered cell on the new skill's dev inputs; the one that already answers it best (ties: the lowest dev loss) is cloned, its weight deltas copied into the new cell, and the clone is trained on the new skill only. The control trains the same modules from zero for the same steps. Dev picks which one becomes the cell.

| new skill | nearest cell | clone dev / test | from zero dev / test | steps |
|---|---|---|---|---|
| orders_any (does the sentence order ANY risky action?) | route_step | 1.000 / 0.967 | 1.000 / 0.918 | 60 |
| licence_open (is a licence free for any use, including commercial?) | orders_spend | 1.000 / 0.756 | 1.000 / 0.807 | 60 |

### Organizers and the gate

- **gate**: a cell that routes any input to the group of cells that reads it (order, step, failure, claim, sentences, page, json, licence), like the gate of a mixture of experts (`team/cells/skills.py` GROUPS): 0.940 on test inputs from every cell's test split.
- **organizers** run a group: the order organizer asks the five one-kind order cells (spend, delete, send, login, signup) and returns the set that said yes (`team/cells/use.py`).
- **a skill too big for one cell is split again**: one cell reading a whole list of page elements and copying the right id (pick_element) scored 0.927. The smaller skill inside it, `element_match` (does THIS one element reach the goal? yes/no), is its own cell; the page organizer asks it about every element and acts on the most likely yes: **1.000** on the same test pages (182 ms per page).

### Where cells work in the hive (switched on only where they won)

- engine: broken JSON from any member, after the code rules fail (`team/llm.py`) -> `json_repair`: **on**
- coordinator: the instruction checklist from your order (`team/specialists/coordinator.py`) -> `split_orders`: **on**
- coordinator: a plan step names an unknown specialist -> `route_step`: **on**
- researcher: no usable search plan, or a search names an unknown source (`team/specialists/researcher.py`) -> `pick_source`: **on**
- verifier: does the quote state the claim (`team/specialists/verifier.py`) -> `claim_support`: off: cell 0.827 vs verifier = fast+verifier 0.880
- verifier: a cited quote is in no source the team read: which source sentence states the claim -> `quote_pick`: **on**
- guard: the second reading of your order: five one-kind order cells (`team/guard.py`) -> `orders_*`: **on**
- guard: family check: the rule OR the cell -> `family_topic`: **on**
- hive loop: after a failed attempt: retry, reroute now, or stop (`team/hive.py`) -> `next_move`: **on**
- hive: triage: the cheapest way through the hive for the whole task; when sure, a template plan replaces the 4B coordinator and plan reviewer (`team/specialists/coordinator.py`) -> `task_kind`: **on**

Measured, but not switched on (or with a cost):

- checklist (`split_orders`): on a real order the cell respelled a model id ('Smol LM2') and left out 'Do not log in or pay': its training orders had no ids and no negations. The coordinator now keeps the span of your own words closest to each line and adds any sentence of the order that no line covers, as written (`team/specialists/coordinator.py`); on the test split that scores 0.927 vs 0.913 for the raw cell.
- JSON repair (`json_repair`): the cell turns ANY text into JSON ('no json here' -> {"no": null}); it never saw text without JSON. The hook now runs only on text that holds a broken object, rejects a repair whose keys are not in the text, and is asked before the code rules settle for a list inside a broken object (they returned [1, 2] for a whole object). As used: 1.000 on the test split; the code rules alone 0.493.
- family check: the rule OR the cell scores 0.875 vs the rule alone 0.875 on test. The cell catches family steps the rule misses ('Plan a trip with the kids', 'Choose a school for our son') and wrongly flags as many ('Family Guy' trivia, 'brother-in-arms' quotes); a wrongly flagged step is dropped and listed in the report. Kept on because your family rule is strict. No confidence threshold helps: dev is perfect at every threshold and test has 9-10 false blocks at every one (`training/reports/cells/thresholds_and_cascade.md`). The writer's step is judged by the rule alone.
- triage (`task_kind`): served test 0.913. A shortcut needs the cell's confidence to reach its kind's threshold, chosen on dev (write 0.97, calc 0.9, lookup 0.9, site 0.9, code 0.9): it is taken for 70% of test tasks and is right on 0.966. What it still gets wrong: a lookup it confidently calls a writing task (the writer then answers from its own knowledge and the critic marks it; an until-done round re-plans with the coordinator).
- cell -> member cascade (the cell answers when sure, unsure cases go up): on every cell measured, the threshold chosen on dev sent nothing up, so the cascade equals the cell; none is wired (`training/reports/cells/thresholds_and_cascade.md`).
- `claim_support`: cell 0.827 vs the verifier member 0.880: the bigger member keeps the job.
- `licence_open`: cell 0.741 vs the juror member 0.933: the bigger member keeps the job. The 135M cell lacks the world knowledge the test needs (e.g. that ISC is a permissive licence).
- page organizer (`element_match` per element): 1.0 on the test pages vs the browser member's 0.88, asked exactly as the hive asks it. On the browser's held-out click cases on live pages it picked the right element in 4/8; the browser member got 7/8 of the same cases (`training/reports/browser/`), so the browser keeps choosing its own clicks.
- `gate`: routes 0.940 of test inputs to the right group. The hive calls each cell at a fixed hook, so nothing needs routing yet; the gate is ready for inputs that arrive without one.
- `orders_any`: made by the factory to test cloning; not wired, the five one-kind order cells already read every order.

### End-to-end: one real task with cells on (`training/reports/cells/hive_check/`)

> Find the licence and the parameter count of HuggingFaceTB/SmolLM2-135M-Instruct on Hugging Face and give me a two-line summary. Do not log in or pay.

- run 1: correct answer (Apache-2.0, 0.135B; jury 3/3). The order cells read 'Do not log in or pay' as no order (right). The checklist cell respelled the model id and left out 'Do not log in or pay' -> fixed (lines keep your words; uncovered sentences are added).
- run 2, the final code: same correct answer; the checklist has all 4 instructions in your words, 4/4 done. This time the coordinator also planned a browser and a coder step; when they failed, the `next_move` cell stopped the browser step after 1 attempt (page not reachable), retried the coder after a crash, and stopped it after a second failure, instead of always using all 3 attempts.
- the other hooks (JSON repair, routing rescue, source pick, quote rescue) only fire when something breaks; nothing they cover broke in these two runs, so they are exercised by their tests and test splits only.

Turn every cell off with `AGENT_TEAM_CELLS=0`.

Commands: `python training/cells_build.py` (after a clone: rebuild the base and the cells for llama.cpp); `python training/cells_pipeline.py <skill>` (probe, locator pick, candidates, promote); `python training/cells_factory.py <new_skill>`; `python training/cells_incumbents.py <skill>`; `python training/cells_compare.py`.
<!-- cells:end -->

## Dreaming: getting better on its own (`team/dream.py`)

`python -m team dream`, or automatically when `serve` has been idle 30 minutes (at most once a day):

1. **Replay** every past run: board, verdicts and every recorded model call.
2. **Lessons:** each verified failure becomes a one-line rule in `memory/lessons.jsonl`; the team
   reads the relevant ones at the start of similar tasks.
3. **Rehearse:** re-attempt failed tasks with today's weights and lessons (approvals are never granted
   while dreaming).
4. **Distil:** every model call inside a step the verifier passed becomes a training example for that
   specialist (`training/data/self/`), so it learns from its own verified work.
5. **Retrain with a gate:** when a specialist has 12+ new examples, a candidate weight edit is trained
   and scored on the held-out evals. It replaces the current weights only if it does not score lower.
   Old versions are kept in `adapters/.previous/`.

Built and wired into `serve`; not run as a full cycle in this session (CPU time went to the demo and evals). `python -m team dream --no-train` runs the replay, lessons and distil parts in minutes.

## The hive grows itself: jobs nobody declared (`python -m team life`, `team/cells/spawn.py`)

Every cell above was a job somebody named first. This loop has no such step: the hive reads its own work and finds
the small jobs in it.

```
members work -> every call is logged -> NOTICE: which call sites reply with a few fixed values? -> a new job
   -> PRACTICE: the member decides recombined older cases (near misses, mismatches)
   -> COMPETE: candidate edits of the 135M base (then the 360M, only if the 135M cannot hold the job)
   -> GATE: judged on the newest real decisions, label by label
   -> WORK: the cell answers the member's call when it is sure; the member answers the rest (and is logged)
   -> AUDIT: one sure call in ten also goes to the member; under 93% agreement the cell is RETIRED
   -> more work is logged -> retrain on the newer decisions -> ...
```

- **Notice.** A call site is one member with one instruction. If at least 97% of its replies are a few fixed values
  (PASS/FAIL, true/false, ...), it is a job. Text beside the decision is allowed only when it is an explanation; a
  label that comes with text only the member can write (a list of fixes) is never answered by a cell.
- **Gate.** A cell that has learned nothing agrees nine times in ten on a site that says yes nine times in ten. So a
  label is only switched on if the newest real decisions hold at least 3 where the member chose another label, and
  the cell is wrong at most half as often as answering blindly would be; then 95% agreement on what it answers, at
  least a fifth of the calls answered, at least 10 answered. Too few decisions to judge is reported as that, not as a
  failure of the cell, and no bigger base is tried.
- **Practice is training only.** A cell is judged only on real decisions newer than anything it trained on.
- `python -m team serve` runs a turn when the device is idle; `cells/LIFE.md` lists every call site, what the member
  spends there, whether it is a job and who holds it. `AGENT_TEAM_SPAWN=0` turns every spawned cell off.

**Measured (this is one job, on one day of work; the numbers are small and are stated as they are).** The hive did 5
whole tasks and 35 research questions on live sources (`training/life_feed.py`, `training/life_drill.py`; none of
them bench tasks). It noticed 2 decision sites among 15. One had enough decisions: the verifier's fact check
("does this quote support this claim"), 162 distinct real decisions (72 from that work, 90 from the verifier checking
the facts of the reading test below).

| spawned cell | base | newest 25 real decisions (15 supported, 10 unsupported) | cost per call |
|---|---|---|---|
| `sp_verifier_75e567` | SmolLM2-135M + rank-2 edit | answers 13 (52%), agrees with the verifier on 13 of 13; 92% agreement over all 25 | 81 ms against 4.7 s |

It answers only SUPPORTED; UNSUPPORTED always goes to the verifier (dev did not vouch for that label). The first
round, with 72 decisions, left 11 to judge on: the cell agreed on 10 and stayed off for lack of evidence.

Live, on 12 further research questions with every sure answer also sent to the verifier
(`AGENT_TEAM_SPAWN_AUDIT=1`): 26 fact checks (the verifier: 22 supported, 4 unsupported); the cell was sure on 20 and
agreed on 19 (95%). The miss: claim "-196 °C", quote "−195.8 °C"; the verifier rejected it, the cell would have passed
it, so 1 of the verifier's 4 rejections would have slipped through. 20 audits are few, and the miss is a near-miss
number, the kind that matters most. Its confidences were left as the gate set them, not tuned on these calls.

What the logs also show: the small checks are a small share of the hive's time (the fact check about 5%). The
largest share by far is the 4B reading sources. That is the next section.

`python -m team org` prints the hive as an organisation: teams, their members, their cells, and who holds each job.

## Small models on the 4B's biggest job: reading in chunks (`training/chunk_read.py`)

The researcher (Qwen3-4B) reads up to 9000 characters of sources in one call. The same 26 real inputs from the logs,
read again by the plain Qwen3-1.7B in chunks of 1800 characters, each chunk its own call with a one-job instruction;
both sides through the hive's checks (quote word for word in the source, the verifier on claim against quote).

| | Qwen3-4B, whole | Qwen3-1.7B, in chunks |
|---|---|---|
| facts that passed the checks | 38 | 52 |
| of the 4B's 38, also found | | 19 |
| inputs with every fact of the 4B found (of 21 where it had any) | | 7 |
| inputs with none found where the 4B had some | | 5 |
| inputs where only this side had a checked fact | | 5 |
| model seconds | 2202 | 1205 |

**The same 26 inputs after the reader's instruction lost its example value** (`training/reports/chunk_read.json`; the
table above is kept in `chunk_read_first_instruction.json`). The instruction used to show what a claim looks like with
("X has 0.135B parameters"); in the small-only runs the 1.7B returned that parameter count as a fact when asked for
download counts. Without the example, and told to read first what the task asks for:

| Qwen3-1.7B in chunks | with the example | without it |
|---|---|---|
| facts that passed the checks | 52 | 62 |
| of the 4B's 38, also found | 19 | 28 |
| inputs with every fact of the 4B found (of 21) | 7 | 14 |
| inputs with none found where the 4B had some | 5 | 1 |
| model seconds | 1205 | 1216 |

Not shown by this: whether a checked fact answers the question (the checks test the quote, not relevance), and the
4B's time includes its summary and item list. The small reader is good on long pages and bad on short search results
and lists. Neither replaces the other; they miss different things. Not yet built: small reader first, 4B only where
it comes back empty.

## School: small models learn a bigger member's job (`python -m team school`, `team/school.py`)

Cells take over small decisions (a few fixed answers). School is for the jobs that are not small decisions: writing a
plan, writing a program. The bigger member is the teacher, a small model is the student, and the student's weights are
edited on the teacher's own work.

1. **Lessons.** The teacher writes new tasks (eight at a time, each call on another topic) and does its job on each;
   a lesson is the task, the teacher's answer, and what that answer decides (for a plan: which specialists in which
   order; for a program: what it prints when it is run). Tasks from the bench are never lessons.
2. **Training.** A weight edit (LoRA) of the student on the lessons, on the CPU (128 lessons: 25 minutes).
3. **Exam.** Lessons that were never trained on. Scored: the untouched student, each taught specialist alone, the
   general ones voting, and tasks routed to a narrow specialist where one owns the territory.
4. **Back to school.** Each later visit brings new lessons; the present specialists take them first; for the ones the
   hive got wrong the teacher writes more tasks of the same kind, and a new narrow specialist is trained on that gap
   alone. Nobody is replaced or retrained: old and new specialists exist side by side, and a task goes to the one
   whose known lessons it resembles most.
5. **Who holds the job.** At 85% agreement with the teacher (and 3 points over the untouched student) the role has
   graduated. In the hive with nothing above 1.7B (`AGENT_TEAM_SMALL=1`) the teacher is not there and the untouched
   student would do the job, so there the taught specialists hold it as soon as the exam puts them ahead of it.
   `AGENT_TEAM_SCHOOL=0` switches that off.

The always-on agent sends one role to school whenever the device is idle, each role in turn. `python -m team org`
shows every role's state.

**Measured: the planner (Qwen3-4B teaching Qwen3-1.7B), two visits, 232 lessons.**

| | untouched 1.7B | taught 1.7B | the 4B |
|---|---|---|---|
| same plan as the 4B on 46 unseen lessons | 30% | 59% | |
| of those, the 24 one- and two-specialist plans | | 24 of 24 | |
| of those, the 22 plans with three or more specialists | | 3 of 22 | |
| the planner's own eval suite, 14 cases, scored by rules (`training/observe.py`) | 0.449 | 0.663 | 0.872 |

What this shows, and what it does not:
- The taught student is clearly ahead of the untouched one on both measures, and reaches about half of the 4B's lead
  on the independent suite. It has not graduated.
- It learned every simple plan and almost none of the long ones. The 4B's own long plans are not a clean target: for
  "write a script that scrapes headlines and saves them" it planned researcher, browser, coder, calculator, writer.
  Agreement with such a plan is not the same as a good plan, so the 59% understates the student on long tasks and
  the exam cannot say by how much.
- The first narrow specialist (trained on 37 lessons around 11 gaps) did not help: in its territory it got 9 of 26
  exam lessons right, the general one the same 9. With it or without it the hive scores 59%; at least one of the
  specialists is right on 61%. More specialists on the same noisy long plans will not move this; cleaner lessons
  for long plans will (the plan after the reviewer and the code checks, or plans from runs that passed).

In the small-only hive the taught planner holds the job. In one clean run of all 16 development tasks with nothing
above 1.7B (`small7`) every plan it made was the right one; the run scored 11 of 16, and the five failures were all
after planning (`training/reports/hive_bench/small_only_notes.md`).

**Measured: the coder (Qwen2.5-Coder-7B teaching Qwen2.5-Coder-1.5B), one visit, 160 lessons.** Its lessons are
programs that ran, and the exam asks whether the student's program prints what the teacher's prints.

| | untouched 1.5B | taught 1.5B |
|---|---|---|
| prints the same as the 7B's program on 32 unseen lessons, as first scored | 59% (19) | 81% (26) |
| the same exam, scored again after two corrections to the key (below) | 66% (21) | 84% (27) |

What this shows, and what it does not:
- The taught student is 22 points ahead of the untouched one after one class of 25 minutes' training. It has not
  graduated (85%); in the small-only hive it holds the coder's job, as the rule above says.
- Of its 6 misses, one is not a miss (166.3256237947956 against 166.32562379479558: the same sum; the key now compares
  long decimals to 10 significant digits, for later exams; this exam stays as scored), one is a lesson where the
  teacher itself was wrong (a future value of 1.6 million from 10000 and 200 a month), and four are real (vowels
  counted wrong, a grouping, an off-by-one, a doubling time).
- The key was corrected twice after the first scoring, and the unusable answers were asked again: long decimals are
  compared to 10 significant digits, and an import a program never uses no longer keeps it out (the untouched
  student had 11 programs refused for importing a web library it then did not use). Both students gained two
  lessons. 84% is one lesson short of graduating.
- The lessons are pure computations. They do not teach what the 1.5B fails at inside the hive: changing a working
  program on feedback without breaking it, and reading values from a fetched page. That needs a second kind of lesson.

## Recruits: the hive brings in other small models itself (`python -m team recruit`, `team/recruit.py`)

Almost every member of the small hive is the same Qwen3-1.7B with another weight edit, and copies of one model make
the same mistakes: the planner's second specialist got the same 9 exam lessons right as the first. A weight edit also
sharpens what a model can nearly do and adds little where it cannot (the taught planner: 24 of 24 short plans, 3 of
22 long ones). So the hive looks for other families, and it does that without anyone choosing models for it:

1. **Find.** It searches Hugging Face for small chat models in GGUF it has not looked at. It takes a model only if it
   has at most 2.0B parameters, is ungated (nothing logs in or uses a token), is under Apache-2.0, MIT or BSD (the
   model and its base), comes from its own makers or a known converter, and is not a variant made to drop the
   model's safety behaviour. Every model looked at is recorded with the reason it was passed over.
2. **Download.** One file, and never when less than 4 GB would stay free. Nothing is deleted to make room.
3. **Tryout.** The recruit takes each school role's exam untouched (the lessons nobody trained on).
4. **Enrol.** At least as good as the role's untouched student: it becomes one more voice of the role, and the role's
   exam decides by measurement whether answering together beats the best one alone.
5. **Teach.** Better than the untouched student by the school's margin: it is the better student. An edit of its
   weights is trained on the lessons the teacher already gave (no new teacher time), and that specialist takes the
   exam too. The job goes to whoever measures best.

**Measured: the first two recruits, and whether other families miss other things** (`training/diverse.py`,
`training/reports/diverse_coders.json`; the coder's 32 unseen lessons, every model untouched except the taught one).

| model | right alone, of 32 |
|---|---|
| Qwen2.5-Coder-1.5B, taught by the school | 27 |
| Qwen2.5-Coder-1.5B, untouched | 21 |
| Qwen3-1.7B (the hive's general small model) | 17 |
| Yi-Coder-1.5B (recruit) | 12 |
| SmolLM2-1.7B (recruit) | 0 |

- Neither recruit was enrolled: both are under the untouched student on programs (38% and 0% against 66%) and on
  plans (15% and 4% against 30%). SmolLM2-1.7B wrote no program that ran and printed the right thing.
- The same model twice does share mistakes: the taught and the untouched 1.5B are both wrong on 4 lessons, where two
  independent models with their scores would both be wrong on 1.7. With another family the overlap is nearer chance
  (4 against 2.3 with Qwen3-1.7B, 4 against 3.1 with Yi-Coder).
- But the other families are weaker, so they add little: at least one model is right on 28 lessons for the same
  model twice, 29 for three families, 30 for all five. Taking what most models print gives 27, the same as the best
  one alone. More voices did not make the answer better here.
- What other families do give is a check that needs no teacher: whenever two models of different families printed
  the same thing, it was right. 16 of 16 (taught 1.5B and Qwen3-1.7B), 11 of 11, 13 of 13, 11 of 11, 7 of 7. On 32
  lessons that is a small sample; it says where the hive can trust a program without asking the jury, and where
  (they disagree) the effort should go. Not built into the run loop yet.

The always-on agent recruits one model whenever the device is idle, in turn with dreaming, growing cells, evolving
instructions and school. `python -m team org` lists every recruit and its tryouts; `cells/recruits.json` is the record.

## The demo

`demo/TASK.md` is the one prompt; `demo/README.md` is generated from the run's own records; `demo/run/` holds
everything (board, every model call, screenshots, the code the coder wrote, the report). Honest result: see
`demo/README.md` "Status" - the research and license/size checks were done and verified; the benchmark part was
not (the coder's program failed on the 4-bit models the researcher picked), and the report says so.
Earlier attempts and what each one exposed are kept in `runs/demo-attempt-*` (not in git).

## Install (your laptop)

Needs: Python 3.11+, ~8 GB free RAM for the team (16 GB machine is fine), ~10 GB disk for models.

```bash
python -m venv .venv && source .venv/bin/activate
```
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```
```bash
pip install -r requirements.txt
```
```bash
CMAKE_ARGS="-DGGML_NATIVE=ON" pip install llama-cpp-python==0.3.36
```
(compiles llama.cpp for your CPU; needs a C++ compiler and cmake, ~10 min)
```bash
playwright install chromium
```
```bash
python training/cells_build.py
```
(builds the 18 cells and their shared SmolLM2-135M base for llama.cpp from `cells/adapters/`: ~2 min,
~185 MB in `cells/gguf/`, which git does not carry. Skip it and the first task builds them, saying so in its log;
if that fails, the log says the cells are off and the bigger members and the code rules do those jobs.)
```bash
python -m pytest -q tests
```

The first task downloads the models from Hugging Face, no account or token needed: Qwen3-4B 4-bit
(2.5 GB), Qwen3-1.7B 8-bit (1.8 GB), Qwen2.5-Coder-7B 4-bit (4.7 GB), plus tokenizer files. The
specialists' own weight edits are in `adapters_gguf/` (9-17 MB each; PyTorch versions in `adapters/`).
Training or retraining edits (`training/`, `dream`) also downloads Qwen3-1.7B in bf16 (4 GB).
Without llama-cpp-python the team falls back to PyTorch (`AGENT_TEAM_ENGINE=hf`) with the 1.7B models.

Lighter machine: `AGENT_TEAM_MAX_LOADED=1` keeps only one model in RAM at a time (slower: models
reload when roles switch). Bigger machine: `AGENT_TEAM_BRAIN=brain8b` makes Qwen3-8B 4-bit (5 GB) the brain (supported, not measured here).

## How well it does (measured on whole tasks, `training/hive_bench.py`)

Each task runs through the whole hive (`python -m team`, unattended), from a frozen copy of the code so no edit can
reach a run in progress, and is checked in code against the live answer (training/reports/hive_bench/).

| set | tasks | pass | what it means |
|---|---|---|---|
| development | 16 (lookups, papers, a chart, a website, a scrape to CSV, arithmetic, dates, units, translate, summarise, fix text, draft, code, fix code, explain, given data) | 14/16, then **15/16** | fixes were tried on these, so this flatters it |
| held-out set 1 | 16 fresh tasks of the same kinds, written before the fixes and run once | **9/16** | the honest number then |
| held-out set 2 | 16 more fresh tasks, contamination-checked before they ran, run once on later code | **11/16** (10/16 as first scored) | one check was wrong (it wanted "apache-2.0" for a right "Apache License 2.0") and was corrected |
| held-out set 3 | 16 more fresh tasks, contamination-checked, run once on the code of the evening (0147aa4) | **13/16** | the honest number now |

The gap is the measurement: fixes made on development tasks carried over to fresh tasks far less than the development
score suggested. Each held-out failure and its cause is in `training/reports/hive_bench/heldout_notes.md`: a chart
shown but never saved, a column of "Unknown" covering a value never found, a weekday printed as a number, two decimals
where one was asked (the prompt's own example), a sentence handed back instead of translated or rewritten, and a
Wikipedia article whose quotes could never match because the reader split every link onto its own line. All are fixed
with checks in code and tests; the held-out score above stays as measured, because those tasks informed the fixes.
Set 2's five failures (`heldout2_notes.md`): a birth date the browser made up and the jury passed, a 404 from a link
joined to the wrong page, a right "$161.00" struck because the calculator printed "161.0", a German grammar error, and
handed-over data sent to web search. Four were the hive's own checks letting a wrong result through or striking a
right one. Each was fixed in code, and held-out set 3, which no fix had seen, then scored 13/16 (`heldout3_notes.md`:
a browser that gave up on page 1 of a listing, a formal rewrite that turned his question into a command, a right
explanation given twice).

Measured engine and swarm decisions (each switched only where measured better):
- llama.cpp's repacked weight copies off: peak memory 12.9 GB -> 7.8 GB at the same speed and answers; the 16-bit
  attention cache on: 1.6x faster at 8.2 GB, the same decisions (training/reports/arch_bench.json). Prompt-lookup
  decoding crashed in llama-cpp-python 0.3.36 and stays off.
- Two jobs at once: 4% faster for +2.2 GB (training/reports/workers.json); the cell pool: 1.2x for +1 GB
  (training/reports/cells/pool.json). Both stay off: on a CPU the models already use every core.
- Translations go to the 4B: chrF 51.6 on 120 held-out professional translations, against 48.4 for a translation
  edit of the 1.7B made for it and 46.7 for the writer (training/reports/translator.json). The edit sharpened the 1.7B
  (+1.8, not clear on 120 sentences); the bigger model simply knows the languages better.
- Two cells that won on synthetic test data failed on real text (answers_q: 3/15 real pairs right; claims_agree:
  rewordings called conflicts): their jobs went to the 4B and to a rule (training/reports/research_eval_notes.md).

## Limits (measured, not guessed)

- **Speed.** On a 4-core CPU the 1.7B specialists generate ~8-10 tokens/s. A big multi-step task
  takes tens of minutes, not seconds. Training a specialist takes 5-80 minutes.
- **Reasoning ceiling.** These are 1.5-1.7B models. They plan, click, extract and judge well inside
  the shapes they were trained on; they are far weaker than frontier models at open-ended reasoning
  or long, novel programs. The verifier and retries catch many mistakes; they cannot create ability
  the models lack. Everything the team could not confirm goes under "Not confirmed" in the report.
- **Search.** General web search engines block scripted queries (DuckDuckGo and Mojeek returned bot
  walls from the cloud machine this was built on). The team does not try to get around bot checks;
  it uses sources that offer APIs (Hugging Face, Hacker News, arXiv, OpenAlex for scholarly papers in every field,
  PyPI, Wikipedia pages, any URL) and the real browser. On your own connection DuckDuckGo may work; the `web` source
  tries it. OpenAlex needs no key; its anonymous budget is per IP address and per day (the cloud machine's ran out),
  and an optional free key in `OPENALEX_API_KEY` gives you your own.
- **Sites.** No logins unless you allow a site per task; no sign-ups ever; CAPTCHAs are not solved.
- **Code isolation.** Code runs as your user in the run's `work/` folder with a timeout. It is not a
  container. The guard stops deleting/sending/spending code from running without your yes.
- **Evals are small** (3-18 cases per specialist), so a single case moves a score a lot. Numbers are
  real measurements, not benchmarks.
- **Not done on purpose:** removing the base models' built-in safety training. The team's filters
  are your rules above, nothing else.

## Layout

```
team/            the team: hive.py (orchestration), board.py (shared memory), guard.py (your rules),
                 llm.py (model pool), memory.py, dream.py, serve.py, chat.py, web.py, vault.py
team/specialists coordinator, researcher, browser_agent, coder, verifier, writer
team/tools       web.py (live sources), browser.py (Chromium), sandbox.py, preview.py
adapters/        each specialist's trained weight edit (+ training_meta.json)
training/        evals (held out), data builders, train_lora.py, inspect_weights.py, observe.py, reports/
demo/            the end-to-end demo: task, full trace, report, screenshots
memory/          profile, policy, lessons, run history, schedule (yours, not in git)
tests/           rule and parsing tests (no models needed)
```
