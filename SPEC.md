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
| One big task end-to-end, live sources, real code, real verification, work shown | DEMO_STATUS | `demo/README.md` (generated from the run's own records), `demo/run/` |
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
| Kill switch: terminal, web, serve; halts models, browser, code; records where it stopped | KILL_STATUS | `team/stop.py`; Ctrl+C, `python -m team stop`, web Stop button, `inbox/STOP`; tests + `training/test_kill_switch.sh` |

## Models and weights

| requirement | status | what / evidence |
|---|---|---|
| Small specialists, no VRAM, under 16 GB RAM, no spending | Done | CPU only; peak measured in the demo run (`demo/run/memory.txt`); all models Apache-2.0, ungated |
| Unfiltered, no restrictions | Not done on purpose | the base models' own safety training was not removed. The team adds no filter beyond Arnav's own rules |
| Train them and edit weights; observe each specialist personally | Done | held-out evals per specialist (`training/observe.py`, `training/reports/`); LoRA edits for 6 members; kept only where they won |
| Edit internals directly; find the right ones | STEER_STATUS | `training/steer.py`: per-layer direction between right/wrong replies, layer+strength swept, gated; applied as llama.cpp control vector |
| Improve when they fail; more models; better architecture | Done | engine v2 (llama.cpp 4-bit), 4B brain, 7B coder, design fixes listed in README; every change measured |
| Shared weights across members | Done | one copy of each base; members hot-swap their edits per call (`team/llm.py`) |
| "Match frontier assistants, but better" | Not met | measured: 1.7-7B CPU models are far below frontier assistants on open-ended reasoning. The hive's design (verification, voting, re-routing) narrows the gap on structured tasks; it does not close it |

## Hive and smith swarm

| requirement | status | what / evidence |
|---|---|---|
| Many members, not 3 | Done | 14+ roles in `team/config.py`; swarm benchmark of SWARM_N members |
| Swarm of smiths, one kind of improvement each, several per job, competing, measured winners kept | Partial | `team/smiths.py`: 10 jobs, 15 smiths, ledger, competition + gate. Exercised: SMITHS_EXERCISED. Built but not exercised end-to-end here: cloner + router teacher on a real niche, retirer, the two competing weight trainers (CPU time) |
| Smiths improve, clone and specialise smiths | Partial | smith-of-smiths in code (`improve_smiths`); needs ≥2 trials per smith before it acts, so it has not fired yet |
| Huge swarm that keeps multiplying, members specialising | Partial | cloning, routing and retiring are built; growth happens as `dream`/`smiths` cycles run over time, not yet over many cycles |
| Huge swarm in under 10 GB | SWARM_STATUS | `training/swarm_bench.py` → `training/reports/swarm_bench.json` |

## Assistant behaviour

| requirement | status | what / evidence |
|---|---|---|
| Proactive, self-improving, learns tasks, dreaming | Partial | `python -m team dream`: replay, lessons, rehearsal, distil, gated retrain; runs automatically from `serve` when idle. DREAM_STATUS |
| Always available, any time | Done | `python -m team serve` (inbox + schedule), `python -m team web` (local page), `python -m team chat` |
| Complete tasks fully, no half work | Partial | checklist + critic + re-routing push for completeness; the demo shows where it still falls short |

## GitHub

| requirement | status | what / evidence |
|---|---|---|
| Use HiveMIND, keep it updated | Done | pushed after every milestone; draft PR #1 |
