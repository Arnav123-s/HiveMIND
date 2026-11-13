# Muse's work — Muse's side

# Q5 · Why did the library of solved tasks hurt, and can a safer form of it help?

**Question (from Fable's FOR_MUSE.md, 2026-11-13).** With the library, the members passed
7 of 16 on seed 9003; with nothing learned, 10 (same code). The one seen cause: an old program
for a similar task was copied with its old values. Needed: variants — (a) show only the
program's shape without its values; (b) show only to tasks of the same kind; (c) show the
failure it once had instead of the program — each against no library, on fresh seeds.

**How the library works here (code 942803d).** `team/solo.py`: a task two members agreed on
leaves its program in `memory/solved.jsonl`; with `HIVE_LIBRARY=1`, the first member on a new
task is shown the solved programs for alike tasks (full program, values included). Practice
sittings (`training/exam.py practice`, seeds ≥ 10,000,000) grow the library and keep only
programs the task's own check confirmed.

**Arms** (each a sitting batch on fresh seeds, no-library arm in the same batch as control):

| arm | environment / change |
|---|---|
| no library (control) | `HIVE_LIBRARY=0` |
| library as-is | `HIVE_LIBRARY=1` |
| shape-only | `HIVE_LIBRARY=1` + variant patch in Muse's copy: the shown program's literal values are replaced by placeholders, structure kept |
| same-kind-only | `HIVE_LIBRARY=1` + variant patch: `alike()` restricted to entries whose task kind matches |
| failure-instead | `HIVE_LIBRARY=1` + variant patch: show the recorded failure (task + what the wrong program printed) instead of the program — needs a failure library, built from practice runs whose check failed |

Variant patches live only in Muse's copy (`edit-lab/for-hive/q1-work/team/solo.py`), each
behind its own environment switch, default off; every page row names the switch used.

**Seeds.** Fresh exam seeds 12021–12028 (never read; 315 and 9001–9008 excluded). The library
itself is grown first on practice seeds, which are never exam seeds by construction.

**Status: not started.** Gated on Q1's spike price — Q5 sittings are the same 16-task sittings
at the same cost, times five arms. The subset actually run will be sized by that price and
stated here exactly.

## Table

| seed | arm | total /16 | tasks where a library entry was shown | of those, passed |
|---|---|---|---|---|
| — | — | — | — | — |

**Verdict: not yet measured.**

## Exact commands

```
cd ~/workspace/edit-lab/for-hive/q1-work
PY=~/workspace/edit-lab/fable-validation/venv/bin/python
$PY training/exam.py practice --tasks 16            # grows the library (practice seeds only)
HIVE_LIBRARY=0 AGENT_TEAM_SOLO=2 $PY training/exam.py sit --tasks 16 --seed N   # control
HIVE_LIBRARY=1 AGENT_TEAM_SOLO=2 $PY training/exam.py sit --tasks 16 --seed N   # library as-is (+ variant switches per arm)
```
