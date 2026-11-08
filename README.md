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

<!-- cells:start -->
## Cells: one tiny model per smallest skill (`team/cells/`, `training/cells*.py`)

Every smallest job in the hive is its own specialist, a **cell**. A cell is trained for one micro-skill only (is a purchase ordered? which specialist takes this step? does this quote state this claim? retry, reroute or give up?) and is allowed to be bad at everything else: other cells cover that. All cells share **one** frozen SmolLM2-135M (144 MB at 8-bit) in RAM; each cell owns only a small weight delta, hot-swapped per call in llama.cpp. A label cell answers through a grammar that only allows its labels.

**18 cells**, 11.8M edited parameters in total, 48 MB of deltas on one 144 MB base.

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

| skill | base | locator pick (r8) | pick r8 + r2 elsewhere | r2 everywhere | random K (r8) | r8 everywhere |
|---|---|---|---|---|---|---|
| claim_support | 0.493 | 0.587 (252K) | 0.800* (799K) | 0.833 (611K) | 0.667 (249K) | 0.807 (2442K) |
| element_match | 0.500 | 0.867 (295K) | 0.993* (832K) | 0.980 (611K) | - | - |
| family_topic | 0.500 | 0.850 (313K) | 0.750 (846K) | 0.787* (611K) | - | - |
| json_repair | 0.360 | 1.000 (226K) | 1.000 (780K) | 1.000* (611K) | - | - |
| licence_open | 0.444 | - | - | - | - | - |
| next_move | 0.253 | 0.947 (387K) | 0.973 (901K) | 0.880 (611K) | - | - |
| orders_any | 0.672 | - | - | - | - | - |
| orders_delete | 0.328 | 0.869 (253K) | 0.902 (801K) | 0.951* (611K) | - | - |
| orders_login | 0.148 | 0.934 (280K) | 0.984 (820K) | 0.984* (611K) | - | - |
| orders_send | 0.213 | 0.885 (306K) | 0.885* (840K) | 0.934 (611K) | - | - |
| orders_signup | 0.246 | 0.836 (315K) | 0.934* (847K) | 1.000 (611K) | - | - |
| orders_spend | 0.311 | 0.885 (304K) | 0.967 (839K) | 0.967* (611K) | - | - |
| pick_element | 0.000 | 0.473 (313K) | 0.887 (846K) | 0.927* (611K) | - | - |
| pick_source | 0.122 | 0.932* (412K) | 0.878 (919K) | 0.878 (611K) | - | - |
| quote_pick | 0.167 | 0.620 (319K) | 0.980* (850K) | 0.993 (611K) | 0.667 (290K) | 0.987 (2442K) |
| route_step | 0.186 | 0.992 (263K) | 0.975 (808K) | 0.992* (611K) | - | - |
| split_orders | 0.007 | 0.813 (209K) | 0.900* (767K) | 0.833 (611K) | - | - |

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

Measured, but not switched on (or with a cost):

- checklist (`split_orders`): on a real order the cell respelled a model id ('Smol LM2') and left out 'Do not log in or pay': its training orders had no ids and no negations. The coordinator now keeps the span of your own words closest to each line and adds any sentence of the order that no line covers, as written (`team/specialists/coordinator.py`); on the test split that scores 0.927 vs 0.913 for the raw cell.
- JSON repair (`json_repair`): the cell turns ANY text into JSON ('no json here' -> {"no": null}); it never saw text without JSON. The hook now runs only on text that holds a broken object, rejects a repair whose keys are not in the text, and is asked before the code rules settle for a list inside a broken object (they returned [1, 2] for a whole object). As used: 1.000 on the test split; the code rules alone 0.493.
- family check: the rule OR the cell scores 0.875 vs the rule alone 0.875 on test. The cell catches family steps the rule misses ('Plan a trip with the kids', 'Choose a school for our son') and wrongly flags as many ('Family Guy' trivia, 'brother-in-arms' quotes); a wrongly flagged step is dropped and listed in the report. Kept on because your family rule is strict.
- `claim_support`: cell 0.827 vs the verifier member 0.880: the bigger member keeps the job.
- `licence_open`: cell 0.741 vs the juror member 0.933: the bigger member keeps the job. The 135M cell lacks the world knowledge the test needs (e.g. that ISC is a permissive licence).
- page organizer (`element_match` per element): 1.0 on the test pages vs the browser member's 0.88, asked exactly as the hive asks it. Not wired: the browser member decides whole actions toward a multi-step goal, and the hive has no single-click goal to hand the organizer yet.
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
