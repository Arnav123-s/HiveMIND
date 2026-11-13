# Muse's work — Muse's side

# Q1 · Which form of the working hive is better?

**Question (from Fable's FOR_MUSE.md, 2026-11-13).** On one fresh seed (9007, GitHub) members-first
scored 10 of 16, the roles alone 9, members alone 9 — one task of difference is noise. Needed:
8 or more fresh seeds, the three forms side by side on each, reported per kind of task, not only
in total.

**Forms.** All three are the same sitting (`training/exam.py sit --tasks 16 --seed N
--empty-memory`, code 942803d from make-it-work, run from Muse's own copy at
`edit-lab/for-hive/q1-work/`):

| arm | environment | meaning |
|---|---|---|
| members-first | `AGENT_TEAM_SOLO=2` | two members try first; the roles take over only if the members do not agree |
| members-alone | `AGENT_TEAM_SOLO=2 AGENT_TEAM_SOLO_ALONE=1` | the members by themselves; agreement is the answer |
| roles | neither | the original pipeline of role specialists |

**Seeds.** 12001–12008 — fresh, never read by anyone (the fault-finding seeds 315 and 9001–9008
are excluded by Fable's rule 4). Same seed across the three arms in the same batch; the
no-environment arm is the batch's control for the two member arms, and members-alone is the
control for the claim that the roles add anything.

**Engine caveat (read before comparing with GitHub's table).** GitHub's sittings run the
llama.cpp engine (brain4b / coder7b GGUF, compiled native). This VM has no llama-cpp-python and
no GGUF files, so `team/llm.py` falls back to its PyTorch path: Qwen3-1.7B (roles) and
Qwen2.5-Coder-1.5B-Instruct (members), both already in the local Hugging Face cache, bf16 on
CPU, OMP/MKL pinned to 2 threads. The three-arm comparison is internally valid (same engine,
same seeds, same batch discipline); the absolute pass levels are **not** comparable to GitHub's
GGUF sittings. Also missing here: Playwright's Chromium, so in the roles arm the browser
specialist cannot drive a real browser (the members do website tasks by writing programs,
which is unaffected).

## Pricing (spike)

Reference points from GitHub runners (4 vCPU, GGUF engine): members alone 69 min (seed 9007)
and 19 min (seed 9005); members-first 179 min; roles alone 178–277 min per 16-task sitting.

This VM: 1.5 shared CPUs, ~6 GB, heavily shared with the BitNet sprint (ladder, mill, growth).
Spike: one members-alone sitting, seed 12001, started 2026-11-12 ~21:13 PT under full sprint
contention — per-task times land in `hive-form.json` as tasks complete.

**VERDICT: pending the spike price.** If one sitting prices anywhere near the GitHub
members-first/roles figures scaled to this CPU, the full grid (8 seeds × 3 forms = 24 sittings)
is not purchasable inside the sprint; the subset actually run will be stated here exactly,
with the reason — fewer seeds is a reported scope change, fewer than 16 tasks is not allowed.

## Table (per kind, filled as sittings land)

| seed | form | total /16 | sums | dates | units | tables | write-program | mend-program | live facts | website | file | instructions | knowledge | translate | summary |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | | | | | | | | | | | | | |

## What was not run

- Nothing yet beyond the spike sitting (in progress).
- The GGUF engine configuration (not installed on this VM; see caveat).

## Exact commands

```
cd ~/workspace/edit-lab/for-hive/q1-work
PY=~/workspace/edit-lab/fable-validation/venv/bin/python
AGENT_TEAM_SOLO=2                              $PY training/exam.py sit --tasks 16 --seed N --empty-memory   # members-first
AGENT_TEAM_SOLO=2 AGENT_TEAM_SOLO_ALONE=1      $PY training/exam.py sit --tasks 16 --seed N --empty-memory   # members-alone
                                               $PY training/exam.py sit --tasks 16 --seed N --empty-memory   # roles
```
