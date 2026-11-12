> **Muse's work** — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# Fable / make-it-work — Limits & Withholding Audit (2026-11-11)

Read-only audit of `~/workspace/fable-audit-copy` at make-it-work **d31fd51** / main **8be45ff**.
Question (Arnav): could the architecture be *intentionally* limiting things or withholding capabilities beyond what is disclosed?
Method: full read of SPEC.md, config, gates, feature flags, workflows, serving paths, and a git-history scan (329 commits on make-it-work) for commits that lowered a limit, raised a threshold, or disabled a feature. Nothing was edited or run except read-only inspection.

---

## A. Confirmed intentional limits — WITH disclosure in their own docs

These are deliberate. Every one is stated openly in the repo itself.

1. **Base models' safety training NOT removed ("unfiltered" refused).**
   - SPEC.md, "Models and weights": `| Unfiltered, no restrictions | Not done on purpose | the base models' own safety training was not removed. The team adds no filter beyond Arnav's own rules |`
   - SPEC.md, Round 3: `| Unfiltered | Not done on purpose | the models' own safety training is not removed; the hive adds no refusals beyond his rules, and his explicit order is the approval |`
   - README.md "Limits" (~line 1118): `**Not done on purpose:** removing the base models' built-in safety training. The team's filters are your rules above, nothing else.`
2. **"Match frontier assistants" not attempted to be claimed.**
   - SPEC.md: `| "Match frontier assistants, but better" | Not met | measured: 1.7-7B CPU models are far below frontier assistants on open-ended reasoning… |` and Round 3: `| Perfect on every task | Not met |`.
3. **Internals steering built but not run (disclosed).** SPEC.md: `| Edit internals directly… | Partial (built, not run) | training/steer.py: per-layer direction… |` — verified: `training/steer.py` exists; no `.cvec.json` file exists in `adapters_gguf/` (only 7 LoRA .gguf files), so no steering vector has ever been produced or served. The serving hook for one does exist (`team/llm.py:175` `_cvec_for`, env `AGENT_TEAM_CVEC_*` or `adapters_gguf/<role>.cvec.json`).
4. **Dream cycle: built, wired, not run as a full cycle (disclosed).** SPEC.md: dreaming `Partial` — "Not run as a full cycle here." Code check: `python -m team dream` is a real CLI command (`team/__main__.py`), and `team/serve.py:87-99` runs it automatically when idle (once/day cadence). So it is *reachable and scheduled*, not disabled — it simply had not completed a full cycle in their sessions.
5. **Smith swarm: built, partially exercised, no full competitive cycle (disclosed).** SPEC.md rates it `Partial`: "no full competitive cycle was run in this session (CPU time went to the demo and evals)"; smith-of-smiths "needs ≥2 trials per smith before it acts, so it has not fired yet." Code check: `team/smiths.py` is wired — CLI (`python -m team smiths`) and live routing (`team/hive.py:186-187`, `smiths.route(...)` — "a specialised clone, only where it measurably wins"). Note: unlike dream/school/evolve, smiths is **not** in serve.py's idle background rotation — it runs on demand or not at all. That matches the disclosure ("not exercised end-to-end"), and the reason given is CPU time, not a switch.
6. **Mixture-of-experts gate cell not in the serving loop (disclosed).** SPEC.md: "the gate cell routes 0.940 of test inputs to the right group; the hive calls cells at fixed hooks, so the gate is not in the loop yet." Verified: `cells/wins.json` has `gate: use=false` (score 0.94, no incumbent), and no serving code calls it as a router.
7. **Cell pool off by default (disclosed, measured).** `team/cells/pool.py`: `AGENT_TEAM_CELL_WORKERS` default 1 = no pool, with the measurement in the comment (2 workers: 7.9s vs 9.5s for 160 questions, +1.0 GB — "a second a task is not worth a GB"). SPEC.md: "The cell pool's first measurement failed (75x slower: a thread setting), fixed, off until re-measured."
8. **Arnav's own rules enforced as hard limits (by design, his spec).** Guard (`team/guard.py`): spend/delete/send/login/signup only when explicitly ordered; family topics dropped unless ordered; kill switch (`team/stop.py`). README "Limits": "No logins unless you allow a site per task; no sign-ups ever; CAPTCHAs are not solved." GitHub workflows run with `--approve never` and read-only tokens (`ask.yml`, `exam.yml`) — appropriate for a public repo, stated in the workflow comments.
9. **Measured-off features, each with its measurement in the repo:**
   - Prompt-lookup decoding OFF (`team/config.py`: `LOOKUP` default "0") — crashed on real prompts in llama-cpp-python 0.3.36 (`training/reports/arch_bench.json`).
   - llama.cpp repacked weight copies OFF (`REPACK` default "0") — with them, peak 12.9 GB, over the 10 GB budget; without, 7.8 GB, same verdicts.
   - BitNet "teacher" off by default — commit `334603b` with `training/reports/bitnet_recipe.json`: teacher helps per step (3.8081 vs 3.9963 @600 steps) but costs 1.7× time; equal-time no-teacher wins (3.6988).
   - Sleep/self-teaching of the stem cell "not built in" — commit `71e2d53`, `training/reports/sleep.json`: learns more per step, not per minute.
   - 22-layer cut of the 135M cell base rejected — faster (1.7×) but accuracy 0.936 → 0.789 (SPEC.md).

## B. Limits that are resource-justified

| Cap | Value | Where | Resource it matches |
|---|---|---|---|
| RAM budget | 10 GB default (`AGENT_TEAM_RAM_GB`) | `team/config.py:99` | Arnav's own spec: swarm under 10 GB, no VRAM, CPU only |
| Max base models resident | 2 (1 if RAM < 7 GB) | `team/config.py:114`, enforced `team/llm.py:261` | the 10 GB budget; LRU unload, ~4 s reload |
| Context window | 6144 tokens (4096 for 1.7B roles) | `team/config.py:112-113` | KV-cache size inside the RAM budget; prompts are middle-cut to fit (`team/llm.py:339-349`) rather than failing |
| Recruit ceiling | ≤2.0B params, file ≤2.3 GB | `team/recruit.py:35,76` | only models that can sit the roles' exams on CPU inside the budget |
| Cell/tiny model size | SmolLM2-135M base; tiny brain ~2.6M weights; stem cell 4096 vocab / dim 192 / 4 layers / ctx 256 | `training/scratch.py:51` | "smallest specialist possible" is Arnav's own requirement; a smaller cut was tried and lost (A9) |
| Workflow time budget | 180 budget-minutes per turn, job timeout 345 min, 10 min/birth, 3 births/body | `.github/workflows/hive.yml:34-39` | GitHub free runners: 360-min job limit; state is saved after every body so a cut-off loses little |
| Background-work health gates | training only below 75 °C CPU, not on battery, not when the device is busy; jobs refused below 1 GB free disk, nothing deleted to make room | `team/health.py:18,101`, `team/config.py` (DISK floor in `team/harvest.py:159`, `team/recruit.py:35`) | "never damages the device" requirement; notably conservative for a laptop with known thermal problems |
| Harvest source size | ≤300 MB per source file | `team/harvest.py:159` | disk floor (4 GB kept free) |

## C. Gates and thresholds — checked against the docs

All adoption gates in code match their documentation, and none was found set at a never-trigger level:

- **School graduation** (`team/school.py:38`): `GRADUATE=0.85, MARGIN=0.03, MIN_TEST=30, DONE=0.97`; enforced at `team/school.py:669` exactly as the docstring describes (≥85% agreement with the teacher AND ≥3 points over the untouched student). It has *not* fired: `cells/school.json` shows coordinator and coder both `graduated: false`. **But** the second, documented path has fired: both are `ahead: true`, and `team/school.py:554-560` (`holds`) lets an ahead student hold the job in the SMALL hive — `team/config.py` applies `runs_on` for graduated **or ahead** roles. So the stricter gate not firing is not withholding the capability; the capability is live in the small-only hive through the disclosed fallback. Git history: the school constants were only ever *added* (MIN_GAP, then MAX_GAP); 0.85/0.03/30 never changed.
- **Cell vs incumbent** (`team/cells/use.py`): a cell takes a job iff `wins.json` says `use: true`, which `training/cells_compare.py` writes from same-test measurements. Of 25 jobs: 20 cells hold their job; 5 don't — claim_support (cell 0.827 < verifier 0.88), licence_open (0.741 < 0.933), result_relevant (tied 1.0 vs 1.0 with a code rule that is 70× faster — note in wins.json explains), gate (A6), orders_any (factory-made cell, no incumbent recorded, guard uses the five per-kind order cells instead — `team/cells/use.py` `orders()`). Every non-adoption has a measured reason recorded.
- **Body birth gate** (`training/body.py:546`): `KEEP=0.001` overall gain, `HARM=0.01` per-territory regression limit, `IDLE=0.0005` retirement worth; newborn-local gate `LOCAL=0.004` (`training/body.py:91`). These are *small* numbers — births are refused often (by design: "keep it only if the body measures better"), but the bar is low, not unreachable; bodies demonstrably grew to 22 cells under it. `NEAR_M=4`, awake-cell cache 32, trainers capped at 8 with a 3-births-0-kept eviction (`training/body.py:567-581`) — population management, disclosed in code comments.
- **Learned cells** (`team/cells/learn.py:19`): `AGREE=0.97` — a cell grown from the hive's own decisions answers only at a confidence where it agreed with the member ≥97% on dev; otherwise the member answers (and the answer is logged as more training data). Strict, but it is a confidence fallback, not a block: the job is always answered by someone.
- **Tiny brain holds** (`cells/scratch/holds.json`): currently **empty** — the from-scratch brain holds no jobs. Rule (`team/cells/tiny.py:64`, `decide_holds`): score ≥ current holder on the same unseen test. Empty is a measurement outcome (2.6M weights vs trained 135M cells), and the same ≥ rule is what let cells take 20 jobs from bigger members. Worth watching on future refreshes, but nothing about the rule is asymmetric.
- **Run limits** (`team/config.py:124-129`): `MAX_STEPS=10, MAX_FOREACH=6, MAX_RETRIES=2, BROWSER_MAX_ACTIONS=14, CODER_MAX_ATTEMPTS=4`, `CODE_TIMEOUT=1800s`. These bound a single run's shape; retries re-route to another specialist rather than stopping (`team/hive.py:220`). Present since introduction; git history shows no lowering.
- **hive_state no-overwrite guard** (`training/hive_state.py:179` + commit `88f6a27`): a pull/save refuses to overwrite a hive with as many living cells or more unless `--force`. This is a data-loss guard (a stale clone can't erase growth), and `--force` exists and is used by the workflow itself.

## D. Git history — did any commit quietly reduce capability?

Scan of all 329 make-it-work commits (messages + targeted diffs on `team/config.py`, `team/school.py`, `training/body.py`):

- **No commit lowers a cap, raises a gate, or removes a feature.** The gate constants in school.py and body.py appear only as additions when the features were introduced; config limits were introduced at their current values.
- The only "off by default" commits are the measured ones in A9 (teacher `334603b`, sleep `71e2d53`), each landing *with its measurement report in the same commit*.
- Feature-disabling commits are the safety/robustness kind and are loud about it: `1a8426f` (abort the run if the hive can't be fetched, so it never starts a new hive by accident), `88f6a27` (never save over a bigger hive).

## E. Anything that looks like an *undisclosed* arbitrary cap or withheld capability?

**Nothing found that fits that description.** The closest candidates, weighed honestly:

1. **Smiths not in the idle rotation** (serve.py runs dream/grow/evolve/school/body/brain/recruit/life when idle, but never smiths). For withholding: the improvement swarm is the one system that improves *other* members, and it only runs when manually invoked. Against: SPEC.md discloses plainly that no full smith cycle was run and why (CPU time); the module is fully wired to the CLI and to live routing. Reads as unfinished scheduling, not concealment.
2. **Steering (internals editing) never executed.** For: it's the one "edit internals directly" capability with zero artifacts (no .cvec.json ever produced). Against: SPEC.md labels it "Partial (built, not run)" in the open; the builder and the serving hook both exist; running it costs the same scarce CPU everything else queues for.
3. **holds.json empty / no school graduations yet.** For: two headline "takeover" mechanisms have produced no takeovers. Against: both have documented secondary paths that *are* live (ahead-holds in the small hive; cells — the older mechanism — hold 20 of 25 jobs), and the records with the failing numbers are committed in the repo rather than hidden.

In each case the incompleteness is (a) disclosed in SPEC.md in plain words, and (b) better explained by the documented constraint — one CPU, sessions spent on the demo/evals/bench — than by intent.

## F. Bottom line

**No. The evidence does not support intentional withholding beyond what Fable discloses.**

Every deliberate limit found is either (1) stated verbatim in SPEC.md/README.md — chiefly the refusal to strip the base models' safety training, which is the single real "withheld capability" and is announced three times; (2) Arnav's own rules (guard, kill switch, no-signup/CAPTCHA limits); (3) resource-matched to the stated hardware and the free-runner budget; or (4) a measured-off feature shipped with its measurement. Gates match their docs, no gate was ever tightened in git history, and measured winners demonstrably do take jobs in the serving path (20/25 cell jobs, ahead-students in the small hive, bodies growing under the birth gate). What remains unbuilt or unrun — a full smith cycle, steering, gate-cell routing, tiny-brain holds — is labelled as such in their own checklist.

Counts: **9 disclosed intentional-limit items** (A), **8 resource-justified caps** (B), **0 undisclosed arbitrary caps or withheld capabilities** (E).
