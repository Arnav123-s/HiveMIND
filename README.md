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

## Your rules, enforced in code (`team/guard.py`)

These are the team's only filters.

| rule | what happens |
|---|---|
| Family and relationships are never task material | the task (or any planned step) is refused before any work |
| Spending money | stops and asks you (`y/N` in the terminal). In `serve`/`web`, it is not done and is listed in the report as waiting for you |
| Deleting | same: stops and asks. Code containing `os.remove`, `shutil.rmtree`, `rm -rf`, ... is not run until you say yes |
| Sending a message as you | same: send/post/reply/submit buttons, form submits, `smtplib`, HTTP POST to anything but read-only query APIs |
| No accounts, no sign-ups | hard block: sign-up links, register pages and password fields are refused |
| No logins | hard block, unless you name the site for one task (below) |

**Standing approvals.** If you want any of spend/delete/send to stop asking, set it in
`memory/policy.json`: `{"spend": "ask", "delete": "allow", "send": "ask"}` (`ask`, `allow` or `deny`).
Default is `ask` for all three.

**Using your credentials.** Put them in `~/.agent-team/credentials.json` (outside the repo, `chmod 600`):
```json
{"quotes.toscrape.com": {"username": "you", "password": "..."}}
```
and allow that one site for that one task:
```bash
python -m team --allow-login quotes.toscrape.com "Log in and list my ..."
```
The browser fills the form itself. The values never go into a model prompt, the board, the logs or the
trace. Sign-ups stay blocked even then.

## How the specialists were improved

TRAINING_SECTION

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

DREAM_SECTION

## The demo

DEMO_SECTION

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
