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

## Giving it a task

```bash
python -m team "Find the three cheapest Mystery books on books.toscrape.com and save them to a CSV"
```

```bash
python -m team --file my_task.md
```

```bash
python -m team chat
```

```bash
python -m team web
```
(then open http://127.0.0.1:8765, a chat-style page that shows the team working live)

```bash
python -m team serve
```
Always on: drop tasks into `inbox/` (or `python -m team add "task"`), reports appear in `outbox/`.
Recurring tasks go in `memory/schedule.json`. When idle, it dreams (below).

Tell it how you like things done; every report follows it:

```bash
python -m team remember "Prices in INR. Short answers, table first."
```

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
python -m pytest -q tests
```

The first task downloads the models from Hugging Face, no account or token needed: Qwen3-4B 4-bit
(2.5 GB), Qwen3-1.7B 8-bit (1.8 GB), Qwen2.5-Coder-7B 4-bit (4.7 GB), plus tokenizer files. The
specialists' own weight edits are in `adapters_gguf/` (9-17 MB each; PyTorch versions in `adapters/`).
Training or retraining edits (`training/`, `dream`) also downloads Qwen3-1.7B in bf16 (4 GB).
Without llama-cpp-python the team falls back to PyTorch (`AGENT_TEAM_ENGINE=hf`) with the 1.7B models.

Lighter machine: `AGENT_TEAM_MAX_LOADED=1` keeps only one model in RAM at a time (slower: models
reload when roles switch). Bigger machine: `AGENT_TEAM_BRAIN=brain8b` makes Qwen3-8B 4-bit (5 GB) the brain (supported, not measured here).

## Limits (measured, not guessed)

- **Speed.** On a 4-core CPU the 1.7B specialists generate ~8-10 tokens/s. A big multi-step task
  takes tens of minutes, not seconds. Training a specialist takes 5-80 minutes.
- **Reasoning ceiling.** These are 1.5-1.7B models. They plan, click, extract and judge well inside
  the shapes they were trained on; they are far weaker than frontier models at open-ended reasoning
  or long, novel programs. The verifier and retries catch many mistakes; they cannot create ability
  the models lack. Everything the team could not confirm goes under "Not confirmed" in the report.
- **Search.** General web search engines block scripted queries (DuckDuckGo and Mojeek returned bot
  walls from the cloud machine this was built on). The team does not try to get around bot checks;
  it uses sources that offer APIs (Hugging Face, Hacker News, arXiv, PyPI, Wikipedia pages, any
  URL) and the real browser. On your own connection DuckDuckGo may work; the `web` source tries it.
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
