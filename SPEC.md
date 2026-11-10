# Spec checklist

Every requirement Arnav gave, what was built, the evidence, and its status.
**Done** = built and exercised with the evidence shown. **Partial** = built and exercised, but short of the
requirement in a way stated here. **Not done** = with the reason.

## Original task

| requirement | status | what / evidence |
|---|---|---|
| New repo, built in `agent-team/` | Done | local git repo; pushed to GitHub `Arnav123-s/HiveMIND` (branch `results-and-demo`, draft PR #1; `main` holds the first version) |
| Hive of specialists for everyday work + hard coding, research, real browser work | Done | 6 work specialists + 4 quality-control members + order reader + harness smiths (README "The team"); browser clicks/types/navigates real sites (`team/tools/browser.py`) |
| One prompt; team self-organises, assigns, checks, delivers | Done | `python -m team "..."`; coordinator plan → specialists → jury verification → retries/re-routing → writer (`team/hive.py`); runs in `runs/`, demo in `demo/` |
| One big task end-to-end, live sources, real code, real verification, work shown | Partial | `demo/README.md` (generated from the run's own records), `demo/run/` |
| README: the team, how to give a task, limits | Done | `README.md` |
| Mark what could not be confirmed, say where I looked | Done | report sections "Not confirmed"; README "Limits"; final report "Found" |

## Rules (strict order-following)

| requirement | status | what / evidence |
|---|---|---|
| Risky things only under explicit order | Done | `team/guard.py`: orders parsed from the task (command-position verbs; nouns, terms, negations excluded); unordered risky actions ask / wait |
| Family/relationships only when ordered, exactly as ordered | Done | `check_task(step, goal)`: steps touching family are dropped unless the order itself is about it |
| Spend / delete / send / login / sign-up / credentials only when ordered for that task | Done | `Guard.ask` approves only ordered kinds and logs the sentence relied on; logins/sign-ups only on sites the order names; tests in `tests/test_rules.py` |
| Two independent readings of the order | Done | parser + order-reader member (own weight edit); both must agree: 0 false approvals on 63 held-out sentences (`training/reports/orders_edited.json`) |
| Do exactly what was ordered, nothing extra, nothing skipped; reviewer and critic check it | Done | grounded instruction checklist; plan reviewer checks coverage + no extras; critic writes "Your instructions" ✅/❌ and flags unordered actions |
| Credentials accurate, local, never in prompts/logs/traces | Done (not exercised with real credentials) | `team/vault.py` + browser `login` action fills forms itself; no credentials were available or used in this session |
| Kill switch: terminal, web, serve; halts models, browser, code; records where it stopped | Done | `team/stop.py`; Ctrl+C, `python -m team stop`, web Stop button, `inbox/STOP`; tests + `training/test_kill_switch.sh` |

## Models and weights

| requirement | status | what / evidence |
|---|---|---|
| Small specialists, no VRAM, under 16 GB RAM, no spending | Done | CPU only; peak measured in the demo run (`demo/run/memory.txt`); all models Apache-2.0, ungated |
| Unfiltered, no restrictions | Not done on purpose | the base models' own safety training was not removed. The team adds no filter beyond Arnav's own rules |
| Train them and edit weights; observe each specialist personally | Done | held-out evals per specialist (`training/observe.py`, `training/reports/`); LoRA edits for 6 members; kept only where they won |
| Edit internals directly; find the right ones | Partial (built, not run) | `training/steer.py`: per-layer direction between right/wrong replies, layer+strength swept, gated; applied as llama.cpp control vector |
| Improve when they fail; more models; better architecture | Done | engine v2 (llama.cpp 4-bit), 4B brain, 7B coder, design fixes listed in README; every change measured |
| Shared weights across members | Done | one copy of each base; members hot-swap their edits per call (`team/llm.py`) |
| "Match frontier assistants, but better" | Not met | measured: 1.7-7B CPU models are far below frontier assistants on open-ended reasoning. The hive's design (verification, voting, re-routing) narrows the gap on structured tasks; it does not close it |

## Hive and smith swarm

| requirement | status | what / evidence |
|---|---|---|
| Many members, not 3 | Done | 14+ roles in `team/config.py`; swarm benchmark of 22 members |
| Swarm of smiths, one kind of improvement each, several per job, competing, measured winners kept | Partial | `team/smiths.py`: 10 jobs, 15 smiths, ledger, competition + gate. Exercised: the examiner and prompt-smith via the evolution harness code path, but no full competitive cycle was run in this session (CPU time went to the demo and evals). Built but not exercised end-to-end here: cloner + router teacher on a real niche, retirer, the two competing weight trainers (CPU time) |
| Smiths improve, clone and specialise smiths | Partial | smith-of-smiths in code (`improve_smiths`); needs ≥2 trials per smith before it acts, so it has not fired yet |
| Huge swarm that keeps multiplying, members specialising | Partial | cloning, routing and retiring are built; growth happens as `dream`/`smiths` cycles run over time, not yet over many cycles |
| Huge swarm in under 10 GB | Done | `training/swarm_bench.py` → `training/reports/swarm_bench.json` |

## Assistant behaviour

| requirement | status | what / evidence |
|---|---|---|
| Proactive, self-improving, learns tasks, dreaming | Partial | `python -m team dream`: replay, lessons, rehearsal, distil, gated retrain; runs automatically from `serve` when idle. Not run as a full cycle here |
| Always available, any time | Done | `python -m team serve` (inbox + schedule), `python -m team web` (local page), `python -m team chat` |
| Complete tasks fully, no half work | Partial | checklist + critic + re-routing push for completeness; the demo shows where it still falls short |

## Cells: one tiny specialist per smallest skill

| requirement | status | what / evidence |
|---|---|---|
| Every smallest thing done by a different specialist, allowed to be bad at everything else | Done for 18 micro-skills | one cell per micro-skill: a weight delta on one shared frozen SmolLM2-135M, hot-swapped per call in llama.cpp; label cells answer through a grammar of their labels (`team/cells/`, README "Cells") |
| The smallest specialist model possible | Done | 135M base, the smallest base tried; a 22-layer cut of it (106M) was faster (1.7x) but lost accuracy (0.936 -> 0.789 test), so cells stay on the full base (`training/reports/cells/cut22.json`) |
| Surgical weight edits that make it better | Done | each cell's delta changes 0.38-0.85M of 135M parameters; every cell beats the untouched base on test (e.g. route_step 0.19 -> 0.99, split_orders 0.01 -> 0.91) |
| Find what to edit (I act as the locator until real locators exist) | Done, with a finding | gradient x weight and per-layer knockout maps per skill; my rules picked modules (`training/cells_view.py`, every pick logged in `locator_log.jsonl`). Measured: my concentrated pick was best on 2 of 15 skills; small edits on every module won most. No trained locator cell yet: the log is its future training data |
| Cells beat what does each job today | Done: 14 cells take a job, 2 lose to the member | cell vs incumbent on the same test inputs (`cells/wins.json`, `training/reports/cells/SUMMARY.md`): e.g. split_orders 0.91 vs 0.28 (4B coordinator), next_move 0.90 vs 0.57, pick_source 0.93 vs 0.70, at 50-160 ms vs 1-11 s per call. The verifier (0.88 vs 0.83) and the juror on licences (0.93 vs 0.74) keep their jobs |
| Organizers / specialists of specialists | Done | order organizer (five one-kind cells; with the parser: 0.905 exact, 0 false approvals vs the member's 0.873); page organizer (element_match per element: 1.000 vs one cell 0.927 vs browser member 0.880) |
| Mixture of experts: a gate over the cells | Partial | the gate cell routes 0.940 of test inputs to the right group; the hive calls cells at fixed hooks, so the gate is not in the loop yet |
| Every part of engine, harness, loop | Partial | cells in the engine (JSON repair), coordinator (checklist, routing), researcher (source), verifier (evidence sentence), guard (order reading, family), hive loop (retry/reroute/stop). The big members still do open-ended reasoning, writing and code |
| New task -> clone the nearest specialist and edit the clone | Done | `training/cells_factory.py`: parent finder + clone + from-zero control. orders_any: clone 0.967 vs from zero 0.918 test; licence_open: clone 0.756 vs 0.807 (cloning did not help there) |
| More specialists, more coverage | Partial | 18 cells now; adding one is one command (`cells_pipeline.py` or `cells_factory.py`); growth is not automatic yet |

## GitHub

| requirement | status | what / evidence |
|---|---|---|
| Use HiveMIND, keep it updated | Done | pushed after every milestone; PR #1 merged; cells in PR #2 |

## Round 3: make it work for every kind of task (branch `make-it-work`, PR #5)

| requirement | status | what / evidence |
|---|---|---|
| Fix every problem found | Done for every one found | each dev bench failure read and fixed generally (training/reports/hive_bench/new_notes.md, new2_notes.md); 90 tests |
| Every task kind passes, as a hive, minimal compute | Partial | dev bench 7/16 (baseline) -> 9/16 -> 12/16 -> 14/16 (new3) -> 15/16 (new4, frozen 2574473). Held-out set 1, run once on frozen code: **9/16** (the honest number then); again after the fixes it informed: 13/16 (not clean). Held-out set 2 (16 fresh tasks, contamination-checked before any run): 11/16 on d45bc04. Held-out set 3 (16 more): **13/16** on 0147aa4 |
| Do NOT benchmax | Done, with leaks found and removed | training/contamination_check.py over all training data, cell generators and prompts: a calculator prompt example was a dev task (removed); cell generators named bench model ids, units, a category, a package and a version (removed, cells retrained); two held-out tasks were contaminated by older training data and were replaced before the held-out set ever ran. Older member training data still names some dev tasks' entities: those dev passes are marked as not evidence of generalisation |
| Teach it / alter weights so it uses the browser more naturally | Done | new browser weight edit from 52 recorded expert steps; cases 0.714 -> 0.786, skills 0.333 -> 0.5 (training/reports/browser/) |
| Smaller specialists for smaller tasks | Done | 25 cells; new this round: triage (task_kind), three research cells (gap finder 0.933 vs the 4B's 0.840; cross-check 0.953 vs 0.853), cells grown from the hive's own decisions (learned_claim, learned_item, learned_line) |
| Many swarms at once under 10 GB | Built; measurement pending | `--workers N` (one process, shared models); training/workers_bench.py queued |
| Give it a task and leave it, with a good SDK/interface | Done | team/sdk.py, team/api.py (OpenAI/Anthropic-compatible, jobs, SSE), checked with the official SDKs against a stand-in hive |
| One prompt, then talk to it normally; it does the rest | Done | `./hive`: team/converse.py routes each message (talk / work / project / stop / remember); the API's chat endpoints route the same way |
| A hive of many specialists working as one, not one big model | Done as far as measured | every judgement split into cells where they win; research hive (sub-questions, relevance, gaps, cross-checks, experiments) and coding hive (error reader, his examples as tests, previews); the big members keep what needs generation |
| Grow new specialists from new problems and new data | Done (mechanism); first grown cell pending | team/cells/learn.py + `python -m team grow`: member decisions logged, a cell trained on them with the member as teacher, answers only when as sure as dev showed; runs by itself when idle |
| Research that experiments and does math, not only reading | Done (built and tested); real-run evaluation pending | experiment/math sub-questions go to the coder; RESULT lines are claims backed by the program's output; arXiv papers read in full |
| Hard multi-day coding / long tasks | Done (built and tested) | team/project.py: milestones, a persistent workspace, resume after restart, the service works on open projects when idle |
| Always on, reachable, never damages the device | Done | `python -m team install` (systemd / launchd / logon task), team/health.py (low priority, a free core, idle unload, battery/heat/busy/RAM/disk checks, never deletes to make room), one instance only; checked live (health, lock, nice 10) |
| Unfiltered | Not done on purpose | the models' own safety training is not removed; the hive adds no refusals beyond his rules, and his explicit order is the approval |
| Better architecture: less RAM, faster | Partial | found: llama.cpp keeps a repacked second copy of the weights (the 4B 6.1 -> 3.6 GB without it); 8-bit KV already on; speed and answer equality measured by training/arch_bench.py (pending). The cell pool's first measurement failed (75x slower: a thread setting), fixed, off until re-measured |
| Perfect on every task | Not met | measured pass rates are above; no system does every task perfectly |

## Round 4: what the held-out set showed (same branch)

| finding | fix (general, checked in code, tested) |
|---|---|
| dev fixes carried over to fresh tasks far less than the dev score suggested (14/16 dev, 9/16 held-out) | a second held-out set, written and contamination-checked before it runs; failures are read for their cause, never tuned to the task |
| a chart shown with plt.show() and never saved passed the jury | a drawn chart with no image file is sent back and never passes; programs run with a non-window plotting backend |
| a value never found was covered with "Unknown" in every row; three jurors passed it | a placeholder column is a broken file; the data hint says never to use one; a missing element is looked up on the page itself ("class author is on <small>") |
| answers in the wrong form (weekday as 6, two decimals for one) | the calculator checks the form asked for in code and gets one fix; a weekday next to a date is corrected from the calendar; named answers pass the verifier |
| his own text handed back instead of translated or rewritten | its own writer prompt; a report that repeats his text (repeats included) is marked not done in code, which sends it to the fix and the editor |
| Wikipedia quotes never matched: the reader split every link onto its own line | the reader keeps inline text inline (one line per block); quotes match on their words in order |
| a long page crashed a model call (prompt over the window) | the engine fits every prompt to the model's window (the middle of the longest message is cut) |
| research questions went to the coder (triage) or got padded plans | a research question goes to the research hive; steps added "if needed" are dropped |
| no scholarly search (web search engines refuse automated queries) | OpenAlex (papers in every field, abstracts quotable, credited to the DOI); rate limits waited out as the server asks |
| 404s from links joined to the wrong page; a retry previewed the missing page | 404s get their own hint (urljoin to the page the link is on); a retry previews only his task's pages |
| a translation edit of the 1.7B (WMT24++, 900 pairs) | measured on 120 held-out sentences: +1.8 chrF over the writer, not clear; the 4B +3.2 over the edit (CI +0.7 to +5.6): translations go to the 4B, the edit is kept in adapters/.rejected |
| cells that won on synthetic data failed on real research text (answers_q 3/15, claims_agree rewordings as conflicts) | their jobs went to the 4B researcher and to a rule (two values for one thing); a cell answers first again only after a real-data check |
| research questions: the meta sub-question, battery "experiments", relevance on long sub-questions, unlabelled experiment results, over-claimed ticks | each fixed in code (research_eval_notes.md); the research hive has not been measured again since |
| engine: repacked weight copies and the 8-bit attention cache | off and on by measurement: 12.9 -> 8.2 GB peak and 1.6x faster with the same decisions |
